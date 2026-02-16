# Guide: Close Day Workflow

> Täglicher Abschluss mit Zeiterfassung.

---

## Wann

Am Ende jedes Arbeitstages oder wenn du "close day" sagst.

## Ablauf

### 1. WORKLOG prüfen

```markdown
## 2026-02-08 (Samstag)
- 10:00 Framework-Design (AGENT-1)
- 12:00 Struktur implementiert (AGENT-1)
- 14:00 ADRs geschrieben (AGENT-1)
```

### 2. Mit Kalender abgleichen

Falls Meetings fehlen → nachtragen.

### 3. Lücken füllen

```markdown
- 11:00 ??? Was war hier?
```

→ Nachfragen oder rekonstruieren

### 4. Tickets zuordnen

Jeder Eintrag braucht eine Ticket-ID:
- `KUNDE-123` für Kundenprojekte
- `GENAI-45` für Kompetenzteam
- `INTERN-0` für interne Arbeit

### 5. Tempo-Vorschlag

Am Ende bekommst du eine Buchungsempfehlung:

```
📋 Tempo-Buchungen:
- AGENT-1: 4h (Framework-Arbeit)

Gesamt: 4h
```

### 6. Archivierung (Freitags)

Wenn KW endet:
1. WORKLOG.md Inhalt → `archive/KW-XX.md`
2. WORKLOG.md leeren (nur Header behalten)

## Tipps

- **Früh eintragen**: Lieber grob als vergessen
- **Ticket-ID immer**: Erleichtert close_day
- **Bei Unsicherheit**: `(???)` markieren, später klären

---

## ⚠️ VS Code Session-Retention

**Wichtig:** VS Code löscht Copilot Chat-Sessions automatisch nach kurzer Zeit (meist beim Schließen oder nach wenigen Tagen).

### Problem
Die Tools `summarize_day` und `summarize_week` lesen Sessions aus:
```
%APPDATA%\Code\User\workspaceStorage\*\chatSessions\*.jsonl
```

Diese Dateien werden von VS Code **nicht dauerhaft aufbewahrt**.

### Lösung: Täglich archivieren

Am Ende jedes Arbeitstages ausführen:

```bash
# Einfache Zusammenfassung
python nova-core/skills/summarize_day.py --llm

# Mit direktem Schreiben ins WORKLOG
python nova-core/skills/summarize_day.py --llm --write

# Tagesabschluss mit Ticket-Zuordnung
python nova-core/skills/summarize_day.py --close-day
```

### Automatisierung (optional)

Windows Task Scheduler einrichten für tägliche Ausführung um 18:00:
```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\REPO\NOVA\nova-core\skills\summarize_day.py --llm --write"
$trigger = New-ScheduledTaskTrigger -Daily -At 6pm
Register-ScheduledTask -TaskName "NOVA-DailySummary" -Action $action -Trigger $trigger
```
