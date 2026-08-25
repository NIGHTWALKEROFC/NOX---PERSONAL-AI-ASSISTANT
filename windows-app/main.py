import sys
import threading
from rich.console import Console
from rich.panel import Panel

import api_client
from voice_engine import VoiceEngine

console = Console()


def print_nox(text: str):
    console.print(Panel(text, title="[bold magenta]NOX[/bold magenta]", border_style="magenta", expand=False))


def print_status(text: str):
    console.print(f"[dim]· {text}[/dim]")


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
        on_reply=print_nox,
    )
    engine.start()
    threading.Event().wait()


def run_chat_terminal():
    console.print(Panel(
        "NOX is online.\nType a message and press Enter, or just speak \"hey nox\" out loud.\nType 'exit' to quit.",
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
        try:
            result = api_client.chat(text, speak=False)
            print_nox(result["reply"])
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    threading.Thread(target=run_gui, daemon=True).start()
    threading.Thread(target=run_voice, daemon=True).start()
    run_chat_terminal()
