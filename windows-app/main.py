import logging
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

import sys
import threading
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.theme import Theme

import api_client
from voice_engine import VoiceEngine
from paste_safe_input import PasteSafeInput

nox_theme = Theme({
    "you": "bold #A8C7FA",
    "nox": "bold #E8A87C",
    "status": "italic #8A8A8A",
    "err": "bold #E06C75",
})
console = Console(theme=nox_theme)


def print_status(text: str):
    console.print(f"  · {text}", style="status")


def print_nox_reply(text: str):
    console.print("[nox]NOX[/nox] ", end="")
    try:
        console.print(Markdown(text))
    except Exception:
        console.print(text)


def stream_chat_to_terminal(text: str):
    full = ""
    saw_status = False
    with console.status("[status]thinking...[/status]", spinner="dots") as status:
        try:
            for event in api_client.chat_stream(text, speak=False):
                if event["type"] == "status":
                    status.update(f"[status]{event['text']}[/status]")
                    saw_status = True
                elif event["type"] == "token":
                    full += event["text"]
                elif event["type"] == "done":
                    pass
        except Exception as e:
            console.print(f"\n[err]Error:[/err] {e}")
            return
    print_nox_reply(full if full else "(no response)")


def run_gui():
    from PySide6.QtWidgets import QApplication
    from gui import MainWindow
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


def run_voice():
    engine = VoiceEngine(
        on_status=print_status,
        on_transcript=lambda t: print_status(f"Heard: {t}"),
        on_reply=lambda t: print_nox_reply(t),
    )
    engine.start()
    threading.Event().wait()


def print_help():
    console.print(Panel(
        "[bold]/new[/bold]              start a new named chat\n"
        "[bold]/chats[/bold]            list saved chats\n"
        "[bold]/load <id-start>[/bold]  switch to a chat (paste first few characters of its id)\n"
        "[bold]/delete <id-start>[/bold] delete a saved chat\n"
        "[bold]/savechat[/bold]         summarize the current chat into long-term memory\n"
        "[bold]/help[/bold]             show this again\n"
        "[bold]exit[/bold]              quit",
        title="Commands", border_style="#8A8A8A"
    ))


def resolve_chat_id(prefix: str) -> str | None:
    for c in api_client.list_chats():
        if c["id"].startswith(prefix):
            return c["id"]
    return None


def run_chat_terminal():
    console.print(Panel(
        f"NOX is online. Chat: [status]{api_client.get_session()[:8]}[/status]\n"
        "Type a message and press Enter, or speak \"hey nox\" out loud.\n"
        "Type /help for chat management commands.",
        title="[nox]NOX Assistant[/nox]", border_style="#E8A87C",
    ))
    reader = PasteSafeInput()

    while True:
        console.print("[you]You:[/you] ", end="")
        text = reader.get_message()
        if text is None:
            break
        if not text:
            continue

        if text.lower() in ("exit", "quit"):
            break
        if text == "/help":
            print_help()
            continue
        if text == "/new":
            new_id = api_client.create_chat()
            api_client.set_session(new_id)
            console.print(f"[status]Started new chat: {new_id[:8]}[/status]")
            continue
        if text == "/chats":
            for c in api_client.list_chats():
                console.print(f"  {c['id'][:8]}  {c['name']}")
            continue
        if text.startswith("/load "):
            prefix = text.split(" ", 1)[1].strip()
            found = resolve_chat_id(prefix)
            if found:
                api_client.set_session(found)
                console.print(f"[status]Switched to chat: {found[:8]}[/status]")
            else:
                console.print("[err]No matching chat found.[/err]")
            continue
        if text.startswith("/delete "):
            prefix = text.split(" ", 1)[1].strip()
            found = resolve_chat_id(prefix)
            if found:
                api_client.delete_chat(found)
                console.print(f"[status]Deleted chat: {found[:8]}[/status]")
            else:
                console.print("[err]No matching chat found.[/err]")
            continue
        if text == "/savechat":
            result = api_client.save_chat_to_memory(api_client.get_session())
            facts = result.get("facts_saved", [])
            if facts:
                console.print("[status]Saved to memory:[/status]")
                for f in facts:
                    console.print(f"  • {f}")
            else:
                console.print("[status]Nothing notable to save.[/status]")
            continue

        stream_chat_to_terminal(text)


if __name__ == "__main__":
    threading.Thread(target=run_gui, daemon=True).start()
    threading.Thread(target=run_voice, daemon=True).start()
    run_chat_terminal()
