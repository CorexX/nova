"""
Tool: Project Resume
Buendelt den Kontext fuer "weiterarbeiten" an einem Projekt:
- optional Session-Init ausfuehren
- Zielpfad robust aufloesen (struktur-agnostisch)
- optional Projektnamen aufloesen (project_hint)
- Dokumente laden (explizit oder auto-discovery)
- fehlende Dateien explizit als "nicht vorhanden" markieren
- optional Continue-Report (Kurzuebersicht, letzte Schritte, offene Punkte, Plan)
"""

from __future__ import annotations

import difflib
import re
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
                "project_hint": {
                    "type": "string",
                    "description": (
                        "Optionaler Projektname/Freitext (z.B. 'homlab' oder "
                        "'homelab'). Wenn gesetzt, wird der Projektpfad unter "
                        "nova-knowledge/projects automatisch ermittelt."
                    ),
                },
                "mode": {
                    "type": "string",
                    "enum": ["bundle", "continue"],
                    "default": "bundle",
                    "description": (
                        "bundle: klassische Dokumentausgabe. "
                        "continue: kompakter Fortsetzungsreport mit "
                        "Kurzuebersicht/letzten Schritten/offenen Punkten/Plan."
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
            "anyOf": [
                {"required": ["path"]},
                {"required": ["project_hint"]},
            ],
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


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _iter_project_dirs(projects_root: Path) -> list[Path]:
    if not projects_root.exists() or not projects_root.is_dir():
        return []
    dirs: list[Path] = []
    for p in projects_root.rglob("*"):
        if not p.is_dir():
            continue
        if (p / "README.md").exists() or (p / "CURRENT.md").exists() or (p / "BACKLOG.md").exists():
            dirs.append(p)
    return sorted(dirs)


def _resolve_target_from_hint(project_hint: str, knowledge_root: Path) -> tuple[Path | None, list[Path], bool]:
    projects_root = knowledge_root / "projects"
    candidates = _iter_project_dirs(projects_root)
    if not candidates:
        return None, [], False

    norm_hint = _normalize_token(project_hint)
    scored: list[tuple[int, Path]] = []
    for c in candidates:
        rel = c.relative_to(knowledge_root).as_posix()
        base = c.name
        norm_rel = _normalize_token(rel)
        norm_base = _normalize_token(base)
        score = 0

        if norm_hint and norm_base == norm_hint:
            score = 200
        elif norm_hint and norm_hint in norm_base:
            score = 170
        elif norm_hint and norm_hint in norm_rel:
            score = 140

        if score > 0:
            scored.append((score, c))

    if not scored and norm_hint:
        by_name = {c.name: c for c in candidates}
        close_names = difflib.get_close_matches(
            project_hint,
            list(by_name.keys()),
            n=5,
            cutoff=0.55,
        )
        for idx, name in enumerate(close_names):
            scored.append((100 - idx, by_name[name]))

    if not scored:
        return None, [], False

    scored.sort(key=lambda x: (-x[0], str(x[1])))
    selected = scored[0][1]
    shortlist = [p for _, p in scored[:5]]
    ambiguous = len(scored) > 1 and scored[0][0] == scored[1][0]
    return selected, shortlist, ambiguous


def _extract_goal(readme_text: str) -> str | None:
    for line in readme_text.splitlines():
        if line.strip().lower().startswith("- goal:"):
            return line.split(":", 1)[1].strip()
    return None


def _extract_section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    heading_norm = heading.strip().lower()
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == f"## {heading_norm}":
            start = i + 1
            break
    if start is None:
        return []
    out: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        out.append(line)
    return out


def _extract_checkboxes(lines: list[str], checked: bool) -> list[str]:
    marker = "[x]" if checked else "[ ]"
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"- {marker} "):
            result.append(stripped[len(f"- {marker} ") :].strip())
    return result


def _extract_numbered(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        match = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if match:
            result.append(match.group(1).strip())
    return result


def _read_text_if_exists(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _build_continue_report(selected: Path, knowledge_root: Path) -> list[str]:
    readme_path = selected / "README.md"
    current_path = selected / "CURRENT.md"
    backlog_path = selected / "BACKLOG.md"

    readme_text = _read_text_if_exists(readme_path)
    current_text = _read_text_if_exists(current_path)
    backlog_text = _read_text_if_exists(backlog_path)

    goal = _extract_goal(readme_text)

    current_in_progress = _extract_section_lines(current_text, "In Progress")
    current_next_actions = _extract_section_lines(current_text, "Next Actions (This Week)")
    backlog_now = _extract_section_lines(backlog_text, "Now")

    done_steps = _extract_checkboxes(current_in_progress, checked=True)
    open_current = _extract_checkboxes(current_in_progress, checked=False)
    open_backlog_now = _extract_checkboxes(backlog_now, checked=False)
    next_actions = _extract_numbered(current_next_actions)

    lines = [
        "## Continue Report",
        "",
        "### Kurzuebersicht",
        f"- Projektpfad: `{selected}`",
        f"- Relative Lage: `{selected.relative_to(knowledge_root).as_posix()}`",
    ]
    if goal:
        lines.append(f"- Ziel: {goal}")
    else:
        lines.append("- Ziel: nicht eindeutig in README gefunden")

    lines.extend(
        [
            "",
            "### Letzte Arbeitsschritte",
        ]
    )
    if done_steps:
        for item in done_steps[:5]:
            lines.append(f"- [x] {item}")
    else:
        lines.append("- Keine abgehakten Punkte in `CURRENT.md` gefunden.")

    lines.extend(
        [
            "",
            "### Offene Punkte",
        ]
    )
    if open_current:
        lines.append("- Aus `CURRENT.md` (In Progress):")
        for item in open_current[:6]:
            lines.append(f"  - [ ] {item}")
    if open_backlog_now:
        lines.append("- Aus `BACKLOG.md` (Now):")
        for item in open_backlog_now[:6]:
            lines.append(f"  - [ ] {item}")
    if not open_current and not open_backlog_now:
        lines.append("- Keine offenen Punkte in den priorisierten Sektionen gefunden.")

    lines.extend(
        [
            "",
            "### Naechster Konkreter Plan",
        ]
    )
    plan_items = next_actions[:3] if next_actions else open_current[:3]
    if plan_items:
        for idx, item in enumerate(plan_items, start=1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("1. Projektstatus pruefen und CURRENT/BACKLOG aktualisieren.")

    return lines


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
    path_arg = str(args.get("path") or "").strip()
    project_hint = str(args.get("project_hint") or "").strip()
    mode = str(args.get("mode") or "bundle").strip().lower()
    documents = args.get("documents") or []
    include_session_init = bool(args.get("include_session_init", True))
    include_core = bool(args.get("include_core", False))
    max_chars = int(args.get("max_chars_per_file", 12000))
    max_chars = max(500, max_chars)
    discovery_max_files = max(1, int(args.get("discovery_max_files", 12)))
    discovery_max_depth = max(1, int(args.get("discovery_max_depth", 4)))

    selected: Path | None = None
    candidates: list[Path] = []
    ambiguous = False

    if path_arg:
        selected, candidates = _resolve_target_dir(path_arg, workspace_root, cfg.knowledge_root)
    elif project_hint:
        selected, candidates, ambiguous = _resolve_target_from_hint(project_hint, cfg.knowledge_root)

    lines = [
        "# Project Resume Bundle",
        "",
        "## Status",
        f"- Anfrage-Pfad: `{path_arg or '-'}`",
        f"- Projekt-Hinweis: `{project_hint or '-'}`",
        f"- Modus: `{mode}`",
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
        lines.append("Pfad nicht gefunden. Uebergebe `path` oder `project_hint`.")
        return [TextContent(type="text", text="\n".join(lines))]

    lines.append(f"- Zielpfad: `{selected}`")
    if len(candidates) > 1:
        lines.append(f"- Kandidaten: {len(candidates)} (bestes Match gewaehlt)")
    if ambiguous:
        lines.append("- Hinweis: Mehrdeutiger Treffer (gleiches Scoring), bitte Pfad verifizieren.")
    lines.append("")

    if mode == "continue":
        lines.extend(_build_continue_report(selected, cfg.knowledge_root))
        if include_core:
            lines.append("")
            lines.append("## CORE")
            lines.append("### core/CORE.md")
            lines.append(_read_file_block(cfg.core_md, max_chars))
        return [TextContent(type="text", text="\n".join(lines))]

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
