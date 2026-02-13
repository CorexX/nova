#!/usr/bin/env python3
"""
Skill: Summarize Day / Close Day
Liest alle Copilot Sessions des Tages und fasst sie zusammen.
Mit --close-day: Ordnet Zeit Tickets zu und erstellt Buchungsvorschlag.

Usage:
    python summarize_day.py [--date YYYY-MM-DD] [--raw] [--llm] [--write]
    python summarize_day.py --close-day        # Tagesabschluss mit Ticket-Zuordnung

Examples:
    python summarize_day.py                    # Einfache Übersicht
    python summarize_day.py --date 2026-02-08  # Bestimmtes Datum
    python summarize_day.py --llm              # LLM-Zusammenfassung
    python summarize_day.py --llm --write      # Direkt ins WORKLOG schreiben
    python summarize_day.py --close-day        # Ticket-Buchungsvorschlag
    python summarize_day.py --close-day --write # Buchung + WORKLOG schreiben
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# Logging Setup
logger = logging.getLogger("summarize_day")

def setup_logging(verbose: bool = False):
    """Konfiguriert Logging basierend auf --verbose Flag."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(handler)
    logger.setLevel(level)

# Load .env from nova-core
try:
    from dotenv import load_dotenv
    env_path = Path(os.getenv("NOVA_CORE_ROOT", Path(__file__).resolve().parent.parent)) / ".env"
    load_dotenv(env_path)
except ImportError:
    pass


# =============================================================================
# CONSTANTS
# =============================================================================


def get_nova_root() -> Path:
    """Findet das NOVA Workspace Root."""
    raw = os.getenv("NOVA_WORKSPACE_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return get_core_root().parent


def get_core_root() -> Path:
    """Findet das nova-core Root."""
    raw = os.getenv("NOVA_CORE_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return Path(__file__).resolve().parent.parent


def get_knowledge_root() -> Path:
    """Findet das nova-knowledge Root."""
    raw = os.getenv("NOVA_KNOWLEDGE_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return get_nova_root() / "nova-knowledge"


def load_tickets() -> dict:
    """
    Lädt TICKETS.md und parst die aktiven Tickets.
    
    Returns:
        Dict mit Ticket-ID als Key und Ticket-Info als Value
    """
    tickets_path = get_knowledge_root() / "TICKETS.md"
    
    if not tickets_path.exists():
        return {}
    
    content = tickets_path.read_text(encoding="utf-8")
    tickets = {}
    
    # Parse die Tabelle: | Ticket | Projekt | Beschreibung | Budget | Verbraucht | Rest |
    import re
    table_pattern = r"\|\s*([A-Z]+-[A-Z0-9]+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|"
    
    for match in re.finditer(table_pattern, content):
        ticket_id = match.group(1).strip()
        tickets[ticket_id] = {
            "projekt": match.group(2).strip(),
            "beschreibung": match.group(3).strip(),
            "budget": match.group(4).strip(),
            "verbraucht": match.group(5).strip(),
            "rest": match.group(6).strip(),
        }
    
    return tickets


def get_session_storage_path() -> Path:
    """
    Findet den VS Code workspaceStorage Pfad.
    Sessions liegen in: %APPDATA%/Code/User/workspaceStorage/{workspaceId}/chatSessions/
    """
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', '')) / "Code" / "User" / "workspaceStorage"
    else:  # macOS
        base = Path.home() / "Library" / "Application Support" / "Code" / "User" / "workspaceStorage"
    
    # Linux fallback
    if not base.exists():
        base = Path.home() / ".config" / "Code" / "User" / "workspaceStorage"
    
    return base


# =============================================================================
# SESSION PARSING
# =============================================================================

def get_session_files(target_date: date) -> list[Path]:
    """
    Findet alle Session-Dateien die am Zieldatum modifiziert wurden.
    
    Unterstützt beide Formate:
    - .jsonl (älteres Event-basiertes Format)
    - .json (neueres Single-Object Format)
    
    Args:
        target_date: Das Datum für das Sessions gesucht werden
        
    Returns:
        Liste von Session-Dateipfaden (.jsonl oder .json)
    """
    start = time.time()
    base_path = get_session_storage_path()
    logger.debug(f"Session storage path: {base_path}")
    
    if not base_path.exists():
        logger.warning(f"Base path does not exist: {base_path}")
        return []
    
    sessions = []
    workspace_count = 0
    checked_files = 0
    
    # Durchsuche alle Workspace-Ordner
    workspace_dirs = list(base_path.iterdir())
    logger.debug(f"Found {len(workspace_dirs)} workspace directories to scan")
    
    for workspace_dir in workspace_dirs:
        if not workspace_dir.is_dir():
            continue
        
        workspace_count += 1
        chat_sessions_dir = workspace_dir / "chatSessions"
        if not chat_sessions_dir.exists():
            continue
        
        logger.debug(f"Scanning: {chat_sessions_dir}")
        
        # Finde alle Session-Dateien (.jsonl und .json)
        for pattern in ["*.jsonl", "*.json"]:
            for session_file in chat_sessions_dir.glob(pattern):
                checked_files += 1
                # Check modification date
                try:
                    mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                    if mtime.date() == target_date:
                        logger.debug(f"Match: {session_file.name} (mtime: {mtime})")
                        sessions.append(session_file)
                except OSError as e:
                    logger.warning(f"Cannot stat {session_file}: {e}")
    
    elapsed = time.time() - start
    logger.info(f"Scanned {workspace_count} workspaces, {checked_files} files in {elapsed:.2f}s → {len(sessions)} sessions for {target_date}")
    
    return sessions


def parse_session_file(session_file: Path) -> dict:
    """
    Parst eine Session Datei (.jsonl oder .json Format).
    
    Args:
        session_file: Pfad zur Session-Datei
        
    Returns:
        Dictionary mit extrahierten Informationen
    """
    start = time.time()
    logger.debug(f"Parsing: {session_file.name} ({session_file.stat().st_size / 1024:.1f} KB)")
    
    session_info = {
        "id": session_file.stem,
        "title": None,
        "model": None,
        "agent": None,
        "prompts": [],              # User prompts mit vollem Kontext
        "thinking_blocks": [],      # AI Denkprozesse
        "tools_used": set(),        # Verwendete Tools
        "files_read": set(),        # Gelesene Dateien
        "files_modified": set(),    # Bearbeitete Dateien
        "terminal_commands": [],    # Terminal Commands
        "start_time": None,
        "end_time": None,
        "creation_date": None,
        "request_count": 0,
    }
    
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            if not content:
                return session_info
            
            # Detect format: .json (single object) vs .jsonl (line-delimited)
            if session_file.suffix == ".json" or content.startswith("{"):
                # Single JSON object format (newer VS Code versions)
                try:
                    data = json.loads(content)
                    parse_json_session(data, session_info)
                except json.JSONDecodeError as e:
                    session_info["error"] = f"JSON parse error: {e}"
            else:
                # JSONL format (older VS Code versions)
                for line in content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        process_session_event(event, session_info)
                    except json.JSONDecodeError:
                        continue
                        
    except Exception as e:
        session_info["error"] = str(e)
        logger.warning(f"Error parsing {session_file.name}: {e}")
    
    # Convert sets to lists for JSON serialization
    session_info["tools_used"] = list(session_info["tools_used"])
    session_info["files_read"] = list(session_info["files_read"])
    session_info["files_modified"] = list(session_info["files_modified"])
    
    # Calculate duration
    if session_info["start_time"] and session_info["end_time"]:
        duration_ms = session_info["end_time"] - session_info["start_time"]
        session_info["duration_minutes"] = round(duration_ms / 60000, 1)
    
    elapsed = time.time() - start
    logger.debug(f"Parsed {session_file.name} in {elapsed:.3f}s ({session_info['request_count']} requests)")
    
    return session_info


def parse_json_session(data: dict, session_info: dict) -> None:
    """
    Parst das neuere .json Session-Format (single JSON object).
    
    Args:
        data: Das geparste JSON-Objekt
        session_info: Dictionary zum Befüllen
    """
    # Basic metadata
    session_info["title"] = data.get("customTitle")
    session_info["creation_date"] = data.get("creationDate")
    
    # Requests
    requests = data.get("requests", [])
    session_info["request_count"] = len(requests)
    
    for i, req in enumerate(requests):
        # Model & Agent (from first request)
        if i == 0:
            session_info["model"] = req.get("modelId")
            agent = req.get("agent")
            if isinstance(agent, dict):
                session_info["agent"] = agent.get("id")
            elif isinstance(agent, str):
                session_info["agent"] = agent
        
        # Timestamps
        ts = req.get("timestamp")
        if ts:
            if session_info["start_time"] is None:
                session_info["start_time"] = ts
            session_info["end_time"] = ts
        
        # User message
        msg = req.get("message", {})
        if isinstance(msg, dict):
            text = msg.get("text", "")
        elif isinstance(msg, str):
            text = msg
        else:
            text = ""
            
        if text:
            prompt_text = text[:1500]
            if len(text) > 1500:
                prompt_text += "..."
            session_info["prompts"].append(prompt_text)
        
        # Response items
        for resp_item in req.get("response", []):
            if not isinstance(resp_item, dict):
                continue
            
            tool_id = resp_item.get("toolId", "")
            if tool_id:
                tool_name = tool_id.replace("copilot_", "").replace("_", " ")
                session_info["tools_used"].add(tool_name)
            
            # File edits
            resp_kind = resp_item.get("kind")
            if resp_kind == "textEditGroup":
                uri = resp_item.get("uri", {})
                if isinstance(uri, dict):
                    path = uri.get("path", "")
                else:
                    path = str(uri)
                if path:
                    session_info["files_modified"].add(path)
            
            # Terminal commands
            if resp_kind == "terminalCommand":
                cmd = resp_item.get("command", "")
                if cmd:
                    session_info["terminal_commands"].append(cmd[:400])


def process_session_event(event: dict, session_info: dict) -> None:
    """
    Verarbeitet ein Session Event und extrahiert maximalen Kontext.
    
    Args:
        event: Das JSON Event
        session_info: Dictionary zum Befüllen
    """
    kind = event.get("kind")
    
    # kind 0 = Initial session state
    if kind == 0:
        v = event.get("v", {})
        session_info["title"] = v.get("customTitle")
        session_info["creation_date"] = v.get("creationDate")
        
        requests = v.get("requests", [])
        session_info["request_count"] = len(requests)
        
        # Extract all requests
        for i, req in enumerate(requests):
            # Model & Agent (from first request)
            if i == 0:
                session_info["model"] = req.get("modelId")
                agent = req.get("agent")
                if isinstance(agent, dict):
                    session_info["agent"] = agent.get("id")
                elif isinstance(agent, str):
                    session_info["agent"] = agent
            
            # Timestamps
            ts = req.get("timestamp")
            if ts:
                if session_info["start_time"] is None:
                    session_info["start_time"] = ts
                session_info["end_time"] = ts  # Last request time
            
            # User message - keep more context
            msg = req.get("message", {})
            text = msg.get("text", "")
            if text:
                # Keep more of the prompt (1500 chars für Kommunikationsanalyse)
                prompt_text = text[:1500]
                if len(text) > 1500:
                    prompt_text += "..."
                session_info["prompts"].append(prompt_text)
            
            # Extract from response items
            for resp_item in req.get("response", []):
                if not isinstance(resp_item, dict):
                    continue
                
                resp_kind = resp_item.get("kind")
                tool_id = resp_item.get("toolId", "")
                
                # Tool usage
                if tool_id:
                    tool_name = tool_id.replace("copilot_", "").replace("_", " ")
                    session_info["tools_used"].add(tool_name)
                
                # File edits
                if resp_kind == "textEditGroup":
                    uri = resp_item.get("uri", {})
                    path = uri.get("path", "") or uri.get("fsPath", "")
                    if path:
                        session_info["files_modified"].add(path)
                
                # Thinking blocks - extract more content
                if resp_kind == "thinking":
                    val = resp_item.get("value", "").strip()
                    if val and len(val) > 30:
                        # Take up to 1500 chars per thinking block (für Kommunikationsanalyse)
                        summary = val[:1500]
                        # Try to end at a sentence
                        for end in [". ", "! ", "? ", "\n\n"]:
                            pos = summary.rfind(end)
                            if pos > 100:
                                summary = summary[:pos + 1]
                                break
                        if summary.strip():
                            session_info["thinking_blocks"].append(summary.strip())
                
                # Tool invocations - extract files read and terminal commands
                if resp_kind == "toolInvocationSerialized":
                    tool_id = resp_item.get("toolId", "")
                    
                    # Get pastTenseMessage (dict with 'value' key)
                    past_msg = resp_item.get("pastTenseMessage", {})
                    if isinstance(past_msg, dict):
                        past_text = past_msg.get("value", "")
                    else:
                        past_text = str(past_msg)
                    
                    # Extract file paths from pastTenseMessage
                    if "readFile" in tool_id or "read_file" in tool_id:
                        # Format: "Read [](file:///path), lines X to Y"
                        import re
                        match = re.search(r'file:///([^)#\s]+)', past_text)
                        if match:
                            file_path = match.group(1).replace('%3A', ':').replace('%20', ' ')
                            session_info["files_read"].add(file_path)
                    
                    # Extract find/search results
                    if "findFiles" in tool_id or "find_files" in tool_id:
                        result_details = resp_item.get("resultDetails", [])
                        if isinstance(result_details, list):
                            for rd in result_details[:5]:
                                if isinstance(rd, dict):
                                    path = rd.get("fsPath") or rd.get("path", "")
                                    if path:
                                        session_info["files_read"].add(path)
                    
                    # Extract grep search patterns
                    if "grep" in tool_id.lower():
                        inv_msg = resp_item.get("invocationMessage", {})
                        if isinstance(inv_msg, dict):
                            inv_text = inv_msg.get("value", "")
                            if "Searching" in inv_text:
                                session_info["terminal_commands"].append(f"grep: {inv_text[:100]}")
                    
                    # Terminal commands
                    if "terminal" in tool_id.lower() or "run_in_terminal" in tool_id:
                        if past_text:
                            session_info["terminal_commands"].append(past_text[:400])
                
                # toolSpecificData - terminal output, etc
                tsd = resp_item.get("toolSpecificData", {})
                if isinstance(tsd, dict):
                    if tsd.get("kind") == "terminal":
                        # Could extract terminal output here if needed
                        pass
                
                # Content references - files explicitly mentioned
                content_refs = req.get("contentReferences", [])
                for ref in content_refs:
                    if isinstance(ref, dict):
                        ref_data = ref.get("reference", {})
                        if isinstance(ref_data, dict):
                            path = ref_data.get("path", "") or ref_data.get("fsPath", "")
                            if path:
                                session_info["files_read"].add(path)


# =============================================================================
# SUMMARIZATION
# =============================================================================

def get_llm_client():
    """
    Erstellt einen Claude Client via Azure AI Foundry.
    Returns tuple: (client, error_message)
    """
    try:
        from anthropic import AnthropicFoundry
    except ImportError:
        return None, "ERROR: anthropic package not installed. Run: pip install anthropic"
    
    endpoint = os.getenv('NOVA_AZURE_ENDPOINT')
    api_key = os.getenv('NOVA_AZURE_API_KEY')
    
    if not endpoint or not api_key:
        return None, "ERROR: NOVA_AZURE_ENDPOINT and NOVA_AZURE_API_KEY must be set in nova-core/.env"
    
    return AnthropicFoundry(
        api_key=api_key,
        base_url=endpoint
    ), None


def extract_raw_conversation(session_file: Path) -> str:
    """
    Extrahiert nur die Konversation aus einer Session - keine Tool-Outputs.
    
    Returns:
        Formatierter Konversationstext
    """
    try:
        data = json.loads(open(session_file, 'r', encoding='utf-8').readline())
        if data.get('kind') != 0:
            return ""
        
        v = data['v']
        title = v.get('customTitle', 'Untitled')
        creation_date = v.get('creationDate')
        
        # Format time
        time_str = ""
        if creation_date:
            try:
                dt = datetime.fromtimestamp(creation_date / 1000)
                time_str = f" ({dt.strftime('%H:%M')})"
            except:
                pass
        
        lines = [f"# {title}{time_str}"]
        
        for req in v.get('requests', []):
            # User message
            msg = req.get('message', {}).get('text', '')
            if msg:
                lines.append(f"\nUSER: {msg}")
            
            # Process response items
            ai_parts = []
            thinking_parts = []
            tool_actions = []
            
            for item in req.get('response', []):
                if not isinstance(item, dict):
                    continue
                
                kind = item.get('kind')
                
                # AI text response (kind=None with value)
                if kind is None and 'value' in item:
                    val = item.get('value', '')
                    if val:
                        ai_parts.append(val)
                
                # Thinking blocks - full content
                elif kind == 'thinking':
                    val = item.get('value', '').strip()
                    if val:
                        thinking_parts.append(val)
                
                # Tool actions (just what was done, not the output)
                elif kind == 'toolInvocationSerialized':
                    past_msg = item.get('pastTenseMessage', {})
                    if isinstance(past_msg, dict):
                        action = past_msg.get('value', '')
                        if action:
                            # Clean up file:/// URIs
                            action = action.replace('file:///', '').replace('%3A', ':').replace('%20', ' ')
                            tool_actions.append(action[:500])
            
            # Add thinking (mehr Kontext für Kommunikationsanalyse)
            if thinking_parts:
                # Erweitert auf 1500 chars pro Block, max 10 Blocks (~15k chars)
                thinking_summary = "\n---\n".join([t[:1500] for t in thinking_parts[:10]])
                lines.append(f"\nTHINKING:\n{thinking_summary}")
            
            # Add tool actions
            if tool_actions:
                lines.append(f"\nACTIONS: {' | '.join(tool_actions[:15])}")
            
            # Add AI response
            if ai_parts:
                ai_text = "".join(ai_parts)
                lines.append(f"\nAI: {ai_text}")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"# Error parsing session: {e}"


def summarize_with_llm(sessions_data: list[dict], target_date: date, session_files: list[Path] = None) -> str:
    """
    Nutzt Claude um die Sessions sinnvoll zusammenzufassen.
    Schickt rohe Konversation + aggregierte Metadaten.
    """
    client, error = get_llm_client()
    if not client:
        return error or "LLM Client konnte nicht erstellt werden"
    
    model = os.getenv('NOVA_MODEL', 'claude-opus-4-6')
    
    # Extract raw conversations from session files
    conversations = []
    if session_files:
        for sf in session_files:
            conv = extract_raw_conversation(sf)
            if conv and len(conv) > 50:  # Skip empty sessions
                conversations.append(conv)
    
    if not conversations:
        return "Keine Konversationen gefunden."
    
    # Aggregate metadata from sessions_data
    all_files_read = set()
    all_files_modified = set()
    all_tools = set()
    all_terminal_cmds = []
    total_requests = 0
    total_duration = 0
    
    for session in sessions_data:
        all_files_read.update(session.get("files_read", []))
        all_files_modified.update(session.get("files_modified", []))
        all_tools.update(session.get("tools_used", []))
        all_terminal_cmds.extend(session.get("terminal_commands", []))
        total_requests += session.get("request_count", 0)
        total_duration += session.get("duration_minutes", 0)
    
    # Format metadata
    files_read_str = "\n".join([f"  - {Path(f).name}" for f in sorted(all_files_read)[:20]]) or "  (keine)"
    files_modified_str = "\n".join([f"  - {Path(f).name}" for f in sorted(all_files_modified)[:15]]) or "  (keine)"
    tools_str = ", ".join(sorted(all_tools)[:15]) or "(keine)"
    terminal_str = "\n".join([f"  - {cmd[:100]}" for cmd in all_terminal_cmds[:10]]) or "  (keine)"
    
    # Join all conversations
    all_conversations = "\n\n" + "="*50 + "\n\n".join(conversations)
    
    weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    weekday = weekdays[target_date.weekday()]
    
    prompt = f"""Analysiere die folgenden Copilot-Konversationen vom {target_date.strftime('%Y-%m-%d')} ({weekday}).

## METADATEN
- Sessions: {len(sessions_data)}
- Requests gesamt: {total_requests}
- Geschätzte Arbeitszeit: {round(total_duration)} Minuten

### Gelesene Dateien:
{files_read_str}

### Bearbeitete Dateien:
{files_modified_str}

### Verwendete Tools: {tools_str}

### Terminal Commands:
{terminal_str}

## KONVERSATIONS-FORMAT
- USER: Was der Benutzer gefragt/angewiesen hat
- THINKING: Interne Überlegungen des AI
- ACTIONS: Ausgeführte Tool-Aktionen
- AI: Antworten an den Benutzer

---

## AUFGABE
Erstelle einen detaillierten WORKLOG-Eintrag mit folgendem Format:

```markdown
## {target_date.strftime('%Y-%m-%d')} ({weekday})

### Übersicht
[2-3 Sätze: Was wurde heute insgesamt erreicht? Hauptfokus?]

### Aktivitäten
- [Gruppierte Hauptaktivität 1 mit konkreten Details]
- [Gruppierte Hauptaktivität 2 mit konkreten Details]
- ...

### Bearbeitete Dateien
- `datei1.py` - [was wurde gemacht]
- `datei2.md` - [was wurde gemacht]

### Erkenntnisse & Learnings
- [Technische Erkenntnis oder gelerntes Konzept]
- [Interessante Lösung oder Pattern]

### Offene Punkte / Nächste Schritte
- [ ] [Was noch zu tun ist]
- [ ] [Follow-up für morgen]

### Kommunikations-Feedback
[Analysiere die Qualität der Zusammenarbeit User ↔ Agent]

**Schwierigkeiten:**
- [Wo gab es Missverständnisse? User musste korrigieren/wiederholen]
- [Hat Agent Annahmen getroffen statt zu fragen?]
- [Fehlender Kontext der zu Problemen führte]

**Was gut funktioniert hat:**
- [Erfolgreiche Kommunikationsmuster]
- [Effiziente Anweisungen die sofort verstanden wurden]

**Verbesserungsvorschläge:**
- [Konkrete Tipps für bessere Zusammenarbeit]
```

Schreibe auf Deutsch. Sei detailliert aber strukturiert. Erwähne konkrete Dateinamen und Technologien.

WICHTIG für Kommunikations-Feedback: Sei ehrlich und konkret. Nenne spezifische Beispiele aus den Konversationen. Dieses Feedback hilft User und Agent, sich besser aufeinander einzustellen.

---

KONVERSATIONEN:
{all_conversations}"""

    try:
        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        return response.content[0].text
    except Exception as e:
        print(f"ERROR: LLM call failed: {e}")
        return ""


def close_day_with_llm(sessions_data: list[dict], target_date: date, session_files: list[Path] = None) -> str:
    """
    Tagesabschluss mit Ticket-Zuordnung.
    Analysiert Sessions und ordnet Zeit den Tickets zu.
    
    Returns:
        Formatierter Buchungsvorschlag
    """
    client, error = get_llm_client()
    if not client:
        return error or "❌ Kein LLM Client verfügbar (ANTHROPIC_API_KEY?)"
    
    model = os.getenv('NOVA_MODEL', 'claude-opus-4-6')
    
    # Extract raw conversations
    conversations = []
    if session_files:
        for sf in session_files:
            conv = extract_raw_conversation(sf)
            if conv and len(conv) > 50:
                conversations.append(conv)
    
    if not conversations:
        return "Keine Konversationen gefunden."
    
    # Aggregate metadata from sessions_data
    all_files_read = set()
    all_files_modified = set()
    all_tools = set()
    all_terminal_cmds = []
    total_requests = 0
    total_duration = 0
    
    for session in sessions_data:
        all_files_read.update(session.get("files_read", []))
        all_files_modified.update(session.get("files_modified", []))
        all_tools.update(session.get("tools_used", []))
        all_terminal_cmds.extend(session.get("terminal_commands", []))
        total_requests += session.get("request_count", 0)
        total_duration += session.get("duration_minutes", 0)
    
    # Format metadata
    files_modified_str = "\n".join([f"  - {Path(f).name}" for f in sorted(all_files_modified)[:15]]) or "  (keine)"
    
    all_conversations = "\n\n" + "="*50 + "\n\n".join(conversations)
    
    # Load tickets
    tickets = load_tickets()
    tickets_info = "KEINE TICKETS GEFUNDEN" if not tickets else "\n".join([
        f"- {tid}: {t['projekt']} - {t['beschreibung']} (Rest: {t['rest']})"
        for tid, t in tickets.items()
    ])
    
    weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    weekday = weekdays[target_date.weekday()]
    
    prompt = f"""Analysiere die Copilot-Konversationen vom {target_date.strftime('%Y-%m-%d')} ({weekday}) und erstelle einen ZEITBUCHUNGS-VORSCHLAG.

## METADATEN
- Sessions: {len(sessions_data)}
- Requests gesamt: {total_requests}
- Geschätzte aktive Zeit: {round(total_duration)} Minuten

### Bearbeitete Dateien:
{files_modified_str}

## Aktive Tickets:
{tickets_info}

## Aufgabe:
1. Identifiziere alle Aktivitäten aus den Konversationen
2. Schätze die Dauer jeder Aktivität (in Stunden, z.B. 0.5h, 1h, 2h)
   - Nutze die Metadaten als Hinweis, aber schätze realistisch
   - Bedenke: Zwischen Requests liegt oft Nachdenk-/Testzeit
3. Ordne jede Aktivität einem Ticket zu:
   - Wenn Ticket-ID erwähnt → direkt zuordnen
   - Wenn Kundenname/Projekt erkennbar → passendes Ticket vorschlagen
   - Wenn internes NOVA-Thema → INT-NOVA
   - Wenn nicht zuordenbar → "UNZUGEORDNET" + Vorschlag für neues Ticket
4. Prüfe ob Gesamtzeit realistisch ist (Tagessoll: ~8h)

## Output-Format:
```markdown
## Tagesabschluss {target_date.strftime('%Y-%m-%d')} ({weekday})

### Übersicht
[1-2 Sätze: Was war der Fokus heute?]

### Aktivitäten (detailliert)
- [Aktivität 1 mit konkreten Details, bearbeitete Dateien]
- [Aktivität 2 mit konkreten Details]

### Zeitvorschlag

| Ticket | Aktivität | Std |
|--------|-----------|----:|
| XXX-123 | ... | Xh |
| ... | ... | ... |
| **Gesamt** | | **Xh** |

### Erkenntnisse
- [Was wurde gelernt/erreicht]

### Warnungen (falls vorhanden)
- ⚠️ ...

### Neue Tickets (falls unzugeordnet)
Für unzugeordnete Aktivitäten:
- Vorschlag: INT-XXX "Titel" für [Aktivität]
```

Schreibe auf Deutsch. Sei präzise bei der Zeitschätzung.

---

KONVERSATIONEN:
{all_conversations}"""

    try:
        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3500,
        )
        return response.content[0].text
    except Exception as e:
        print(f"ERROR: LLM call failed: {e}")
        return ""


def write_to_worklog(content: str, worklog_path: Path) -> bool:
    """
    Hängt Inhalt ans WORKLOG.md an.
    """
    try:
        with open(worklog_path, 'a', encoding='utf-8') as f:
            f.write("\n\n" + content)
        return True
    except Exception as e:
        print(f"ERROR: Could not write to WORKLOG: {e}")
        return False


def summarize_sessions(sessions_data: list[dict]) -> str:
    """
    Fasst alle Sessions zusammen.
    
    Args:
        sessions_data: Liste von Session-Dicts
        
    Returns:
        Formatierter Summary-String
    """
    if not sessions_data:
        return "Keine Copilot Sessions für diesen Tag gefunden."
    
    lines = []
    lines.append(f"## Copilot Sessions ({len(sessions_data)} gefunden)")
    lines.append("")
    
    for i, session in enumerate(sessions_data, 1):
        title = session.get("title")
        prompts = session.get("prompts", [])
        tools = session.get("tools_used", [])
        files = session.get("files_modified", [])
        
        # Use title if available, otherwise first prompt
        topic = title or "Unbekannt"
        if not title and prompts:
            topic = prompts[0][:80]
            if len(prompts[0]) > 80:
                topic += "..."
        
        # Format time
        time_str = ""
        if session.get("creation_date"):
            try:
                ts = session["creation_date"]
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts / 1000)  # JS timestamp in ms
                    time_str = f" ({dt.strftime('%H:%M')})"
            except:
                pass
        
        lines.append(f"### Session {i}{time_str}")
        lines.append(f"- **Thema**: {topic}")
        
        # Show all thinking blocks
        thinking_blocks = session.get("thinking_blocks", [])
        if thinking_blocks:
            lines.append(f"- **Kontext**:")
            for t in thinking_blocks[:5]:  # Max 5 blocks
                lines.append(f"  - {t}")
        
        if prompts:
            lines.append(f"- **Prompts**: {len(prompts)}")
        
        if tools:
            lines.append(f"- **Tools**: {', '.join(list(tools)[:5])}")
        
        if files:
            # Show only filenames, not full paths
            filenames = [Path(f).name for f in list(files)[:5]]
            lines.append(f"- **Dateien**: {', '.join(filenames)}")
        
        lines.append("")
    
    return "\n".join(lines)


def generate_worklog_entry(sessions_data: list[dict], target_date: date) -> str:
    """
    Generiert einen WORKLOG-Eintrag im erwarteten Format.
    
    Args:
        sessions_data: Liste von Session-Dicts
        target_date: Das Datum
        
    Returns:
        WORKLOG-formatierter String
    """
    if not sessions_data:
        return ""
    
    weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    weekday = weekdays[target_date.weekday()]
    
    lines = []
    lines.append(f"## {target_date.strftime('%Y-%m-%d')} ({weekday})")
    lines.append("")
    
    for session in sessions_data:
        title = session.get("title")
        prompts = session.get("prompts", [])
        
        # Use title if available, otherwise first prompt
        topic = title or "Copilot Session"
        if not title and prompts:
            topic = prompts[0][:60]
            if len(prompts[0]) > 60:
                topic += "..."
        
        # Use creation time
        time_str = "??:??"
        if session.get("creation_date"):
            try:
                ts = session["creation_date"]
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts / 1000)  # JS timestamp in ms
                    time_str = dt.strftime("%H:%M")
            except:
                pass
        
        lines.append(f"- {time_str} {topic} (TICKET-???)")
    
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

def main():
    # Fix Windows encoding
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    parser = argparse.ArgumentParser(
        description="Fasst Copilot Sessions des Tages zusammen."
    )
    parser.add_argument(
        "--date", "-d",
        type=str,
        help="Datum im Format YYYY-MM-DD (default: heute)"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Zeige rohe Session-Daten als JSON"
    )
    parser.add_argument(
        "--worklog",
        action="store_true",
        help="Generiere WORKLOG-Format statt Summary"
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Nutze LLM (Claude) für intelligente Zusammenfassung"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Schreibe direkt ins WORKLOG.md (nur mit --llm oder --close-day)"
    )
    parser.add_argument(
        "--close-day",
        action="store_true",
        dest="close_day",
        help="Tagesabschluss: Zeit auf Tickets zuordnen"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Zeige detailliertes Logging (Debug-Modus)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    logger.debug("Starting summarize_day")
    
    # Parse date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Ungültiges Datum: {args.date}")
            return
    else:
        target_date = date.today()
    
    # Find sessions
    session_files = get_session_files(target_date)
    
    if not session_files:
        print(f"Keine Sessions für {target_date} gefunden.")
        print(f"Session-Ordner: {get_session_storage_path()}")
        return
    
    # Parse all sessions
    sessions_data = []
    for session_file in session_files:
        data = parse_session_file(session_file)
        if data.get("prompts") or data.get("title"):  # Include sessions with prompts or title
            sessions_data.append(data)
    
    # Sort by creation date
    sessions_data.sort(key=lambda x: x.get("creation_date") or 0)
    
    # Output
    if args.raw:
        print(json.dumps(sessions_data, indent=2, default=str))
    elif args.close_day:
        # Tagesabschluss mit Ticket-Zuordnung
        summary = close_day_with_llm(sessions_data, target_date, session_files)
        if summary:
            print(summary)
            if args.write:
                worklog_path = get_knowledge_root() / "WORKLOG.md"
                if worklog_path.exists():
                    if write_to_worklog(summary, worklog_path):
                        print(f"\n✓ Geschrieben nach {worklog_path}")
                else:
                    print(f"\nWORKLOG nicht gefunden: {worklog_path}")
    elif args.llm:
        summary = summarize_with_llm(sessions_data, target_date, session_files)
        if summary:
            print(summary)
            if args.write:
                worklog_path = get_knowledge_root() / "WORKLOG.md"
                if worklog_path.exists():
                    if write_to_worklog(summary, worklog_path):
                        print(f"\n✓ Geschrieben nach {worklog_path}")
                else:
                    print(f"\nWORKLOG nicht gefunden: {worklog_path}")
    elif args.worklog:
        print(generate_worklog_entry(sessions_data, target_date))
    else:
        print(summarize_sessions(sessions_data))


if __name__ == "__main__":
    main()
