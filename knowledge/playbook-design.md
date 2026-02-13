# Playbook Design

> Wie Playbooks in NOVA aufgebaut sind.

---

## Was ist ein Playbook?

Ein **Playbook** ist eine wiederverwendbare Anleitung für den Agent. Es definiert einen Workflow mit klaren Schritten.

## Struktur

```markdown
# Playbook: Name

> Ein-Satz-Beschreibung.

---

## Trigger

Wann wird das Playbook aktiviert?

- User sagt "xyz"
- Bestimmte Situation

## Voraussetzungen

Was muss existieren?

## Schritte

1. Erster Schritt
2. Zweiter Schritt
3. ...

## Output

Was produziert das Playbook?

## Beispiel

Konkreter Beispiel-Dialog.
```

## Trigger-Arten

### User-Trigger

```markdown
## Trigger

User sagt:
- "close day"
- "Tagesabschluss"
- "Was hab ich heute gemacht?"
```

### Zeit-Trigger (Zukunft)

```markdown
## Trigger

- Jeden Freitag 17:00
- Am Ende jeder Woche
```

### Kontext-Trigger (Zukunft)

```markdown
## Trigger

- Wenn BACKLOG > 20 Items
- Wenn 7 Tage ohne Commit
```

## Best Practices

### Atomar

Ein Playbook = Ein Ziel. Nicht mehrere Dinge kombinieren.

### Idempotent

Mehrfach ausführen sollte nicht schaden.

### Mit Beispiel

Immer einen konkreten Beispiel-Dialog zeigen.

### Output definieren

Klar sagen, was am Ende entsteht (Datei, Nachricht, etc.).

## Ordnung

```
playbooks/
├── close_day.md
├── weekly_review.md      # (geplant)
├── gap_detection.md      # (geplant)
└── onboard_customer.md   # (geplant)
```

## Zukunft

In Phase 2+ können Playbooks auch:
- Von der Orchestrierung automatisch getriggert werden
- Andere Playbooks aufrufen
- Loop bis Bedingung erfüllt
