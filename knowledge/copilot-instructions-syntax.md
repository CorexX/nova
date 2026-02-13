# Copilot Instructions Syntax

> Wie GitHub Copilot Chat Instruktionen lädt.

---

## Automatisches Laden

Copilot Chat lädt automatisch:

```
.github/copilot-instructions.md
```

Diese Datei wird bei **jeder** Chat-Session geladen.

## Syntax

Standard Markdown. Copilot versteht:

- Überschriften für Struktur
- Code-Blöcke für Beispiele
- Listen für Regeln
- Links zu anderen Dateien

## Instruktionen zum Lesen

Copilot kann angewiesen werden, weitere Dateien zu lesen:

```markdown
## Beim Start

Lies zuerst:
- `pfad/zu/datei.md`
```

Copilot befolgt dies und lädt die Datei.

## Best Practices

### Kurz halten

Die Hauptdatei sollte ein Pointer sein, nicht die gesamte Dokumentation.

### Klare Befehle

```markdown
❌ Du könntest vielleicht...
✅ Lies zuerst CORE.md
```

### Pfade relativ zum Workspace

```markdown
✅ nova-knowledge/CURRENT.md
❌ e:\Dev\...\CURRENT.md
```

## Debugging

Falls Instruktionen nicht geladen werden:

1. Datei muss genau `.github/copilot-instructions.md` heißen
2. Muss im Workspace-Root liegen
3. Muss valides Markdown sein
4. Copilot Chat neu starten

## Referenzen

- [Copilot Customization Docs](https://docs.github.com/en/copilot/customizing-copilot)
