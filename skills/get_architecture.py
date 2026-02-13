#!/usr/bin/env python3
"""
Skill: Get Architecture
Liefert eine context-sparende Zusammenfassung der NOVA-Architektur.

Liest aus nova-core/meta/ARCHITECTURE.md:
- Kompakt: Extrahiert den <!-- COMPACT_START --> bis <!-- COMPACT_END --> Bereich
- Full: Gibt die komplette Datei zurück
- Section: Sucht nach ## [Sektionsname] und gibt diesen Abschnitt zurück

Usage:
    python get_architecture.py [--full] [--section SECTION]

Examples:
    python get_architecture.py              # Kompakte Übersicht
    python get_architecture.py --full       # Komplette ARCHITECTURE.md
    python get_architecture.py -s "Design-Prinzipien"
"""

import argparse
import re
from pathlib import Path


# =============================================================================
# CONSTANTS
# =============================================================================

COMPACT_START = "<!-- COMPACT_START"
COMPACT_END = "<!-- COMPACT_END -->"

# Default path (relativ zum Skill)
DEFAULT_ARCHITECTURE_PATH = Path(__file__).parent.parent / "meta" / "ARCHITECTURE.md"


# =============================================================================
# FUNCTIONS
# =============================================================================

def read_architecture_file(path: Path | None = None) -> str:
    """Liest die ARCHITECTURE.md Datei."""
    if path is None:
        path = DEFAULT_ARCHITECTURE_PATH
    
    if not path.exists():
        return f"ERROR: ARCHITECTURE.md nicht gefunden: {path}"
    
    return path.read_text(encoding="utf-8")


def extract_compact(content: str) -> str:
    """Extrahiert den COMPACT-Bereich aus der ARCHITECTURE.md."""
    # Suche nach COMPACT_START und COMPACT_END
    start_match = re.search(r"<!-- COMPACT_START[^>]*-->", content)
    end_match = re.search(r"<!-- COMPACT_END -->", content)
    
    if not start_match or not end_match:
        # Fallback: Erste 100 Zeilen
        lines = content.split("\n")[:100]
        return "\n".join(lines) + "\n\n[... truncated, use --full for complete file]"
    
    # Extrahiere den Bereich zwischen den Markern
    start_pos = start_match.end()
    end_pos = end_match.start()
    
    compact = content[start_pos:end_pos].strip()
    return compact


def extract_section(content: str, section_name: str) -> str:
    """Extrahiert eine bestimmte Sektion (## Heading) aus der ARCHITECTURE.md."""
    # Suche nach der Sektion (case-insensitive)
    pattern = rf"^## .*{re.escape(section_name)}.*$"
    lines = content.split("\n")
    
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if re.match(pattern, line, re.IGNORECASE):
            start_idx = i
        elif start_idx is not None and line.startswith("## "):
            end_idx = i
            break
    
    if start_idx is None:
        # Liste verfügbare Sektionen
        sections = [line for line in lines if line.startswith("## ")]
        section_list = "\n".join(f"  - {s[3:]}" for s in sections[:15])
        return f"Sektion '{section_name}' nicht gefunden.\n\nVerfügbare Sektionen:\n{section_list}"
    
    if end_idx is None:
        end_idx = len(lines)
    
    return "\n".join(lines[start_idx:end_idx]).strip()


def get_architecture(
    full: bool = False, 
    section: str | None = None,
    architecture_path: Path | None = None
) -> str:
    """
    Gibt Architektur-Zusammenfassung zurück.
    
    Args:
        full: Komplette ARCHITECTURE.md ausgeben
        section: Nur bestimmte Sektion (## Heading)
        architecture_path: Pfad zur ARCHITECTURE.md (optional)
        
    Returns:
        Formatierter String
    """
    content = read_architecture_file(architecture_path)
    
    if content.startswith("ERROR:"):
        return content
    
    if full:
        return content
    
    if section:
        return extract_section(content, section)
    
    return extract_compact(content)


def main():
    parser = argparse.ArgumentParser(
        description="NOVA Architektur-Übersicht (liest aus ARCHITECTURE.md)"
    )
    parser.add_argument(
        "--full", "-f",
        action="store_true",
        help="Komplette ARCHITECTURE.md ausgeben"
    )
    parser.add_argument(
        "--section", "-s",
        type=str,
        help="Nur bestimmte Sektion (z.B. 'Design-Prinzipien', 'Komponenten')"
    )
    parser.add_argument(
        "--path", "-p",
        type=str,
        help="Pfad zur ARCHITECTURE.md (default: nova-core/meta/ARCHITECTURE.md)"
    )
    
    args = parser.parse_args()
    
    path = Path(args.path) if args.path else None
    print(get_architecture(full=args.full, section=args.section, architecture_path=path))


if __name__ == "__main__":
    main()
