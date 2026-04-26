"""Tool: nova_knowledge_update."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.types import TextContent, Tool

from .paths import resolve_paths
from .common import json_text, slugify


ALLOWED_MEMORY_TYPES = {
    "fact",
    "preference",
    "decision",
    "task",
    "procedure",
    "episode",
    "source",
    "summary",
    "question",
    "constraint",
    "entity",
    "relationship",
}

ALLOWED_SCOPES = {"global", "user", "project", "repo", "task", "session", "agent"}
ALLOWED_MODES = {"append", "dry_run", "propose_patch"}


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
                "title": {"type": "string", "description": "Optionaler Eintragstitel"},
                "confidence": {"type": "number", "description": "Optional 0.0-1.0"},
                "next_action": {"type": "string", "description": "Optionaler naechster Schritt"},
                "memory_type": {
                    "type": "string",
                    "enum": sorted(ALLOWED_MEMORY_TYPES),
                    "default": "fact",
                    "description": "Typ der Erinnerung",
                },
                "scope": {
                    "type": "string",
                    "enum": sorted(ALLOWED_SCOPES),
                    "default": "global",
                    "description": "Geltungsbereich der Erinnerung",
                },
                "mode": {
                    "type": "string",
                    "enum": sorted(ALLOWED_MODES),
                    "default": "append",
                    "description": "append schreibt direkt, dry_run zeigt Vorschau, propose_patch erzeugt Review-Patch",
                },
                "target_path": {
                    "type": "string",
                    "description": "Optionaler Zielpfad innerhalb NOVA_KNOWLEDGE_ROOT",
                },
                "supersedes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: Memory-IDs, die durch diesen Eintrag ersetzt werden",
                },
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

    # Fallback: best passender Projektordner ohne knowledge-Unterordner.
    if candidates:
        return candidates[0]

    # Fallback ohne Strukturannahme.
    return knowledge_root / "knowledge"


def _resolve_target_path(knowledge_root: Path, target_path: str) -> tuple[Path | None, str | None]:
    if not target_path.strip():
        return None, None
    raw = Path(target_path).expanduser()
    candidate = raw if raw.is_absolute() else knowledge_root / raw
    try:
        resolved = candidate.resolve()
        root = knowledge_root.resolve()
        resolved.relative_to(root)
    except ValueError:
        return None, "target_path must stay inside NOVA_KNOWLEDGE_ROOT"
    return resolved, None


def _parse_confidence(value: Any) -> tuple[float | None, str | None]:
    if value is None:
        return None, None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None, "confidence must be a number between 0.0 and 1.0"
    if confidence < 0.0 or confidence > 1.0:
        return None, "confidence must be between 0.0 and 1.0"
    return confidence, None


def _make_entry_block(
    *,
    entry_id: str,
    observed_at: str,
    time_of_day: str,
    title: str,
    project: str,
    topic: str,
    source: str,
    confidence: float | None,
    content: str,
    next_action: str,
    memory_type: str,
    scope: str,
    supersedes: list[str],
) -> str:
    confidence_text = f"{confidence:.2f}" if confidence is not None else "n/a"
    supersedes_text = ", ".join(supersedes) if supersedes else "[]"
    entry_block = [
        f"## {time_of_day} - {title}",
        "",
        f"- entry_id: {entry_id}",
        f"- observed_at: {observed_at}",
        f"- project: {project or 'global'}",
        f"- topic: {topic}",
        f"- source: {source}",
        f"- memory_type: {memory_type}",
        f"- scope: {scope}",
        "- status: active",
        f"- confidence: {confidence_text}",
        f"- supersedes: {supersedes_text}",
        "",
        "### Insight",
        content,
    ]
    if next_action:
        entry_block.extend(["", "### Next Action", next_action])
    return "\n".join(entry_block).rstrip() + "\n"


def _make_note_body(*, project: str, topic: str, day: str, memory_type: str, scope: str, entry_block: str) -> str:
    body = [
        "---",
        f"project: {project or 'global'}",
        f"topic: {topic}",
        f"date: {day}",
        f"memory_type: {memory_type}",
        f"scope: {scope}",
        "---",
        "",
        f"# Knowledge Update - {topic}",
        "",
        entry_block.rstrip(),
    ]
    return "\n".join(body).rstrip() + "\n"


def _make_patch_text(note_path: Path, entry_block: str) -> str:
    return "\n".join([
        "*** Begin Patch",
        f"*** Update File: {note_path.as_posix()}",
        "@@ append knowledge update @@",
        "+",
        "+---",
        "+",
        *[f"+{line}" for line in entry_block.rstrip().splitlines()],
        "*** End Patch",
        "",
    ])


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    cfg = resolve_paths(workspace_root)

    content = str(args.get("content", "")).strip()
    source = str(args.get("source", "")).strip()
    project = str(args.get("project", "")).strip()
    topic = str(args.get("topic", "")).strip() or "general"
    title = str(args.get("title", "")).strip() or topic
    confidence_raw = args.get("confidence")
    next_action = str(args.get("next_action", "")).strip()
    memory_type = str(args.get("memory_type", "fact")).strip().lower() or "fact"
    scope = str(args.get("scope", "global")).strip().lower() or "global"
    mode = str(args.get("mode", "append")).strip().lower() or "append"
    target_path_raw = str(args.get("target_path", "")).strip()
    supersedes = [str(item).strip() for item in (args.get("supersedes") or []) if str(item).strip()]

    validation_errors: dict[str, str] = {}
    if not content:
        validation_errors["content"] = "content is required"
    if not source:
        validation_errors["source"] = "source is required"
    if memory_type not in ALLOWED_MEMORY_TYPES:
        validation_errors["memory_type"] = f"unsupported memory_type: {memory_type}"
    if scope not in ALLOWED_SCOPES:
        validation_errors["scope"] = f"unsupported scope: {scope}"
    if mode not in ALLOWED_MODES:
        validation_errors["mode"] = f"unsupported mode: {mode}"

    confidence, confidence_error = _parse_confidence(confidence_raw)
    if confidence_error:
        validation_errors["confidence"] = confidence_error

    explicit_target, target_error = _resolve_target_path(cfg.knowledge_root, target_path_raw)
    if target_error:
        validation_errors["target_path"] = target_error

    if validation_errors:
        payload = {
            "status": "error",
            "message": "knowledge update validation failed" if "target_path" not in validation_errors else validation_errors["target_path"],
            "validation_errors": validation_errors,
            "written_paths": [],
        }
        return [TextContent(type="text", text=json_text(payload))]

    now = datetime.now(timezone.utc).astimezone()
    day = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y%m%d-%H%M%S")
    time_of_day = now.strftime("%H:%M:%S")
    observed_at = now.isoformat(timespec="seconds")
    topic_slug = slugify(topic)

    if explicit_target is not None:
        note_path = explicit_target
        target_reason = "explicit_target_path"
    else:
        target_dir = _target_knowledge_dir(cfg.knowledge_root, project)
        note_path = target_dir / f"{now.strftime('%Y%m%d')}-{topic_slug}.md"
        target_reason = "project_match_or_default_knowledge_dir"

    entry_id = f"mem_{stamp}_{topic_slug}"
    entry_block = _make_entry_block(
        entry_id=entry_id,
        observed_at=observed_at,
        time_of_day=time_of_day,
        title=title,
        project=project,
        topic=topic,
        source=source,
        confidence=confidence,
        content=content,
        next_action=next_action,
        memory_type=memory_type,
        scope=scope,
        supersedes=supersedes,
    )

    entry = {
        "entry_id": entry_id,
        "observed_at": observed_at,
        "project": project or "global",
        "topic": topic,
        "source": source,
        "memory_type": memory_type,
        "scope": scope,
        "status": "active",
        "confidence": confidence,
        "supersedes": supersedes,
    }

    base_payload = {
        "status": "ok",
        "mode": mode,
        "entry": entry,
        "entry_ids": [entry_id],
        "target_reason": target_reason,
        "duplicate_candidates": [],
        "validation_warnings": [],
        "link_updates": [],
    }

    if mode == "dry_run":
        payload = {
            **base_payload,
            "written_paths": [],
            "would_write_paths": [str(note_path.resolve())],
            "index_stale": False,
            "recommended_maintenance": None,
        }
        return [TextContent(type="text", text=json_text(payload))]

    if mode == "propose_patch":
        patch_dir = cfg.index_root / "patches"
        patch_dir.mkdir(parents=True, exist_ok=True)
        patch_path = patch_dir / f"{entry_id}.patch"
        patch_path.write_text(_make_patch_text(note_path, entry_block), encoding="utf-8")
        payload = {
            **base_payload,
            "written_paths": [],
            "would_write_paths": [str(note_path.resolve())],
            "proposed_patch_path": str(patch_path.resolve()),
            "index_stale": False,
            "recommended_maintenance": None,
        }
        return [TextContent(type="text", text=json_text(payload))]

    note_path.parent.mkdir(parents=True, exist_ok=True)
    if note_path.exists():
        existing = note_path.read_text(encoding="utf-8").rstrip()
        updated = existing + "\n\n---\n\n" + entry_block.rstrip() + "\n"
        note_path.write_text(updated, encoding="utf-8")
    else:
        body = _make_note_body(
            project=project,
            topic=topic,
            day=day,
            memory_type=memory_type,
            scope=scope,
            entry_block=entry_block,
        )
        note_path.write_text(body, encoding="utf-8")

    payload = {
        **base_payload,
        "written_paths": [str(note_path.resolve())],
        "would_write_paths": [str(note_path.resolve())],
        "index_stale": True,
        "recommended_maintenance": {"operation": "index", "force": False},
    }
    return [TextContent(type="text", text=json_text(payload))]
