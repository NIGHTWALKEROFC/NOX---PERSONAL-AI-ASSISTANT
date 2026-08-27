import uuid
from database import get_conn


def _make_name(first_message: str) -> str:
    words = first_message.strip().split()
    name = " ".join(words[:6])
    if len(words) > 6:
        name += "..."
    return name[:60] if name else "New chat"


def ensure_chat(chat_id: str, first_message: str | None = None):
    conn = get_conn()
    row = conn.execute("SELECT id FROM chats WHERE id = ?", (chat_id,)).fetchone()
    if not row:
        name = _make_name(first_message) if first_message else "New chat"
        conn.execute("INSERT INTO chats (id, name) VALUES (?, ?)", (chat_id, name))
        conn.commit()
    conn.close()


def create_chat(name: str | None = None) -> str:
    chat_id = str(uuid.uuid4())
    conn = get_conn()
    conn.execute("INSERT INTO chats (id, name) VALUES (?, ?)", (chat_id, name or "New chat"))
    conn.commit()
    conn.close()
    return chat_id


def list_chats() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, created_at, updated_at FROM chats ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_messages(chat_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE chat_id = ? ORDER BY id ASC", (chat_id,)
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def append_message(chat_id: str, role: str, content: str, first_message_for_naming: str | None = None):
    ensure_chat(chat_id, first_message_for_naming)
    conn = get_conn()
    conn.execute(
        "INSERT INTO chat_messages (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, role, content)
    )
    conn.execute("UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()


def delete_chat(chat_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM chat_messages WHERE chat_id = ?", (chat_id,))
    conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()


def rename_chat(chat_id: str, name: str):
    conn = get_conn()
    conn.execute("UPDATE chats SET name = ? WHERE id = ?", (name, chat_id))
    conn.commit()
    conn.close()
