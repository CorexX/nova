# NOVA MCP Server

> Model Context Protocol Server für GitHub Copilot Integration.

---

## Übersicht

Der MCP Server exposed NOVA Core Tools fuer GitHub Copilot. Diese erscheinen als `mcp_nova-skills_*` Tools im Chat.

## Contracts

Verbindliche Modulgrenzen, Pfad-/Env-Contracts und der Betriebs-Impact auf NOVA stehen in `../CONTRACTS.md`.

---

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Copilot                                             │
│  └─ mcp_nova-skills_*                                       │
└────────────────────┬────────────────────────────────────────┘
                     │ MCP Protocol
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  mcp/nova_mcp_core_server.py                                │
│  └─ tools/*.py (Adapter)                                    │
└────────────────────┬────────────────────────────────────────┘
                     │ subprocess / asyncio
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  nova-core/skills/*.py                                      │
│  (Eigenständige CLI-Skripte)                                │
└─────────────────────────────────────────────────────────────┘
```

### Prinzip: Skills als eigenständige Skripte

**Skills sind eigenständige CLI-Skripte** unter `nova-core/skills/`. Sie können:
- Direkt per Terminal aufgerufen werden
- Von MCP-Tools als Wrapper referenziert werden
- Unabhängig vom MCP-Server getestet werden

**MCP-Tools sind Adapter** die:
- Entweder Skill-Skripte integrieren oder Logik direkt in `mcp/tools/*` kapseln
- Argumente übersetzen (MCP-Schema → CLI-Argumente)
- Output zurückgeben

### Warum diese Trennung?

1. **Wiederverwendbarkeit**: Skills funktionieren auch ohne VS Code/Copilot
2. **Testbarkeit**: CLI-Skripte sind einfacher zu testen
3. **Debugging**: Fehler im Skill können isoliert debuggt werden
4. **Flexibilität**: Neue Frontends (CLI, Web, etc.) können Skills nutzen

---

## Struktur

```
nova-core/
├── skills/                 # ← Eigenständige CLI-Skripte
│   ├── summarize_day.py    # Tages-Session-Zusammenfassung
│   ├── summarize_week.py   # Wochen-Session-Zusammenfassung
│   ├── get_architecture.py
│   └── list_skills.py
└── mcp/
    ├── nova_mcp_core_server.py  # Hauptserver
    ├── README.md           # Diese Datei
    └── tools/              # MCP-Adapter (direkt + Skill-Integration)
        ├── utils/          # Shared Utilities
        │   └── subprocess_utils.py  # Timeout-sicherer Subprocess-Wrapper
        ├── tests/          # Tool-Tests (PFLICHT, Stand 2026-02-13: 304 passed, 5 skipped)
        │   ├── conftest.py
        │   └── test_*.py   # 24 Test-Module
        ├── context/        # Context-Loading Tools
        │   ├── session_init.py
        │   └── get_*.py    # 11 Getter-Tools
        ├── git/            # Git-bezogene Tools
        │   └── push_repos.py
        ├── health/         # System-Status
        │   └── health_check.py
        ├── search/         # Semantische Suche
        │   ├── search_vault.py
        │   └── index_vault.py
        ├── sessions/       # Session-Tools
        │   ├── summarize_day.py
        │   └── summarize_week.py
        ├── system/         # Prozess-/Runtime-Tools
        │   └── 
        ├── testing/        # Test-Runner
        │   └── run_tests.py
        └── worklog/        # Worklog-Tools
            └── append.py
```

---

## Verfuegbare Tools (Auszug)

| Tool | Kategorie | Beschreibung |
|------|-----------|--------------|
| `nova_context_resolve` | v2 | Selektive Kontextauflösung (PFLICHT am Start) |
| `nova_project_continue` | v2 | Projekt fortsetzen (3-Schritt-Plan) |
| `nova_project_create` | v2 | Projekt strukturiert anlegen |
| `nova_knowledge_query` | v2 | Semantische Wissensabfrage |
| `nova_knowledge_update` | v2 | Erkenntnis persistieren (append-first) |
| `nova_system_maintain` | v2 | System warten (health, index, test, restart) |
| `nova_health_check` | health | Detaillierter System-Status Report |
| `nova_git_push_repos` | git | Pushed alle Git-Repos im Workspace (derzeit defekt) |
| `nova_worklog_append` | worklog | Fügt Eintrag zum WORKLOG.md hinzu |
| `nova_run_tests` | testing | Führt pytest für Tool-Tests aus |
| `nova_search_vault` | search | Semantische Suche in der Vault |
| `nova_index_vault` | search | Indexiert die Vault für Suche |
| `nova_get_agent_skills` | context | Listet Agent-Skill-Spezifikationen vs Legacy-Skripte |
| `nova_summarize_day` | sessions | Fasst Copilot Sessions eines Tages zusammen |
| `nova_summarize_week` | sessions | Fasst Copilot Sessions einer Woche zusammen |
| `nova_n8n_list_workflows` | n8n | Listet Workflows via n8n API |
| `nova_n8n_get_workflow` | n8n | Holt Workflow-Details via n8n API |
| `nova_n8n_create_workflow` | n8n | Erstellt einen Workflow via n8n API |
| `nova_n8n_update_workflow` | n8n | Aktualisiert einen Workflow via n8n API |
| `nova_n8n_delete_workflow` | n8n | Loescht einen Workflow via n8n API |
| `nova_n8n_api_request` | n8n | Generischer API-Request (GET/POST/PUT/PATCH/DELETE) auf beliebige n8n Endpoints |
| `nova_restart_server` | system | Plant einen MCP-Server-Restart (self-terminate mit Delay) |

Hinweis: n8n ist optional. Ohne `N8N_BASE_URL` + `N8N_API_KEY` bleibt der Core funktionsfaehig; nur `nova_n8n_*` melden "optional feature not configured".

### `nova_n8n_api_request` (Wildcard n8n API)

Generischer Zugriff auf beliebige n8n API-Endpunkte mit `GET/POST/PUT/PATCH/DELETE`.

Input-Parameter:
- `method` (required): `GET | POST | PUT | PATCH | DELETE`
- `path` (required): Endpoint-Pfad, z. B. `/api/v1/workflows`
- `payload` (optional): JSON-Objekt fuer `POST/PUT/PATCH`
- `base_url` (optional): n8n Base URL (fallback: `N8N_BASE_URL`)
- `api_key` (optional): n8n API Key (fallback: `N8N_API_KEY`)
- `insecure_tls` (optional): TLS-Verify deaktivieren
- `compact` (optional, default `true`): reduziert GET-Ausgaben auf kontextrelevante Felder; mit `false` kommt die volle Raw-Antwort

Wichtige Guardrails:
- `path` muss ein Pfad sein, keine volle URL
- `GET` mit `payload` wird abgelehnt
- `payload` muss ein JSON-Objekt sein

Beispiele:

```json
{
  "method": "GET",
  "path": "/api/v1/workflows?limit=10"
}
```

```json
{
  "method": "POST",
  "path": "/api/v1/workflows",
  "payload": {
    "name": "Demo Workflow",
    "nodes": [],
    "connections": {}
  }
}
```

```json
{
  "method": "PATCH",
  "path": "/api/v1/workflows/<workflow_id>",
  "payload": {
    "name": "Renamed Workflow"
  }
}
```

### Health Check

Der `nova_health_check` zeigt den Status aller NOVA-Subsysteme in 5 Gruppen:

```
✅ **CORE:** MCP Tools 27 Tools │ Python 3.13 │ Core Files 3 │ Dependencies 3 OK
✅ **VAULT:** Kunden 9 │ Kompetenz 2 │ WORKLOG ✓ │ TICKETS ✓
✅ **SEARCH:** Embedding Model Cached │ Vault Index 67 Dateien
✅ **CONTENT:** Playbooks 1 │ Guides 3 │ Skills 4 │ Templates 2
✅ **TODAY:** Worklog Heute: 0 Einträge │ CURRENT 1d alt
```

| Gruppe | Prüft |
|--------|-------|
| CORE | MCP Tools, Python Version, Core Files, Dependencies |
| VAULT | Kunden, Kompetenz, WORKLOG.md, TICKETS.md |
| SEARCH | Embedding Model Cache, Vault Index |
| CONTENT | Playbooks, Guides, Skills, Templates |
| TODAY | Heutige Worklog-Einträge, CURRENT.md Aktualität |

> **⚠️ Hinweis:** VS Code löscht Chat-Sessions automatisch. Für `summarize_day/week` müssen Sessions noch vorhanden sein. Siehe [close-day-workflow.md](../playbooks/close-day-workflow.md#vs-code-session-retention).

---

## Installation

### 1. Requirements installieren

```bash
cd nova-core
pip install -r requirements.txt
```

Die `requirements.txt` enthält Runtime-Dependencies sowie Test-Dependencies
(`pytest`, `pytest-asyncio`).

Optionale Pfad-ENV-Variablen (fuer entkoppelte Setups):

```env
NOVA_CORE_ROOT=/abs/path/to/nova-core
NOVA_KNOWLEDGE_ROOT=/abs/path/to/nova-knowledge
NOVA_INDEX_ROOT=/abs/path/to/index-storage
```

### 2. VS Code Konfiguration

Die MCP-Konfiguration liegt in `.vscode/mcp.json`:

```json
{
  "servers": {
    "nova-skills": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/launcher.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

Hinweis: Im embedded Layout kann der `args`-Pfad auch `${workspaceFolder}/nova-core/launcher.py` sein.

### 3. VS Code neu laden

`Ctrl+Shift+P` → "Reload Window"

---

## Embedding Model (Startup)

Der Server lädt beim Start das **SentenceTransformer Model** `all-MiniLM-L6-v2` für `nova_search_vault`. Das dauert **~30-35 Sekunden** (einmalig pro Session).

Nach dem Laden ist `nova_search_vault` **instant** (<100ms).

> **Details:** Warum so langsam? Workarounds? → siehe `nova-knowledge/projekte/nova/knowledge/mcp-server.md`

---

## Tools Hinzufügen

### 1. Tool-Modul erstellen

Neuen Ordner unter `tools/` anlegen:

```
tools/
└── meine_kategorie/
    ├── __init__.py
    └── mein_tool.py
```

### 2. Tool-Struktur

Jedes Tool-Modul muss zwei Funktionen haben:

```python
from pathlib import Path
from mcp.types import Tool, TextContent


def get_tool_definition(workspace_root: Path) -> Tool:
    """Gibt die Tool-Definition zurück."""
    return Tool(
        name="nova_mein_tool",
        description="Beschreibung des Tools",
        inputSchema={
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Beschreibung"
                }
            },
            "required": ["param1"]
        }
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    """Führt das Tool aus."""
    # Implementierung
    return [TextContent(type="text", text="Ergebnis")]
```

### 3. Tests schreiben

**Jedes Tool MUSS Tests haben.** Tests liegen unter `tools/tests/`:

```
tools/tests/
├── conftest.py
├── test_worklog_append.py
├── test_git_push_repos.py
└── test_skills_list_skills.py
```

Mindestens folgende Tests sind erforderlich:

```python
# tests/test_mein_tool.py
import pytest
from pathlib import Path
from mcp.types import Tool, TextContent
from tools.meine_kategorie.mein_tool import get_tool_definition, execute


class TestToolDefinition:
    """Tests für die Tool-Definition."""
    
    def test_returns_tool_instance(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)
    
    def test_has_correct_name(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert tool.name == "nova_mein_tool"
    
    def test_has_description(self, tmp_path: Path):
        tool = get_tool_definition(tmp_path)
        assert tool.description


class TestExecute:
    """Tests für die Tool-Ausführung."""
    
    @pytest.mark.asyncio
    async def test_returns_text_content(self, tmp_path: Path):
        result = await execute({}, tmp_path)
        assert isinstance(result[0], TextContent)
```

### 4. In Server registrieren

In `nova_mcp_core_server.py` importieren und zu `TOOLS` hinzufuegen:

```python
from tools.meine_kategorie import mein_tool

TOOLS = {
    # ... existing tools ...
    "nova_mein_tool": mein_tool,
}
```

---

## Testen

### Test-Übersicht

Alle MCP-Tools haben vollständige Tests. Stand: Februar 2026.

| Test-Datei | Tool | Tests |
|------------|------|-------|
| `test_context_get_current.py` | `nova_get_current` | 8 |
| `test_context_get_tickets.py` | `nova_get_tickets` | 7 |
| `test_context_get_rules.py` | `nova_get_rules` | 8 |
| `test_context_get_scope.py` | `nova_get_scope` | 8 |
| `test_context_get_conventions.py` | `nova_get_conventions` | 8 |
| `test_context_get_collections.py` | `nova_get_collections` | 5 |
| `test_context_get_paths.py` | `nova_get_paths` | 3 |
| `test_context_get_structure.py` | `nova_get_structure` | 11 |
| `test_context_get_templates.py` | `nova_get_templates` | 10 |
| `test_context_get_guides.py` | `nova_get_guides` | 10 |
| `test_context_get_playbooks.py` | `nova_get_playbooks` | 11 |
| `test_health_check.py` | `nova_health_check` | 22 |
| `test_search_search_vault.py` | `nova_search_vault` | 18 |
| `test_search_index_vault.py` | `nova_index_vault` | 23 |
| `test_sessions_summarize_day.py` | `nova_summarize_day` | 19 |
| `test_sessions_summarize_week.py` | `nova_summarize_week` | 22 |
| `test_git_push_repos.py` | `nova_git_push_repos` | 13 |
| `test_testing_run_tests.py` | `nova_run_tests` | 17 |
| `test_worklog_append.py` | `nova_worklog_append` | 9 |
| `test_architecture_get_architecture.py` | `nova_get_architecture` | 10 |
| `test_n8n_tools.py` | `nova_n8n_*` | 33 |

**Gesamt (2026-02-13): 304 passed, 5 skipped (`python -m pytest mcp/tools/tests -q`)**

### Tests ausführen

```bash
cd nova-core/mcp
python -m pytest tools/tests/ -v
```

Hinweis: Der erste Lauf kann deutlich länger dauern (Dependency-Importe,
Modell-Download und Initialisierung).

### Schneller Lauf (ohne verbose)

```bash
python -m pytest tools/tests/ -q
```

### Einzelnes Tool testen

```bash
python -m pytest tools/tests/test_search_search_vault.py -v
```

### Mit Coverage

```bash
pytest tools/tests/ -v --cov=tools --cov-report=term-missing
```

### Test-Kategorien

Tests folgen einem einheitlichen Muster:

1. **TestToolDefinition**: Prüft `get_tool_definition()`
   - Gibt Tool-Instanz zurück
   - Hat korrekten Namen (`nova_*`)
   - Hat Beschreibung
   - Schema stimmt

2. **TestExecute**: Prüft `execute()`
   - Gibt `list[TextContent]` zurück
   - Behandelt Fehler graceful
   - Mockt externe Dependencies (Subprocess, ChromaDB, etc.)

---

## Lokales Testen (Server)

```bash
# Syntax prüfen
python -m py_compile nova-core/mcp/nova_mcp_core_server.py

# Import testen
cd nova-core/mcp
python -c "from nova_mcp_core_server import TOOLS; print(list(TOOLS.keys()))"
```

---

## Tool-Kategorien

| Kategorie | Beschreibung | Beispiele |
|-----------|--------------|-----------|
| `context/` | Session- und Kontextzugriff | session_init, get_rules, get_paths |
| `search/` | Lokale semantische Suche | index_vault, search_vault |
| `sessions/` | Session-Auswertung | summarize_day, summarize_week |
| `health/` | Systemdiagnostik | health_check |
| `git/` | Git-Operationen | push_repos |
| `worklog/` | Worklog-Schreiben | append |
| `testing/` | Tool-Testausfuehrung | run_tests |
| `architecture/` | Architektur-Referenz | get_architecture |
| `n8n/` | Optionale Workflow-API | list/get/create/update/delete + generic api_request |

---

## Troubleshooting

### Server startet nicht

1. Python-Pfad prüfen: `which python` / `where python`
2. MCP installiert? `pip show mcp`
3. Logs: VS Code Output → "MCP"

### Tools erscheinen nicht

1. VS Code neu laden
2. `.vscode/mcp.json` prüfen
3. Server-Import testen (siehe oben)

> **Mehr Troubleshooting:** → `nova-knowledge/projekte/nova/knowledge/mcp-server.md`

---

## ⚠️ Bekannte Fallstricke

### Subprocess Timeout

Tools mit externen Prozessen **müssen** `tools/utils/subprocess_utils.py` mit Timeout nutzen.

### `ModuleNotFoundError: No module named 'mcp.types'`

Der Ordner `nova-core/mcp/` darf **KEIN** `__init__.py` haben!

```
nova-core/mcp/
├── nova_mcp_core_server.py  ✅
├── tools/           ✅
└── __init__.py      ❌ VERBOTEN!
```

---

*Siehe auch: `README.md` (Root), `meta/ARCHITECTURE.md`, `CONTRACTS.md`*


