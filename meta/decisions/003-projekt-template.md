# ADR-003: Projekt-Template Struktur

> Entscheidung für erweiterte Projektstruktur mit Unterordnern.

---

## Status

**Akzeptiert** (2026-02-08)

## Kontext

Projekte brauchen eine einheitliche Struktur. Zwei Optionen:

1. **Minimal**: Nur README.md und 2-3 Dateien
2. **Erweitert**: Vollständige Ordnerstruktur mit docs/, knowledge/, notes/, etc.

## Entscheidung

**Erweiterte Struktur** mit folgenden Ordnern:

```
projekt/
├── README.md          # Übersicht + Quick Links
├── BACKLOG.md         # Alle offenen Aufgaben
├── docs/
│   ├── decisions/     # ADRs
│   └── guides/        # How-Tos
├── knowledge/         # Gelerntes, wiederverwendbar
├── notes/             # Session-Notes, Meetings
├── assets/            # Bilder, Diagramme
├── research/          # Recherche, Vergleiche
└── archive/           # Abgeschlossene Items
```

## Gründe

1. **Konsistenz**: Gleiche Struktur überall = weniger kognitive Last
2. **Skalierbarkeit**: Wächst mit dem Projekt
3. **Trennung von Concerns**: Knowledge vs. Notes vs. Decisions klar getrennt
4. **Agent-freundlich**: Klare Pfade, keine Ratespiele

## Alternativen

### Minimale Struktur
```
projekt/
├── README.md
├── NOTES.md
└── LEARNING.md
```

- **Pro**: Einfacher Start
- **Contra**: Wächst chaotisch, schwer zu refactoren

## Konsequenzen

- Templates müssen alle Ordner enthalten (auch wenn leer)
- README.md enthält Quick Links zu allen Unterordnern
- Leere Ordner bekommen .gitkeep oder README.md
