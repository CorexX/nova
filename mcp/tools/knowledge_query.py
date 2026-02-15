"""Tool: nova_knowledge_query."""

from __future__ import annotations

from pathlib import Path

from mcp.types import TextContent, Tool

from .paths import resolve_paths
from .search_shared import tool_logger, semantic_search
from .common import json_text, short_snippet


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_knowledge_query",
        description="Fragt Wissen semantisch ab und liefert strukturierte Treffer mit Relevanzbegruendung.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Wissensfrage"},
                "project": {"type": "string", "description": "Optionaler Projektfilter (substring auf Pfad)"},
                "topic": {"type": "string", "description": "Optionaler Topic-Filter (substring auf Pfad)"},
                "limit": {"type": "integer", "default": 5, "description": "Maximale Trefferanzahl"},
            },
            "required": ["query"],
        },
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    log = tool_logger("knowledge_query")
    cfg = resolve_paths(workspace_root)
    query = str(args.get("query", "")).strip()
    project = str(args.get("project", "")).strip().lower()
    topic = str(args.get("topic", "")).strip().lower()
    limit = max(1, min(20, int(args.get("limit", 5))))
    if not query:
        return [TextContent(type="text", text=json_text({"status": "error", "message": "query is required"}))]

    if not cfg.search_enabled:
        payload = {
            "status": "error",
            "message": "Semantische Suche ist deaktiviert (search_enabled=false).",
            "query": query,
            "project": project or None,
            "topic": topic or None,
        }
        return [TextContent(type="text", text=json_text(payload))]

    try:
        results = semantic_search(str(cfg.chroma_path), query, limit * 3, log)
    except Exception as exc:
        log(f"Error: {exc}")
        payload = {
            "status": "error",
            "message": f"Semantische Suche fehlgeschlagen ({type(exc).__name__}): {exc}",
            "query": query,
            "project": project or None,
            "topic": topic or None,
        }
        return [TextContent(type="text", text=json_text(payload))]

    matches: list[dict] = []
    seen: set[str] = set()
    for item in results:
        meta = item.get("meta") or {}
        path = str(item.get("path") or meta.get("path") or "")
        if not path or path in seen:
            continue
        path_l = path.lower()
        if project and project not in path_l:
            continue
        if topic and topic not in path_l:
            continue
        seen.add(path)
        distance = float(item.get("distance", 1.0))
        score = float(max(0.0, 1.0 - distance))
        doc = str(item.get("doc") or item.get("text") or "")
        matches.append({
            "path": path,
            "snippet": short_snippet(doc),
            "score": round(score, 4),
            "why_relevant": "semantic_similarity",
        })
        if len(matches) >= limit:
            break

    payload = {
        "status": "ok",
        "query": query,
        "project": project or None,
        "topic": topic or None,
        "matches": matches,
    }
    return [TextContent(type="text", text=json_text(payload))]
