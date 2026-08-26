import io
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
import config

_playback_lock = threading.Lock()
_stop_flag = threading.Event()


def record_seconds(duration: float) -> np.ndarray:
    frames = sd.rec(
        int(duration * config.SAMPLE_RATE),
        samplerate=config.SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    return frames.flatten()


def play_wav_bytes(wav_bytes: bytes):
    """Blocking playback — used for short confirmations like 'Yes?'."""
    data, samplerate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    sd.play(data, samplerate)
    sd.wait()


def play_wav_bytes_interruptible(wav_bytes: bytes):
    """Playback that stop_playback() can cut short mid-sentence — used for full replies."""
    data, samplerate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    _stop_flag.clear()
    with _playback_lock:
        sd.play(data, samplerate)
        while True:
            try:
                stream = sd.get_stream()
                if not stream or not stream.active:
                    break
            except Exception:
                break
            if _stop_flag.is_set():
                sd.stop()
                break
            sd.sleep(50)


def stop_playback():
    _stop_flag.set()
    sd.stop()


def is_playing() -> bool:
    try:
        stream = sd.get_stream()
        return bool(stream and stream.active)
    except Exception:
        return False
