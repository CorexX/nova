"""Path resolution and configuration for the NOVA memory engine.

Priority: environment variables > nova.toml > defaults.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NovaMemoryConfig:
    """Minimal configuration for NOVA 2.0."""

    core_root: Path
    knowledge_root: Path
    index_root: Path
    chroma_path: Path
    search_enabled: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    search_top_k: int = 5

    @property
    def current_md(self) -> Path:
        return self.knowledge_root / "CURRENT.md"

    @property
    def tickets_md(self) -> Path:
        return self.knowledge_root / "TICKETS.md"

    @property
    def worklog_md(self) -> Path:
        return self.knowledge_root / "WORKLOG.md"

    @property
    def principles_md(self) -> Path:
        return self.core_root / "meta" / "PRINCIPLES.md"


def _find_config_file(start_dir: Path) -> Path | None:
    for candidate in (start_dir / "nova.toml", start_dir.parent / "nova.toml"):
        if candidate.exists():
            return candidate
    return None


def _load_toml(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _configured_value(env_key: str, toml_value: Any) -> Any:
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value
    return toml_value


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() not in {"false", "0", "no", "off"}


def _resolve_path(raw: str | None, default: Path, workspace_root: Path) -> Path:
    if not raw:
        return default.resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    return candidate.resolve()


def load_config(workspace_root: Path) -> NovaMemoryConfig:
    workspace_root = workspace_root.resolve()
    toml_data = _load_toml(_find_config_file(workspace_root))
    paths_cfg = toml_data.get("paths", {})
    search_cfg = toml_data.get("search", {})

    core_default = workspace_root if (workspace_root / "mcp").exists() else workspace_root / "nova"
    knowledge_default = workspace_root.parent / "nova-knowledge"
    index_default = workspace_root / ".nova" / "index"

    core_root = _resolve_path(
        _configured_value("NOVA_CORE_ROOT", paths_cfg.get("core_root")),
        core_default,
        workspace_root,
    )
    knowledge_root = _resolve_path(
        _configured_value("NOVA_KNOWLEDGE_ROOT", paths_cfg.get("knowledge_root")),
        knowledge_default,
        workspace_root,
    )
    index_root = _resolve_path(
        _configured_value("NOVA_INDEX_ROOT", paths_cfg.get("index_root")),
        index_default,
        workspace_root,
    )
    chroma_path = _resolve_path(
        _configured_value("NOVA_CHROMA_PATH", search_cfg.get("chroma_path")),
        index_root / "chroma",
        workspace_root,
    )

    search_enabled = _as_bool(
        _configured_value("NOVA_SEARCH_ENABLED", search_cfg.get("enabled")),
        True,
    )
    embedding_model = str(
        _configured_value("NOVA_EMBEDDING_MODEL", search_cfg.get("embedding_model"))
        or "all-MiniLM-L6-v2"
    )
    search_top_k = int(search_cfg.get("top_k", 5))

    return NovaMemoryConfig(
        core_root=core_root,
        knowledge_root=knowledge_root,
        index_root=index_root,
        chroma_path=chroma_path,
        search_enabled=search_enabled,
        embedding_model=embedding_model,
        search_top_k=search_top_k,
    )


# Backwards-compatible aliases for existing tool modules.
NovaConfig = NovaMemoryConfig
NovaPaths = NovaMemoryConfig


def resolve_paths(workspace_root: Path) -> NovaMemoryConfig:
    return load_config(workspace_root)
