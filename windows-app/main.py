import sys
import threading
from rich.console import Console
from rich.panel import Panel

import api_client
from voice_engine import VoiceEngine

console = Console()


def print_status(text: str):
    console.print(f"[dim]  ({text})[/dim]")


def stream_chat_to_terminal(text: str):
    console.print("[bold magenta]NOX:[/bold magenta] ", end="")
    try:
        started_reply = False
        for event in api_client.chat_stream(text, speak=False):
            if event["type"] == "status":
                if started_reply:
                    console.print()
                print_status(event["text"])
                console.print("[bold magenta]NOX:[/bold magenta] ", end="")
                started_reply = False
            elif event["type"] == "token":
                console.print(event["text"], end="")
                started_reply = True
            elif event["type"] == "done":
                console.print()
    except Exception as e:
        console.print(f"[bold red]\nError:[/bold red] {e}")


def run_gui():
    from PySide6.QtWidgets import QApplication
    from gui import MainWindow
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


def run_voice():
    def on_stream_token(t):
        console.print(t, end="")

    engine = VoiceEngine(
        on_status=print_status,
        on_transcript=lambda t: print_status(f"Heard: {t}"),
        on_reply=lambda t: console.print(),
        on_stream_token=on_stream_token,
    )
    engine.start()
    threading.Event().wait()


def run_chat_terminal():
    console.print(Panel(
        "NOX is online.\nType a message and press Enter, or just speak \"hey nox\" out loud.\n"
        "While NOX is talking, just start speaking to interrupt it (barge-in).\nType 'exit' to quit.",
        title="[bold green]NOX Assistant[/bold green]",
        border_style="green",
    ))
    while True:
        try:
            text = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("exit", "quit"):
            break
        stream_chat_to_terminal(text)


if __name__ == "__main__":
    threading.Thread(target=run_gui, daemon=True).start()
    threading.Thread(target=run_voice, daemon=True).start()
    run_chat_terminal()
