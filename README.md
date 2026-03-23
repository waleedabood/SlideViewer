# Slide Viewer

A markdown-powered desktop presentation tool built with Python, PyQt6, and Chromium-based rendering.

Create, edit, and present slide decks using standard markdown. Features a live editor with real-time preview, AI assistant integration, customizable themes, and PowerPoint export.

## Features

- **Full Markdown Rendering** -- headings, bold, italic, lists, tables, code blocks with syntax highlighting, blockquotes, links, images, horizontal rules
- **Live Editor** -- real-time slide preview with syntax highlighting as you type
- **AI Assistant** -- built-in chat panel powered by OpenAI GPT-4o-mini for rewriting, improving, or generating slide content
- **5 Preset Themes** -- Default Light, Dark Pro, Academic, Minimal, Ocean -- plus full color, font, and font size customization
- **Per-Slide Theme Overrides** -- override the global theme on any slide with `<!-- theme: bg=#000 text=#fff -->` comments
- **Image Support** -- insert images with multiple layout options (right half, left half, full with caption, inline centered); drag-and-drop repositioning and resizing in the preview
- **Table & Column Editors** -- visual editors for inserting and editing tables and multi-column layouts
- **Full Markdown Panel** -- edit the entire deck as one markdown document with bidirectional sync
- **Slide Sorter** -- drag-and-drop reordering of all slides
- **Overflow Detection** -- checks if content fits the presentation size (1920x1080) and flags slides that would scroll
- **Presentation Mode** -- fullscreen slide show with arrow key / click / Space navigation
- **Presenter Mode** -- fullscreen slides with speaker notes, next slide preview, and a presentation timer
- **PowerPoint Export** -- export slides as .pptx files
- **Speaker Notes** -- add `notes:` on its own line within a slide to include speaker notes
- **Copy LLM Instructions** -- one-click copy of the slide format guide for use with any AI assistant
- **Autosave & Recent Files** -- automatic saving and quick access to recently opened files

## Installation

### Standalone macOS App (no Python needed)

1. Download **SlideViewer-macOS.zip** from the [latest release](https://github.com/waleedabood/SlideViewer/releases/latest)
2. Unzip it
3. **First launch only** — macOS will show a security warning because the app is not signed with an Apple Developer certificate. To open it:
   - **Right-click** (or Control-click) the app and select **Open**, then click **Open** in the dialog
   - Or run this in Terminal: `xattr -cr /path/to/SlideViewer.app`
4. After the first launch, it will open normally

### Install via pip

```bash
pip install slide-viewer
```

**Requirements:** Python 3.10+, PyQt6 with WebEngine support

Or from the project directory:

```bash
pip install .
```

## Usage

```bash
# As a package
python -m slide_viewer

# Or via the CLI entry point (after pip install)
slide-viewer
```

The application opens with a sample slide deck. From there you can:

- **Load a file** -- File > Load from File (Ctrl+O) supports `.md` and `.txt`
- **Paste markdown** -- File > Load from Code (Ctrl+Shift+O) to paste raw markdown
- **Edit slides** -- use the left editor panel; changes preview in real time
- **Navigate** -- Prev/Next buttons, arrow keys, or click slides in the navigator
- **Add / insert / delete slides** -- toolbar buttons for managing slides
- **Customize theme** -- right dock panel with color pickers, fonts, and preset themes
- **Save** -- File > Save to File (Ctrl+S) exports as a single `.md` file
- **Export to PowerPoint** -- File > Export to PowerPoint (Ctrl+Shift+E)
- **Present** -- F5 for presentation mode, Shift+F5 for presenter mode with notes

## Slide Format

Slides are separated by `slide#` on its own line with blank lines before and after:

```markdown
# Title Slide
### Subtitle

slide#

## Second Slide

- Bullet point one
- Bullet point two

slide#

## Third Slide

More content here.
```

### Speaker Notes

Add `notes:` on its own line within any slide. Everything below becomes speaker notes:

```markdown
## My Slide

Content visible in the presentation.

notes:

These notes are only visible in Presenter Mode and exported to PPTX.
```

### Using AI to Generate Slides

1. Click the **Copy LLM Instructions** button in the toolbar
2. Open your preferred AI assistant (ChatGPT, Claude, Gemini, etc.)
3. Paste the instructions and ask the AI to create slides on your topic
4. Copy the AI's markdown output
5. Paste into the Full Markdown panel (Ctrl+M) or use File > Load from Code (Ctrl+Shift+O)

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Load from File |
| Ctrl+Shift+O | Load from Code |
| Ctrl+S | Save to File |
| Ctrl+Shift+E | Export to PowerPoint |
| Ctrl+E | Toggle Editor Panel |
| Ctrl+T | Toggle Style Panel |
| Ctrl+M | Toggle Markdown Panel |
| Ctrl+F | Find/Replace (Full Markdown panel) |
| F5 | Presentation Mode |
| Shift+F5 | Presenter Mode (with notes) |
| F1 | User Guide |
| Left / Up | Previous slide |
| Right / Down | Next slide |
| Space | Next slide (presentation mode) |
| Esc | Exit presentation / presenter mode |

## AI Assistant

The bottom-left panel provides an AI chat powered by OpenAI's GPT-4o-mini. Enter your API key in the field at the bottom of the chat panel -- it persists between sessions.

The AI has context about your full presentation and the current slide. Ask it to rewrite, improve, or restructure slides, and use the **Replace** or **Insert** buttons to apply changes. An **Undo** button lets you revert the last AI edit.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Citation

If you use Slide Viewer in your work, please see [CITATION.cff](CITATION.cff) for citation information.
