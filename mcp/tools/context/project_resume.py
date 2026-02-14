"""
Tool: Project Resume
Buendelt den Kontext fuer "weiterarbeiten" an einem Projekt:
- optional Session-Init ausfuehren
- Zielpfad robust aufloesen (struktur-agnostisch)
- Dokumente laden (explizit oder auto-discovery)
- fehlende Dateien explizit als "nicht vorhanden" markieren
"""

from __future__ import annotations

from pathlib import Path

from mcp.types import TextContent, Tool

from ..paths import resolve_paths


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_project_resume",
        description=(
            "Buendelt Fortsetzungs-Kontext fuer einen uebergebenen Pfad: "
            "Session-Init, Pfadaufloesung, Dokumente inkl. "
            "'nicht vorhanden'-Markierung."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Zielpfad fuer den Kontext (absolut oder relativ). "
                        "Beispiel: 'projects/internal/homelab'"
                    ),
                },
                "documents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optionale relative Dokumentpfade unterhalb des Zielpfads. "
                        "Wenn leer: automatische Markdown-Discovery."
                    ),
                },
                "include_session_init": {
                    "type": "boolean",
                    "default": True,
                    "description": "Fuehrt vor dem Laden optional nova_session_init aus.",
                },
                "include_core": {
                    "type": "boolean",
                    "default": False,
                    "description": "Laedt core/CORE.md zusaetzlich mit.",
                },
                "max_chars_per_file": {
                    "type": "integer",
                    "default": 12000,
                    "description": "Maximale Zeichen pro Datei im Output.",
                },
                "discovery_max_files": {
                    "type": "integer",
                    "default": 12,
                    "description": "Max. Dateien fuer Auto-Discovery.",
                },
                "discovery_max_depth": {
                    "type": "integer",
                    "default": 4,
                    "description": "Max. Rekursionstiefe fuer Auto-Discovery.",
                },
            },
            "required": ["path"],
        },
    )


def _resolve_target_dir(path_arg: str, workspace_root: Path, knowledge_root: Path) -> tuple[Path | None, list[Path]]:
    raw = Path(path_arg).expanduser()
    candidates: list[Path] = []

    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append((workspace_root / raw))
        candidates.append((knowledge_root / raw))

    resolved_existing: list[Path] = []
    for c in candidates:
        p = c.resolve()
        if p.exists() and p.is_dir() and p not in resolved_existing:
            resolved_existing.append(p)

    if not resolved_existing:
        return None, [c.resolve() for c in candidates]

    return resolved_existing[0], resolved_existing


def _read_file_block(path: Path, max_chars: int) -> str:
    if not path.exists():
        return f"- Status: nicht vorhanden\n- Pfad: `{path}`\n"

    if not path.is_file():
        return f"- Status: nicht vorhanden\n- Pfad: `{path}`\n- Hinweis: Kein regulaeres File\n"

    content = path.read_text(encoding="utf-8")
    truncated = False
    if len(content) > max_chars:
        content = content[:max_chars]
        truncated = True

    lines = [
        "- Status: vorhanden",
        f"- Pfad: `{path}`",
    ]
    if truncated:
        lines.append(f"- Hinweis: Ausgabe auf {max_chars} Zeichen begrenzt")
    lines.append("")
    lines.append("```md")
    lines.append(content.rstrip())
    lines.append("```")
    return "\n".join(lines) + "\n"


def _discover_markdown_docs(base_dir: Path, max_files: int, max_depth: int) -> list[Path]:
    base_parts = len(base_dir.parts)
    found: list[Path] = []

    for p in sorted(base_dir.rglob("*.md")):
        rel_depth = len(p.parts) - base_parts
        if rel_depth > max_depth:
            continue
        found.append(p)
        if len(found) >= max_files:
            break

    return found


async def _run_session_init(workspace_root: Path) -> tuple[str, str]:
    try:
        from . import session_init as session_init_tool

        result = await session_init_tool.execute({}, workspace_root)
        text = result[0].text if result else ""
        return "OK", text
    except Exception as e:
        return f"FEHLER ({type(e).__name__})", ""


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    cfg = resolve_paths(workspace_root)
    path_arg = str(args["path"]).strip()
    documents = args.get("documents") or []
    include_session_init = bool(args.get("include_session_init", True))
    include_core = bool(args.get("include_core", False))
    max_chars = int(args.get("max_chars_per_file", 12000))
    max_chars = max(500, max_chars)
    discovery_max_files = max(1, int(args.get("discovery_max_files", 12)))
    discovery_max_depth = max(1, int(args.get("discovery_max_depth", 4)))

    selected, candidates = _resolve_target_dir(path_arg, workspace_root, cfg.knowledge_root)

    lines = [
        "# Project Resume Bundle",
        "",
        "## Status",
        f"- Anfrage-Pfad: `{path_arg}`",
    ]

    if include_session_init:
        session_status, _ = await _run_session_init(workspace_root)
        lines.append(f"- Session Init: {session_status}")
    else:
        lines.append("- Session Init: SKIP")

    if selected is None:
        lines.append("- Zielpfad: nicht vorhanden")
        if candidates:
            lines.append("- Gepruefte Pfade:")
            for c in candidates:
                lines.append(f"  - `{c}`")
        lines.append("")
        lines.append("## Ergebnis")
        lines.append("Pfad nicht gefunden.")
        return [TextContent(type="text", text="\n".join(lines))]

    lines.append(f"- Zielpfad: `{selected}`")
    if len(candidates) > 1:
        lines.append(f"- Kandidaten: {len(candidates)} (erstes Match gewaehlt)")
    lines.append("")

    lines.append("## Dokumente")
    if documents:
        for rel in documents:
            rel_path = Path(rel)
            doc_path = selected / rel_path
            lines.append(f"### {rel}")
            lines.append(_read_file_block(doc_path, max_chars))
    else:
        discovered = _discover_markdown_docs(selected, discovery_max_files, discovery_max_depth)
        lines.append(f"- Modus: Auto-Discovery (`*.md`, max_files={discovery_max_files}, max_depth={discovery_max_depth})")
        if not discovered:
            lines.append("- Ergebnis: nicht vorhanden")
        lines.append("")
        for doc_path in discovered:
            rel = doc_path.relative_to(selected)
            lines.append(f"### {rel.as_posix()}")
            lines.append(_read_file_block(doc_path, max_chars))

    if include_core:
        lines.append("## CORE")
        lines.append("### core/CORE.md")
        lines.append(_read_file_block(cfg.core_md, max_chars))

    return [TextContent(type="text", text="\n".join(lines))]
