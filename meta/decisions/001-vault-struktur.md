# ADR-001: Vault-Struktur

> Architektur-Entscheidung zur Vault-Organisation.

---

## Status

**Akzeptiert** (2026-02-08)

## Kontext

NOVA braucht eine klare, domaeinenneutrale Ordnerstruktur fuer:
- Arbeitssteuerung
- Projekte
- Referenzwissen
- schnelle Suche ueber den gesamten Vault

## Entscheidung

Struktur unter `nova-knowledge/`:

```
nova-knowledge/
|-- inbox/           # Schnelles Capture
|-- areas/           # Laufende Verantwortungsbereiche
|-- projects/        # Vorhaben mit Ziel/Ende
|-- resources/       # Guides, Templates, Konzepte
|-- operations/      # Daily/Weekly/Monthly Steuerung
`-- archive/         # Abgeschlossenes
```

Globale Dateien:
- `WORKLOG.md` - zentral, append-only
- `TICKETS.md` - aktive Ticket-/Budgetsicht
- `CURRENT.md` - aktueller Fokus

## Alternativen

1. Domain-spezifische Top-Level (`kunden`, `kompetenz`) - verworfen, weil nicht allgemein genug
2. Flache Struktur - verworfen, weil bei Wachstum unuebersichtlich
3. Separate Vaults - verworfen, weil Querverlinkung und Suche schwieriger

## Konsequenzen

- Tools arbeiten ueber `knowledge_root` und sind nicht an feste Domain-Ordner gebunden
- Context-Tools liefern generische Collections/Pfade
- Search (`nova_index_vault`, `nova_search_vault`) bleibt die primaere Navigation
