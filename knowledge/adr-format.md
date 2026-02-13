# ADR-Format

> Architecture Decision Records - Format und Best Practices.

---

## Was ist ein ADR?

Ein **Architecture Decision Record** dokumentiert eine wichtige Entscheidung im Projekt.

## Format

```markdown
# ADR-XXX: Kurzer Titel

> Ein-Satz-Zusammenfassung.

---

## Status

**Akzeptiert** | Vorgeschlagen | Abgelehnt | Ersetzt durch ADR-YYY

## Kontext

Was ist das Problem? Warum muss entschieden werden?

## Entscheidung

Was wurde entschieden?

## Gründe

Warum diese Entscheidung?

## Alternativen

Was wurde nicht gewählt und warum?

## Konsequenzen

Was folgt aus der Entscheidung?
```

## Nummerierung

- Fortlaufend: `001`, `002`, `003`
- Keine Lücken lassen
- Bei Ablehnung: Status ändern, nicht löschen

## Wann ein ADR?

✅ Technologie-Auswahl (Framework, Sprache)
✅ Strukturentscheidungen (Ordner, Architektur)
✅ Workflow-Definitionen
✅ Abweichungen von Standards

❌ Bugfixes
❌ Triviale Änderungen
❌ Temporäre Workarounds

## Dateibenennung

```
meta/decisions/
├── 001-initiale-struktur.md
├── 002-database-choice.md
└── 003-api-design.md
```

## Referenzen

- [Michael Nygard: Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
