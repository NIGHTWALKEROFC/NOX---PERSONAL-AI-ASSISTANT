import threading
import time
from faster_whisper import WhisperModel
import config
import api_client
from audio_io import record_seconds, play_wav_bytes


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
        segments, _ = self._model.transcribe(audio, language="en")
        return " ".join(seg.text for seg in segments).strip().lower()

    def _loop(self):
        self.on_status("listening for wake phrase")
        while self._running:
            duration = config.COMMAND_CHUNK_SECONDS if self._active else config.PASSIVE_CHUNK_SECONDS
            audio = record_seconds(duration)
            text = self._transcribe(audio)
            if not text:
                continue

            self.on_transcript(text)

            if not self._active:
                if config.WAKE_PHRASE in text:
                    self._active = True
                    self.on_status("active — listening for command")
                continue

            if config.SLEEP_PHRASE in text:
                self._active = False
                self.on_status("listening for wake phrase")
                continue

            self.on_status("thinking")
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
