from database import get_conn


def remember(fact: str) -> int:
    conn = get_conn()
    cur = conn.execute("INSERT INTO memory (fact) VALUES (?)", (fact,))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_memory() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM memory ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def forget(memory_id: int) -> bool:
    conn = get_conn()
    conn.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()
    return True
