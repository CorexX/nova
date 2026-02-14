#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA MCP Server
Exposed NOVA Skills als Tools für GitHub Copilot.

Usage:
    python nova_mcp_core_server.py

Der Server wird über VS Code's MCP-Konfiguration gestartet.
"""

import asyncio
import sys
import os
from pathlib import Path

# CPU threads for PyTorch/Transformers (half of available cores)
# Note: This mainly helps inference speed, not model loading.
# Loading is I/O-bound + Python GIL + Tokenizer init (~30s fixed).
_cpu_count = os.cpu_count() or 4
_threads = max(2, _cpu_count // 2)
os.environ.setdefault("OMP_NUM_THREADS", str(_threads))
os.environ.setdefault("MKL_NUM_THREADS", str(_threads))

# Force UTF-8 encoding on Windows
if sys.platform == 'win32':
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Tool Imports
from tools.git import push_repos
from tools.worklog import append as worklog_append
from tools.testing import run_tests
from tools.sessions import summarize_day, summarize_week
from tools.architecture import get_architecture
from tools.context import (
    session_init,
    get_rules,
    get_scope,
    get_structure,
    get_playbooks,
    get_guides,
    get_templates,
    get_conventions,
    get_current,
    get_tickets,
    get_collections,
    get_paths,
    get_agent_skills,
    project_resume,
)
from tools.search import index_vault, search_vault
from tools.health import health_check
from tools.n8n import (
    list_workflows as n8n_list_workflows,
    get_workflow as n8n_get_workflow,
    create_workflow as n8n_create_workflow,
    update_workflow as n8n_update_workflow,
    delete_workflow as n8n_delete_workflow,
)


# =============================================================================
# SERVER SETUP
# =============================================================================

server = Server("nova-skills")

def detect_workspace_root() -> Path:
    """
    Erkennt Workspace-Root fuer beide Layouts:
    - Standalone Repo: `<workspace>/mcp/nova_mcp_core_server.py`
    - Embedded Layout: `<workspace>/nova-core/mcp/nova_mcp_core_server.py`
    """
    core_root = Path(__file__).resolve().parent.parent
    parent = core_root.parent

    if (
        core_root.name == "nova-core"
        and (
            (parent / "nova.toml").exists()
            or (parent / "nova-knowledge").exists()
            or (parent / ".vscode").exists()
        )
    ):
        return parent

    return core_root


WORKSPACE_ROOT = detect_workspace_root()


# =============================================================================
# TOOL REGISTRY
# =============================================================================

# Mapping: tool_name → module
TOOLS = {
    # Core Tools
    "nova_git_push_repos": push_repos,
    "nova_worklog_append": worklog_append,
    "nova_run_tests": run_tests,
    "nova_summarize_day": summarize_day,
    "nova_summarize_week": summarize_week,
    "nova_get_architecture": get_architecture,
    # Context Tools
    "nova_session_init": session_init,
    "nova_get_rules": get_rules,
    "nova_get_scope": get_scope,
    "nova_get_structure": get_structure,
    "nova_get_playbooks": get_playbooks,
    "nova_get_guides": get_guides,
    "nova_get_templates": get_templates,
    "nova_get_conventions": get_conventions,
    "nova_get_current": get_current,
    "nova_get_tickets": get_tickets,
    "nova_get_collections": get_collections,
    "nova_get_paths": get_paths,
    "nova_get_agent_skills": get_agent_skills,
    "nova_project_resume": project_resume,
    # Search Tools
    "nova_index_vault": index_vault,
    "nova_search_vault": search_vault,
    # Health Tools
    "nova_health_check": health_check,
    # n8n Tools
    "nova_n8n_list_workflows": n8n_list_workflows,
    "nova_n8n_get_workflow": n8n_get_workflow,
    "nova_n8n_create_workflow": n8n_create_workflow,
    "nova_n8n_update_workflow": n8n_update_workflow,
    "nova_n8n_delete_workflow": n8n_delete_workflow,
}


# =============================================================================
# MCP HANDLERS
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Registriert alle verfügbaren Tools."""
    return [
        module.get_tool_definition(WORKSPACE_ROOT) 
        for module in TOOLS.values()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Führt ein Tool aus."""
    if name in TOOLS:
        return await TOOLS[name].execute(arguments, WORKSPACE_ROOT)
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


# =============================================================================
# MAIN
# =============================================================================

# Flag: Embedding Model beim Start laden (statt lazy beim ersten search_vault)
# Setze NOVA_PRELOAD_MODEL=0 um auf lazy loading zu wechseln
PRELOAD_MODEL = os.environ.get("NOVA_PRELOAD_MODEL", "1") == "1"


def preload_embedding_model():
    """Lädt Embedding Model synchron beim Server-Start (~30s)."""
    import time
    import warnings
    
    print("[NOVA | Loading embedding model]", file=sys.stderr, flush=True)
    start = time.time()
    
    # Progress-Ticker im Hintergrund
    import threading
    stop_ticker = threading.Event()
    
    def progress_ticker():
        elapsed = 0
        while not stop_ticker.is_set():
            stop_ticker.wait(5)
            if not stop_ticker.is_set():
                elapsed += 5
                remaining = max(0, 30 - elapsed)
                print(f"[NOVA | Loading embedding model] {elapsed}s / ~{30 if remaining else elapsed}s", file=sys.stderr, flush=True)
    
    ticker = threading.Thread(target=progress_ticker, daemon=True)
    ticker.start()
    
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from tools.search.shared import get_model
            get_model()
        
        stop_ticker.set()
        elapsed = time.time() - start
        print(f"[NOVA | Model ready] {elapsed:.0f}s", file=sys.stderr, flush=True)
        
    except ImportError as e:
        stop_ticker.set()
        print(f"[NOVA | Model skipped] {e}", file=sys.stderr, flush=True)
    except Exception as e:
        stop_ticker.set()
        print(f"[NOVA | Model failed] {e}", file=sys.stderr, flush=True)


async def main():
    """Startet den MCP Server."""
    print(f"[NOVA | Starting] {_threads} threads", file=sys.stderr, flush=True)
    
    # Model beim Start laden (blocking, ~30s)
    if PRELOAD_MODEL:
        preload_embedding_model()
    else:
        print("[NOVA | Model] lazy mode (NOVA_PRELOAD_MODEL=0)", file=sys.stderr, flush=True)
    
    print(f"[NOVA | Ready] {len(TOOLS)} tools", file=sys.stderr, flush=True)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
