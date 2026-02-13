#!/usr/bin/env python3
"""
Skill: Summarize Week
Liest alle Copilot Sessions der letzten Woche und fasst sie zusammen.
Nutzt summarize_day.py für die Basis-Funktionen.

Usage:
    python summarize_week.py                     # Aktuelle Woche (Mo-So)
    python summarize_week.py --last              # Letzte Woche
    python summarize_week.py --days 7            # Letzte 7 Tage
    python summarize_week.py --from 2026-02-03   # Ab bestimmtem Datum
    python summarize_week.py --llm               # Mit LLM-Zusammenfassung
    python summarize_week.py --llm --write       # Direkt ins WORKLOG schreiben

Examples:
    python summarize_week.py --last --llm        # Letzte Woche, LLM-Summary
    python summarize_week.py --days 5 --llm      # Letzte 5 Arbeitstage
"""

import argparse
import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

# Import from summarize_day
from summarize_day import (
    get_core_root,
    get_knowledge_root,
    get_nova_root,
    get_session_files,
    parse_session_file,
    extract_raw_conversation,
    get_llm_client,
    load_tickets,
    write_to_worklog,
)

# Load .env from nova-core
try:
    from dotenv import load_dotenv
    env_path = get_core_root() / ".env"
    load_dotenv(env_path)
except ImportError:
    pass


# =============================================================================
# WEEK DATA COLLECTION
# =============================================================================

def get_week_boundaries(reference_date: date, last_week: bool = False) -> tuple[date, date]:
    """
    Berechnet Wochengrenzen (Montag bis Sonntag).
    
    Args:
        reference_date: Referenzdatum
        last_week: Wenn True, nimm die vorherige Woche
        
    Returns:
        Tuple (start_date, end_date)
    """
    # Finde Montag dieser Woche
    days_since_monday = reference_date.weekday()
    monday = reference_date - timedelta(days=days_since_monday)
    
    if last_week:
        monday = monday - timedelta(days=7)
    
    sunday = monday + timedelta(days=6)
    
    return monday, sunday


def collect_week_sessions(start_date: date, end_date: date) -> dict[date, list]:
    """
    Sammelt alle Sessions für einen Datumsbereich.
    
    Args:
        start_date: Startdatum
        end_date: Enddatum
        
    Returns:
        Dict mit Datum als Key und Liste von (session_data, session_file) als Value
    """
    all_sessions = {}
    current = start_date
    
    while current <= end_date:
        session_files = get_session_files(current)
        if session_files:
            sessions = []
            for sf in session_files:
                data = parse_session_file(sf)
                if data.get("prompts") or data.get("title"):
                    sessions.append((data, sf))
            
            if sessions:
                # Sort by creation date
                sessions.sort(key=lambda x: x[0].get("creation_date") or 0)
                all_sessions[current] = sessions
        
        current += timedelta(days=1)
    
    return all_sessions


def aggregate_week_stats(week_sessions: dict[date, list]) -> dict:
    """
    Aggregiert Statistiken für die ganze Woche.
    
    Args:
        week_sessions: Dict mit Sessions pro Tag
        
    Returns:
        Aggregierte Statistiken
    """
    stats = {
        "days_active": len(week_sessions),
        "total_sessions": 0,
        "total_requests": 0,
        "total_duration_minutes": 0,
        "all_files_read": set(),
        "all_files_modified": set(),
        "all_tools": set(),
        "all_terminal_cmds": [],
        "daily_stats": {},
    }
    
    for day, sessions in week_sessions.items():
        day_stats = {
            "sessions": len(sessions),
            "requests": 0,
            "duration": 0,
            "files_modified": set(),
        }
        
        for session_data, _ in sessions:
            stats["total_sessions"] += 1
            stats["total_requests"] += session_data.get("request_count", 0)
            stats["total_duration_minutes"] += session_data.get("duration_minutes", 0)
            stats["all_files_read"].update(session_data.get("files_read", []))
            stats["all_files_modified"].update(session_data.get("files_modified", []))
            stats["all_tools"].update(session_data.get("tools_used", []))
            stats["all_terminal_cmds"].extend(session_data.get("terminal_commands", []))
            
            day_stats["requests"] += session_data.get("request_count", 0)
            day_stats["duration"] += session_data.get("duration_minutes", 0)
            day_stats["files_modified"].update(session_data.get("files_modified", []))
        
        day_stats["files_modified"] = list(day_stats["files_modified"])
        stats["daily_stats"][day.strftime("%Y-%m-%d")] = day_stats
    
    # Convert sets to lists
    stats["all_files_read"] = list(stats["all_files_read"])
    stats["all_files_modified"] = list(stats["all_files_modified"])
    stats["all_tools"] = list(stats["all_tools"])
    
    return stats


# =============================================================================
# WEEK SUMMARIZATION
# =============================================================================

def summarize_week_simple(week_sessions: dict[date, list], stats: dict) -> str:
    """
    Einfache Wochen-Zusammenfassung ohne LLM.
    
    Args:
        week_sessions: Sessions pro Tag
        stats: Aggregierte Statistiken
        
    Returns:
        Formatierter Summary-String
    """
    if not week_sessions:
        return "Keine Sessions in diesem Zeitraum gefunden."
    
    dates = sorted(week_sessions.keys())
    start = dates[0]
    end = dates[-1]
    
    lines = []
    lines.append(f"# Wochenzusammenfassung {start.strftime('%Y-%m-%d')} bis {end.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append("## Übersicht")
    lines.append(f"- **Aktive Tage:** {stats['days_active']}")
    lines.append(f"- **Sessions gesamt:** {stats['total_sessions']}")
    lines.append(f"- **Requests gesamt:** {stats['total_requests']}")
    lines.append(f"- **Geschätzte Arbeitszeit:** {round(stats['total_duration_minutes'] / 60, 1)}h")
    lines.append("")
    
    # Daily breakdown
    lines.append("## Tagesübersicht")
    lines.append("")
    
    weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    
    for day in sorted(week_sessions.keys()):
        sessions = week_sessions[day]
        day_stat = stats["daily_stats"].get(day.strftime("%Y-%m-%d"), {})
        wd = weekdays[day.weekday()]
        
        lines.append(f"### {day.strftime('%Y-%m-%d')} ({wd})")
        lines.append(f"- Sessions: {len(sessions)}, Requests: {day_stat.get('requests', 0)}")
        
        # List session titles
        for session_data, _ in sessions:
            title = session_data.get("title") or "Untitled"
            prompts = session_data.get("prompts", [])
            if not session_data.get("title") and prompts:
                title = prompts[0][:50] + "..." if len(prompts[0]) > 50 else prompts[0]
            lines.append(f"  - {title}")
        
        lines.append("")
    
    # Files modified
    if stats["all_files_modified"]:
        lines.append("## Bearbeitete Dateien")
        for f in sorted(stats["all_files_modified"])[:20]:
            lines.append(f"- `{Path(f).name}`")
        if len(stats["all_files_modified"]) > 20:
            lines.append(f"- ... und {len(stats['all_files_modified']) - 20} weitere")
        lines.append("")
    
    return "\n".join(lines)


def summarize_week_with_llm(week_sessions: dict[date, list], stats: dict, start_date: date, end_date: date) -> str:
    """
    Nutzt LLM für intelligente Wochen-Zusammenfassung.
    
    Args:
        week_sessions: Sessions pro Tag
        stats: Aggregierte Statistiken
        start_date: Wochenstart
        end_date: Wochenende
        
    Returns:
        LLM-generierte Zusammenfassung
    """
    client = get_llm_client()
    if not client:
        return "❌ Kein LLM Client verfügbar"
    
    model = os.getenv('NOVA_MODEL', 'claude-opus-4-6')
    
    # Extract conversations per day
    daily_conversations = {}
    for day, sessions in week_sessions.items():
        day_convs = []
        for _, session_file in sessions:
            conv = extract_raw_conversation(session_file)
            if conv and len(conv) > 50:
                day_convs.append(conv)
        if day_convs:
            daily_conversations[day] = day_convs
    
    if not daily_conversations:
        return "Keine Konversationen gefunden."
    
    # Format daily conversations
    weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    
    conversations_text = ""
    for day in sorted(daily_conversations.keys()):
        wd = weekdays[day.weekday()]
        conversations_text += f"\n\n{'='*60}\n## {day.strftime('%Y-%m-%d')} ({wd})\n{'='*60}\n"
        conversations_text += "\n---\n".join(daily_conversations[day])
    
    # Format metadata
    files_modified_str = "\n".join([f"  - {Path(f).name}" for f in sorted(stats["all_files_modified"])[:25]]) or "  (keine)"
    tools_str = ", ".join(sorted(stats["all_tools"])[:15]) or "(keine)"
    
    # Load tickets for context
    tickets = load_tickets()
    tickets_info = "KEINE TICKETS" if not tickets else "\n".join([
        f"- {tid}: {t['projekt']} - {t['beschreibung']}"
        for tid, t in tickets.items()
    ])
    
    prompt = f"""Analysiere die Copilot-Konversationen der Woche vom {start_date.strftime('%Y-%m-%d')} bis {end_date.strftime('%Y-%m-%d')}.

## METADATEN
- Aktive Tage: {stats['days_active']}
- Sessions gesamt: {stats['total_sessions']}
- Requests gesamt: {stats['total_requests']}
- Geschätzte Arbeitszeit: {round(stats['total_duration_minutes'] / 60, 1)} Stunden

### Bearbeitete Dateien:
{files_modified_str}

### Verwendete Tools: {tools_str}

### Aktive Tickets/Projekte:
{tickets_info}

---

## AUFGABE
Erstelle eine **Wochenzusammenfassung** mit folgendem Format:

```markdown
# Woche {start_date.strftime('%Y-%m-%d')} bis {end_date.strftime('%Y-%m-%d')}

## Highlights der Woche
- [Top 3-5 wichtigste Errungenschaften/Fortschritte]

## Tagesübersicht

### Montag (falls aktiv)
- [Hauptaktivitäten des Tages]

### Dienstag (falls aktiv)
- [Hauptaktivitäten des Tages]

[... weitere aktive Tage ...]

## Projekte & Tickets
- **TICKET-XXX**: [Was wurde daran gemacht]
- **Projekt Y**: [Fortschritt]

## Technische Highlights
- [Interessante Lösungen, neue Tools/Techniken gelernt]
- [Patterns oder Best Practices angewendet]

## Zeitverteilung (geschätzt)

| Bereich | Stunden |
|---------|--------:|
| Projekt A | Xh |
| Internes | Xh |
| **Gesamt** | **Xh** |

## Offene Punkte / Nächste Woche
- [ ] [Was noch zu erledigen ist]
- [ ] [Geplante Aufgaben]
```

Schreibe auf Deutsch. Gruppiere ähnliche Aktivitäten. Sei detailliert bei wichtigen Themen, prägnant bei Routine.

---

KONVERSATIONEN DER WOCHE:
{conversations_text}"""

    try:
        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=6000,
        )
        return response.content[0].text
    except Exception as e:
        print(f"ERROR: LLM call failed: {e}")
        return ""


# =============================================================================
# CLI
# =============================================================================

def main():
    # Fix Windows encoding
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    parser = argparse.ArgumentParser(
        description="Fasst Copilot Sessions einer Woche zusammen."
    )
    parser.add_argument(
        "--last", "-l",
        action="store_true",
        help="Letzte Woche statt aktuelle Woche"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        help="Anzahl Tage zurück (statt Wochengrenzen)"
    )
    parser.add_argument(
        "--from", "-f",
        dest="from_date",
        type=str,
        help="Startdatum im Format YYYY-MM-DD"
    )
    parser.add_argument(
        "--to", "-t",
        dest="to_date",
        type=str,
        help="Enddatum im Format YYYY-MM-DD (default: heute)"
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Nutze LLM für intelligente Zusammenfassung"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Schreibe direkt ins WORKLOG.md (nur mit --llm)"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Zeige rohe Statistiken als JSON"
    )
    
    args = parser.parse_args()
    
    today = date.today()
    
    # Determine date range
    if args.days:
        end_date = today
        start_date = today - timedelta(days=args.days - 1)
    elif args.from_date:
        try:
            start_date = datetime.strptime(args.from_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Ungültiges Datum: {args.from_date}")
            return
        
        if args.to_date:
            try:
                end_date = datetime.strptime(args.to_date, "%Y-%m-%d").date()
            except ValueError:
                print(f"Ungültiges Datum: {args.to_date}")
                return
        else:
            end_date = today
    else:
        # Use week boundaries
        start_date, end_date = get_week_boundaries(today, last_week=args.last)
        # Don't go into the future
        if end_date > today:
            end_date = today
    
    print(f"Sammle Sessions von {start_date} bis {end_date}...")
    
    # Collect sessions
    week_sessions = collect_week_sessions(start_date, end_date)
    
    if not week_sessions:
        print(f"Keine Sessions im Zeitraum {start_date} bis {end_date} gefunden.")
        return
    
    print(f"Gefunden: {sum(len(s) for s in week_sessions.values())} Sessions an {len(week_sessions)} Tagen\n")
    
    # Aggregate stats
    stats = aggregate_week_stats(week_sessions)
    
    # Output
    if args.raw:
        print(json.dumps(stats, indent=2, default=str))
    elif args.llm:
        summary = summarize_week_with_llm(week_sessions, stats, start_date, end_date)
        if summary:
            print(summary)
            if args.write:
                worklog_path = get_knowledge_root() / "WORKLOG.md"
                if worklog_path.exists():
                    if write_to_worklog(summary, worklog_path):
                        print(f"\n✓ Geschrieben nach {worklog_path}")
                else:
                    print(f"\nWORKLOG nicht gefunden: {worklog_path}")
    else:
        print(summarize_week_simple(week_sessions, stats))


if __name__ == "__main__":
    main()
