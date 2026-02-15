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
from tools import (
    context_resolve,
    project_continue,
    project_create,
    knowledge_query,
    knowledge_update,
    system_maintain,
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
    "nova_context_resolve": context_resolve,
    "nova_project_continue": project_continue,
    "nova_project_create": project_create,
    "nova_knowledge_query": knowledge_query,
    "nova_knowledge_update": knowledge_update,
    "nova_system_maintain": system_maintain,
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

# Flag: Index-Backend beim Serverstart initialisieren (default: aktiv)
PREWARM_INDEX_BACKEND = os.environ.get("NOVA_PREWARM_INDEX_BACKEND", "1") == "1"


async def main():
    """Startet den MCP Server."""
    print(f"[NOVA | Starting] {_threads} threads", file=sys.stderr, flush=True)
    
    if PREWARM_INDEX_BACKEND:
        system_maintain.initialize_on_startup(WORKSPACE_ROOT)
    else:
        print("[NOVA | Index backend] lazy mode (NOVA_PREWARM_INDEX_BACKEND=0)", file=sys.stderr, flush=True)
    
    print(f"[NOVA | Ready] {len(TOOLS)} tools", file=sys.stderr, flush=True)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
