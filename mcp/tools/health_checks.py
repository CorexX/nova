"""Grouped runtime health checks for NOVA MCP tools."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from .paths import resolve_paths


def _count_md_files(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob("*.md"))


def _age_days(path: Path) -> int | None:
    if not path.exists():
        return None
    ts = path.stat().st_mtime
    then = datetime.fromtimestamp(ts, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    return max(0, int((now - then).total_seconds() // 86400))


async def run_grouped_checks(workspace_root: Path) -> list[dict[str, str]]:
    cfg = resolve_paths(workspace_root)

    core_files = [
        cfg.core_md,
        workspace_root / "mcp" / "nova_mcp_core_server.py",
        workspace_root / "mcp" / "tools" / "paths.py",
    ]
    core_ok = sum(1 for p in core_files if p.exists())

    vault_notes = _count_md_files(cfg.knowledge_root)
    current_age = _age_days(cfg.current_md)

    groups: list[dict[str, str]] = []
    groups.append({
        "name": "CORE",
        "status": "OK" if core_ok == len(core_files) else "WARN",
        "summary": f"MCP Tools 6 Tools | Python {sys.version_info.major}.{sys.version_info.minor} | Core Files {core_ok} vorhanden",
    })
    groups.append({
        "name": "VAULT",
        "status": "OK" if cfg.knowledge_root.exists() else "WARN",
        "summary": (
            f"Knowledge Root {'OK' if cfg.knowledge_root.exists() else 'MISSING'} | "
            f"Notes {vault_notes} | WORKLOG {'OK' if cfg.worklog_md.exists() else 'MISSING'} | "
            f"TICKETS {'OK' if cfg.tickets_md.exists() else 'MISSING'}"
        ),
    })
    groups.append({
        "name": "SEARCH",
        "status": "OK" if cfg.search_enabled else "WARN",
        "summary": (
            f"Search {'enabled' if cfg.search_enabled else 'disabled'} | "
            f"Chroma Path {'OK' if cfg.chroma_path.exists() else 'MISSING'}"
        ),
    })
    groups.append({
        "name": "CONTENT",
        "status": "OK",
        "summary": "Tool surface minimal (v2 only)",
    })
    groups.append({
        "name": "TODAY",
        "status": "OK",
        "summary": (
            "CURRENT "
            + (f"{current_age}d alt" if current_age is not None else "MISSING")
        ),
    })

    return groups


def format_grouped_simple(groups: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for g in groups:
        status = g.get("status", "INFO")
        name = g.get("name", "GROUP")
        summary = g.get("summary", "")
        lines.append(f"[{status}] **{name}:** {summary}")
    return "\n".join(lines)
