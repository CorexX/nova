#!/usr/bin/env python3
"""
Tool: Find All Sessions
Findet und analysiert alle VS Code Copilot/Codex Sessions.

Usage:
    python find_all_sessions.py [--date YYYY-MM-DD] [--verbose]
"""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional


def get_session_storage_paths() -> list[Path]:
    """Findet alle moeglichen Session-Storage Pfade."""
    paths = []
    
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            # VS Code Standard
            paths.append(Path(appdata) / "Code" / "User" / "workspaceStorage")
            # VS Code Insiders
            paths.append(Path(appdata) / "Code - Insiders" / "User" / "workspaceStorage")
            # Cursor
            paths.append(Path(appdata) / "Cursor" / "User" / "workspaceStorage")
    else:
        # macOS
        paths.append(Path.home() / "Library" / "Application Support" / "Code" / "User" / "workspaceStorage")
        # Linux
        paths.append(Path.home() / ".config" / "Code" / "User" / "workspaceStorage")
    
    return [p for p in paths if p.exists()]


def find_sessions(target_date: Optional[date] = None) -> list[dict]:
    """
    Findet alle Session-Dateien, optional gefiltert nach Datum.
    
    Args:
        target_date: Optionales Datum fuer Filterung
        
    Returns:
        Liste von Session-Infos
    """
    sessions = []
    
    for base_path in get_session_storage_paths():
        print(f"Scanning: {base_path}", file=sys.stderr)
        
        for workspace_dir in base_path.iterdir():
            if not workspace_dir.is_dir():
                continue
            
            chat_dir = workspace_dir / "chatSessions"
            if not chat_dir.exists():
                continue
            
            # Workspace Info
            workspace_json = workspace_dir / "workspace.json"
            workspace_info = None
            if workspace_json.exists():
                try:
                    workspace_info = json.loads(workspace_json.read_text(encoding='utf-8'))
                except:
                    pass
            
            for session_file in chat_dir.glob("*"):
                if session_file.suffix not in ['.json', '.jsonl']:
                    continue
                
                try:
                    stat = session_file.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    
                    # Filter nach Datum
                    if target_date and mtime.date() != target_date:
                        continue
                    
                    session_info = {
                        "file": str(session_file),
                        "size_kb": round(stat.st_size / 1024, 1),
                        "modified": mtime.isoformat(),
                        "workspace": workspace_info.get("folder") if workspace_info else None,
                        "format": session_file.suffix,
                    }
                    
                    # Parse Session Content
                    content = session_file.read_text(encoding='utf-8', errors='ignore')
                    parsed = parse_session(content, session_file.suffix)
                    session_info.update(parsed)
                    
                    sessions.append(session_info)
                    
                except Exception as e:
                    print(f"Error: {session_file}: {e}", file=sys.stderr)
    
    return sessions


def parse_session(content: str, format: str) -> dict:
    """Parst Session-Inhalt."""
    result = {
        "title": None,
        "model": None,
        "agent": None,
        "request_count": 0,
        "user_messages": [],
        "tools_used": [],
        "files_touched": [],
    }
    
    if not content.strip():
        return result
    
    try:
        if format == ".json":
            data = json.loads(content)
            _extract_session_data(data, result)
                
        elif format == ".jsonl":
            lines = content.strip().split('\n')
            max_request_idx = 0
            
            for line in lines:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    kind = event.get("kind")
                    
                    # kind 0 = base session data
                    if kind == 0:
                        v = event.get("v", {})
                        _extract_session_data(v, result)
                    
                    # kind 1, 2 = incremental updates
                    # Track highest request index to count total requests
                    elif kind in (1, 2):
                        k = event.get("k", [])
                        if k and k[0] == "requests" and len(k) > 1:
                            idx = k[1]
                            if isinstance(idx, int):
                                max_request_idx = max(max_request_idx, idx + 1)
                        
                except json.JSONDecodeError:
                    continue
            
            # Update request count from incremental updates
            if max_request_idx > result["request_count"]:
                result["request_count"] = max_request_idx
                    
    except Exception as e:
        result["parse_error"] = str(e)
    
    return result


def _extract_session_data(data: dict, result: dict):
    """Extract session metadata from session object."""
    result["title"] = data.get("customTitle")
    
    creation = data.get("creationDate")
    if creation:
        try:
            result["creation_date"] = datetime.fromtimestamp(creation / 1000).isoformat()
        except:
            result["creation_date"] = str(creation)
    
    requests = data.get("requests", [])
    result["request_count"] = len(requests)
    
    for req in requests:
        # Model
        if not result["model"]:
            result["model"] = req.get("modelId")
        
        # Agent
        agent = req.get("agent")
        if agent:
            if isinstance(agent, dict):
                result["agent"] = agent.get("id")
            else:
                result["agent"] = str(agent)
        
        # User Message
        msg = req.get("message")
        if msg:
            text = msg.get("text", "")[:200]
            if text:
                result["user_messages"].append(text)
        
        # Tool Invocations from response
        response = req.get("response", {})
        if isinstance(response, dict):
            for item in response.get("result", {}).get("value", []):
                if isinstance(item, dict):
                    tool_ref = item.get("toolInvocations", [])
                    for tool in tool_ref:
                        if isinstance(tool, dict):
                            tool_name = tool.get("toolId") or tool.get("name")
                            if tool_name and tool_name not in result["tools_used"]:
                                result["tools_used"].append(tool_name)
                    
                    # Files
                    refs = item.get("references", [])
                    for ref in refs:
                        if isinstance(ref, dict):
                            uri = ref.get("uri", {})
                            if isinstance(uri, dict):
                                path = uri.get("path", "")
                                if path and path not in result["files_touched"]:
                                    result["files_touched"].append(path)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Find all VS Code sessions")
    parser.add_argument("--date", help="Filter by date (YYYY-MM-DD)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full details")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--no-empty", action="store_true", help="Hide sessions with 0 requests")
    args = parser.parse_args()
    
    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = date.today()
    
    print(f"\nSearching sessions for: {target_date}\n", file=sys.stderr)
    
    sessions = find_sessions(target_date)
    
    # Filter empty sessions
    if args.no_empty:
        sessions = [s for s in sessions if s.get('request_count', 0) > 0]
    
    if args.json:
        print(json.dumps(sessions, indent=2, default=str))
        return
    
    print(f"Found {len(sessions)} sessions\n")
    print("=" * 80)
    
    for i, s in enumerate(sessions, 1):
        print(f"\n[{i}] {s.get('title') or 'Untitled'}")
        print(f"    Model: {s.get('model') or 'unknown'} | Agent: {s.get('agent') or 'none'}")
        print(f"    Requests: {s.get('request_count')} | Size: {s.get('size_kb')} KB")
        print(f"    Modified: {s.get('modified')}")
        
        if s.get('workspace'):
            print(f"    Workspace: {s.get('workspace')}")
        
        if s.get('tools_used'):
            print(f"    Tools: {', '.join(s['tools_used'][:5])}")
        
        if args.verbose and s.get('user_messages'):
            print("    Messages:")
            for msg in s['user_messages'][:3]:
                print(f"      - {msg[:100]}...")
        
        if s.get('parse_error'):
            print(f"    ⚠️ Parse Error: {s.get('parse_error')}")
    
    print("\n" + "=" * 80)
    
    # Summary
    total_requests = sum(s.get('request_count', 0) for s in sessions)
    agents_used = set(s.get('agent') for s in sessions if s.get('agent'))
    models_used = set(s.get('model') for s in sessions if s.get('model'))
    
    print(f"\nSummary:")
    print(f"  Sessions: {len(sessions)}")
    print(f"  Total Requests: {total_requests}")
    print(f"  Agents: {', '.join(agents_used) or 'none'}")
    print(f"  Models: {', '.join(models_used) or 'unknown'}")


if __name__ == "__main__":
    main()
