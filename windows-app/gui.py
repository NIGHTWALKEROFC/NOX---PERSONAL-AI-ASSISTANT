from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QLabel, QMessageBox, QTextEdit
)
from PySide6.QtCore import Qt
import api_client


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
        try:
            api_client.add_text_knowledge(text)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
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
        try:
            self.list_widget.clear()
            for item in api_client.list_knowledge():
                label = f"[{item['source_type']}] {item['source_name']} ({item['id'][:8]})"
                list_item = QListWidgetItem(label)
                list_item.setData(Qt.UserRole, item["id"])
                self.list_widget.addItem(list_item)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        doc_id = item.data(Qt.UserRole)
        try:
            result = api_client.delete_knowledge(doc_id)
            if not result.get("fully_removed", True):
                QMessageBox.warning(self, "Warning", "Delete may not have fully removed all data.")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
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
        try:
            api_client.add_memory(fact)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
        self.input.clear()
        self.refresh()

    def refresh(self):
        try:
            self.list_widget.clear()
            for item in api_client.list_memory():
                list_item = QListWidgetItem(item["fact"])
                list_item.setData(Qt.UserRole, item["id"])
                self.list_widget.addItem(list_item)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        memory_id = item.data(Qt.UserRole)
        try:
            api_client.delete_memory(memory_id)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
        self.refresh()


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Custom personality / instructions for NOX (applied to every conversation):"))
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        save_btn = QPushButton("Save Personality")
        save_btn.clicked.connect(self.save)
        layout.addWidget(save_btn)
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        self.load()

    def load(self):
        try:
            self.text_edit.setPlainText(api_client.get_personality())
        except Exception as e:
            self.status_label.setText(f"Could not load: {e}")

    def save(self):
        try:
            api_client.set_personality(self.text_edit.toPlainText())
            self.status_label.setText("Saved.")
        except Exception as e:
            self.status_label.setText(f"Could not save: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOX — Training, Memory & Settings")
        self.resize(700, 550)

        tabs = QTabWidget()
        tabs.addTab(TrainingTab(), "Training")
        tabs.addTab(MemoryTab(), "Memory")
        tabs.addTab(SettingsTab(), "Settings")

        self.setCentralWidget(tabs)
