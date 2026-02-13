# NOVA System (Public)

## Purpose
Dieses Dokument beschreibt das uebergeordnete NOVA-System ohne sensible Betriebsdaten.

## System Scope
- `nova-core`: Framework, MCP-Server, Skills, Playbooks, Standards.
- `nova-server`: Ingestion-Service (z. B. Telegram Webhook -> Inbox).
- `nova-knowledge`: Private Wissens- und Arbeitsdaten.

## Architecture
```text
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTENDS                                   │
│      VS Code · Claude Desktop · CLI · Web (optional n8n)           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          NOVA CORE                                  │
│               Persona · Regeln · MCP Tools · Playbooks              │
└───────────────┬──────────────────────────────┬──────────────────────┘
                │                              │
                ▼                              ▼
      ┌─────────────────────┐        ┌─────────────────────┐
      │   CONTEXT / ACTION  │        │       SEARCH        │
      │   (Markdown/Git)    │        │    (Chroma Index)   │
      │   nova-knowledge    │        │   NOVA_INDEX_ROOT   │
      └─────────────────────┘        └─────────────────────┘

Ingress (separat):
Telegram/Webhook -> nova-server -> INBOX in nova-knowledge
```

1. Frontend/Client spricht mit NOVA (MCP oder API).
2. `nova-core` orchestriert Kontexte, Skills und Suchfunktionen.
3. `nova-server` schreibt rohe Ingestion-Eintraege in `nova-knowledge`.
4. `nova-core` verarbeitet und nutzt diese Daten fuer Suche, Worklog und Zusammenfassungen.

## Responsibility Split
- `nova-core` besitzt Logik, Regeln, Tooling und Versionierbarkeit.
- `nova-server` besitzt nur Ingestion-Laufzeit und Auth/Validation.
- `nova-knowledge` besitzt nur Inhalte, keine Runtime-Logik.

## Read/Write Matrix
| Repo | Liest | Schreibt |
|------|-------|----------|
| `nova-core` | `nova-core/*`, `nova-knowledge/*`, optional Index-Store | optional `nova-knowledge/*` (Tool-Operationen), `NOVA_INDEX_ROOT/*` |
| `nova-server` | eigene Runtime-Config (`.env`/ENV), eingehende Webhooks | konfigurierter Inbox-Pfad in `nova-knowledge` |
| `nova-knowledge` | n/a (Datenrepo, kein Runtime-Prozess) | manuelle Pflege, plus Writes durch `nova-core`/`nova-server` |

## Shared Contracts
- Cross-Repo Uebersicht: `../README.md`
- Repo-spezifisch:
  - `CONTRACTS.md` (nova-core)
  - `../nova-server/CONTRACTS.md`
  - `../nova-knowledge/CONTRACTS.md`

## Security and Privacy Boundary
- Teilbar/oeffentlich: `nova-core`, optional Teile von `nova-server`.
- Privat: `nova-knowledge` und alle produktiven Betriebsparameter.

## Companion Document (Private)
Sensible Betriebsdetails (Hosts, Domains, Tokens, Deployment-Schritte, On-Call) stehen in:
- `../nova-knowledge/SYSTEM_PRIVATE.md`

## Decoupling Status (2026-02-13)
### Done
- Repo-Grenzen und Rollen dokumentiert (`meta/SYSTEM.md`, `CONTRACTS.md`, Root-README).
- Pfad-/Runtime-Contracts eingefuehrt (`NOVA_CORE_ROOT`, `NOVA_KNOWLEDGE_ROOT`, `NOVA_INDEX_ROOT`, `KNOWLEDGE_ROOT`, `INBOX_PATH`).
- `nova-server` als eigenstaendiges Ingestion-Modul dokumentiert und abgegrenzt.
- Architekturfluss fuer das Zusammenspiel aller drei Repos aktualisiert.

### Open
- Index-Artefakte liegen noch unter `nova-core/index` und sollten extern betrieben werden (`NOVA_INDEX_ROOT`) inkl. Repo-Cleanup.
- Grenztests fuer entkoppelte Laufzeit (kein implizites `tmp/.../nova-knowledge`) koennen weiter ausgebaut werden.
