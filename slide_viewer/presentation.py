"""Fullscreen presentation and presenter-view windows."""

import time

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QShortcut
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from .constants import _TRANSITION_CSS
from .models import SlideData, StyleSettings
from .renderer import MarkdownRenderer


class PresentationWindow(QMainWindow):
    """Fullscreen frameless window for presenting slides. Esc to exit."""

    closed = pyqtSignal()

    def __init__(self, renderer: MarkdownRenderer, style: StyleSettings,
                 slide_data: SlideData, base_url: QUrl = None, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        self.renderer = renderer
        self.style = style
        self.slide_data = slide_data
        self._base_url = base_url or QUrl("about:blank")

        self.web_view = QWebEngineView()
        self.web_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCentralWidget(self.web_view)

        QShortcut(Qt.Key.Key_Escape, self).activated.connect(self.close)
        QShortcut(Qt.Key.Key_Right, self).activated.connect(self._next)
        QShortcut(Qt.Key.Key_Down, self).activated.connect(self._next)
        QShortcut(Qt.Key.Key_Space, self).activated.connect(self._next)
        QShortcut(Qt.Key.Key_Left, self).activated.connect(self._prev)
        QShortcut(Qt.Key.Key_Up, self).activated.connect(self._prev)

        self.showFullScreen()
        self.setFocus()
        self._render()

    def _render(self):
        html = self.renderer.render(
            self.slide_data.content_for_render(),
            self.style,
            presentation=True,
            slide_number=self.slide_data.current_index + 1,
            slide_total=self.slide_data.total,
        )
        transition = self.style.transition
        if transition in _TRANSITION_CSS:
            html = html.replace("</style>", _TRANSITION_CSS[transition] + "\n</style>")
        self.web_view.page().setHtml(html, self._base_url)

    def _next(self):
        if self.slide_data.current_index < self.slide_data.total - 1:
            self.slide_data.current_index += 1
            self._render()

    def _prev(self):
        if self.slide_data.current_index > 0:
            self.slide_data.current_index -= 1
            self._render()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


class PresenterWindow(QMainWindow):
    """Fullscreen presenter view: current slide, notes, next slide, timer."""

    closed = pyqtSignal()

    def __init__(self, renderer: MarkdownRenderer, style: StyleSettings,
                 slide_data: SlideData, base_url: QUrl = None, parent=None):
        super().__init__(parent)
        self.renderer = renderer
        self.style = style
        self.slide_data = slide_data
        self._base_url = base_url or QUrl("about:blank")
        self._start_time = time.time()

        self.setWindowTitle("Presenter View")

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        self.current_view = QWebEngineView()
        self.current_view.setMinimumWidth(500)
        root.addWidget(self.current_view, 3)

        right = QVBoxLayout()
        right.setSpacing(8)

        notes_label = QLabel("Speaker Notes")
        notes_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right.addWidget(notes_label)

        self.notes_display = QPlainTextEdit()
        self.notes_display.setReadOnly(True)
        self.notes_display.setFont(QFont("Arial", 14))
        self.notes_display.setStyleSheet(
            "QPlainTextEdit { background: #2b2b3c; color: #e0e0e0; "
            "border: 1px solid #555; border-radius: 6px; padding: 10px; }"
        )
        right.addWidget(self.notes_display, 3)

        next_label = QLabel("Next Slide")
        next_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        right.addWidget(next_label)

        self.next_view = QWebEngineView()
        self.next_view.setMaximumHeight(250)
        right.addWidget(self.next_view, 2)

        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #888; padding: 4px;"
        )
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.timer_label)

        root.addLayout(right, 2)

        QShortcut(Qt.Key.Key_Escape, self).activated.connect(self.close)
        QShortcut(Qt.Key.Key_Right, self).activated.connect(self._next)
        QShortcut(Qt.Key.Key_Down, self).activated.connect(self._next)
        QShortcut(Qt.Key.Key_Space, self).activated.connect(self._next)
        QShortcut(Qt.Key.Key_Left, self).activated.connect(self._prev)
        QShortcut(Qt.Key.Key_Up, self).activated.connect(self._prev)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_timer)
        self._timer.start(1000)

        self.showFullScreen()
        self.setFocus()
        self._render()

    def _render(self):
        idx = self.slide_data.current_index
        html = self.renderer.render(
            self.slide_data.content_for_render(idx), self.style,
            presentation=True,
            slide_number=idx + 1, slide_total=self.slide_data.total,
        )
        self.current_view.page().setHtml(html, self._base_url)
        self.notes_display.setPlainText(self.slide_data.note_for(idx))

        nxt = idx + 1
        if nxt < self.slide_data.total:
            next_html = self.renderer.render(
                self.slide_data.content_for_render(nxt), self.style,
                presentation=True,
                slide_number=nxt + 1, slide_total=self.slide_data.total,
            )
            self.next_view.page().setHtml(next_html, self._base_url)
        else:
            self.next_view.setHtml("<html><body style='background:#222;color:#888;"
                                   "display:flex;align-items:center;justify-content:center;"
                                   "height:100vh;font-family:sans-serif;'>"
                                   "<h2>End of presentation</h2></body></html>")

    def _next(self):
        if self.slide_data.current_index < self.slide_data.total - 1:
            self.slide_data.current_index += 1
            self._render()

    def _prev(self):
        if self.slide_data.current_index > 0:
            self.slide_data.current_index -= 1
            self._render()

    def _update_timer(self):
        elapsed = int(time.time() - self._start_time)
        mins, secs = divmod(elapsed, 60)
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def closeEvent(self, event):
        self._timer.stop()
        self.closed.emit()
        super().closeEvent(event)
