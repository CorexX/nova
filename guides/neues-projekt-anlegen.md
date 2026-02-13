# Guide: Projekt unter `projects/` anlegen

> Standardvorgehen zum Anlegen eines neuen Projekts unter `projects/`.

---

## Einordnung

Ein Eintrag unter `projects/` ist ein abgegrenztes Vorhaben mit klarer Struktur.
Empfohlene Kategorie: `projects/client/`, `projects/internal/`, `projects/personal/`.

---

## Schritte

### 1. Ordner anlegen

```bash
mkdir -p nova-knowledge/projects/client/neues-projekt
```

### 2. README.md anpassen

Datei: `nova-knowledge/projects/client/neues-projekt/README.md`

```markdown
# Projektname

> Ein-Satz-Beschreibung des Projekts.

## Quick Links

- [[projekte/]] - Teilprojekte
- [[notes/]] - Projektspezifisches Wissen
- [[TICKETS|Aktive Tickets]]

## Kontext

- **Domaene**: z.B. Retail
- **Stack**: z.B. Azure, Databricks
- **Hauptansprechpartner**: Name oder Team
- **Laufzeit**: seit YYYY-MM

## Teilprojekte

| Projekt | Status | Zeitraum |
|---------|--------|----------|
| ... | aktiv | ... |
```

### 3. Erstes Teilprojekt anlegen

```bash
mkdir -p nova-knowledge/projects/client/neues-projekt/projekte/erstes-teilprojekt
```

### 4. In TICKETS.md eintragen

Falls sofort Tickets existieren:

```markdown
## neues-projekt

| Ticket | Titel | Status |
|--------|-------|--------|
| PROJ-1 | Setup | offen |
```

## Checkliste

- [ ] Ordner erstellt
- [ ] README.md angepasst
- [ ] Mindestens ein Teilprojekt angelegt
- [ ] In TICKETS.md eingetragen (falls Tickets existieren)

## Namenskonvention

- **Ordnername**: lowercase, keine Leerzeichen, Bindestriche ok
- **Beispiele**: `kundenportal-relaunch`, `sales-ai-agent`, `etl-modernisierung`
