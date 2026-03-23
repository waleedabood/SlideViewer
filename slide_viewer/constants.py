"""Shared constants, templates, and regex patterns used across the package."""

SLIDE_DELIMITER = "slide#"

DEFAULT_MARKDOWN = r"""# Welcome to Slide Viewer
### A Markdown-Powered Presentation Tool

slide#

## Features

- ✅ Full markdown rendering
- ✅ Live editor with real-time preview
- ✅ AI assistant powered by GPT-4o-mini
- ✅ Customizable themes
- ✅ Load & save `.md` files

slide#

## Getting Started

1. **Load a file** — File → Load from File
2. **Paste markdown** — File → Load from Code
3. **Edit** — Use the left panel editor
4. **Ask AI** — Type in the AI chat below

slide#

## Table Example

| Feature | Status | Notes |
|---------|--------|-------|
| Rendering | ✅ Active | Full markdown support |
| AI Chat | ✅ Active | Requires OpenAI API key |
| Themes | ✅ Active | 5 built-in presets |

slide#

## Code Example

```python
def hello_world():
    print("Hello from Slide Viewer!")
    return "slides are fun"
```

slide#

# Thank You

> Start creating your presentation by editing slides on the left panel or asking the AI assistant for help.
"""

PRESET_THEMES = {
    "Default Light": {
        "bg_color": "#ffffff",
        "text_color": "#1a1a2e",
        "heading_color": "#16213e",
        "accent_color": "#0f3460",
    },
    "Dark Pro": {
        "bg_color": "#1a1a2e",
        "text_color": "#eaeaea",
        "heading_color": "#e94560",
        "accent_color": "#e94560",
    },
    "Academic": {
        "bg_color": "#f5f0e8",
        "text_color": "#2c2c2c",
        "heading_color": "#8b1a1a",
        "accent_color": "#8b1a1a",
    },
    "Minimal": {
        "bg_color": "#fafafa",
        "text_color": "#333333",
        "heading_color": "#333333",
        "accent_color": "#999999",
    },
    "Ocean": {
        "bg_color": "#0d2137",
        "text_color": "#c8dde8",
        "heading_color": "#48a9a6",
        "accent_color": "#48a9a6",
    },
}

FONT_OPTIONS = [
    "Arial",
    "Georgia",
    "Times New Roman",
    "Courier New",
    "Verdana",
    "Trebuchet MS",
    "Palatino",
    "Helvetica",
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{csp_policy}">
<style>
  :root {{
    --bg-color: {bg_color};
    --text-color: {text_color};
    --accent-color: {accent_color};
    --font-family: {font_family};
    --font-size: {font_size};
    --heading-color: {heading_color};
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: 100%; height: 100%; overflow: hidden; }}
  body {{
    background: {viewport_bg};
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: var(--font-family);
  }}
  .slide-frame {{
    width: {slide_width};
    height: {slide_height};
    max-width: 100vw;
    max-height: 100vh;
    background: var(--bg-color);
    color: var(--text-color);
    font-size: var(--font-size);
    line-height: 1.6;
    padding: {frame_padding};
    overflow: auto;
    display: flex;
    align-items: {frame_align};
    justify-content: center;
    {slide_shadow}
  }}
  .slide-content {{ width: 100%; overflow: auto; }}
  h1 {{ color: var(--heading-color); font-size: 2.4em; margin-bottom: 0.5em;
        border-bottom: 3px solid var(--accent-color); padding-bottom: 0.2em; }}
  h2 {{ color: var(--heading-color); font-size: 1.9em; margin-bottom: 0.4em; }}
  h3 {{ color: var(--heading-color); font-size: 1.5em; margin-bottom: 0.3em; }}
  h4, h5, h6 {{ color: var(--heading-color); margin-bottom: 0.3em; }}
  p {{ margin: 0.6em 0; }}
  a {{ color: var(--accent-color); }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th {{ background: var(--accent-color); color: white; padding: 10px 14px; text-align: left; }}
  td {{ border: 1px solid #ccc; padding: 8px 14px; }}
  tr:nth-child(even) {{ background: rgba(0,0,0,0.05); }}
  .layout-table-right {{
    float: right; width: 48%; margin: 0 0 0.8em 1em; clear: right;
  }}
  .layout-table-left {{
    float: left; width: 48%; margin: 0 1em 0.8em 0; clear: left;
  }}
  .layout-table-right table, .layout-table-left table {{
    width: 100%; font-size: 0.85em;
  }}
  blockquote {{ border-left: 4px solid var(--accent-color); padding: 0.5em 1em;
                opacity: 0.85; margin: 1em 0; font-style: italic; }}
  code {{ background: rgba(0,0,0,0.08); padding: 2px 6px; border-radius: 4px;
          font-family: 'Courier New', monospace; }}
  pre {{ background: #1e1e1e; color: #d4d4d4; padding: 1em; border-radius: 8px;
         overflow-x: auto; margin: 1em 0; }}
  pre code {{ background: none; padding: 0; color: inherit; }}
  ul, ol {{ padding-left: 2em; margin: 0.5em 0; }}
  li {{ margin: 0.3em 0; }}
  hr {{ border: none; border-top: 2px solid var(--accent-color); margin: 1.5em 0; }}
  img {{ max-width: 90%; border-radius: 8px; border: 1px solid rgba(0,0,0,0.12);
         padding: 4px; display: block; margin: 1em auto;
         box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .layout-img-right {{
    float: right; width: 48%; margin: 0 0 0.8em 1em; clear: right;
  }}
  .layout-img-left {{
    float: left; width: 48%; margin: 0 1em 0.8em 0; clear: left;
  }}
  .layout-img-right img, .layout-img-left img {{
    width: 100%; max-width: 100%; border-radius: 8px; object-fit: cover;
    margin: 0; padding: 0; border: none; box-shadow: none; display: block;
  }}
  .layout-img-right p, .layout-img-left p {{
    text-align: center; opacity: 0.85; font-size: 0.85em; margin-top: 0.4em;
  }}
  .layout-img-full {{
    display: flex; flex-direction: column; align-items: center; width: 100%;
  }}
  .layout-img-full img {{
    width: 100%; max-width: 100%; object-fit: contain;
    border-radius: 8px; margin: 0 auto 0.5em auto;
  }}
  .layout-img-full p {{ text-align: center; opacity: 0.85; font-size: 0.9em; }}
  .layout-cols {{
    display: flex; gap: 2em; width: 100%; margin: 0.8em 0;
  }}
  .layout-cols > .col {{
    flex: 1; min-width: 0;
  }}
  .layout-cols > .col > *:first-child {{ margin-top: 0; }}
  .slide-counter {{
    position: fixed; bottom: 12px; right: 20px;
    font-size: 13px; color: rgba(128,128,128,0.6);
    font-family: var(--font-family);
    {counter_display}
  }}
  {pygments_css}
  {extra_css}
</style>
</head>
<body>
  <div class="slide-frame">
    <div class="slide-content">
      {content}
    </div>
  </div>
  <div class="slide-counter">{slide_counter}</div>
  {drag_resize_js}
</body>
</html>"""

NOTES_DELIMITER = "notes:"

_TRANSITION_CSS = {
    "fade": (
        "@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }"
        ".slide-frame { animation: fadeIn 0.4s ease; }"
    ),
    "slide-left": (
        "@keyframes slideLeft { from { transform: translateX(100%); } to { transform: translateX(0); } }"
        ".slide-frame { animation: slideLeft 0.4s ease; }"
    ),
    "slide-right": (
        "@keyframes slideRight { from { transform: translateX(-100%); } to { transform: translateX(0); } }"
        ".slide-frame { animation: slideRight 0.4s ease; }"
    ),
    "zoom": (
        "@keyframes zoomIn { from { transform: scale(0.85); opacity: 0; } to { transform: scale(1); opacity: 1; } }"
        ".slide-frame { animation: zoomIn 0.4s ease; }"
    ),
}

DRAG_RESIZE_JS = """<style>
.sv-manipulable { cursor: move; }
.sv-manipulable:hover { outline: 2px dashed rgba(74,158,255,0.5); outline-offset: 2px; }
.sv-manipulable.sv-selected { outline: 2px solid #4a9eff; outline-offset: 2px; }
.sv-handle {
  position: absolute; width: 10px; height: 10px;
  background: #4a9eff; border: 1px solid #fff; border-radius: 2px;
  z-index: 1000; pointer-events: auto;
}
.sv-handle-tl { top: -5px; left: -5px; cursor: nw-resize; }
.sv-handle-tr { top: -5px; right: -5px; cursor: ne-resize; }
.sv-handle-bl { bottom: -5px; left: -5px; cursor: sw-resize; }
.sv-handle-br { bottom: -5px; right: -5px; cursor: se-resize; }
</style>
<script>
(function() {
  var selected = null;
  var handles = [];
  var dragging = false;
  var resizing = false;
  var startX, startY, startLeft, startTop, startWidth;
  var activeHandle = null;

  function getFrame() {
    return document.querySelector('.slide-frame');
  }

  function parsePercent(val) {
    if (!val) return 0;
    var m = val.match(/(-?[\\d.]+)%/);
    return m ? parseFloat(m[1]) : 0;
  }

  function getContainerForImg(img) {
    var p = img.parentElement;
    if (p && p.classList &&
        (p.classList.contains('layout-img-right') ||
         p.classList.contains('layout-img-left') ||
         p.classList.contains('layout-img-full'))) {
      return p;
    }
    return null;
  }

  function getAllManipulables() {
    var items = [];
    var divs = document.querySelectorAll('.layout-img-right, .layout-img-left, .layout-img-full');
    divs.forEach(function(d) {
      if (!d.closest('.layout-cols')) {
        d.classList.add('sv-manipulable');
        d.style.position = 'relative';
        items.push(d);
      }
    });
    var imgs = document.querySelectorAll('.slide-content img');
    imgs.forEach(function(img) {
      if (!getContainerForImg(img) && !img.closest('.layout-cols')) {
        img.classList.add('sv-manipulable');
        img.style.position = 'relative';
        items.push(img);
      }
    });
    return items;
  }

  function getImgSrc(el) {
    var img = el.tagName === 'IMG' ? el : el.querySelector('img');
    return img ? img.getAttribute('src') : '';
  }

  function getImgIndex(el) {
    var src = getImgSrc(el);
    var all = document.querySelectorAll('.slide-content img');
    var idx = 0;
    for (var i = 0; i < all.length; i++) {
      if (all[i].getAttribute('src') === src) {
        var container = getContainerForImg(all[i]);
        var target = container || all[i];
        if (target === el) return idx;
        idx++;
      }
    }
    return 0;
  }

  function removeHandles() {
    handles.forEach(function(h) { h.remove(); });
    handles = [];
    if (selected) selected.classList.remove('sv-selected');
    selected = null;
  }

  function createHandles(el) {
    removeHandles();
    selected = el;
    el.classList.add('sv-selected');
    var positions = ['tl', 'tr', 'bl', 'br'];
    positions.forEach(function(pos) {
      var h = document.createElement('div');
      h.className = 'sv-handle sv-handle-' + pos;
      h.dataset.pos = pos;
      el.appendChild(h);
      handles.push(h);
      h.addEventListener('mousedown', onResizeStart);
    });
  }

  function sendUpdate(el) {
    var frame = getFrame();
    if (!frame) return;
    var frameRect = frame.getBoundingClientRect();
    var src = getImgSrc(el);
    var idx = getImgIndex(el);
    var w = parsePercent(el.style.width);
    var l = parsePercent(el.style.left);
    var mt = parsePercent(el.style.marginTop);
    if (w === 0) {
      var elRect = el.getBoundingClientRect();
      w = Math.round(elRect.width / frameRect.width * 100);
    }
    var msg = {
      src: src,
      index: idx,
      width: Math.round(w),
      left: Math.round(l),
      marginTop: Math.round(mt)
    };
    console.log('SLIDEVIEWER_IMG:' + JSON.stringify(msg));
  }

  function onDragStart(e) {
    if (e.target.classList.contains('sv-handle')) return;
    var el = e.currentTarget;
    e.preventDefault();
    e.stopPropagation();
    dragging = true;
    selected = el;
    startX = e.clientX;
    startY = e.clientY;
    startLeft = parsePercent(el.style.left);
    startTop = parsePercent(el.style.marginTop);
    createHandles(el);
    document.addEventListener('mousemove', onDragMove);
    document.addEventListener('mouseup', onDragEnd);
  }

  function onDragMove(e) {
    if (!dragging || !selected) return;
    e.preventDefault();
    var frame = getFrame();
    var frameRect = frame.getBoundingClientRect();
    var dx = (e.clientX - startX) / frameRect.width * 100;
    var dy = (e.clientY - startY) / frameRect.height * 100;
    selected.style.left = (startLeft + dx) + '%';
    selected.style.marginTop = (startTop + dy) + '%';
  }

  function onDragEnd(e) {
    if (!dragging || !selected) return;
    dragging = false;
    document.removeEventListener('mousemove', onDragMove);
    document.removeEventListener('mouseup', onDragEnd);
    sendUpdate(selected);
  }

  function onResizeStart(e) {
    e.preventDefault();
    e.stopPropagation();
    resizing = true;
    activeHandle = e.target.dataset.pos;
    var el = e.target.parentElement;
    selected = el;
    startX = e.clientX;
    startWidth = parsePercent(el.style.width);
    if (startWidth === 0) {
      var frame = getFrame();
      var frameRect = frame.getBoundingClientRect();
      startWidth = el.getBoundingClientRect().width / frameRect.width * 100;
    }
    document.addEventListener('mousemove', onResizeMove);
    document.addEventListener('mouseup', onResizeEnd);
  }

  function onResizeMove(e) {
    if (!resizing || !selected) return;
    e.preventDefault();
    var frame = getFrame();
    var frameRect = frame.getBoundingClientRect();
    var dx = (e.clientX - startX) / frameRect.width * 100;
    var newWidth;
    if (activeHandle === 'tr' || activeHandle === 'br') {
      newWidth = startWidth + dx;
    } else {
      newWidth = startWidth - dx;
    }
    newWidth = Math.max(10, Math.min(100, newWidth));
    selected.style.width = newWidth + '%';
    // Force layout recalc so surrounding text reflows
    void selected.offsetHeight;
  }

  function onResizeEnd(e) {
    if (!resizing || !selected) return;
    resizing = false;
    activeHandle = null;
    document.removeEventListener('mousemove', onResizeMove);
    document.removeEventListener('mouseup', onResizeEnd);
    sendUpdate(selected);
  }

  document.addEventListener('DOMContentLoaded', function() {
    var items = getAllManipulables();
    items.forEach(function(el) {
      el.addEventListener('mousedown', onDragStart);
    });
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.sv-manipulable') && !e.target.classList.contains('sv-handle')) {
        removeHandles();
      }
    });
  });
})();
</script>"""
