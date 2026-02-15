"""
AI Chat Exporter — Smart Title Generator.

Generates concise, clean headings from verbose user questions.
Two strategies:
  1. AI-powered  — calls an OpenAI-compatible API (needs API key in config)
  2. Heuristic   — local NLP-style cleanup (zero dependencies, always available)
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Filler / stop words to strip in heuristic mode
# ──────────────────────────────────────────────

_FILLER_STARTS = [
    "can you ", "could you ", "please ", "i want to ", "i need to ",
    "i want you to ", "i need you to ", "i would like to ", "help me ",
    "tell me ", "show me ", "write me ", "give me ", "explain to me ",
    "explain me ", "explain ", "what is ", "what are ", "how to ",
    "how do i ", "how can i ", "how do you ", "what does ", "what do ",
    "i am ", "i'm ", "we need to ", "let's ", "let us ",
]

_FILLER_ENDS = [
    " please", " thanks", " thank you", " for me", " asap",
    " in detail", " with examples", " with example",
    " step by step", " briefly",
]


# ──────────────────────────────────────────────
#  Heuristic Title Generator
# ──────────────────────────────────────────────

def _title_case(text: str) -> str:
    """Smart title-case that keeps short words lowercase (except first)."""
    small = {"a", "an", "the", "and", "but", "or", "for", "nor", "on",
             "at", "to", "by", "in", "of", "is", "it", "vs", "with"}
    words = text.split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or w.lower() not in small:
            result.append(w.capitalize())
        else:
            result.append(w.lower())
    return " ".join(result)


def generate_title_heuristic(question: str, max_length: int = 60) -> str:
    """
    Generate a clean, concise title from a verbose question using heuristics.

    Steps:
      1. Strip filler prefixes/suffixes
      2. Remove trailing punctuation
      3. Truncate to max_length at a word boundary
      4. Apply title case

    Args:
        question: The raw user question / phrase.
        max_length: Maximum title length in characters.

    Returns:
        A clean title string.
    """
    text = question.strip()

    # Remove filler starts (greedy — apply all that match)
    lower = text.lower()
    for filler in sorted(_FILLER_STARTS, key=len, reverse=True):
        if lower.startswith(filler):
            text = text[len(filler):]
            lower = text.lower()

    # Remove filler ends
    lower = text.lower()
    for filler in sorted(_FILLER_ENDS, key=len, reverse=True):
        if lower.endswith(filler):
            text = text[: -len(filler)]
            lower = text.lower()

    # Strip trailing punctuation
    text = text.strip(" ?.!,;:")

    # Truncate at word boundary
    if len(text) > max_length:
        truncated = text[:max_length].rsplit(" ", 1)[0]
        text = truncated.rstrip(" ,.;:-")

    # Title case
    text = _title_case(text)

    return text if text else question[:max_length]


# ──────────────────────────────────────────────
#  AI-Powered Title Generator (OpenAI-compatible)
# ──────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a title generator. Given a user's question or message from an AI chat, "
    "generate a short, concise title (3-8 words) suitable as a Markdown heading. "
    "Return ONLY the title text, no quotes, no punctuation at the end, no explanation."
)


def generate_title_ai(
    question: str,
    *,
    api_key: str,
    api_base: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
) -> Optional[str]:
    """
    Call an OpenAI-compatible API to generate a concise title.

    Args:
        question: The raw user question.
        api_key: API key for authentication.
        api_base: Base URL (supports OpenAI, Azure, local LLMs).
        model: Model identifier.

    Returns:
        Generated title, or None if the API call fails.
    """
    url = f"{api_base.rstrip('/')}/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "max_tokens": 30,
        "temperature": 0.3,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            title = data["choices"][0]["message"]["content"].strip().strip('"\'')
            logger.info("AI generated title: '%s'", title)
            return title
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, Exception) as exc:
        logger.warning("AI title generation failed (%s) — falling back to heuristic.", exc)
        return None


# ──────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────

def generate_smart_title(
    question: str,
    *,
    api_key: Optional[str] = None,
    api_base: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    max_length: int = 60,
) -> str:
    """
    Generate a clean title — uses AI if an API key is configured, 
    otherwise falls back to heuristic.

    Args:
        question: Raw user question / phrase.
        api_key: Optional OpenAI API key. If None or empty, uses heuristic.
        api_base: API base URL.
        model: Model name.
        max_length: Max title length for heuristic fallback.

    Returns:
        A concise, clean title string.
    """
    if api_key:
        ai_title = generate_title_ai(
            question, api_key=api_key, api_base=api_base, model=model
        )
        if ai_title:
            return ai_title

    return generate_title_heuristic(question, max_length=max_length)
