# Slide Markdown Format Guide

> Use this guide when asking an AI (ChatGPT, Claude, Gemini, etc.) to generate
> presentation content for the Slide Viewer app.

## Quick-Start Prompt

Copy-paste this into any AI chat to get a ready-to-use slide deck:

```
Write a [NUMBER]-slide presentation about [TOPIC].
Use this exact format:
- Separate each slide with a line containing only "slide#"
- Start each slide with a heading (# or ##)
- Use bullet points, tables, code blocks, and blockquotes where appropriate
- Do NOT wrap the output in a code block — give me raw markdown only
- Do NOT include "Slide 1", "Slide 2" labels — just the content
```

## Format Rules

### Slide Delimiter

Each slide is separated by `slide#` on its own line, with blank lines above and below:

```markdown
# First Slide Title

Content for slide one.

slide#

## Second Slide Title

Content for slide two.

slide#

## Third Slide

More content here.
```

**Important:**
- The delimiter is exactly `slide#` on its own line (no leading spaces)
- Leave a blank line before and after each `slide#`
- Do NOT use `---` as a delimiter (it conflicts with markdown horizontal rules and tables)
- You CAN safely use `---` inside slides for horizontal rules or table syntax

### Headings

- Use `#` (h1) for title slides or major sections
- Use `##` (h2) for regular slide titles
- Use `###` (h3) for subtitles beneath the main heading
- Every slide should start with at least one heading

### Supported Markdown Features

| Feature | Syntax | Notes |
|---------|--------|-------|
| Bold | `**text**` | Use for emphasis |
| Italic | `*text*` | Use for subtle emphasis |
| Bullet list | `- item` | Unordered list |
| Numbered list | `1. item` | Ordered list |
| Table | `\| col \| col \|` | Include a header row |
| Code block | `` ```language `` | Syntax highlighted |
| Inline code | `` `code` `` | Inline monospace |
| Blockquote | `> text` | Great for quotes or callouts |
| Link | `[text](url)` | Clickable link |
| Image | `![alt](url)` | Embedded image |
| Horizontal rule | `---` or `***` | Safe to use inside slides |

### Tables

Tables render nicely with styled headers. Always include the alignment row:

```markdown
| Name | Role | Status |
|------|------|--------|
| Alice | Engineer | Active |
| Bob | Designer | Active |
```

### Code Blocks

Fenced code blocks get syntax highlighting. Always specify the language:

````markdown
```python
def example():
    return "highlighted code"
```
````

Supported languages: python, javascript, typescript, java, c, cpp, go, rust,
bash, sql, html, css, json, yaml, and many more.

### Blockquotes

Use for quotes, key takeaways, or callout boxes:

```markdown
> "The only way to do great work is to love what you do." — Steve Jobs
```

## Images

### Using the Insert Image Button (Recommended)

The editor has an **Insert Image** button that opens a dialog where you can:

1. Browse for a local image file (PNG, JPG, GIF, WebP, SVG)
2. Choose a layout from the dropdown
3. Enter an optional caption
4. Click OK — the formatted HTML is inserted at the cursor

The image is automatically converted to a base64 data URI so it embeds directly in the slide (no external file dependencies).

### Layout Options

| Layout | Description | CSS Class |
|--------|-------------|-----------|
| **Right half** | Image on the right, text on the left (50/50 grid) | `layout-img-right` |
| **Left half** | Image on the left, text on the right (50/50 grid) | `layout-img-left` |
| **Full with caption** | Full-width image with caption text below (~80/20 split) | `layout-img-full` |
| **Inline (centered)** | Standard markdown image, centered with a border | *(standard `![alt](url)` syntax)* |

### Manual HTML (for AI-generated slides)

If you're writing slides by hand or asking an AI, use these HTML patterns:

**Right half (image right, text left):**
```html
<div class="layout-img-right">
<img src="URL_OR_PATH">
<p>Caption or description text goes here.</p>
</div>
```

**Left half (image left, text right):**
```html
<div class="layout-img-left">
<img src="URL_OR_PATH">
<p>Caption or description text goes here.</p>
</div>
```

**Full with caption:**
```html
<div class="layout-img-full">
<img src="URL_OR_PATH">
<p>Caption text here.</p>
</div>
```

**Inline centered image:**
```markdown
![description](URL_OR_PATH)
```

> **Tip for AI prompts:** Tell the AI to use `<div class="layout-img-right">` (or left/full) for image layouts. The CSS classes are built into the Slide Viewer theme.

## Slide Design Tips

1. **One idea per slide** — don't overcrowd
2. **6 bullets max** — if you need more, split into two slides
3. **Use tables for comparisons** — they render as styled grids
4. **Code blocks stay short** — 10 lines or fewer looks best
5. **Title slide first** — start with `#` and a subtitle with `###`
6. **Thank-you slide last** — end with a closing or summary slide

## Example Prompt Templates

### For a Technical Tutorial

```
Create a 10-slide markdown presentation teaching [TOPIC].
Separate slides with "slide#" on its own line.
Include:
- A title slide
- An overview slide with bullet points
- 2-3 slides with code examples (use ```language blocks)
- A table comparing approaches/tools
- A summary slide with key takeaways
- A closing slide
Give me raw markdown only, no wrapping code block.
```

### For a Business Presentation

```
Create an 8-slide markdown presentation about [TOPIC].
Separate slides with "slide#" on its own line.
Include:
- Title slide with subtitle
- Problem statement slide
- Solution overview with bullet points
- Key metrics in a table
- Timeline or roadmap as a numbered list
- Next steps slide
- Thank-you slide with a blockquote
Give me raw markdown only, no wrapping code block.
```

### For a Lecture / Educational Deck

```
Create a 12-slide markdown presentation for a lecture on [TOPIC].
Separate slides with "slide#" on its own line.
Include:
- Title slide
- Learning objectives (bullet list)
- Core concept slides with definitions in blockquotes
- Examples with code blocks or tables
- Practice problems or discussion questions
- Summary and references
Give me raw markdown only, no wrapping code block.
```

## Full Example (5 Slides)

Below is a complete, valid slide file you can reference:

```markdown
# Project Status Update
### Q1 2026 Review

slide#

## Key Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Revenue | $1.2M | $1.35M | ✅ Exceeded |
| Users | 10,000 | 9,800 | ⚠️ Close |
| Uptime | 99.9% | 99.95% | ✅ Exceeded |

slide#

## Accomplishments

- **Launched v2.0** with redesigned dashboard
- **Reduced load time** by 40% via caching
- **Onboarded 3 enterprise clients**
- **Hired 2 senior engineers**

> "Best quarter in company history." — CTO

slide#

## Challenges

1. User acquisition slightly below target
2. Mobile app delayed by 2 weeks
3. Third-party API rate limiting issues

### Mitigations
- Increased ad spend for Q2
- Added dedicated mobile sprint team
- Implemented request queuing system

slide#

# Q2 Goals

- 🎯 Reach 15,000 active users
- 🚀 Launch mobile app (iOS + Android)
- 💰 Hit $1.5M revenue target
- 🔧 Achieve 99.99% uptime SLA

> Let's make Q2 even better.
```

## Loading into Slide Viewer

Once you have the markdown output from an AI:

1. **Copy** the raw markdown text
2. Open Slide Viewer
3. Go to **File → Load from Code**
4. **Paste** the markdown into the dialog
5. Click **OK**

Or save it as a `.md` file and use **File → Load from File**.
