"""
Tool: Session Init
Liefert minimalen aber vollstaendigen Kontext fuer den Session-Start.

Laedt aus CORE.md:
- Persona (Ton, Stil, Signature-Phrasen)
- Session-Start Workflow
- Arbeitsablauf

Laedt aus PRINCIPLES.md (Single Source of Truth):
- Kernprinzipien (Top 4)
- Schreib-Scope
- Lade-Regeln (Lazy Loading Trigger)

Plus dynamische Daten:
- Datum/KW
- CURRENT.md (Fokus)
- Tickets (kompakt)
- Collections (Top-Level, nur Namen)
"""

import re
from datetime import datetime
from pathlib import Path
from mcp.types import Tool, TextContent
from ..paths import resolve_paths

# Lazy imports (vermeidet zirkulaere Imports)
_index_vault_module = None
_health_check_module = None

def _get_index_vault():
    global _index_vault_module
    if _index_vault_module is None:
        from ..search import index_vault as _mod
        _index_vault_module = _mod
    return _index_vault_module


def _get_health_check():
    global _health_check_module
    if _health_check_module is None:
        # Direkt checks importieren, nicht health_check (spart MCP re-import)
        from ..health import checks as _mod
        _health_check_module = _mod
    return _health_check_module


def _list_subdirs(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted([d.name for d in path.iterdir() if d.is_dir() and not d.name.startswith("_")])


def _list_top_level_collections(knowledge_root: Path) -> list[str]:
    if not knowledge_root.exists():
        return []
    return sorted([
        d.name
        for d in knowledge_root.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_"))
    ])


# =============================================================================
# TOOL DEFINITION
# =============================================================================

def get_tool_definition(workspace_root: Path) -> Tool:
    """Gibt die Tool-Definition zurueck."""
    return Tool(
        name="nova_session_init",
        description=(
            "Laedt minimalen Session-Kontext: Regeln, Scope, Fokus, Tickets. "
            "PFLICHT am Anfang jeder Session. Ohne diesen Aufruf fehlt der Kontext."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_section(content: str, header: str) -> str | None:
    """Extrahiert eine Sektion aus Markdown (bis zum naechsten ---)."""
    pattern = rf"(## {header}.*?)(?=\n---|\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else None


def _get_top_principles(content: str) -> str:
    """Extrahiert die Prinzipien-Tabelle (kompakt, nur Tabelle)."""
    match = re.search(r"(\| # \| Prinzip.*?)(?=\n\n|\n###)", content, re.DOTALL)
    if match:
        return "## Kernprinzipien\n\n" + match.group(1).strip()
    return "[ERR] Kernprinzipien nicht gefunden"


def _get_scope(content: str) -> str:
    """Extrahiert Schreib-Scope Tabelle."""
    section = _extract_section(content, "Schreib-Scope")
    return section if section else "[ERR] Schreib-Scope nicht gefunden"


def _get_load_rules(content: str) -> str:
    """Extrahiert Lade-Regeln Tabelle."""
    # Suche spezifisch nach der Lade-Regeln Sektion bis zur leeren Zeile nach Tabelle
    match = re.search(
        r"(## Lade-Regeln.*?\n\|[^\n]+\|\n\|[-| ]+\|(?:\n\|[^\n]+\|)+)",
        content,
        re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return "[ERR] Lade-Regeln nicht gefunden"


def _get_core_persona(content: str) -> str:
    """Extrahiert Kernpersona + Persona-Overlay aus CORE.md."""
    blocks: list[str] = []

    identity_match = re.search(
        r"(^##\s+Wer du bist.*?)(?=^\s*##\s+\S|\Z)",
        content,
        re.DOTALL | re.MULTILINE,
    )
    if identity_match:
        blocks.append(identity_match.group(1).strip())

    overlay_match = re.search(
        r"(^#\s+Persona Overlay.*?)(?=^\s*#\s+\S|\Z)",
        content,
        re.DOTALL | re.MULTILINE,
    )
    if overlay_match:
        blocks.append(overlay_match.group(1).strip())

    if blocks:
        return "\n\n".join(blocks)
    return "[ERR] Persona nicht gefunden"


def _get_core_session_start(content: str) -> str:
    """Extrahiert Session-Start aus CORE.md."""
    match = re.search(
        r"(## Session-Start.*?)(?=\n---|\n## |\Z)",
        content,
        re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return None  # Optional, nicht kritisch


# =============================================================================
# TOOL IMPLEMENTATION
# =============================================================================

async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    """Liefert minimalen Session-Kontext."""
    paths = resolve_paths(workspace_root)
    knowledge_root = paths.knowledge_root
    core_path = paths.core_md
    principles_path = paths.principles_md
    
    sections = []
    
    # --- Header mit Datum ---
    now = datetime.now()
    weekday = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][now.weekday()]
    kw = now.isocalendar()[1]
    sections.append(f"# Session Context")
    sections.append(f"**{now.strftime('%Y-%m-%d')} ({weekday}), KW{kw:02d}**\n")
    
    # --- Aus CORE.md laden ---
    if core_path.exists():
        core_content = core_path.read_text(encoding="utf-8")
        
        # Persona
        persona = _get_core_persona(core_content)
        if persona:
            sections.append(persona)
            sections.append("")
        
        # Session-Start (optional, fuer Erinnerung)
        session_start = _get_core_session_start(core_content)
        if session_start:
            sections.append(session_start)
            sections.append("")
    else:
        sections.append("[ERR] CORE.md nicht gefunden\n")
    
    # --- Aus PRINCIPLES.md laden ---
    if principles_path.exists():
        principles = principles_path.read_text(encoding="utf-8")
        
        # Kernprinzipien (Tabelle)
        sections.append(_get_top_principles(principles))
        sections.append("")
        
        # Schreib-Scope
        sections.append(_get_scope(principles))
        sections.append("")
        
        # Lade-Regeln
        sections.append(_get_load_rules(principles))
        sections.append("")
    else:
        sections.append("[ERR] PRINCIPLES.md nicht gefunden\n")
    
    # --- CURRENT.md (Fokus) ---
    current_path = knowledge_root / "CURRENT.md"
    if current_path.exists():
        current_content = current_path.read_text(encoding="utf-8")
        sections.append("## Aktueller Fokus")
        sections.append(current_content.strip())
        sections.append("")
    
    # --- TICKETS.md (nur Aktive Tickets + Buchungsregeln) ---
    tickets_path = knowledge_root / "TICKETS.md"
    if tickets_path.exists():
        tickets_content = tickets_path.read_text(encoding="utf-8")
        
        # Extrahiere "Aktive Tickets" Sektion
        active_match = re.search(
            r"(## Aktive Tickets.*?\n\|[^\n]+\|\n\|[-| ]+\|(?:\n\|[^\n]+\|)+)",
            tickets_content,
            re.DOTALL
        )
        
        # Extrahiere "Buchungsregeln" Sektion (Standard-Tickets + Fallback)
        rules_match = re.search(
            r"(## Buchungsregeln.*?)(?=\n---)",
            tickets_content,
            re.DOTALL
        )
        
        if active_match:
            sections.append(active_match.group(1).strip())
            sections.append("")
        
        if rules_match:
            sections.append(rules_match.group(1).strip())
            sections.append("")
    
    # --- Top-Level Collections ---
    collections = _list_top_level_collections(knowledge_root)
    if collections:
        sections.append(f"## Collections: {', '.join(f'`{c}`' for c in collections)}")

    # --- Auto-Indexing (inkrementell, non-blocking) ---
    if not paths.search_enabled:
        index_status = "[SKIP] Indexing uebersprungen (search.enabled=false)"
    else:
        try:
            index_tool = _get_index_vault()
            index_result = await index_tool.execute({"force": False}, workspace_root)
            index_text = ""
            if index_result and getattr(index_result[0], "text", None):
                index_text = index_result[0].text

            if "Index aktualisiert" in index_text:
                index_status = "[OK] Auto-Index: aktualisiert (inkrementell)"
            else:
                first_line = next((line.strip() for line in index_text.splitlines() if line.strip()), None)
                if first_line:
                    index_status = f"[INFO] Auto-Index: {first_line}"
                else:
                    index_status = "[INFO] Auto-Index: keine Statusmeldung"
        except Exception as e:
            index_status = f"[WARN] Auto-Index fehlgeschlagen: {type(e).__name__}"

    sections.append("")
    sections.append("## Index Status")
    sections.append(index_status)
    sections.append("")
    
    # --- Health Check (schnell, ~0.2s - ohne MCP re-import) ---
    health_status = ""
    try:
        checks = _get_health_check()
        groups = await checks.run_grouped_checks(workspace_root)
        health_status = "## System Status\n" + checks.format_grouped_simple(groups)
        
        # Aktionen hinzufuegen wenn noetig
        actions = checks.get_actions_from_groups(groups)
        if actions:
            health_status += "\n\n**Action Required:**\n" + "\n".join(actions)
    except Exception as e:
        health_status = f"## System Status\n[WARN] Health-Check fehlgeschlagen: {type(e).__name__}"
    
    sections.append(f"\n---\n{health_status}")
    sections.append("\n[OK] Startklar")
    
    result = "\n".join(sections)
    
    return [TextContent(type="text", text=result)]


