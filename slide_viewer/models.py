"""Data classes for slide content and style settings."""

import re
from copy import copy
from dataclasses import dataclass, field

from .constants import NOTES_DELIMITER, SLIDE_DELIMITER

_DANGEROUS_CSS_RE = re.compile(
    r"expression\s*\(|javascript\s*:|behavior\s*:|"
    r"-moz-binding\s*:|@import\b",
    re.IGNORECASE,
)
_GRADIENT_RE = re.compile(
    r"^(linear|radial|conic|repeating-linear|repeating-radial|repeating-conic)-gradient\(",
    re.IGNORECASE,
)


def _sanitize_css_bg(value: str, kind: str) -> str:
    """Return *value* if it looks safe for use in CSS, else empty string."""
    if _DANGEROUS_CSS_RE.search(value):
        return ""
    if kind == "gradient":
        if not _GRADIENT_RE.match(value.strip()):
            return ""
    elif kind == "image":
        v = value.strip()
        # Allow file paths, data: URIs, and http(s) URLs
        if not (
            v.startswith("/")
            or v.startswith("data:")
            or v.startswith("http://")
            or v.startswith("https://")
            or v.startswith("file://")
        ):
            return ""
    return value


@dataclass
class StyleSettings:
    """Holds all visual settings for the slide theme."""

    bg_color: str = "#ffffff"
    text_color: str = "#1a1a2e"
    heading_color: str = "#16213e"
    accent_color: str = "#0f3460"
    font_family: str = "Arial"
    font_size: int = 18
    bg_type: str = "solid"
    bg_value: str = ""
    transition: str = "none"

    def bg_css(self) -> str:
        if self.bg_type == "gradient" and self.bg_value:
            val = _sanitize_css_bg(self.bg_value, "gradient")
            return val if val else self.bg_color
        if self.bg_type == "image" and self.bg_value:
            val = _sanitize_css_bg(self.bg_value, "image")
            return f"url({val}) center/cover no-repeat" if val else self.bg_color
        return self.bg_color


@dataclass
class SlideData:
    """Holds the list of slide markdown strings and current index."""

    slides: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    current_index: int = 0

    @property
    def total(self) -> int:
        return len(self.slides)

    @property
    def current_markdown(self) -> str:
        if 0 <= self.current_index < self.total:
            return self.slides[self.current_index]
        return ""

    @current_markdown.setter
    def current_markdown(self, value: str):
        if 0 <= self.current_index < self.total:
            self.slides[self.current_index] = value

    @property
    def current_note(self) -> str:
        if 0 <= self.current_index < len(self.notes):
            return self.notes[self.current_index]
        return ""

    @current_note.setter
    def current_note(self, value: str):
        while len(self.notes) < self.total:
            self.notes.append("")
        if 0 <= self.current_index < len(self.notes):
            self.notes[self.current_index] = value

    def content_for_render(self, index: int | None = None) -> str:
        """Return only the slide content (without notes) for rendering."""
        idx = index if index is not None else self.current_index
        if 0 <= idx < self.total:
            md = self.slides[idx]
            if f"\n{NOTES_DELIMITER}\n" in md:
                return md.split(f"\n{NOTES_DELIMITER}\n", 1)[0]
            if md.startswith(f"{NOTES_DELIMITER}\n"):
                return ""
            return md
        return ""

    def note_for(self, index: int | None = None) -> str:
        idx = index if index is not None else self.current_index
        if 0 <= idx < self.total:
            md = self.slides[idx]
            if f"\n{NOTES_DELIMITER}\n" in md:
                return md.split(f"\n{NOTES_DELIMITER}\n", 1)[1]
        return ""

    def joined(self) -> str:
        return f"\n\n{SLIDE_DELIMITER}\n\n".join(self.slides)


# ---------------------------------------------------------------------------
# Per-slide theme parsing
# ---------------------------------------------------------------------------

_THEME_COMMENT_RE = re.compile(
    r"<!--\s*theme:\s*(.*?)\s*-->", re.DOTALL
)


def _parse_slide_theme(md_text: str, base: StyleSettings) -> tuple[str, StyleSettings]:
    """Strip per-slide <!-- theme: ... --> comment and return (cleaned md, merged style)."""
    m = _THEME_COMMENT_RE.search(md_text)
    if not m:
        return md_text, base
    style = copy(base)
    cleaned = md_text[: m.start()] + md_text[m.end() :]
    pairs = re.findall(r"(\w+)=([^\s]+)", m.group(1))
    _map = {"bg": "bg_color", "text": "text_color", "heading": "heading_color",
            "accent": "accent_color", "font": "font_family", "size": "font_size"}
    for key, val in pairs:
        attr = _map.get(key)
        if attr == "font_size":
            style.font_size = int(val)
        elif attr:
            setattr(style, attr, val)
        elif key == "bg_type":
            style.bg_type = val
        elif key == "bg_value":
            style.bg_value = val
    return cleaned.strip(), style
