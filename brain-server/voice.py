import subprocess
import wave
from pathlib import Path

PIPER_DIR = Path(__file__).parent / "voice-models"
PIPER_EXE = PIPER_DIR / "piper.exe"
VOICE_MODEL = PIPER_DIR / "en_US-amy-medium.onnx"
OUTPUT_DIR = Path(__file__).parent / "data" / "tts_out"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def speak_to_file(text: str, filename: str = "reply.wav") -> Path:
    out_path = OUTPUT_DIR / filename
    process = subprocess.run(
        [
            str(PIPER_EXE),
            "--model", str(VOICE_MODEL),
            "--output_file", str(out_path),
        ],
        input=text.encode("utf-8"),
        capture_output=True,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Piper failed: {process.stderr.decode(errors='ignore')}")
    return out_path


def is_valid_wav(path: Path) -> bool:
    try:
        with wave.open(str(path), "rb"):
            return True
    except Exception:
        return False
