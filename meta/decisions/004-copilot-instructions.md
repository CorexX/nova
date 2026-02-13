# ADR-004: Copilot-Instructions am Workspace-Root

> Entscheidung für Platzierung der Copilot-Instruktionen.

---

## Status

**Akzeptiert** (2026-02-08)

## Kontext

GitHub Copilot Chat lädt automatisch `.github/copilot-instructions.md` als Kontext. Die Frage war, wo diese Datei liegen soll.

## Entscheidung

**Workspace Root**: `.github/copilot-instructions.md` liegt im Workspace-Root, nicht in einem Unterordner.

```
knowledge-workspace/
├── .github/
│   └── copilot-instructions.md  # ← Hier
├── nova-core/
└── nova-knowledge/
```

## Gründe

1. **Automatisches Laden**: Copilot sucht nur im Workspace-Root
2. **Minimale Indirektion**: Direkte Referenz auf CORE.md
3. **Single Entry Point**: Nur eine Datei pflegen

## Inhalt

Die `copilot-instructions.md` ist ein Pointer:

```markdown
# Copilot Instructions

Du arbeitest im `knowledge-workspace`.

## Beim Start
Lies zuerst: `nova-core/core/CORE.md`

## Bei Arbeit
Lies zusätzlich:
- `nova-knowledge/CURRENT.md`
- `nova-knowledge/TICKETS.md`
```

## Alternativen

### Vollständige Instruktionen in copilot-instructions.md
- **Pro**: Alles an einem Ort
- **Contra**: Duplikation mit CORE.md, schwer zu pflegen

### Symbolischer Link
- **Pro**: Keine Duplikation
- **Contra**: Windows-Kompatibilität fraglich

## Konsequenzen

- Bei Änderungen an Core-Instruktionen: CORE.md bearbeiten
- copilot-instructions.md nur ändern wenn Pfade sich ändern
- Getestet und funktioniert (Agent lädt Instruktionen)
