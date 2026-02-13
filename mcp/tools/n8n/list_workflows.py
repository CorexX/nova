"""Tool: List n8n workflows."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.types import Tool, TextContent

from .client import (
    OptionalFeatureNotConfigured,
    request_json,
    resolve_n8n_config,
    workflows_path,
)


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_n8n_list_workflows",
        description="Listet n8n Workflows via API.",
        inputSchema={
            "type": "object",
            "properties": {
                "base_url": {"type": "string", "description": "n8n Base URL, z.B. https://n8n.home"},
                "api_key": {"type": "string", "description": "n8n API Key (optional, sonst env N8N_API_KEY)"},
                "limit": {"type": "integer", "description": "Maximale Anzahl (default: 20)"},
                "insecure_tls": {"type": "boolean", "description": "TLS-Verify deaktivieren (self-signed certs)"},
            },
            "required": [],
        },
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    try:
        base_url, api_key, insecure_tls = resolve_n8n_config(args)
    except OptionalFeatureNotConfigured as e:
        return [TextContent(type="text", text=str(e))]
    except ValueError as e:
        return [TextContent(type="text", text=str(e))]

    limit = int(args.get("limit", 20))
    result = request_json(
        base_url=base_url,
        api_key=api_key,
        method="GET",
        path=workflows_path(limit),
        insecure_tls=insecure_tls,
    )

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
