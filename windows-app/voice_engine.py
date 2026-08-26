import threading
import time
import re
import numpy as np
from difflib import SequenceMatcher
from faster_whisper import WhisperModel
import config
import api_client
from audio_io import record_seconds, play_wav_bytes, play_wav_bytes_interruptible, stop_playback, is_playing

WAKE_CANDIDATES = ["nox", "knox", "nots", "notes", "nodes", "knocks", "noks", "nox's"]
SLEEP_CANDIDATES = ["nox sleep", "nots sleep", "nodes sleep", "knox sleep"]

ACTIVE_TIMEOUT_SECONDS = 15
BARGE_IN_RMS_THRESHOLD = 0.03


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0


def _is_garbage(text: str) -> bool:
    if len(text) > 40 and len(set(text.replace(" ", ""))) <= 3:
        return True
    words = text.split()
    if len(words) > 6 and len(set(words)) <= 2:
        return True
    return False


def _contains_wake(text: str) -> bool:
    words = re.findall(r"[a-z']+", text.lower())
    for w in words:
        for candidate in WAKE_CANDIDATES:
            if SequenceMatcher(None, w, candidate).ratio() > 0.75:
                return True
    return False


def _contains_sleep(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in SLEEP_CANDIDATES) or (
        "sleep" in lowered and _contains_wake(lowered)
    )


class VoiceEngine:
    def __init__(self, on_status=None, on_transcript=None, on_reply=None, on_stream_token=None):
        self.on_status = on_status or (lambda s: None)
        self.on_transcript = on_transcript or (lambda t: None)
        self.on_reply = on_reply or (lambda t: None)
        self.on_stream_token = on_stream_token or (lambda t: None)
        self._running = False
        self._thread = None
        self._model = WhisperModel(config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        self._active = False
        self._active_since = 0.0

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        stop_playback()

    def _transcribe(self, audio) -> str:
        segments, _ = self._model.transcribe(audio, language=config.WHISPER_LANGUAGE, vad_filter=True)
        return " ".join(seg.text for seg in segments).strip().lower()

    def _speak_blocking(self, text: str):
        try:
            api_client.speak_text(text)
            audio_bytes = api_client.get_audio_bytes("/audio/ad_hoc.wav")
            play_wav_bytes(audio_bytes)
        except Exception as e:
            self.on_status(f"(could not speak: {e})")

    def _speak_reply_interruptible(self, wav_bytes: bytes):
        threading.Thread(target=play_wav_bytes_interruptible, args=(wav_bytes,), daemon=True).start()

    def _handle_command(self, text: str):
        self.on_status("thinking")
        self.on_transcript(f"[SENDING: {text}]")
        full_reply = ""
        try:
            for event in api_client.chat_stream(text, speak=True):
                if event["type"] == "status":
                    self.on_status(event["text"])
                elif event["type"] == "token":
                    full_reply += event["text"]
                    self.on_stream_token(event["text"])
                elif event["type"] == "done":
                    self.on_reply(event.get("reply", full_reply))
                    audio_url = event.get("audio_url")
                    if audio_url:
                        audio_bytes = api_client.get_audio_bytes(audio_url)
                        self._speak_reply_interruptible(audio_bytes)
        except Exception as e:
            self.on_reply(f"(voice error: {e})")

    def _loop(self):
        self.on_status("listening for wake phrase")
        while self._running:
            barging = is_playing()
            duration = 1.5 if barging else (config.COMMAND_CHUNK_SECONDS if self._active else config.PASSIVE_CHUNK_SECONDS)
            audio = record_seconds(duration)
            level = _rms(audio)

            if barging:
                if level > BARGE_IN_RMS_THRESHOLD:
                    text = self._transcribe(audio)
                    if text and not _is_garbage(text) and not _contains_sleep(text):
                        stop_playback()
                        self.on_transcript(f"[BARGE-IN: {text}]")
                        self._active = True
                        self._active_since = time.time()
                        self._handle_command(text)
                continue

            if level < 0.01:
                if self._active and (time.time() - self._active_since) > ACTIVE_TIMEOUT_SECONDS:
                    self._active = False
                    self.on_status("listening for wake phrase")
                    self.on_transcript("[TIMED OUT — back to passive listening]")
                time.sleep(0.15)
                continue

            text = self._transcribe(audio)
            if not text or _is_garbage(text):
                if self._active and (time.time() - self._active_since) > ACTIVE_TIMEOUT_SECONDS:
                    self._active = False
                    self.on_status("listening for wake phrase")
                    self.on_transcript("[TIMED OUT — back to passive listening]")
                time.sleep(0.15)
                continue

            self.on_transcript(text)

            if not self._active:
                if _contains_wake(text):
                    self._active = True
                    self._active_since = time.time()
                    self.on_status("active — listening for command")
                    self.on_transcript("[WAKE WORD DETECTED]")
                    self._speak_blocking("Yes?")
                time.sleep(0.15)
                continue

            if _contains_sleep(text):
                self._active = False
                self.on_status("listening for wake phrase")
                self.on_transcript("[SLEEP]")
                self._speak_blocking("Going to sleep.")
                time.sleep(0.15)
                continue

            self._active_since = time.time()
            self._handle_command(text)
            self.on_status("active — listening for command")
            time.sleep(0.15)
