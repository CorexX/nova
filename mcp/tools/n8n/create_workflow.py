"""Tool: Create n8n workflow."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.types import Tool, TextContent

from .client import (
    OptionalFeatureNotConfigured,
    request_json,
    resolve_n8n_config,
    sanitize_workflow_payload,
)


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_n8n_create_workflow",
        description="Erstellt einen n8n Workflow via API.",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow": {"type": "object", "description": "Workflow-Payload (name, nodes, connections, settings)"},
                "base_url": {"type": "string", "description": "n8n Base URL"},
                "api_key": {"type": "string", "description": "n8n API Key"},
                "insecure_tls": {"type": "boolean", "description": "TLS-Verify deaktivieren"},
            },
            "required": ["workflow"],
        },
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    workflow = args.get("workflow")
    if not isinstance(workflow, dict):
        return [TextContent(type="text", text="Arg 'workflow' must be an object")]

    try:
        base_url, api_key, insecure_tls = resolve_n8n_config(args)
    except OptionalFeatureNotConfigured as e:
        return [TextContent(type="text", text=str(e))]
    except ValueError as e:
        return [TextContent(type="text", text=str(e))]

    payload = sanitize_workflow_payload(workflow)
    result = request_json(
        base_url=base_url,
        api_key=api_key,
        method="POST",
        path="/api/v1/workflows",
        payload=payload,
        insecure_tls=insecure_tls,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
