import ollama
from config import MODEL_NAME, SYSTEM_PROMPT
import settings
import tools


def _build_system_prompt() -> str:
    custom = settings.get_personality()
    if custom:
        return f"{SYSTEM_PROMPT}\n\nAdditional personality/instructions from the user:\n{custom}"
    return SYSTEM_PROMPT


def chat_stream(message: str, history: list[dict], context_chunks: list[str] | None = None):
    """Generator yielding dicts: {'type': 'status'|'token'|'done', ...}"""
    messages = [{"role": "system", "content": _build_system_prompt()}]

    if context_chunks:
        yield {"type": "status", "text": f"Searching knowledge... found {len(context_chunks)} relevant chunk(s)"}
        context_text = "\n\n".join(context_chunks)
        messages.append({
            "role": "system",
            "content": f"Relevant knowledge base context:\n{context_text}"
        })

    messages.extend(history)
    messages.append({"role": "user", "content": message})

    try:
        first = ollama.chat(model=MODEL_NAME, messages=messages, tools=tools.TOOL_DEFINITIONS)
        msg = first["message"]
        tool_calls = msg.get("tool_calls") or []
    except Exception:
        # Some Ollama/model combinations don't support tools — fall back silently.
        tool_calls = []

    if tool_calls:
        messages.append(msg)
        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn_args = call["function"].get("arguments") or {}
            yield {"type": "status", "text": f"Running command: {fn_name}..."}
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
    """Non-streaming wrapper, used where a single final string is simpler to consume."""
    full_text = ""
    for event in chat_stream(message, history, context_chunks):
        if event["type"] == "done":
            full_text = event["reply"]
    return full_text
