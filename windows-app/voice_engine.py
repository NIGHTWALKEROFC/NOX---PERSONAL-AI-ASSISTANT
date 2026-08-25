import threading
import time
import re
import numpy as np
from difflib import SequenceMatcher
from faster_whisper import WhisperModel
import config
import api_client
from audio_io import record_seconds, play_wav_bytes

WAKE_CANDIDATES = ["nox", "knox", "nots", "notes", "nodes", "knocks", "noks", "nox's"]
SLEEP_CANDIDATES = ["nox sleep", "nots sleep", "nodes sleep", "knox sleep"]


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
    def __init__(self, on_status=None, on_transcript=None, on_reply=None):
        self.on_status = on_status or (lambda s: None)
        self.on_transcript = on_transcript or (lambda t: None)
        self.on_reply = on_reply or (lambda t: None)
        self._running = False
        self._thread = None
        self._model = WhisperModel(config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        self._active = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _transcribe(self, audio) -> str:
        segments, _ = self._model.transcribe(audio, language="en", vad_filter=True)
        return " ".join(seg.text for seg in segments).strip().lower()

    def _speak(self, text: str):
        try:
            api_client.speak_text(text)
            audio_bytes = api_client.get_audio_bytes("/audio/ad_hoc.wav")
            play_wav_bytes(audio_bytes)
        except Exception as e:
            self.on_status(f"(could not speak: {e})")

    def _loop(self):
        self.on_status("listening for wake phrase")
        while self._running:
            duration = config.COMMAND_CHUNK_SECONDS if self._active else config.PASSIVE_CHUNK_SECONDS
            audio = record_seconds(duration)

            if _rms(audio) < 0.01:
                time.sleep(0.2)
                continue

            text = self._transcribe(audio)
            if not text or _is_garbage(text):
                time.sleep(0.2)
                continue

            self.on_transcript(text)

            if not self._active:
                if _contains_wake(text):
                    self._active = True
                    self.on_status("active — listening for command")
                    self.on_transcript("[WAKE WORD DETECTED]")
                    self._speak("Yes?")
                time.sleep(0.2)
                continue

            if _contains_sleep(text):
                self._active = False
                self.on_status("listening for wake phrase")
                self.on_transcript("[SLEEP]")
                self._speak("Going to sleep.")
                time.sleep(0.2)
                continue

            self.on_status("thinking")
            self.on_transcript(f"[SENDING: {text}]")
            try:
                result = api_client.chat(text, speak=True)
                reply = result["reply"]
                self.on_reply(reply)
                if result.get("audio_url"):
                    audio_bytes = api_client.get_audio_bytes(result["audio_url"])
                    play_wav_bytes(audio_bytes)
            except Exception as e:
                self.on_reply(f"(voice error: {e})")

            self.on_status("active — listening for command")
            time.sleep(0.2)
