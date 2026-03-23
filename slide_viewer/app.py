"""Main application window and entry point."""

import atexit
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont, QImage, QKeyEvent
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QDialog,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .ai import AIChatPanel
from .constants import DEFAULT_MARKDOWN, FONT_OPTIONS, SLIDE_DELIMITER
from .dialogs import (
    ColumnsEditorDialog,
    ImageEditorDialog,
    LoadCodeDialog,
    SlideSorterDialog,
    TableEditorDialog,
    _COLS_DIV_RE,
    _IMAGE_DIV_RE,
    _INLINE_IMG_RE,
    _INLINE_IMG_TAG_RE,
    _MD_TABLE_DIV_RE,
    _MD_TABLE_RE,
    _SINGLE_COL_RE,
    _parse_style,
    build_image_snippet,
)
from .editor import MarkdownEditorPanel, MarkdownHighlighter
from .models import SlideData, StyleSettings, _THEME_COMMENT_RE
from .panels import FullMarkdownPanel, SlideNavigator, StylePanel
from .exporter import PptxExporter
from .presentation import PresentationWindow, PresenterWindow
from .renderer import MarkdownRenderer


class SlideWebPage(QWebEnginePage):
    """Custom page that intercepts JS console messages for image drag/resize."""

    image_moved = pyqtSignal(str, int, int, int, int)  # src, index, width%, left%, margin-top%

    def javaScriptConsoleMessage(self, level, message, line, source):
        if message.startswith("SLIDEVIEWER_IMG:"):
            try:
                data = json.loads(message[len("SLIDEVIEWER_IMG:"):])
                self.image_moved.emit(
                    data["src"],
                    int(data.get("index", 0)),
                    int(data["width"]),
                    int(data["left"]),
                    int(data["marginTop"]),
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                pass


class SlideViewerApp(QMainWindow):
    """Main window — orchestrates all components."""

    def __init__(self):
        super().__init__()
        self.style_settings = StyleSettings()
        self.slide_data = SlideData()
        self.renderer = MarkdownRenderer()
        self._current_file: str | None = None
        self._dirty = False
        self._presentation_window: PresentationWindow | None = None
        self._presenter_window: PresenterWindow | None = None
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_current_slide)
        self._working_dir = Path(tempfile.mkdtemp(prefix="slide_viewer_"))
        self._initial_temp_dir = self._working_dir
        atexit.register(self._cleanup_temp_dir)
        self._image_counter = 0
        self._settings = QSettings("SlideViewer", "SlideViewer")
        self._overflow_state: dict[int, bool] = {}
        self._render_generation = 0
        self._overflow_view: QWebEngineView | None = None
        self._overflow_mode = "idle"
        self._scan_index = 0
        self._check_gen = 0
        self._check_idx = 0
        self._overflow_check_timer = QTimer(self)
        self._overflow_check_timer.setSingleShot(True)
        self._overflow_check_timer.timeout.connect(self._do_current_overflow_check)
        self._overflow_measure_timer = QTimer(self)
        self._overflow_measure_timer.setSingleShot(True)
        self._overflow_measure_timer.timeout.connect(self._run_delayed_overflow_check)
        self._style_rescan_timer = QTimer(self)
        self._style_rescan_timer.setSingleShot(True)
        self._style_rescan_timer.timeout.connect(self._scan_all_overflows)

        self._init_window()
        self._init_menu()
        self._init_toolbar()
        self._init_central()
        self._init_style_dock()
        self._init_markdown_dock()

        self._highlighter = MarkdownHighlighter(self.editor_panel.editor.document())
        self.editor_panel.clean_view_toggled.connect(
            lambda on: setattr(self._highlighter, "clean_mode", on)
        )

        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start(60_000)

        self._load_markdown(DEFAULT_MARKDOWN.strip())
        self._update_title()

    # -- Window setup -------------------------------------------------------

    def _init_window(self):
        self.setWindowTitle("Slide Viewer — Untitled")
        self.resize(1400, 900)
        self.setMinimumSize(900, 600)

    # -- Menu bar -----------------------------------------------------------

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        load_file_action = QAction("Load from File", self)
        load_file_action.setShortcut("Ctrl+O")
        load_file_action.triggered.connect(self._load_from_file)
        file_menu.addAction(load_file_action)

        load_code_action = QAction("Load from Code", self)
        load_code_action.setShortcut("Ctrl+Shift+O")
        load_code_action.triggered.connect(self._load_from_code)
        file_menu.addAction(load_code_action)

        file_menu.addSeparator()

        save_action = QAction("Save to File", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_to_file)
        file_menu.addAction(save_action)

        export_pptx_action = QAction("Export to PowerPoint", self)
        export_pptx_action.setShortcut("Ctrl+Shift+E")
        export_pptx_action.triggered.connect(self._export_to_pptx)
        file_menu.addAction(export_pptx_action)

        file_menu.addSeparator()
        self._recent_menu = file_menu.addMenu("Recent Files")
        self._populate_recent_menu()

        view_menu = menubar.addMenu("View")

        self._toggle_editor_action = QAction("Toggle Editor Panel", self)
        self._toggle_editor_action.setShortcut("Ctrl+E")
        self._toggle_editor_action.triggered.connect(self._toggle_editor)
        view_menu.addAction(self._toggle_editor_action)

        self._toggle_style_action = QAction("Toggle Style Panel", self)
        self._toggle_style_action.setShortcut("Ctrl+T")
        self._toggle_style_action.triggered.connect(self._toggle_style_dock)
        view_menu.addAction(self._toggle_style_action)

        self._toggle_markdown_action = QAction("Toggle Markdown Panel", self)
        self._toggle_markdown_action.setShortcut("Ctrl+M")
        self._toggle_markdown_action.triggered.connect(self._toggle_markdown_dock)
        view_menu.addAction(self._toggle_markdown_action)

        view_menu.addSeparator()

        present_action = QAction("Presentation Mode", self)
        present_action.setShortcut("F5")
        present_action.triggered.connect(self._start_presentation)
        view_menu.addAction(present_action)

        presenter_action = QAction("Presenter Mode (with Notes)", self)
        presenter_action.setShortcut("Shift+F5")
        presenter_action.triggered.connect(self._start_presenter)
        view_menu.addAction(presenter_action)

        help_menu = menubar.addMenu("Help")
        guide_action = QAction("User Guide", self)
        guide_action.setShortcut("F1")
        guide_action.triggered.connect(self._show_user_guide)
        help_menu.addAction(guide_action)
        about_action = QAction("About Slide Viewer", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # -- Toolbar ------------------------------------------------------------

    def _init_toolbar(self):
        toolbar = QToolBar("Navigation")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        toolbar.setStyleSheet(
            "QToolBar { spacing: 6px; padding: 4px; }"
            "QToolButton { padding: 4px 10px; }"
        )
        self.addToolBar(toolbar)

        prev_btn = QPushButton("\u25c0 Prev")
        prev_btn.clicked.connect(self._prev_slide)
        toolbar.addWidget(prev_btn)

        next_btn = QPushButton("\u25b6 Next")
        next_btn.clicked.connect(self._next_slide)
        toolbar.addWidget(next_btn)

        toolbar.addSeparator()

        self.slide_label = QLabel("Slide 1 / 1")
        self.slide_label.setStyleSheet("font-weight: bold; padding: 0 12px;")
        toolbar.addWidget(self.slide_label)

        toolbar.addSeparator()

        add_btn = QPushButton("+ Add Slide")
        add_btn.clicked.connect(self._add_slide)
        toolbar.addWidget(add_btn)

        insert_btn = QPushButton("\u2795 Insert Slide")
        insert_btn.setToolTip("Insert a new slide before the current slide")
        insert_btn.clicked.connect(self._insert_slide)
        toolbar.addWidget(insert_btn)

        del_btn = QPushButton("\U0001f5d1 Delete Slide")
        del_btn.clicked.connect(self._delete_slide)
        toolbar.addWidget(del_btn)

        toolbar.addSeparator()

        save_btn = QPushButton("\U0001f4be Save")
        save_btn.setToolTip("Save presentation (Ctrl+S)")
        save_btn.clicked.connect(self._save_to_file)
        toolbar.addWidget(save_btn)

        toolbar.addSeparator()

        sorter_btn = QPushButton("\u25a6 Slide Sorter")
        sorter_btn.setToolTip("View all slides and rearrange them")
        sorter_btn.clicked.connect(self._open_slide_sorter)
        toolbar.addWidget(sorter_btn)

        toolbar.addSeparator()

        copy_instr_btn = QPushButton("\U0001f4cb Copy LLM Instructions")
        copy_instr_btn.setToolTip(
            "Copy slide format guide to clipboard for use with AI assistants"
        )
        copy_instr_btn.clicked.connect(self._copy_instructions)
        toolbar.addWidget(copy_instr_btn)

        toolbar.addSeparator()

        self._overflow_label = QLabel("\u26a0 Content overflows slide")
        self._overflow_label.setStyleSheet(
            "color: #e67e22; font-weight: bold; padding: 0 8px;"
        )
        self._overflow_label.setVisible(False)
        toolbar.addWidget(self._overflow_label)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        check_overflow_btn = QPushButton("Check All Slides")
        check_overflow_btn.setToolTip("Scan all slides for content overflow")
        check_overflow_btn.clicked.connect(self._scan_all_overflows)
        toolbar.addWidget(check_overflow_btn)

        toolbar.addSeparator()

        present_btn = QPushButton("\u26f6 Present")
        present_btn.setStyleSheet("font-weight: bold;")
        present_btn.clicked.connect(self._start_presentation)
        toolbar.addWidget(present_btn)

    # -- Central layout -----------------------------------------------------

    def _init_central(self):
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setChildrenCollapsible(False)

        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.setChildrenCollapsible(False)
        left_splitter.setMinimumWidth(250)
        left_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.editor_panel = MarkdownEditorPanel()
        self.editor_panel.editor.installEventFilter(self)
        self.editor_panel.content_changed.connect(self._on_editor_changed)
        self.editor_panel.apply_requested.connect(self._apply_editor)
        self.editor_panel.image_insert_requested.connect(self._insert_image)
        self.editor_panel.image_edit_requested.connect(self._edit_image)
        self.editor_panel.table_insert_requested.connect(self._insert_table)
        self.editor_panel.table_edit_requested.connect(self._edit_table)
        self.editor_panel.columns_insert_requested.connect(self._insert_columns)
        self.editor_panel.columns_edit_requested.connect(self._edit_columns)
        self.editor_panel.color_requested.connect(self._color_selected_text)
        self.editor_panel.font_requested.connect(self._font_selected_text)
        self.editor_panel.fontsize_requested.connect(self._fontsize_selected_text)
        self.editor_panel.slide_theme_requested.connect(self._edit_slide_theme)
        left_splitter.addWidget(self.editor_panel)

        self.chat_panel = AIChatPanel()
        self.chat_panel.slide_update_requested.connect(self._on_ai_update)
        self.chat_panel.slide_insert_requested.connect(self._on_ai_insert)
        self.chat_panel.undo_requested.connect(self._on_ai_update)
        left_splitter.addWidget(self.chat_panel)

        left_splitter.setStretchFactor(0, 6)
        left_splitter.setStretchFactor(1, 4)

        self.web_view = QWebEngineView()
        self._slide_page = SlideWebPage(self.web_view)
        self.web_view.setPage(self._slide_page)
        self._slide_page.image_moved.connect(self._on_image_moved)
        self.web_view.setMinimumWidth(300)
        self.web_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(self.web_view)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setSizes([450, 950])

        self._left_splitter = left_splitter
        self._main_splitter = main_splitter
        self.setCentralWidget(main_splitter)

    # -- Style dock ---------------------------------------------------------

    def _init_style_dock(self):
        self.style_panel = StylePanel(self.style_settings)
        self.style_panel.style_changed.connect(self._on_style_changed)

        self.slide_navigator = SlideNavigator()
        self.slide_navigator.slide_selected.connect(self._go_to_slide)

        dock_container = QWidget()
        dock_layout = QVBoxLayout(dock_container)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(0)
        dock_layout.addWidget(self.style_panel)
        dock_layout.addWidget(self.slide_navigator, 1)

        self.style_dock = QDockWidget("Slide Theme", self)
        self.style_dock.setWidget(dock_container)
        self.style_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.style_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.style_dock)

    def _init_markdown_dock(self):
        self.markdown_panel = FullMarkdownPanel()
        self.markdown_panel.content_edited.connect(self._on_full_markdown_edited)

        self.markdown_dock = QDockWidget("Full Markdown", self)
        self.markdown_dock.setWidget(self.markdown_panel)
        self.markdown_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.markdown_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.markdown_dock)
        self.splitDockWidget(self.style_dock, self.markdown_dock, Qt.Orientation.Vertical)
        self.markdown_dock.visibilityChanged.connect(self._on_markdown_dock_visible)

    # -- Slide logic --------------------------------------------------------

    def _load_markdown(self, text: str):
        slides = re.split(r"\n" + re.escape(SLIDE_DELIMITER) + r"\n", text)
        self.slide_data.slides = [s.strip() for s in slides if s.strip()]
        if not self.slide_data.slides:
            self.slide_data.slides = ["# New Slide\n\nAdd your content here."]
        self.slide_data.current_index = 0
        self._clear_overflow_state()
        self._sync_ui()

    def _sync_ui(self):
        self.editor_panel.set_text(self.slide_data.current_markdown)
        self._render_current_slide()
        self._update_slide_label()
        self.slide_navigator.update_slides(
            self.slide_data.slides, self.slide_data.current_index
        )
        self.chat_panel.reset_for_slide()
        self._update_markdown_panel()

    def _render_current_slide(self):
        self._render_generation += 1
        html = self.renderer.render(
            self.slide_data.content_for_render(), self.style_settings
        )
        base_url = QUrl.fromLocalFile(str(self._working_dir) + "/")
        self.web_view.page().setHtml(html, base_url)
        self._overflow_check_timer.start(500)

    def _update_slide_label(self):
        idx = self.slide_data.current_index + 1
        total = self.slide_data.total
        self.slide_label.setText(f"Slide {idx} / {total}")

    def _update_title(self):
        name = self._current_file or "Untitled"
        dirty = " *" if self._dirty else ""
        self.setWindowTitle(f"Slide Viewer — {name}{dirty}")

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self._update_title()

    # -- Navigation ---------------------------------------------------------

    def _prev_slide(self):
        if self.slide_data.current_index > 0:
            self.slide_data.current_index -= 1
            self._sync_ui()

    def _next_slide(self):
        if self.slide_data.current_index < self.slide_data.total - 1:
            self.slide_data.current_index += 1
            self._sync_ui()

    def _add_slide(self):
        new_slide = "# New Slide\n\nAdd your content here."
        idx = self.slide_data.current_index + 1
        self.slide_data.slides.insert(idx, new_slide)
        self.slide_data.current_index = idx
        self._clear_overflow_state()
        self._mark_dirty()
        self._sync_ui()

    def _insert_slide(self):
        dialog = LoadCodeDialog(self)
        dialog.setWindowTitle("Insert Slides")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        text = dialog.text_edit.toPlainText().strip()
        if not text:
            return
        new_slides = re.split(r"\n" + re.escape(SLIDE_DELIMITER) + r"\n", text)
        new_slides = [s.strip() for s in new_slides if s.strip()]
        if not new_slides:
            return
        idx = self.slide_data.current_index
        for i, slide in enumerate(new_slides):
            self.slide_data.slides.insert(idx + i, slide)
        self._clear_overflow_state()
        self._mark_dirty()
        self._sync_ui()
        self.statusBar().showMessage(
            f"Inserted {len(new_slides)} slide(s) at position {idx + 1}.", 5000
        )

    def _delete_slide(self):
        if self.slide_data.total <= 1:
            QMessageBox.information(
                self, "Cannot Delete", "You must have at least one slide."
            )
            return
        reply = QMessageBox.question(
            self,
            "Delete Slide",
            f"Delete slide {self.slide_data.current_index + 1}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self.slide_data.slides[self.slide_data.current_index]
            if self.slide_data.current_index >= self.slide_data.total:
                self.slide_data.current_index = self.slide_data.total - 1
            self._clear_overflow_state()
            self._mark_dirty()
            self._sync_ui()

    # -- Overflow detection (presentation-mode, 1920x1080) --------------------

    def _on_style_changed(self):
        self._clear_overflow_state()
        self._render_current_slide()
        self._style_rescan_timer.start(1200)

    _OVERFLOW_JS = """
    (function() {
        var frame = document.querySelector('.slide-frame');
        if (!frame) return false;
        return frame.scrollHeight > frame.clientHeight + 2;
    })();
    """

    def _ensure_overflow_view(self):
        if self._overflow_view is not None:
            return
        self._overflow_view = QWebEngineView()
        self._overflow_view.setFixedSize(1920, 1080)
        self._overflow_view.setAttribute(
            Qt.WidgetAttribute.WA_DontShowOnScreen, True
        )
        self._overflow_view.setAttribute(
            Qt.WidgetAttribute.WA_QuitOnClose, False
        )
        self._overflow_view.show()
        self._overflow_view.page().loadFinished.connect(
            self._on_overflow_view_loaded
        )

    def _on_overflow_view_loaded(self, ok: bool):
        if self._overflow_mode == "current":
            self._on_current_overflow_loaded(ok)
        elif self._overflow_mode == "scanning":
            self._on_scan_loaded(ok)

    # -- Per-slide overflow check (debounced, presentation-mode) ------------

    def _do_current_overflow_check(self):
        if self._overflow_mode == "scanning":
            return
        self._ensure_overflow_view()
        self._overflow_mode = "current"
        self._check_gen = self._render_generation
        self._check_idx = self.slide_data.current_index
        content = self.slide_data.content_for_render()
        html = self.renderer.render(
            content, self.style_settings, presentation=True
        )
        base_url = QUrl.fromLocalFile(str(self._working_dir) + "/")
        self._overflow_view.page().setHtml(html, base_url)

    def _on_current_overflow_loaded(self, ok: bool):
        if not ok or self._render_generation != self._check_gen:
            self._overflow_mode = "idle"
            return
        self._overflow_measure_timer.start(250)

    def _run_delayed_overflow_check(self):
        if self._overflow_mode == "current":
            idx = self._check_idx
            self._overflow_view.page().runJavaScript(
                self._OVERFLOW_JS,
                lambda overflows, i=idx: self._on_current_overflow_result(
                    i, overflows
                ),
            )
        elif self._overflow_mode == "scanning":
            idx = self._scan_index
            self._overflow_view.page().runJavaScript(
                self._OVERFLOW_JS,
                lambda overflows, i=idx: self._on_scan_overflow_result(
                    i, overflows
                ),
            )

    def _on_current_overflow_result(self, index: int, overflows: bool):
        self._overflow_mode = "idle"
        self._overflow_state[index] = bool(overflows)
        self._overflow_label.setVisible(bool(overflows))
        self.slide_navigator.mark_overflow(index, bool(overflows))

    # -- Batch scan (presentation-mode) -------------------------------------

    def _scan_all_overflows(self):
        if self._overflow_mode != "idle":
            return
        self._overflow_mode = "scanning"
        self._overflow_state.clear()
        self.slide_navigator.clear_overflow_marks()
        self._scan_index = 0
        self._ensure_overflow_view()

        self.statusBar().showMessage(
            f"Checking slide 1 of {self.slide_data.total}..."
        )
        self._scan_render_slide()

    def _scan_render_slide(self):
        if self._scan_index >= self.slide_data.total:
            self._overflow_mode = "idle"
            count = sum(1 for v in self._overflow_state.values() if v)
            if count:
                self.statusBar().showMessage(
                    f"Scan complete: {count} slide(s) overflow.", 5000
                )
            else:
                self.statusBar().showMessage(
                    "Scan complete: all slides fit.", 5000
                )
            return

        content = self.slide_data.content_for_render(index=self._scan_index)
        html = self.renderer.render(
            content, self.style_settings, presentation=True
        )
        base_url = QUrl.fromLocalFile(str(self._working_dir) + "/")
        self._overflow_view.page().setHtml(html, base_url)

    def _on_scan_loaded(self, ok: bool):
        if self._overflow_mode != "scanning":
            return
        if not ok:
            self._scan_index += 1
            self._scan_render_slide()
            return
        self._overflow_measure_timer.start(250)

    def _on_scan_overflow_result(self, index: int, overflows: bool):
        if self._overflow_mode != "scanning":
            return
        self._overflow_state[index] = bool(overflows)
        self.slide_navigator.mark_overflow(index, bool(overflows))
        if index == self.slide_data.current_index:
            self._overflow_label.setVisible(bool(overflows))

        self._scan_index += 1
        if self._scan_index < self.slide_data.total:
            self.statusBar().showMessage(
                f"Checking slide {self._scan_index + 1}"
                f" of {self.slide_data.total}..."
            )
        self._scan_render_slide()

    def _clear_overflow_state(self):
        self._overflow_state.clear()
        self._overflow_label.setVisible(False)
        self.slide_navigator.clear_overflow_marks()
        self._overflow_mode = "idle"

    # -- Editor integration -------------------------------------------------

    def _on_editor_changed(self):
        self.slide_data.current_markdown = self.editor_panel.get_text()
        self._render_timer.start(300)
        self._update_markdown_panel()
        self._mark_dirty()

    def _apply_editor(self):
        self.slide_data.current_markdown = self.editor_panel.get_text()
        self._render_current_slide()

    # -- Text color (editor selection) ---------------------------------------

    def _color_selected_text(self):
        cursor = self.editor_panel.editor.textCursor()
        selected = cursor.selectedText()
        if not selected:
            QMessageBox.information(
                self,
                "No Selection",
                "Select text in the markdown editor first, then click \U0001f3a8.",
            )
            return

        color = QColorDialog.getColor(QColor("#e94560"), self, "Pick Text Color")
        if not color.isValid():
            return

        existing = re.match(
            r'^<span\s+style="color:\s*[^"]*;">(.*)</span>$', selected, re.DOTALL
        )
        if existing:
            inner = existing.group(1)
        else:
            inner = selected

        colored = f'<span style="color: {color.name()};">{inner}</span>'
        cursor.insertText(colored)
        self.editor_panel.editor.setTextCursor(cursor)

    _SPAN_STYLE_RE = re.compile(
        r'^<span\s+style="([^"]*)">(.*)</span>$', re.DOTALL
    )

    def _wrap_with_style(self, prop: str, value: str):
        """Wrap the editor selection with a span style, merging into existing spans."""
        cursor = self.editor_panel.editor.textCursor()
        selected = cursor.selectedText()
        if not selected:
            QMessageBox.information(
                self, "No Selection",
                "Select text in the markdown editor first.",
            )
            return

        m = self._SPAN_STYLE_RE.match(selected)
        if m:
            old_style = m.group(1)
            inner = m.group(2)
            cleaned = re.sub(rf"{re.escape(prop)}:\s*[^;]+;?\s*", "", old_style).strip()
            new_style = f"{prop}: {value}; {cleaned}".strip().rstrip(";") + ";"
        else:
            inner = selected
            new_style = f"{prop}: {value};"

        wrapped = f'<span style="{new_style}">{inner}</span>'
        cursor.insertText(wrapped)
        self.editor_panel.editor.setTextCursor(cursor)

    def _font_selected_text(self):
        from PyQt6.QtWidgets import QInputDialog

        cursor = self.editor_panel.editor.textCursor()
        if not cursor.selectedText():
            QMessageBox.information(
                self, "No Selection",
                "Select text in the markdown editor first, then click F.",
            )
            return

        fonts = FONT_OPTIONS + ["monospace", "cursive", "fantasy"]
        font, ok = QInputDialog.getItem(
            self, "Pick Font", "Font family:", fonts, 0, False
        )
        if ok and font:
            self._wrap_with_style("font-family", font)

    def _fontsize_selected_text(self):
        from PyQt6.QtWidgets import QInputDialog

        cursor = self.editor_panel.editor.textCursor()
        if not cursor.selectedText():
            QMessageBox.information(
                self, "No Selection",
                "Select text in the markdown editor first, then click T\u2195.",
            )
            return

        sizes = [str(s) + "px" for s in range(10, 50, 2)]
        size, ok = QInputDialog.getItem(
            self, "Pick Size", "Font size:", sizes, 4, True
        )
        if ok and size:
            self._wrap_with_style("font-size", size)

    # -- Clipboard image paste ------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self.editor_panel.editor and event.type() == event.Type.KeyPress:
            if (event.key() == Qt.Key.Key_V
                    and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                mime = QApplication.clipboard().mimeData()
                if mime and mime.hasImage():
                    self._paste_clipboard_image(mime)
                    return True
        return super().eventFilter(obj, event)

    def _paste_clipboard_image(self, mime_data):
        """Handle pasting an image from the clipboard."""
        qimage = QImage(mime_data.imageData())
        if qimage.isNull():
            return

        images_dir = self._working_dir / "images"
        images_dir.mkdir(exist_ok=True)

        self._image_counter += 1
        short_name = f"image{self._image_counter}.png"
        dest_path = images_dir / short_name
        qimage.save(str(dest_path), "PNG")

        dlg = ImageEditorDialog(self, preset_path=str(dest_path))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            dest_path.unlink(missing_ok=True)
            self._image_counter -= 1
            return

        rel_path = f"images/{short_name}"
        snippet = dlg.snippet(rel_path)
        self.editor_panel.insert_snippet(snippet)

    # -- Image insertion / editing -------------------------------------------

    def _insert_image(self):
        dlg = ImageEditorDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        src_path = dlg.image_path
        if not src_path:
            return

        images_dir = self._working_dir / "images"
        images_dir.mkdir(exist_ok=True)

        self._image_counter += 1
        ext = Path(src_path).suffix
        short_name = f"image{self._image_counter}{ext}"
        shutil.copy2(src_path, images_dir / short_name)

        rel_path = f"images/{short_name}"
        snippet = dlg.snippet(rel_path)
        self.editor_panel.insert_snippet(snippet)

    def _edit_image(self):
        md = self.editor_panel.get_text()

        entries: list[tuple[str, str, str, str, re.Match]] = []
        for m in _IMAGE_DIV_RE.finditer(md):
            entries.append((m.group(3), m.group(1), m.group(4) or "", m.group(2) or "", m))
        for m in _INLINE_IMG_RE.finditer(md):
            entries.append((m.group(2), "inline", m.group(1), "", m))

        if not entries:
            QMessageBox.information(self, "No Images", "No images found in the current slide.")
            return

        if len(entries) == 1:
            chosen = 0
        else:
            labels = [e[0].split("/")[-1] for e in entries]
            from PyQt6.QtWidgets import QInputDialog
            label, ok = QInputDialog.getItem(
                self, "Select Image", "Choose an image to edit:", labels, 0, False
            )
            if not ok:
                return
            chosen = labels.index(label)

        src, css_class, caption, style_str, match = entries[chosen]
        style_vals = _parse_style(style_str)
        old_snippet = match.group(0)

        dlg = ImageEditorDialog(
            self,
            edit_src=src,
            edit_class=css_class,
            edit_caption=caption,
            edit_style=style_vals,
        )

        def _on_live_change(_src: str, new_snippet: str):
            nonlocal old_snippet
            current = self.editor_panel.get_text()
            if old_snippet in current:
                updated = current.replace(old_snippet, new_snippet, 1)
                self.editor_panel.set_text(updated)
                self.slide_data.current_markdown = updated
                self._render_current_slide()
                old_snippet = new_snippet

        dlg.snippet_changed.connect(_on_live_change)
        dlg.exec()

    # -- Image drag/resize from preview --------------------------------------

    def _on_image_moved(self, src: str, index: int, width: int, left: int, margin_top: int):
        """Handle an image being dragged or resized on the slide preview."""
        md = self.editor_panel.get_text()

        # Collect all image entries: (src, css_class, caption, match_object)
        entries: list[tuple[str, str, str, re.Match]] = []
        div_spans: set[tuple[int, int]] = set()

        for m in _IMAGE_DIV_RE.finditer(md):
            entries.append((m.group(3), m.group(1), m.group(4) or "", m))
            div_spans.add((m.start(), m.end()))

        for m in _INLINE_IMG_TAG_RE.finditer(md):
            # Skip if this <img> is inside a div already matched
            if any(s <= m.start() and m.end() <= e for s, e in div_spans):
                continue
            entries.append((m.group(1), "inline", m.group(2) or "image", m))

        for m in _INLINE_IMG_RE.finditer(md):
            # Skip if overlapping with a div or inline img tag match
            if any(s <= m.start() and m.end() <= e for s, e in div_spans):
                continue
            already = any(
                e[3].start() <= m.start() and m.end() <= e[3].end()
                for e in entries if e[3] is not m
            )
            if already:
                continue
            entries.append((m.group(2), "inline", m.group(1), m))

        # Find the matching entry by src and index
        match_count = 0
        target = None
        for entry in entries:
            if entry[0] == src:
                if match_count == index:
                    target = entry
                    break
                match_count += 1

        if target is None:
            return

        img_src, css_class, caption, match = target
        old_snippet = match.group(0)
        new_snippet = build_image_snippet(
            src=img_src,
            css_class=css_class,
            caption=caption,
            width=width,
            left=left,
            margin_top=margin_top,
        )

        if old_snippet != new_snippet and old_snippet in md:
            updated = md.replace(old_snippet, new_snippet, 1)
            self.editor_panel.set_text(updated)
            self.slide_data.current_markdown = updated
            self._render_current_slide()
            self._dirty = True
            self._update_title()

    # -- Table insertion / editing -------------------------------------------

    def _insert_table(self):
        dlg = TableEditorDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        md = dlg.to_markdown()
        if md:
            self.editor_panel.insert_snippet(md)

    def _edit_table(self):
        md = self.editor_panel.get_text()

        layout_class = ""
        layout_width: int | None = None
        table_md = ""
        old_snippet = ""

        div_match = _MD_TABLE_DIV_RE.search(md)
        if div_match:
            layout_class = div_match.group(1)
            layout_width = int(div_match.group(2)) if div_match.group(2) else 48
            table_md = div_match.group(3).strip()
            old_snippet = div_match.group(0)
        else:
            plain_match = _MD_TABLE_RE.search(md)
            if plain_match:
                table_md = plain_match.group(0).rstrip("\n")
                old_snippet = table_md
            else:
                QMessageBox.information(
                    self, "No Table", "No markdown table found in the current slide."
                )
                return

        dlg = TableEditorDialog(
            self,
            markdown_table=table_md,
            layout_class=layout_class,
            layout_width=layout_width,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_table = dlg.to_markdown()
        if new_table:
            updated = md.replace(old_snippet, new_table, 1)
            self.editor_panel.set_text(updated)
            self.slide_data.current_markdown = updated
            self._render_current_slide()

    # -- Column layout insertion / editing -----------------------------------

    def _insert_columns(self):
        dlg = ColumnsEditorDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        snippet = dlg.to_snippet()
        if snippet:
            self.editor_panel.insert_snippet(snippet)

    def _edit_columns(self):
        md = self.editor_panel.get_text()
        match = _COLS_DIV_RE.search(md)
        if not match:
            QMessageBox.information(
                self, "No Column Layout",
                "No column layout found in the current slide.",
            )
            return

        old_snippet = match.group(0)
        col_contents = _SINGLE_COL_RE.findall(match.group(1))

        gap_match = re.search(r'gap:\s*([\d.]+em)', old_snippet)
        gap = gap_match.group(1) if gap_match else "2em"

        ratios: list[int] = []
        for col_div in re.finditer(r'<div\s+class="col"[^>]*>', old_snippet):
            flex_m = re.search(r'flex:\s*(\d+)', col_div.group(0))
            ratios.append(int(flex_m.group(1)) if flex_m else 1)

        dlg = ColumnsEditorDialog(
            self,
            column_contents=col_contents,
            ratios=ratios if ratios else None,
            gap=gap,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_snippet = dlg.to_snippet()
        if new_snippet:
            updated = md.replace(old_snippet, new_snippet, 1)
            self.editor_panel.set_text(updated)
            self.slide_data.current_markdown = updated
            self._render_current_slide()

    def _scan_image_counter(self):
        """Set _image_counter based on existing imageN files in images/ dir."""
        images_dir = self._working_dir / "images"
        if not images_dir.exists():
            return
        max_num = 0
        for f in images_dir.iterdir():
            m = re.match(r"image(\d+)", f.stem)
            if m:
                max_num = max(max_num, int(m.group(1)))
        self._image_counter = max(self._image_counter, max_num)

    # -- AI integration -----------------------------------------------------

    def _on_ai_update(self, new_markdown: str):
        self.slide_data.current_markdown = new_markdown
        self.editor_panel.set_text(new_markdown)
        self._render_current_slide()

    def _on_ai_insert(self, markdown_snippet: str):
        self.editor_panel.insert_snippet(markdown_snippet)
        self.slide_data.current_markdown = self.editor_panel.get_text()
        self._render_current_slide()

    # -- File I/O -----------------------------------------------------------

    def _load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Markdown File", "", "Markdown Files (*.md *.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self._load_markdown(content)
            self._current_file = path
            self._working_dir = Path(path).parent
            self._scan_image_counter()
            self._update_title()
            self._add_recent_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Error Loading File", str(exc))

    def _load_from_code(self):
        dialog = LoadCodeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.text_edit.toPlainText().strip()
            if text:
                self._load_markdown(text)
                self._current_file = None
                self._update_title()

    def _save_to_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Markdown File", "", "Markdown Files (*.md);;All Files (*)"
        )
        if not path:
            return
        try:
            save_dir = Path(path).parent
            src_images = self._working_dir / "images"

            if save_dir.resolve() != self._working_dir.resolve() and src_images.exists():
                dst_images = save_dir / "images"
                if dst_images.exists():
                    if dst_images.is_symlink():
                        dst_images.unlink()
                    else:
                        shutil.rmtree(dst_images)
                shutil.copytree(src_images, dst_images)

            with open(path, "w", encoding="utf-8") as f:
                f.write(self.slide_data.joined())
            self._current_file = path
            self._working_dir = save_dir
            self._dirty = False
            self._update_title()
            self._add_recent_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Error Saving File", str(exc))

    def _export_to_pptx(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to PowerPoint", "",
            "PowerPoint Files (*.pptx);;All Files (*)",
        )
        if not path:
            return
        if not path.endswith(".pptx"):
            path += ".pptx"

        self.statusBar().showMessage("Exporting slides to PowerPoint…")

        base_url = QUrl.fromLocalFile(str(self._working_dir) + "/")
        self._pptx_exporter = PptxExporter(
            self.slide_data,
            self.style_settings,
            self.renderer,
            path,
            base_url,
            parent=self,
        )
        self._pptx_exporter.progress.connect(self._on_export_progress)
        self._pptx_exporter.finished.connect(self._on_export_finished)
        self._pptx_exporter.error.connect(self._on_export_error)
        self._pptx_exporter.start()

    def _on_export_progress(self, current: int, total: int):
        self.statusBar().showMessage(
            f"Rendering slide {current} of {total}…"
        )

    def _on_export_finished(self, path: str):
        self.statusBar().showMessage("Export complete!", 5000)
        QMessageBox.information(
            self, "Export Complete",
            f"Presentation saved to:\n{path}",
        )

    def _on_export_error(self, msg: str):
        self.statusBar().clearMessage()
        QMessageBox.critical(self, "Export Error", msg)

    # -- Direct slide navigation --------------------------------------------

    def _go_to_slide(self, index: int):
        if 0 <= index < self.slide_data.total:
            self.slide_data.current_index = index
            self._sync_ui()

    # -- Slide sorter -------------------------------------------------------

    def _open_slide_sorter(self):
        dlg = SlideSorterDialog(self.slide_data.slides, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_slides = dlg.get_slides()
        if new_slides == self.slide_data.slides:
            return
        self.slide_data.slides = new_slides
        if not self.slide_data.slides:
            self.slide_data.slides = ["# New Slide\n\nAdd your content here."]
        self.slide_data.current_index = 0
        self._clear_overflow_state()
        self._mark_dirty()
        self._sync_ui()

    # -- Presentation mode --------------------------------------------------

    def _start_presentation(self):
        if self._presentation_window is not None:
            self._presentation_window.close()
        self.hide()
        base_url = QUrl.fromLocalFile(str(self._working_dir) + "/")
        self._presentation_window = PresentationWindow(
            self.renderer, self.style_settings, self.slide_data,
            base_url=base_url, parent=None,
        )
        self._presentation_window.closed.connect(self._on_presentation_closed)

    def _on_presentation_closed(self):
        self._presentation_window = None
        self.show()
        self.raise_()
        self.activateWindow()
        self._sync_ui()

    # -- Keyboard navigation ------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_F1:
            self._show_user_guide()
            return
        if (
            self.editor_panel.editor.hasFocus()
            or self.chat_panel.user_input.hasFocus()
            or self.markdown_panel.text_view.hasFocus()
        ):
            super().keyPressEvent(event)
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self._next_slide()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self._prev_slide()
        else:
            super().keyPressEvent(event)

    # -- Markdown panel sync ------------------------------------------------

    def _update_markdown_panel(self):
        if hasattr(self, "markdown_panel") and self.markdown_dock.isVisible():
            self.markdown_panel.update_content(self.slide_data.joined())

    def _on_full_markdown_edited(self):
        text = self.markdown_panel.get_text()
        slides = re.split(r"\n" + re.escape(SLIDE_DELIMITER) + r"\n", text)
        self.slide_data.slides = [s.strip() for s in slides if s.strip()]
        if not self.slide_data.slides:
            self.slide_data.slides = ["# New Slide\n\nAdd your content here."]
        if self.slide_data.current_index >= self.slide_data.total:
            self.slide_data.current_index = self.slide_data.total - 1
        self._clear_overflow_state()
        self.editor_panel.set_text(self.slide_data.current_markdown)
        self._render_timer.start(300)
        self._update_slide_label()
        self.slide_navigator.update_slides(
            self.slide_data.slides, self.slide_data.current_index
        )
        self._mark_dirty()

    def _on_markdown_dock_visible(self, visible: bool):
        if visible:
            self._update_markdown_panel()

    # -- View toggles -------------------------------------------------------

    def _toggle_editor(self):
        parent = self._left_splitter.parent()
        if parent:
            vis = self._left_splitter.isVisible()
            self._left_splitter.setVisible(not vis)

    def _toggle_style_dock(self):
        vis = self.style_dock.isVisible()
        self.style_dock.setVisible(not vis)

    def _toggle_markdown_dock(self):
        vis = self.markdown_dock.isVisible()
        self.markdown_dock.setVisible(not vis)
        if not vis:
            self.markdown_dock.raise_()
            self._update_markdown_panel()

    # -- Copy LLM Instructions ----------------------------------------------

    def _copy_instructions(self):
        guide_path = Path(__file__).parent / "SLIDE_FORMAT_GUIDE.md"
        if not guide_path.exists():
            QMessageBox.warning(
                self,
                "File Not Found",
                "Could not find SLIDE_FORMAT_GUIDE.md in the package directory.",
            )
            return
        try:
            text = guide_path.read_text(encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to read guide file:\n{exc}")
            return

        QApplication.clipboard().setText(text)
        QMessageBox.information(
            self,
            "Instructions Copied",
            "The slide format instructions have been copied to your clipboard.\n\n"
            "Next steps:\n"
            "1. Open your preferred AI assistant (ChatGPT, Claude, Gemini, etc.)\n"
            "2. Paste the instructions into the chat\n"
            "3. Ask the AI to create slides on your topic\n"
            "4. Copy the AI's markdown output\n"
            "5. Paste it into the Full Markdown panel (Ctrl+M)\n"
            "   or use File \u2192 Load from Code (Ctrl+Shift+O)",
        )

    # -- Help ---------------------------------------------------------------

    def _show_user_guide(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Slide Viewer — User Guide")
        dlg.setMinimumSize(640, 520)
        dlg.resize(720, 580)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet(
            "QTextBrowser { font-size: 13px; line-height: 1.5; "
            "padding: 12px; background: white; color: black; }"
        )
        browser.setHtml(self._USER_GUIDE_HTML)
        layout.addWidget(browser)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec()

    def _show_about(self):
        QMessageBox.about(
            self,
            "About Slide Viewer",
            "<p><b>Slide Viewer</b></p>"
            "<p>A markdown-powered presentation tool.</p>"
            "<p>Create and edit slides with markdown, customize themes, "
            "present fullscreen, and export to PowerPoint.</p>"
            "<p>Press <b>F1</b> for the User Guide.</p>",
        )

    _USER_GUIDE_HTML = """
    <h1>Slide Viewer — User Guide</h1>

    <h2>Overview</h2>
    <p>Slide Viewer is a desktop app for creating and presenting slides from markdown.
    The window is split into: <b>editor panel</b> (left), <b>slide preview</b> (center),
    and <b>Slide Theme / Slide Navigator</b> (right). You can also open a <b>Full Markdown</b>
    panel to edit the whole deck as one document.</p>

    <h2>Interface</h2>
    <ul>
    <li><b>Editor panel (left)</b> — Markdown for the current slide with live preview.
    Toolbar: insert image, table, columns, text color, font, theme override.</li>
    <li><b>Slide preview (center)</b> — Live 16:9 preview of the current slide.
    Images can be dragged and resized directly in the preview.</li>
    <li><b>Slide Theme (right)</b> — Colors, font, font size, preset themes (5 built-in),
    background (solid/gradient/image), and transitions.</li>
    <li><b>Slide Navigator (right)</b> — List of all slides; click to jump. Slides that
    overflow in presentation mode are marked with a warning icon.</li>
    <li><b>AI chat (bottom left)</b> — Optional OpenAI assistant; enter your API key
    in the chat panel. The AI can rewrite or suggest changes for the current slide.</li>
    <li><b>Full Markdown panel</b> — View/edit the entire deck as one document; slides
    are separated by <code>slide#</code> on its own line. Open with <b>Ctrl+M</b>.</li>
    </ul>

    <h2>Toolbar</h2>
    <ul>
    <li><b>Prev / Next</b> — Navigate between slides.</li>
    <li><b>+ Add Slide</b> — Adds a new blank slide <i>after</i> the current slide.</li>
    <li><b>Insert Slide</b> — Opens a dialog where you can paste markdown containing
    one or more slides (separated by <code>slide#</code>). The new slides are inserted
    <i>before</i> the current slide position. This is useful for bulk-inserting slides
    generated by an AI or copied from another source.</li>
    <li><b>Delete Slide</b> — Removes the current slide (with confirmation).</li>
    <li><b>Save</b> — Quick save (Ctrl+S).</li>
    <li><b>Slide Sorter</b> — Opens a dialog showing all slides as a sortable list.
    Drag and drop to rearrange slide order, then click OK to apply.</li>
    <li><b>Copy LLM Instructions</b> — Copies the slide format guide to your clipboard.
    Paste it into any AI assistant (ChatGPT, Claude, Gemini, etc.) to generate
    slides in the correct format, then paste the AI output into the Full Markdown
    panel (Ctrl+M) or use File &rarr; Load from Code (Ctrl+Shift+O).</li>
    <li><b>Check All Slides</b> — Scans every slide for content overflow at
    presentation size (1920&times;1080).</li>
    <li><b>Present</b> — Starts fullscreen presentation mode (F5).</li>
    </ul>

    <h2>Slide format</h2>
    <p>Slides are separated by <code>slide#</code> on its own line (blank lines before
    and after). Use standard markdown: headings, bold, lists, tables, code blocks,
    blockquotes, links, images.</p>

    <h3>Speaker notes</h3>
    <p>Add <code>notes:</code> on its own line within a slide. Everything below it
    becomes speaker notes, visible in Presenter Mode (Shift+F5) and exported to
    PowerPoint.</p>

    <h3>Per-slide theme override</h3>
    <p>Add a comment on the first line of any slide to override the global theme:<br>
    <code>&lt;!-- theme: bg=#1a1a2e text=#eee heading=#e94560 --&gt;</code></p>

    <h2>File and export</h2>
    <ul>
    <li><b>File &rarr; Load from File</b> (Ctrl+O) — Open a .md or .txt file.</li>
    <li><b>File &rarr; Load from Code</b> (Ctrl+Shift+O) — Paste raw markdown.</li>
    <li><b>File &rarr; Save to File</b> (Ctrl+S) — Save all slides as one markdown file.</li>
    <li><b>File &rarr; Export to PowerPoint</b> (Ctrl+Shift+E) — Export slides as .pptx.</li>
    </ul>

    <h2>View and presentation</h2>
    <ul>
    <li><b>View &rarr; Toggle Editor Panel</b> (Ctrl+E) — Show/hide the left editor.</li>
    <li><b>View &rarr; Toggle Style Panel</b> (Ctrl+T) — Show/hide the right theme/navigator.</li>
    <li><b>View &rarr; Toggle Markdown Panel</b> (Ctrl+M) — Show/hide full markdown.</li>
    <li><b>View &rarr; Presentation Mode</b> (F5) — Fullscreen slides; arrow keys,
    click, or Space to advance. Esc to exit.</li>
    <li><b>View &rarr; Presenter Mode</b> (Shift+F5) — Fullscreen with speaker notes,
    next slide preview, and a presentation timer.</li>
    </ul>

    <h2>Overflow check</h2>
    <p>Slides are checked at <b>presentation size</b> (1920&times;1080). If content would
    require scrolling in presentation mode, a warning appears in the toolbar and the
    slide is marked in the navigator. Use <b>Check All Slides</b> to scan the whole
    deck. Fix overflow by shortening text, reducing list items, or splitting content
    across slides.</p>

    <h2>Keyboard shortcuts</h2>
    <table border="1" cellpadding="4" cellspacing="0" style="border-collapse: collapse;">
    <tr><th>Shortcut</th><th>Action</th></tr>
    <tr><td>Ctrl+O</td><td>Load from File</td></tr>
    <tr><td>Ctrl+Shift+O</td><td>Load from Code</td></tr>
    <tr><td>Ctrl+S</td><td>Save to File</td></tr>
    <tr><td>Ctrl+Shift+E</td><td>Export to PowerPoint</td></tr>
    <tr><td>Ctrl+E</td><td>Toggle Editor Panel</td></tr>
    <tr><td>Ctrl+T</td><td>Toggle Style Panel</td></tr>
    <tr><td>Ctrl+M</td><td>Toggle Markdown Panel</td></tr>
    <tr><td>Ctrl+F</td><td>Find/Replace (in Full Markdown panel)</td></tr>
    <tr><td>F5</td><td>Presentation Mode</td></tr>
    <tr><td>Shift+F5</td><td>Presenter Mode (with notes)</td></tr>
    <tr><td>F1</td><td>User Guide</td></tr>
    <tr><td>Left / Up</td><td>Previous slide</td></tr>
    <tr><td>Right / Down</td><td>Next slide</td></tr>
    <tr><td>Space</td><td>Next slide (presentation mode)</td></tr>
    <tr><td>Esc</td><td>Exit presentation / presenter mode</td></tr>
    </table>
    """

    # -- Auto-save & recent files -------------------------------------------

    def _autosave(self):
        if self._current_file:
            try:
                with open(self._current_file, "w", encoding="utf-8") as f:
                    f.write(self.slide_data.joined())
            except Exception:
                pass

    def _add_recent_file(self, path: str):
        recent = self._settings.value("recent_files", []) or []
        if isinstance(recent, str):
            recent = [recent]
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._settings.setValue("recent_files", recent[:10])
        self._populate_recent_menu()

    def _populate_recent_menu(self):
        self._recent_menu.clear()
        recent = self._settings.value("recent_files", []) or []
        if isinstance(recent, str):
            recent = [recent]
        if not recent:
            action = self._recent_menu.addAction("(no recent files)")
            action.setEnabled(False)
            return
        for path in recent:
            action = self._recent_menu.addAction(Path(path).name)
            action.setToolTip(path)
            action.triggered.connect(lambda checked, p=path: self._load_file_path(p))

    def _load_file_path(self, path: str):
        if not Path(path).exists():
            QMessageBox.warning(self, "File Not Found", f"Cannot find:\n{path}")
            return
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self._load_markdown(content)
            self._current_file = path
            self._working_dir = Path(path).parent
            self._scan_image_counter()
            self._update_title()
            self._add_recent_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Error Loading File", str(exc))

    # -- Presenter mode -----------------------------------------------------

    def _start_presenter(self):
        if self._presenter_window is not None:
            self._presenter_window.close()
        self.hide()
        base_url = QUrl.fromLocalFile(str(self._working_dir) + "/")
        self._presenter_window = PresenterWindow(
            self.renderer, self.style_settings, self.slide_data,
            base_url=base_url, parent=None,
        )
        self._presenter_window.closed.connect(self._on_presenter_closed)

    def _on_presenter_closed(self):
        self._presenter_window = None
        self.show()
        self.raise_()
        self.activateWindow()
        self._sync_ui()

    # -- Close event (unsaved changes prompt) --------------------------------

    def _cleanup_temp_dir(self):
        """Remove the initial temp directory if it still exists."""
        d = getattr(self, "_initial_temp_dir", None)
        if d and d.exists() and str(d).startswith(tempfile.gettempdir()):
            shutil.rmtree(d, ignore_errors=True)

    def closeEvent(self, event):
        self._cleanup_temp_dir()
        if not self._dirty:
            event.accept()
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Unsaved Changes")
        msg.setText("You have unsaved changes.")
        msg.setInformativeText("Do you want to save before closing?")
        save_btn = msg.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        save_as_btn = msg.addButton("Save As...", QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(save_btn)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked is save_btn:
            if self._current_file:
                try:
                    with open(self._current_file, "w", encoding="utf-8") as f:
                        f.write(self.slide_data.joined())
                    event.accept()
                except Exception as exc:
                    QMessageBox.critical(self, "Error Saving File", str(exc))
                    event.ignore()
            else:
                self._save_to_file()
                if self._dirty:
                    event.ignore()
                else:
                    event.accept()
        elif clicked is save_as_btn:
            self._save_to_file()
            if self._dirty:
                event.ignore()
            else:
                event.accept()
        elif clicked is discard_btn:
            event.accept()
        else:
            event.ignore()

    # -- Per-slide theme editor ---------------------------------------------

    def _edit_slide_theme(self):
        from PyQt6.QtWidgets import QInputDialog

        md = self.slide_data.current_markdown
        existing = {}
        m = _THEME_COMMENT_RE.search(md)
        if m:
            for key, val in re.findall(r"(\w+)=([^\s]+)", m.group(1)):
                existing[key] = val

        items = ["bg", "text", "heading", "accent"]
        labels = {"bg": "Background", "text": "Text Color",
                  "heading": "Heading Color", "accent": "Accent Color"}

        key, ok = QInputDialog.getItem(
            self, "Slide Theme Override",
            "Which property to override for this slide?",
            [f"{labels[k]} ({existing.get(k, 'not set')})" for k in items],
            0, False,
        )
        if not ok:
            return
        chosen = items[[f"{labels[k]} ({existing.get(k, 'not set')})" for k in items].index(key)]

        current_val = existing.get(chosen, "#ffffff")
        color = QColorDialog.getColor(QColor(current_val), self, f"Pick {labels[chosen]}")
        if not color.isValid():
            return

        existing[chosen] = color.name()
        comment = "<!-- theme: " + " ".join(f"{k}={v}" for k, v in existing.items()) + " -->"

        if m:
            new_md = md[:m.start()] + comment + md[m.end():]
        else:
            new_md = comment + "\n" + md

        self.slide_data.current_markdown = new_md
        self.editor_panel.set_text(new_md)
        self._render_current_slide()
        self._update_markdown_panel()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Slide Viewer")
    app.setOrganizationName("SlideViewer")

    window = SlideViewerApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
