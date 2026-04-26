"""Tool: nova_knowledge_query."""

from __future__ import annotations

from pathlib import Path

from mcp.types import TextContent, Tool

from .paths import resolve_paths
from .search_shared import tool_logger, semantic_search, full_text_search, hybrid_search, graph_search, facet_counts
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
                "mode": {
                    "type": "string",
                    "enum": ["semantic", "full_text", "hybrid", "graph"],
                    "default": "semantic",
                    "description": "Suchmodus: semantisch, SQLite-FTS oder kombiniert",
                },
                "dedupe": {
                    "type": "string",
                    "enum": ["none", "path", "section"],
                    "default": "section",
                    "description": "Deduplizierung: keine, pro Pfad oder pro Pfad+Section/Chunk",
                },
                "filters": {
                    "type": "object",
                    "description": "Optionale Facettenfilter für full_text-Suche, z.B. {'project':'nova','memory_type':['decision'],'tag':'mcp'}",
                    "additionalProperties": {"type": ["string", "array"]},
                },
                "include_facets": {
                    "type": "boolean",
                    "default": False,
                    "description": "Liefert verfügbare Facetten-Zählungen für die aktuelle Anfrage zurück",
                },
            },
            "required": ["query"],
        },
    )


def _normalize_filters(filters: object) -> dict[str, list[str]]:
    if not isinstance(filters, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for key, value in filters.items():
        facet_type = str(key).strip().lower()
        if not facet_type:
            continue
        raw_values = value if isinstance(value, list) else [value]
        clean = [str(item).strip().lower() for item in raw_values if str(item).strip()]
        if clean:
            normalized[facet_type] = sorted(set(clean))
    return normalized


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    log = tool_logger("knowledge_query")
    cfg = resolve_paths(workspace_root)
    query = str(args.get("query", "")).strip()
    project = str(args.get("project", "")).strip().lower()
    topic = str(args.get("topic", "")).strip().lower()
    limit = max(1, min(20, int(args.get("limit", 5))))
    mode = str(args.get("mode", "semantic")).strip().lower()
    if mode not in {"semantic", "full_text", "hybrid", "graph"}:
        mode = "semantic"
    dedupe = str(args.get("dedupe", "section")).strip().lower()
    if dedupe not in {"none", "path", "section"}:
        dedupe = "section"
    filters = _normalize_filters(args.get("filters"))
    include_facets = bool(args.get("include_facets", False))
    if not query:
        return [TextContent(type="text", text=json_text({"status": "error", "message": "query is required"}))]

    if filters and mode != "full_text":
        return [TextContent(type="text", text=json_text({
            "status": "error",
            "message": "Facet filters are currently supported only with mode=full_text.",
            "query": query,
            "mode": mode,
            "filters": filters,
        }))]

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
        if mode == "full_text":
            results = full_text_search(str(cfg.index_root), query, limit * 3, log, filters=filters)
        elif mode == "graph":
            results = graph_search(str(cfg.index_root), query, limit * 3, log)
        elif mode == "hybrid":
            results = hybrid_search(str(cfg.chroma_path), str(cfg.index_root), query, limit * 3, log)
        else:
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
        if not path:
            continue
        chunk_index = meta.get("chunk_index")
        match_id = str(item.get("id") or meta.get("id") or "")
        if dedupe == "path":
            dedupe_key = path
        elif dedupe == "section":
            dedupe_key = match_id or f"{path}#{meta.get('section') or ''}#{chunk_index if chunk_index is not None else ''}"
        else:
            dedupe_key = ""
        if dedupe_key and dedupe_key in seen:
            continue
        path_l = path.lower()
        if project and project not in path_l:
            continue
        if topic and topic not in path_l:
            continue
        if dedupe_key:
            seen.add(dedupe_key)
        distance = float(item.get("distance", 1.0))
        score = float(item.get("score", max(0.0, 1.0 - distance)))
        doc = str(item.get("doc") or item.get("text") or "")
        match = {
            "id": match_id,
            "path": path,
            "section": meta.get("section") or "",
            "line_start": meta.get("line_start"),
            "line_end": meta.get("line_end"),
            "memory_type": meta.get("memory_type") or "fact",
            "chunk_index": meta.get("chunk_index"),
            "facets": meta.get("facets") or {},
            "lifecycle_status": meta.get("lifecycle_status") or "active",
            "supersedes": meta.get("supersedes") or [],
            "snippet": short_snippet(doc),
            "score": round(score, 4),
            "why_relevant": item.get("why_relevant") or ("full_text_match" if mode == "full_text" else "semantic_similarity"),
            "citation": {
                "path": path,
                "section": meta.get("section") or "",
                "line_start": meta.get("line_start"),
                "line_end": meta.get("line_end"),
                "lifecycle_status": meta.get("lifecycle_status") or "active",
                "supersedes": meta.get("supersedes") or [],
            },
        }
        if meta.get("graph_via") is not None:
            match["graph_via"] = meta.get("graph_via")
        matches.append(match)
        if len(matches) >= limit:
            break

    payload = {
        "status": "ok",
        "query": query,
        "mode": mode,
        "project": project or None,
        "topic": topic or None,
        "dedupe": dedupe,
        "filters": filters,
        "matches": matches,
    }
    if include_facets:
        try:
            payload["available_facets"] = facet_counts(str(cfg.index_root), query, filters=filters)
        except Exception as exc:
            log(f"Error: {exc}")
            return [TextContent(type="text", text=json_text({
                "status": "error",
                "message": f"Facettenberechnung fehlgeschlagen ({type(exc).__name__}): {exc}",
                "query": query,
                "project": project or None,
                "topic": topic or None,
                "filters": filters,
            }))]
    return [TextContent(type="text", text=json_text(payload))]
