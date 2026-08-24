import ollama
from config import MODEL_NAME, SYSTEM_PROMPT


def chat(message: str, history: list[dict], context_chunks: list[str] | None = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context_chunks:
        context_text = "\n\n".join(context_chunks)
        messages.append({
            "role": "system",
            "content": f"Relevant knowledge base context:\n{context_text}"
        })

    messages.extend(history)
    messages.append({"role": "user", "content": message})

    response = ollama.chat(model=MODEL_NAME, messages=messages)
    return response["message"]["content"]
