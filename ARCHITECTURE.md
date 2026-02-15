# 🏗️ Architecture Guide — AI Chat Exporter

> **Version 3.0.0** — Last updated 2026-02-15

This document describes the internal architecture, module responsibilities, data flow, and the **change-impact map** so developers know exactly which files are affected when they modify something.

---

## 📁 Project Structure

```
AI_Chat_Exporter/
├── watcher.py            # CLI entry point + file watcher
├── converter.py          # HTML → Markdown conversion engine
├── config_loader.py      # Typed config loading (config.json → dataclass)
├── logger.py             # Centralised logging setup
├── config.json           # User-editable settings
├── requirements.txt      # Python dependencies
├── .gitignore
├── README.md
├── ARCHITECTURE.md       # ← you are here
├── LICENSE
└── Exported_Notes/       # Output directory (git-ignored)
```

---

## 🔄 Data Flow

```
┌──────────────┐
│  HTML File    │  (saved from ChatGPT / Gemini / Claude / Copilot)
└──────┬───────┘
       │
       ▼
┌──────────────────┐     loads      ┌─────────────────┐
│   watcher.py     │ ◄──────────── │  config_loader   │
│  (CLI / Watcher) │               │  (config.json)   │
└──────┬───────────┘               └─────────────────┘
       │ calls extract_response()
       ▼
┌──────────────────┐
│  converter.py    │
│  ┌────────────┐  │
│  │ Language   │  │  ← detects 15+ languages
│  │ Detector   │  │
│  ├────────────┤  │
│  │ Frontmatter│  │  ← YAML metadata for Obsidian
│  │ Generator  │  │
│  ├────────────┤  │
│  │ Extractor  │  │  ← finds AI response in DOM
│  └────────────┘  │
└──────┬───────────┘
       │ returns ExtractionResult
       ▼
┌──────────────────┐
│  save_to_file()  │  → Exported_Notes/*.md
└──────────────────┘
```

---

## 📦 Module Responsibilities

### `watcher.py` — CLI & Orchestration
| Responsibility | Details |
|---|---|
| CLI argument parsing | `argparse` with `--watch`, `--file`, `--batch`, `--merge`, `--debug` flags |
| Interactive menu | Fallback when no CLI args provided |
| Live file watching | `watchdog` observer on Downloads folder |
| Batch processing | Glob all `*.htm*` files in a directory |
| Terminal UI | ANSI-colored output via `_Style` helper class |

### `converter.py` — Conversion Engine
| Responsibility | Details |
|---|---|
| HTML loading | `pathlib`-based UTF-8 file read |
| DOM extraction | BeautifulSoup — locates user message → walks to AI response |
| Language detection | 3-tier strategy: HTML class → proximity search → syntax analysis |
| Auto-tagging | Scans markdown for code patterns → generates tag list |
| Frontmatter | YAML block with title, date, tags, source |
| File saving | Write/append modes with frontmatter management |
| `ExtractionResult` | Dataclass return type with `success`, `markdown`, `word_count`, `detected_languages` |

### `config_loader.py` — Configuration
| Responsibility | Details |
|---|---|
| JSON parsing | Reads `config.json` with error handling |
| Typed access | `AppConfig` and `ExporterSettings` dataclasses |
| Defaults | Every field has a sensible fallback |
| Path resolution | `downloads_dir` auto-resolves `~/Downloads` if not set |

### `logger.py` — Logging
| Responsibility | Details |
|---|---|
| Console output | Formatted log messages to stdout |
| File logging | Optional `exporter.log` file (debug-level) |
| One-time setup | Guard prevents duplicate handler registration |

---

## 🔗 Dependency Graph

```
watcher.py
  ├── converter.py
  │     └── config_loader.py
  ├── config_loader.py
  └── logger.py

converter.py
  └── config_loader.py

config_loader.py
  └── (stdlib only)

logger.py
  └── (stdlib only)
```

---

## ⚡ Change-Impact Map

> **"If I change X, what else breaks?"**

This table helps developers understand cascading effects.

| Changed File / Component | Direct Impact | Side Effects |
|---|---|---|
| **`config.json`** | `config_loader.py` reads new fields | If new keys added → update `AppConfig` / `ExporterSettings` dataclasses |
| **`config_loader.py` → `AppConfig` fields** | `converter.py` and `watcher.py` consume the config | Any new setting needs to be wired into the relevant consumer |
| **`config_loader.py` → `ExporterSettings` fields** | `converter.py` uses these in `save_to_file()` and `generate_frontmatter()` | Add matching key in `config.json` and default in dataclass |
| **`converter.py` → `extract_response()` signature** | `watcher.py` calls this function | Update all call sites in `process_file()` |
| **`converter.py` → `ExtractionResult` fields** | `watcher.py` reads `.success`, `.markdown`, `.word_count`, `.detected_languages`, `.message` | If field renamed/removed → update `process_file()` |
| **`converter.py` → `save_to_file()` signature** | `watcher.py` calls this function | Update `process_file()` call sites |
| **`converter.py` → `_LABEL_MAP` / `_CODE_BLOCK_TAG_MAP`** | Only internal to `converter.py` | Adding a new language here auto-enables detection + tagging |
| **`converter.py` → `generate_frontmatter()`** | Called by `save_to_file()` internally | Changes affect all exported `.md` files |
| **`converter.py` → `get_code_language()`** | Used as callback by `markdownify` | Changes affect code block language annotations in output |
| **`watcher.py` → `_build_parser()`** | Only affects CLI interface | No cascading impact on other modules |
| **`watcher.py` → `interactive_menu()`** | Only affects interactive mode | No cascading impact |
| **`watcher.py` → `process_file()`** | Core orchestration loop | Changes here affect all 3 modes (watch, manual, batch) |
| **`logger.py`** | All modules import `logging` | Changing format/level affects all log output |
| **`requirements.txt`** | `pip install` | Version bumps may introduce breaking changes in `beautifulsoup4`, `markdownify`, `watchdog` |

---

## 🧪 Adding a New Language

To add support for a new programming language (e.g., **Scala**):

1. **`converter.py` → `_LABEL_MAP`** — add proximity-search labels:
   ```python
   "scala": "scala",
   ```

2. **`converter.py` → `_CODE_BLOCK_TAG_MAP`** — add code-fence markers:
   ```python
   "```scala": "scala",
   ```

3. **`converter.py` → `get_code_language()`** — *(optional)* add syntax heuristics:
   ```python
   # Scala
   if "object " in code and "def " in code and "val " in code:
       return "scala"
   ```

4. **`converter.py` → `_auto_detect_tags()`** — *(optional)* add content heuristics:
   ```python
   if "case class" in lower or "implicit " in lower:
       tags.add("scala")
   ```

**No other files need to change** — the language maps are self-contained.

---

## 🛡️ Adding a New Config Option

1. **`config.json`** — add the key with a default value.
2. **`config_loader.py`** — add the field to `ExporterSettings` (or `AppConfig`) dataclass, and parse it in `load_config()`.
3. **Consumer module** — reference `config.settings.new_option` where needed.
4. **`ARCHITECTURE.md`** — document the option in the change-impact table.
5. **`README.md`** — document the option in the Configuration section.

---

## 🚀 Adding a New CLI Flag

1. **`watcher.py` → `_build_parser()`** — add `parser.add_argument(...)`.
2. **`watcher.py` → `main()`** — handle `args.new_flag` in the dispatch logic.
3. **`README.md`** — document the flag in the Usage section.

---

## 📐 Design Decisions

| Decision | Rationale |
|---|---|
| **Dataclasses over dicts** | Type safety, IDE autocompletion, self-documenting |
| **`pathlib` over `os.path`** | Modern, chainable, cross-platform path API |
| **`ExtractionResult` return type** | Replaces `(str, str)` tuple — extensible, typed, clear |
| **No global mutable state** | Config passed explicitly; no `global MERGE_TARGET` |
| **ANSI colors without `rich`** | Zero extra dependencies for terminal styling |
| **Separate `config_loader`** | Single responsibility; testable in isolation |
| **`logging` over `print`** | Levelled output, file logging, structured messages |

---

## 📋 Supported Languages (Detection)

| Language | HTML Class | Proximity | Syntax | Auto-Tag |
|---|:---:|:---:|:---:|:---:|
| Python | ✔ | ✔ | ✔ | ✔ |
| C++ | ✔ | ✔ | ✔ | ✔ |
| JavaScript | ✔ | ✔ | ✔ | ✔ |
| TypeScript | ✔ | ✔ | ✔ | ✔ |
| Java | ✔ | ✔ | ✔ | ✔ |
| Rust | ✔ | ✔ | ✔ | ✔ |
| Go | ✔ | ✔ | ✔ | ✔ |
| SQL | ✔ | ✔ | ✔ | — |
| Bash/Shell | ✔ | ✔ | — | — |
| Ruby | ✔ | ✔ | — | — |
| C# | ✔ | ✔ | — | — |
| Kotlin | ✔ | ✔ | — | — |
| Swift | ✔ | ✔ | — | — |
| PHP | ✔ | ✔ | — | — |
| Dart | ✔ | ✔ | — | — |
| HTML | ✔ | ✔ | ✔ | — |
| CSS | ✔ | ✔ | — | — |
| R | ✔ | ✔ | — | — |
