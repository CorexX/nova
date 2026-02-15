<div align="center">

# N O V A

### **N**otes-based **O**rchestrated **V**irtual **A**ssistant

[![Local-First](https://img.shields.io/badge/Local--First-Knowledge-22c55e?style=for-the-badge)](.)
[![Agent Ready](https://img.shields.io/badge/Stateless-Agent_Ready-f97316?style=for-the-badge)](.)
[![MCP Native](https://img.shields.io/badge/MCP-Native-8b5cf6?style=for-the-badge)](.)
[![Token Efficient](https://img.shields.io/badge/Token-Efficient-ec4899?style=for-the-badge)](.)

*Persistenter Kontext fuer stateless Agenten.*  
*Weniger Prompt-Last, schnellere Ergebnisse.*

</div>

## Projektvision

Moderne Agenten sind stark, aber zustandslos. Kontext geht verloren, Entscheidungen bleiben fluechtig.
NOVA baut deshalb ein persistentes, kontrolliertes Arbeitsgedaechtnis fuer reale Agentenarbeit.

**NOVA ist kein Chat-Interface. NOVA ist eine Arbeitsumgebung fuer Agenten.**

### Ein-Satz-Vision

NOVA ist ein persistentes, agentenfaehiges Kontext- und Arbeitssystem, das selektive Kontextbereitstellung mit strukturierter Wissensverankerung verbindet.

### Arbeitszyklus (Kern von NOVA)

```
Init -> Intent -> Context -> Action -> Persist -> Review
```

| Schritt | Ziel |
|---------|------|
| `Init` | Session und Basis-Kontext starten |
| `Intent` | Nutzerabsicht einordnen (z. B. weiterarbeiten, neues Projekt, Frage, Workflow-Run) |
| `Context` | Relevante Informationen selektiv laden |
| `Action` | Agent arbeitet aktiv an Dateien, Code, Runbooks, Repos |
| `Persist` | Erkenntnisse strukturiert zurueck in die Wissensbasis schreiben |
| `Review` | Ergebnis und naechste Schritte transparent machen |

### Produktprinzipien

| Prinzip | Aussage |
|---------|---------|
| Persistenz vor Antwort | Relevante Arbeit erzeugt Wissen im System |
| Append statt Overwrite | Historie bleibt nachvollziehbar |
| Struktur-agnostisch, semantisch auswertbar | Keine starre Dokumentpflicht, aber nutzbare Metadaten und Relationen |
| Kontext vor Aktion | Kein Handeln ohne aufgeloesten Arbeitskontext |
| Transparenz | Quelle, Auswahlgrund und Sicherheitsgrad werden sichtbar |

### Was NOVA explizit nicht ist

- Kein generischer Chatbot
- Kein Kalender- oder Task-Assistent
- Keine reine RAG-Engine
- Keine starre Wissensplattform

## Was NOVA ist

NOVA erweitert die Zusammenarbeit mit stateless Agenten (z. B. Copilot oder Codex) um eine fehlende Schicht:  
**Kontext, der bleibt, waechst und wiederverwendbar ist.**
Context-Orchestrierungs-Layer für Agenten.

```
  Ohne:   Session --> Recherche --> vergessen
                      Session --> Recherche --> vergessen
                                  Session --> Recherche --> vergessen

  Mit:    Session ----+
                      |---> Knowledge Base ---> alle Sessions nutzen es
          Session ----+
```

## Kernnutzen

| Kontext mitnehmen | Verbindungen sichtbar | Strukturiert ablegen | Token sparen |
|:------------------:|:---------------------:|:--------------------:|:------------:|
| Arbeitskontext fuer Projekte dauerhaft speichern | Wissen ueber Sessions verknuepfen | Rohe Informationen in auffindbare Eintraege ueberfuehren | Direkte Arbeit statt wiederholt suchen |

## Warum das Token spart

```
  Ohne:   Prompt --> sammle Kontext --> recherchiere --> Antwort
                          (tokens)          (tokens)

  Mit:    Prompt --> MCP Tool --> Antwort
                      (1 call)
```

| Ebene | Mechanismus | Effekt |
|:-----:|-------------|--------|
| **1** | Retrieval statt Prompt-Ballast | `nova_search_vault` liefert relevante Inhalte + Dateipfade |
| **2** | Programmatische Wiederverwendung | MCP-Tools erledigen repetitive Aufgaben automatisch |
| **3** | Gezielter Kontext | Agent bekommt passenden Ausschnitt, nicht alles |

## search_vault

`nova_search_vault` liefert semantisch passende Kontexteintraege aus der Knowledge-Base inklusive Dateipfade.

```
  Query --> Embeddings --> Match --> Docs + Paths
```

## Use Cases

| Use Case | Input | Output |
|----------|-------|--------|
| **Quelle → Wissen** | Artikel-Link | Strukturierter Eintrag |
| **Video → Projekt** | Video-Content | Projektbezogene Insights |
| **Doku → Notes** | PDF/Docs | Kernaussagen + offene Fragen |
| **Meeting → Tasks** | Rohnotizen | Entscheidungen + Dokumentation |
| **Code → Wissen** | Repository | Architektur-Dokumentation |
| **Kontinuierliche Pflege** | Neue Quellen | Konsistentes, erweitertes Wissen |

## Architektur

Klare Trennung von Framework und Wissen:

```
                    Agent (Copilot/Codex)
                            |
                       MCP Protocol
                            |
              nova-core <-------> nova-knowledge
              (portable)          (private)
```

**Startoptionen:** Neu starten (Template-Struktur) oder bestehende Wissensdatenbank anbinden.

## Betriebsprinzipien

```
  Start --> Init --> Intent --> Kontext --> Aktion --> Persistenz --> Review
                                                        |             |
                                                        +--> Worklog  +--> Naechster Schritt
```

| Prinzip | Regel |
|---------|-------|
| Session Start | Immer mit `nova_context_resolve(query="session init")` beginnen |
| Persistieren | Ergebnisse in Vault speichern, nicht nur im Chat |
| Append | Bestehende Notes erweitern, nicht ueberschreiben |
| Kontextoekonomie | Kontext gezielt laden, budgetieren, deduplizieren, priorisieren |
| Modular | Core lauffaehig ohne optionale Integrationen |

<details>
<summary>Mehr Details</summary>

- `core/CORE.md` - Hauptidentitaet
- `core/PRINCIPLES.md` - Detaillierte Prinzipien
- `CONTRACTS.md` - API-Vertraege

</details>

## Quick Start

```bash
# 1) Repo klonen
git clone https://github.com/dein-user/nova-core.git
cd nova-core

# 2) Setup starten
python setup.py

# 3) VS Code neu laden

# 4) Neue Session starten
nova_context_resolve
```

**Express Setup:** `python setup.py --quick` (nutzt Defaults)

**Setup erstellt:**

| Datei | Beschreibung |
|-------|-------------|
| `nova.toml` | Konfiguration |
| `.vscode/mcp.json` | MCP-Server Config |
| `.venv` | Virtual Environment |
| `nova-knowledge/` | Grundstruktur (optional) |

## Voraussetzungen

| Requirement | Version |
|-------------|-------|
| Python | `3.11+` |
| VS Code | Latest |
| Copilot/Codex | oder MCP-faehiger Client |

## Konfiguration

<details>
<summary><b>Standard Setup</b> - Im Normalfall reicht <code>setup.py</code></summary>

Fuer Spezialfaelle via Environment:

```env
NOVA_CORE_ROOT=/abs/path/to/nova-core
NOVA_KNOWLEDGE_ROOT=/abs/path/to/nova-knowledge
NOVA_INDEX_ROOT=/abs/path/to/index-storage
```

</details>

<details>
<summary><b>Optional: n8n Integration</b></summary>

```env
N8N_BASE_URL=https://n8n.home
N8N_API_KEY=your-n8n-api-key
N8N_INSECURE_TLS=false
```

> Ohne n8n bleibt NOVA voll funktionsfaehig; nur `nova_n8n_*` sind deaktiviert.

</details>

## MCP in VS Code

```json
{
  "servers": {
    "nova-skills": {
      "type": "stdio",
      "command": "python",
      "args": ["${workspaceFolder}/nova-core/launcher.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

**Connection:** VS Code <-> stdio <-> launcher.py -> MCP Server -> 27 Tools

## Quality Gate

```bash
python -m pytest mcp/tools/tests -q
```

## Struktur

```
nova-core/                      nova-knowledge/
├── core/                       ├── CURRENT.md
│   ├── CORE.md                 ├── TICKETS.md
│   └── PRINCIPLES.md           ├── WORKLOG.md
├── mcp/                        ├── inbox/
│   ├── nova_mcp_core_server.py ├── areas/
│   └── tools/                  ├── projects/
├── playbooks/                  ├── resources/
├── playbooks/                  └── operations/
├── templates/
├── setup.py
└── launcher.py
```

## Weiterfuehrend

| Dokument | Inhalt |
|----------|--------|
| [CORE.md](core/CORE.md) | Hauptidentitaet & Regeln |
| [PRINCIPLES.md](core/PRINCIPLES.md) | Detaillierte Prinzipien |
| [CONTRACTS.md](CONTRACTS.md) | API-Vertraege |
| [ARCHITECTURE.md](meta/ARCHITECTURE.md) | Systemarchitektur |
| [ROADMAP.md](meta/ROADMAP.md) | Entwicklungsplan |

<div align="center">

*Built with persistence in mind.*

**[Documentation](meta/ARCHITECTURE.md)** · **[Roadmap](meta/ROADMAP.md)** · **[Changelog](meta/CHANGELOG.md)**

</div>
