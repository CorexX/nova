# ADR-002: Globales WORKLOG

> Entscheidung für ein zentrales WORKLOG statt verteilter Logs.

---

## Status

**Akzeptiert** (2026-02-08)

## Kontext

Die Zeiterfassung muss für das `close_day` Playbook funktionieren. Es gibt zwei Ansätze:

1. **Globales WORKLOG** - Eine Datei für alle Aktivitäten
2. **Verteiltes WORKLOG** - Pro Kunde/Projekt ein eigenes Log

## Entscheidung

**Globales WORKLOG** in `nova-knowledge/WORKLOG.md`.

### Gründe

1. **Einfacheres close_day**: Agent muss nur eine Datei lesen
2. **Chronologische Übersicht**: Tagesablauf ist sofort sichtbar
3. **Weniger Kontext-Wechsel**: Kein Springen zwischen Dateien beim Eintragen
4. **Archivierung einfacher**: Eine Datei pro Woche ins Archiv

### Format

```markdown
## YYYY-MM-DD (Wochentag)
- HH:MM Aktivität (TICKET-ID)
- HH:MM Aktivität (TICKET-ID)
```

## Alternativen

### Pro Kunde/Projekt
- **Pro**: Kontextnäher, bessere Trennung
- **Contra**: close_day müsste alle durchsuchen, mehr Overhead

### Hybrid (Global + Referenzen)
- **Pro**: Flexibel
- **Contra**: Zu komplex für Phase 1

## Konsequenzen

- WORKLOG.md wird am Wochenende archiviert
- Ticket-IDs müssen im Eintrag stehen für Zuordnung
- Bei Unsicherheit über Ticket: trotzdem eintragen, später zuordnen
