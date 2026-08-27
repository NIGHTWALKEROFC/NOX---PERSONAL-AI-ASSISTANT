import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).parent / "data"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "nox.log"


def setup_logging():
    # Quiet the noisy-but-harmless HF Hub line, same as before.
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Rotating: keeps nox.log under 5MB, keeps 5 old copies (nox.log.1 .. .5)
    # before deleting the oldest — so it never grows forever, and you always
    # have recent history to check after something breaks overnight.
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root.addHandler(file_handler)

    return logging.getLogger("nox")
