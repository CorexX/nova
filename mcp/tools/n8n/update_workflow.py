"""Tool: Update n8n workflow."""

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
        name="nova_n8n_update_workflow",
        description="Aktualisiert einen n8n Workflow via API.",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "n8n Workflow-ID"},
                "workflow": {"type": "object", "description": "Workflow-Payload"},
                "base_url": {"type": "string", "description": "n8n Base URL"},
                "api_key": {"type": "string", "description": "n8n API Key"},
                "insecure_tls": {"type": "boolean", "description": "TLS-Verify deaktivieren"},
            },
            "required": ["workflow_id", "workflow"],
        },
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    workflow_id = args.get("workflow_id")
    workflow = args.get("workflow")
    if not workflow_id:
        return [TextContent(type="text", text="Missing required arg: workflow_id")]
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
        method="PUT",
        path=f"/api/v1/workflows/{workflow_id}",
        payload=payload,
        insecure_tls=insecure_tls,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
