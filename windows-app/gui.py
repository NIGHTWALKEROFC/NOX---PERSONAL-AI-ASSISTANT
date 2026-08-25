from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QLabel, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject
import api_client
from voice_engine import VoiceEngine


class ChatTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message to NOX...")
        self.input.returnPressed.connect(self.send)
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send)

        row = QHBoxLayout()
        row.addWidget(self.input)
        row.addWidget(send_btn)

        layout.addWidget(self.display)
        layout.addLayout(row)

    def send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.display.append(f"You: {text}")
        self.input.clear()
        try:
            result = api_client.chat(text, speak=False)
            self.display.append(f"NOX: {result['reply']}")
        except Exception as e:
            self.display.append(f"[error: {e}]")

    def append_voice_line(self, who: str, text: str):
        self.display.append(f"{who}: {text}")


class TrainingTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        text_row = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Paste text to teach NOX...")
        add_text_btn = QPushButton("Add Text")
        add_text_btn.clicked.connect(self.add_text)
        text_row.addWidget(self.text_input)
        text_row.addWidget(add_text_btn)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://...")
        add_url_btn = QPushButton("Add URL")
        add_url_btn.clicked.connect(self.add_url)
        url_row.addWidget(self.url_input)
        url_row.addWidget(add_url_btn)

        pdf_btn = QPushButton("Add PDF File")
        pdf_btn.clicked.connect(self.add_pdf)

        self.list_widget = QListWidget()
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.refresh)
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected)

        layout.addLayout(text_row)
        layout.addLayout(url_row)
        layout.addWidget(pdf_btn)
        layout.addWidget(QLabel("Trained knowledge:"))
        layout.addWidget(self.list_widget)
        layout.addWidget(refresh_btn)
        layout.addWidget(delete_btn)

        self.refresh()

    def add_text(self):
        text = self.text_input.text().strip()
        if not text:
            return
        api_client.add_text_knowledge(text)
        self.text_input.clear()
        self.refresh()

    def add_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        try:
            api_client.add_url_knowledge(url)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
        self.url_input.clear()
        self.refresh()

    def add_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            api_client.add_pdf_knowledge(path)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        for item in api_client.list_knowledge():
            label = f"[{item['source_type']}] {item['source_name']} ({item['id'][:8]})"
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.UserRole, item["id"])
            self.list_widget.addItem(list_item)

    def delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        doc_id = item.data(Qt.UserRole)
        api_client.delete_knowledge(doc_id)
        self.refresh()


class MemoryTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Fact for NOX to remember...")
        add_btn = QPushButton("Remember")
        add_btn.clicked.connect(self.add)
        row.addWidget(self.input)
        row.addWidget(add_btn)

        self.list_widget = QListWidget()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        delete_btn = QPushButton("Forget Selected")
        delete_btn.clicked.connect(self.delete_selected)

        layout.addLayout(row)
        layout.addWidget(self.list_widget)
        layout.addWidget(refresh_btn)
        layout.addWidget(delete_btn)

        self.refresh()

    def add(self):
        fact = self.input.text().strip()
        if not fact:
            return
        api_client.add_memory(fact)
        self.input.clear()
        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        for item in api_client.list_memory():
            list_item = QListWidgetItem(item["fact"])
            list_item.setData(Qt.UserRole, item["id"])
            self.list_widget.addItem(list_item)

    def delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        memory_id = item.data(Qt.UserRole)
        api_client.delete_memory(memory_id)
        self.refresh()


class VoiceSignals(QObject):
    status = Signal(str)
    transcript = Signal(str)
    reply = Signal(str)


class SettingsTab(QWidget):
    def __init__(self, chat_tab: ChatTab):
        super().__init__()
        self.chat_tab = chat_tab
        layout = QVBoxLayout(self)

        self.status_label = QLabel("Voice: off")
        self.voice_toggle = QCheckBox("Enable voice control (wake phrase: 'hey nox')")
        self.voice_toggle.stateChanged.connect(self.toggle_voice)

        layout.addWidget(self.voice_toggle)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.signals = VoiceSignals()
        self.signals.status.connect(self.status_label.setText)
        self.signals.transcript.connect(lambda t: self.chat_tab.append_voice_line("Heard", t))
        self.signals.reply.connect(lambda t: self.chat_tab.append_voice_line("NOX (voice)", t))

        # Voice engine is NOT created here — creating it loads the speech model,
        # which takes time. It's only built the first time the user turns voice on,
        # so the app window opens instantly instead of appearing frozen.
        self.engine = None

    def toggle_voice(self, state):
        if state:
            self.status_label.setText("Voice: loading speech model (first time may take a moment)...")
            if self.engine is None:
                self.engine = VoiceEngine(
                    on_status=lambda s: self.signals.status.emit(f"Voice: {s}"),
                    on_transcript=lambda t: self.signals.transcript.emit(t),
                    on_reply=lambda t: self.signals.reply.emit(t),
                )
            self.engine.start()
        else:
            if self.engine:
                self.engine.stop()
            self.status_label.setText("Voice: off")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOX")
        self.resize(800, 600)

        tabs = QTabWidget()
        chat_tab = ChatTab()
        tabs.addTab(chat_tab, "Chat")
        tabs.addTab(TrainingTab(), "Training")
        tabs.addTab(MemoryTab(), "Memory")
        tabs.addTab(SettingsTab(chat_tab), "Settings")

        self.setCentralWidget(tabs)
