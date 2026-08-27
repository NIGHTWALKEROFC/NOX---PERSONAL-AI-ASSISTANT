import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from llm import chat, chat_stream, summarize_chat_to_facts
from database import init_db
import knowledge
import memory as mem
import voice
import settings as app_settings
import chats
import config

app = FastAPI(title="NOX Brain Server")
init_db()

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


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
    name: str | None = None


class MemoryRequest(BaseModel):
    fact: str


class SpeakRequest(BaseModel):
    text: str


class PersonalityRequest(BaseModel):
    text: str


class CreateChatRequest(BaseModel):
    name: str | None = None


class RenameChatRequest(BaseModel):
    name: str


class CodeExecutionRequest(BaseModel):
    enabled: bool


@app.get("/health")
def health():
    return {"status": "ok", "model": config.MODEL_NAME}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    history = chats.get_messages(req.session_id)
    context_chunks = knowledge.search(req.message)
    reply = chat(req.message, history, context_chunks)

    chats.append_message(req.session_id, "user", req.message, first_message_for_naming=req.message)
    chats.append_message(req.session_id, "assistant", reply)

    audio_url = None
    if req.speak:
        voice.speak_to_file(reply, f"{req.session_id}_reply.wav")
        audio_url = f"/audio/{req.session_id}_reply.wav"

    return ChatResponse(reply=reply, audio_url=audio_url)


@app.post("/chat/stream")
def chat_stream_endpoint(req: ChatRequest):
    history = chats.get_messages(req.session_id)
    context_chunks = knowledge.search(req.message)

    def event_generator():
        full_reply = ""
        for event in chat_stream(req.message, history, context_chunks):
            if event["type"] == "done":
                full_reply = event["reply"]
                chats.append_message(req.session_id, "user", req.message, first_message_for_naming=req.message)
                chats.append_message(req.session_id, "assistant", full_reply)

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


async def _read_upload_guarded(file: UploadFile) -> bytes:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024*1024)}MB).")
    return data


@app.post("/knowledge/text")
def knowledge_text(req: TextKnowledgeRequest):
    doc_id = knowledge.add_text(req.text, req.name)
    return {"doc_id": doc_id}


@app.post("/knowledge/pdf")
async def knowledge_pdf(file: UploadFile = File(...), name: str = Form(None)):
    file_bytes = await _read_upload_guarded(file)
    doc_id = knowledge.add_pdf(file_bytes, name or file.filename)
    return {"doc_id": doc_id}


@app.post("/knowledge/image")
async def knowledge_image(file: UploadFile = File(...), name: str = Form(None)):
    file_bytes = await _read_upload_guarded(file)
    result = knowledge.add_image(file_bytes, file.filename, name)
    return result


@app.post("/knowledge/url")
def knowledge_url(req: UrlKnowledgeRequest):
    doc_id = knowledge.add_url(req.url, req.name)
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


@app.get("/settings/code-execution")
def get_code_execution():
    return {"enabled": app_settings.is_code_execution_enabled()}


@app.post("/settings/code-execution")
def set_code_execution(req: CodeExecutionRequest):
    app_settings.set_code_execution_enabled(req.enabled)
    return {"enabled": req.enabled}


@app.post("/chats")
def create_chat(req: CreateChatRequest):
    chat_id = chats.create_chat(req.name)
    return {"id": chat_id}


@app.get("/chats")
def list_chats():
    return chats.list_chats()


@app.get("/chats/{chat_id}/messages")
def get_chat_messages(chat_id: str):
    return chats.get_messages(chat_id)


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: str):
    chats.delete_chat(chat_id)
    return {"deleted": chat_id}


@app.put("/chats/{chat_id}/name")
def rename_chat(chat_id: str, req: RenameChatRequest):
    chats.rename_chat(chat_id, req.name)
    return {"renamed": chat_id, "name": req.name}


@app.post("/chats/{chat_id}/save-to-memory")
def save_chat_to_memory(chat_id: str):
    messages = chats.get_messages(chat_id)
    facts = summarize_chat_to_facts(messages)
    saved_ids = [mem.remember(fact) for fact in facts]
    return {"facts_saved": facts, "ids": saved_ids}
