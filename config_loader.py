"""
Configuration loader for AI Chat Exporter.

Loads settings from config.json and provides typed access
with sensible defaults for all configuration values.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.json"


@dataclass
class AISettings:
    """Settings for AI-powered title generation."""
    enabled: bool = False
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"


@dataclass
class ExporterSettings:
    """Individual export settings."""
    strip_buttons: bool = True
    include_metadata: bool = True
    date_format: str = "%Y-%m-%d"
    heading_style: str = "ATX"
    wrap_code_blocks: bool = True
    max_filename_length: int = 50
    smart_titles: bool = True


@dataclass
class AppConfig:
    """Top-level application configuration."""
    default_save_folder: str = "Exported_Notes"
    downloads_path: str = ""
    supported_platforms: List[str] = field(
        default_factory=lambda: ["ChatGPT", "Gemini", "Claude", "Copilot", "DeepSeek"]
    )
    settings: ExporterSettings = field(default_factory=ExporterSettings)
    ai: AISettings = field(default_factory=AISettings)
    version: str = "3.0.0"

    @property
    def save_folder(self) -> Path:
        return Path(self.default_save_folder)

    @property
    def downloads_dir(self) -> Path:
        if self.downloads_path:
            return Path(self.downloads_path)
        return Path.home() / "Downloads"


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """
    Load configuration from JSON file with fallback defaults.

    Args:
        config_path: Optional path to config file. Uses default if None.

    Returns:
        Populated AppConfig dataclass.
    """
    path = config_path or CONFIG_PATH

    if not path.exists():
        logger.warning("Config file not found at %s — using defaults.", path)
        return AppConfig()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        settings_raw = raw.get("settings", {})
        settings = ExporterSettings(
            strip_buttons=settings_raw.get("strip_buttons", True),
            include_metadata=settings_raw.get("include_metadata", True),
            date_format=settings_raw.get("date_format", "%Y-%m-%d"),
            heading_style=settings_raw.get("heading_style", "ATX"),
            wrap_code_blocks=settings_raw.get("wrap_code_blocks", True),
            max_filename_length=settings_raw.get("max_filename_length", 50),
            smart_titles=settings_raw.get("smart_titles", True),
        )
        ai_raw = raw.get("ai", {})
        ai = AISettings(
            enabled=ai_raw.get("enabled", False),
            api_key=ai_raw.get("api_key", ""),
            api_base=ai_raw.get("api_base", "https://api.openai.com/v1"),
            model=ai_raw.get("model", "gpt-4o-mini"),
        )
        config = AppConfig(
            default_save_folder=raw.get("default_save_folder", "Exported_Notes"),
            downloads_path=raw.get("downloads_path", ""),
            supported_platforms=raw.get(
                "supported_platforms",
                ["ChatGPT", "Gemini", "Claude", "Copilot", "DeepSeek"],
            ),
            settings=settings,
            ai=ai,
            version=raw.get("version", "3.0.0"),
        )
        logger.info("Config loaded from %s", path)
        return config
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("Failed to parse config: %s — using defaults.", exc)
        return AppConfig()
