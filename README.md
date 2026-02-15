# 📝 AI Chat Exporter

> **v3.0.0** — Convert AI chat HTML exports into clean, tagged Markdown notes.

A modern Python CLI tool that converts saved HTML chat logs from **ChatGPT, Gemini, Claude, Copilot, and DeepSeek** into structured Markdown files — ready for **Obsidian**, **Notion**, or any knowledge base.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Live Watch Mode** | Auto-detects new HTML files in your Downloads folder via `watchdog` |
| **Batch Processing** | Process every HTML file in a directory at once |
| **CLI + Interactive** | Full `argparse` CLI flags **or** guided interactive menu |
| **Smart Extraction** | Finds specific AI responses by search phrase |
| **Session Merging** | Append multiple extractions into a single "Master Note" |
| **15+ Language Detection** | Python, C++, JS, TS, Rust, Go, Java, SQL, Bash, Ruby, C#, Kotlin, Swift, and more |
| **3-Tier Detection** | HTML class → proximity search → syntax analysis |
| **YAML Frontmatter** | Auto-generated tags, date, source for Obsidian compatibility |
| **Typed Architecture** | Dataclasses, type hints, pathlib, structured logging |
| **Zero Config Start** | Works out of the box — `config.json` is optional |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/AI-Chat-Exporter.git
cd AI-Chat-Exporter
pip install -r requirements.txt
```

### 2. Run (Interactive)

```bash
python watcher.py
```

The interactive menu will guide you through mode selection and merge preferences.

### 3. Run (CLI)

```bash
# Live watch mode
python watcher.py --watch

# Process a single file
python watcher.py --file "path/to/chat.html"

# Batch process a folder
python watcher.py --batch "path/to/folder"

# Merge all extractions into one file
python watcher.py --file "chat.html" --merge "StudyNotes.md"

# Debug logging
python watcher.py --watch --debug
```

---

## 🖥️ CLI Reference

| Flag | Short | Description |
|---|---|---|
| `--version` | `-v` | Print version and exit |
| `--watch` | `-w` | Start live-watch mode on Downloads folder |
| `--file PATH` | `-f` | Process a single HTML file |
| `--batch PATH` | `-b` | Process all HTML files in a directory |
| `--merge NAME` | `-m` | Merge all extractions into one `.md` file |
| `--downloads PATH` | | Override the watched Downloads directory |
| `--debug` | | Enable verbose debug logging |

---

## ⚙️ Configuration

Edit `config.json` to customise behaviour:

```json
{
    "default_save_folder": "Exported_Notes",
    "downloads_path": "",
    "supported_platforms": ["ChatGPT", "Gemini", "Claude", "Copilot", "DeepSeek"],
    "version": "3.0.0",
    "settings": {
        "strip_buttons": true,
        "include_metadata": true,
        "date_format": "%Y-%m-%d",
        "heading_style": "ATX",
        "wrap_code_blocks": true,
        "max_filename_length": 50
    }
}
```

| Setting | Default | Description |
|---|---|---|
| `downloads_path` | `""` (auto: `~/Downloads`) | Directory to watch for new HTML files |
| `default_save_folder` | `Exported_Notes` | Where exported `.md` files are saved |
| `strip_buttons` | `true` | Remove copy/share buttons from the HTML |
| `include_metadata` | `true` | Add YAML frontmatter to exported files |
| `date_format` | `%Y-%m-%d` | Date format in frontmatter |
| `heading_style` | `ATX` | Markdown heading style (`ATX` = `#`, `SETEXT` = underlines) |
| `max_filename_length` | `50` | Max characters for auto-generated filenames |

> **Tip:** Leave `downloads_path` empty to auto-detect your system's Downloads folder.

---

## 📁 Project Structure

```
AI_Chat_Exporter/
├── watcher.py            # CLI entry point + file watcher
├── converter.py          # HTML → Markdown conversion engine
├── config_loader.py      # Typed config management
├── logger.py             # Centralised logging
├── config.json           # User settings
├── requirements.txt      # Dependencies
├── ARCHITECTURE.md       # Developer guide & change-impact map
├── README.md
├── LICENSE
└── Exported_Notes/       # Output (git-ignored)
```

> See [ARCHITECTURE.md](ARCHITECTURE.md) for the full dependency graph, data-flow diagrams, and change-impact map.

---

## 🔧 How It Works

1. **Input** — Save any AI chat page as `.html` (Ctrl+S in browser)
2. **Detection** — The watcher picks it up, or you pass it via `--file`
3. **Search** — You enter a phrase from the conversation
4. **Extraction** — BeautifulSoup locates the user message → walks the DOM to the AI response
5. **Language Detection** — Code blocks are analyzed with a 3-tier strategy:
   - HTML class attributes (`language-python`)
   - Proximity search (nearest text label above the block)
   - Syntax pattern matching (regex on code content)
6. **Output** — Clean Markdown with YAML frontmatter, auto-tags, and proper code fences

---

## 🧑‍💻 For Developers

The [ARCHITECTURE.md](ARCHITECTURE.md) file contains:

- **Data-flow diagrams** — visual representation of the pipeline
- **Module responsibility tables** — what each file owns
- **Dependency graph** — which modules import which
- **Change-impact map** — "if I change X, what else breaks?"
- **Step-by-step guides** — adding new languages, config options, and CLI flags

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/new-platform`)
3. Read [ARCHITECTURE.md](ARCHITECTURE.md) for the change-impact map
4. Make your changes
5. Submit a Pull Request

---

## 📄 License

MIT License