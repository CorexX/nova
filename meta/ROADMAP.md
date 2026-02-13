# ROADMAP

> Geplante Features, Architektur-Vision und Integrationen für NOVA.

---

## � Die große Vision: NOVA Server Mode

> **NOVA als Always-On Personal Assistant auf deinem Homeserver.**  
> Inspiriert von [OpenClaw](https://github.com/openclaw/openclaw) – aber Knowledge-First statt Chat-First.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HOMESERVER                                     │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         NOVA GATEWAY                                │   │
│   │                                                                     │   │
│   │   • Always-on Service (Docker)                                      │   │
│   │   • LLM Connection (Claude/GPT via API)                             │   │
│   │   • Knowledge Vault + Vector Store                                  │   │
│   │   • Async Task Queue                                                │   │
│   │                                                                     │   │
│   └───────────────────────────┬─────────────────────────────────────────┘   │
│                               │                                             │
│              ┌────────────────┼────────────────┐                            │
│              ▼                ▼                ▼                            │
│         ┌────────┐       ┌────────┐       ┌────────┐                        │
│         │Telegram│       │  Web   │       │ Matrix │                        │
│         │  Bot   │       │  Chat  │       │  Bot   │                        │
│         └────────┘       └────────┘       └────────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DU (überall)                                   │
│                                                                             │
│   📱 Telegram:     "Hey NOVA, notier: Meeting mit Kunde X verschoben"       │
│   💻 Web Chat:     "Was steht heute an?"                                    │
│   🖥️ VS Code:      [wie heute - voller Power-Modus]                         │
│   📋 CLI:          nova ask "Zusammenfassung KW7"                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phasen

| Phase | Feature | Beschreibung | Status |
|-------|---------|--------------|--------|
| 1 | **Telegram Inbox** | Quick Capture unterwegs → direkt in Vault | Geplant |
| 2 | **Async Queue** | Background Tasks, Scheduled Jobs | Geplant |
| 3 | **Web Chat** | Browser Interface (self-hosted) | Geplant |
| 4 | **Proactive Agent** | Daily Briefings, Reminder, Nudges | Geplant |
| 5 | **Multi-Channel** | Matrix, Discord, Voice (Whisper) | Später |

### Phase 1: Telegram Inbox Bot (MVP)

**Status:** 🎯 NEXT UP

```
┌──────────────────────────────────────────────────────────────────┐
│   Du (unterwegs):   "Idee für NOVA: CLI interface"              │
│   NOVA:             "✓ Notiert."                                │
│                                                                  │
│   [Später in VS Code]                                            │
│   nova_session_init() → zeigt Inbox                              │
└──────────────────────────────────────────────────────────────────┘
```

#### MVP Scope (1 Abend, ~4h)

| Feature | Beschreibung |
|---------|--------------|
| ✅ Text → INBOX.md | Jede Nachricht wird appended |
| ✅ Chat-ID Whitelist | Nur du darfst schreiben |
| ✅ Bestätigung | "✓ Notiert." als Reply |
| ✅ Docker | Ein Container, läuft auf Homeserver |
| ❌ Kein LLM | Kein Verstehen, nur Capture |
| ❌ Keine Strukturierung | Phase 2 |

#### Dateien

```
nova-server/                     # NEU
├── telegram/
│   ├── bot.py                  # ~50 Zeilen Kernlogik
│   ├── config.py               # BOT_TOKEN, ALLOWED_CHAT_IDS
│   └── Dockerfile
├── docker-compose.yml
└── README.md
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
    
    await update.message.reply_text("✓ Notiert.")

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, handle))
app.run_polling()
```

#### Phase 2 (später)

- LLM versteht Kontext: "leg das bei Netto ab"
- Bilder/Dateien speichern
- Semantic Search Antworten
- Integration in `nova_session_init()` (zeigt neue Inbox-Einträge)

### Phase 4: Proaktiver Agent

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   [08:00]  NOVA → Telegram:                                      │
│            "Guten Morgen. Heute: 3 Tickets offen.                │
│             Meeting 14:00 mit Netto. Budget bei 72%."            │
│                                                                  │
│   [12:00]  NOVA → Telegram:                                      │
│            "Erinnerung: Terraform-PR noch offen."                │
│                                                                  │
│   [18:00]  NOVA → Telegram:                                      │
│            "Tagesabschluss? Soll ich close day ausführen?"       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Architektur (geplant)

```
nova-server/                     # NEU
├── gateway/
│   ├── main.py                 # FastAPI Gateway
│   ├── queue.py                # Task Queue (Redis/SQLite)
│   └── llm.py                  # LLM Connector
│
├── channels/
│   ├── telegram.py             # Telegram Bot
│   ├── matrix.py               # Matrix Bot
│   ├── web.py                  # Web Chat API
│   └── cli.py                  # CLI Interface
│
├── workers/
│   ├── capture.py              # Quick Capture → Vault
│   ├── research.py             # Background Research
│   └── scheduled.py            # Cron Jobs
│
├── docker-compose.yml
└── Dockerfile
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

## 🔴 Priorität Hoch

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| **n8n MCP Tools** | Workflows listen/get/create/update/delete via n8n Public API | ✓ Implementiert |
| **Token-Effizienz Tools** | Dedizierte MCP Tools statt Chat-Workflows. Siehe Sektion unten. | 🎯 In Planung |
| **Jira/Tempo Integration** | Tickets anlegen, Zeit buchen | Geplant (auf ORALYIS RECHNER) |
| **CLI Interface** | NOVA ohne VS Code nutzen (Cron, Automation) | Geplant |
| **Semantic Search** | Vault durchsuchen nach Bedeutung, nicht nur Text | ✓ Implementiert |

---

## ✓ Fortschritt (2026-02-12)

### n8n Integration abgeschlossen

- Neue MCP Tools: `nova_n8n_list_workflows`, `nova_n8n_get_workflow`, `nova_n8n_create_workflow`, `nova_n8n_update_workflow`, `nova_n8n_delete_workflow`
- n8n Config via ENV: `N8N_BASE_URL`, `N8N_API_KEY`, optional `N8N_INSECURE_TLS`
- `N8N_BASE_URL` wird normalisiert (auch bei `/workflow/...` URLs)
- Workflow-Payload wird bei Create/Update von read-only Feldern bereinigt (z. B. `active`, `id`, `updatedAt`)
- Testabdeckung fuer n8n Tools erweitert (26 Tests)
- Doku aktualisiert in `README.md` und `.env.example`

---

## 🎯 Token-Effizienz Tools

> **Problem:** Chat-basierte Workflows verbrennen 3-8k Tokens pro Aktion.  
> **Lösung:** Dedizierte MCP Tools für repetitive Patterns.

### Die "Big 3" (First Priority)

| Tool | Ersparnis | Frequenz | Beschreibung |
|------|-----------|----------|--------------|
| `nova_get_projekt_context` | ~8k Tokens | Täglich | Lädt Kunde + Projekt + Backlog + Knowledge in einem Call |
| `nova_update_status` | ~4k Tokens | Mehrfach täglich | Generisches Update: Entity + Status → Auto-findet Dateien, updated WORKLOG + Knowledge |
| `nova_create_knowledge` | ~3k Tokens | Wöchentlich | Strukturierte Erstellung mit richtigem Pfad + Frontmatter + Verlinkung |

### Update-Tools (Batch 2)

| Tool | Beschreibung | Status |
|------|--------------|--------|
| `nova_backlog_toggle` | `[ ]` → `[x]` in BACKLOG.md | Geplant |
| `nova_release_log` | Pipeline + Release + Status → Updated Tabelle + WORKLOG | Geplant |
| `nova_current_move` | Item in CURRENT.md zwischen Sektionen verschieben | Geplant |
| `nova_ticket_update` | Ticket-Felder ändern (Progress, Status, etc.) | Geplant |

### Read-Tools (Batch 3)

| Tool | Beschreibung | Status |
|------|--------------|--------|
| `nova_get_ticket_context` | Ticket-ID → findet Projekt, lädt relevanten Kontext | Geplant |
| `nova_knowledge_lookup` | Topic + Scope → Semantic Search + strukturierte Ausgabe | Geplant |
| `nova_locate` | "Wo ist X?" → Findet Datei/Pfad | Geplant |

### Create-Tools (Batch 4)

| Tool | Beschreibung | Status |
|------|--------------|--------|
| `nova_create_kunde` | Neuen Kunden mit Template anlegen | Geplant |
| `nova_create_projekt` | Neues Projekt unter Kunde anlegen | Geplant |
| `nova_create_meeting` | Meeting-Note mit Datum + Template + Teilnehmer | Geplant |

### Analyse-Tools (Batch 5)

| Tool | Beschreibung | Status |
|------|--------------|--------|
| `nova_week_summary` | WORKLOG → Tickets → Zeiten aggregieren | Geplant |
| `nova_projekt_status` | Backlog + Tickets + CURRENT → Status-Report | Geplant |
| `nova_list_open_todos` | Alle `[ ]` in allen BACKLOGs finden | Geplant |
| `nova_find_stale` | Notes älter als X Tage ohne Update | Geplant |

### Geschätzte Token-Ersparnis

| Szenario | Heute (Chat) | Mit Tool | Ersparnis |
|----------|--------------|----------|-----------|
| Projekt-Onboarding | ~8.000 | ~800 | 90% |
| Release-Update | ~5.000 | ~500 | 90% |
| Backlog-Item done | ~3.000 | ~300 | 90% |
| Knowledge erstellen | ~3.000 | ~400 | 87% |
| Wochenübersicht | ~6.000 | ~600 | 90% |

**→ Erwartete Gesamtersparnis: 80-90% bei repetitiven Workflows**

---

## 🟡 Priorität Mittel

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| **WORKLOG Refactoring** | Format robuster machen, Append-Logik fixen, session_init Zählung | In Arbeit |
| **Repo-Indexing** | Repos in Vector Store (Docs, READMEs, ADRs) für Cross-Repo Suche | Geplant |
| **Browser Automation** | Playwright MCP Server – klicken, navigieren, Screenshots | Geplant |
| **Proaktive Agents** | Heartbeats, Cron, Agent-ruft-Agent, externe Trigger | Geplant |
| **Ingestion Bot** | Telegram/WhatsApp → Vault (Quick Capture unterwegs) | Geplant |
| **Vault Linting** | Broken Links, Format-Checks, Stale Detection | Geplant |
| **extract_todos** | Todos aus Meeting-Notes/Dateien extrahieren → TICKETS.md | Geplant |

---

## Repo-Indexing

> Repos im Vector Store für schnelles Onboarding und Cross-Repo Patterns.

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
| `full` | Alles (⚠️ langsam, nur für Archiv) |

### Use Cases

- **Onboarding**: Neues Projekt schnell verstehen
- **Pattern-Suche**: "Wie haben wir Auth woanders gelöst?"
- **Cross-Repo Wissen**: Verbindungen finden

---

## 🟢 Nice-to-have

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| **generate_weekly** | Wöchentlichen Report aus WORKLOG generieren | Geplant |
| **link_checker** | Broken Links in Vault finden | Idee |
| **Usage Analytics** | Welche Tools werden genutzt? Optimierung | Idee |
| **Knowledge Sharing** | Notes exportieren, Team-Sync | Später |
| **Web UI** | Browser-Interface für NOVA | Phase 3 |
| **Multi-Agent** | Spezialisierte Agenten orchestrieren | Phase 3 |

---

## Semantic Search ✓

> ✓ **Implementiert** mit ChromaDB + sentence-transformers (all-MiniLM-L6-v2)

### Features

- **Lokal**: Keine Cloud-Abhängigkeit, alles auf deinem Rechner
- **Inkrementell**: Nur geänderte Notes werden neu indexiert
- **Auto-Update**: Index wird bei `nova_session_init()` automatisch aktualisiert
- **Persistent**: Index in `nova-core/index/chroma/`

### Tools

| Tool | Funktion |
|------|----------|
| `nova_search_vault(query)` | Semantische Suche in der Vault |
| `nova_index_vault()` | Index manuell aktualisieren (auto bei Session-Start) |

### Beispiele

```
nova_search_vault("RAG-Architekturen")   → Relevante Notes
nova_search_vault("Netto ETL")           → Kunden-Knowledge
```

---

## Proaktive Agents

> Ziel: NOVA handelt ohne Aufforderung.

### Trigger-Typen

| Trigger | Beschreibung |
|---------|--------------|
| **Heartbeat/Cron** | Zeitgesteuert: "17:00 → close day Reminder" |
| **Agent-to-Agent** | Ein Agent ruft anderen: "Ingestion → Categorizer → Writer" |
| **External Webhook** | Telegram, Slack, API-Call → NOVA reagiert |
| **Event-based** | Git Push → "Soll ich CHANGELOG updaten?" |

### Architektur

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Cron      │     │  Telegram   │     │  Webhook    │
│  Scheduler  │     │    Bot      │     │   API       │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  NOVA Orchestrator │
                  │  (entscheidet was) │
                  └─────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Agent A      Agent B      Agent C
```

---

## Vault Linting

> Ziel: Qualität der Notes automatisch prüfen.

### Checks

| Check | Beschreibung |
|-------|--------------|
| **Broken Links** | `[[Note]]` existiert nicht |
| **Stale Detection** | Note älter als X Monate ohne Update |
| **Format Validation** | WORKLOG-Format korrekt? YAML-Frontmatter? |
| **Orphan Notes** | Notes ohne Verlinkung |
| **Duplicate Detection** | Ähnliche Notes zusammenführen? |

### Output

```markdown
## Vault Health Report

✅ 234 Notes OK
⚠️ 12 Stale Notes (>6 Monate)
❌ 3 Broken Links
📝 5 Format-Warnungen
```

---

## Jira/Tempo Integration

| Tool | Funktion |
|------|----------|
| `jira_create_ticket` | Ticket in Jira anlegen |
| `jira_get_ticket` | Ticket-Details abrufen |
| `tempo_log_time` | Zeit in Tempo buchen |
| `tempo_get_logged` | Gebuchte Zeiten abrufen |
| `jira_sync_tickets` | TICKETS.md ↔ Jira synchronisieren |

### API-Zugang

- **Jira:** example-org.atlassian.net
- **Tempo:** io.tempo.jira/tempo-app
- **Auth:** API Token (in Environment oder Secrets)

### Use Cases

1. **close day** → Zeiten direkt nach Tempo buchen
2. **Neuer Kunde** → PreSales-Ticket automatisch anlegen
3. **TICKETS.md** → Automatisch aus Jira befüllen

---

## CLI Interface

> Ziel: NOVA ohne VS Code nutzen – für Automation, Cron Jobs, Scripting.

### Use Cases

1. `nova close-day` → Tagesabschluss als Cron Job
2. `nova push` → Repos pushen
3. `nova add "Meeting mit Kunde X"` → Quick-Add zum WORKLOG

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

Guide: playbooks/ingestion-pipeline-nova-server.md

---

## Browser Automation

> Ziel: NOVA kann im Browser interagieren – klicken, navigieren, Formulare ausfüllen.

### Lösung: Playwright MCP Server

```powershell
# Installation in VS Code
code --add-mcp '{"name":"playwright","command":"npx","args":["@executeautomation/playwright-mcp-server"]}'
```

### Tools die ich dann habe

| Tool | Beschreibung |
|------|--------------|
| `playwright_navigate` | URL öffnen |
| `playwright_click` | Element anklicken |
| `playwright_type` | Text eingeben |
| `playwright_screenshot` | Screenshot machen |
| `playwright_resize` | Device-Emulation (iPhone, iPad, etc.) |

### Use Cases

1. Azure DevOps Pipeline genehmigen
2. Formulare ausfüllen
3. Webseiten-Tests automatisieren
4. Screenshots für Dokumentation

### Referenz

- [GitHub: executeautomation/mcp-playwright](https://github.com/executeautomation/mcp-playwright) (5.2k ⭐)
- Docs: https://executeautomation.github.io/mcp-playwright/

---

## 🚫 Bewusste Grenzen (Nicht geplant)

| Feature | Grund |
|---------|-------|
| Autonome Deployments | Sicherheit, Kontrolle |
| Direkter Prod-Zugriff | Sicherheit |
| Selbst-Modifikation des Core | Stabilität |
| Unbeschränkte externe APIs | Kosten, Sicherheit |
| Real-time Collaboration | Komplexität |
| Code-Ausführung aus User-Input | Sicherheit |

---

## 🏛️ Architektur-Prinzipien

### Multi-Interface

NOVA ist **nicht** an ein einzelnes Interface gebunden:

| Interface | Modus | LLM-Quelle | Use Case |
|-----------|-------|------------|----------|
| **VS Code Copilot** | Synchron | Copilot (gratis) | Interaktive Arbeit, Dialog |
| **CLI** | Synchron | Eigener API-Key | Cron Jobs, Automation |
| **Telegram Bot** | Asynchron | Eigener API-Key | Unterwegs, Quick Capture |
| **Web UI** | Beides | Eigener API-Key | Browser-basiert |

### LLM-Provider Strategie

Skills die LLM benötigen haben zwei Modi:
1. **Via Copilot** – Gratis, aber nur im VS Code Context
2. **Standalone** – Eigener API-Key (Azure OpenAI, OpenAI, Anthropic)

### Knowledge-First

> **Vault = Source of Truth.** Chat ist Arbeitsfläche, nicht Ergebnis.

- Alles Relevante wird persistiert
- Markdown + Git = universell, versioniert, durchsuchbar
- Semantic Search über alle Notes

---

*Letzte Aktualisierung: 2026-02-12*

