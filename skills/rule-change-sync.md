# Skill: rule-change-sync

## Zweck
Kurzer Workflow, um Regel-/Verhaltensanpassungen an allen noetigen Stellen konsistent zu machen.

## Wann nutzen
- Wenn CORE-Verhalten, Antwortformat oder Unklarheits-/Fallback-Regeln geaendert werden.
- Wenn Aenderungen sofort wirken sollen und auch nach Re-Setup bestehen muessen.

## Source of Truth
`templates/personas/base.md` (global)

## Minimaler Workflow
1. Scope festlegen:
   - Globales Verhalten -> `templates/personas/base.md`
   - Persona-spezifisch -> `templates/personas/<persona>.md`
2. Template zuerst patchen (dauerhaft).
3. Aktive Laufzeitdatei synchronisieren (sofort wirksam):
   - `core/CORE.md` mit derselben Aenderung patchen.
4. Optional Doku aktualisieren, wenn Nutzerfluss betroffen ist:
   - `README.md` oder passendes `playbooks/*.md`.
5. Kurz pruefen und abschliessen.

## Check-Kommandos (PowerShell)
```powershell
rg -n "Unklarheits-Regel|ctx:|hits:|next:" templates/personas core/CORE.md
git diff -- templates/personas/base.md core/CORE.md README.md playbooks
git status --short
```

## Done-Kriterien
- Regel in Template enthalten (persistiert nach Re-Setup).
- Regel in `core/CORE.md` enthalten (sofort aktiv).
- Optional: User-Doku angepasst, falls Verhalten fuer Nutzer sichtbar ist.
- Diff ist klein, zielgerichtet und ohne Nebenwirkungen.

## Guardrails
- Keine stillen Annahmen bei mehrdeutigen Begriffen.
- Bei `matches: []` immer zweiter Lookup ohne enge Filter.
- Ausgabe kurz und stabil halten (kompakte Pipe-Zeile).
