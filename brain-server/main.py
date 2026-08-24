from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from llm import chat
from database import init_db
import knowledge
import memory as mem
import config

app = FastAPI(title="NOX Brain Server")
init_db()

sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str


class TextKnowledgeRequest(BaseModel):
    text: str
    name: str = "manual text"


class UrlKnowledgeRequest(BaseModel):
    url: str


class MemoryRequest(BaseModel):
    fact: str


@app.get("/health")
def health():
    return {"status": "ok", "model": config.MODEL_NAME}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    history = sessions.get(req.session_id, [])
    context_chunks = knowledge.search(req.message)
    reply = chat(req.message, history, context_chunks)

    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    sessions[req.session_id] = history[-20:]

    return ChatResponse(reply=reply)


@app.post("/knowledge/text")
def knowledge_text(req: TextKnowledgeRequest):
    doc_id = knowledge.add_text(req.text, req.name)
    return {"doc_id": doc_id}


@app.post("/knowledge/pdf")
async def knowledge_pdf(file: UploadFile = File(...)):
    file_bytes = await file.read()
    doc_id = knowledge.add_pdf(file_bytes, file.filename)
    return {"doc_id": doc_id}


@app.post("/knowledge/url")
def knowledge_url(req: UrlKnowledgeRequest):
    doc_id = knowledge.add_url(req.url)
    return {"doc_id": doc_id}


@app.post("/knowledge/voice")
def knowledge_voice(transcript: str = Form(...), name: str = Form("voice note")):
    doc_id = knowledge.add_voice_transcript(transcript, name)
    return {"doc_id": doc_id}


@app.get("/knowledge/list")
def knowledge_list():
    return knowledge.list_knowledge()


@app.delete("/knowledge/{doc_id}")
def knowledge_delete(doc_id: str):
    knowledge.delete_knowledge(doc_id)
    return {"deleted": doc_id}


@app.post("/memory")
def memory_add(req: MemoryRequest):
    memory_id = mem.remember(req.fact)
    return {"id": memory_id}


@app.get("/memory")
def memory_list():
    return mem.list_memory()


@app.delete("/memory/{memory_id}")
def memory_delete(memory_id: int):
    mem.forget(memory_id)
    return {"deleted": memory_id}
