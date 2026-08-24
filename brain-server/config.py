import os

MODEL_NAME = os.environ.get("NOX_MODEL", "llama3.1:8b")
HOST = "0.0.0.0"
PORT = 8420
SYSTEM_PROMPT = (
    "You are NOX, a private local AI assistant. Be direct, helpful, "
    "and concise unless asked for detail."
)
