# Obsidian Linking

> Wie Links in Obsidian funktionieren.

---

## Wikilinks

Standard in Obsidian:

```markdown
[[Dateiname]]
[[Dateiname|Anzeigename]]
[[Dateiname#Heading]]
[[Dateiname#Heading|Anzeigename]]
```

## Relative Pfade

Für Ordner:

```markdown
[[ordner/datei]]
[[../andere-ebene/datei]]
```

## Markdown Links

Auch möglich (besser für Git-Kompatibilität):

```markdown
[Text](pfad/zu/datei.md)
[Text](datei.md#heading)
```

## Aliase

In YAML Frontmatter:

```yaml
---
aliases:
  - Kurzname
  - Anderer Name
---
```

Dann funktioniert `[[Kurzname]]`.

## Embeds

Inhalt einbetten:

```markdown
![[datei]]
![[datei#heading]]
![[bild.png]]
```

## Best Practices

### Eindeutige Namen

```
❌ README.md (überall)
✅ nova-core-readme.md
```

Oder: Pfade in Links verwenden.

### Relative Pfade bevorzugen

Bei Umbenennung von Ordnern bleiben Links intakt.

### Keine Sonderzeichen

```
❌ Mein Projekt (2024).md
✅ mein-projekt-2024.md
```

## Git-Kompatibilität

Für Code-Repos (die nicht nur in Obsidian gelesen werden):

- Markdown-Links statt Wikilinks
- Relative Pfade
- Keine Spaces in Dateinamen
