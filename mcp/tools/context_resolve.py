"""Tool: nova_context_resolve."""

from __future__ import annotations

from pathlib import Path
import re

from mcp.types import TextContent, Tool

from .paths import resolve_paths
from .search_shared import tool_logger, semantic_search
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
                "include_inventory": {
                    "type": "boolean",
                    "default": False,
                    "description": "Optional: liefert eine kompakte Ordneruebersicht (sinnvoll fuer session init).",
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


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _build_inventory(cfg, workspace_root: Path, scope: list[str]) -> dict:
    knowledge_root = cfg.knowledge_root
    if not knowledge_root.exists():
        return {
            "status": "unavailable",
            "reason": "knowledge_root_missing",
            "knowledge_root": rel_or_abs(knowledge_root, workspace_root),
        }

    all_top = sorted([d.name for d in knowledge_root.iterdir() if d.is_dir()])
    top_level = all_top[:12]

    ignore_names = {
        "knowledge",
        "docs",
        "notes",
        "assets",
        "archive",
        "research",
        "prompts",
        "__pycache__",
    }
    signals = ("CURRENT.md", "BACKLOG.md", "README.md")
    project_paths: list[str] = []

    candidates: list[Path] = []
    for path in knowledge_root.rglob("*"):
        if not path.is_dir():
            continue
        if path.name.lower() in ignore_names:
            continue
        if not any((path / filename).exists() for filename in signals):
            continue
        rel_path = path.relative_to(knowledge_root).as_posix()
        if not _path_in_scope(rel_path, scope):
            continue
        candidates.append(path)

    # Deduplicate nested project-like folders.
    # Keep nested folders only when they are likely explicit sub-project containers.
    for path in sorted(candidates, key=lambda p: len(p.parts)):
        rel_l = path.relative_to(knowledge_root).as_posix().lower()
        has_parent_candidate = any(parent in candidates for parent in path.parents)
        if has_parent_candidate and "/projekte/" not in rel_l and "/projects/" not in rel_l:
            continue
        project_paths.append(path.relative_to(knowledge_root).as_posix())

    project_paths = sorted(set(project_paths))
    return {
        "status": "ok",
        "knowledge_root": rel_or_abs(knowledge_root, workspace_root),
        "top_level_dirs": top_level,
        "project_paths": project_paths[:20],
        "counts": {
            "top_level_dirs": len(all_top),
            "project_paths": len(project_paths),
        },
    }


def _extract_numbered_section(md_text: str, heading: str, max_items: int = 8) -> list[str]:
    lines = md_text.splitlines()
    section_lines: list[str] = []
    in_section = False
    heading_l = heading.lower()
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("## "):
            title = line[3:].strip().lower()
            if in_section and title != heading_l:
                break
            in_section = title == heading_l
            continue
        if in_section:
            section_lines.append(line)

    out: list[str] = []
    for line in section_lines:
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            out.append(m.group(1).strip())
        if len(out) >= max_items:
            break
    return out


def _core_directives(cfg, workspace_root: Path) -> dict:
    core_md = cfg.core_md
    if not core_md.exists():
        return {
            "status": "unavailable",
            "reason": "core_missing",
            "core_path": rel_or_abs(core_md, workspace_root),
        }

    try:
        text = core_md.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {
            "status": "unavailable",
            "reason": "core_read_failed",
            "core_path": rel_or_abs(core_md, workspace_root),
        }

    hard_rules = _extract_numbered_section(text, "Nicht verhandelbare Regeln", max_items=8)
    priorities = _extract_numbered_section(text, "Prioritaet bei Konflikten", max_items=4)
    return {
        "status": "ok",
        "core_path": rel_or_abs(core_md, workspace_root),
        "hard_rules": hard_rules,
        "priorities": priorities,
        "fallback_policy": "Wenn session init fehlschlaegt: core/CORE.md lokal lesen und mit bestmoeglichem lokalen Kontext fortfahren.",
    }


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    log = tool_logger("context_resolve")
    cfg = resolve_paths(workspace_root)
    query = str(args.get("query", "")).strip()
    project_hint = str(args.get("project_hint", "")).strip()
    token_budget = max(300, int(args.get("token_budget", 1200)))
    scope = [str(s) for s in (args.get("scope") or [])]
    include_inventory = _as_bool(args.get("include_inventory", False))
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
    if include_inventory:
        payload["inventory"] = _build_inventory(cfg, workspace_root, scope)
    if query.lower() == "session init":
        payload["core_directives"] = _core_directives(cfg, workspace_root)
    return [TextContent(type="text", text=json_text(payload))]
