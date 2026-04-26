#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOVA 2.0 MCP server: memory/context tools only."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_cpu_count = os.cpu_count() or 4
_threads = max(2, _cpu_count // 2)
os.environ.setdefault("OMP_NUM_THREADS", str(_threads))
os.environ.setdefault("MKL_NUM_THREADS", str(_threads))

if sys.platform == "win32":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from tools import context_resolve, knowledge_query, knowledge_update, memory_maintain

server = Server("nova-memory")


def detect_workspace_root() -> Path:
    """Return the NOVA repository root for standalone and embedded layouts."""
    core_root = Path(__file__).resolve().parent.parent
    parent = core_root.parent
    if core_root.name == "nova-core" and (parent / "nova-knowledge").exists():
        return parent
    return core_root


WORKSPACE_ROOT = detect_workspace_root()

TOOLS = {
    "nova_context_resolve": context_resolve,
    "nova_knowledge_query": knowledge_query,
    "nova_knowledge_update": knowledge_update,
    "nova_memory_maintain": memory_maintain,
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [module.get_tool_definition(WORKSPACE_ROOT) for module in TOOLS.values()]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name in TOOLS:
        return await TOOLS[name].execute(arguments, WORKSPACE_ROOT)
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main() -> None:
    print(f"[NOVA memory | Starting] {_threads} threads", file=sys.stderr, flush=True)
    print(f"[NOVA memory | Ready] {len(TOOLS)} tools", file=sys.stderr, flush=True)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
