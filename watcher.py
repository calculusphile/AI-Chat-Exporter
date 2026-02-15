"""
AI Chat Exporter — Watcher & CLI Interface.

Provides four operating modes:
  1. Live Watch  — monitors Downloads folder for new HTML files
  2. Manual      — processes a single file on demand
  3. Batch       — processes all HTML files in a directory
  4. Full Page   — converts entire HTML chat pages to Markdown

Supports AI-powered smart titles for cleaner headings.
Uses argparse for CLI flags so the tool can be scripted or run
interactively with a rich terminal UI.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config_loader import AppConfig, load_config
from converter import ExtractionResult, extract_response, extract_full_page, save_to_file
from title_generator import generate_smart_title
from logger import setup_logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Pretty-print helpers (no external dependency)
# ──────────────────────────────────────────────

class _Style:
    """ANSI escape helpers for coloured terminal output."""
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"

    @staticmethod
    def ok(msg: str) -> str:
        return f"{_Style.GREEN}✔ {msg}{_Style.RESET}"

    @staticmethod
    def warn(msg: str) -> str:
        return f"{_Style.YELLOW}⚠ {msg}{_Style.RESET}"

    @staticmethod
    def err(msg: str) -> str:
        return f"{_Style.RED}✖ {msg}{_Style.RESET}"

    @staticmethod
    def info(msg: str) -> str:
        return f"{_Style.CYAN}ℹ {msg}{_Style.RESET}"

    @staticmethod
    def header(msg: str) -> str:
        width = 48
        border = "═" * width
        pad = (width - len(msg)) // 2
        return (
            f"\n{_Style.MAGENTA}{_Style.BOLD}"
            f"╔{border}╗\n"
            f"║{' ' * pad}{msg}{' ' * (width - pad - len(msg))}║\n"
            f"╚{border}╝"
            f"{_Style.RESET}\n"
        )

    @staticmethod
    def divider() -> str:
        return f"{_Style.DIM}{'─' * 50}{_Style.RESET}"


# ──────────────────────────────────────────────
#  Processing Pipeline
# ──────────────────────────────────────────────

def _sanitize_filename(name: str, max_len: int = 50) -> str:
    """Create a filesystem-safe filename from a phrase."""
    safe = re.sub(r'[<>:"/\\|?*]', "", name)
    safe = safe.replace(" ", "_").strip("_")
    return safe[:max_len] + ".md"


def _get_smart_title(phrase: str, config: AppConfig) -> str:
    """Generate a smart title using AI or heuristic fallback."""
    if not config.settings.smart_titles:
        return phrase

    api_key = config.ai.api_key if config.ai.enabled else None
    return generate_smart_title(
        phrase,
        api_key=api_key,
        api_base=config.ai.api_base,
        model=config.ai.model,
        max_length=config.settings.max_filename_length,
    )


def process_file(
    file_path: Path,
    *,
    merge_target: Optional[str] = None,
    config: AppConfig,
) -> int:
    """
    Interactive loop: repeatedly ask user for phrases from one HTML file.

    Args:
        file_path: Path to the HTML file.
        merge_target: Filename to append all extractions to (or None).
        config: Application configuration.

    Returns:
        Number of successful extractions.
    """
    print(f"\n{_Style.info(f'Opened: {file_path.name}')}")

    if not file_path.exists():
        print(_Style.err("File not found."))
        return 0

    count = 0
    while True:
        print(_Style.divider())
        phrase = input(f"{_Style.CYAN}  ▸ Search phrase (ENTER to finish): {_Style.RESET}")

        if not phrase.strip():
            print(_Style.ok(f"Done — {count} extraction(s) from this file."))
            break

        logger.debug("Searching for: '%s'", phrase)
        result: ExtractionResult = extract_response(file_path, phrase, config=config)

        if result.success and result.markdown:
            title = _get_smart_title(phrase, config)
            if title != phrase:
                print(f"    {_Style.DIM}Title: {title}{_Style.RESET}")

            if merge_target:
                saved = save_to_file(
                    result.markdown, merge_target, title, mode="a", config=config
                )
                print(_Style.ok(f"Appended to {merge_target}  ({result.word_count} words)"))
            else:
                fname = _sanitize_filename(title, config.settings.max_filename_length)
                saved = save_to_file(
                    result.markdown, fname, title, mode="w", config=config
                )
                print(_Style.ok(f"Saved → {fname}  ({result.word_count} words)"))

            if result.detected_languages:
                langs = ", ".join(result.detected_languages)
                print(f"    {_Style.DIM}Languages detected: {langs}{_Style.RESET}")
            count += 1
        else:
            print(_Style.warn(result.message))

    return count


def batch_process(
    directory: Path,
    *,
    merge_target: Optional[str] = None,
    config: AppConfig,
) -> None:
    """Process every HTML/HTM file in a directory."""
    html_files = sorted(directory.glob("*.htm*"))
    if not html_files:
        print(_Style.warn(f"No HTML files found in {directory}"))
        return

    print(_Style.info(f"Found {len(html_files)} HTML file(s) in {directory}"))
    for f in html_files:
        process_file(f, merge_target=merge_target, config=config)


# ──────────────────────────────────────────────
#  Full-Page Processing
# ──────────────────────────────────────────────

def process_full_page(
    file_path: Path,
    *,
    merge_target: Optional[str] = None,
    config: AppConfig,
) -> int:
    """
    Convert an entire HTML chat page to Markdown (no search phrase needed).

    Args:
        file_path: Path to the HTML file.
        merge_target: Filename to append to (or None for auto-naming).
        config: Application configuration.

    Returns:
        1 if successful, 0 otherwise.
    """
    print(f"\n{_Style.info(f'Full-page export: {file_path.name}')}")

    if not file_path.exists():
        print(_Style.err("File not found."))
        return 0

    result: ExtractionResult = extract_full_page(file_path, config=config)

    if result.success and result.markdown:
        # Use the filename (without extension) as the base title
        raw_title = file_path.stem.replace("_", " ").replace("-", " ")
        title = _get_smart_title(raw_title, config)

        if title != raw_title:
            print(f"    {_Style.DIM}Title: {title}{_Style.RESET}")

        if merge_target:
            saved = save_to_file(
                result.markdown, merge_target, title, mode="a", config=config
            )
            print(_Style.ok(f"Appended to {merge_target}  ({result.word_count} words)"))
        else:
            fname = _sanitize_filename(title, config.settings.max_filename_length)
            saved = save_to_file(
                result.markdown, fname, title, mode="w", config=config
            )
            print(_Style.ok(f"Saved → {fname}  ({result.word_count} words)"))

        if result.detected_languages:
            langs = ", ".join(result.detected_languages)
            print(f"    {_Style.DIM}Languages detected: {langs}{_Style.RESET}")
        return 1
    else:
        print(_Style.warn(result.message))
        return 0


def batch_full_page(
    directory: Path,
    *,
    merge_target: Optional[str] = None,
    config: AppConfig,
) -> None:
    """Full-page export every HTML/HTM file in a directory."""
    html_files = sorted(directory.glob("*.htm*"))
    if not html_files:
        print(_Style.warn(f"No HTML files found in {directory}"))
        return

    print(_Style.info(f"Full-page export: {len(html_files)} file(s) in {directory}"))
    total = 0
    for f in html_files:
        total += process_full_page(f, merge_target=merge_target, config=config)
    print(f"\n{_Style.ok(f'Batch complete — {total}/{len(html_files)} file(s) exported.')}")


# ──────────────────────────────────────────────
#  Live Watcher
# ──────────────────────────────────────────────

class _HTMLFileHandler(FileSystemEventHandler):
    """React to new HTML files appearing in the watched directory."""

    def __init__(self, merge_target: Optional[str], config: AppConfig) -> None:
        super().__init__()
        self.merge_target = merge_target
        self.config = config

    def on_created(self, event) -> None:  # type: ignore[override]
        path = Path(event.src_path)
        if path.suffix.lower() in {".html", ".htm"}:
            print(f"\n{_Style.info(f'Detected: {path.name}')}")
            time.sleep(1)  # allow write to finish
            process_file(path, merge_target=self.merge_target, config=self.config)
            print(f"\n{_Style.DIM}Listening for new files…{_Style.RESET}")


def start_watcher(
    watch_dir: Path,
    *,
    merge_target: Optional[str] = None,
    config: AppConfig,
) -> None:
    """Start the watchdog observer on *watch_dir*."""
    handler = _HTMLFileHandler(merge_target, config)
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=False)

    print(_Style.ok(f"Live watcher running on: {watch_dir}"))
    print(f"{_Style.DIM}Press Ctrl+C to stop.{_Style.RESET}\n")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{_Style.warn('Shutting down watcher…')}")
        observer.stop()
    observer.join()


# ──────────────────────────────────────────────
#  CLI Entry Point
# ──────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-chat-exporter",
        description="Convert AI chat HTML exports into clean Markdown notes.",
    )
    parser.add_argument(
        "-v", "--version",
        action="store_true",
        help="Show version and exit.",
    )
    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Start live-watch mode on the Downloads folder.",
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        default=None,
        help="Path to a single HTML file to process.",
    )
    parser.add_argument(
        "-b", "--batch",
        type=str,
        default=None,
        help="Path to a folder — process all HTML files inside.",
    )
    parser.add_argument(
        "-p", "--full-page",
        action="store_true",
        help="Export entire HTML page(s) instead of searching for specific phrases.",
    )
    parser.add_argument(
        "-m", "--merge",
        type=str,
        default=None,
        help="Merge all extractions into this single .md file.",
    )
    parser.add_argument(
        "--downloads",
        type=str,
        default=None,
        help="Override the Downloads directory path.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug-level logging.",
    )
    return parser


def interactive_menu(config: AppConfig) -> None:
    """Fallback interactive menu when no CLI flags are passed."""
    print(_Style.header("AI Chat Exporter  v" + config.version))

    # Merge preference
    print(f"  {_Style.BOLD}Merge all notes into one file?{_Style.RESET}")
    merge_input = input("  Filename (e.g. MyNotes.md) or ENTER for separate files: ").strip()
    merge_target: Optional[str] = None
    if merge_input:
        if not merge_input.endswith(".md"):
            merge_input += ".md"
        merge_target = merge_input
        print(_Style.ok(f"Merge mode → {merge_target}"))
    else:
        print(_Style.info("Individual mode — one file per question."))

    # Mode selection
    print(f"\n  {_Style.BOLD}Select mode:{_Style.RESET}")
    print(f"  {_Style.CYAN}1{_Style.RESET}  Live Watch  (auto-detect new HTML files)")
    print(f"  {_Style.CYAN}2{_Style.RESET}  Manual      (search & extract from a file)")
    print(f"  {_Style.CYAN}3{_Style.RESET}  Batch       (process all HTML files in a folder)")
    print(f"  {_Style.CYAN}4{_Style.RESET}  Full Page   (convert entire HTML page to Markdown)")
    print(f"  {_Style.CYAN}5{_Style.RESET}  Full Batch  (full-page export all HTML in a folder)")

    choice = input(f"\n  {_Style.CYAN}▸ Choice [1/2/3/4/5]: {_Style.RESET}").strip()

    if choice == "1":
        start_watcher(config.downloads_dir, merge_target=merge_target, config=config)

    elif choice == "2":
        raw = input("  HTML file path (or filename in Downloads): ").strip()
        path = Path(raw)
        if not path.is_absolute():
            path = config.downloads_dir / raw
        process_file(path, merge_target=merge_target, config=config)

    elif choice == "3":
        raw = input("  Folder path (ENTER for Downloads): ").strip()
        folder = Path(raw) if raw else config.downloads_dir
        batch_process(folder, merge_target=merge_target, config=config)

    elif choice == "4":
        raw = input("  HTML file path (or filename in Downloads): ").strip()
        path = Path(raw)
        if not path.is_absolute():
            path = config.downloads_dir / raw
        process_full_page(path, merge_target=merge_target, config=config)

    elif choice == "5":
        raw = input("  Folder path (ENTER for Downloads): ").strip()
        folder = Path(raw) if raw else config.downloads_dir
        batch_full_page(folder, merge_target=merge_target, config=config)

    else:
        print(_Style.err("Invalid choice."))


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Logging
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)

    # Config
    config = load_config()
    if args.downloads:
        config.downloads_path = args.downloads

    # Version
    if args.version:
        print(f"AI Chat Exporter v{config.version}")
        return

    # Merge target
    merge_target: Optional[str] = None
    if args.merge:
        merge_target = args.merge if args.merge.endswith(".md") else args.merge + ".md"

    # Dispatch
    if args.file and args.full_page:
        process_full_page(Path(args.file), merge_target=merge_target, config=config)
    elif args.batch and args.full_page:
        batch_full_page(Path(args.batch), merge_target=merge_target, config=config)
    elif args.file:
        process_file(Path(args.file), merge_target=merge_target, config=config)
    elif args.batch:
        batch_process(Path(args.batch), merge_target=merge_target, config=config)
    elif args.watch:
        start_watcher(config.downloads_dir, merge_target=merge_target, config=config)
    else:
        interactive_menu(config)


if __name__ == "__main__":
    main()