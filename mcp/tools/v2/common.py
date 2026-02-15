"""Shared helpers for v2 tool output and path handling."""

from __future__ import annotations

import json
import re
from pathlib import Path


def slugify(value: str) -> str:
    """Create a stable filesystem-safe slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "item"


def short_snippet(text: str, max_chars: int = 260) -> str:
    """Return a compact one-line snippet."""
    one_line = " ".join(text.split())
    if len(one_line) <= max_chars:
        return one_line
    return one_line[: max_chars - 3] + "..."


def json_text(payload: dict) -> str:
    """Serialize a payload for MCP text response."""
    return json.dumps(payload, ensure_ascii=False, indent=2)


def rel_or_abs(path: Path, base: Path) -> str:
    """Prefer workspace-relative path where possible."""
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())

