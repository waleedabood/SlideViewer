"""Side-panel widgets: StylePanel, SlideNavigator, and FullMarkdownPanel."""

import re
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .constants import FONT_OPTIONS, PRESET_THEMES
from .models import StyleSettings


class StylePanel(QWidget):
    """Right dock panel: theme customization controls."""

    style_changed = pyqtSignal()

    def __init__(self, style: StyleSettings, parent=None):
        super().__init__(parent)
        self.style = style
        self._color_buttons: dict[str, QPushButton] = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        title = QLabel("Slide Theme")
        title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px 0;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        color_fields = [
            ("Background Color", "bg_color"),
            ("Text Color", "text_color"),
            ("Heading Color", "heading_color"),
            ("Accent Color", "accent_color"),
        ]
        for label_text, attr in color_fields:
            btn = QPushButton()
            btn.setFixedSize(100, 28)
            self._update_color_btn(btn, getattr(self.style, attr))
            btn.clicked.connect(lambda checked, a=attr, b=btn: self._pick_color(a, b))
            self._color_buttons[attr] = btn
            form.addRow(label_text, btn)

        self.font_combo = QComboBox()
        self.font_combo.addItems(FONT_OPTIONS)
        self.font_combo.setCurrentText(self.style.font_family)
        self.font_combo.currentTextChanged.connect(self._on_font_changed)
        form.addRow("Font Family", self.font_combo)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(10, 48)
        self.size_spin.setValue(self.style.font_size)
        self.size_spin.valueChanged.connect(self._on_size_changed)
        form.addRow("Font Size", self.size_spin)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESET_THEMES.keys())
        self.preset_combo.currentTextChanged.connect(self._apply_preset)
        form.addRow("Preset Theme", self.preset_combo)

        layout.addLayout(form)

        bg_group = QGroupBox("Background")
        bg_layout = QFormLayout(bg_group)
        bg_layout.setSpacing(8)

        self.bg_type_combo = QComboBox()
        self.bg_type_combo.addItems(["solid", "gradient", "image"])
        self.bg_type_combo.setCurrentText(self.style.bg_type)
        self.bg_type_combo.currentTextChanged.connect(self._on_bg_type_changed)
        bg_layout.addRow("Type", self.bg_type_combo)

        self._grad_row = QWidget()
        grad_h = QHBoxLayout(self._grad_row)
        grad_h.setContentsMargins(0, 0, 0, 0)
        grad_h.setSpacing(4)
        self._grad_color1 = QPushButton("#ffffff")
        self._grad_color1.setFixedSize(60, 26)
        self._grad_color1.setStyleSheet("background: #ffffff; border: 1px solid #999; border-radius: 3px;")
        self._grad_color1.clicked.connect(lambda: self._pick_grad_color(1))
        self._grad_color2 = QPushButton("#0f3460")
        self._grad_color2.setFixedSize(60, 26)
        self._grad_color2.setStyleSheet("background: #0f3460; border: 1px solid #999; border-radius: 3px;")
        self._grad_color2.clicked.connect(lambda: self._pick_grad_color(2))
        self._grad_dir = QComboBox()
        self._grad_dir.addItems(["to right", "to left", "to bottom", "to top",
                                  "to bottom right", "to top left"])
        self._grad_dir.currentTextChanged.connect(self._update_gradient)
        grad_h.addWidget(self._grad_color1)
        grad_h.addWidget(self._grad_color2)
        grad_h.addWidget(self._grad_dir, 1)
        bg_layout.addRow("Gradient", self._grad_row)

        self._img_row = QWidget()
        img_h = QHBoxLayout(self._img_row)
        img_h.setContentsMargins(0, 0, 0, 0)
        self._img_path_label = QLabel("None")
        self._img_path_label.setStyleSheet("color: #888;")
        img_h.addWidget(self._img_path_label, 1)
        img_browse = QPushButton("Browse")
        img_browse.clicked.connect(self._browse_bg_image)
        img_h.addWidget(img_browse)
        bg_layout.addRow("Image", self._img_row)

        layout.addWidget(bg_group)
        self._on_bg_type_changed(self.style.bg_type)

        trans_group = QGroupBox("Transitions")
        trans_layout = QFormLayout(trans_group)
        self.transition_combo = QComboBox()
        self.transition_combo.addItems(["none", "fade", "slide-left", "slide-right", "zoom"])
        self.transition_combo.setCurrentText(self.style.transition)
        self.transition_combo.currentTextChanged.connect(self._on_transition_changed)
        trans_layout.addRow("Effect", self.transition_combo)
        layout.addWidget(trans_group)

        layout.addStretch()

    @staticmethod
    def _update_color_btn(btn: QPushButton, color: str):
        btn.setStyleSheet(
            f"background-color: {color}; border: 1px solid #999; border-radius: 4px;"
        )
        btn.setText(color)

    def _pick_color(self, attr: str, btn: QPushButton):
        current = QColor(getattr(self.style, attr))
        color = QColorDialog.getColor(current, self, "Pick Color")
        if color.isValid():
            hex_color = color.name()
            setattr(self.style, attr, hex_color)
            self._update_color_btn(btn, hex_color)
            self.style_changed.emit()

    def _on_font_changed(self, font: str):
        self.style.font_family = font
        self.style_changed.emit()

    def _on_size_changed(self, size: int):
        self.style.font_size = size
        self.style_changed.emit()

    def _apply_preset(self, name: str):
        theme = PRESET_THEMES.get(name)
        if not theme:
            return
        for attr, value in theme.items():
            setattr(self.style, attr, value)
            if attr in self._color_buttons:
                self._update_color_btn(self._color_buttons[attr], value)
        self.style_changed.emit()

    def _on_bg_type_changed(self, bg_type: str):
        self.style.bg_type = bg_type
        self._grad_row.setVisible(bg_type == "gradient")
        self._img_row.setVisible(bg_type == "image")
        if bg_type == "solid":
            self.style.bg_value = ""
        self.style_changed.emit()

    def _pick_grad_color(self, which: int):
        btn = self._grad_color1 if which == 1 else self._grad_color2
        color = QColorDialog.getColor(QColor(btn.text()), self, "Gradient Color")
        if color.isValid():
            btn.setText(color.name())
            btn.setStyleSheet(
                f"background: {color.name()}; border: 1px solid #999; border-radius: 3px;"
            )
            self._update_gradient()

    def _update_gradient(self):
        c1 = self._grad_color1.text()
        c2 = self._grad_color2.text()
        direction = self._grad_dir.currentText()
        self.style.bg_type = "gradient"
        self.style.bg_value = f"linear-gradient({direction}, {c1}, {c2})"
        self.style_changed.emit()

    def _browse_bg_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.svg);;All Files (*)",
        )
        if path:
            name = Path(path).name
            self._img_path_label.setText(name)
            self._img_path_label.setStyleSheet("")
            self.style.bg_type = "image"
            self.style.bg_value = f"url({path}) center/cover no-repeat"
            self.style_changed.emit()

    def _on_transition_changed(self, transition: str):
        self.style.transition = transition
        self.style_changed.emit()


class SlideNavigator(QWidget):
    """Clickable list of all slides for quick navigation."""

    slide_selected = pyqtSignal(int)

    _OVERFLOW_COLOR = QColor("#e67e22")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._overflow_marks: dict[int, bool] = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(4)

        sep = QLabel("Slide Navigator")
        sep.setStyleSheet(
            "font-weight: bold; font-size: 14px; padding: 4px 10px;"
        )
        layout.addWidget(sep)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { border: 1px solid #ccc; border-radius: 4px; }"
            "QListWidget::item { padding: 6px 10px; }"
            "QListWidget::item:selected { background: #0f3460; color: white; }"
            "QListWidget::item:hover { background: #d0dff0; }"
        )
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self.list_widget, 1)

    def update_slides(self, slides: list[str], current_index: int):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for i, slide_md in enumerate(slides):
            first_line = slide_md.strip().split("\n")[0]
            title = re.sub(r"^#+\s*", "", first_line).strip() or "(empty slide)"
            overflows = self._overflow_marks.get(i, False)
            prefix = "\u26a0 " if overflows else "  "
            item = QListWidgetItem(f"{prefix}{i + 1}.  {title}")
            item.setData(Qt.ItemDataRole.UserRole, title)
            if overflows:
                item.setForeground(self._OVERFLOW_COLOR)
            self.list_widget.addItem(item)
        if 0 <= current_index < self.list_widget.count():
            self.list_widget.setCurrentRow(current_index)
        self.list_widget.blockSignals(False)

    def mark_overflow(self, index: int, overflows: bool):
        self._overflow_marks[index] = overflows
        if 0 <= index < self.list_widget.count():
            item = self.list_widget.item(index)
            title = item.data(Qt.ItemDataRole.UserRole) or ""
            prefix = "\u26a0 " if overflows else "  "
            item.setText(f"{prefix}{index + 1}.  {title}")
            if overflows:
                item.setForeground(self._OVERFLOW_COLOR)
            else:
                item.setData(Qt.ItemDataRole.ForegroundRole, None)

    def clear_overflow_marks(self):
        self._overflow_marks.clear()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            title = item.data(Qt.ItemDataRole.UserRole) or ""
            item.setText(f"  {i + 1}.  {title}")
            item.setData(Qt.ItemDataRole.ForegroundRole, None)

    def _on_row_changed(self, row: int):
        if row >= 0:
            self.slide_selected.emit(row)


class FullMarkdownPanel(QWidget):
    """Right dock panel: editable view of the complete presentation markdown."""

    content_edited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(3)

        btn_style = (
            "QPushButton { font-size: 14px; padding: 2px 8px; border: 1px solid #bbb; "
            "border-radius: 4px; background: #f0f0f0; color: #1a1a1a; }"
            "QPushButton:hover { background: #dce6f0; }"
            "QPushButton:disabled { color: #aaa; background: #e8e8e8; }"
        )

        undo_btn = QPushButton("\u21b6 Undo")
        undo_btn.setToolTip("Undo (Ctrl+Z)")
        undo_btn.setStyleSheet(btn_style)
        undo_btn.clicked.connect(self._undo)
        header.addWidget(undo_btn)

        redo_btn = QPushButton("\u21b7 Redo")
        redo_btn.setToolTip("Redo (Ctrl+Shift+Z)")
        redo_btn.setStyleSheet(btn_style)
        redo_btn.clicked.connect(self._redo)
        header.addWidget(redo_btn)

        header.addStretch()

        self._find_btn = QPushButton("\U0001f50d Find")
        self._find_btn.setToolTip("Find text (Ctrl+F)")
        self._find_btn.setStyleSheet(btn_style)
        self._find_btn.clicked.connect(self._toggle_find_bar)
        header.addWidget(self._find_btn)

        layout.addLayout(header)

        self._find_bar = QWidget()
        self._find_bar.setVisible(False)
        find_layout = QHBoxLayout(self._find_bar)
        find_layout.setContentsMargins(0, 0, 0, 0)
        find_layout.setSpacing(4)

        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText("Search...")
        self._find_input.setStyleSheet(
            "QLineEdit { padding: 4px; border: 1px solid #888; border-radius: 4px; }"
        )
        self._find_input.returnPressed.connect(self._find_next)
        find_layout.addWidget(self._find_input, 1)

        find_prev_btn = QPushButton("\u25b2")
        find_prev_btn.setToolTip("Find Previous")
        find_prev_btn.setFixedWidth(28)
        find_prev_btn.setStyleSheet(btn_style)
        find_prev_btn.clicked.connect(self._find_prev)
        find_layout.addWidget(find_prev_btn)

        find_next_btn = QPushButton("\u25bc")
        find_next_btn.setToolTip("Find Next")
        find_next_btn.setFixedWidth(28)
        find_next_btn.setStyleSheet(btn_style)
        find_next_btn.clicked.connect(self._find_next)
        find_layout.addWidget(find_next_btn)

        close_find_btn = QPushButton("\u2715")
        close_find_btn.setToolTip("Close Find")
        close_find_btn.setFixedWidth(28)
        close_find_btn.setStyleSheet(btn_style)
        close_find_btn.clicked.connect(self._close_find_bar)
        find_layout.addWidget(close_find_btn)

        self._find_status = QLabel("")
        self._find_status.setStyleSheet("color: #888; font-size: 11px; padding: 0 4px;")
        find_layout.addWidget(self._find_status)

        layout.addWidget(self._find_bar)

        self.text_view = QPlainTextEdit()
        self.text_view.setFont(QFont("Courier New", 12))
        self.text_view.setStyleSheet(
            "QPlainTextEdit { background: #1e1e2e; color: #cdd6f4; "
            "border: 1px solid #45475a; border-radius: 6px; padding: 8px; }"
        )
        self.text_view.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_view, 1)

    def _on_text_changed(self):
        if not self._updating:
            self.content_edited.emit()

    def get_text(self) -> str:
        return self.text_view.toPlainText()

    def _undo(self):
        self.text_view.undo()

    def _redo(self):
        self.text_view.redo()

    def _toggle_find_bar(self):
        visible = not self._find_bar.isVisible()
        self._find_bar.setVisible(visible)
        if visible:
            self._find_input.setFocus()
            self._find_input.selectAll()
        else:
            self._clear_find_highlights()

    def _close_find_bar(self):
        self._find_bar.setVisible(False)
        self._find_status.setText("")
        self._clear_find_highlights()

    def _find_next(self):
        self._do_find(backward=False)

    def _find_prev(self):
        self._do_find(backward=True)

    def _do_find(self, backward=False):
        query = self._find_input.text()
        if not query:
            self._find_status.setText("")
            return

        text = self.text_view.toPlainText()
        cursor = self.text_view.textCursor()
        start = cursor.position()

        if backward:
            idx = text.rfind(query, 0, start)
            if idx < 0:
                idx = text.rfind(query)
        else:
            idx = text.find(query, start)
            if idx < 0:
                idx = text.find(query)

        if idx >= 0:
            cursor = self.text_view.textCursor()
            cursor.setPosition(idx)
            cursor.setPosition(idx + len(query), cursor.MoveMode.KeepAnchor)
            self.text_view.setTextCursor(cursor)
            self.text_view.centerCursor()
            count = text.lower().count(query.lower())
            self._find_status.setText(f"{count} match(es)")
        else:
            self._find_status.setText("Not found")

    def _clear_find_highlights(self):
        cursor = self.text_view.textCursor()
        cursor.clearSelection()
        self.text_view.setTextCursor(cursor)

    def update_content(self, full_markdown: str):
        self._updating = True
        scroll_bar = self.text_view.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        cursor = self.text_view.textCursor()
        cursor_pos = cursor.position()
        self.text_view.setPlainText(full_markdown)
        scroll_bar.setValue(scroll_pos)
        cursor = self.text_view.textCursor()
        cursor.setPosition(min(cursor_pos, len(full_markdown)))
        self.text_view.setTextCursor(cursor)
        self._updating = False
