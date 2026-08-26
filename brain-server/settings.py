from database import get_conn

DEFAULT_PERSONALITY = ""


def get_personality() -> str:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = 'personality'").fetchone()
    conn.close()
    return row["value"] if row else DEFAULT_PERSONALITY


def set_personality(text: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('personality', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (text,)
    )
    conn.commit()
    conn.close()
