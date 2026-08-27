import json
import requests
import config

BASE = config.SERVER_URL
CURRENT_SESSION_ID = config.SESSION_ID


def set_session(session_id: str):
    global CURRENT_SESSION_ID
    CURRENT_SESSION_ID = session_id


def get_session() -> str:
    return CURRENT_SESSION_ID


def chat(message: str, speak: bool = False) -> dict:
    resp = requests.post(f"{BASE}/chat", json={
        "session_id": CURRENT_SESSION_ID, "message": message, "speak": speak,
    })
    resp.raise_for_status()
    return resp.json()


def chat_stream(message: str, speak: bool = False):
    resp = requests.post(
        f"{BASE}/chat/stream",
        json={"session_id": CURRENT_SESSION_ID, "message": message, "speak": speak},
        stream=True,
    )
    resp.raise_for_status()
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        try:
            yield json.loads(line[len("data: "):])
        except json.JSONDecodeError:
            continue


def speak_text(text: str) -> dict:
    resp = requests.post(f"{BASE}/speak", json={"text": text})
    resp.raise_for_status()
    return resp.json()


def get_audio_bytes(audio_url: str) -> bytes:
    resp = requests.get(f"{BASE}{audio_url}")
    resp.raise_for_status()
    return resp.content


def add_text_knowledge(text: str, name: str = "manual text") -> dict:
    resp = requests.post(f"{BASE}/knowledge/text", json={"text": text, "name": name})
    resp.raise_for_status()
    return resp.json()


def add_pdf_knowledge(file_path: str, name: str | None = None) -> dict:
    with open(file_path, "rb") as f:
        data = {"name": name} if name else {}
        resp = requests.post(f"{BASE}/knowledge/pdf", files={"file": f}, data=data)
    resp.raise_for_status()
    return resp.json()


def add_image_knowledge(file_path: str, name: str | None = None) -> dict:
    with open(file_path, "rb") as f:
        data = {"name": name} if name else {}
        resp = requests.post(f"{BASE}/knowledge/image", files={"file": f}, data=data)
    resp.raise_for_status()
    return resp.json()


def add_url_knowledge(url: str, name: str | None = None) -> dict:
    resp = requests.post(f"{BASE}/knowledge/url", json={"url": url, "name": name})
    resp.raise_for_status()
    return resp.json()


def add_voice_knowledge(transcript: str, name: str = "voice note") -> dict:
    resp = requests.post(f"{BASE}/knowledge/voice", data={"transcript": transcript, "name": name})
    resp.raise_for_status()
    return resp.json()


def list_knowledge() -> list:
    resp = requests.get(f"{BASE}/knowledge/list")
    resp.raise_for_status()
    return resp.json()


def delete_knowledge(doc_id: str) -> dict:
    resp = requests.delete(f"{BASE}/knowledge/{doc_id}")
    resp.raise_for_status()
    return resp.json()


def add_memory(fact: str) -> dict:
    resp = requests.post(f"{BASE}/memory", json={"fact": fact})
    resp.raise_for_status()
    return resp.json()


def list_memory() -> list:
    resp = requests.get(f"{BASE}/memory")
    resp.raise_for_status()
    return resp.json()


def delete_memory(memory_id: int) -> dict:
    resp = requests.delete(f"{BASE}/memory/{memory_id}")
    resp.raise_for_status()
    return resp.json()


def get_personality() -> str:
    resp = requests.get(f"{BASE}/settings/personality")
    resp.raise_for_status()
    return resp.json().get("text", "")


def set_personality(text: str) -> dict:
    resp = requests.post(f"{BASE}/settings/personality", json={"text": text})
    resp.raise_for_status()
    return resp.json()


def create_chat(name: str | None = None) -> str:
    resp = requests.post(f"{BASE}/chats", json={"name": name})
    resp.raise_for_status()
    return resp.json()["id"]


def list_chats() -> list:
    resp = requests.get(f"{BASE}/chats")
    resp.raise_for_status()
    return resp.json()


def delete_chat(chat_id: str) -> dict:
    resp = requests.delete(f"{BASE}/chats/{chat_id}")
    resp.raise_for_status()
    return resp.json()


def save_chat_to_memory(chat_id: str) -> dict:
    resp = requests.post(f"{BASE}/chats/{chat_id}/save-to-memory")
    resp.raise_for_status()
    return resp.json()
