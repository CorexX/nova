# NOVA Architecture

> Die komplette Architektur in einem Dokument.
> Minimalistisch, aber vollständig.

---

<!-- COMPACT_START - Diese Sektion wird vom nova_get_architecture Tool extrahiert -->

## Quick Reference (Agent Context)

> **Vault = Source of Truth.** Chat ist Arbeitsfläche, nicht Ergebnis.

### Struktur
```
NOVA/                   # Framework (public) - Code, Skills, Regeln
├── core/CORE.md        # Agent-Grundregeln (generiert aus templates/)
├── mcp/                # MCP Server + Tool-Adapter
│   └── tools/          # 11 Tool-Module
├── skills/             # CLI-Skripte (eigenständig)
├── playbooks/          # Workflows (close_day, etc.)
├── templates/          # Source of Truth für Personas + Projekt-Templates
│   ├── personas/       # base.md + persona overlays
│   └── knowledge/      # CURRENT.md, TICKETS.md, WORKLOG.md
└── meta/               # Framework-Dokumentation
    ├── ARCHITECTURE.md # Diese Datei
    ├── PRINCIPLES.md   # Kernprinzipien
    ├── ROADMAP.md      # Entwicklungsplanung
    └── SYSTEM.md       # System-Übersicht

nova-knowledge/         # Daten (privat) - Arbeit, Kunden, Wissen
├── WORKLOG.md          # Append-only Arbeitslog
├── CURRENT.md          # Aktueller Fokus
├── TICKETS.md          # Budgets, Zeiterfassung
├── projects/           # Kundenprojekte + Interne Projekte
└── resources/          # Guides, Decisions, Templates
```

### Schichten
```
Interface    → Copilot Chat | CLI | API
Protocol     → MCP (Model Context Protocol)
Tools        → mcp/tools/*.py (Adapter)
Skills       → skills/*.py (eigenständige CLI)
Persistence  → Markdown + Git
```

### Design-Regeln
1. **Vault = Truth** - Ergebnisse in Dateien, nicht Chat
2. **Append-only** - WORKLOG nur anhängen
3. **MCP Tools nutzen** - Bevorzuge MCP-Tools für Agent-Interaktion
4. **Agent schlägt vor** - Mensch entscheidet

### Schreib-Scope (Agent)
- ✅ `nova-knowledge/WORKLOG.md` (append)
- ✅ `nova-knowledge/CURRENT.md`, `TICKETS.md` (edit)
- ✅ `**/knowledge/*.md` (neue Dateien)
- ❌ `NOVA/**` (Framework-Code)
- ❌ Bestehende Notes überschreiben

### MCP Tools (Kern)
| Tool | Funktion |
|------|----------|
| `nova_context_resolve` | Kontext selektiv auflösen |
| `nova_project_continue` | Projekt fortsetzen |
| `nova_project_create` | Neues Projekt anlegen |
| `nova_knowledge_query` | Semantische Wissenssuche |
| `nova_knowledge_update` | Erkenntnisse persistieren |
| `nova_system_maintain` | System-Health, Index, Restart |

<!-- COMPACT_END -->

---

## Inhaltsverzeichnis

1. [Philosophie](#1-philosophie)
2. [System-Übersicht](#2-system-übersicht)
3. [Schichtenmodell](#3-schichtenmodell)
4. [Komponenten](#4-komponenten)
5. [Datenfluss](#5-datenfluss)
6. [Design-Prinzipien](#6-design-prinzipien)
7. [Konventionen](#7-konventionen)
8. [Erweiterung](#8-erweiterung)
9. [Sicherheit](#9-sicherheit)
10. [Roadmap-Architektur](#10-roadmap-architektur)

---

## 1. Philosophie

### Das Problem

```
┌─────────────────────────────────────────────────────────────────┐
│  Chat mit KI-Agent                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ "Erkenntnisse entstehen..."                               │  │
│  │ "Wichtige Entscheidungen werden getroffen..."             │  │
│  │ "Kontext wird aufgebaut..."                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▼                                   │
│                    [ Session endet ]                            │
│                              ▼                                   │
│                         ∅ VERLOREN                              │
└─────────────────────────────────────────────────────────────────┘
```

### Die Lösung

```
┌─────────────────────────────────────────────────────────────────┐
│                        NOVA PRINZIP                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   CHAT = Arbeitsfläche        VAULT = Ergebnis                 │
│   (temporär, flüchtig)        (persistent, versioniert)        │
│                                                                 │
│        ┌──────────┐               ┌──────────┐                 │
│        │ Denken   │ ────────────▶ │ Markdown │                 │
│        │ Reden    │   speichern   │ + Git    │                 │
│        │ Arbeiten │               │          │                 │
│        └──────────┘               └──────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Kernaussage

> **Vault = Source of Truth.**
> Alles Relevante gehört in Dateien, nicht in den Chat.

---

## 2. System-Übersicht

### Aktueller Stand (Phase 1)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│     ┌─────────────┐         ┌─────────────┐                    │
│     │   MENSCH    │◀───────▶│   COPILOT   │                    │
│     │             │  Chat   │    Chat     │                    │
│     └─────────────┘         └──────┬──────┘                    │
│                                    │                            │
│                                    │ MCP Protocol               │
│                                    ▼                            │
│                           ┌──────────────┐                      │
│                           │  MCP Server  │                      │
│                           │  (Python)    │                      │
│                           └──────┬───────┘                      │
│                                  │                              │
│                    ┌─────────────┼─────────────┐               │
│                    │             │             │               │
│                    ▼             ▼             ▼               │
│              ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│              │  Skills  │ │  Skills  │ │  Skills  │           │
│              │  (CLI)   │ │  (CLI)   │ │  (CLI)   │           │
│              └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│                   │            │            │                  │
│                   └────────────┼────────────┘                  │
│                                ▼                                │
│                    ┌───────────────────────┐                   │
│                    │        VAULT          │                   │
│                    │  ┌─────────────────┐  │                   │
│                    │  │  nova-core      │  │                   │
│                    │  │  nova-knowledge │  │                   │
│                    │  └─────────────────┘  │                   │
│                    │       Markdown        │                   │
│                    │       + Git           │                   │
│                    └───────────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Ziel-Architektur (Multi-Interface)

```
                         ┌─────────────────┐
                         │   NOVA CORE     │
                         │  (LLM + Skills) │
                         └────────┬────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
       ┌────┴────┐          ┌─────┴─────┐         ┌─────┴─────┐
       │ VS Code │          │    CLI    │         │ Messenger │
       │ Copilot │          │   (MCP)   │         │  (Bot)    │
       └─────────┘          └───────────┘         └───────────┘
        Phase 1               Phase 2               Phase 2
        CURRENT
                                  │
                                  ▼
                           ┌───────────┐
                           │   VAULT   │
                           │           │
                           └───────────┘
```

---

## 3. Schichtenmodell

```
┌─────────────────────────────────────────────────────────────────┐
│ INTERFACE LAYER                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │  Copilot Chat  │  CLI  │  REST API  │  Messenger Bot       │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ PROTOCOL LAYER                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │  MCP (Model Context Protocol)  │  HTTP  │  Webhook         │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ TOOL LAYER                                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │  MCP Server (server.py)                                     │ │
│ │  └─ Tool Adapter (tools/*.py)                               │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ SKILL LAYER                                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │  Standalone CLI Scripts (skills/*.py)                       │ │
│ │  └─ Unabhängig von MCP, direkt ausführbar                   │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ PERSISTENCE LAYER                                               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │  Markdown Files (*.md)                                      │ │
│ │  └─ Git Versionierung                                       │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Warum diese Trennung?

| Problem | Lösung durch Schichten |
|---------|------------------------|
| MCP-Tools sind schwer zu testen | Skills sind eigenständige CLI-Skripte |
| Vendor Lock-in zu Copilot | Skills funktionieren auch ohne VS Code |
| Komplexe Debugging-Sessions | Jede Schicht kann isoliert debuggt werden |
| Schwer zu erweitern | Neue Skills ohne MCP-Änderungen möglich |

---

## 4. Komponenten

### 4.1 Repository-Trennung

```
NOVA/
├── nova-core/          # Framework (public-fähig)
│   ├── core/           # Agent-Regeln
│   ├── skills/         # CLI-Skripte
│   ├── mcp/            # MCP Server + Tools
│   ├── playbooks/      # Workflows
│   ├── guides/         # How-Tos
│   ├── knowledge/      # Framework-Wissen
│   └── meta/           # Architektur, ADRs
│
└── nova-knowledge/     # Daten (privat)
    ├── CURRENT.md      # Aktueller Fokus
    ├── WORKLOG.md      # Append-only Log
    ├── TICKETS.md      # Budgets
    ├── kunden/         # Kundenprojekte
    ├── kompetenz/      # Fachgebiete
    └── weekly/         # Wochenberichte
```

### Warum getrennt?

| Aspekt | nova-core | nova-knowledge |
|--------|-----------|----------------|
| **Inhalt** | Code, Regeln | Persönliche Daten |
| **Sichtbarkeit** | Public-fähig | Strikt privat |
| **Änderungsrate** | Selten | Täglich |
| **Sharing** | Wiederverwendbar | Niemals teilen |

### 4.2 MCP Server

```
nova-core/mcp/
├── server.py           # Hauptserver (Entry Point)
├── requirements.txt    # Dependencies
└── tools/              # Tool-Adapter
    ├── __init__.py
    ├── git/
    │   └── push_repos.py
    ├── worklog/
    │   └── append.py
    ├── skills/
    │   └── list_skills.py
    ├── testing/
    │   └── run_tests.py
    └── tests/          # PFLICHT für jedes Tool
        ├── conftest.py
        └── test_*.py
```

### 4.3 Skills

```
nova-core/skills/
├── list_skills.py      # Meta: Welche Skills gibt es?
├── summarize_day.py    # Sessions zusammenfassen
└── [weitere].py
```

**Charakteristik eines Skills:**

```python
#!/usr/bin/env python3
"""
Skill: [Name]
[Beschreibung]

Usage:
    python [name].py [--options]
"""

# 1. Eigenständig ausführbar (kein Import nötig)
# 2. CLI-Interface mit argparse
# 3. Keine MCP-Dependencies
# 4. Vault-Pfade werden als Parameter übergeben
```

### 4.4 Playbooks

```
nova-core/playbooks/
└── close_day.md        # Tagesabschluss-Workflow
```

**Playbook-Struktur:**

```markdown
# Playbook: [Name]

## Trigger
- "close day"
- Tagesende

## Schritte
1. WORKLOG lesen
2. TICKETS laden
3. Zeitvorschlag erstellen

## Output
- Zeitbuchungs-Vorschlag
```

---

## 5. Datenfluss

### 5.1 Synchroner Flow (Copilot Chat)

```
┌────────────────────────────────────────────────────────────────┐
│  1. USER INPUT                                                 │
│     "Füge zum Worklog hinzu: Meeting mit Kunde X"              │
└─────────────────────────────┬──────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  2. COPILOT INTERPRETATION                                     │
│     → Erkennt: worklog_append Tool benötigt                    │
│     → Parameter: entry="Meeting mit Kunde X"                   │
└─────────────────────────────┬──────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  3. MCP TOOL CALL                                              │
│     nova_worklog_append(entry="Meeting mit Kunde X")           │
└─────────────────────────────┬──────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  4. TOOL ADAPTER (tools/worklog/append.py)                     │
│     → Validiert Parameter                                      │
│     → Formatiert Entry: "- 14:30 Meeting mit Kunde X"          │
└─────────────────────────────┬──────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  5. FILE OPERATION                                             │
│     append(nova-knowledge/WORKLOG.md, entry)                   │
└─────────────────────────────┬──────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  6. RESPONSE TO USER                                           │
│     "Appended to WORKLOG.md: - 14:30 Meeting mit Kunde X"      │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 Asynchroner Flow (Phase 2: Ingestion)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   TELEGRAM   │────▶│   GATEWAY    │────▶│    QUEUE     │
│   Message    │     │   Validate   │     │   Buffer     │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
                     ┌──────────────┐     ┌──────────────┐
                     │    VAULT     │◀────│   WORKER     │
                     │   Write      │     │   Process    │
                     └──────────────┘     └──────────────┘
```

---

## 6. Design-Prinzipien

### 6.1 Vault = Truth

```
❌ FALSCH                          ✅ RICHTIG
──────────────────────────────────────────────────────────
Chat: "Das Meeting war um 10"     WORKLOG.md:
Agent: "OK, gemerkt"               - 10:00 Meeting (PROJ-123)
[Session endet → Wissen weg]      [Persistiert, versioniert]
```

### 6.2 Append-Only für Logs

```
WORKLOG.md
──────────────────────────────────
## 2026-02-09 (Montag)

- 09:00 Standup (INT-001)          ← Nur anhängen
- 10:30 API Review (PROJ-123)      ← Nie ändern
- 14:00 Dokumentation (PROJ-123)   ← Nie löschen

## 2026-02-08 (Sonntag)            ← Historie bleibt
...
```

**Warum?**
- Git-History bleibt sauber
- Keine versehentlichen Datenverluste
- Zeitachse ist immer nachvollziehbar

### 6.3 Agent schlägt vor, Mensch entscheidet

```
┌─────────────────────────────────────────────────────────────────┐
│                         AGENT DARF                              │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Dokumentation vorbereiten                                   │
│  ✅ Zeiteinträge vorschlagen                                    │
│  ✅ Analysen durchführen                                        │
│  ✅ Optionen aufzeigen                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       AGENT DARF NICHT                          │
├─────────────────────────────────────────────────────────────────┤
│  ❌ Finale Entscheidungen treffen                               │
│  ❌ Bestehende Notes überschreiben                              │
│  ❌ Externe API-Calls ohne Bestätigung                          │
│  ❌ Deployments/Side-Effects auslösen                           │
└─────────────────────────────────────────────────────────────────┘
```

### 6.4 Tool-Entwicklung

```
┌─────────────────────────────────────────────────────────────────┐
│                     TOOL DEVELOPMENT WORKFLOW                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Skill als CLI-Skript entwickeln                             │
│     $ python skills/mein_skill.py --help                        │
│     $ python skills/mein_skill.py --input foo                   │
│                                                                 │
│  2. Skill testen (ohne MCP)                                     │
│     $ pytest skills/test_mein_skill.py                          │
│                                                                 │
│  3. MCP-Adapter schreiben (optional)                            │
│     tools/kategorie/mein_skill.py                               │
│     → Ruft skills/mein_skill.py per subprocess auf              │
│                                                                 │
│  4. MCP-Tool testen                                             │
│     $ pytest tools/tests/test_mein_skill.py                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Konventionen

### 7.1 Datei-Benennung

```
TYP                         KONVENTION              BEISPIEL
────────────────────────────────────────────────────────────────
Markdown (Vault)            UPPER_CASE.md           WORKLOG.md
Markdown (Doku)             kebab-case.md           close-day-workflow.md
Python (Skills)             snake_case.py           list_skills.py
Python (Tools)              snake_case.py           push_repos.py
Ordner                      kebab-case/             plattform-engineering/
ADR                         NNN-titel.md            001-vault-struktur.md
```

### 7.2 Vault-Struktur

```
nova-knowledge/
├── CURRENT.md          # Aktueller Fokus (Editierbar)
├── WORKLOG.md          # Arbeitslog (Append-only)
├── TICKETS.md          # Budgets (Editierbar)
│
├── kunden/
│   └── [kunde]/
│       ├── README.md       # Übersicht
│       └── knowledge/      # Kundenwissen
│           └── *.md
│
├── kompetenz/
│   └── [thema]/
│       └── knowledge/
│           └── *.md
│
└── weekly/
    └── [YYYY-WNN].md       # Wochenberichte
```

### 7.3 WORKLOG Format

```markdown
## YYYY-MM-DD (Wochentag)

- HH:MM Aktivität (TICKET-ID)
- HH:MM Aktivität ohne Ticket
- HH:MM Kurzer Kommentar ✅
```

### 7.4 Tool-Naming

```
nova_[kategorie]_[aktion]

Beispiele:
  nova_git_push_repos
  nova_worklog_append
  nova_skills_list
```

### 7.5 Commit Messages

```
[Bereich] Kurzbeschreibung

Bereiche:
  core      - CORE.md, Grundregeln
  skill     - Skills unter skills/
  tool      - MCP Tools
  playbook  - Playbooks
  doc       - Dokumentation
  meta      - Architektur, ADRs

Beispiele:
  [skill] Add summarize_day skill
  [tool] Fix worklog append timestamp
  [doc] Update ARCHITECTURE.md
```

---

## 8. Erweiterung

### 8.1 Neuen Skill hinzufügen

```bash
# 1. Skill erstellen
touch nova-core/skills/mein_skill.py

# 2. Implementieren
cat > nova-core/skills/mein_skill.py << 'EOF'
#!/usr/bin/env python3
"""
Skill: Mein Skill
Beschreibung was es tut.

Usage:
    python mein_skill.py [--option VALUE]
"""

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--option", help="Eine Option")
    args = parser.parse_args()
    
    # Logik hier
    print(f"Result: {args.option}")

if __name__ == "__main__":
    main()
EOF

# 3. Testen
python nova-core/skills/mein_skill.py --option test
```

### 8.2 Neues MCP-Tool hinzufügen

```bash
# 1. Tool-Ordner erstellen
mkdir -p nova-core/mcp/tools/meine_kategorie

# 2. Tool implementieren
cat > nova-core/mcp/tools/meine_kategorie/mein_tool.py << 'EOF'
from pathlib import Path
from mcp.types import Tool, TextContent

def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_meine_kategorie_mein_tool",
        description="Was das Tool tut",
        inputSchema={
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "Ein Parameter"}
            },
            "required": ["param"]
        }
    )

async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    result = f"Executed with {args['param']}"
    return [TextContent(type="text", text=result)]
EOF

# 3. In server.py registrieren
# TOOLS dict erweitern

# 4. Tests schreiben (PFLICHT!)
cat > nova-core/mcp/tools/tests/test_mein_tool.py << 'EOF'
import pytest
from pathlib import Path
from tools.meine_kategorie.mein_tool import get_tool_definition, execute

def test_returns_tool():
    tool = get_tool_definition(Path("/tmp"))
    assert tool.name == "nova_meine_kategorie_mein_tool"

@pytest.mark.asyncio
async def test_execute():
    result = await execute({"param": "test"}, Path("/tmp"))
    assert "test" in result[0].text
EOF
```

### 8.3 Neues Playbook hinzufügen

```bash
# Playbook erstellen
cat > nova-core/playbooks/mein_playbook.md << 'EOF'
# Playbook: Mein Playbook

> Kurzbeschreibung

---

## Trigger

- "mein befehl"
- Wenn X passiert

## Voraussetzungen

- Datei Y muss existieren

## Schritte

1. Schritt eins
2. Schritt zwei
3. Schritt drei

## Output

- Was produziert wird

## Beispiel

\`\`\`
[Beispiel-Output]
\`\`\`
EOF
```

---

## 9. Sicherheit

### 9.1 Zugriffskontrolle

```
┌─────────────────────────────────────────────────────────────────┐
│  FILESYSTEM-SCOPE                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ERLAUBT (Schreiben)                                            │
│  ├─ nova-knowledge/WORKLOG.md      (append-only)                │
│  ├─ nova-knowledge/CURRENT.md      (editierbar)                 │
│  ├─ nova-knowledge/TICKETS.md      (editierbar)                 │
│  └─ nova-knowledge/**/knowledge/   (neue Dateien)               │
│                                                                 │
│  VERBOTEN (Schreiben)                                           │
│  ├─ nova-core/**                   (Code ändern)                │
│  ├─ Bestehende Knowledge Notes     (überschreiben)              │
│  └─ Alles außerhalb Vault          (Filesystem)                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Ingestion Security (Phase 2)

```
INPUT VALIDATION
────────────────────────────────────────────────────────────
1. Allowlist           Nur bekannte User-IDs
2. Deduplication       SHA256-Hash, 24h Window
3. Content Type        Nur text/plain, text/url
4. URL Validation      Keine internen IPs (SSRF)
5. Size Limits         Max 5MB fetch, 50k chars
6. Rate Limiting       10/min, 100/hour per user
```

---

## 10. Roadmap-Architektur

### Phase 1: Copilot (CURRENT)

```
✅ MCP Server funktioniert
✅ Skills als CLI-Skripte
✅ Vault-Struktur etabliert
✅ WORKLOG Append-only
```

### Phase 2: Multi-Interface

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│     │ Copilot  │    │   CLI    │    │ Telegram │              │
│     └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│          │               │               │                     │
│          └───────────────┼───────────────┘                     │
│                          ▼                                      │
│                   ┌─────────────┐                              │
│                   │  NOVA CORE  │                              │
│                   │   Skills    │                              │
│                   └──────┬──────┘                              │
│                          ▼                                      │
│                   ┌─────────────┐                              │
│                   │    VAULT    │                              │
│                   └─────────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Neue Komponenten:**
- CLI für Cron Jobs / Automation
- Messenger Gateway für asynchrone Ingestion
- LLM-Provider Abstraktion (Azure OpenAI, OpenAI, Anthropic)

### Phase 3: Platform

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│     ┌──────────────────────────────────────────────────┐       │
│     │                   WEB UI                          │       │
│     │  ┌──────────┐ ┌──────────┐ ┌──────────┐         │       │
│     │  │Dashboard │ │ Review   │ │ Search   │         │       │
│     │  └──────────┘ └──────────┘ └──────────┘         │       │
│     └─────────────────────┬────────────────────────────┘       │
│                           │                                     │
│                           ▼                                     │
│                    ┌─────────────┐                             │
│                    │  REST API   │                             │
│                    └──────┬──────┘                             │
│                           │                                     │
│                           ▼                                     │
│   ┌───────────────────────────────────────────────────────┐    │
│   │                    NOVA CORE                          │    │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │    │
│   │  │ Agent 1 │ │ Agent 2 │ │ Agent 3 │ │ Agent N │    │    │
│   │  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │    │
│   └───────────────────────────────────────────────────────┘    │
│                           │                                     │
│                           ▼                                     │
│                    ┌─────────────┐                             │
│                    │    VAULT    │                             │
│                    └─────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Neue Komponenten:**
- REST API für programmatischen Zugriff
- Web UI für Dashboard und Reviews
- Multi-Agent Orchestrierung
- Gap Detection (Was fehlt im Knowledge?)

---

## Quick Reference

### Wo finde ich was?

| Frage | Antwort |
|-------|---------|
| Was soll der Agent tun? | `nova-core/core/CORE.md` |
| Wie funktioniert close_day? | `nova-core/playbooks/close_day.md` |
| Welche Skills gibt es? | `nova-core/skills/` |
| Welche MCP-Tools? | `nova-core/mcp/tools/` |
| Wie erweitere ich? | Dieses Dokument, Abschnitt 8 |
| Warum diese Entscheidung? | `nova-core/meta/decisions/` |
| Was wurde geändert? | `nova-core/meta/CHANGELOG.md` |

### Wichtigste Befehle

```bash
# Skills auflisten
python nova-core/skills/list_skills.py

# Tests ausführen
cd nova-core/mcp && pytest tools/tests/

# MCP Server manuell starten (Debug)
python nova-core/mcp/server.py
```

---

*Letzte Aktualisierung: 2026-02-09*
