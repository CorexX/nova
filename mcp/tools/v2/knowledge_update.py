"""Tool: nova_knowledge_update."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mcp.types import TextContent, Tool

from ..paths import resolve_paths
from .common import json_text, rel_or_abs, slugify


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_knowledge_update",
        description="Persistiert Erkenntnisse append-first mit Mindestsemantik.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Neue Erkenntnis"},
                "source": {"type": "string", "description": "Quelle der Erkenntnis"},
                "project": {"type": "string", "description": "Optionales Projekt"},
                "topic": {"type": "string", "description": "Optionales Thema"},
                "confidence": {"type": "number", "description": "Optional 0.0-1.0"},
                "next_action": {"type": "string", "description": "Optionaler naechster Schritt"},
            },
            "required": ["content", "source"],
        },
    )


def _target_knowledge_dir(knowledge_root: Path, project: str) -> Path:
    project = project.strip()
    if not project:
        # Struktur-agnostisch: vorhandene Knowledge-Orte wiederverwenden.
        for candidate in [
            knowledge_root / "knowledge",
            knowledge_root / "resources" / "knowledge",
        ]:
            if candidate.exists() and candidate.is_dir():
                return candidate
        return knowledge_root / "knowledge"

    project_n = slugify(project)
    candidates = [d for d in knowledge_root.rglob("*") if d.is_dir() and project_n in slugify(d.name)]
    candidates.sort(key=lambda p: len(p.parts))
    for c in candidates:
        nested_knowledge = c / "knowledge"
        if nested_knowledge.exists() and nested_knowledge.is_dir():
            return nested_knowledge
        # Auch ohne Subfolder direkt in Projektordner schreiben.
        return c

    # Fallback ohne Strukturannahme.
    return knowledge_root / "knowledge"


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    cfg = resolve_paths(workspace_root)

    content = str(args.get("content", "")).strip()
    source = str(args.get("source", "")).strip()
    project = str(args.get("project", "")).strip()
    topic = str(args.get("topic", "")).strip() or "general"
    confidence_raw = args.get("confidence")
    next_action = str(args.get("next_action", "")).strip()

    confidence = None
    if confidence_raw is not None:
        try:
            confidence = max(0.0, min(1.0, float(confidence_raw)))
        except (TypeError, ValueError):
            confidence = None

    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y%m%d-%H%M%S")
    topic_slug = slugify(topic)

    target_dir = _target_knowledge_dir(cfg.knowledge_root, project)
    target_dir.mkdir(parents=True, exist_ok=True)
    note_path = target_dir / f"{stamp}-{topic_slug}.md"

    confidence_text = f"{confidence:.2f}" if confidence is not None else "n/a"
    body = [
        "---",
        f"source: {source}",
        f"project: {project or 'global'}",
        f"topic: {topic}",
        f"confidence: {confidence_text}",
        f"date: {day}",
        "---",
        "",
        f"# Knowledge Update - {topic}",
        "",
        "## Insight",
        content,
    ]
    if next_action:
        body.extend(["", "## Next Action", next_action])

    note_path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")

    entry_id = f"{stamp}-{topic_slug}"
    payload = {
        "status": "ok",
        "written_paths": [rel_or_abs(note_path, workspace_root)],
        "entry_ids": [entry_id],
        "link_updates": [],
    }
    return [TextContent(type="text", text=json_text(payload))]
