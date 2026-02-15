"""Tool: nova_project_create."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mcp.types import TextContent, Tool

from .paths import resolve_paths
from .common import json_text, rel_or_abs, slugify


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_project_create",
        description="Legt ein neues Projekt strukturiert an und bootstrappt die Kern-Dateien.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer": {"type": "string", "description": "Kundenname oder Domäne"},
                "project_name": {"type": "string", "description": "Projektname"},
                "template": {
                    "type": "string",
                    "description": "Optionaler Template-Name (aktuell metadata only)",
                    "default": "default",
                },
                "initial_context": {
                    "type": "string",
                    "description": "Optionaler Initialkontext fuer README/CURRENT",
                },
                "target_root": {
                    "type": "string",
                    "description": (
                        "Optionales Zielverzeichnis relativ zu nova-knowledge (z. B. 'projects' "
                        "oder 'kunden'). Ohne Angabe wird heuristisch ein Projekt-Root ermittelt."
                    ),
                },
            },
            "required": ["customer", "project_name"],
        },
    )


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _infer_project_base(knowledge_root: Path) -> Path:
    # Struktur-agnostisch: bestaende Projektsammlungen bevorzugen.
    preferred = ["projects", "kunden", "workspaces", "areas"]
    for name in preferred:
        candidate = knowledge_root / name
        if candidate.exists() and candidate.is_dir():
            return candidate
    return knowledge_root / "projects"


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    cfg = resolve_paths(workspace_root)
    customer = str(args.get("customer", "")).strip()
    project_name = str(args.get("project_name", "")).strip()
    template = str(args.get("template", "default")).strip() or "default"
    initial_context = str(args.get("initial_context", "")).strip()
    target_root = str(args.get("target_root", "")).strip()

    customer_slug = slugify(customer)
    project_slug = slugify(project_name)
    if target_root:
        base_root = (cfg.knowledge_root / target_root).resolve()
    else:
        base_root = _infer_project_base(cfg.knowledge_root)

    project_root = base_root / customer_slug / project_slug
    knowledge_dir = project_root / "knowledge"

    if project_root.exists():
        payload = {
            "status": "exists",
            "message": "Projekt existiert bereits.",
            "project_path": rel_or_abs(project_root, workspace_root),
        }
        return [TextContent(type="text", text=json_text(payload))]

    created_paths: list[str] = []
    bootstrap_files: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d")

    for directory in [project_root, knowledge_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        created_paths.append(rel_or_abs(directory, workspace_root))

    readme_path = project_root / "README.md"
    current_path = project_root / "CURRENT.md"
    backlog_path = project_root / "BACKLOG.md"

    readme = (
        f"# {project_name}\n\n"
        f"- Customer: {customer}\n"
        f"- Created: {now}\n"
        f"- Template: {template}\n\n"
        "## Goal\n\n"
        f"{initial_context or 'Projektziel definieren.'}\n"
    )
    current = (
        f"# CURRENT - {project_name}\n\n"
        "## In Progress\n\n"
        "- [ ] Projektstart vorbereiten\n\n"
        "## Next Actions (This Week)\n\n"
        "1. Zielbild konkretisieren\n"
        "2. Erste Arbeitspakete definieren\n"
        "3. BACKLOG priorisieren\n"
    )
    backlog = (
        f"# BACKLOG - {project_name}\n\n"
        "## Now\n\n"
        "- [ ] Kickoff-Notiz erstellen\n\n"
        "## Next\n\n"
        "- [ ] Arbeitspakete strukturieren\n\n"
        "## Later\n\n"
        "- [ ] Betriebsmetriken definieren\n"
    )

    for path, content in [
        (readme_path, readme),
        (current_path, current),
        (backlog_path, backlog),
    ]:
        if _write_if_missing(path, content):
            bootstrap_files.append(rel_or_abs(path, workspace_root))

    payload = {
        "status": "ok",
        "project_path": rel_or_abs(project_root, workspace_root),
        "created_paths": created_paths,
        "bootstrap_files": bootstrap_files,
        "next_actions": [
            "Projektziel in README.md schaerfen.",
            "CURRENT.md mit konkreten Tasks aktualisieren.",
            "Erste Erkenntnisse via nova_knowledge_update persistieren.",
        ],
    }
    return [TextContent(type="text", text=json_text(payload))]
