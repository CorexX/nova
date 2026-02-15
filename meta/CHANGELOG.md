# Changelog

> Änderungshistorie für nova-core.

## Format

```markdown
## [YYYY-MM-DD] - Kurzbeschreibung

### Added
- Neue Features

### Changed
- Änderungen an bestehendem

### Fixed
- Bugfixes

### Removed
- Entfernte Features
```

---

## [2026-02-15] - Remove test operation from nova_system_maintain

### Changed
- `mcp/tools/v2/system_maintain.py`: `operation=\"test\"` aus public MCP API entfernt.
- `nova_system_maintain` unterstuetzt jetzt nur noch `health`, `index`, `restart`.
- Unsupported operations liefern jetzt klare Meldung mit erlaubten Werten.

### Documentation
- `mcp/README.md` aktualisiert: `nova_system_maintain` zeigt nur noch `(health, index, restart)`.
- Migration-Hinweis ergaenzt: Testausfuehrung ueber `nova_run_tests`.

### Migration
- Breaking change: `nova_system_maintain(operation=\"test\")` ist nicht mehr verfuegbar.
- Ersatz: `nova_run_tests` mit optionalem `pattern`.

---

## [2026-02-13] - Documentation sync for current core state

### Changed
- `README.md` um einen expliziten Ist-Stand erweitert (`2026-02-13`) inklusive technischer Anpassungen, abgeleiteter Erkenntnisse und operativer Kernpunkte.
- `mcp/README.md` auf aktuellen Server-Einstiegspunkt und reale Kennzahlen synchronisiert (`mcp/nova_mcp_core_server.py`, 27 Tools, aktueller Teststatus).
- Veraltete MCP-Doku-Referenzen auf `server.py` und nicht mehr zutreffende Tool-Kategorien bereinigt.

### Verification
- MCP Tool Suite lokal verifiziert: `python -m pytest mcp/tools/tests -q` -> `304 passed, 5 skipped`.

### Insights
- Stabilitaet kommt in NOVA Core aktuell hauptsaechlich aus Runtime-Guardrails (Launcher + klare Tool-Registry), weniger aus Prompt-Komplexitaet.
- Doku-Drift an Einstiegspunkten und Testzahlen ist ein reales Betriebsrisiko; diese Daten muessen als first-class Statusinformation gepflegt werden.

---

## [2026-02-12] - n8n MCP Integration

### Added
- Neue n8n MCP Tools: `nova_n8n_list_workflows`, `nova_n8n_get_workflow`, `nova_n8n_create_workflow`, `nova_n8n_update_workflow`, `nova_n8n_delete_workflow`
- Testdatei `mcp/tools/tests/test_n8n_tools.py` mit erweiterter Abdeckung (26 Tests)
- n8n ENV Beispiele in `.env.example`: `N8N_BASE_URL`, `N8N_API_KEY`, `N8N_INSECURE_TLS`

### Changed
- `resolve_n8n_config()` unterstuetzt jetzt optional `N8N_INSECURE_TLS` aus der Umgebung
- n8n Base URL wird normalisiert (z. B. von `/workflow/...` auf Host-Basis)
- README um n8n Konfiguration und Sicherheits-Hinweise ergaenzt

### Fixed
- Create/Update von n8n Workflows entfernt read-only Felder (z. B. `active`, `id`, `updatedAt`) vor API-Calls
- n8n Tooling robuster gegen typische TLS-/Payload-Probleme in internen Setups

### Documentation
- Roadmap-Ingestion konkretisiert: Laufzeit in `nova-server`, n8n optional als Orchestrator
- Neuer Umsetzungsleitfaden: `guides/ingestion-pipeline-nova-server.md`
- `nova-server/README.md` als detaillierte Lernanleitung erweitert (SSH-Zugang, Go-Live, Webhook, Troubleshooting)

---

## [2026-02-10] - Coherence Audit

### Fixed
- `session_init.py`: Persona loading regex now matches `## Wer du bist` (was `## Persona`)
- All `work/` path references updated to `nova-knowledge/` across playbooks and ADRs
- CHANGELOG entries corrected (removed non-existent `policies/` and `templates/` folder refs)

### Removed
- `SKILL_CANDIDATES.md` from Schreib-Scope (file never existed)
- `nova_list_skills` from tool documentation (tools loaded by VS Code at session start)
- Duplicate `nova-knowledge/ROADMAP.md` (source of truth is `nova-core/meta/ROADMAP.md`)

---

## [2026-02-08] - NOVA Naming

### Changed
- System umbenannt zu **NOVA** = Notes-based Orchestrated Virtual Assistant
- `agent-core/` → `nova-core/`
- `agent-work/` → `nova-work/` → `nova-knowledge/`
- Alle Pfad-Referenzen aktualisiert

---

## [2026-02-08] - Struktur-Vereinheitlichung

### Changed
- Ordnernamen ohne Nummern-Präfixe (konsistent mit nova-knowledge/)
- `00_CORE/` → `core/`
- `02_PLAYBOOKS/` → `playbooks/`
- `04_GUIDES/` → `guides/`
- `05_KNOWLEDGE/` → `knowledge/`
- `90_META/` → `meta/`

### Added
- `guides/` - How-Tos für Workflows
- `knowledge/` - Framework-Wissen (ADR-Format, Obsidian Linking, etc.)
- `meta/decisions/` - Framework-ADRs

---

## [2026-02-08] - Initial Skeleton

### Added
- Komplette Vault-Struktur erstellt
- core: CORE.md
- playbooks: close_day.md
- meta: ARCHITECTURE_HIGH, ARCHITECTURE_LOW, CHANGELOG, MIGRATIONS

### Notes
- Nur Skeleton, keine Laufzeitlogik
- Templates ohne Frontmatter

---

Tags: #meta #changelog
