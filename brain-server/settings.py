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


def is_code_execution_enabled() -> bool:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = 'code_execution_enabled'").fetchone()
    conn.close()
    # Off by default — this is real power (arbitrary code/commands on your PC),
    # so it requires an explicit opt-in rather than being on out of the box.
    return row["value"] == "1" if row else False


def set_code_execution_enabled(enabled: bool):
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('code_execution_enabled', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("1" if enabled else "0",)
    )
    conn.commit()
    conn.close()
