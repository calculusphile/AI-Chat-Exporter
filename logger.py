"""
Logging setup for AI Chat Exporter.

Provides consistent, configurable logging across all modules
with both console (rich) and file output.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent
LOG_FILE = LOG_DIR / "exporter.log"

_CONFIGURED = False


def setup_logging(level: int = logging.INFO, log_to_file: bool = True) -> None:
    """
    Configure the root logger with a console handler and optional file handler.

    Args:
        level: Logging level (default INFO).
        log_to_file: Whether to also write logs to exporter.log.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    # File handler (optional)
    if log_to_file:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)
