"""
Shared path resolution and configuration for NOVA MCP tools.

Config loading priority: ENV vars > nova.toml > Defaults
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NovaConfig:
    """Complete NOVA configuration."""

    # Paths
    core_root: Path
    knowledge_root: Path
    index_root: Path
    chroma_path: Path  # Chroma DB storage

    # Vault settings
    vault_name: str = "Work"
    daily_folder: str = "daily"

    # Search settings
    search_enabled: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    search_top_k: int = 5

    # Integrations
    n8n_base_url: str = ""
    n8n_api_key: str = ""
    n8n_insecure_tls: bool = False

    # Logging
    log_level: str = "INFO"

    # --- Path Properties ---

    @property
    def core_md(self) -> Path:
        return self.core_root / "core" / "CORE.md"

    @property
    def principles_md(self) -> Path:
        primary = self.core_root / "core" / "PRINCIPLES.md"
        if primary.exists():
            return primary

        fallback = self.core_root / "meta" / "PRINCIPLES.md"
        if fallback.exists():
            return fallback

        return primary

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
    def config_file(self) -> Path:
        parent_cfg = self.core_root.parent / "nova.toml"
        if parent_cfg.exists():
            return parent_cfg
        return self.core_root / "nova.toml"


# --- Config Loading ---


def _find_config_file(start_dir: Path) -> Path | None:
    """Sucht nova.toml im Workspace (aufwärts)."""
    candidates = [
        start_dir / "nova.toml",
        start_dir.parent / "nova.toml",  # NOVA Root
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_toml(path: Path) -> dict[str, Any]:
    """Lädt TOML-Config sicher."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _env_or(key: str, toml_val: Any, default: Any) -> Any:
    """Priorität: ENV > TOML > Default"""
    env_val = os.getenv(key)
    if env_val is not None:
        return env_val
    if toml_val is not None:
        return toml_val
    return default


def _resolve_path(
    raw: str | None, default: Path, workspace_root: Path
) -> Path:
    """Löst Pfad relativ zum Workspace auf."""
    if not raw:
        return default.resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    return candidate.resolve()


def _is_within(path: Path, parent: Path) -> bool:
    """True, wenn path in/unter parent liegt."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def load_config(workspace_root: Path) -> NovaConfig:
    """
    Lädt NOVA-Konfiguration mit Priorität:
    1. Environment Variables (höchste)
    2. nova.toml
    3. Defaults (niedrigste)
    """
    toml_path = _find_config_file(workspace_root)
    toml_data = _load_toml(toml_path) if toml_path else {}

    paths_cfg = toml_data.get("paths", {})
    vault_cfg = toml_data.get("vault", {})
    search_cfg = toml_data.get("search", {})
    integrations_cfg = toml_data.get("integrations", {})
    logging_cfg = toml_data.get("logging", {})

    # Defaults: Standalone (`workspace_root == core_root`) oder Embedded (`workspace_root/nova-core`)
    if (workspace_root / "mcp").exists() and (workspace_root / "core").exists():
        core_default = workspace_root
    elif (workspace_root / "nova-core" / "mcp").exists():
        core_default = workspace_root / "nova-core"
    else:
        core_default = workspace_root / "nova-core"

    knowledge_default = workspace_root / "nova-knowledge"

    workspace_root = workspace_root.resolve()

    # Paths
    core_root = _resolve_path(
        _env_or("NOVA_CORE_ROOT", paths_cfg.get("core_root"), None),
        core_default,
        workspace_root,
    )
    knowledge_root = _resolve_path(
        _env_or("NOVA_KNOWLEDGE_ROOT", paths_cfg.get("knowledge_root"), None),
        knowledge_default,
        workspace_root,
    )
    index_root = _resolve_path(
        _env_or("NOVA_INDEX_ROOT", paths_cfg.get("index_root"), None),
        workspace_root / ".nova" / "index",
        workspace_root,
    )
    
    # Chroma path: default to index_root/chroma
    chroma_path = _resolve_path(
        _env_or("NOVA_CHROMA_PATH", search_cfg.get("chroma_path"), None),
        index_root / "chroma",
        workspace_root,
    )

    # Safety rail: keep index/chroma local to active workspace by default.
    # Explicit opt-out for advanced setups:
    #   NOVA_ALLOW_EXTERNAL_PATHS=true
    allow_external_raw = os.getenv("NOVA_ALLOW_EXTERNAL_PATHS", "false")
    allow_external_paths = str(allow_external_raw).lower() in ("true", "1", "yes", "on")
    if not allow_external_paths:
        default_knowledge_root = (workspace_root / "nova-knowledge").resolve()
        default_index_root = (workspace_root / ".nova" / "index").resolve()

        if not _is_within(knowledge_root, workspace_root):
            knowledge_root = default_knowledge_root

        if not _is_within(index_root, workspace_root):
            index_root = default_index_root

        # Chroma must stay under index_root, otherwise force default.
        if not _is_within(chroma_path, index_root):
            chroma_path = (index_root / "chroma").resolve()
    
    # Search enabled (default True)
    search_enabled_raw = _env_or("NOVA_SEARCH_ENABLED", search_cfg.get("enabled"), True)
    search_enabled = str(search_enabled_raw).lower() not in ("false", "0", "no")

    n8n_insecure_tls_raw = _env_or(
        "N8N_INSECURE_TLS",
        integrations_cfg.get("n8n_insecure_tls"),
        False,
    )
    n8n_insecure_tls = str(n8n_insecure_tls_raw).lower() in ("true", "1", "yes", "on")

    return NovaConfig(
        core_root=core_root,
        knowledge_root=knowledge_root,
        index_root=index_root,
        chroma_path=chroma_path,
        vault_name=vault_cfg.get("name", "Work"),
        daily_folder=vault_cfg.get("daily_folder", "daily"),
        search_enabled=search_enabled,
        embedding_model=search_cfg.get("embedding_model", "all-MiniLM-L6-v2"),
        search_top_k=int(search_cfg.get("top_k", 5)),
        # Optional integration: n8n is not required for core startup.
        n8n_base_url=_env_or("N8N_BASE_URL", integrations_cfg.get("n8n_base_url"), ""),
        n8n_api_key=_env_or("N8N_API_KEY", integrations_cfg.get("n8n_api_key"), ""),
        n8n_insecure_tls=n8n_insecure_tls,
        log_level=logging_cfg.get("level", "INFO"),
    )


# --- Backwards Compatibility ---

# Alias für bestehenden Code
NovaPaths = NovaConfig


def resolve_paths(workspace_root: Path) -> NovaConfig:
    """Legacy-Funktion, nutzt jetzt load_config()."""
    return load_config(workspace_root)
