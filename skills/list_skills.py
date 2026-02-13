#!/usr/bin/env python3
"""
Skill: List Skills
Listet alle verfügbaren NOVA Skills auf.

Usage:
    python list_skills.py [--verbose] [-t TAG]

Examples:
    python list_skills.py
    python list_skills.py --verbose
    python list_skills.py -t git
"""

import argparse
import sys
from pathlib import Path


# =============================================================================
# SKILL REGISTRY
# =============================================================================

SKILLS = [
    {
        "name": "nova_git_push_repos",
        "category": "git",
        "description": "Pushed alle Git-Repos im Workspace",
        "tags": ["git", "automation"],
    },
    {
        "name": "nova_worklog_append",
        "category": "worklog",
        "description": "Fügt Eintrag zum WORKLOG.md hinzu",
        "tags": ["worklog", "documentation"],
    },
    {
        "name": "nova_list_skills",
        "category": "skills",
        "description": "Listet verfügbare Skills auf",
        "tags": ["meta", "skills"],
    },
    {
        "name": "nova_run_tests",
        "category": "testing",
        "description": "Führt pytest für Tool-Tests aus",
        "tags": ["testing", "quality"],
    },
    {
        "name": "nova_summarize_day",
        "category": "sessions",
        "description": "Fasst Copilot Sessions des Tages zusammen für WORKLOG",
        "tags": ["sessions", "worklog", "automation"],
    },
    {
        "name": "nova_get_architecture",
        "category": "architecture",
        "description": "Liefert context-sparende Architektur-Übersicht",
        "tags": ["meta", "architecture", "context"],
    },
]


# =============================================================================
# FUNCTIONS
# =============================================================================

def list_skills(verbose: bool = False, tag: str | None = None) -> str:
    """
    Listet alle Skills auf.
    
    Args:
        verbose: Zeige Details zu allen Skills
        tag: Filter nach Tag
        
    Returns:
        Formatierter String mit Skills
    """
    skills = SKILLS
    
    # Filter by tag
    if tag:
        skills = [s for s in skills if tag.lower() in [t.lower() for t in s["tags"]]]
    
    if not skills:
        return f"Keine Skills mit Tag '{tag}' gefunden."
    
    lines = []
    lines.append(f"NOVA Skills ({len(skills)} verfügbar)")
    lines.append("=" * 40)
    
    if verbose:
        for skill in skills:
            lines.append(f"\n{skill['name']}")
            lines.append(f"  Kategorie: {skill['category']}")
            lines.append(f"  Beschreibung: {skill['description']}")
            lines.append(f"  Tags: {', '.join(skill['tags'])}")
    else:
        for skill in skills:
            lines.append(f"  - {skill['name']}: {skill['description']}")
    
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Listet alle verfügbaren NOVA Skills auf."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Zeige Details zu allen Skills"
    )
    parser.add_argument(
        "-t", "--tag",
        type=str,
        help="Filtere nach Tag (z.B. 'git', 'automation')"
    )
    
    args = parser.parse_args()
    
    output = list_skills(verbose=args.verbose, tag=args.tag)
    print(output)


if __name__ == "__main__":
    main()
