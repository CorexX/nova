"""Tool: Restart MCP server process after a short delay."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from mcp.types import TextContent, Tool

DEFAULT_DELAY_SECONDS = 2
MIN_DELAY_SECONDS = 1
MAX_DELAY_SECONDS = 30


def get_tool_definition(workspace_root: Path) -> Tool:
    """Return MCP tool definition."""
    return Tool(
        name="nova_restart_server",
        description=(
            "Plant einen MCP-Server-Restart durch self-terminate des aktuellen "
            "Prozesses nach kurzer Verzoegerung."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "delay_seconds": {
                    "type": "integer",
                    "description": (
                        "Verzoegerung bis self-terminate in Sekunden (1-30, default: 2)."
                    ),
                    "minimum": MIN_DELAY_SECONDS,
                    "maximum": MAX_DELAY_SECONDS,
                }
            },
            "required": [],
        },
    )


def _terminate_process() -> None:
    """Terminate current process so MCP supervisor can restart it."""
    os._exit(0)


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    """Schedule process termination and return immediately."""
    try:
        delay = int(args.get("delay_seconds", DEFAULT_DELAY_SECONDS))
    except (TypeError, ValueError):
        return [
            TextContent(
                type="text",
                text="Invalid argument: 'delay_seconds' must be an integer.",
            )
        ]

    if delay < MIN_DELAY_SECONDS or delay > MAX_DELAY_SECONDS:
        return [
            TextContent(
                type="text",
                text=(
                    f"Invalid argument: 'delay_seconds' must be between "
                    f"{MIN_DELAY_SECONDS} and {MAX_DELAY_SECONDS}."
                ),
            )
        ]

    timer = threading.Timer(delay, _terminate_process)
    timer.daemon = True
    timer.start()

    return [
        TextContent(
            type="text",
            text=(
                f"OK: MCP server self-terminate scheduled in {delay}s. "
                "Supervisor/VS Code should restart it automatically."
            ),
        )
    ]
