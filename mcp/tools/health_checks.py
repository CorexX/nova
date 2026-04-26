"""Grouped health checks for the NOVA memory engine."""

from __future__ import annotations

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
    then = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    return max(0, int((now - then).total_seconds() // 86400))


async def run_grouped_checks(workspace_root: Path) -> list[dict[str, str]]:
    cfg = resolve_paths(workspace_root)
    semantic_index = cfg.index_root / "semantic_index.json"
    hash_file = cfg.index_root / "file_hashes.json"

    groups: list[dict[str, str]] = []
    groups.append({
        "name": "VAULT",
        "status": "OK" if cfg.knowledge_root.exists() else "WARN",
        "summary": (
            f"knowledge_root={cfg.knowledge_root} | "
            f"exists={cfg.knowledge_root.exists()} | "
            f"markdown_files={_count_md_files(cfg.knowledge_root)}"
        ),
    })
    groups.append({
        "name": "INDEX",
        "status": "OK" if semantic_index.exists() else "WARN",
        "summary": (
            f"index_root={cfg.index_root} | "
            f"semantic_index={semantic_index.exists()} | "
            f"file_hashes={hash_file.exists()} | "
            f"age_days={_age_days(semantic_index)}"
        ),
    })
    groups.append({
        "name": "SEARCH",
        "status": "OK" if cfg.search_enabled else "WARN",
        "summary": (
            f"enabled={cfg.search_enabled} | "
            f"embedding_model={cfg.embedding_model} | "
            f"top_k={cfg.search_top_k}"
        ),
    })
    groups.append({
        "name": "BOUNDARY",
        "status": "OK",
        "summary": "memory/context only; no operator runtime responsibilities",
    })
    return groups


def format_grouped_simple(groups: list[dict[str, str]]) -> str:
    return "\n".join(
        f"[{group.get('status', 'INFO')}] **{group.get('name', 'GROUP')}:** {group.get('summary', '')}"
        for group in groups
    )
