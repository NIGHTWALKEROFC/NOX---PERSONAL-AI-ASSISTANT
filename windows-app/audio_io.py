import io
import numpy as np
import sounddevice as sd
import soundfile as sf
import config


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
    data, samplerate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    sd.play(data, samplerate)
    sd.wait()
