SERVER_URL = "http://localhost:8420"
SESSION_ID = "windows-main"

WAKE_PHRASE = "hey nox"
SLEEP_PHRASE = "nox sleep"

SAMPLE_RATE = 16000
PASSIVE_CHUNK_SECONDS = 2.5
COMMAND_CHUNK_SECONDS = 4

# "small" gives noticeably better Malayalam/multilingual accuracy than "base".
# If replies feel slower after this change, drop back to "base".
WHISPER_MODEL_SIZE = "small"

# None = auto-detect language per utterance, so English and Malayalam
# both work without switching a setting. Set to "ml" to force Malayalam only,
# or "en" to force English only, if auto-detect ever guesses wrong.
WHISPER_LANGUAGE = None
