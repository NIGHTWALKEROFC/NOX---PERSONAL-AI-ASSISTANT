import logging
import ollama
from config import MODEL_NAME, SYSTEM_PROMPT, NUM_CTX
import settings
import tools

logger = logging.getLogger("nox.llm")
HISTORY_TURNS = 12


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

    yield {"type": "status", "text": "Thinking..."}

    full_text = ""
    collected_tool_calls = []

    # Single streaming call, tools included — the previous version always ran
    # a separate non-streaming "check for tools" pass before this one, which
    # doubled generation time on every message even when no tool was needed.
    try:
        for chunk in ollama.chat(
            model=MODEL_NAME, messages=messages, tools=tools.TOOL_DEFINITIONS,
            stream=True, options={"num_ctx": NUM_CTX}
        ):
            msg = chunk.get("message", {})
            piece = msg.get("content")
            if piece:
                full_text += piece
                yield {"type": "token", "text": piece}
            tc = msg.get("tool_calls")
            if tc:
                collected_tool_calls.extend(tc)
    except Exception:
        logger.exception("Primary streaming chat call failed")

    # Only fire a second pass if a tool was actually requested and no reply
    # text came through yet (the model deferred to the tool instead of answering).
    if collected_tool_calls and not full_text:
        messages.append({"role": "assistant", "content": "", "tool_calls": collected_tool_calls})
        for call in collected_tool_calls:
            fn_name = call["function"]["name"]
            fn_args = call["function"].get("arguments") or {}
            yield {"type": "status", "text": f"Running: {fn_name}..."}
            fn = tools.TOOL_FUNCTIONS.get(fn_name)
            if fn:
                try:
                    result = fn(**fn_args) if fn_args else fn()
                except Exception as e:
                    logger.exception("Tool %s raised an exception", fn_name)
                    result = f"Error running {fn_name}: {e}"
            else:
                result = f"Unknown tool: {fn_name}"
            yield {"type": "status", "text": f"{fn_name} finished"}
            messages.append({"role": "tool", "content": result, "name": fn_name})

        yield {"type": "status", "text": "Thinking..."}
        try:
            for chunk in ollama.chat(model=MODEL_NAME, messages=messages, stream=True, options={"num_ctx": NUM_CTX}):
                piece = chunk["message"]["content"]
                if piece:
                    full_text += piece
                    yield {"type": "token", "text": piece}
        except Exception:
            logger.exception("Post-tool streaming chat call failed")
            if not full_text:
                full_text = "(something went wrong generating a reply — check nox.log for details)"

    if not full_text and not collected_tool_calls:
        full_text = "(no response — check nox.log for details)"

    yield {"type": "done", "reply": full_text}


def chat(message: str, history: list[dict], context_chunks: list[str] | None = None) -> str:
    full_text = ""
    for event in chat_stream(message, history, context_chunks):
        if event["type"] == "done":
            full_text = event["reply"]
    return full_text


def summarize_chat_to_facts(messages: list[dict]) -> list[str]:
    if not messages:
        return []
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    prompt = (
        "Read this conversation and extract up to 5 short standalone facts worth "
        "remembering long-term about the user or the discussion (one per line, no numbering, "
        "no extra commentary). If nothing is worth remembering, reply with just: NONE\n\n"
        f"{transcript}"
    )
    try:
        response = ollama.chat(
            model=MODEL_NAME, messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": NUM_CTX}
        )
    except Exception:
        logger.exception("summarize_chat_to_facts failed")
        return []
    text = response["message"]["content"].strip()
    if text.upper() == "NONE" or not text:
        return []
    return [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
