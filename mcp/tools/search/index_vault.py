"""
Tool: Index Vault
Builds a simple JSON semantic index for markdown notes.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from mcp.types import TextContent, Tool

from ..paths import resolve_paths
from .shared import batch_encode_texts, tool_logger


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_index_vault",
        description="Indexiert die Vault fuer Semantic Search. Laeuft inkrementell.",
        inputSchema={
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Komplett neu indexieren (ignoriert Cache)",
                    "default": False,
                },
            },
            "required": [],
        },
    )


def split_by_headers(content: str) -> list[dict]:
    chunks = []
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


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    log = tool_logger("index_vault")
    paths = resolve_paths(workspace_root)
    force = bool(args.get("force", False))

    vault_path = paths.knowledge_root
    index_path = paths.index_root
    hash_file = index_path / "file_hashes.json"
    semantic_index_file = index_path / "semantic_index.json"

    if not vault_path.exists():
        return [TextContent(type="text", text=f"[ERROR] Vault nicht gefunden: {vault_path}")]

    index_path.mkdir(parents=True, exist_ok=True)

    try:
        _ = batch_encode_texts(["warmup"])
    except ImportError as e:
        return [TextContent(type="text", text=f"[ERROR] Dependencies fehlen: {e}\n\nInstalliere mit:\npip install sentence-transformers")]

    existing_hashes = {} if force else _load_json(hash_file, {})
    existing_index = {"items": []} if force else _load_json(semantic_index_file, {"items": []})

    items_by_path: dict[str, list[dict]] = {}
    for item in existing_index.get("items", []):
        path = item.get("path")
        if not path:
            continue
        items_by_path.setdefault(path, []).append(item)

    md_files = list(vault_path.rglob("*.md"))
    current_paths = set()
    indexed = 0
    skipped = 0
    deleted = 0

    for md_file in md_files:
        try:
            rel_path = str(md_file.relative_to(workspace_root)).replace("\\", "/")
        except ValueError:
            rel_path = str(md_file).replace("\\", "/")
        current_paths.add(rel_path)

        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        if not force and existing_hashes.get(rel_path) == content_hash:
            skipped += 1
            continue

        chunks = split_by_headers(content)
        texts = [c["text"] for c in chunks]
        embeddings = batch_encode_texts(texts) if texts else []
        items_by_path[rel_path] = [
            {
                "id": f"{rel_path}#{i}",
                "path": rel_path,
                "section": chunk.get("section", ""),
                "chunk_index": i,
                "text": chunk["text"],
                "embedding": emb,
            }
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]

        existing_hashes[rel_path] = content_hash
        indexed += 1

    for old_path in list(existing_hashes.keys()):
        if old_path in current_paths:
            continue
        if old_path in items_by_path:
            del items_by_path[old_path]
            deleted += 1
        del existing_hashes[old_path]

    final_items = []
    for path_items in items_by_path.values():
        final_items.extend(path_items)

    payload = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "model": paths.embedding_model,
        "items": final_items,
    }

    hash_file.write_text(json.dumps(existing_hashes, indent=2, ensure_ascii=False), encoding="utf-8")
    semantic_index_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    log("Done")
    return [TextContent(type="text", text=f"""[OK] Index aktualisiert

| Metrik | Wert |
|--------|------|
| Neu/Geaendert | {indexed} |
| Unveraendert | {skipped} |
| Geloescht | {deleted} |
| **Dateien gesamt** | {len(current_paths)} |
| **Chunks im Index** | {len(final_items)} |
| Scope | `{vault_path}` |
| Index | `{semantic_index_file}` |
""")]
