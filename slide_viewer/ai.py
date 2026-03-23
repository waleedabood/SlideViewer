"""AI assistant: background OpenAI worker thread and chat panel widget."""

import re

from PyQt6.QtCore import QSettings, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .models import SlideData


class AIWorker(QThread):
    """Background thread for OpenAI API calls."""

    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key: str, messages: list[dict], parent=None):
        super().__init__(parent)
        self._api_key = api_key
        self._messages = messages

    def run(self):
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self._messages,
                max_tokens=2000,
                temperature=0.7,
            )
            text = response.choices[0].message.content or ""
            self.response_ready.emit(text)
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class AIChatPanel(QWidget):
    """Bottom-left panel: chat UI with OpenAI integration."""

    slide_update_requested = pyqtSignal(str)
    slide_insert_requested = pyqtSignal(str)
    undo_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chat_history: list[dict] = []
        self._pre_ai_markdown: str | None = None
        self._pending_markdown: str | None = None
        self._worker: AIWorker | None = None
        self._settings = QSettings("SlideViewer", "SlideViewer")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        title = QLabel("AI Assistant — Current Slide Context")
        title.setStyleSheet("font-weight: bold; font-size: 13px; padding: 2px;")
        layout.addWidget(title)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(
            "background: #f7f7f8; border: 1px solid #ddd; border-radius: 6px; padding: 6px;"
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.chat_display)
        layout.addWidget(scroll, 1)

        input_row = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Ask the AI about this slide…")
        self.user_input.returnPressed.connect(self._on_send)
        input_row.addWidget(self.user_input, 1)
        layout.addLayout(input_row)

        chat_btn_style = (
            "QPushButton { padding: 4px 8px; border: 1px solid #bbb; "
            "border-radius: 4px; background: #f0f0f0; color: #1a1a1a; }"
            "QPushButton:hover { background: #dce6f0; }"
            "QPushButton:disabled { color: #aaa; background: #e8e8e8; }"
        )

        btn_row = QHBoxLayout()

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self._on_send)
        send_btn.setFixedWidth(55)
        send_btn.setStyleSheet(chat_btn_style)
        btn_row.addWidget(send_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_chat)
        clear_btn.setFixedWidth(55)
        clear_btn.setStyleSheet(chat_btn_style)
        btn_row.addWidget(clear_btn)

        self._replace_btn = QPushButton("Replace")
        self._replace_btn.clicked.connect(self._on_replace)
        self._replace_btn.setFixedWidth(65)
        self._replace_btn.setEnabled(False)
        self._replace_btn.setStyleSheet(chat_btn_style)
        btn_row.addWidget(self._replace_btn)

        self._insert_btn = QPushButton("Insert")
        self._insert_btn.clicked.connect(self._on_insert)
        self._insert_btn.setFixedWidth(55)
        self._insert_btn.setEnabled(False)
        self._insert_btn.setStyleSheet(chat_btn_style)
        btn_row.addWidget(self._insert_btn)

        self._undo_btn = QPushButton("Undo")
        self._undo_btn.clicked.connect(self._on_undo)
        self._undo_btn.setFixedWidth(55)
        self._undo_btn.setEnabled(False)
        self._undo_btn.setStyleSheet(chat_btn_style)
        btn_row.addWidget(self._undo_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        key_row = QHBoxLayout()
        key_label = QLabel("API Key:")
        key_label.setFixedWidth(55)
        key_row.addWidget(key_label)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-…")
        saved_key = self._settings.value("openai_api_key", "")
        if saved_key:
            self.api_key_input.setText(saved_key)
        self.api_key_input.textChanged.connect(self._save_api_key)
        key_row.addWidget(self.api_key_input, 1)
        layout.addLayout(key_row)

    def _save_api_key(self):
        self._settings.setValue("openai_api_key", self.api_key_input.text().strip())

    def _clear_chat(self):
        self._chat_history.clear()
        self.chat_display.clear()
        self._pre_ai_markdown = None
        self._pending_markdown = None
        self._replace_btn.setEnabled(False)
        self._insert_btn.setEnabled(False)
        self._undo_btn.setEnabled(False)

    def reset_for_slide(self):
        """Clear chat state when switching to a different slide."""
        self._clear_chat()

    def _append_bubble(self, role: str, text: str):
        color = "#d1e7ff" if role == "user" else "#e8e8e8"
        align = "right" if role == "user" else "left"
        label = "You" if role == "user" else "AI"
        escaped = text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        html = (
            f'<div style="text-align:{align}; margin: 6px 0;">'
            f'<span style="background:{color}; color: #1a1a1a; padding: 8px 12px; border-radius: 12px; '
            f'display: inline-block; max-width: 85%; text-align: left; font-size: 13px;">'
            f"<b>{label}:</b><br>{escaped}</span></div>"
        )
        self.chat_display.append(html)

    def send_message(self, slide_data: SlideData):
        """Called externally to trigger a send with current slide context."""
        message = self.user_input.text().strip()
        if not message:
            return

        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(
                self,
                "API Key Required",
                "Please enter your OpenAI API key in the field below the chat.",
            )
            return

        self._pre_ai_markdown = slide_data.current_markdown

        self._append_bubble("user", message)
        self._chat_history.append({"role": "user", "content": message})
        self.user_input.clear()
        self.user_input.setEnabled(False)

        system_prompt = (
            "You are a presentation slide editor assistant.\n"
            f"The user is editing Slide {slide_data.current_index + 1} "
            f"of {slide_data.total}.\n\n"
            "=== CURRENT SLIDE ===\n"
            f"{slide_data.current_markdown}\n"
            "=== END CURRENT SLIDE ===\n\n"
            "When the user asks you to make changes, respond with "
            "the complete updated slide markdown wrapped in a markdown code block "
            "(```markdown ... ```). Only return the content for this single slide. "
            "If the user asks a question without requesting changes, answer "
            "conversationally."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            *self._chat_history,
        ]

        self._worker = AIWorker(api_key, messages, parent=self)
        self._worker.response_ready.connect(self._on_response)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(lambda: self.user_input.setEnabled(True))
        self._worker.start()

    def _on_send(self):
        window = self.window()
        if hasattr(window, "slide_data"):
            window.slide_data.current_markdown = window.editor_panel.get_text()
            self.send_message(window.slide_data)

    def _on_response(self, text: str):
        self._chat_history.append({"role": "assistant", "content": text})
        self._append_bubble("assistant", text)

        match = re.search(r"```[\w]*\s*\n([\s\S]*?)```", text)
        if match:
            self._pending_markdown = match.group(1).strip()
        else:
            self._pending_markdown = text.strip()

        self._replace_btn.setEnabled(True)
        self._insert_btn.setEnabled(True)
        self._append_bubble(
            "assistant",
            "Click **Replace** to overwrite the slide, or **Insert** to add at cursor.",
        )

    def _on_replace(self):
        if self._pending_markdown is not None:
            self.slide_update_requested.emit(self._pending_markdown)
            self._undo_btn.setEnabled(True)
            self._replace_btn.setEnabled(False)
            self._insert_btn.setEnabled(False)
            self._append_bubble("assistant", "Replaced slide content.")
            self._pending_markdown = None

    def _on_insert(self):
        if self._pending_markdown is not None:
            self.slide_insert_requested.emit(self._pending_markdown)
            self._replace_btn.setEnabled(False)
            self._insert_btn.setEnabled(False)
            self._append_bubble("assistant", "Inserted at cursor position.")
            self._pending_markdown = None

    def _on_undo(self):
        if self._pre_ai_markdown is not None:
            self.undo_requested.emit(self._pre_ai_markdown)
            self._pre_ai_markdown = None
            self._undo_btn.setEnabled(False)
            self._append_bubble("assistant", "↩ Reverted to previous slide content.")

    def _on_error(self, error_text: str):
        self._append_bubble("assistant", f"⚠️ Error: {error_text}")
