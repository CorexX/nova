"""Tool: nova_knowledge_query."""

from __future__ import annotations

from pathlib import Path

from mcp.types import TextContent, Tool

from ..paths import resolve_paths
from ..search.shared import tool_logger, semantic_search
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


def _fallback_keyword_matches(
    knowledge_root: Path,
    query: str,
    project: str,
    topic: str,
    limit: int,
) -> list[dict]:
    terms = [t.lower() for t in query.split() if len(t) > 2]
    if not terms:
        return []

    matches: list[dict] = []
    for md in sorted(knowledge_root.rglob("*.md")):
        rel = md.as_posix()
        rel_l = rel.lower()
        if project and project not in rel_l:
            continue
        if topic and topic not in rel_l:
            continue
        try:
            content = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        low = content.lower()
        score_raw = sum(low.count(t) for t in terms)
        if score_raw <= 0:
            continue
        matches.append(
            {
                "path": rel,
                "snippet": short_snippet(content),
                "score": round(min(0.99, 0.2 + (score_raw / 20.0)), 4),
                "why_relevant": "keyword_overlap_fallback",
            }
        )
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:limit]


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    log = tool_logger("knowledge_query")
    cfg = resolve_paths(workspace_root)
    query = str(args.get("query", "")).strip()
    project = str(args.get("project", "")).strip().lower()
    topic = str(args.get("topic", "")).strip().lower()
    limit = max(1, min(20, int(args.get("limit", 5))))
    if not query:
        return [TextContent(type="text", text=json_text({"status": "error", "message": "query is required"}))]

    results = []
    if cfg.search_enabled:
        try:
            results = semantic_search(str(cfg.chroma_path), query, limit * 3, log)
        except Exception as exc:
            log(f"Error: {exc}")
            fallback = _fallback_keyword_matches(cfg.knowledge_root, query, project, topic, limit)
            payload = {
                "status": "fallback",
                "message": f"Semantische Suche nicht verfuegbar ({type(exc).__name__}). Keyword-Fallback verwendet.",
                "query": query,
                "project": project or None,
                "topic": topic or None,
                "matches": fallback,
            }
            return [TextContent(type="text", text=json_text(payload))]
    else:
        fallback = _fallback_keyword_matches(cfg.knowledge_root, query, project, topic, limit)
        payload = {
            "status": "fallback",
            "message": "Semantische Suche deaktiviert. Keyword-Fallback verwendet.",
            "query": query,
            "project": project or None,
            "topic": topic or None,
            "matches": fallback,
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
