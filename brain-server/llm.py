import ollama
from config import MODEL_NAME, SYSTEM_PROMPT
import settings
import tools

HISTORY_TURNS = 12  # smaller window = less topic-bleeding between unrelated questions


def _build_system_prompt() -> str:
    custom = settings.get_personality()
    if custom:
        return f"{SYSTEM_PROMPT}\n\nAdditional personality/instructions from the user:\n{custom}"
    return SYSTEM_PROMPT


def chat_stream(message: str, history: list[dict], context_chunks: list[str] | None = None):
    messages = [{"role": "system", "content": _build_system_prompt()}]

    if context_chunks:
        yield {"type": "status", "text": f"Searching knowledge... found {len(context_chunks)} relevant chunk(s)"}
        context_text = "\n\n".join(context_chunks)
        messages.append({"role": "system", "content": f"Relevant knowledge base context:\n{context_text}"})

    messages.extend(history[-HISTORY_TURNS:])
    messages.append({"role": "user", "content": message})

    try:
        first = ollama.chat(model=MODEL_NAME, messages=messages, tools=tools.TOOL_DEFINITIONS)
        msg = first["message"]
        tool_calls = msg.get("tool_calls") or []
    except Exception:
        tool_calls = []

    if tool_calls:
        messages.append(msg)
        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn_args = call["function"].get("arguments") or {}
            yield {"type": "status", "text": f"Running: {fn_name}..."}
            fn = tools.TOOL_FUNCTIONS.get(fn_name)
            if fn:
                try:
                    result = fn(**fn_args) if fn_args else fn()
                except Exception as e:
                    result = f"Error running {fn_name}: {e}"
            else:
                result = f"Unknown tool: {fn_name}"
            yield {"type": "status", "text": f"{fn_name} finished"}
            messages.append({"role": "tool", "content": result, "name": fn_name})

    yield {"type": "status", "text": "Thinking..."}

    full_text = ""
    for chunk in ollama.chat(model=MODEL_NAME, messages=messages, stream=True):
        piece = chunk["message"]["content"]
        if piece:
            full_text += piece
            yield {"type": "token", "text": piece}

    yield {"type": "done", "reply": full_text}


def chat(message: str, history: list[dict], context_chunks: list[str] | None = None) -> str:
    full_text = ""
    for event in chat_stream(message, history, context_chunks):
        if event["type"] == "done":
            full_text = event["reply"]
    return full_text


def summarize_chat_to_facts(messages: list[dict]) -> list[str]:
    """Used by 'save chat to memory' — condenses a conversation into short standalone facts."""
    if not messages:
        return []
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    prompt = (
        "Read this conversation and extract up to 5 short standalone facts worth "
        "remembering long-term about the user or the discussion (one per line, no numbering, "
        "no extra commentary). If nothing is worth remembering, reply with just: NONE\n\n"
        f"{transcript}"
    )
    response = ollama.chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
    text = response["message"]["content"].strip()
    if text.upper() == "NONE" or not text:
        return []
    return [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
