import requests
import config

BASE = config.SERVER_URL


def chat(message: str, speak: bool = False) -> dict:
    resp = requests.post(f"{BASE}/chat", json={
        "session_id": config.SESSION_ID,
        "message": message,
        "speak": speak,
    })
    resp.raise_for_status()
    return resp.json()


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


def add_pdf_knowledge(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        resp = requests.post(f"{BASE}/knowledge/pdf", files={"file": f})
    resp.raise_for_status()
    return resp.json()


def add_url_knowledge(url: str) -> dict:
    resp = requests.post(f"{BASE}/knowledge/url", json={"url": url})
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
