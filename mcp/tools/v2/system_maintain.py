"""Tool: nova_system_maintain."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
import threading
from pathlib import Path
from typing import Any

from mcp.types import TextContent, Tool

from ..paths import resolve_paths
from ..search.shared import batch_encode_texts
from .common import json_text

_BACKEND_LOCK = threading.Lock()
_BACKEND_READY = False
_BACKEND_WORKSPACE: Path | None = None
_BACKEND_ERROR: str | None = None
_CHROMADB: Any = None
_COLLECTION: Any = None
_EMBEDDER: Any = None


def _log(message: str) -> None:
    print(f"[NOVA | system_maintain] {message}", file=sys.stderr, flush=True)


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_system_maintain",
        description="Fuehrt Betriebsaufgaben aus: health, index oder restart.",
        inputSchema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["health", "index", "restart"],
                    "description": "Gewuenschte Wartungsoperation",
                },
                "force": {
                    "type": "boolean",
                    "description": "Optional fuer index: full rebuild",
                    "default": False,
                },
                "delay_seconds": {
                    "type": "integer",
                    "description": "Optional fuer restart: Delay in Sekunden (1-30)",
                    "default": 2,
                },
            },
            "required": ["operation"],
        },
    )


def _split_by_headers(content: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    sections = re.split(r"\n(?=#{1,2}\s)", content)
    for section in sections:
        if not section.strip():
            continue
        header_match = re.match(r"^(#{1,2})\s+(.+)", section)
        section_name = header_match.group(2).strip() if header_match else ""
        chunks.append({"text": section.strip()[:2000], "section": section_name})
    if not chunks and content.strip():
        chunks.append({"text": content.strip()[:2000], "section": ""})
    return chunks


def _ensure_index_backend(workspace_root: Path, force_reload: bool = False) -> tuple[bool, str]:
    global _BACKEND_READY, _BACKEND_WORKSPACE, _BACKEND_ERROR

    ws = workspace_root.resolve()
    with _BACKEND_LOCK:
        needs_reload = (
            force_reload
            or not _BACKEND_READY
            or _BACKEND_WORKSPACE is None
            or _BACKEND_WORKSPACE != ws
        )
        if not needs_reload:
            return True, "ready"

        try:
            _ = batch_encode_texts(["warmup"])

            _BACKEND_READY = True
            _BACKEND_WORKSPACE = ws
            _BACKEND_ERROR = None
            return True, "initialized"
        except Exception as exc:
            _BACKEND_READY = False
            _BACKEND_ERROR = f"{type(exc).__name__}: {exc}"
            return False, _BACKEND_ERROR


def initialize_on_startup(workspace_root: Path) -> None:
    ok, message = _ensure_index_backend(workspace_root)
    if ok:
        _log("Index backend initialized at startup.")
    else:
        _log(f"Index backend init failed: {message}")


def _schedule_restart(delay_seconds: int) -> dict:
    delay = max(1, min(30, int(delay_seconds)))

    def _terminate_process() -> None:
        os._exit(0)

    timer = threading.Timer(delay, _terminate_process)
    timer.daemon = True
    timer.start()
    return {
        "status": "ok",
        "operation": "restart",
        "details": {"delay_seconds": delay},
        "artifacts": [],
    }


async def _run_health(workspace_root: Path) -> dict:
    from ..health.checks import format_grouped_simple, run_grouped_checks

    groups = await run_grouped_checks(workspace_root)
    return {
        "status": "ok",
        "operation": "health",
        "details": {"summary": format_grouped_simple(groups)},
        "artifacts": [],
    }


async def _run_index(args: dict, workspace_root: Path) -> dict:
    cfg = resolve_paths(workspace_root)
    force = bool(args.get("force", False))
    ok, message = _ensure_index_backend(workspace_root, force_reload=force)
    if not ok:
        return {
            "status": "error",
            "operation": "index",
            "details": {
                "message": f"Dependencies fehlen oder Backend nicht verfuegbar: {message}",
                "hint": "Installiere mit: pip install sentence-transformers",
            },
            "artifacts": [],
        }

    vault_path = cfg.knowledge_root
    index_path = cfg.index_root
    hash_file = index_path / "file_hashes.json"
    semantic_index_file = index_path / "semantic_index.json"

    if not vault_path.exists():
        return {
            "status": "error",
            "operation": "index",
            "details": {"message": f"Vault not found: {vault_path}"},
            "artifacts": [],
        }

    index_path.mkdir(parents=True, exist_ok=True)

    existing_hashes: dict[str, str] = {}
    if hash_file.exists() and not force:
        try:
            existing_hashes = json.loads(hash_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_hashes = {}

    existing_items_by_path: dict[str, list[dict[str, Any]]] = {}
    if semantic_index_file.exists() and not force:
        try:
            existing_index = json.loads(semantic_index_file.read_text(encoding="utf-8"))
            for item in existing_index.get("items", []):
                if not isinstance(item, dict):
                    continue
                path = str(item.get("path", ""))
                if not path:
                    continue
                existing_items_by_path.setdefault(path, []).append(item)
        except Exception:
            existing_items_by_path = {}

    md_files = list(vault_path.rglob("*.md"))
    current_paths: set[str] = set()
    skipped = 0
    deleted = 0
    indexed = 0

    for md_file in md_files:
        try:
            rel_path = str(md_file.relative_to(workspace_root)).replace("\\", "/")
        except ValueError:
            rel_path = str(md_file).replace("\\", "/")
        current_paths.add(rel_path)

        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        if not force and existing_hashes.get(rel_path) == content_hash:
            skipped += 1
            continue

        chunks = _split_by_headers(content)

        texts = [chunk["text"] for chunk in chunks]
        try:
            embeddings = batch_encode_texts(texts) if texts else []
        except Exception as exc:
            return {
                "status": "error",
                "operation": "index",
                "details": {
                    "message": f"Embedding fehlgeschlagen ({type(exc).__name__}): {exc}",
                    "hint": "Pruefe sentence-transformers Installation und Modellzugriff.",
                },
                "artifacts": [],
            }
        new_items: list[dict[str, Any]] = []
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            new_items.append(
                {
                    "id": f"{rel_path}#{idx}",
                    "path": rel_path,
                    "section": chunk.get("section", ""),
                    "chunk_index": idx,
                    "text": chunk["text"],
                    "embedding": emb,
                }
            )
        existing_items_by_path[rel_path] = new_items
        existing_hashes[rel_path] = content_hash
        indexed += 1

    for old_path in list(existing_hashes.keys()):
        if old_path in current_paths:
            continue
        if old_path in existing_items_by_path:
            del existing_items_by_path[old_path]
            deleted += 1
        del existing_hashes[old_path]

    all_items: list[dict[str, Any]] = []
    for path_items in existing_items_by_path.values():
        all_items.extend(path_items)

    semantic_index = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "model": cfg.embedding_model,
        "items": all_items,
    }

    hash_file.write_text(
        json.dumps(existing_hashes, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    semantic_index_file.write_text(
        json.dumps(semantic_index, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "operation": "index",
        "details": {
            "force": force,
            "changed_files": indexed,
            "unchanged_files": skipped,
            "deleted_files": deleted,
            "total_files": len(md_files),
            "total_chunks": len(all_items),
            "scope": str(vault_path),
            "index_file": str(semantic_index_file),
        },
        "artifacts": [],
    }


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    _ = resolve_paths(workspace_root)
    op = str(args.get("operation", "")).strip().lower()

    if op == "health":
        payload = await _run_health(workspace_root)
    elif op == "index":
        payload = await _run_index(args, workspace_root)
    elif op == "restart":
        payload = _schedule_restart(int(args.get("delay_seconds", 2)))
    else:
        payload = {
            "status": "error",
            "operation": op,
            "details": {"message": "Unsupported operation. Allowed: health, index, restart"},
            "artifacts": [],
        }

    return [TextContent(type="text", text=json_text(payload))]
