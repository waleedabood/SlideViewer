"""Markdown-to-HTML rendering engine for slides."""

import re

import markdown
from pygments.formatters import HtmlFormatter

from .constants import DRAG_RESIZE_JS, HTML_TEMPLATE
from .models import StyleSettings, _parse_slide_theme
from .sanitizer import sanitize_slide_html


class MarkdownRenderer:
    """Converts markdown text + StyleSettings into a full HTML page."""

    def __init__(self):
        self._pygments_css = HtmlFormatter(style="monokai").get_style_defs(
            ".codehilite"
        )

    def render(
        self,
        md_text: str,
        style: StyleSettings,
        presentation: bool = False,
        slide_number: int = 0,
        slide_total: int = 0,
    ) -> str:
        md_text, style = _parse_slide_theme(md_text, style)

        processed = re.sub(
            r"\n{3,}",
            lambda m: "\n\n" + "&nbsp;\n\n" * (m.group().count("\n") - 2),
            md_text,
        )
        md = markdown.Markdown(
            extensions=["extra", "codehilite", "nl2br", "toc", "sane_lists"],
            extension_configs={"codehilite": {"guess_lang": True, "linenums": False}},
        )
        html_content = sanitize_slide_html(md.convert(processed))

        bg_css = style.bg_css()

        if presentation:
            viewport_bg = bg_css
            slide_width = "100vw"
            slide_height = "100vh"
            slide_shadow = ""
            counter_display = ""
            counter_text = f"{slide_number} / {slide_total}" if slide_total else ""
            frame_padding = "10vh 6vw"
            frame_align = "flex-start"
            scale = style.font_size / 18
            font_size = f"{2.8 * scale:.2f}vw"
            extra_css = (
                "h1 { margin-bottom: 1.2vw; } "
                "h2 { margin-bottom: 1vw; } "
                "h3 { margin-bottom: 0.7vw; } "
                "p  { margin: 0.8vw 0; } "
                "ul, ol { margin: 0.8vw 0; } "
                "li { margin: 0.5vw 0; } "
                "table { margin: 1.5vw 0; } "
                "blockquote { margin: 1.5vw 0; } "
                "pre { margin: 1.5vw 0; }"
            )
        else:
            viewport_bg = "#e8e8e8"
            slide_width = "min(96%, 960px)"
            slide_height = "auto"
            slide_shadow = (
                "aspect-ratio: 16 / 9; "
                "box-shadow: 0 4px 24px rgba(0,0,0,0.15); "
                "border-radius: 6px;"
            )
            counter_display = "display: none;"
            counter_text = ""
            frame_padding = "50px 70px"
            frame_align = "flex-start"
            font_size = f"{style.font_size}px"
            extra_css = ""

        if presentation:
            csp = (
                "default-src 'none'; "
                "style-src 'unsafe-inline'; "
                "img-src data: file: https: http:;"
            )
        else:
            csp = (
                "default-src 'none'; "
                "script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; "
                "img-src data: file: https: http:;"
            )

        return HTML_TEMPLATE.format(
            csp_policy=csp,
            bg_color=bg_css,
            text_color=style.text_color,
            heading_color=style.heading_color,
            accent_color=style.accent_color,
            font_family=style.font_family,
            font_size=font_size,
            pygments_css=self._pygments_css,
            extra_css=extra_css,
            content=html_content,
            viewport_bg=viewport_bg,
            slide_width=slide_width,
            slide_height=slide_height,
            slide_shadow=slide_shadow,
            counter_display=counter_display,
            slide_counter=counter_text,
            frame_padding=frame_padding,
            frame_align=frame_align,
            drag_resize_js=DRAG_RESIZE_JS if not presentation else "",
        )
