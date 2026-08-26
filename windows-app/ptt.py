import numpy as np
from faster_whisper import WhisperModel
import config
import api_client
from audio_io import record_seconds, play_wav_bytes

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel(config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def push_to_talk(duration: float = 5.0) -> tuple[str, str]:
    """Records `duration` seconds, transcribes, sends to NOX, speaks the reply.
    Returns (heard_text, reply_text)."""
    audio = record_seconds(duration)
    if float(np.sqrt(np.mean(np.square(audio)))) < 0.005:
        return "", "(heard nothing)"

    model = _get_model()
    segments, _ = model.transcribe(audio, language=config.WHISPER_LANGUAGE, vad_filter=True)
    text = " ".join(seg.text for seg in segments).strip()
    if not text:
        return "", "(could not understand)"

    try:
        result = api_client.chat(text, speak=True)
        reply = result["reply"]
        if result.get("audio_url"):
            audio_bytes = api_client.get_audio_bytes(result["audio_url"])
            play_wav_bytes(audio_bytes)
        return text, reply
    except Exception as e:
        return text, f"(error: {e})"
