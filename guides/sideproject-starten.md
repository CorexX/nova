# Guide: Projekt starten (personal/experiments)

> Standardvorgehen zum Start eines neuen freien Projekts.

---

## Wann ein freies Projekt?

- Persoenliche Lernprojekte
- Interne Tools
- Experimente
- Open-Source-Beitraege

## Schritte

### 1. Ordner erstellen

```bash
mkdir -p nova-knowledge/projects/personal/mein-projekt
```

### 2. README.md ausfuellen

```markdown
# Projektname

> Ein-Satz-Beschreibung.

## Status

In Arbeit

## Quick Links

- [[BACKLOG]] - Offene Aufgaben
- [[docs/decisions/]] - Entscheidungen
- [[notes/]] - Gelerntes

## Ziel

Was soll das Projekt erreichen?

## Stack

- Sprache: ...
- Framework: ...
- Infrastruktur: ...
```

### 3. BACKLOG initialisieren

```markdown
# Backlog

## Naechste Schritte

- [ ] Erste Aufgabe
- [ ] Zweite Aufgabe

## Ideen

- Irgendwann mal...
```

### 4. Erste ADR schreiben

Wichtige Architekturentscheidungen dokumentieren:

```markdown
# ADR-001: Technologie-Stack

## Status
Akzeptiert

## Entscheidung
Python + FastAPI weil...
```

## Nach dem Start

- Regelmaessig BACKLOG aktualisieren
- Learnings in `notes/` festhalten
- Session-Notizen in `notes/meetings/` schreiben
