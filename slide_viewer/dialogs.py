"""Dialog windows: LoadCode, ImageEditor, ColumnsEditor, and TableEditor."""

import re
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class LoadCodeDialog(QDialog):
    """Dialog for pasting markdown directly."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load from Code")
        self.resize(700, 500)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paste your markdown below:"))

        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont("Courier New", 12))
        layout.addWidget(self.text_edit, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)


# ---------------------------------------------------------------------------
# Image-related regex helpers
# ---------------------------------------------------------------------------

_COLS_DIV_RE = re.compile(
    r'<div\s+class="layout-cols"[^>]*>\s*'
    r'((?:<div\s+class="col"[^>]*>[\s\S]*?</div>\s*)+)'
    r'</div>',
    re.DOTALL,
)

_SINGLE_COL_RE = re.compile(
    r'<div\s+class="col"[^>]*>\s*([\s\S]*?)\s*</div>',
    re.DOTALL,
)

_IMAGE_DIV_RE = re.compile(
    r'<div class="(layout-img-\w+)"(?: style="([^"]*)")?>\s*\n'
    r'<img src="([^"]+)">\s*(?:\n<p>([^<]*)</p>)?\s*\n</div>',
    re.DOTALL,
)

_INLINE_IMG_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

_INLINE_IMG_TAG_RE = re.compile(
    r'<img src="([^"]+)"(?: alt="([^"]*)")?(?: style="([^"]*)")?>'
)


def _parse_style(style_str: str | None) -> dict[str, int]:
    """Extract width / left / margin-top percentages from a style string."""
    vals: dict[str, int] = {}
    if not style_str:
        return vals
    for prop in ("width", "margin-top"):
        m = re.search(rf"{re.escape(prop)}:\s*(-?\d+)%", style_str)
        if m:
            vals[prop] = int(m.group(1))
    m = re.search(r"(?<!margin-)left:\s*(-?\d+)%", style_str)
    if m:
        vals["left"] = int(m.group(1))
    return vals


DEFAULT_WIDTHS = {
    "layout-img-right": 48,
    "layout-img-left": 48,
    "layout-img-full": 100,
    "inline": 50,
}


def build_image_snippet(
    src: str,
    css_class: str,
    caption: str,
    width: int | None = None,
    left: int | None = None,
    margin_top: int | None = None,
) -> str:
    """Build an image HTML snippet from layout class and position values."""
    default_w = DEFAULT_WIDTHS.get(css_class, 48)
    parts: list[str] = []
    if width is not None and width != default_w:
        parts.append(f"width: {width}%;")
    if left is not None and left != 0:
        parts.append(f"position: relative; left: {left}%;")
    if margin_top is not None and margin_top != 0:
        parts.append(f"margin-top: {margin_top}%;")
    style = " ".join(parts)
    style_attr = f' style="{style}"' if style else ""

    if css_class == "inline":
        alt = caption or "image"
        if style:
            return f'<img src="{src}" alt="{alt}" style="{style}">'
        return f"![{alt}]({src})"

    cap_html = f"\n<p>{caption}</p>" if caption else ""
    return f'<div class="{css_class}"{style_attr}>\n<img src="{src}">{cap_html}\n</div>'


class ImageEditorDialog(QDialog):
    """Dialog for inserting or editing an image with layout, size, and position controls."""

    LAYOUTS = [
        ("Right half (image right, text left)", "layout-img-right"),
        ("Left half (image left, text right)", "layout-img-left"),
        ("Full with caption", "layout-img-full"),
        ("Inline (centered)", "inline"),
    ]

    snippet_changed = pyqtSignal(str, str)

    def __init__(self, parent=None, *, edit_src: str | None = None,
                 edit_class: str | None = None, edit_caption: str = "",
                 edit_style: dict[str, int] | None = None,
                 preset_path: str | None = None):
        super().__init__(parent)
        self._edit_mode = edit_src is not None
        self._image_path: str | None = None
        self._src = edit_src or ""
        self._old_snippet: str | None = None

        self.setWindowTitle("Edit Image" if self._edit_mode else "Insert Image")
        self.setMinimumWidth(500)

        root = QVBoxLayout(self)

        if not self._edit_mode:
            file_group = QGroupBox("Image File")
            file_layout = QHBoxLayout(file_group)
            self._path_label = QLabel("No file selected")
            self._path_label.setStyleSheet("color: #888;")
            file_layout.addWidget(self._path_label, 1)
            browse_btn = QPushButton("Browse…")
            browse_btn.clicked.connect(self._browse)
            file_layout.addWidget(browse_btn)
            root.addWidget(file_group)

            self._preview = QLabel()
            self._preview.setFixedHeight(160)
            self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._preview.setStyleSheet(
                "background: #f0f0f0; border: 1px solid #ccc; border-radius: 4px;"
            )
            root.addWidget(self._preview)

            if preset_path:
                self._image_path = preset_path
                self._path_label.setText(Path(preset_path).name)
                self._path_label.setStyleSheet("")
                pix = QPixmap(preset_path)
                if not pix.isNull():
                    self._preview.setPixmap(
                        pix.scaled(
                            self._preview.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
        else:
            src_label = QLabel(f"Image: {edit_src}")
            src_label.setStyleSheet("font-weight: bold; padding: 4px;")
            root.addWidget(src_label)

        form = QFormLayout()

        self._layout_combo = QComboBox()
        for label, _ in self.LAYOUTS:
            self._layout_combo.addItem(label)
        if edit_class:
            for i, (_, cls) in enumerate(self.LAYOUTS):
                if cls == edit_class:
                    self._layout_combo.setCurrentIndex(i)
                    break
        form.addRow("Layout:", self._layout_combo)

        init_class = edit_class or self.LAYOUTS[0][1]
        init_style = edit_style or {}

        self._width_spin = QSpinBox()
        self._width_spin.setRange(10, 100)
        self._width_spin.setSuffix(" %")
        self._width_spin.setValue(init_style.get("width", DEFAULT_WIDTHS.get(init_class, 48)))
        form.addRow("Width:", self._width_spin)

        self._hoffset_spin = QSpinBox()
        self._hoffset_spin.setRange(-50, 50)
        self._hoffset_spin.setSuffix(" %")
        self._hoffset_spin.setValue(init_style.get("left", 0))
        form.addRow("H-Offset (\u2190\u2192):", self._hoffset_spin)

        self._voffset_spin = QSpinBox()
        self._voffset_spin.setRange(-50, 50)
        self._voffset_spin.setSuffix(" %")
        self._voffset_spin.setValue(init_style.get("margin-top", 0))
        form.addRow("V-Offset (\u2191\u2193):", self._voffset_spin)

        self._caption_edit = QLineEdit()
        self._caption_edit.setPlaceholderText("Optional caption…")
        self._caption_edit.setText(edit_caption)
        form.addRow("Caption:", self._caption_edit)

        root.addLayout(form)

        self._layout_combo.currentIndexChanged.connect(self._on_layout_changed)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        if self._edit_mode:
            self._width_spin.valueChanged.connect(self._emit_live)
            self._hoffset_spin.valueChanged.connect(self._emit_live)
            self._voffset_spin.valueChanged.connect(self._emit_live)
            self._layout_combo.currentIndexChanged.connect(self._emit_live)
            self._caption_edit.textChanged.connect(self._emit_live)

    def _on_layout_changed(self, index: int):
        _, css_class = self.LAYOUTS[index]
        self._width_spin.setValue(DEFAULT_WIDTHS.get(css_class, 48))

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp *.svg);;All Files (*)",
        )
        if path:
            self._image_path = path
            name = Path(path).name
            self._path_label.setText(name)
            self._path_label.setStyleSheet("")
            pix = QPixmap(path)
            if not pix.isNull():
                self._preview.setPixmap(
                    pix.scaled(
                        self._preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

    def _validate_and_accept(self):
        if not self._edit_mode and not self._image_path:
            QMessageBox.warning(self, "No image", "Please select an image file first.")
            return
        self.accept()

    def _emit_live(self):
        if self._edit_mode and self._src:
            new = self.snippet(self._src)
            self.snippet_changed.emit(self._src, new)

    @property
    def image_path(self) -> str | None:
        return self._image_path

    @property
    def layout_class(self) -> str:
        _, css_class = self.LAYOUTS[self._layout_combo.currentIndex()]
        return css_class

    @property
    def caption(self) -> str:
        return self._caption_edit.text().strip()

    def _build_style(self) -> str:
        """Build the inline style string from current spinbox values."""
        _, css_class = self.LAYOUTS[self._layout_combo.currentIndex()]
        default_w = DEFAULT_WIDTHS.get(css_class, 48)
        parts: list[str] = []
        w = self._width_spin.value()
        if w != default_w:
            parts.append(f"width: {w}%;")
        h = self._hoffset_spin.value()
        if h != 0:
            parts.append(f"position: relative; left: {h}%;")
        v = self._voffset_spin.value()
        if v != 0:
            parts.append(f"margin-top: {v}%;")
        return " ".join(parts)

    def snippet(self, src: str) -> str:
        """Return the HTML snippet using the given image src path."""
        return build_image_snippet(
            src=src,
            css_class=self.layout_class,
            caption=self.caption,
            width=self._width_spin.value(),
            left=self._hoffset_spin.value(),
            margin_top=self._voffset_spin.value(),
        )


# ---------------------------------------------------------------------------
# Columns Editor Dialog
# ---------------------------------------------------------------------------

_COL_RATIO_PRESETS: dict[int, list[tuple[str, list[int]]]] = {
    2: [
        ("Equal (1:1)", [1, 1]),
        ("Wider left (2:1)", [2, 1]),
        ("Wider right (1:2)", [1, 2]),
        ("Wide left (3:1)", [3, 1]),
        ("Wide right (1:3)", [1, 3]),
    ],
    3: [
        ("Equal (1:1:1)", [1, 1, 1]),
        ("Wide center (1:2:1)", [1, 2, 1]),
        ("Wide left (2:1:1)", [2, 1, 1]),
        ("Wide right (1:1:2)", [1, 1, 2]),
    ],
    4: [
        ("Equal (1:1:1:1)", [1, 1, 1, 1]),
    ],
}

_GAP_OPTIONS = [
    ("Small (1em)", "1em"),
    ("Medium (2em)", "2em"),
    ("Large (3em)", "3em"),
]


class ColumnsEditorDialog(QDialog):
    """Dialog for inserting or editing a multi-column layout."""

    def __init__(self, parent=None, *, column_contents: list[str] | None = None,
                 ratios: list[int] | None = None, gap: str = "2em"):
        super().__init__(parent)
        self._edit_mode = column_contents is not None
        self.setWindowTitle("Edit Column Layout" if self._edit_mode else "Insert Column Layout")
        self.setMinimumSize(650, 480)
        self.resize(720, 520)

        root = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(10)

        self._col_count_spin = QSpinBox()
        self._col_count_spin.setRange(2, 4)
        init_count = len(column_contents) if column_contents else 2
        self._col_count_spin.setValue(init_count)
        self._col_count_spin.valueChanged.connect(self._on_col_count_changed)
        form.addRow("Number of columns:", self._col_count_spin)

        self._ratio_combo = QComboBox()
        form.addRow("Column ratio:", self._ratio_combo)

        self._gap_combo = QComboBox()
        for label, _ in _GAP_OPTIONS:
            self._gap_combo.addItem(label)
        for i, (_, val) in enumerate(_GAP_OPTIONS):
            if val == gap:
                self._gap_combo.setCurrentIndex(i)
                break
        form.addRow("Gap size:", self._gap_combo)

        root.addLayout(form)

        cols_label = QLabel("Column Contents (markdown):")
        cols_label.setStyleSheet("font-weight: bold; padding-top: 6px;")
        root.addWidget(cols_label)

        self._editors_container = QWidget()
        self._editors_layout = QHBoxLayout(self._editors_container)
        self._editors_layout.setContentsMargins(0, 0, 0, 0)
        self._editors_layout.setSpacing(6)
        self._col_editors: list[QPlainTextEdit] = []
        root.addWidget(self._editors_container, 1)

        action_row = QHBoxLayout()
        action_row.addStretch()
        ok_btn = QPushButton("Update Layout" if self._edit_mode else "Insert Layout")
        ok_btn.setStyleSheet("font-weight: bold; padding: 6px 20px;")
        ok_btn.clicked.connect(self.accept)
        action_row.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        action_row.addWidget(cancel_btn)
        root.addLayout(action_row)

        self._populate_ratio_combo(init_count)
        if ratios:
            self._select_matching_ratio(ratios)
        self._rebuild_editors(init_count, column_contents)

    def _populate_ratio_combo(self, count: int):
        self._ratio_combo.blockSignals(True)
        self._ratio_combo.clear()
        for label, _ in _COL_RATIO_PRESETS.get(count, []):
            self._ratio_combo.addItem(label)
        self._ratio_combo.blockSignals(False)

    def _select_matching_ratio(self, ratios: list[int]):
        count = len(ratios)
        for i, (_, preset_ratios) in enumerate(_COL_RATIO_PRESETS.get(count, [])):
            if preset_ratios == ratios:
                self._ratio_combo.setCurrentIndex(i)
                return

    def _rebuild_editors(self, count: int, contents: list[str] | None = None):
        old_texts = [e.toPlainText() for e in self._col_editors]

        for editor in self._col_editors:
            self._editors_layout.removeWidget(editor)
            editor.deleteLater()
        self._col_editors.clear()

        editor_style = (
            "QPlainTextEdit { background: #1e1e2e; color: #cdd6f4; "
            "border: 1px solid #45475a; border-radius: 6px; padding: 6px; }"
        )

        for i in range(count):
            editor = QPlainTextEdit()
            editor.setFont(QFont("Courier New", 12))
            editor.setStyleSheet(editor_style)
            if contents and i < len(contents):
                editor.setPlainText(contents[i])
            elif i < len(old_texts):
                editor.setPlainText(old_texts[i])
            else:
                editor.setPlainText(f"**Column {i + 1}**\n\nContent here...")
            self._editors_layout.addWidget(editor)
            self._col_editors.append(editor)

    def _on_col_count_changed(self, count: int):
        self._populate_ratio_combo(count)
        self._rebuild_editors(count)

    @property
    def selected_gap(self) -> str:
        idx = self._gap_combo.currentIndex()
        if 0 <= idx < len(_GAP_OPTIONS):
            return _GAP_OPTIONS[idx][1]
        return "2em"

    @property
    def selected_ratios(self) -> list[int]:
        count = self._col_count_spin.value()
        idx = self._ratio_combo.currentIndex()
        presets = _COL_RATIO_PRESETS.get(count, [])
        if 0 <= idx < len(presets):
            return presets[idx][1]
        return [1] * count

    def to_snippet(self) -> str:
        gap = self.selected_gap
        ratios = self.selected_ratios
        is_equal = len(set(ratios)) == 1

        parts: list[str] = []
        parts.append(f'<div class="layout-cols" style="gap: {gap};">')

        for i, editor in enumerate(self._col_editors):
            content = editor.toPlainText().strip() or f"**Column {i + 1}**"
            ratio = ratios[i] if i < len(ratios) else 1
            if is_equal:
                parts.append('<div class="col" markdown="1">')
            else:
                parts.append(f'<div class="col" style="flex: {ratio};" markdown="1">')
            parts.append("")
            parts.append(content)
            parts.append("")
            parts.append("</div>")

        parts.append("</div>")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Table Editor Dialog
# ---------------------------------------------------------------------------

_MD_TABLE_RE = re.compile(
    r"^(\|[^\n]+\|\n)"
    r"(\|[\s:|-]+\|\n)"
    r"((?:\|[^\n]+\|\n?)*)",
    re.MULTILINE,
)

_MD_TABLE_DIV_RE = re.compile(
    r'<div\s+class="(layout-table-(?:right|left))"'
    r'(?:\s+style="width:\s*(\d+)%;")?'
    r'\s+markdown="1">\s*\n'
    r"((?:\|[^\n]+\|\n)"
    r"(?:\|[\s:|-]+\|\n)"
    r"(?:(?:\|[^\n]+\|\n?)*))"
    r"\s*</div>",
    re.MULTILINE,
)


class TableEditorDialog(QDialog):
    """Excel-like table editor that produces/consumes markdown tables."""

    TABLE_LAYOUTS = [
        ("Full width", ""),
        ("Float right", "layout-table-right"),
        ("Float left", "layout-table-left"),
    ]

    def __init__(self, parent=None, *, markdown_table: str | None = None,
                 layout_class: str = "", layout_width: int | None = None):
        super().__init__(parent)
        self._edit_mode = markdown_table is not None
        self.setWindowTitle("Edit Table" if self._edit_mode else "Insert Table")
        self.setMinimumSize(600, 400)
        self.resize(700, 450)

        root = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        add_row_btn = QPushButton("+ Row")
        add_row_btn.clicked.connect(self._add_row)
        btn_bar.addWidget(add_row_btn)

        del_row_btn = QPushButton("\u2212 Row")
        del_row_btn.clicked.connect(self._remove_row)
        btn_bar.addWidget(del_row_btn)

        add_col_btn = QPushButton("+ Column")
        add_col_btn.clicked.connect(self._add_column)
        btn_bar.addWidget(add_col_btn)

        del_col_btn = QPushButton("\u2212 Column")
        del_col_btn.clicked.connect(self._remove_column)
        btn_bar.addWidget(del_col_btn)

        btn_bar.addStretch()

        move_up_btn = QPushButton("\u2191")
        move_up_btn.setToolTip("Move row up")
        move_up_btn.setFixedWidth(32)
        move_up_btn.clicked.connect(self._move_row_up)
        btn_bar.addWidget(move_up_btn)

        move_down_btn = QPushButton("\u2193")
        move_down_btn.setToolTip("Move row down")
        move_down_btn.setFixedWidth(32)
        move_down_btn.clicked.connect(self._move_row_down)
        btn_bar.addWidget(move_down_btn)

        move_left_btn = QPushButton("\u2190")
        move_left_btn.setToolTip("Move column left")
        move_left_btn.setFixedWidth(32)
        move_left_btn.clicked.connect(self._move_col_left)
        btn_bar.addWidget(move_left_btn)

        move_right_btn = QPushButton("\u2192")
        move_right_btn.setToolTip("Move column right")
        move_right_btn.setFixedWidth(32)
        move_right_btn.clicked.connect(self._move_col_right)
        btn_bar.addWidget(move_right_btn)

        root.addLayout(btn_bar)

        self.table = QTableWidget()
        self.table.setStyleSheet(
            "QTableWidget { gridline-color: #bbb; font-size: 13px; }"
            "QHeaderView::section { background: #e8e8e8; padding: 4px 8px; "
            "border: 1px solid #ccc; font-weight: bold; }"
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        root.addWidget(self.table, 1)

        layout_row = QHBoxLayout()
        layout_row.addWidget(QLabel("Position:"))
        self._layout_combo = QComboBox()
        for label, _ in self.TABLE_LAYOUTS:
            self._layout_combo.addItem(label)
        if layout_class:
            for i, (_, cls) in enumerate(self.TABLE_LAYOUTS):
                if cls == layout_class:
                    self._layout_combo.setCurrentIndex(i)
                    break
        self._layout_combo.currentIndexChanged.connect(self._on_layout_changed)
        layout_row.addWidget(self._layout_combo)

        layout_row.addWidget(QLabel("Width:"))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(10, 100)
        self._width_spin.setSuffix(" %")
        self._width_spin.setValue(layout_width if layout_width is not None else 48)
        layout_row.addWidget(self._width_spin)
        layout_row.addStretch()
        root.addLayout(layout_row)

        is_full = (self._layout_combo.currentIndex() == 0)
        self._width_spin.setVisible(not is_full)

        action_row = QHBoxLayout()
        action_row.addStretch()
        insert_btn = QPushButton("Update Table" if self._edit_mode else "Insert Table")
        insert_btn.setStyleSheet("font-weight: bold; padding: 6px 20px;")
        insert_btn.clicked.connect(self.accept)
        action_row.addWidget(insert_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        action_row.addWidget(cancel_btn)
        root.addLayout(action_row)

        if markdown_table:
            self._load_from_markdown(markdown_table)
        else:
            self._init_default()

    def _on_layout_changed(self, index: int):
        self._width_spin.setVisible(index != 0)

    @property
    def selected_layout_class(self) -> str:
        _, cls = self.TABLE_LAYOUTS[self._layout_combo.currentIndex()]
        return cls

    @property
    def selected_width(self) -> int:
        return self._width_spin.value()

    def _init_default(self):
        self.table.setRowCount(3)
        self.table.setColumnCount(3)
        self._update_headers()

    def _update_headers(self):
        for c in range(self.table.columnCount()):
            self.table.setHorizontalHeaderItem(c, QTableWidgetItem(f"Col {c + 1}"))

    def _add_row(self):
        self.table.insertRow(self.table.rowCount())

    def _remove_row(self):
        row = self.table.currentRow()
        if row < 0:
            row = self.table.rowCount() - 1
        if self.table.rowCount() > 1:
            self.table.removeRow(row)

    def _add_column(self):
        col = self.table.columnCount()
        self.table.insertColumn(col)
        self.table.setHorizontalHeaderItem(col, QTableWidgetItem(f"Col {col + 1}"))

    def _remove_column(self):
        col = self.table.currentColumn()
        if col < 0:
            col = self.table.columnCount() - 1
        if self.table.columnCount() > 1:
            self.table.removeColumn(col)
            self._update_headers()

    def _swap_rows(self, r1: int, r2: int):
        cols = self.table.columnCount()
        for c in range(cols):
            item1 = self.table.takeItem(r1, c)
            item2 = self.table.takeItem(r2, c)
            self.table.setItem(r1, c, item2 if item2 else QTableWidgetItem(""))
            self.table.setItem(r2, c, item1 if item1 else QTableWidgetItem(""))
        self.table.setCurrentCell(r2, self.table.currentColumn())

    def _swap_cols(self, c1: int, c2: int):
        rows = self.table.rowCount()
        for r in range(rows):
            item1 = self.table.takeItem(r, c1)
            item2 = self.table.takeItem(r, c2)
            self.table.setItem(r, c1, item2 if item2 else QTableWidgetItem(""))
            self.table.setItem(r, c2, item1 if item1 else QTableWidgetItem(""))
        h1 = self.table.horizontalHeaderItem(c1)
        h2 = self.table.horizontalHeaderItem(c2)
        t1 = h1.text() if h1 else ""
        t2 = h2.text() if h2 else ""
        self.table.setHorizontalHeaderItem(c1, QTableWidgetItem(t2))
        self.table.setHorizontalHeaderItem(c2, QTableWidgetItem(t1))
        self.table.setCurrentCell(self.table.currentRow(), c2)

    def _move_row_up(self):
        row = self.table.currentRow()
        if row > 0:
            self._swap_rows(row, row - 1)

    def _move_row_down(self):
        row = self.table.currentRow()
        if 0 <= row < self.table.rowCount() - 1:
            self._swap_rows(row, row + 1)

    def _move_col_left(self):
        col = self.table.currentColumn()
        if col > 0:
            self._swap_cols(col, col - 1)

    def _move_col_right(self):
        col = self.table.currentColumn()
        if 0 <= col < self.table.columnCount() - 1:
            self._swap_cols(col, col + 1)

    def _load_from_markdown(self, md: str):
        lines = [ln.strip() for ln in md.strip().splitlines() if ln.strip()]
        if len(lines) < 2:
            self._init_default()
            return

        def split_row(line: str) -> list[str]:
            line = line.strip()
            if line.startswith("|"):
                line = line[1:]
            if line.endswith("|"):
                line = line[:-1]
            return [cell.strip() for cell in line.split("|")]

        header_cells = split_row(lines[0])
        separator_idx = 1
        data_lines = lines[separator_idx + 1:]

        cols = len(header_cells)
        rows = 1 + len(data_lines)

        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)

        for c, text in enumerate(header_cells):
            self.table.setHorizontalHeaderItem(c, QTableWidgetItem(f"Col {c + 1}"))
            self.table.setItem(0, c, QTableWidgetItem(text))

        for r, line in enumerate(data_lines, start=1):
            cells = split_row(line)
            for c in range(cols):
                text = cells[c] if c < len(cells) else ""
                self.table.setItem(r, c, QTableWidgetItem(text))

    def _cell_text(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        return item.text().strip() if item else ""

    def to_markdown(self) -> str:
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        if rows == 0 or cols == 0:
            return ""

        col_widths = []
        for c in range(cols):
            w = 3
            for r in range(rows):
                w = max(w, len(self._cell_text(r, c)))
            col_widths.append(w)

        def format_row(cells: list[str]) -> str:
            padded = [cells[i].ljust(col_widths[i]) for i in range(cols)]
            return "| " + " | ".join(padded) + " |"

        header_cells = [self._cell_text(0, c) for c in range(cols)]
        header_line = format_row(header_cells)

        separator = "| " + " | ".join("-" * w for w in col_widths) + " |"

        data_lines = []
        for r in range(1, rows):
            cells = [self._cell_text(r, c) for c in range(cols)]
            data_lines.append(format_row(cells))

        table_md = "\n".join([header_line, separator] + data_lines)

        layout_cls = self.selected_layout_class
        if not layout_cls:
            return table_md

        width = self.selected_width
        style_attr = f' style="width: {width}%;"' if width != 48 else ""
        return (
            f'<div class="{layout_cls}"{style_attr} markdown="1">\n'
            f"\n{table_md}\n\n"
            f"</div>"
        )


# ---------------------------------------------------------------------------
# Slide Sorter Dialog
# ---------------------------------------------------------------------------


class _SlideSorterList(QListWidget):
    """QListWidget subclass with proper insertion-point drop behavior."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setGridSize(QSize(195, 140))
        self.setIconSize(QSize(190, 130))
        self.setSpacing(4)
        self.setStyleSheet(
            "QListWidget { background: #eaeaea; border: 1px solid #ccc; "
            "border-radius: 6px; padding: 8px; }"
            "QListWidget::item { border-radius: 4px; padding: 4px; }"
            "QListWidget::item:selected { background: #c0d8f0; border: 2px solid #0f3460; }"
        )

    def dropEvent(self, event):
        super().dropEvent(event)
        if hasattr(self.parent(), '_renumber'):
            self.parent()._renumber()


class SlideSorterDialog(QDialog):
    """Grid view of all slides as thumbnails with drag-and-drop reordering."""

    def __init__(self, slides: list[str], parent=None):
        super().__init__(parent)
        self._slides_md = list(slides)
        self.setWindowTitle("Slide Sorter")
        self.setMinimumSize(800, 600)
        self.resize(960, 680)

        root = QVBoxLayout(self)

        hint = QLabel(
            "Drag and drop to rearrange. Hold Ctrl/Cmd to select multiple slides."
        )
        hint.setStyleSheet("color: #555; font-size: 13px; padding: 4px;")
        root.addWidget(hint)

        self.list_widget = _SlideSorterList(self)

        content_area = QHBoxLayout()

        for i, slide_md in enumerate(slides):
            self._add_slide_item(i, slide_md)

        content_area.addWidget(self.list_widget, 3)

        # Right detail panel
        self._detail_panel = QVBoxLayout()
        self._detail_panel.setSpacing(8)

        self._detail_title = QLabel("Select a slide")
        self._detail_title.setStyleSheet(
            "font-weight: bold; font-size: 14px; padding: 4px;"
        )
        self._detail_title.setWordWrap(True)
        self._detail_panel.addWidget(self._detail_title)

        self._detail_number = QLabel("")
        self._detail_number.setStyleSheet("color: #0f3460; font-size: 12px; padding: 0 4px;")
        self._detail_panel.addWidget(self._detail_number)

        self._detail_preview = QPlainTextEdit()
        self._detail_preview.setFont(QFont("Courier New", 11))
        self._detail_preview.setStyleSheet(
            "QPlainTextEdit { background: #1e1e2e; color: #cdd6f4; "
            "border: 1px solid #45475a; border-radius: 6px; padding: 8px; }"
        )
        self._detail_panel.addWidget(self._detail_preview, 1)

        detail_widget = QWidget()
        detail_widget.setLayout(self._detail_panel)
        detail_widget.setMinimumWidth(250)
        detail_widget.setMaximumWidth(350)
        content_area.addWidget(detail_widget, 1)

        root.addLayout(content_area, 1)

        self._editing_index = -1
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self._detail_preview.textChanged.connect(self._on_detail_edited)

        btn_row = QHBoxLayout()

        delete_btn = QPushButton("\U0001f5d1 Delete Selected")
        delete_btn.setStyleSheet("color: #c0392b; padding: 6px 14px;")
        delete_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(delete_btn)

        btn_row.addStretch()

        apply_btn = QPushButton("Apply Order")
        apply_btn.setStyleSheet("font-weight: bold; padding: 6px 20px;")
        apply_btn.clicked.connect(self.accept)
        btn_row.addWidget(apply_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        root.addLayout(btn_row)

    def _add_slide_item(self, index: int, slide_md: str):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, index)
        item.setIcon(QIcon(self._create_thumbnail(index, slide_md)))
        self.list_widget.addItem(item)

    def _renumber(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            orig = item.data(Qt.ItemDataRole.UserRole)
            md = self._slides_md[orig]
            item.setIcon(QIcon(self._create_thumbnail(i, md)))

    def _on_selection_changed(self, current, _previous):
        self._editing_index = -1
        if current is None:
            self._detail_title.setText("Select a slide")
            self._detail_number.setText("")
            self._detail_preview.setPlainText("")
            return
        orig = current.data(Qt.ItemDataRole.UserRole)
        md = self._slides_md[orig]
        row = self.list_widget.row(current)
        first_line = md.strip().split("\n")[0]
        title = re.sub(r"^#+\s*", "", first_line).strip() or "(empty)"
        self._detail_title.setText(title)
        self._detail_number.setText(f"Slide {row + 1} of {self.list_widget.count()}")
        self._detail_preview.blockSignals(True)
        self._detail_preview.setPlainText(md)
        self._detail_preview.blockSignals(False)
        self._editing_index = orig

    def _on_detail_edited(self):
        if self._editing_index < 0:
            return
        new_md = self._detail_preview.toPlainText()
        self._slides_md[self._editing_index] = new_md
        # Update title label
        first_line = new_md.strip().split("\n")[0] if new_md.strip() else ""
        title = re.sub(r"^#+\s*", "", first_line).strip() or "(empty)"
        self._detail_title.setText(title)
        # Refresh thumbnail
        current = self.list_widget.currentItem()
        if current:
            row = self.list_widget.row(current)
            current.setIcon(QIcon(self._create_thumbnail(row, new_md)))

    def _delete_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        remaining = self.list_widget.count() - len(selected)
        if remaining < 1:
            QMessageBox.warning(
                self, "Cannot Delete", "You must keep at least one slide."
            )
            return
        reply = QMessageBox.question(
            self,
            "Delete Slides",
            f"Delete {len(selected)} selected slide(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for item in selected:
            self.list_widget.takeItem(self.list_widget.row(item))
        self._renumber()

    def _create_thumbnail(self, index: int, slide_md: str) -> QPixmap:
        from PyQt6.QtWidgets import QApplication
        dpr = QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 2.0
        w, h = 190, 130
        pixmap = QPixmap(int(w * dpr), int(h * dpr))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(QColor("white"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Border
        painter.setPen(QPen(QColor("#aaa"), 1))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 5, 5)

        # Slide number badge
        painter.setBrush(QColor("#0f3460"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(5, 5, 28, 16, 3, 3)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(5, 5, 28, 16, Qt.AlignmentFlag.AlignCenter, str(index + 1))

        # Title line
        lines = slide_md.strip().split("\n")
        title = re.sub(r"^#+\s*", "", lines[0]).strip() if lines else ""
        title = re.sub(r"<[^>]+>", "", title)
        painter.setPen(QColor("#1a1a2e"))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        if len(title) > 28:
            title = title[:28] + "..."
        painter.drawText(38, 17, title)

        # Content preview
        painter.setPen(QColor("#555"))
        painter.setFont(QFont("Arial", 7))
        y = 30
        for line in lines[1:8]:
            text = re.sub(r"^#+\s*", "", line).strip()
            text = re.sub(r"<[^>]+>", "", text)
            if not text:
                y += 6
                continue
            if len(text) > 38:
                text = text[:38] + "..."
            painter.drawText(7, y, text)
            y += 12
            if y > h - 8:
                break

        painter.end()
        return pixmap

    def get_new_order(self) -> list[int]:
        """Return the original slide indices in the new order."""
        order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            order.append(item.data(Qt.ItemDataRole.UserRole))
        return order

    def get_slides(self) -> list[str]:
        """Return slides content in the new order, with any edits applied."""
        return [self._slides_md[i] for i in self.get_new_order()]
