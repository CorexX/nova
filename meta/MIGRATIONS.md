# Migrations

> Dokumentation für Breaking Changes und Migration-Pfade.

## Format

```markdown
## Migration: [ID] - Kurzbeschreibung

**Von**: Version/Zustand vorher
**Nach**: Version/Zustand nachher
**Breaking**: Ja/Nein

### Betroffene Dateien
- file1.md
- file2.md

### Schritte
1. Schritt 1
2. Schritt 2

### Rollback
Falls nötig, so zurück.
```

---

## Migration: M001 - Initial Setup

**Von**: Kein Vault
**Nach**: Skeleton v1.0
**Breaking**: Nein (initial)

### Betroffene Dateien
- Alle (neu erstellt)

### Schritte
1. Repository klonen
2. `python scripts/init_vaults.py` (später)
3. Vaults in Obsidian öffnen

### Rollback
Repository löschen und neu klonen.

---

## Geplante Migrations

| ID | Beschreibung | Status |
|----|--------------|--------|
| M002 | Templates zu Obsidian-native Templates | Geplant |
| M003 | Frontmatter-Validierung verschärfen | Geplant |

---

Tags: #meta #migrations
