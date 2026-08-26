import json
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from llm import chat, chat_stream
from database import init_db
import knowledge
import memory as mem
import voice
import settings as app_settings
import config

app = FastAPI(title="NOX Brain Server")
init_db()

sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    speak: bool = False


class ChatResponse(BaseModel):
    reply: str
    audio_url: str | None = None


class TextKnowledgeRequest(BaseModel):
    text: str
    name: str = "manual text"


class UrlKnowledgeRequest(BaseModel):
    url: str


class MemoryRequest(BaseModel):
    fact: str


class SpeakRequest(BaseModel):
    text: str


class PersonalityRequest(BaseModel):
    text: str


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

    audio_url = None
    if req.speak:
        voice.speak_to_file(reply, f"{req.session_id}_reply.wav")
        audio_url = f"/audio/{req.session_id}_reply.wav"

    return ChatResponse(reply=reply, audio_url=audio_url)


@app.post("/chat/stream")
def chat_stream_endpoint(req: ChatRequest):
    history = sessions.get(req.session_id, [])
    context_chunks = knowledge.search(req.message)

    def event_generator():
        full_reply = ""
        for event in chat_stream(req.message, history, context_chunks):
            if event["type"] == "done":
                full_reply = event["reply"]
                history.append({"role": "user", "content": req.message})
                history.append({"role": "assistant", "content": full_reply})
                sessions[req.session_id] = history[-20:]

                audio_url = None
                if req.speak and full_reply:
                    voice.speak_to_file(full_reply, f"{req.session_id}_reply.wav")
                    audio_url = f"/audio/{req.session_id}_reply.wav"
                event = {**event, "audio_url": audio_url}

            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/speak")
def speak_endpoint(req: SpeakRequest):
    voice.speak_to_file(req.text, "ad_hoc.wav")
    return {"audio_url": "/audio/ad_hoc.wav"}


@app.get("/audio/{filename}")
def get_audio(filename: str):
    path = voice.OUTPUT_DIR / filename
    return FileResponse(path, media_type="audio/wav")


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
    return knowledge.delete_knowledge(doc_id)


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


@app.get("/settings/personality")
def get_personality():
    return {"text": app_settings.get_personality()}


@app.post("/settings/personality")
def set_personality(req: PersonalityRequest):
    app_settings.set_personality(req.text)
    return {"saved": True}
