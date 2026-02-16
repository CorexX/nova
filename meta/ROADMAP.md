# ROADMAP

> Geplante Features, Architektur-Vision und Integrationen fÃ¼r NOVA.

---

## Top-Fokus 2026-02: MCP Rebuild (Direct Tools)

Ziel: MCP-Tooling direkt auf 6 Kern-Tools neu aufbauen, ohne Legacy/Fascade-Schicht.

Leitlinie:
1. Ein Tool = ein klarer Kernauftrag
2. Vertrage zuerst festlegen, dann Implementierung
3. Persistenz und Kontextaufloesung sind Pflicht, nicht optional

### Toolset v2 (Source of Truth)

1. `nova_context_resolve`
- Zweck: Relevanten Arbeitskontext selektiv aufloesen (priorisieren, budgetieren, deduplizieren, Quellen offenlegen).
- Input (minimum): `query`, optional `project_hint`, `token_budget`, `scope`.
- Output (minimum): `context_items[]`, `sources[]`, `confidence`, `selection_reason`.
- Done: Liefert fuer freie Anfragen konsistent nutzbaren Arbeitskontext statt Volltext-Dumps.

2. `nova_project_continue`
- Zweck: Laufendes Projekt robust fortsetzen.
- Input (minimum): `project_hint`, optional `mode` (`continue`|`status`).
- Output (minimum): `project_path`, `last_steps[]`, `open_items[]`, `next_plan[]` (max 3 Schritte).
- Done: "Weiterarbeiten" funktioniert ohne manuelle Pfadsuche.

3. `nova_project_create`
- Zweck: Neues Projekt strukturiert anlegen.
- Input (minimum): `customer`, `project_name`, optional `template`, `initial_context`.
- Output (minimum): `created_paths[]`, `bootstrap_files[]`, `next_actions[]`.
- Done: Neues Projekt ist in einem Call arbeitsfaehig angelegt.

4. `nova_knowledge_query`
- Zweck: Wissensabfrage ueber semantische Suche plus strukturierte Rueckgabe.
- Input (minimum): `query`, optional `project`, `topic`, `limit`.
- Output (minimum): `matches[]` mit `path`, `snippet`, `score`, `why_relevant`.
- Done: Liefert praezise, nachvollziehbare Treffer fuer Arbeitsentscheidungen.

5. `nova_knowledge_update`
- Zweck: Erkenntnisse append-first persistieren.
- Input (minimum): `content`, `source`, optional `project`, `topic`, `confidence`, `next_action`.
- Output (minimum): `written_paths[]`, `entry_ids[]`, `link_updates[]`.
- Done: Relevante Arbeit wird strukturiert verankert, Historie bleibt nachvollziehbar.

6. `nova_system_maintain`
- Zweck: Systembetrieb zentral steuern (health, index, tests, restart).
- Input (minimum): `operation` (`health`|`index`|`test`|`restart`) + optionale Parameter.
- Output (minimum): `status`, `details`, `artifacts`.
- Done: Betriebsaufgaben sind mit einem Tool standardisiert und transparent.

### Umsetzungsplan (Direct Build)

1. Tool-Contracts finalisieren
- Ergebnis: JSON-Schema pro Tool (Input/Output/Fehlercodes) in Doku versioniert.
- Done wenn: Alle 6 Tools haben verbindliche Contracts.

2. Neue Tool-Module implementieren
- Ergebnis: Je Tool ein Modul unter `mcp/tools/v2/` mit Tests.
- Done wenn: Toolaufrufe funktionieren isoliert und geben stabile Strukturen zurueck.

3. Server-Registry umstellen
- Ergebnis: `mcp/nova_mcp_core_server.py` registriert nur das v2-Toolset.
- Done wenn: MCP listet genau diese 6 Kern-Tools.

4. Persistenz- und Kontextqualitaet absichern
- Ergebnis: Guardrails fuer append-only, Quellenpflicht und Confidence.
- Done wenn: Ohne Quelle/Grund keine "fertige" Antwort als Erfolg zurueckkommt.

5. Doku synchronisieren
- Ergebnis: `README.md`, `meta/ARCHITECTURE.md`, `CONTRACTS.md` auf v2 aktualisiert.
- Done wenn: Doku und Registry keinen Drift mehr haben.

---
## ï¿½ Die groÃŸe Vision: NOVA Server Mode

> **NOVA als Always-On Personal Assistant auf deinem Homeserver.**  
> Inspiriert von [OpenClaw](https://github.com/openclaw/openclaw) â€“ aber Knowledge-First statt Chat-First.

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                              HOMESERVER                                     â”‚
â”‚                                                                             â”‚
â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚   â”‚                         NOVA GATEWAY                                â”‚   â”‚
â”‚   â”‚                                                                     â”‚   â”‚
â”‚   â”‚   â€¢ Always-on Service (Docker)                                      â”‚   â”‚
â”‚   â”‚   â€¢ LLM Connection (Claude/GPT via API)                             â”‚   â”‚
â”‚   â”‚   â€¢ Knowledge Vault + Vector Store                                  â”‚   â”‚
â”‚   â”‚   â€¢ Async Task Queue                                                â”‚   â”‚
â”‚   â”‚                                                                     â”‚   â”‚
â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                               â”‚                                             â”‚
â”‚              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                            â”‚
â”‚              â–¼                â–¼                â–¼                            â”‚
â”‚         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”       â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”       â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”                        â”‚
â”‚         â”‚Telegramâ”‚       â”‚  Web   â”‚       â”‚ Matrix â”‚                        â”‚
â”‚         â”‚  Bot   â”‚       â”‚  Chat  â”‚       â”‚  Bot   â”‚                        â”‚
â”‚         â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜       â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜       â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜                        â”‚
â”‚                                                                             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                    â”‚
                                    â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                              DU (Ã¼berall)                                   â”‚
â”‚                                                                             â”‚
â”‚   ðŸ“± Telegram:     "Hey NOVA, notier: Meeting mit Kunde X verschoben"       â”‚
â”‚   ðŸ’» Web Chat:     "Was steht heute an?"                                    â”‚
â”‚   ðŸ–¥ï¸ VS Code:      [wie heute - voller Power-Modus]                         â”‚
â”‚   ðŸ“‹ CLI:          nova ask "Zusammenfassung KW7"                           â”‚
â”‚                                                                             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Phasen

| Phase | Feature | Beschreibung | Status |
|-------|---------|--------------|--------|
| 1 | **Telegram Inbox** | Quick Capture unterwegs â†’ direkt in Vault | Geplant |
| 2 | **Async Queue** | Background Tasks, Scheduled Jobs | Geplant |
| 3 | **Web Chat** | Browser Interface (self-hosted) | Geplant |
| 4 | **Proactive Agent** | Daily Briefings, Reminder, Nudges | Geplant |
| 5 | **Multi-Channel** | Matrix, Discord, Voice (Whisper) | SpÃ¤ter |

### Phase 1: Telegram Inbox Bot (MVP)

**Status:** ðŸŽ¯ NEXT UP

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   Du (unterwegs):   "Idee fÃ¼r NOVA: CLI interface"              â”‚
â”‚   NOVA:             "âœ“ Notiert."                                â”‚
â”‚                                                                  â”‚
â”‚   [SpÃ¤ter in VS Code]                                            â”‚
â”‚   nova_context_resolve() â†’ zeigt Inbox                              â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

#### MVP Scope (1 Abend, ~4h)

| Feature | Beschreibung |
|---------|--------------|
| âœ… Text â†’ INBOX.md | Jede Nachricht wird appended |
| âœ… Chat-ID Whitelist | Nur du darfst schreiben |
| âœ… BestÃ¤tigung | "âœ“ Notiert." als Reply |
| âœ… Docker | Ein Container, lÃ¤uft auf Homeserver |
| âŒ Kein LLM | Kein Verstehen, nur Capture |
| âŒ Keine Strukturierung | Phase 2 |

#### Dateien

```
nova-server/                     # NEU
â”œâ”€â”€ telegram/
â”‚   â”œâ”€â”€ bot.py                  # ~50 Zeilen Kernlogik
â”‚   â”œâ”€â”€ config.py               # BOT_TOKEN, ALLOWED_CHAT_IDS
â”‚   â””â”€â”€ Dockerfile
â”œâ”€â”€ docker-compose.yml
â””â”€â”€ README.md
```

#### Code-Skizze

```python
# bot.py
from telegram.ext import Application, MessageHandler, filters
from datetime import datetime

INBOX_PATH = "/vault/nova-knowledge/INBOX.md"
ALLOWED_IDS = [123456789]  # Deine Chat-ID

async def handle(update, context):
    if update.effective_chat.id not in ALLOWED_IDS:
        return
    
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    text = update.message.text
    
    with open(INBOX_PATH, "a") as f:
        f.write(f"\n- [{ts}] {text}")
    
    await update.message.reply_text("âœ“ Notiert.")

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, handle))
app.run_polling()
```

#### Phase 2 (spÃ¤ter)

- LLM versteht Kontext: "leg das bei Kunde A ab"
- Bilder/Dateien speichern
- Semantic Search Antworten
- Integration in `nova_session_init()` (zeigt neue Inbox-EintrÃ¤ge)

### Phase 4: Proaktiver Agent

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                                                                  â”‚
â”‚   [08:00]  NOVA â†’ Telegram:                                      â”‚
â”‚            "Guten Morgen. Heute: 3 Tickets offen.                â”‚
â”‚             Meeting 14:00 mit Kunde A. Budget bei 72%."          â”‚
â”‚                                                                  â”‚
â”‚   [12:00]  NOVA â†’ Telegram:                                      â”‚
â”‚            "Erinnerung: Terraform-PR noch offen."                â”‚
â”‚                                                                  â”‚
â”‚   [18:00]  NOVA â†’ Telegram:                                      â”‚
â”‚            "Tagesabschluss? Soll ich close day ausfÃ¼hren?"       â”‚
â”‚                                                                  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Architektur (geplant)

```
nova-server/                     # NEU
â”œâ”€â”€ gateway/
â”‚   â”œâ”€â”€ main.py                 # FastAPI Gateway
â”‚   â”œâ”€â”€ queue.py                # Task Queue (Redis/SQLite)
â”‚   â””â”€â”€ llm.py                  # LLM Connector
â”‚
â”œâ”€â”€ channels/
â”‚   â”œâ”€â”€ telegram.py             # Telegram Bot
â”‚   â”œâ”€â”€ matrix.py               # Matrix Bot
â”‚   â”œâ”€â”€ web.py                  # Web Chat API
â”‚   â””â”€â”€ cli.py                  # CLI Interface
â”‚
â”œâ”€â”€ workers/
â”‚   â”œâ”€â”€ capture.py              # Quick Capture â†’ Vault
â”‚   â”œâ”€â”€ research.py             # Background Research
â”‚   â””â”€â”€ scheduled.py            # Cron Jobs
â”‚
â”œâ”€â”€ docker-compose.yml
â””â”€â”€ Dockerfile
```

### Unterschied zu OpenClaw

| Aspekt | OpenClaw | NOVA |
|--------|----------|------|
| Fokus | Chat-First | Knowledge-First |
| Persistence | Sessions | Git Vault |
| Persona | SOUL.md | CORE.md |
| Skills | ClawHub | Playbooks + MCP |
| Stack | Node.js | Python |

---

## ðŸ”´ PrioritÃ¤t Hoch

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| **Core Simplification (Intent-first)** | 30+ Einzeltools auf klare Facade reduzieren, Intent-Routing standardisieren, Persistenz-Contract vereinheitlichen | **Top-Prioritaet** |
| **n8n MCP Tools** | Workflows listen/get/create/update/delete via n8n Public API | âœ“ Implementiert |
| **Token-Effizienz Tools** | Dedizierte MCP Tools statt Chat-Workflows. Siehe Sektion unten. | ðŸŽ¯ In Planung |
| **Jira/Tempo Integration** | Tickets anlegen, Zeit buchen | Geplant (auf ORALYIS RECHNER) |
| **CLI Interface** | NOVA ohne VS Code nutzen (Cron, Automation) | Geplant |
| **Semantic Search** | Vault durchsuchen nach Bedeutung, nicht nur Text | âœ“ Implementiert |

---

## âœ“ Fortschritt (2026-02-12)

### n8n Integration abgeschlossen

- Neue MCP Tools: `nova_n8n_list_workflows`, `nova_n8n_get_workflow`, `nova_n8n_create_workflow`, `nova_n8n_update_workflow`, `nova_n8n_delete_workflow`
- n8n Config via ENV: `N8N_BASE_URL`, `N8N_API_KEY`, optional `N8N_INSECURE_TLS`
- `N8N_BASE_URL` wird normalisiert (auch bei `/workflow/...` URLs)
- Workflow-Payload wird bei Create/Update von read-only Feldern bereinigt (z. B. `active`, `id`, `updatedAt`)
- Testabdeckung fuer n8n Tools erweitert (26 Tests)
- Doku aktualisiert in `README.md` und `.env.example`

---

## ðŸŽ¯ Token-Effizienz Tools

> **Problem:** Chat-basierte Workflows verbrennen 3-8k Tokens pro Aktion.  
> **LÃ¶sung:** Dedizierte MCP Tools fÃ¼r repetitive Patterns.

### Die "Big 3" (First Priority)

| Tool | Ersparnis | Frequenz | Beschreibung |
|------|-----------|----------|--------------|
| `nova_get_projekt_context` | ~8k Tokens | TÃ¤glich | LÃ¤dt Kunde + Projekt + Backlog + Knowledge in einem Call |
| `nova_update_status` | ~4k Tokens | Mehrfach tÃ¤glich | Generisches Update: Entity + Status â†’ Auto-findet Dateien, updated WORKLOG + Knowledge |
| `nova_create_knowledge` | ~3k Tokens | WÃ¶chentlich | Strukturierte Erstellung mit richtigem Pfad + Frontmatter + Verlinkung |

### Update-Tools (Batch 2)

| Tool | Beschreibung | Status |
|------|--------------|--------|
| `nova_backlog_toggle` | `[ ]` â†’ `[x]` in BACKLOG.md | Geplant |
| `nova_release_log` | Pipeline + Release + Status â†’ Updated Tabelle + WORKLOG | Geplant |
| `nova_current_move` | Item in CURRENT.md zwischen Sektionen verschieben | Geplant |
| `nova_ticket_update` | Ticket-Felder Ã¤ndern (Progress, Status, etc.) | Geplant |

### Read-Tools (Batch 3)

| Tool | Beschreibung | Status |
|------|--------------|--------|
| `nova_get_ticket_context` | Ticket-ID â†’ findet Projekt, lÃ¤dt relevanten Kontext | Geplant |
| `nova_knowledge_lookup` | Topic + Scope â†’ Semantic Search + strukturierte Ausgabe | Geplant |
| `nova_locate` | "Wo ist X?" â†’ Findet Datei/Pfad | Geplant |

### Create-Tools (Batch 4)

| Tool | Beschreibung | Status |
|------|--------------|--------|
| `nova_create_kunde` | Neuen Kunden mit Template anlegen | Geplant |
| `nova_create_projekt` | Neues Projekt unter Kunde anlegen | Geplant |
| `nova_create_meeting` | Meeting-Note mit Datum + Template + Teilnehmer | Geplant |

### Analyse-Tools (Batch 5)

| Tool | Beschreibung | Status |
|------|--------------|--------|
| `nova_week_summary` | WORKLOG â†’ Tickets â†’ Zeiten aggregieren | Geplant |
| `nova_projekt_status` | Backlog + Tickets + CURRENT â†’ Status-Report | Geplant |
| `nova_list_open_todos` | Alle `[ ]` in allen BACKLOGs finden | Geplant |
| `nova_find_stale` | Notes Ã¤lter als X Tage ohne Update | Geplant |

### GeschÃ¤tzte Token-Ersparnis

| Szenario | Heute (Chat) | Mit Tool | Ersparnis |
|----------|--------------|----------|-----------|
| Projekt-Onboarding | ~8.000 | ~800 | 90% |
| Release-Update | ~5.000 | ~500 | 90% |
| Backlog-Item done | ~3.000 | ~300 | 90% |
| Knowledge erstellen | ~3.000 | ~400 | 87% |
| WochenÃ¼bersicht | ~6.000 | ~600 | 90% |

**â†’ Erwartete Gesamtersparnis: 80-90% bei repetitiven Workflows**

---

## ðŸŸ¡ PrioritÃ¤t Mittel

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| **WORKLOG Refactoring** | Format robuster machen, Append-Logik fixen, session_init ZÃ¤hlung | In Arbeit |
| **Repo-Indexing** | Repos in Vector Store (Docs, READMEs, ADRs) fÃ¼r Cross-Repo Suche | Geplant |
| **Browser Automation** | Playwright MCP Server â€“ klicken, navigieren, Screenshots | Geplant |
| **Proaktive Agents** | Heartbeats, Cron, Agent-ruft-Agent, externe Trigger | Geplant |
| **Ingestion Bot** | Telegram/WhatsApp â†’ Vault (Quick Capture unterwegs) | Geplant |
| **Vault Linting** | Broken Links, Format-Checks, Stale Detection | Geplant |
| **extract_todos** | Todos aus Meeting-Notes/Dateien extrahieren â†’ TICKETS.md | Geplant |

---

## Repo-Indexing

> Repos im Vector Store fÃ¼r schnelles Onboarding und Cross-Repo Patterns.

### Konzept

```
nova_index_repo(
    path="path/to/repo",
    scope="docs",      # docs | config | decisions | full
    persistent=False   # Session oder permanent
)
```

### Scopes

| Scope | Indexiert |
|-------|-----------|
| `docs` | README, docs/, *.md |
| `config` | + package.json, terraform, yaml |
| `decisions` | + ADRs, ARCHITECTURE |
| `full` | Alles (âš ï¸ langsam, nur fÃ¼r Archiv) |

### Use Cases

- **Onboarding**: Neues Projekt schnell verstehen
- **Pattern-Suche**: "Wie haben wir Auth woanders gelÃ¶st?"
- **Cross-Repo Wissen**: Verbindungen finden

---

## ðŸŸ¢ Nice-to-have

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| **generate_weekly** | WÃ¶chentlichen Report aus WORKLOG generieren | Geplant |
| **link_checker** | Broken Links in Vault finden | Idee |
| **Usage Analytics** | Welche Tools werden genutzt? Optimierung | Idee |
| **Knowledge Sharing** | Notes exportieren, Team-Sync | SpÃ¤ter |
| **Web UI** | Browser-Interface fÃ¼r NOVA | Phase 3 |
| **Multi-Agent** | Spezialisierte Agenten orchestrieren | Phase 3 |

---

## Semantic Search âœ“

> âœ“ **Implementiert** mit ChromaDB + sentence-transformers (all-MiniLM-L6-v2)

### Features

- **Lokal**: Keine Cloud-AbhÃ¤ngigkeit, alles auf deinem Rechner
- **Inkrementell**: Nur geÃ¤nderte Notes werden neu indexiert
- **Auto-Update**: Index wird bei `nova_session_init()` automatisch aktualisiert
- **Persistent**: Index in `nova-core/index/chroma/`

### Tools

| Tool | Funktion |
|------|----------|
| `nova_search_vault(query)` | Semantische Suche in der Vault |
| `nova_index_vault()` | Index manuell aktualisieren (auto bei Session-Start) |

### Beispiele

```
nova_search_vault("RAG-Architekturen")   â†’ Relevante Notes
nova_search_vault("Kunde-A ETL")         â†’ Kunden-Knowledge
```

---

## Proaktive Agents

> Ziel: NOVA handelt ohne Aufforderung.

### Trigger-Typen

| Trigger | Beschreibung |
|---------|--------------|
| **Heartbeat/Cron** | Zeitgesteuert: "17:00 â†’ close day Reminder" |
| **Agent-to-Agent** | Ein Agent ruft anderen: "Ingestion â†’ Categorizer â†’ Writer" |
| **External Webhook** | Telegram, Slack, API-Call â†’ NOVA reagiert |
| **Event-based** | Git Push â†’ "Soll ich CHANGELOG updaten?" |

### Architektur

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   Cron      â”‚     â”‚  Telegram   â”‚     â”‚  Webhook    â”‚
â”‚  Scheduler  â”‚     â”‚    Bot      â”‚     â”‚   API       â”‚
â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜
       â”‚                   â”‚                   â”‚
       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
                           â–¼
                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                  â”‚  NOVA Orchestrator â”‚
                  â”‚  (entscheidet was) â”‚
                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
              â–¼            â–¼            â–¼
         Agent A      Agent B      Agent C
```

---

## Vault Linting

> Ziel: QualitÃ¤t der Notes automatisch prÃ¼fen.

### Checks

| Check | Beschreibung |
|-------|--------------|
| **Broken Links** | `[[Note]]` existiert nicht |
| **Stale Detection** | Note Ã¤lter als X Monate ohne Update |
| **Format Validation** | WORKLOG-Format korrekt? YAML-Frontmatter? |
| **Orphan Notes** | Notes ohne Verlinkung |
| **Duplicate Detection** | Ã„hnliche Notes zusammenfÃ¼hren? |

### Output

```markdown
## Vault Health Report

âœ… 234 Notes OK
âš ï¸ 12 Stale Notes (>6 Monate)
âŒ 3 Broken Links
ðŸ“ 5 Format-Warnungen
```

---

## Jira/Tempo Integration

| Tool | Funktion |
|------|----------|
| `jira_create_ticket` | Ticket in Jira anlegen |
| `jira_get_ticket` | Ticket-Details abrufen |
| `tempo_log_time` | Zeit in Tempo buchen |
| `tempo_get_logged` | Gebuchte Zeiten abrufen |
| `jira_sync_tickets` | TICKETS.md â†” Jira synchronisieren |

### API-Zugang

- **Jira:** example-org.atlassian.net
- **Tempo:** io.tempo.jira/tempo-app
- **Auth:** API Token (in Environment oder Secrets)

### Use Cases

1. **close day** â†’ Zeiten direkt nach Tempo buchen
2. **Neuer Kunde** â†’ PreSales-Ticket automatisch anlegen
3. **TICKETS.md** â†’ Automatisch aus Jira befÃ¼llen

---

## CLI Interface

> Ziel: NOVA ohne VS Code nutzen â€“ fÃ¼r Automation, Cron Jobs, Scripting.

### Use Cases

1. `nova close-day` â†’ Tagesabschluss als Cron Job
2. `nova push` â†’ Repos pushen
3. `nova add "Meeting mit Kunde X"` â†’ Quick-Add zum WORKLOG

### Technisch

- MCP-Tools direkt via CLI aufrufen
- Eigener LLM API-Key (Azure OpenAI, OpenAI, Anthropic)

---

## Ingestion Bot (Phase 2)

> Ziel: Unterwegs schnell Wissen erfassen.

**Architektur-Entscheidung:** Laufzeit in 
ova-server, nicht in 
ova-core.

- Telegram Input -> 
ova-server Ingestion Endpoint
- Optional n8n als Orchestrator (Trigger, Retry, Fehlerpfad)
- Link schicken -> automatisch extrahieren, zusammenfassen, Erkenntnisse ableiten
- Strukturierte Ablage in Vault (Knowledge-Note + INBOX.md append-only)

**MVP Deliverables:**

1. Telegram Capture + Chat-ID Whitelist
2. URL/Text Verarbeitung mit dedup
3. LLM-basierte Extraktion (JSON Schema)
4. Markdown Writer in 
ova-knowledge
5. Monitoring/Retry/Dead-Letter

Guide: guides/ingestion-pipeline-nova-server.md

---

## Browser Automation

> Ziel: NOVA kann im Browser interagieren â€“ klicken, navigieren, Formulare ausfÃ¼llen.

### LÃ¶sung: Playwright MCP Server

```powershell
# Installation in VS Code
code --add-mcp '{"name":"playwright","command":"npx","args":["@executeautomation/playwright-mcp-server"]}'
```

### Tools die ich dann habe

| Tool | Beschreibung |
|------|--------------|
| `playwright_navigate` | URL Ã¶ffnen |
| `playwright_click` | Element anklicken |
| `playwright_type` | Text eingeben |
| `playwright_screenshot` | Screenshot machen |
| `playwright_resize` | Device-Emulation (iPhone, iPad, etc.) |

### Use Cases

1. Azure DevOps Pipeline genehmigen
2. Formulare ausfÃ¼llen
3. Webseiten-Tests automatisieren
4. Screenshots fÃ¼r Dokumentation

### Referenz

- [GitHub: executeautomation/mcp-playwright](https://github.com/executeautomation/mcp-playwright) (5.2k â­)
- Docs: https://executeautomation.github.io/mcp-playwright/

---

## ðŸš« Bewusste Grenzen (Nicht geplant)

| Feature | Grund |
|---------|-------|
| Autonome Deployments | Sicherheit, Kontrolle |
| Direkter Prod-Zugriff | Sicherheit |
| Selbst-Modifikation des Core | StabilitÃ¤t |
| UnbeschrÃ¤nkte externe APIs | Kosten, Sicherheit |
| Real-time Collaboration | KomplexitÃ¤t |
| Code-AusfÃ¼hrung aus User-Input | Sicherheit |

---

## ðŸ›ï¸ Architektur-Prinzipien

### Multi-Interface

NOVA ist **nicht** an ein einzelnes Interface gebunden:

| Interface | Modus | LLM-Quelle | Use Case |
|-----------|-------|------------|----------|
| **VS Code Copilot** | Synchron | Copilot (gratis) | Interaktive Arbeit, Dialog |
| **CLI** | Synchron | Eigener API-Key | Cron Jobs, Automation |
| **Telegram Bot** | Asynchron | Eigener API-Key | Unterwegs, Quick Capture |
| **Web UI** | Beides | Eigener API-Key | Browser-basiert |

### LLM-Provider Strategie

Skills die LLM benÃ¶tigen haben zwei Modi:
1. **Via Copilot** â€“ Gratis, aber nur im VS Code Context
2. **Standalone** â€“ Eigener API-Key (Azure OpenAI, OpenAI, Anthropic)

### Knowledge-First

> **Vault = Source of Truth.** Chat ist ArbeitsflÃ¤che, nicht Ergebnis.

- Alles Relevante wird persistiert
- Markdown + Git = universell, versioniert, durchsuchbar
- Semantic Search Ã¼ber alle Notes

---

*Letzte Aktualisierung: 2026-02-12*





