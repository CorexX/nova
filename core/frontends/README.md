# NOVA Frontend Integration

> Wie man NOVA in verschiedenen Clients einbindet.

## Architektur

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚           CORE.md                   â”‚  â† Persona, Bootstrap, Tools
â”‚         PRINCIPLES.md               â”‚  â† Regeln, Scope (SSoT)
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                  â†‘
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚             â”‚             â”‚
â”Œâ”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚Copilotâ”‚    â”‚ Claude â”‚    â”‚  TUI   â”‚
â”‚VS Codeâ”‚    â”‚Desktop â”‚    â”‚ n8n    â”‚
â”‚       â”‚    â”‚  MCP   â”‚    â”‚ Custom â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Prinzip:** CORE.md ist die Single Source of Truth. Frontend-Adapter sind minimal.

---

## Andock-Modell (Core + Context Adapter)

NOVA Core bleibt unveraendert. Nur der Context Adapter wird pro Umgebung getauscht.

Minimaler Adapter-Output:

```json
{
  "context_id": "my-context",
  "current": "...",
  "tickets": [],
  "knowledge_paths": ["..."],
  "write_policy": {"append_only": ["WORKLOG.md"]},
  "search_provider": "local|remote"
}
```

Beispiele fuer Kontextquellen:
- lokale Vault (`nova-knowledge/`)
- anderes Repo
- Confluence/Jira/Git/DB via MCP/HTTP Adapter

---
## MCP-Clients (Claude Desktop, etc.)

MCP-Clients nutzen `nova_session_init()` automatisch:

```json
{
  "mcpServers": {
    "nova-skills": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "cwd": "/path/to/nova-core"
    }
  }
}
```

**Bootstrap:** `nova_session_init()` â†’ lÃ¤dt CORE.md + PRINCIPLES.md + CURRENT.md

---

## VS Code GitHub Copilot

Copilot liest `.github/copilot-instructions.md` automatisch.

Diese Datei ist ein Minimal-Adapter:
- Verweist auf CORE.md als Hauptquelle
- Instruiert `nova_session_init()` zu nutzen
- Fallback: Direktes Lesen von CORE.md

---

## Cursor / Windsurf

Analog zu Copilot - `.cursorrules` oder Ã¤hnliche Datei:

```markdown
Bei Session-Start: nova_session_init() aufrufen.
Fallback: Lies nova-core/core/CORE.md
```

---

## Eigene TUI / CLI

```python
# Beispiel: CORE.md als System-Prompt laden
from pathlib import Path

def get_system_prompt():
    core = Path("nova-core/core/CORE.md").read_text()
    principles = Path("nova-core/core/PRINCIPLES.md").read_text()
    return f"{core}\n\n---\n\n{principles}"
```

---

## n8n / Automatisierung

FÃ¼r n8n-Workflows mit LLM-Nodes:

1. **HTTP Request Node** â†’ CORE.md aus Git/local lesen
2. **Set Node** â†’ Als `system_prompt` setzen
3. **OpenAI/Claude Node** â†’ Mit System-Prompt nutzen

---

## Web App

```typescript
// Beispiel: React/Next.js
const CORE_MD_URL = '/api/nova/core';

async function getSystemPrompt() {
  const [core, principles] = await Promise.all([
    fetch(`${CORE_MD_URL}/CORE.md`).then(r => r.text()),
    fetch(`${CORE_MD_URL}/PRINCIPLES.md`).then(r => r.text())
  ]);
  return `${core}\n\n---\n\n${principles}`;
}
```

---

## Neue Frontends hinzufÃ¼gen

1. **Minimal-Adapter erstellen** (verweist auf CORE.md)
2. **Bootstrap sicherstellen** (`nova_session_init()` oder File-Read)
3. **Hier dokumentieren**

> Regel: Keine Logik in Adaptern. Alles in CORE.md + PRINCIPLES.md.

