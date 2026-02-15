#!/usr/bin/env python3
"""
NOVA Core Setup - Standalone Setup fuer nova-core

Usage:
    python setup.py                        # Standalone Repo (interaktiv)
    python setup.py --quick                # Standalone Repo (Defaults)
    python nova-core/setup.py              # Embedded in Workspace
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ============================================================================
# Constants
# ============================================================================

NOVA_ASCII = r"""
    _   _______ _    _____
   / | / / __ \ |  / /   |
  /  |/ / / / / | / / /| |
 / /|  / /_/ /| |/ / ___ |
/_/ |_/\____/ |___/_/  |_|
"""

PERSONAS = {
    "default": "Stil-Overlay: professionell, klar, hilfreich",
    "soviet": "Stil-Overlay: direkt, trocken, lakonisch",
    "minimal": "Stil-Overlay: maximal knapp, sachlich",
}

CLIENTS = {
    "copilot": "GitHub Copilot (VS Code Agent Mode)",
    "codex": "Codex (AGENTS.md-basierte Instruktionen)",
    "both": "Beides (Copilot + Codex)",
}

# Default vault layout (domain-neutral)
VAULT_BASE_DIRS = [
    "inbox",
    "areas",
    "projects",
    "resources",
    "operations",
    "archive",
]

VAULT_SUB_DIRS = [
    "projects/client",
    "projects/internal",
    "projects/personal",
    "projects/experiments",
    "areas/business",
    "areas/engineering",
    "areas/learning",
    "areas/personal",
    "resources/playbooks",
    "resources/guides",
    "resources/templates",
    "resources/concepts",
    "resources/decisions",
    "operations/daily",
    "operations/weekly",
    "operations/monthly",
]


def is_within(path: Path, parent: Path) -> bool:
    """True, wenn path in/unter parent liegt."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def default_knowledge_root(core_dir: Path, workspace: Path) -> Path:
    """
    Default-Pfad fuer Knowledge.
    - Standalone (workspace == core_dir): neben nova-core
    - Embedded: im Workspace neben nova-core
    """
    if workspace.resolve() == core_dir.resolve():
        return core_dir.parent / "nova-knowledge"
    return workspace / "nova-knowledge"


def default_index_root(core_dir: Path) -> Path:
    """Default-Pfad fuer Index/Chroma relativ zu core_root."""
    return core_dir / ".nova" / "index"


def default_chroma_path(core_dir: Path) -> Path:
    """Default-Pfad fuer Chroma-DB relativ zu core_root."""
    return default_index_root(core_dir) / "chroma"


def is_invalid_knowledge_root(path: Path, core_dir: Path) -> bool:
    """Knowledge darf nie innerhalb von nova-core liegen."""
    return is_within(path, core_dir)

# ============================================================================
# Config Model
# ============================================================================

@dataclass
class SetupConfig:
    """Setup-Konfiguration."""
    core_dir: Path
    workspace: Path
    knowledge_root: Path | None = None
    chroma_path: Path | None = None
    persona: str = "default"
    vault_name: str = "nova-knowledge"
    search_enabled: bool = True
    create_knowledge: bool = False
    client: str = "copilot"
    update_codex_mcp: bool = False
    
    def __post_init__(self):
        if self.knowledge_root is None:
            self.knowledge_root = default_knowledge_root(self.core_dir, self.workspace)
        if self.chroma_path is None:
            self.chroma_path = default_chroma_path(self.core_dir)


# ============================================================================
# Output Helpers
# ============================================================================

C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "cyan": "\033[96m",
}

def p(text: str = "", style: str = "reset") -> None:
    print(f"{C.get(style, '')}{text}{C['reset']}")

def ok(text: str) -> None:
    print(f"  {C['green']}OK{C['reset']} {text}")

def info(text: str) -> None:
    print(f"  {C['dim']}>{C['reset']} {text}")

def warn(text: str) -> None:
    print(f"  {C['yellow']}!{C['reset']} {text}")

def err(text: str) -> None:
    print(f"  {C['red']}X{C['reset']} {text}")


# ============================================================================
# Detection
# ============================================================================

def detect_setup(workspace: Path, core_dir: Path) -> dict:
    """Erkennt existierende Konfiguration."""
    return {
        "nova_toml": workspace / "nova.toml",
        "mcp_json": workspace / ".vscode" / "mcp.json",
        "core_md": core_dir / "core" / "CORE.md",
        "venv": core_dir / ".venv",
        "existing_knowledge": None,
        "obsidian_vaults": [],
    }


def find_knowledge(workspace: Path, core_dir: Path) -> Path | None:
    """Findet existierenden Knowledge-Ordner."""
    default_path = default_knowledge_root(core_dir, workspace)
    candidates = [
        default_path,
        workspace / "nova-knowledge",
        workspace / "knowledge",
        core_dir.parent / "nova-knowledge",
    ]
    for c in candidates:
        if c.exists() and (c / "CURRENT.md").exists() and not is_invalid_knowledge_root(c, core_dir):
            return c
    return None


def detect_workspace_root(core_dir: Path) -> Path:
    """
    Erkennt den Workspace-Root fuer zwei Layouts:
    - Standalone Repo: workspace == core_dir
    - Embedded Layout: workspace enthaelt Unterordner `nova-core/`
    """
    env_workspace = os.getenv("NOVA_WORKSPACE_ROOT")
    if env_workspace:
        return Path(env_workspace).expanduser().resolve()

    parent = core_dir.parent.resolve()
    cwd = Path.cwd().resolve()

    # Typischer Embedded-Aufruf: `python nova-core/setup.py` aus Workspace-Root
    if cwd == parent:
        return parent

    # Bereits vorhandener Embedded-Workspace (nach erstem Setup)
    if (
        core_dir.name == "nova-core"
        and (parent / "nova-core").resolve() == core_dir.resolve()
        and (
            (parent / "nova.toml").exists()
            or (parent / "nova-knowledge").exists()
            or (parent / ".vscode").exists()
        )
    ):
        return parent

    # Fallback: Standalone
    return core_dir.resolve()


# ============================================================================
# Interactive
# ============================================================================

def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    val = input(f"  {prompt}{hint}: ").strip()
    return val if val else default


def ask_yn(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    val = input(f"  {prompt} {hint}: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes", "j", "ja")


def ask_path(prompt: str, default: Path) -> Path:
    val = ask(prompt, str(default))
    return Path(val).expanduser().resolve()


def ask_choice(options: list[tuple[str, str]], default: int = 0) -> int:
    """Auswahl."""
    p()
    for i, (key, desc) in enumerate(options):
        marker = ">" if i == default else " "
        print(f"  {marker} [{i+1}] {key}: {desc}")
    p()
    while True:
        val = ask("Wahl", str(default + 1))
        try:
            idx = int(val) - 1
        except ValueError:
            warn(f"Ungueltige Eingabe: '{val}'. Bitte Zahl 1-{len(options)} eingeben.")
            continue

        if 0 <= idx < len(options):
            return idx

        warn(f"Ungueltige Auswahl: {val}. Erlaubt ist 1-{len(options)}.")


# ============================================================================
# Setup Steps
# ============================================================================

def check_python() -> bool:
    if sys.version_info < (3, 11):
        err(f"Python 3.11+ required (got {sys.version_info.major}.{sys.version_info.minor})")
        return False
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    return True


def setup_venv(core_dir: Path) -> bool:
    """Erstellt venv in nova-core."""
    venv_path = core_dir / ".venv"
    
    if venv_path.exists():
        ok(".venv exists")
        return True
    
    info("Creating .venv...")
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        err("Failed to create venv")
        return False
    
    pip = venv_path / ("Scripts" if sys.platform == "win32" else "bin") / "pip"
    reqs = core_dir / "requirements.txt"
    
    if reqs.exists():
        info("Installing dependencies...")
        info("Das kann je nach Internet/CPU laenger dauern (typisch ~2-8 Minuten).")
        info("Grund: grosse ML-Dependencies; beim ersten Search-Start folgt zusaetzlich ein Model-Download (~30-90 Sekunden).")
        subprocess.run([str(pip), "install", "-r", str(reqs)], capture_output=True)
    
    ok(".venv created")
    return True


def collect_persona(config: SetupConfig) -> SetupConfig:
    """Persona-Auswahl."""
    p("\n--- Persona ---", "cyan")
    p("CORE.md definiert NOVAs Verhalten und Stil.", "dim")
    p()
    
    options = [(k, v) for k, v in PERSONAS.items()]
    choice = ask_choice(options, default=0)
    config.persona = options[choice][0]
    
    ok(f"Persona: {config.persona}")
    return config


def collect_knowledge(config: SetupConfig) -> SetupConfig:
    """Knowledge-Ordner Konfiguration."""
    p("\n--- Knowledge ---", "cyan")
    p("Wo speichert NOVA Kontext? (CURRENT.md, TICKETS.md, WORKLOG.md)", "dim")
    p()
    
    default_path = default_knowledge_root(config.core_dir, config.workspace)
    existing = find_knowledge(config.workspace, config.core_dir)
    
    options = []
    if existing:
        options.append(("Gefunden", str(existing)))
    options.append(("Neu erstellen", str(default_path)))
    options.append(("Custom", "Eigenen Pfad angeben"))
    
    choice = ask_choice(options, default=0)
    
    if options[choice][0] == "Custom":
        config.knowledge_root = ask_path("Pfad", config.knowledge_root)
        if is_invalid_knowledge_root(config.knowledge_root, config.core_dir):
            warn("Knowledge-Pfad innerhalb von nova-core ist nicht erlaubt. Nutze Standardpfad neben nova-core.")
            config.knowledge_root = default_path
        config.create_knowledge = not config.knowledge_root.exists()
    elif options[choice][0] == "Neu erstellen":
        config.knowledge_root = default_path
        config.create_knowledge = True
    else:
        config.knowledge_root = existing
        config.create_knowledge = False
    
    config.vault_name = config.knowledge_root.name
    return config


def collect_search(config: SetupConfig) -> SetupConfig:
    """Semantic Search Konfiguration."""
    p("\n--- Semantic Search ---", "cyan")
    p("Lokale Vektor-DB fuer bedeutungsbasierte Suche.", "dim")
    p()
    
    config.search_enabled = ask_yn("Aktivieren?", True)
    
    if config.search_enabled:
        config.chroma_path = default_chroma_path(config.core_dir)
    
    return config


def collect_client(config: SetupConfig) -> SetupConfig:
    """Client-Auswahl (Copilot/Codex/Both)."""
    p("\n--- Client ---", "cyan")
    p("Fuer welchen Agent-Client soll Setup optimiert werden?", "dim")
    p()

    options = [(k, v) for k, v in CLIENTS.items()]
    choice = ask_choice(options, default=0)
    config.client = options[choice][0]

    ok(f"Client: {config.client}")
    return config


def list_codex_mcp_servers() -> list[dict[str, str]]:
    """Liest alle [mcp_servers.*]-Eintraege aus ~/.codex/config.toml."""
    config_path = Path.home() / ".codex" / "config.toml"
    if not config_path.exists():
        return []

    content = config_path.read_text(encoding="utf-8")
    section_re = re.compile(r"(?ms)^\[mcp_servers\.([^\]]+)\]\n.*?(?=^\[|\Z)")
    result: list[dict[str, str]] = []

    for m in section_re.finditer(content):
        name = m.group(1).strip()
        section = m.group(0)
        command = re.search(r'(?m)^command\s*=\s*"(.*?)"\s*$', section)
        cwd = re.search(r'(?m)^cwd\s*=\s*"(.*?)"\s*$', section)
        args = re.search(r"(?m)^args\s*=\s*\[(.*?)\]\s*$", section)
        result.append(
            {
                "name": name,
                "command": command.group(1) if command else "",
                "cwd": cwd.group(1) if cwd else "",
                "args": args.group(1) if args else "",
            }
        )

    return result


def analyze_codex_config(core_dir: Path) -> tuple[str, str]:
    """
    Bewertet ~/.codex/config.toml fuer nova-skills.
    Returns: (status, detail)
    status in {"missing_file", "missing_section", "mismatch", "ok"}
    """
    config_path = Path.home() / ".codex" / "config.toml"
    if not config_path.exists():
        return ("missing_file", f"{config_path} fehlt")

    content = config_path.read_text(encoding="utf-8")
    section_re = re.compile(r"(?ms)^\[mcp_servers\.nova-skills\]\n.*?(?=^\[|\Z)")
    match = section_re.search(content)
    if not match:
        return ("missing_section", "[mcp_servers.nova-skills] fehlt")

    section = match.group(0)
    expected_server = str((core_dir / "launcher.py").resolve()).lower()
    expected_cwd = str(core_dir.resolve()).lower()

    server_match = re.search(r'(?m)^args\s*=\s*\[\s*"(.*?)"\s*\]\s*$', section)
    cwd_match = re.search(r'(?m)^cwd\s*=\s*"(.*?)"\s*$', section)

    if not server_match or not cwd_match:
        return ("mismatch", "args/cwd unvollstaendig")

    actual_server = server_match.group(1).replace("\\\\", "\\").lower()
    actual_cwd = cwd_match.group(1).replace("\\\\", "\\").lower()

    if actual_server != expected_server or actual_cwd != expected_cwd:
        return (
            "mismatch",
            f"gefunden: args={server_match.group(1)} | cwd={cwd_match.group(1)}",
        )

    return ("ok", "bereits auf diesen Workspace gesetzt")


def collect_codex_setup(config: SetupConfig) -> SetupConfig:
    """Interaktive Abfrage fuer Codex-MCP-Konfiguration."""
    if config.client not in ("codex", "both"):
        config.update_codex_mcp = False
        return config

    p("\n--- Codex MCP ---", "cyan")
    p(
        "Pruefe ~/.codex/config.toml, damit Codex den MCP-Server im aktuellen Workspace startet.",
        "dim",
    )
    p(
        "Wenn hier ein alter Pfad steht, landen Index/Tools im falschen Projekt.",
        "dim",
    )
    p()

    servers = list_codex_mcp_servers()
    if servers:
        p("Gefundene MCP-Server in ~/.codex/config.toml:", "dim")
        for srv in servers:
            info(
                f"{srv['name']} | command={srv['command'] or '-'} | cwd={srv['cwd'] or '-'}"
            )
    else:
        info("Keine [mcp_servers.*]-Eintraege gefunden.")
        info(
            "Wenn du jetzt bestaetigst, wird nova-skills eingetragen und bei Codex-Start automatisch gestartet (stdio)."
        )
    p()

    other_nova = [
        srv
        for srv in servers
        if "nova" in srv["name"].lower() and srv["name"].lower() != "nova-skills"
    ]
    if other_nova:
        warn("Andere Nova-Instanz(en) erkannt:")
        for srv in other_nova:
            warn(f"- {srv['name']} (cwd={srv['cwd'] or '-'})")
        info(
            "Pruefe Doppelkonfigurationen, damit nicht versehentlich die falsche Nova-Instanz genutzt wird."
        )
        p()

    status, detail = analyze_codex_config(config.core_dir)
    if status == "ok":
        ok(f"Codex MCP: {detail}")
        config.update_codex_mcp = ask_yn(
            "Trotzdem neu schreiben (idempotent)?", False
        )
    elif status in ("missing_file", "missing_section"):
        warn(f"Codex MCP: {detail}")
        info("Bei 'Ja' wird [mcp_servers.nova-skills] in ~/.codex/config.toml angelegt.")
        info("Gesetzt werden nur: args=<.../launcher.py>, command=python, cwd=<.../nova-core>.")
        config.update_codex_mcp = ask_yn(
            "Codex MCP jetzt automatisch einrichten?", True
        )
    else:
        warn(f"Codex MCP: {detail}")
        info("Bei 'Ja' wird nur der Block [mcp_servers.nova-skills] auf den aktuellen Workspace korrigiert.")
        info("Andere Einstellungen in ~/.codex/config.toml bleiben unveraendert.")
        config.update_codex_mcp = ask_yn(
            "Auf aktuellen Workspace korrigieren?", True
        )

    if config.update_codex_mcp:
        ok("Codex MCP wird beim Apply aktualisiert (wirksam nach Codex/IDE-Neustart)")
    else:
        info("Codex MCP bleibt unveraendert")
    return config


def show_preview(config: SetupConfig, findings: dict) -> None:
    """Preview der Aenderungen."""
    p("\n--- Preview ---", "cyan")
    p()
    
    p("Dateien:", "bold")
    
    if findings["nova_toml"].exists():
        info("nova.toml (ueberschreiben)")
    else:
        ok("nova.toml (neu)")
    
    if findings["mcp_json"].exists():
        info(".vscode/mcp.json (ueberschreiben)")
    else:
        ok(".vscode/mcp.json (neu)")

    if config.client in ("copilot", "both"):
        instructions_path = config.workspace / ".github" / "copilot-instructions.md"
        if instructions_path.exists():
            info(".github/copilot-instructions.md (behalten)")
        else:
            ok(".github/copilot-instructions.md (neu)")

    if config.client in ("codex", "both"):
        agents_path = config.workspace / "AGENTS.md"
        if agents_path.exists():
            info("AGENTS.md (behalten)")
        else:
            ok("AGENTS.md (neu)")
        if config.update_codex_mcp:
            ok("~/.codex/config.toml (mcp_servers.nova-skills aktualisieren)")
        else:
            info("~/.codex/config.toml (unveraendert)")

    if not is_within(config.knowledge_root, config.workspace):
        workspace_file = config.workspace / "nova.code-workspace"
        if workspace_file.exists():
            info("nova.code-workspace (aktualisieren)")
        else:
            ok("nova.code-workspace (neu)")
    
    ok(f"core/CORE.md <- templates/personas/base.md + {config.persona}.md")
    
    if config.create_knowledge:
        ok(f"{config.knowledge_root.name}/ (erstellen mit Templates)")
    
    p()
    p("Konfiguration:", "bold")
    info(f"persona        = {config.persona}")
    info(f"knowledge_root = {config.knowledge_root}")
    info(f"chroma_path    = {config.chroma_path}")
    info(f"search_enabled = {config.search_enabled}")
    info(f"client         = {config.client}")
    p()


def apply_config(config: SetupConfig) -> bool:
    """Wendet Konfiguration an."""
    templates_dir = config.core_dir / "templates"
    if is_invalid_knowledge_root(config.knowledge_root, config.core_dir):
        err(f"Knowledge path not allowed inside nova-core: {config.knowledge_root}")
        return False
    
    # 1. CORE.md aus Base + Persona-Overlay
    base_src = templates_dir / "personas" / "base.md"
    persona_src = templates_dir / "personas" / f"{config.persona}.md"
    core_dst = config.core_dir / "core" / "CORE.md"
    core_dst.parent.mkdir(parents=True, exist_ok=True)
    
    if base_src.exists() and persona_src.exists():
        base_content = base_src.read_text(encoding="utf-8").strip()
        persona_content = persona_src.read_text(encoding="utf-8").strip()
        combined = (
            f"{base_content}\n\n"
            "---\n\n"
            f"{persona_content}\n"
        )
        core_dst.write_text(combined, encoding="utf-8")
        ok(f"CORE.md <- base + {config.persona}")
    elif persona_src.exists():
        shutil.copy(persona_src, core_dst)
        warn("base.md not found, fallback to persona-only CORE.md")
        ok(f"CORE.md <- {config.persona}")
    else:
        warn(f"Persona template not found: {persona_src}")
    
    # 2. Knowledge-Ordner erstellen
    if config.create_knowledge:
        config.knowledge_root.mkdir(parents=True, exist_ok=True)
        
        knowledge_templates = templates_dir / "knowledge"
        if knowledge_templates.exists():
            for tmpl in knowledge_templates.glob("*.md"):
                dst = config.knowledge_root / tmpl.name
                if not dst.exists():
                    shutil.copy(tmpl, dst)

        ok(f"Knowledge: {config.knowledge_root}")

        # Empfohlene Basisstruktur fuer neue Vaults (optional, nicht erzwungen)
        for rel_dir in [*VAULT_BASE_DIRS, *VAULT_SUB_DIRS]:
            (config.knowledge_root / rel_dir).mkdir(parents=True, exist_ok=True)
    
    # 3. .nova/ Infrastruktur (immer relativ zum gewaehlten core_root)
    index_root = config.chroma_path.parent
    index_root.mkdir(parents=True, exist_ok=True)
    config.chroma_path.mkdir(parents=True, exist_ok=True)

    def _toml_path_for_workspace(path: Path) -> str:
        """
        Prefer relative POSIX paths in nova.toml.
        Falls relative nicht moeglich ist (z.B. anderer Drive auf Windows),
        wird ein absoluter POSIX-Pfad geschrieben.
        """
        try:
            return path.resolve().relative_to(config.workspace.resolve()).as_posix() or "."
        except ValueError:
            return path.resolve().as_posix()
    
    # 4. nova.toml
    toml_content = f"""# NOVA Configuration
# Generated by setup.py

[paths]
core_root = "{_toml_path_for_workspace(config.core_dir)}"
knowledge_root = "{_toml_path_for_workspace(config.knowledge_root)}"
index_root = "{_toml_path_for_workspace(index_root)}"

[vault]
name = "{config.vault_name}"

[search]
enabled = {'true' if config.search_enabled else 'false'}
chroma_path = "{_toml_path_for_workspace(config.chroma_path)}"
embedding_model = "all-MiniLM-L6-v2"
top_k = 5

[logging]
level = "INFO"
"""
    (config.workspace / "nova.toml").write_text(toml_content, encoding="utf-8")
    ok("nova.toml")
    
    # 5. .vscode/mcp.json
    vscode_dir = config.workspace / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    
    if config.workspace == config.core_dir:
        launcher_arg = "${workspaceFolder}/launcher.py"
    else:
        launcher_arg = "${workspaceFolder}/nova-core/launcher.py"

    mcp_config = {
        "servers": {
            "nova-skills": {
                "type": "stdio",
                "command": "python",
                "args": [launcher_arg],
                "cwd": "${workspaceFolder}"
            }
        }
    }
    (vscode_dir / "mcp.json").write_text(json.dumps(mcp_config, indent=2), encoding="utf-8")
    ok(".vscode/mcp.json")
    
    # 6. .gitignore
    gitignore = config.workspace / ".gitignore"
    additions = [".nova/", "nova.toml"]
    if config.knowledge_root.parent == config.workspace:
        additions.append(f"{config.knowledge_root.name}/")
    
    existing_content = gitignore.read_text() if gitignore.exists() else ""
    to_add = [a for a in additions if a not in existing_content]
    
    if to_add:
        with gitignore.open("a") as f:
            f.write("\n# NOVA (private)\n" + "\n".join(to_add) + "\n")
        ok(".gitignore updated")
    
    # 7. client-spezifische Instruktionen
    if config.client in ("copilot", "both"):
        gh_dir = config.workspace / ".github"
        gh_dir.mkdir(exist_ok=True)

        instructions = gh_dir / "copilot-instructions.md"
        if not instructions.exists():
            if config.workspace == config.core_dir:
                core_ref = "../core/CORE.md"
            else:
                core_ref = "../nova-core/core/CORE.md"
            instructions.write_text("""# NOVA Agent Instructions

Du bist NOVA - ein persistentes, agentenfähiges Kontextsystem.

## SESSION-START (PFLICHT)

Bei JEDER neuen Konversation SOFORT ausfuehren:

```
nova_context_resolve(query="session init")
```

Keine anderen Tools vorher. Keine Fragen. Einfach ausfuehren.

## Weitere Regeln

Details in: [CORE.md]({core_ref})
""".replace("{core_ref}", core_ref), encoding="utf-8")
            ok(".github/copilot-instructions.md")

    if config.client in ("codex", "both"):
        agents = config.workspace / "AGENTS.md"
        if not agents.exists():
            if config.workspace == config.core_dir:
                core_path_hint = "core/CORE.md"
            else:
                core_path_hint = "nova-core/core/CORE.md"
            agents.write_text("""# Agent Instructions

## Session Start

- On every new session, run `nova_context_resolve(query="session init")` as the very first action before any response to the user.
- On every new session, read the current version of core.md. That is you. `{core_path_hint}`
- If the tool call fails, report the failure briefly and continue with the best available local context.
""".replace("{core_path_hint}", core_path_hint), encoding="utf-8")
            ok("AGENTS.md")

    # 8. Optional: VS Code Multi-Root Workspace (falls Knowledge ausserhalb liegt)
    if not is_within(config.knowledge_root, config.workspace):
        workspace_file = config.workspace / "nova.code-workspace"

        try:
            existing = {}
            if workspace_file.exists():
                existing = json.loads(workspace_file.read_text(encoding="utf-8"))
                if not isinstance(existing, dict):
                    existing = {}
        except Exception:
            existing = {}

        folders = existing.get("folders", [])
        if not isinstance(folders, list):
            folders = []

        def _folder_path(path: Path) -> str:
            try:
                return path.resolve().relative_to(config.workspace.resolve()).as_posix() or "."
            except ValueError:
                return path.resolve().as_posix()

        core_folder = "."
        knowledge_folder = _folder_path(config.knowledge_root)

        existing_paths = {
            str(entry.get("path")).strip()
            for entry in folders
            if isinstance(entry, dict) and entry.get("path")
        }

        changed = False
        if core_folder not in existing_paths:
            folders.append({"path": core_folder, "name": config.core_dir.name})
            changed = True
        if knowledge_folder not in existing_paths:
            folders.append({"path": knowledge_folder, "name": config.knowledge_root.name})
            changed = True

        existing["folders"] = folders

        if changed or not workspace_file.exists():
            workspace_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            ok("nova.code-workspace")
    
    return True


def show_current_config(workspace: Path) -> None:
    """Zeigt aktuelle Config."""
    toml_path = workspace / "nova.toml"
    
    if not toml_path.exists():
        setup_cmd = "python setup.py" if workspace == Path(__file__).parent.resolve() else "python nova-core/setup.py"
        warn(f"No nova.toml found. Run: {setup_cmd}")
        return
    
    p("\n--- Current Config ---", "cyan")
    p()
    print(toml_path.read_text())


def get_venv_python(core_dir: Path) -> Path | None:
    """Liefert den Python-Interpreter aus .venv."""
    if sys.platform == "win32":
        candidate = core_dir / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = core_dir / ".venv" / "bin" / "python"
    return candidate if candidate.exists() else None


def run_quality_gate(core_dir: Path, workspace: Path) -> bool:
    """Fuehrt einen kompakten Satz wichtiger Tests aus."""
    venv_python = get_venv_python(core_dir)
    if venv_python is None:
        warn("Quality gate uebersprungen: .venv Python nicht gefunden")
        return True

    critical_test_candidates = [
        str(core_dir / "mcp" / "tools" / "tests" / "test_context_session_init.py"),
        str(core_dir / "mcp" / "tools" / "tests" / "test_health_check.py"),
        str(core_dir / "mcp" / "tools" / "tests" / "test_search_search_vault.py"),
    ]
    critical_tests = [p for p in critical_test_candidates if Path(p).exists()]

    if not critical_tests:
        warn(
            "Quality gate uebersprungen: keine kritischen Tests unter "
            "mcp/tools/tests gefunden."
        )
        info("Hinweis: Fuege Tests hinzu oder passe den Quality-Gate-Testsatz an.")
        return True

    cmd = [str(venv_python), "-m", "pytest", "-q", *critical_tests]
    info("Running critical tests...")
    result = subprocess.run(cmd, cwd=workspace)
    return result.returncode == 0


def show_next_steps(config: SetupConfig, quality_gate_ran: bool) -> None:
    """Client-spezifische Next Steps."""
    p("Next steps:")
    p("  1. Open VS Code in workspace")

    if config.client == "copilot":
        p("  2. Copilot Chat (Ctrl+Shift+I)")
        p("  3. Agent mode")
        p("  4. In neuer Session sofort als ersten Tool-Call: nova_context_resolve")
    elif config.client == "codex":
        p("  2. Ensure AGENTS.md is loaded by Codex in workspace root")
        p("  3. Start Codex session in this workspace")
        p("  4. In neuer Session sofort als ersten Tool-Call: nova_context_resolve")
    else:
        p("  2. Copilot path: Copilot Chat (Ctrl+Shift+I) -> Agent mode -> nova_context_resolve")
        p("  3. Codex path: start Codex in workspace root -> nova_context_resolve")
        p("  4. Verify both instruction files: .github/copilot-instructions.md + AGENTS.md")

    quality_gate_cmd = (
        "python -m pytest mcp/tools/tests -q"
        if config.workspace == config.core_dir
        else "python -m pytest nova-core/mcp/tools/tests -q"
    )
    local_tool_cmd = (
        "python mcp/local_tool_runner.py --list"
        if config.workspace == config.core_dir
        else "python nova-core/mcp/local_tool_runner.py --list"
    )

    if quality_gate_ran:
        p("  5. Quality gate wurde bereits ausgefuehrt (kritische Tests)")
    else:
        p(f"  5. Quality gate: {quality_gate_cmd}")
    p(f"  6. Local tool run (fallback): {local_tool_cmd}")
    if not is_within(config.knowledge_root, config.workspace):
        p("  7. VS Code multi-root: open `nova.code-workspace` to include knowledge folder")
    p()


def update_codex_config(core_dir: Path) -> bool:
    """Aktualisiert ~/.codex/config.toml fuer den nova-skills MCP-Server."""
    codex_dir = Path.home() / ".codex"
    config_path = codex_dir / "config.toml"

    launcher_py = (core_dir / "launcher.py").resolve()
    cwd = core_dir.resolve()

    # Use forward slashes for TOML - works on Windows and avoids escape issues.
    server_s = launcher_py.as_posix()
    cwd_s = cwd.as_posix()

    block = (
        "[mcp_servers.nova-skills]\n"
        f'args = ["{server_s}"]\n'
        'command = "python"\n'
        f'cwd = "{cwd_s}"\n'
    )

    codex_dir.mkdir(parents=True, exist_ok=True)
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""

    section_re = re.compile(
        r"(?ms)^\[mcp_servers\.nova-skills\]\n.*?(?=^\[|\Z)"
    )

    if section_re.search(existing):
        updated = section_re.sub(block + "\n", existing, count=1)
    else:
        sep = "\n" if existing and not existing.endswith("\n") else ""
        updated = f"{existing}{sep}\n{block}" if existing else f"{block}\n"

    config_path.write_text(updated, encoding="utf-8")
    ok(f"Codex MCP config: {config_path}")
    return True


# ============================================================================
# Main
# ============================================================================

def run(
    quick: bool = False,
    show: bool = False,
    client: str | None = None,
    skip_quality_gate: bool = False,
    update_codex_mcp: bool = False,
) -> int:
    core_dir = Path(__file__).parent.resolve()
    workspace = detect_workspace_root(core_dir)
    
    if show:
        show_current_config(workspace)
        return 0
    
    p(NOVA_ASCII, "cyan")
    p("  NOVA Core Setup", "bold")
    p(f"  Core: {core_dir}", "dim")
    p(f"  Workspace: {workspace}\n", "dim")
    
    # Check
    if not check_python():
        return 1
    
    # Detect
    findings = detect_setup(workspace, core_dir)
    
    # Config
    config = SetupConfig(core_dir=core_dir, workspace=workspace)
    if client:
        config.client = client
    if update_codex_mcp:
        config.update_codex_mcp = True
    
    if quick:
        config.persona = "default"
        existing = find_knowledge(workspace, core_dir)
        if existing:
            config.knowledge_root = existing
            config.create_knowledge = False
        else:
            config.knowledge_root = default_knowledge_root(core_dir, workspace)
            config.create_knowledge = True
    else:
        if not client:
            config = collect_client(config)
        config = collect_persona(config)
        config = collect_knowledge(config)
        config = collect_search(config)
        # Interaktive DAU-Sicherung: nur relevant wenn Codex genutzt wird.
        if not update_codex_mcp:
            config = collect_codex_setup(config)
    
    # Preview
    show_preview(config, findings)
    
    if not quick:
        if not ask_yn("Anwenden?", True):
            p("\nAbgebrochen.", "yellow")
            return 0
    
    # venv
    p("\n--- Environment ---", "cyan")
    p("Python venv fuer MCP-Server.", "dim")
    if not setup_venv(core_dir):
        return 1
    
    # Apply
    p("\n--- Applying ---", "cyan")
    if not apply_config(config):
        return 1

    if config.update_codex_mcp:
        p("\n--- Codex MCP ---", "cyan")
        p("Aktualisiere ~/.codex/config.toml fuer aktuellen Workspace.", "dim")
        try:
            update_codex_config(core_dir)
        except Exception as e:
            warn(f"Codex config update failed: {e}")

    quality_gate_ran = False
    if not skip_quality_gate:
        p("\n--- Quality Gate ---", "cyan")
        p("Wichtige MCP Tool-Tests werden ausgefuehrt.", "dim")
        quality_gate_ran = run_quality_gate(core_dir, workspace)
        if not quality_gate_ran:
            err("Quality gate failed")
            return 1
        ok("Quality gate passed")
    
    # Done
    p("\n--- Done ---", "green")
    p()
    show_next_steps(config, quality_gate_ran=quality_gate_ran)
    
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NOVA Core Setup")
    parser.add_argument("-q", "--quick", action="store_true", help="Quick with defaults")
    parser.add_argument("-s", "--show", action="store_true", help="Show current config")
    parser.add_argument(
        "--client",
        choices=["copilot", "codex", "both"],
        default=None,
        help="Target client profile for generated instructions",
    )
    parser.add_argument(
        "--skip-quality-gate",
        action="store_true",
        help="Skip automatic post-setup critical tests",
    )
    parser.add_argument(
        "--update-codex-config",
        action="store_true",
        help="Update ~/.codex/config.toml mcp_servers.nova-skills to this workspace",
    )
    args = parser.parse_args()
    
    try:
        return run(
            quick=args.quick,
            show=args.show,
            client=args.client,
            skip_quality_gate=args.skip_quality_gate,
            update_codex_mcp=args.update_codex_config,
        )
    except KeyboardInterrupt:
        p("\n\nAborted.", "yellow")
        return 130


if __name__ == "__main__":
    sys.exit(main())
