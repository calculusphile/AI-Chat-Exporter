"""
AI Chat Exporter — Converter Module.

Handles HTML → Markdown conversion with:
  - Intelligent code-language detection (12+ languages)
  - Auto-tagging via content analysis
  - YAML frontmatter generation for Obsidian / Notion
  - Configurable export settings
"""

from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import markdownify as md

from config_loader import AppConfig, load_config

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Platform Branding Names
# ──────────────────────────────────────────────

_PLATFORM_NAMES: list[str] = [
    "Google Gemini", "Gemini", "ChatGPT", "GPT-4o", "GPT-4",
    "Claude", "Copilot", "Perplexity", "DeepSeek",
]

# ──────────────────────────────────────────────
#  Language Detection Maps
# ──────────────────────────────────────────────

# Label → canonical language name  (used in proximity search)
_LABEL_MAP: dict[str, str] = {
    "c++": "cpp", "cpp": "cpp", "c plus plus": "cpp",
    "python": "python", "py ": "python",
    "javascript": "javascript", "js ": "javascript", "js code": "javascript",
    "typescript": "typescript", "ts ": "typescript",
    "java": "java",
    "rust": "rust",
    "go ": "go", "golang": "go",
    "ruby": "ruby",
    "sql": "sql",
    "bash": "bash", "shell": "bash", "terminal": "bash",
    "html": "html",
    "css": "css",
    "c#": "csharp", "csharp": "csharp",
    "kotlin": "kotlin",
    "swift": "swift",
    "r ": "r", "r code": "r",
    "php": "php",
    "dart": "dart",
}

# Codeblock tag → canonical  (used in frontmatter auto-tagging)
_CODE_BLOCK_TAG_MAP: dict[str, str] = {
    "```python": "python", "```py": "python",
    "```cpp": "cpp", "```c++": "cpp",
    "```javascript": "javascript", "```js": "javascript",
    "```typescript": "typescript", "```ts": "typescript",
    "```java": "java",
    "```rust": "rust", "```rs": "rust",
    "```go": "go",
    "```ruby": "ruby", "```rb": "ruby",
    "```sql": "sql",
    "```bash": "bash", "```sh": "bash",
    "```html": "html",
    "```css": "css",
    "```csharp": "csharp", "```c#": "csharp",
    "```kotlin": "kotlin", "```kt": "kotlin",
    "```swift": "swift",
    "```r": "r",
    "```php": "php",
    "```dart": "dart",
}


# ──────────────────────────────────────────────
#  Result Data Model
# ──────────────────────────────────────────────

@dataclass
class ExtractionResult:
    """Holds the outcome of a single extraction attempt."""
    success: bool
    markdown: Optional[str] = None
    message: str = ""
    word_count: int = 0
    detected_languages: List[str] = field(default_factory=list)
    title: Optional[str] = None


# ──────────────────────────────────────────────
#  Internal Helpers
# ──────────────────────────────────────────────

def _load_html(filepath: Path) -> str:
    """Read an HTML file with UTF-8 encoding."""
    return filepath.read_text(encoding="utf-8")


def _auto_detect_tags(content: str) -> List[str]:
    """
    Scan markdown content and return a deduplicated list of language tags.
    Uses code-block markers AND syntax heuristics.
    """
    tags: set[str] = {"ai-chat"}
    lower = content.lower()

    # Code-block markers
    for marker, lang in _CODE_BLOCK_TAG_MAP.items():
        if marker in lower:
            tags.add(lang)

    # Syntax heuristics
    if "def " in lower and ":" in lower:
        tags.add("python")
    if "#include" in lower or "std::" in lower:
        tags.add("cpp")
    if "console.log" in lower:
        tags.add("javascript")
    if "fmt.println" in lower or "func " in lower and "go" not in tags:
        tags.add("go")
    if "fn " in lower and "let mut" in lower:
        tags.add("rust")
    if "public static void main" in lower:
        tags.add("java")

    return sorted(tags)


def generate_frontmatter(
    title: str,
    content: str,
    *,
    url: str = "Local File",
    date_format: str = "%Y-%m-%d",
) -> str:
    """
    Build YAML frontmatter block for Obsidian/Notion compatibility.

    Args:
        title: Note title.
        content: Markdown body (used for auto-tagging).
        url: Source URL or label.
        date_format: strftime format string.

    Returns:
        YAML frontmatter string terminated by a blank line.
    """
    date_str = datetime.date.today().strftime(date_format)
    tags = _auto_detect_tags(content)
    tag_str = ", ".join(tags)

    return (
        f"---\n"
        f'title: "{title}"\n'
        f"date: {date_str}\n"
        f"tags: [{tag_str}]\n"
        f'source: "{url}"\n'
        f"---\n\n"
    )


# ──────────────────────────────────────────────
#  Language Detection (for <code> elements)
# ──────────────────────────────────────────────

def get_code_language(el: Tag) -> str:
    """
    Detect the programming language of a ``<code>``/``<pre>`` element.

    Strategy (highest priority first):
      1. HTML class inspection  (``language-*`` / ``lang-*``)
      2. Proximity search       (closest preceding text block)
      3. Syntax analysis        (pattern matching on code content)

    Args:
        el: A BeautifulSoup Tag representing a code element.

    Returns:
        Canonical language string, or ``""`` if undetermined.
    """
    # --- 1. HTML Class Inspection ---
    el_classes = el.get("class", []) or []
    parent_classes = el.parent.get("class", []) if el.parent else []
    for cls in el_classes + parent_classes:
        if cls.startswith("language-") or cls.startswith("lang-"):
            return cls.split("-", 1)[1]

    # --- 2. Proximity Search ---
    search_limit = 4
    preceding = el.parent.find_all_previous(
        ["p", "div", "h3", "h4", "h5", "li", "span"], limit=search_limit
    )
    for prev in preceding:
        text = prev.get_text(strip=True).lower()
        if len(text) > 120:
            text = text[-60:]

        for label, lang in _LABEL_MAP.items():
            if label in text:
                # Guard "java" from matching "javascript"
                if label == "java" and "script" in text:
                    continue
                return lang

    # --- 3. Syntax Analysis ---
    code = el.get_text()

    # C / C++
    if "#include" in code or "std::" in code:
        return "cpp"
    if "cout" in code and "<<" in code:
        return "cpp"
    if re.search(
        r"\b(int|void|double|float|bool|char)\s+\w+\s*\(.*?\)\s*\{",
        code,
        re.DOTALL,
    ):
        return "cpp"

    # Python
    if "def " in code and ":" in code:
        return "python"
    if "import " in code and "from " in code:
        return "python"

    # Rust
    if "fn " in code and "let " in code and "->" in code:
        return "rust"

    # Go
    if "func " in code and "fmt." in code:
        return "go"

    # TypeScript / JavaScript
    if "interface " in code and ":" in code and "export " in code:
        return "typescript"
    if "console.log" in code or "document." in code:
        return "javascript"

    # SQL
    if re.search(r"\bSELECT\b.*\bFROM\b", code, re.IGNORECASE | re.DOTALL):
        return "sql"

    # HTML
    if re.search(r"<\/?[a-z]+[^>]*>", code, re.IGNORECASE):
        return "html"

    return ""


# ──────────────────────────────────────────────
#  Platform Artifact Cleanup
# ──────────────────────────────────────────────

# Regex for sidebar / drawer / nav-panel class names
_SIDEBAR_CLASS_RE = re.compile(
    r"sidebar|side-bar|sidenav|side.nav|drawer|nav[-_]?rail|"
    r"chat[-_]?list|conversation[-_]?list|history[-_]?panel|"
    r"left[-_]?panel|left[-_]?nav|menu[-_]?panel|"
    r"threads[-_]?list|thread[-_]?list",
    re.IGNORECASE,
)

# Regex for aria-labels that reveal sidebar / navigation
_SIDEBAR_ARIA_RE = re.compile(
    r"conversation|recent chat|chat history|sidebar|navigation|"
    r"threads|previous chat|menu",
    re.IGNORECASE,
)

# Regex for overlay / popup class names
_OVERLAY_CLASS_RE = re.compile(
    r"tooltip|popover|modal|overlay|backdrop|snackbar",
    re.IGNORECASE,
)

# Regex for user-message class names
_USER_MSG_CLASS_RE = re.compile(
    r"user[-_]?message|human[-_]?message|query[-_]?message|"
    r"user[-_]?turn|human[-_]?turn|request[-_]?row|"
    r"user[-_]?row|prompt[-_]?row",
    re.IGNORECASE,
)


def _strip_platform_artifacts(soup: BeautifulSoup) -> None:
    """
    Remove platform-specific UI chrome from the DOM before Markdown
    conversion.

    Targets:
      • Sidebar / drawer / navigation panels (old-chat lists)
      • Platform branding headers ("Google Gemini", "ChatGPT", …)
      • Input areas, tooltips, modals
      • Common UI detritus that leaks into exports
    """
    # ── 1. Sidebar & navigation panels ──────────────
    for tag in soup(["aside"]):
        tag.decompose()

    for role in ("complementary", "navigation"):
        for el in soup.find_all(attrs={"role": role}):
            el.decompose()

    for el in soup.find_all(class_=_SIDEBAR_CLASS_RE):
        el.decompose()

    for el in soup.find_all(attrs={"aria-label": _SIDEBAR_ARIA_RE}):
        el.decompose()

    # ── 2. Platform branding ───────────────────────
    # <title> tags bleed into markdown as text
    for t in soup(["title"]):
        t.decompose()

    # Standalone text nodes that are JUST a platform name
    for name in _PLATFORM_NAMES:
        pattern = re.compile(rf"^\s*{re.escape(name)}\s*$", re.IGNORECASE)
        for text_node in soup.find_all(string=pattern):
            parent = text_node.parent
            if parent is None:
                continue
            if parent.name in {
                "h1", "h2", "h3", "h4", "h5", "h6",
                "span", "div", "a", "p", "label",
            }:
                parent_text = parent.get_text(strip=True).lower()
                if parent_text in (name.lower(), f"✨ {name.lower()}"):
                    parent.decompose()

    # ── 3. Input / prompt areas ────────────────────
    for el in soup.find_all(attrs={"contenteditable": "true"}):
        el.decompose()
    for el in soup.find_all(["textarea", "input"]):
        el.decompose()

    # ── 4. Modals / tooltips / overlays ────────────
    for role in ("dialog", "tooltip", "alertdialog"):
        for el in soup.find_all(attrs={"role": role}):
            el.decompose()

    for el in soup.find_all(class_=_OVERLAY_CLASS_RE):
        el.decompose()

    logger.debug("Stripped platform artifacts from DOM")


def _simplify_user_messages(soup: BeautifulSoup) -> None:
    """
    Locate user-message containers and strip large code blocks from
    them.

    In a full-page export the user's pasted code would otherwise
    duplicate what the AI response already shows.  This keeps the
    user's *question text* but drops their code pastes so only the
    AI's formatted code appears.
    """
    user_containers: list[Tag] = []

    # ── Data-attribute detection (most reliable) ───
    for attr, val in (
        ("data-message-author-role", "user"),
        ("data-turn-role", "human"),
        ("data-role", "user"),
    ):
        user_containers.extend(soup.find_all(attrs={attr: val}))

    # ── Class-based detection ──────────────────────
    user_containers.extend(soup.find_all(class_=_USER_MSG_CLASS_RE))

    seen: set[int] = set()
    removed = 0
    for container in user_containers:
        cid = id(container)
        if cid in seen:
            continue
        seen.add(cid)

        # Remove <pre> blocks (wrapped code) from user messages
        for code_el in container.find_all("pre"):
            code_el.decompose()
            removed += 1

    if removed:
        logger.debug("Removed %d code block(s) from user messages", removed)


# ──────────────────────────────────────────────
#  Core Extraction Logic
# ──────────────────────────────────────────────

def extract_response(
    file_path: Path | str,
    search_phrase: str,
    *,
    config: Optional[AppConfig] = None,
) -> ExtractionResult:
    """
    Extract an AI response from an HTML chat export.

    Args:
        file_path: Path to the HTML file.
        search_phrase: Text snippet to locate in the conversation.
        config: Optional AppConfig (loaded from config.json if None).

    Returns:
        An ExtractionResult with markdown content and metadata.
    """
    cfg = config or load_config()
    path = Path(file_path)

    if not path.exists():
        return ExtractionResult(success=False, message="File not found.")

    try:
        raw_html = _load_html(path)
    except UnicodeDecodeError:
        logger.error("Encoding error reading %s", path)
        return ExtractionResult(success=False, message="Failed to read file — encoding issue.")

    soup = BeautifulSoup(raw_html, "html.parser")

    # 1. Locate user message containing the search phrase
    user_node = soup.find(
        string=lambda text: text and search_phrase.lower() in text.lower()
    )
    if not user_node:
        logger.warning("Phrase '%s' not found in %s", search_phrase, path.name)
        return ExtractionResult(success=False, message="Phrase not found in the document.")

    # 2. Walk up to a meaningful container
    container = user_node.parent
    while container and container.name not in {"div", "li", "article", "section"}:
        container = container.parent

    if container is None:
        return ExtractionResult(success=False, message="Could not determine message container.")

    # 3. Find the AI response block
    ai_node: Optional[Tag] = None
    for sibling in container.find_all_next("div"):
        if sibling == container:
            continue
        if len(sibling.get_text(strip=True)) > 20:
            ai_node = sibling
            break

    if ai_node is None:
        return ExtractionResult(
            success=False,
            message="Found question, but couldn't isolate the AI answer.",
        )

    # 4. Clean up non-content elements
    removable = ["button", "svg", "img", "nav", "footer", "script", "style"]
    if cfg.settings.strip_buttons:
        removable.extend(["a[class*='copy']", "div[class*='toolbar']"])
    for tag in ai_node(removable[:6]):  # BeautifulSoup tags
        tag.decompose()

    # 5. Convert to Markdown
    heading_style = cfg.settings.heading_style if cfg else "ATX"
    markdown_text: str = md(
        str(ai_node),
        heading_style=heading_style,
        code_language_callback=get_code_language,
    )

    # 6. Post-process — remove excessive blank lines
    markdown_text = re.sub(r"\n{4,}", "\n\n\n", markdown_text)

    detected = _auto_detect_tags(markdown_text)
    detected.discard("ai-chat") if isinstance(detected, set) else None
    word_count = len(markdown_text.split())

    logger.info(
        "Extracted %d words from '%s' (languages: %s)",
        word_count,
        search_phrase,
        ", ".join(detected) or "none",
    )

    return ExtractionResult(
        success=True,
        markdown=markdown_text,
        message="Extraction successful.",
        word_count=word_count,
        detected_languages=detected,
    )


# ──────────────────────────────────────────────
#  Full-Page Export
# ──────────────────────────────────────────────

def extract_full_page(
    file_path: Path | str,
    *,
    config: Optional[AppConfig] = None,
) -> ExtractionResult:
    """
    Convert an entire HTML chat page to Markdown.

    Unlike ``extract_response``, this does NOT search for a specific phrase.
    It converts the whole page, preserving all Q&A pairs.

    Args:
        file_path: Path to the HTML file.
        config: Optional AppConfig.

    Returns:
        ExtractionResult with the full-page markdown.
    """
    cfg = config or load_config()
    path = Path(file_path)

    if not path.exists():
        return ExtractionResult(success=False, message="File not found.")

    try:
        raw_html = _load_html(path)
    except UnicodeDecodeError:
        logger.error("Encoding error reading %s", path)
        return ExtractionResult(success=False, message="Failed to read file — encoding issue.")

    soup = BeautifulSoup(raw_html, "html.parser")

    # ── Phase 0: Extract conversation title before cleanup ──
    chat_title: Optional[str] = None
    title_tag = soup.find("title")
    if title_tag:
        raw_title = title_tag.get_text(strip=True)
        # Strip platform names and "Conversation with ..." prefix
        cleaned = raw_title
        cleaned = re.sub(
            r"(?i)^conversation\s+with\s+", "", cleaned
        )
        for name in _PLATFORM_NAMES:
            cleaned = re.sub(
                rf"(?i)\s*[-–—|]\s*{re.escape(name)}\s*$", "", cleaned
            )
            cleaned = re.sub(
                rf"(?i)^{re.escape(name)}\s*[-–—|]\s*", "", cleaned
            )
        cleaned = cleaned.strip(" -–—|")
        if cleaned:
            chat_title = cleaned

    # ── Phase 1: Basic tag cleanup ─────────────────
    for tag in soup(["button", "svg", "nav", "footer", "script", "style", "header"]):
        tag.decompose()

    if cfg.settings.strip_buttons:
        for tag in soup.select("div[class*='toolbar'], a[class*='copy']"):
            tag.decompose()

    # ── Phase 2: Platform-specific cleanup ─────────
    #   • Strips sidebars / drawers (old chat lists)
    #   • Strips platform branding ("Google Gemini", etc.)
    #   • Strips input areas, overlays, modals
    _strip_platform_artifacts(soup)

    # ── Phase 3: Simplify user messages ────────────
    #   Removes code blocks pasted by the user so only
    #   the AI's formatted code appears in the export.
    _simplify_user_messages(soup)

    # ── Phase 4: Locate main content ───────────────
    main_content = (
        soup.find("main")
        or soup.find("div", role="main")
        or soup.find("article")
        or soup.body
        or soup
    )

    # ── Phase 5: Convert to Markdown ───────────────
    heading_style = cfg.settings.heading_style
    markdown_text: str = md(
        str(main_content),
        heading_style=heading_style,
        code_language_callback=get_code_language,
    )

    # ── Phase 6: Post-process ──────────────────────
    # Remove remaining platform name lines that survived DOM stripping
    for name in _PLATFORM_NAMES:
        markdown_text = re.sub(
            rf"^#+\s*{re.escape(name)}\s*$", "", markdown_text, flags=re.MULTILINE
        )
    # Remove "Conversation with <AI>" headings and standalone lines
    markdown_text = re.sub(
        r"^#+\s*Conversation\s+with\s+\S+.*$", "", markdown_text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    markdown_text = re.sub(
        r"^Conversation\s+with\s+\S+.*$", "", markdown_text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    # Collapse excessive blank lines
    markdown_text = re.sub(r"\n{4,}", "\n\n\n", markdown_text)
    # Strip leading blank lines
    markdown_text = markdown_text.lstrip("\n")

    detected = _auto_detect_tags(markdown_text)
    word_count = len(markdown_text.split())

    logger.info(
        "Full-page export: %d words from '%s' (languages: %s)",
        word_count,
        path.name,
        ", ".join(detected) or "none",
    )

    return ExtractionResult(
        success=True,
        markdown=markdown_text,
        message="Full-page export successful.",
        word_count=word_count,
        detected_languages=detected,
        title=chat_title,
    )


# ──────────────────────────────────────────────
#  File I/O
# ──────────────────────────────────────────────

def save_to_file(
    content: str,
    filename: str,
    title_for_header: str,
    *,
    mode: str = "w",
    config: Optional[AppConfig] = None,
) -> Path:
    """
    Save markdown content to the export folder.

    In write mode a full YAML frontmatter is prepended;
    in append mode a horizontal rule separator is added.

    Args:
        content: Markdown body text.
        filename: Target filename (inside save folder).
        title_for_header: Human-readable title.
        mode: ``'w'`` for new file, ``'a'`` for append.
        config: Optional AppConfig.

    Returns:
        Absolute path of the saved file.
    """
    cfg = config or load_config()
    folder = Path(cfg.default_save_folder)
    folder.mkdir(parents=True, exist_ok=True)
    full_path = folder / filename

    is_new = not full_path.exists() or mode == "w"

    with full_path.open(mode, encoding="utf-8") as fh:
        if is_new:
            header = generate_frontmatter(
                title_for_header,
                content,
                date_format=cfg.settings.date_format,
            )
            fh.write(header + f"# {title_for_header}\n\n" + content)
        else:
            fh.write(f"\n\n---\n\n# {title_for_header}\n\n" + content)

    logger.info("Saved → %s (%s)", full_path, "new" if is_new else "appended")
    return full_path