"""Lightweight HTML sanitizer for slide content.

Strips dangerous tags and attributes while preserving the layout HTML
that Slide Viewer uses for image/table/column positioning.
"""

import re

# Tags allowed in slide HTML output
_ALLOWED_TAGS = frozenset({
    "div", "img", "p", "span", "br", "hr", "em", "strong", "b", "i", "u",
    "a", "ul", "ol", "li", "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "pre", "code", "blockquote",
    "sup", "sub", "del", "abbr", "small",
    "dl", "dt", "dd", "caption", "colgroup", "col",
})

# Attributes allowed per tag (tag -> frozenset of attr names)
_ALLOWED_ATTRS: dict[str, frozenset[str]] = {
    "div": frozenset({"class", "style"}),
    "img": frozenset({"src", "alt", "width", "height", "style", "class"}),
    "span": frozenset({"style", "class"}),
    "a": frozenset({"href", "title", "target", "class"}),
    "p": frozenset({"style", "class"}),
    "td": frozenset({"style", "align", "colspan", "rowspan", "class"}),
    "th": frozenset({"style", "align", "colspan", "rowspan", "class"}),
    "code": frozenset({"class"}),
    "pre": frozenset({"class"}),
    "table": frozenset({"class", "style"}),
    "col": frozenset({"style", "span"}),
    "colgroup": frozenset({"span"}),
    "blockquote": frozenset({"class"}),
    "ol": frozenset({"start", "type"}),
}

# Tags that must be removed entirely (including their content)
_STRIP_TAGS = frozenset({
    "script", "iframe", "object", "embed", "form", "input",
    "textarea", "select", "button", "link", "meta", "style",
    "applet", "base", "frame", "frameset",
})

# Regex for stripping dangerous tags and their content
_STRIP_TAG_RE = re.compile(
    r"<\s*(" + "|".join(_STRIP_TAGS) + r")\b[^>]*>.*?</\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)

# Also catch self-closing dangerous tags
_STRIP_SELF_CLOSING_RE = re.compile(
    r"<\s*(" + "|".join(_STRIP_TAGS) + r")\b[^>]*/?\s*>",
    re.IGNORECASE,
)

# Regex matching on* event handler attributes
_EVENT_ATTR_RE = re.compile(
    r"""\s+on\w+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""",
    re.IGNORECASE,
)

# Regex for javascript: in href/src values
_JS_URI_RE = re.compile(
    r"""((?:href|src)\s*=\s*(?:"|'))(\s*javascript\s*:)""",
    re.IGNORECASE,
)

# Match opening tags to filter attributes
_OPEN_TAG_RE = re.compile(r"<(\w+)(\s[^>]*)?>", re.DOTALL)

# Match individual attributes
_ATTR_RE = re.compile(
    r"""(\w[\w-]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|(\S+))|(\w[\w-]*)""",
)


def _filter_attrs(tag: str, attr_string: str) -> str:
    """Keep only allowed attributes for the given tag."""
    if not attr_string or not attr_string.strip():
        return ""
    allowed = _ALLOWED_ATTRS.get(tag, frozenset())
    parts: list[str] = []
    for m in _ATTR_RE.finditer(attr_string):
        name = (m.group(1) or m.group(5) or "").lower()
        if not name:
            continue
        # Block all event handlers regardless of allowlist
        if name.startswith("on"):
            continue
        if name not in allowed:
            continue
        # Get the value
        val = m.group(2) if m.group(2) is not None else (
            m.group(3) if m.group(3) is not None else m.group(4)
        )
        if val is not None:
            # Strip javascript: from href/src
            if name in ("href", "src") and re.match(r"\s*javascript\s*:", val, re.I):
                continue
            # Strip dangerous CSS expressions from style
            if name == "style":
                val = _sanitize_style(val)
            parts.append(f'{name}="{val}"')
        else:
            parts.append(name)
    return (" " + " ".join(parts)) if parts else ""


def _sanitize_style(style: str) -> str:
    """Remove dangerous patterns from inline style values."""
    # Remove expression(), javascript:, behavior:, -moz-binding:, url() with js
    dangerous = re.compile(
        r"expression\s*\(|javascript\s*:|behavior\s*:|"
        r"-moz-binding\s*:|@import|url\s*\(\s*['\"]?\s*javascript",
        re.IGNORECASE,
    )
    if dangerous.search(style):
        return ""
    return style


def sanitize_slide_html(html: str) -> str:
    """Sanitize HTML produced by the markdown converter.

    Strips dangerous tags entirely, removes event-handler attributes,
    and filters remaining attributes to an allowlist.
    """
    # 1. Remove dangerous tags and their content
    result = _STRIP_TAG_RE.sub("", html)
    result = _STRIP_SELF_CLOSING_RE.sub("", result)

    # 2. Remove event-handler attributes everywhere
    result = _EVENT_ATTR_RE.sub("", result)

    # 3. Neutralize javascript: URIs
    result = _JS_URI_RE.sub(r"\1#blocked:", result)

    # 4. Filter attributes on allowed tags; strip unknown tags but keep content
    def _process_tag(m: re.Match) -> str:
        tag = m.group(1).lower()
        attrs = m.group(2) or ""
        if tag in _ALLOWED_TAGS:
            filtered = _filter_attrs(tag, attrs)
            return f"<{tag}{filtered}>"
        # Unknown tag: strip the tag but keep inner content
        return ""

    result = _OPEN_TAG_RE.sub(_process_tag, result)

    # Also strip closing tags for non-allowed elements
    def _process_closing(m: re.Match) -> str:
        tag = m.group(1).lower()
        return f"</{tag}>" if tag in _ALLOWED_TAGS else ""

    result = re.sub(r"</(\w+)\s*>", _process_closing, result)

    return result
