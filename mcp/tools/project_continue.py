"""Tool: nova_project_continue."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from mcp.types import TextContent, Tool

from .paths import resolve_paths
from .common import json_text, rel_or_abs


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_project_continue",
        description="Setzt ein Projekt robust fort und liefert die naechsten konkreten Schritte.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_hint": {"type": "string", "description": "Projektname oder Freitext-Hinweis"},
                "mode": {
                    "type": "string",
                    "enum": ["continue", "status"],
                    "default": "continue",
                    "description": "continue: inkl. 3-Schritt-Plan, status: nur Lagebild",
                },
            },
            "required": ["project_hint"],
        },
    )


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _project_dirs(knowledge_root: Path) -> list[Path]:
    if not knowledge_root.exists():
        return []
    candidates: list[Path] = []
    for path in knowledge_root.rglob("*"):
        if not path.is_dir():
            continue
        # Struktur-agnostisch: Ordner mit "projekttypischen" Dateien oder >=2 Markdown-Dateien.
        md_files = list(path.glob("*.md"))
        has_signals = any((path / f).exists() for f in ("CURRENT.md", "BACKLOG.md", "README.md"))
        if has_signals or len(md_files) >= 2:
            candidates.append(path)
    return sorted(candidates)


def _select_project(project_hint: str, knowledge_root: Path) -> tuple[Path | None, list[str]]:
    dirs = _project_dirs(knowledge_root)
    if not dirs:
        return None, []
    hint_n = _norm(project_hint)
    scored: list[tuple[int, Path]] = []
    for d in dirs:
        rel = d.relative_to(knowledge_root).as_posix()
        base = d.name
        rel_n = _norm(rel)
        base_n = _norm(base)
        score = 0
        if base_n == hint_n:
            score = 300
        elif hint_n and hint_n in base_n:
            score = 220
        elif hint_n and hint_n in rel_n:
            score = 180
        if score:
            scored.append((score, d))

    if not scored:
        names = [d.name for d in dirs]
        for idx, name in enumerate(difflib.get_close_matches(project_hint, names, n=5, cutoff=0.55)):
            d = next(x for x in dirs if x.name == name)
            scored.append((120 - idx, d))

    if not scored:
        return None, [d.relative_to(knowledge_root).as_posix() for d in dirs[:8]]

    scored.sort(key=lambda x: (-x[0], str(x[1])))
    sel = scored[0][1]
    shortlist = [p.relative_to(knowledge_root).as_posix() for _, p in scored[:5]]
    return sel, shortlist


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _section(text: str, title: str) -> list[str]:
    lines = text.splitlines()
    start = -1
    for i, line in enumerate(lines):
        if line.strip().lower() == f"## {title.lower()}":
            start = i + 1
            break
    if start < 0:
        return []
    out: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        out.append(line)
    return out


def _extract_tasks(lines: list[str], checked: bool | None = None) -> list[str]:
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if checked is None and s.startswith("- "):
            out.append(s[2:].strip())
        elif checked is True and s.startswith("- [x] "):
            out.append(s[6:].strip())
        elif checked is False and s.startswith("- [ ] "):
            out.append(s[6:].strip())
    return out


def _extract_numbered(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            out.append(m.group(1).strip())
    return out


def _rank_project_docs(project_dir: Path) -> list[Path]:
    docs = sorted(project_dir.glob("*.md"))
    if not docs:
        return []
    priority = {"CURRENT.md": 0, "BACKLOG.md": 1, "README.md": 2}
    return sorted(docs, key=lambda p: (priority.get(p.name, 9), p.name.lower()))


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    cfg = resolve_paths(workspace_root)
    hint = str(args.get("project_hint", "")).strip()
    mode = str(args.get("mode", "continue")).strip().lower()

    selected, shortlist = _select_project(hint, cfg.knowledge_root)
    if selected is None:
        payload = {
            "project_hint": hint,
            "status": "not_found",
            "candidates": shortlist,
            "message": "Kein Projekt eindeutig gefunden.",
        }
        return [TextContent(type="text", text=json_text(payload))]

    docs = _rank_project_docs(selected)
    done_steps: list[str] = []
    open_items: list[str] = []
    plan_candidates: list[str] = []

    for doc in docs[:6]:
        text = _read(doc)
        lines = text.splitlines()
        done_steps.extend(_extract_tasks(lines, checked=True))
        open_items.extend(_extract_tasks(lines, checked=False))
        plan_candidates.extend(_extract_numbered(lines))

    # Fallback: Wenn es keine Checkbox-Tasks gibt, einfache Bullet-Items als offene Punkte nehmen.
    if not open_items:
        for doc in docs[:4]:
            open_items.extend(_extract_tasks(_read(doc).splitlines(), checked=None))

    next_plan = (plan_candidates + open_items)[:3]
    if not next_plan:
        next_plan = ["Projektkontext aktualisieren und naechsten Arbeitsschritt festlegen."]

    payload = {
        "project_hint": hint,
        "status": "ok",
        "mode": mode,
        "project_path": rel_or_abs(selected, workspace_root),
        "last_steps": done_steps[:5],
        "open_items": open_items[:10],
        "next_plan": next_plan if mode == "continue" else [],
        "candidates": shortlist,
    }
    return [TextContent(type="text", text=json_text(payload))]
