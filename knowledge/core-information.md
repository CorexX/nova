# NOVA - Core Information

> Kurzuebersicht ueber Rollen, Grenzen und Betriebslogik des NOVA-Systems.

---

## Kernprinzip

**Vault = Source of Truth.**
Chat ist Arbeitsflaeche, nicht Ergebnis.

---

## Repository-Rollen

| Bereich | Rolle | Inhalt |
|---|---|---|
| `nova-core` | Framework (public-faehig) | Regeln, MCP-Tools, technische Integrationen |
| `nova-knowledge` | Arbeitsdaten (privat) | Kunden, Projekte, Notizen, laufendes Wissen |
| `nova-server` | Ingestion/Automation Runtime | Webhooks, optional n8n-nahe Betriebsintegration |

---

## Knowledge Boundary

### Was in `nova-core/knowledge` bleibt

Nur kritisches Framework-Wissen:
- stabile Konventionen
- technische Referenz fuer Tooling/Agent-Verhalten
- selten geaenderte Grundlagen

### Was in `nova-knowledge/knowledge` gehoert

Laufendes Arbeits- und Fachwissen:
- projekt- und kundenspezifische Erkenntnisse
- Research, Notizen, Playbook-nahe Learnings
- inhaltliche Skill-Spezifikationen

---

## Meta Boundary

`nova-core/meta` ist die System-Ebene:
- Architektur
- ADRs / Entscheidungen
- Changelog

`meta` ist nicht der Ort fuer Tageswissen oder Projektinhalte.

---

## Skills im aktuellen Kontext

Der Begriff "Skills" ist zweigeteilt:

1. **Agent-Skill-Spezifikationen (kanonisch)**
   - Ort: `nova-knowledge/skills`
   - Inhalt: anleitende, domain-nahe Skill-Definitionen fuer Agenten

2. **Legacy technische Skripte**
   - Ort: `nova-core/skills`
   - Inhalt: Python-Hilfsskripte fuer bestehende Workflows

Konvention:
- neues inhaltliches Skill-Wissen -> `nova-knowledge/skills`
- technische Runtime-Skripte -> `nova-core/skills`

---

## Search / Index

Der semantische Index ist Runtime-Artefakt und liegt standardmaessig ausserhalb des Repo-Inhalts:
- Default: `.nova/index`
- Override: `NOVA_INDEX_ROOT`

Ziel:
- kein Repo-Ballast durch volatile Index-Daten
- klare Trennung von Code und Laufzeitzustand

---

## MCP Tools (relevant)

- `nova_get_structure`: zeigt aktuelle Struktur + Boundaries
- `nova_get_agent_skills`: listet Skill-Spezifikationen vs Legacy-Skripte
- `nova_index_vault`, `nova_search_vault`: lokale semantische Suche

---

## Wichtige Dateien

- `nova-core/core/CORE.md`
- `nova-core/core/PRINCIPLES.md`
- `nova-core/CONTRACTS.md`
- `nova-knowledge/CURRENT.md`
- `nova-knowledge/TICKETS.md`
- `nova-knowledge/WORKLOG.md`
