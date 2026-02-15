"""
Individual Health Checks fuer NOVA Systems.
Jeder Check ist schnell (<100ms) und gibt strukturierten Status zurueck.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple
from ..paths import resolve_paths


class CheckResult(NamedTuple):
    """Ergebnis eines Health Checks."""
    name: str
    status: str  # "ok", "warning", "error", "info"
    message: str
    detail: str = ""
    action: str = ""  # Empfohlene Aktion bei Problemen
    group: str = ""   # Gruppenzugehoerigkeit


class CheckGroup(NamedTuple):
    """Gruppierte Checks fuer uebersichtliche Darstellung."""
    name: str
    checks: list[CheckResult]
    
    @property
    def status(self) -> str:
        """Worst status in group."""
        if any(c.status == "error" for c in self.checks):
            return "error"
        if any(c.status == "warning" for c in self.checks):
            return "warning"
        return "ok"


def check_vault_index(workspace_root: Path) -> CheckResult:
    """Prueft ob Vault indexiert ist."""
    paths = resolve_paths(workspace_root)
    hash_file = paths.index_root / "file_hashes.json"
    chroma_path = paths.chroma_path
    
    if not hash_file.exists():
        return CheckResult(
            name="Vault Index",
            status="error",
            message="Nicht indexiert",
            detail="file_hashes.json fehlt",
            action="Fuehre `nova_system_maintain(operation='index')` aus"
        )
    
    try:
        hashes = json.loads(hash_file.read_text(encoding="utf-8"))
        file_count = len(hashes)
    except Exception as e:
        return CheckResult(
            name="Vault Index",
            status="error",
            message="Korrupt",
            detail=str(e),
            action="Fuehre `nova_system_maintain(operation='index', force=true)` aus"
        )
    
    # Pruefe ob ChromaDB Ordner existiert (ohne ChromaDB zu laden - das dauert 3-4s!)
    chunk_info = ""
    if chroma_path.exists():
        # Schaetze Chunks basierend auf Dateien (schnell, ohne ChromaDB Import)
        chunk_info = "indexed"
    else:
        chunk_info = "nicht initialisiert"
    
    if file_count == 0:
        return CheckResult(
            name="Vault Index",
            status="warning",
            message="Leer",
            detail="0 Dateien indexiert",
            action="Fuehre `nova_system_maintain(operation='index')` aus"
        )
    
    return CheckResult(
        name="Vault Index",
        status="ok",
        message=f"{file_count} Dateien",
        detail=chunk_info
    )


def check_embedding_model(workspace_root: Path) -> CheckResult:
    """Prueft ob Embedding Model gecached ist."""
    # Standard HuggingFace Cache Pfad
    model_name = "sentence-transformers--all-MiniLM-L6-v2"
    cache_path = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    model_path = cache_path / "hub" / f"models--{model_name}"
    
    if model_path.exists():
        # Berechne Groesse
        try:
            size_mb = sum(f.stat().st_size for f in model_path.rglob("*") if f.is_file()) / (1024 * 1024)
            return CheckResult(
                name="Embedding Model",
                status="ok",
                message="Cached",
                detail=f"{size_mb:.0f} MB"
            )
        except Exception:
            return CheckResult(
                name="Embedding Model",
                status="ok",
                message="Cached"
            )
    
    return CheckResult(
        name="Embedding Model",
        status="warning",
        message="Nicht cached",
        detail="Wird beim ersten Aufruf heruntergeladen (~380 MB)",
        action="Erster `nova_knowledge_query` Aufruf laedt das Modell"
    )


def check_worklog_today(workspace_root: Path) -> CheckResult:
    """Prueft WORKLOG.md auf heutige Eintraege."""
    worklog_path = resolve_paths(workspace_root).worklog_md
    
    if not worklog_path.exists():
        return CheckResult(
            name="Worklog",
            status="warning",
            message="Fehlt",
            detail="WORKLOG.md nicht gefunden",
            action="Erstelle WORKLOG.md"
        )
    
    try:
        content = worklog_path.read_text(encoding="utf-8")
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Zaehle Eintraege mit heutigem Datum oder Zeitstempel
        today_entries = content.count(today_str)
        
        # Alternativ: Zaehle Zeitstempel-Pattern fuer heute (z.B. "- 09:30")
        import re
        time_pattern = re.findall(r"^- \d{2}:\d{2}", content, re.MULTILINE)
        
        if today_entries > 0:
            return CheckResult(
                name="Worklog",
                status="ok",
                message=f"Heute: {today_entries} Eintraege"
            )
        else:
            return CheckResult(
                name="Worklog",
                status="ok",
                message="Heute: 0 Eintraege",
                detail="Noch nichts dokumentiert"
            )
    except Exception as e:
        return CheckResult(
            name="Worklog",
            status="warning",
            message="Lesefehler",
            detail=str(e)
        )


def check_current_freshness(workspace_root: Path) -> CheckResult:
    """Prueft ob CURRENT.md aktuell ist."""
    current_path = resolve_paths(workspace_root).current_md
    
    if not current_path.exists():
        return CheckResult(
            name="CURRENT",
            status="error",
            message="Fehlt",
            detail="CURRENT.md nicht gefunden",
            action="Erstelle CURRENT.md mit aktuellem Fokus"
        )
    
    try:
        # Pruefe Datei-Aenderungsdatum
        mtime = datetime.fromtimestamp(current_path.stat().st_mtime)
        age = datetime.now() - mtime
        
        # Pruefe auch den Inhalt auf "Letzte Aktualisierung"
        content = current_path.read_text(encoding="utf-8")
        import re
        update_match = re.search(r"Letzte Aktualisierung:\s*(\d{4}-\d{2}-\d{2})", content)
        
        if update_match:
            last_update = datetime.strptime(update_match.group(1), "%Y-%m-%d")
            age = datetime.now() - last_update
        
        if age.days == 0:
            return CheckResult(
                name="CURRENT",
                status="ok",
                message="Aktuell",
                detail="Heute aktualisiert"
            )
        elif age.days <= 2:
            return CheckResult(
                name="CURRENT",
                status="ok",
                message=f"{age.days}d alt"
            )
        else:
            return CheckResult(
                name="CURRENT",
                status="warning",
                message=f"{age.days} Tage alt",
                detail=f"Letzte Aenderung: {mtime.strftime('%Y-%m-%d')}",
                action="CURRENT.md aktualisieren"
            )
    except Exception as e:
        return CheckResult(
            name="CURRENT",
            status="warning",
            message="Pruefung fehlgeschlagen",
            detail=str(e)
        )


# =============================================================================
# NEUE CHECKS: CORE
# =============================================================================

def check_mcp_tools(workspace_root: Path) -> CheckResult:
    """Prueft registrierte MCP Tools."""
    core_root = resolve_paths(workspace_root).core_root
    server_path = core_root / "mcp" / "nova_mcp_core_server.py"

    if not server_path.exists():
        return CheckResult(
            name="MCP Tools",
            status="error",
            message="MCP server entrypoint fehlt",
            group="CORE"
        )
    
    try:
        content = server_path.read_text(encoding="utf-8")
        # Zaehle Eintraege in TOOLS dict
        import re
        tools = re.findall(r'"nova_\w+":', content)
        count = len(tools)
        
        return CheckResult(
            name="MCP Tools",
            status="ok",
            message=f"{count} Tools",
            group="CORE"
        )
    except Exception as e:
        return CheckResult(
            name="MCP Tools",
            status="warning",
            message="Lesefehler",
            detail=str(e),
            group="CORE"
        )


def check_python_version(workspace_root: Path) -> CheckResult:
    """Prueft Python Version."""
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    if sys.version_info >= (3, 11):
        return CheckResult(
            name="Python",
            status="ok",
            message=f"{version}",
            group="CORE"
        )
    else:
        return CheckResult(
            name="Python",
            status="warning",
            message=f"{version}",
            detail="Empfohlen: 3.11+",
            group="CORE"
        )


def check_core_files(workspace_root: Path) -> CheckResult:
    """Prueft ob Core-Dateien existieren."""
    paths = resolve_paths(workspace_root)
    required_core_files = [
        paths.core_md,
        paths.principles_md,
    ]
    instruction_candidates = [
        workspace_root / "AGENTS.md",
        workspace_root / ".github" / "copilot-instructions.md",
    ]
    
    missing = []
    for f in required_core_files:
        if not f.exists():
            missing.append(f.name)

    if not any(candidate.exists() for candidate in instruction_candidates):
        missing.append("AGENTS.md/.github/copilot-instructions.md")
    
    if missing:
        return CheckResult(
            name="Core Files",
            status="error",
            message=f"{len(missing)} fehlen",
            detail=", ".join(missing),
            group="CORE"
        )
    
    return CheckResult(
        name="Core Files",
        status="ok",
        message=f"{len(required_core_files) + 1} vorhanden",
        group="CORE"
    )


def check_dependencies(workspace_root: Path) -> CheckResult:
    """Prueft ob wichtige Dependencies installiert sind."""
    required = ["mcp", "chromadb", "sentence_transformers"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        return CheckResult(
            name="Dependencies",
            status="warning",
            message=f"{len(missing)} fehlen",
            detail=", ".join(missing),
            action="pip install -r requirements.txt",
            group="CORE"
        )
    
    return CheckResult(
        name="Dependencies",
        status="ok",
        message=f"{len(required)} OK",
        group="CORE"
    )


# =============================================================================
# NEUE CHECKS: VAULT
# =============================================================================

def check_collections(workspace_root: Path) -> CheckResult:
    """Prueft Top-Level-Collections in knowledge_root."""
    knowledge_root = resolve_paths(workspace_root).knowledge_root

    if not knowledge_root.exists():
        return CheckResult(
            name="Collections",
            status="warning",
            message="Knowledge root fehlt",
            detail=str(knowledge_root),
            group="VAULT",
        )

    collections = [
        d.name for d in knowledge_root.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_"))
    ]

    return CheckResult(
        name="Collections",
        status="ok",
        message=f"{len(collections)}",
        group="VAULT",
    )


def check_notes_total(workspace_root: Path) -> CheckResult:
    """Prueft Anzahl Markdown-Notizen in knowledge_root."""
    knowledge_root = resolve_paths(workspace_root).knowledge_root
    if not knowledge_root.exists():
        return CheckResult(
            name="Notes",
            status="warning",
            message="0",
            detail="Knowledge root fehlt",
            group="VAULT",
        )

    note_count = len(list(knowledge_root.rglob("*.md")))
    return CheckResult(
        name="Notes",
        status="ok",
        message=f"{note_count}",
        group="VAULT",
    )


def check_tickets(workspace_root: Path) -> CheckResult:
    """Prueft TICKETS.md."""
    tickets_path = resolve_paths(workspace_root).tickets_md
    
    if not tickets_path.exists():
        return CheckResult(
            name="TICKETS",
            status="warning",
            message="Fehlt",
            action="TICKETS.md erstellen",
            group="VAULT"
        )
    
    return CheckResult(
        name="TICKETS",
        status="ok",
        message="OK",
        group="VAULT"
    )


def check_worklog_exists(workspace_root: Path) -> CheckResult:
    """Prueft ob WORKLOG.md existiert und schreibbar ist."""
    worklog_path = resolve_paths(workspace_root).worklog_md
    
    if not worklog_path.exists():
        return CheckResult(
            name="WORKLOG",
            status="error",
            message="Fehlt",
            action="WORKLOG.md erstellen",
            group="VAULT"
        )
    
    # Pruefe Schreibrechte
    try:
        if os.access(worklog_path, os.W_OK):
            return CheckResult(
                name="WORKLOG",
                status="ok",
                message="OK",
                group="VAULT"
            )
        else:
            return CheckResult(
                name="WORKLOG",
                status="error",
                message="Nicht schreibbar",
                group="VAULT"
            )
    except Exception:
        return CheckResult(
            name="WORKLOG",
            status="ok",
            message="OK",
            group="VAULT"
        )


# =============================================================================
# NEUE CHECKS: CONTENT
# =============================================================================

def check_playbooks(workspace_root: Path) -> CheckResult:
    """Prueft Playbooks."""
    playbooks_path = resolve_paths(workspace_root).core_root / "playbooks"
    
    if not playbooks_path.exists():
        return CheckResult(
            name="Playbooks",
            status="warning",
            message="0",
            group="CONTENT"
        )
    
    playbooks = list(playbooks_path.glob("*.md"))
    return CheckResult(
        name="Playbooks",
        status="ok",
        message=f"{len(playbooks)}",
        group="CONTENT"
    )


def check_guides(workspace_root: Path) -> CheckResult:
    """Prueft Guides."""
    guides_path = resolve_paths(workspace_root).core_root / "guides"
    
    if not guides_path.exists():
        return CheckResult(
            name="Guides",
            status="ok",
            message="0",
            group="CONTENT"
        )
    
    guides = list(guides_path.glob("*.md"))
    return CheckResult(
        name="Guides",
        status="ok",
        message=f"{len(guides)}",
        group="CONTENT"
    )


def check_skills(workspace_root: Path) -> CheckResult:
    """Prueft Agent-Skill-Spezifikationen und Legacy-Skripte."""
    paths = resolve_paths(workspace_root)
    specs_path = paths.knowledge_root / "skills"
    legacy_path = paths.core_root / "skills"

    spec_count = 0
    legacy_count = 0

    if specs_path.exists():
        spec_count = len([f for f in specs_path.rglob("*.md") if f.name.upper() != "README.md"])
    if legacy_path.exists():
        legacy_count = len([f for f in legacy_path.glob("*.py") if not f.name.startswith("_")])

    return CheckResult(
        name="Skills",
        status="ok",
        message=f"specs:{spec_count} | legacy:{legacy_count}",
        group="CONTENT"
    )


def check_templates(workspace_root: Path) -> CheckResult:
    """Prueft Templates in moderner und legacy Struktur."""
    knowledge_root = resolve_paths(workspace_root).knowledge_root
    template_paths = {p for p in knowledge_root.rglob("_template") if p.is_dir()}
    templates_root = knowledge_root / "resources" / "templates"
    if templates_root.exists():
        template_paths.add(templates_root)

    count = len(template_paths)
    return CheckResult(
        name="Templates",
        status="ok",
        message=f"{count}",
        group="CONTENT"
    )


def check_n8n_optional(workspace_root: Path) -> CheckResult:
    """Prueft optionale n8n-Integration (nicht kritisch fuer Core)."""
    cfg = resolve_paths(workspace_root)
    has_url = bool(cfg.n8n_base_url.strip())
    has_key = bool(cfg.n8n_api_key.strip())

    if not has_url and not has_key:
        return CheckResult(
            name="n8n",
            status="info",
            message="Nicht konfiguriert (optional)",
            group="CONTENT"
        )

    if has_url and has_key:
        tls_mode = "insecure TLS" if cfg.n8n_insecure_tls else "TLS verify"
        return CheckResult(
            name="n8n",
            status="ok",
            message=f"Konfiguriert ({tls_mode})",
            group="CONTENT"
        )

    missing = "API Key" if has_url else "Base URL"
    return CheckResult(
        name="n8n",
        status="warning",
        message=f"Teilkonfiguriert ({missing} fehlt)",
        detail="Setze N8N_BASE_URL und N8N_API_KEY",
        action="N8N_BASE_URL + N8N_API_KEY setzen oder n8n ungenutzt lassen",
        group="CONTENT"
    )


# =============================================================================
# RUN ALL CHECKS (GROUPED)
# =============================================================================

async def run_all_checks(workspace_root: Path) -> list[CheckResult]:
    """Fuehrt alle Health Checks aus (Legacy - flache Liste)."""
    groups = await run_grouped_checks(workspace_root)
    return [check for group in groups for check in group.checks]


async def run_grouped_checks(workspace_root: Path) -> list[CheckGroup]:
    """Fuehrt alle Health Checks gruppiert aus."""
    
    # CORE Gruppe
    core_checks = [
        check_mcp_tools(workspace_root),
        check_python_version(workspace_root),
        check_core_files(workspace_root),
        check_dependencies(workspace_root),
    ]
    
    # VAULT Gruppe  
    vault_checks = [
        check_collections(workspace_root),
        check_notes_total(workspace_root),
        check_worklog_exists(workspace_root),
        check_tickets(workspace_root),
    ]
    
    # SEARCH Gruppe (existierende Checks mit Gruppe)
    search_checks = [
        check_embedding_model(workspace_root),
        check_vault_index(workspace_root),
    ]
    
    # CONTENT Gruppe
    content_checks = [
        check_playbooks(workspace_root),
        check_guides(workspace_root),
        check_skills(workspace_root),
        check_templates(workspace_root),
        check_n8n_optional(workspace_root),
    ]
    
    # TODAY Gruppe
    today_checks = [
        check_worklog_today(workspace_root),
        check_current_freshness(workspace_root),
    ]
    
    return [
        CheckGroup("CORE", core_checks),
        CheckGroup("VAULT", vault_checks),
        CheckGroup("SEARCH", search_checks),
        CheckGroup("CONTENT", content_checks),
        CheckGroup("TODAY", today_checks),
    ]


def format_compact(checks: list[CheckResult]) -> str:
    """Formatiert Checks als kompakte Einzeiler fuer session_init (Legacy)."""
    icons = {"ok": "[OK]", "warning": "[WARN]", "error": "[ERR]", "info": "[INFO]"}
    
    parts = []
    for check in checks:
        icon = icons.get(check.status, "[?]")
        msg = check.message
        if check.detail:
            msg += f" ({check.detail})"
        parts.append(f"{icon} {check.name}: {msg}")
    
    return " | ".join(parts)


def format_grouped_compact(groups: list[CheckGroup]) -> str:
    """
    Formatiert gruppierte Checks als 5-Zeilen-Box fuer session_init.
    """
    icons = {"ok": "[OK]", "warning": "[WARN]", "error": "[ERR]", "info": "[INFO]"}
    
    lines = []
    for group in groups:
        parts = []
        for check in group.checks:
            icon = icons.get(check.status, "")
            # Kompakte Darstellung: Name + Message
            if check.status == "ok":
                parts.append(f"{check.name} {icon} {check.message}")
            else:
                parts.append(f"{check.name} {icon}")
        
        line = f"{group.name:<8} {' | '.join(parts)}"
        lines.append(line)
    
    # Einfache Box (ASCII-kompatibel)
    max_len = max(len(line) for line in lines) + 2
    box_top = "+" + "-" * max_len + "+"
    box_bot = "+" + "-" * max_len + "+"
    
    result = [box_top]
    for line in lines:
        result.append(f"| {line:<{max_len-1}}|")
    result.append(box_bot)
    
    return "\n".join(result)


def format_grouped_simple(groups: list[CheckGroup]) -> str:
    """
    Einfachere Version ohne Box - fuer bessere Kompatibilitaet.
    """
    icons = {"ok": "[OK]", "warning": "[WARN]", "error": "[ERR]", "info": "[INFO]"}
    
    lines = []
    for group in groups:
        group_icon = icons.get(group.status, "")
        parts = []
        for check in group.checks:
            icon = icons.get(check.status, "")
            parts.append(f"{check.name} {check.message}")
        
        line = f"{group_icon} **{group.name}:** {' | '.join(parts)}"
        lines.append(line)
    
    return "\n".join(lines)


def format_compact_oneline(checks: list[CheckResult]) -> str:
    """Noch kompaktere Version - nur Icons und Kurzname."""
    icons = {"ok": "[OK]", "warning": "[WARN]", "error": "[ERR]", "info": "[INFO]"}
    
    parts = []
    for check in checks:
        icon = icons.get(check.status, "[?]")
        # Kuerze Namen
        short_names = {
            "Vault Index": "Vault",
            "Embedding Model": "Model", 
            "Worklog": "Log",
            "CURRENT": "Focus",
            "Git": "Git"
        }
        name = short_names.get(check.name, check.name)
        parts.append(f"{icon}{name}")
    
    return " ".join(parts)


def get_actions_required(checks: list[CheckResult]) -> list[str]:
    """Gibt Liste der empfohlenen Aktionen zurueck."""
    return [
        f"-> {check.action}" 
        for check in checks 
        if check.action and check.status in ("warning", "error")
    ]


def get_actions_from_groups(groups: list[CheckGroup]) -> list[str]:
    """Gibt Liste der empfohlenen Aktionen aus Gruppen zurueck."""
    actions = []
    for group in groups:
        for check in group.checks:
            if check.action and check.status in ("warning", "error"):
                actions.append(f"-> {check.action}")
    return actions






