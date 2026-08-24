import ollama
from config import MODEL_NAME, SYSTEM_PROMPT

def chat(message: str, history: list[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    response = ollama.chat(model=MODEL_NAME, messages=messages)
    return response["message"]["content"]
