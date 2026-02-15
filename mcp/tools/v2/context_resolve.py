"""Tool: nova_context_resolve."""

from __future__ import annotations

from pathlib import Path

from mcp.types import TextContent, Tool

from ..paths import resolve_paths
from ..search.shared import tool_logger, semantic_search
from .common import json_text, rel_or_abs, short_snippet


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_context_resolve",
        description=(
            "Loest relevanten Arbeitskontext selektiv auf: priorisiert, dedupliziert, "
            "budgetiert und mit Quellen/Confidence."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Aktuelle Arbeitsfrage"},
                "project_hint": {"type": "string", "description": "Optionaler Projekt-Hinweis"},
                "token_budget": {
                    "type": "integer",
                    "description": "Token-Budget fuer Kontextauswahl",
                    "default": 1200,
                },
                "scope": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optionale Scope-Filter, z.B. ['projects','resources']",
                },
            },
            "required": ["query"],
        },
    )


def _path_in_scope(path: str, scope: list[str]) -> bool:
    if not scope:
        return True
    path_l = path.lower()
    return any(s.lower() in path_l for s in scope)


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    log = tool_logger("context_resolve")
    cfg = resolve_paths(workspace_root)
    query = str(args.get("query", "")).strip()
    project_hint = str(args.get("project_hint", "")).strip()
    token_budget = max(300, int(args.get("token_budget", 1200)))
    scope = [str(s) for s in (args.get("scope") or [])]
    if not query:
        return [TextContent(type="text", text=json_text({"status": "error", "message": "query is required"}))]

    top_k = max(3, min(12, token_budget // 180))
    if not cfg.search_enabled:
        payload = {
            "status": "error",
            "message": "Semantische Suche ist deaktiviert (search_enabled=false).",
            "query": query,
            "project_hint": project_hint or None,
        }
        return [TextContent(type="text", text=json_text(payload))]

    try:
        results = semantic_search(str(cfg.chroma_path), query, top_k * 2, log)
    except Exception as exc:
        log(f"Search failed: {exc}")
        payload = {
            "status": "error",
            "message": f"Semantische Suche fehlgeschlagen ({type(exc).__name__}): {exc}",
            "query": query,
            "project_hint": project_hint or None,
        }
        return [TextContent(type="text", text=json_text(payload))]

    items: list[dict] = []
    seen: set[str] = set()
    for item in results:
        meta = item.get("meta") or {}
        path = str(item.get("path") or meta.get("path") or "")
        if not path or path in seen or not _path_in_scope(path, scope):
            continue
        seen.add(path)
        distance = float(item.get("distance", 1.0))
        score = float(max(0.0, 1.0 - distance))
        doc = str(item.get("doc") or item.get("text") or "")
        items.append({
            "path": path,
            "score": round(score, 4),
            "snippet": short_snippet(doc),
            "reason": "semantic_match",
        })
        if len(items) >= top_k:
            break

    if project_hint:
        hint_l = project_hint.lower()
        for item in items:
            if hint_l in item["path"].lower():
                item["score"] = round(min(0.999, item["score"] + 0.05), 4)
                item["reason"] += "+project_hint_boost"
        items.sort(key=lambda x: x["score"], reverse=True)

    confidence = 0.0 if not items else round(min(0.99, sum(i["score"] for i in items) / len(items)), 4)
    sources = [{"path": i["path"], "score": i["score"]} for i in items]
    context_items = [
        {
            "path": i["path"],
            "snippet": i["snippet"],
            "why_selected": i["reason"],
        }
        for i in items
    ]

    payload = {
        "query": query,
        "project_hint": project_hint or None,
        "selection_reason": "semantic_search",
        "confidence": confidence,
        "token_budget": token_budget,
        "context_items": context_items,
        "sources": sources,
        "workspace_root": rel_or_abs(workspace_root, workspace_root),
    }
    return [TextContent(type="text", text=json_text(payload))]
