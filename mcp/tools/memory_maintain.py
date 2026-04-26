"""Tool: nova_memory_maintain."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.types import TextContent, Tool

from .common import json_text
from .paths import resolve_paths
from .search_shared import batch_encode_texts


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_memory_maintain",
        description="Runs memory-engine maintenance: health, index, or validate.",
        inputSchema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["health", "index", "validate"],
                    "description": "Maintenance operation",
                },
                "force": {
                    "type": "boolean",
                    "description": "For index: rebuild changed files from scratch",
                    "default": False,
                },
            },
            "required": ["operation"],
        },
    )


def _classify_memory_type(section_name: str, text: str) -> str:
    haystack = f"{section_name}\n{text}".lower()
    if any(word in haystack for word in ("decision", "entscheidung", "adr")):
        return "decision"
    if any(word in haystack for word in ("constraint", "constraints", "einschränkung", "guardrail")):
        return "constraint"
    if any(word in haystack for word in ("open question", "open questions", "offene frage", "frage")):
        return "question"
    if any(word in haystack for word in ("todo", "task", "next action", "- [ ]")):
        return "task"
    if any(word in haystack for word in ("procedure", "workflow", "playbook", "how to")):
        return "procedure"
    if any(word in haystack for word in ("source", "reference", "quelle")):
        return "source"
    return "fact"


def _split_by_headers(content: str) -> list[dict[str, Any]]:
    lines = content.splitlines()
    if not lines:
        return []

    header_indexes = [
        idx for idx, line in enumerate(lines)
        if re.match(r"^#{1,2}\s+.+", line)
    ]
    if not header_indexes and content.strip():
        text = content.strip()[:2000]
        return [{
            "text": text,
            "section": "",
            "line_start": 1,
            "line_end": len(lines),
            "memory_type": _classify_memory_type("", text),
        }]

    chunks: list[dict[str, Any]] = []
    for pos, start_idx in enumerate(header_indexes):
        end_idx = header_indexes[pos + 1] - 1 if pos + 1 < len(header_indexes) else len(lines) - 1
        while end_idx > start_idx and not lines[end_idx].strip():
            end_idx -= 1
        raw_section = "\n".join(lines[start_idx:end_idx + 1]).strip()
        if not raw_section:
            continue
        header_match = re.match(r"^(#{1,2})\s+(.+)", lines[start_idx])
        section_name = header_match.group(2).strip() if header_match else ""
        chunks.append({
            "text": raw_section[:2000],
            "section": section_name,
            "line_start": start_idx + 1,
            "line_end": end_idx + 1,
            "memory_type": _classify_memory_type(section_name, raw_section),
        })
    return chunks


async def _run_health(workspace_root: Path) -> dict:
    from .health_checks import format_grouped_simple, run_grouped_checks

    groups = await run_grouped_checks(workspace_root)
    return {
        "status": "ok",
        "operation": "health",
        "details": {"summary": format_grouped_simple(groups), "groups": groups},
        "artifacts": [],
    }


async def _run_validate(workspace_root: Path) -> dict:
    cfg = resolve_paths(workspace_root)
    problems: list[str] = []
    if not cfg.knowledge_root.exists():
        problems.append(f"knowledge_root missing: {cfg.knowledge_root}")
    if cfg.knowledge_root.resolve() == cfg.core_root.resolve():
        problems.append("knowledge_root must not equal core_root")
    return {
        "status": "ok" if not problems else "warn",
        "operation": "validate",
        "details": {
            "problems": problems,
            "knowledge_root": str(cfg.knowledge_root),
            "index_root": str(cfg.index_root),
        },
        "artifacts": [],
    }


async def _run_index(args: dict, workspace_root: Path) -> dict:
    cfg = resolve_paths(workspace_root)
    force = bool(args.get("force", False))
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
                path = str(item.get("path", ""))
                if path:
                    existing_items_by_path.setdefault(path, []).append(item)
        except Exception:
            existing_items_by_path = {}

    md_files = list(vault_path.rglob("*.md"))
    current_paths: set[str] = set()
    skipped = deleted = indexed = 0

    for md_file in md_files:
        try:
            rel_path = str(md_file.relative_to(workspace_root)).replace("\\", "/")
        except ValueError:
            rel_path = str(md_file).replace("\\", "/")
        current_paths.add(rel_path)

        content = md_file.read_text(encoding="utf-8", errors="ignore")
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
                    "message": f"Embedding failed ({type(exc).__name__}): {exc}",
                    "hint": "Install sentence-transformers or disable semantic search.",
                },
                "artifacts": [],
            }

        existing_items_by_path[rel_path] = [
            {
                "id": f"{rel_path}#{idx}",
                "path": rel_path,
                "section": chunk.get("section", ""),
                "line_start": chunk.get("line_start"),
                "line_end": chunk.get("line_end"),
                "memory_type": chunk.get("memory_type", "fact"),
                "chunk_index": idx,
                "text": chunk["text"],
                "embedding": emb,
            }
            for idx, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]
        existing_hashes[rel_path] = content_hash
        indexed += 1

    for old_path in list(existing_hashes.keys()):
        if old_path not in current_paths:
            existing_items_by_path.pop(old_path, None)
            del existing_hashes[old_path]
            deleted += 1

    all_items = [item for items in existing_items_by_path.values() for item in items]
    semantic_index = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "model": cfg.embedding_model,
        "items": all_items,
    }
    hash_file.write_text(json.dumps(existing_hashes, indent=2, ensure_ascii=False), encoding="utf-8")
    semantic_index_file.write_text(json.dumps(semantic_index, ensure_ascii=False), encoding="utf-8")

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
    op = str(args.get("operation", "")).strip().lower()
    if op == "health":
        payload = await _run_health(workspace_root)
    elif op == "index":
        payload = await _run_index(args, workspace_root)
    elif op == "validate":
        payload = await _run_validate(workspace_root)
    else:
        payload = {
            "status": "error",
            "operation": op,
            "details": {"message": "Unsupported operation. Allowed: health, index, validate"},
            "artifacts": [],
        }
    return [TextContent(type="text", text=json_text(payload))]
