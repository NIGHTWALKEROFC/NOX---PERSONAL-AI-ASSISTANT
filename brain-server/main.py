from fastapi import FastAPI
from pydantic import BaseModel
from llm import chat
import config

app = FastAPI(title="NOX Brain Server")

# in-memory session history (per-session id), simple and functional
sessions: dict[str, list[dict]] = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.get("/health")
def health():
    return {"status": "ok", "model": config.MODEL_NAME}

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    history = sessions.get(req.session_id, [])
    reply = chat(req.message, history)

    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    sessions[req.session_id] = history[-20:]  # keep last 20 turns

    return ChatResponse(reply=reply)
