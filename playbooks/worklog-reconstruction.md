# Playbook: WORKLOG Rekonstruktion

## Wann nutzen?

Wenn WORKLOG.md Einträge fehlen oder lückenhaft ist und aus verschiedenen Quellen rekonstruiert werden muss.

---

## Datenquellen (Priorität)

| Quelle | Pfad | Enthält |
|--------|------|---------|
| **Git Commits** | Alle 3 Repos | Timestamps + Commit Messages |
| **Codex CLI Sessions** | `~/.codex/sessions/YYYY/MM/DD/*.jsonl` | User Prompts + Timestamps |
| **VS Code chatSessions** | `%AppData%/Code/User/workspaceStorage/*/chatSessions/*.json` | Copilot Gespräche |
| **Projekt-Dateien** | `nova-knowledge/projects/clients/*/` | Meeting-Notes, TODOs |
| **KW-Summaries** | `nova-knowledge/operations/worklog/YYYY/KWXX.md` | Outlook/Tempo Exports |

---

## Schritt 1: Git Commits extrahieren

```bash
# Alle Repos durchsuchen (Datum anpassen)
cd /e/Dev/nova-knowledge
git log --oneline --after="2026-02-09" --before="2026-02-17" --format="%ad %s" --date=format:"%Y-%m-%d %H:%M"

cd /e/Dev/nova-server
git log --oneline --after="2026-02-09" --before="2026-02-17" --format="%ad %s" --date=format:"%Y-%m-%d %H:%M"

cd /e/Dev/NOVA
git log --oneline --after="2026-02-09" --before="2026-02-17" --format="%ad %s" --date=format:"%Y-%m-%d %H:%M"
```

---

## Schritt 2: Codex CLI Sessions auswerten

```bash
# Sessions finden
ls -la ~/.codex/sessions/2026/02/

# User-Inputs extrahieren (mit Timestamps aus Dateinamen)
for f in ~/.codex/sessions/2026/02/1*/*.jsonl; do 
  ts=$(basename "$f" | grep -oP '2026-02-\d{2}T\d{2}-\d{2}')
  echo "$ts: $(grep -h '"type":"input_text"' "$f" 2>/dev/null | \
    grep -oP '"text":"[^"]{10,80}"' | head -1 | \
    sed 's/"text":"//;s/"$//' | \
    grep -v 'permissions\|collaboration\|AGENTS\|environment\|Context from')"
done 2>/dev/null | grep -v ": $"
```

**History (falls vorhanden):**
```bash
cat ~/.codex/history.jsonl
```

---

## Schritt 3: VS Code Copilot Sessions

```bash
# chatSessions mit Datum finden
find "%AppData%/Code/User/workspaceStorage" -path "*/chatSessions/*.json" -mtime -10 -exec ls -la {} \;

# Erste User-Message pro Session extrahieren
find "%AppData%/Code/User/workspaceStorage" -name "*.json" -path "*/chatSessions/*" -mtime -10 \
  -exec head -c 1500 {} \; 2>/dev/null | grep -o '"text": "[^"]*"' | head -20
```

---

## Schritt 4: Projekt-Dateien durchsuchen

```bash
# Nach Datums-Referenzen in Client-Projekten suchen
grep -r "2026-02-1[0-7]" /e/Dev/nova-knowledge/projects/clients/*/

# Meeting-Notes finden
find /e/Dev/nova-knowledge/projects -name "*.md" -mtime -10 | xargs grep -l "Meeting\|Abstimmung\|Call"
```

---

## Schritt 5: WORKLOG Format

```markdown
## YYYY-MM-DD (Wochentag) - KWXX

- HH:MM Beschreibung der Aktivität. (TAG)
- Beschreibung ohne Zeit falls unbekannt. (TAG)
```

**Tags:** NOVA, NOVA-SERVER, HOMELAB, CODEX, KUNDE-A, KUNDE-B, PERSONAL, OPS

---

## Multi-Laptop Sync

Falls auf anderen Geräten gearbeitet wurde:

1. **Git Repos remote prüfen:**
   ```bash
   git fetch --all
   git log origin/main --oneline --after="2026-02-09" --format="%ad %s" --date=format:"%Y-%m-%d %H:%M"
   ```

2. **Codex Sessions sync (falls Cloud-Sync aktiv):**
   - Check: `~/.codex/` auf anderen Maschinen
   - Oder: OneDrive/Dropbox sync prüfen

3. **VS Code Settings Sync:**
   - Falls aktiviert: Remote chatSessions via GitHub Gist

---

## Bekannte Speicherorte

| Tool | Windows Pfad |
|------|--------------|
| Codex CLI | `C:\Users\<user>\.codex\sessions\` |
| VS Code Copilot | `%AppData%\Code\User\workspaceStorage\*\chatSessions\` |
| VS Code Logs | `%AppData%\Code\logs\*\exthost\GitHub.copilot-chat\` |
| ChatGPT | Kein lokaler Cache - Export via chatgpt.com Settings |

---

## Hinweise

- Codex CLI wurde erst ab **2026-02-12** installiert
- chatSessions enthalten nur First-Prompt leicht extrahierbar, Rest ist tief nested
- KW-Summaries (operations/worklog/YYYY/) brauchen manuellen Outlook/Tempo Export
