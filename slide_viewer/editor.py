"""Markdown syntax highlighter and editor panel widget."""

import re

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MarkdownHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for markdown in QPlainTextEdit."""

    EDITOR_BG = "#1e1e2e"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = []
        self._code_block_fmt = QTextCharFormat()
        self._clean_mode = False
        self._html_tag_re = re.compile(r"<!--.*?-->|</?[a-zA-Z][^>]*>")
        self._hidden_fmt = QTextCharFormat()
        self._hidden_fmt.setForeground(QColor(self.EDITOR_BG))
        self._hidden_fmt.setFontPointSize(1)
        self._build_rules()

    @property
    def clean_mode(self) -> bool:
        return self._clean_mode

    @clean_mode.setter
    def clean_mode(self, enabled: bool):
        if self._clean_mode != enabled:
            self._clean_mode = enabled
            self.rehighlight()

    def _build_rules(self):
        heading = QTextCharFormat()
        heading.setForeground(QColor("#89b4fa"))
        heading.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r"^#{1,6}\s.*", re.MULTILINE), heading))

        bold = QTextCharFormat()
        bold.setFontWeight(QFont.Weight.Bold)
        bold.setForeground(QColor("#f5c2e7"))
        self._rules.append((re.compile(r"\*\*[^*]+\*\*"), bold))

        italic = QTextCharFormat()
        italic.setFontItalic(True)
        italic.setForeground(QColor("#f5c2e7"))
        self._rules.append((re.compile(r"(?<!\*)\*[^*]+\*(?!\*)"), italic))

        code = QTextCharFormat()
        code.setFontFamily("Courier New")
        code.setForeground(QColor("#a6e3a1"))
        self._rules.append((re.compile(r"`[^`]+`"), code))

        link = QTextCharFormat()
        link.setForeground(QColor("#74c7ec"))
        link.setFontUnderline(True)
        self._rules.append((re.compile(r"\[.*?\]\(.*?\)"), link))

        bquote = QTextCharFormat()
        bquote.setForeground(QColor("#9399b2"))
        bquote.setFontItalic(True)
        self._rules.append((re.compile(r"^>\s.*", re.MULTILINE), bquote))

        list_marker = QTextCharFormat()
        list_marker.setForeground(QColor("#fab387"))
        self._rules.append((re.compile(r"^[\s]*[-*+]\s", re.MULTILINE), list_marker))
        self._rules.append((re.compile(r"^[\s]*\d+\.\s", re.MULTILINE), list_marker))

        self._code_block_fmt.setForeground(QColor("#a6e3a1"))
        self._code_block_fmt.setFontFamily("Courier New")

    def highlightBlock(self, text: str):
        prev_state = self.previousBlockState()
        if prev_state == 1:
            self.setFormat(0, len(text), self._code_block_fmt)
            if text.strip().startswith("```"):
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(1)
            return

        if text.strip().startswith("```"):
            self.setFormat(0, len(text), self._code_block_fmt)
            if not text.strip()[3:].strip() or not text.strip().endswith("```"):
                self.setCurrentBlockState(1)
            return

        self.setCurrentBlockState(0)
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)

        if self._clean_mode:
            for m in self._html_tag_re.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), self._hidden_fmt)


class MarkdownEditorPanel(QWidget):
    """Top-left panel: markdown text editor with Apply button."""

    content_changed = pyqtSignal()
    apply_requested = pyqtSignal()
    image_insert_requested = pyqtSignal()
    image_edit_requested = pyqtSignal()
    table_insert_requested = pyqtSignal()
    table_edit_requested = pyqtSignal()
    columns_insert_requested = pyqtSignal()
    columns_edit_requested = pyqtSignal()
    color_requested = pyqtSignal()
    font_requested = pyqtSignal()
    fontsize_requested = pyqtSignal()
    slide_theme_requested = pyqtSignal()
    clean_view_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(3)
        title = QLabel("Markdown")
        title.setStyleSheet("font-weight: bold; font-size: 13px; padding: 2px;")
        header.addWidget(title)
        header.addStretch()

        icon_btn_style = (
            "QPushButton { font-size: 16px; padding: 2px; border: 1px solid #bbb; "
            "border-radius: 4px; background: #f0f0f0; color: #1a1a1a; }"
            "QPushButton:hover { background: #dce6f0; }"
        )
        icon_size = 30

        img_btn = QPushButton("\U0001f5bc")
        img_btn.setToolTip("Insert Image")
        img_btn.setFixedSize(icon_size, icon_size)
        img_btn.setStyleSheet(icon_btn_style)
        img_btn.clicked.connect(self.image_insert_requested.emit)
        header.addWidget(img_btn)

        edit_img_btn = QPushButton("\U0001f5bc\u270f")
        edit_img_btn.setToolTip("Edit Image")
        edit_img_btn.setFixedSize(icon_size + 6, icon_size)
        edit_img_btn.setStyleSheet(icon_btn_style)
        edit_img_btn.clicked.connect(self.image_edit_requested.emit)
        header.addWidget(edit_img_btn)

        tbl_btn = QPushButton("\u2637")
        tbl_btn.setToolTip("Insert Table")
        tbl_btn.setFixedSize(icon_size, icon_size)
        tbl_btn.setStyleSheet(icon_btn_style)
        tbl_btn.clicked.connect(self.table_insert_requested.emit)
        header.addWidget(tbl_btn)

        edit_tbl_btn = QPushButton("\u2637\u270f")
        edit_tbl_btn.setToolTip("Edit Table")
        edit_tbl_btn.setFixedSize(icon_size + 6, icon_size)
        edit_tbl_btn.setStyleSheet(icon_btn_style)
        edit_tbl_btn.clicked.connect(self.table_edit_requested.emit)
        header.addWidget(edit_tbl_btn)

        cols_btn = QPushButton("\u25a5")
        cols_btn.setToolTip("Insert Column Layout")
        cols_btn.setFixedSize(icon_size, icon_size)
        cols_btn.setStyleSheet(icon_btn_style)
        cols_btn.clicked.connect(self.columns_insert_requested.emit)
        header.addWidget(cols_btn)

        edit_cols_btn = QPushButton("\u25a5\u270f")
        edit_cols_btn.setToolTip("Edit Column Layout")
        edit_cols_btn.setFixedSize(icon_size + 6, icon_size)
        edit_cols_btn.setStyleSheet(icon_btn_style)
        edit_cols_btn.clicked.connect(self.columns_edit_requested.emit)
        header.addWidget(edit_cols_btn)

        color_btn = QPushButton("\U0001f3a8")
        color_btn.setToolTip("Color selected text")
        color_btn.setFixedSize(icon_size, icon_size)
        color_btn.setStyleSheet(icon_btn_style)
        color_btn.clicked.connect(self.color_requested.emit)
        header.addWidget(color_btn)

        font_btn = QPushButton("F")
        font_btn.setToolTip("Change font of selected text")
        font_btn.setFixedSize(icon_size, icon_size)
        font_btn.setStyleSheet(
            "QPushButton { font-size: 14px; font-weight: bold; font-family: serif; "
            "padding: 2px; border: 1px solid #bbb; border-radius: 4px; "
            "background: #f0f0f0; color: #1a1a1a; }"
            "QPushButton:hover { background: #dce6f0; }"
        )
        font_btn.clicked.connect(self.font_requested.emit)
        header.addWidget(font_btn)

        size_btn = QPushButton("T\u2195")
        size_btn.setToolTip("Change size of selected text")
        size_btn.setFixedSize(icon_size, icon_size)
        size_btn.setStyleSheet(icon_btn_style)
        size_btn.clicked.connect(self.fontsize_requested.emit)
        header.addWidget(size_btn)

        theme_btn = QPushButton("\u25d0")
        theme_btn.setToolTip("Per-slide theme override")
        theme_btn.setFixedSize(icon_size, icon_size)
        theme_btn.setStyleSheet(icon_btn_style)
        theme_btn.clicked.connect(self.slide_theme_requested.emit)
        header.addWidget(theme_btn)

        self._clean_btn = QPushButton("\U0001f441")
        self._clean_btn.setToolTip("Clean View — hide HTML tags")
        self._clean_btn.setCheckable(True)
        self._clean_btn.setFixedSize(icon_size, icon_size)
        self._clean_btn.setStyleSheet(
            "QPushButton { font-size: 15px; padding: 2px; border: 1px solid #bbb; "
            "border-radius: 4px; background: #f0f0f0; color: #1a1a1a; }"
            "QPushButton:hover { background: #dce6f0; }"
            "QPushButton:checked { background: #4a9977; color: white; border-color: #3a8866; }"
        )
        self._clean_btn.toggled.connect(self.clean_view_toggled.emit)
        header.addWidget(self._clean_btn)

        apply_btn = QPushButton("\u2713")
        apply_btn.setToolTip("Apply Changes")
        apply_btn.setFixedSize(icon_size, icon_size)
        apply_btn.setStyleSheet(
            "QPushButton { font-size: 16px; padding: 2px; border: 1px solid #4a9; "
            "border-radius: 4px; background: #e6f5ec; color: #1a1a1a; font-weight: bold; }"
            "QPushButton:hover { background: #c8ebd5; }"
        )
        apply_btn.clicked.connect(self.apply_requested.emit)
        header.addWidget(apply_btn)
        layout.addLayout(header)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Courier New", 13))
        self.editor.setStyleSheet(
            "QPlainTextEdit { background: #1e1e2e; color: #cdd6f4; "
            "border: 1px solid #45475a; border-radius: 6px; padding: 8px; }"
        )
        self.editor.textChanged.connect(self.content_changed.emit)
        layout.addWidget(self.editor, 1)

    def insert_snippet(self, text: str):
        """Insert a text snippet at the current cursor position."""
        cursor = self.editor.textCursor()
        cursor.insertText("\n" + text + "\n")
        self.editor.setTextCursor(cursor)

    def get_text(self) -> str:
        return self.editor.toPlainText()

    def set_text(self, text: str):
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
