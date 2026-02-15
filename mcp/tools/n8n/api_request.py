"""Tool: Generic n8n API request (wildcard endpoint access)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.types import TextContent, Tool

from .client import OptionalFeatureNotConfigured, request_json, resolve_n8n_config

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_n8n_api_request",
        description="Generic n8n API request for custom endpoints (GET/POST/PUT/PATCH/DELETE).",
        inputSchema={
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                },
                "path": {
                    "type": "string",
                    "description": "API endpoint path, e.g. /api/v1/workflows or /api/v1/executions",
                },
                "payload": {
                    "type": "object",
                    "description": "Optional JSON body for POST/PUT/PATCH",
                },
                "base_url": {"type": "string", "description": "n8n Base URL"},
                "api_key": {"type": "string", "description": "n8n API key"},
                "insecure_tls": {"type": "boolean", "description": "Disable TLS verification"},
                "compact": {
                    "type": "boolean",
                    "description": "Reduce response to context-relevant fields (default: true). Set false for full raw output.",
                },
            },
            "required": ["method", "path"],
        },
    )


def _normalize_path(path: str) -> str:
    value = path.strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if not value.startswith("/"):
        value = f"/{value}"
    return value


def _validate_payload(method: str, payload: Any) -> str | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        return "Arg 'payload' must be an object when provided"
    if method == "GET":
        return "GET requests do not support 'payload' for this tool"
    return None


def _as_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _workflow_summary(item: dict[str, Any]) -> dict[str, Any]:
    nodes = item.get("nodes")
    connections = item.get("connections")
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "active": item.get("active"),
        "updatedAt": item.get("updatedAt"),
        "createdAt": item.get("createdAt"),
        "nodeCount": len(nodes) if isinstance(nodes, list) else None,
        "connectionCount": len(connections) if isinstance(connections, dict) else None,
    }


def _execution_summary(item: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "id": item.get("id"),
        "workflowId": item.get("workflowId"),
        "status": item.get("status"),
        "startedAt": item.get("startedAt"),
        "stoppedAt": item.get("stoppedAt"),
        "finished": item.get("finished"),
    }
    error = ((item.get("data") or {}).get("resultData") or {}).get("error")
    if isinstance(error, dict):
        summary["error"] = error.get("message")
    return summary


def _compact_get_response(path: str, result: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {"status": result.get("status")}
    if "error" in result:
        err = result.get("error")
        if isinstance(err, dict):
            compact["error"] = {"message": err.get("message"), "code": err.get("code")}
        else:
            compact["error"] = err
        return compact

    data = result.get("data")
    if not isinstance(data, (dict, list)):
        compact["data"] = data
        return compact

    normalized_path = path.split("?", 1)[0]

    if normalized_path == "/api/v1/workflows":
        items = data.get("data") if isinstance(data, dict) else data
        if isinstance(items, list):
            compact["data"] = [_workflow_summary(i) for i in items if isinstance(i, dict)]
            if isinstance(data, dict):
                compact["nextCursor"] = data.get("nextCursor")
            return compact

    if normalized_path.startswith("/api/v1/workflows/") and isinstance(data, dict):
        compact["data"] = _workflow_summary(data)
        return compact

    if normalized_path == "/api/v1/executions":
        items = data.get("data") if isinstance(data, dict) else data
        if isinstance(items, list):
            compact["data"] = [_execution_summary(i) for i in items if isinstance(i, dict)]
            if isinstance(data, dict):
                compact["nextCursor"] = data.get("nextCursor")
            return compact

    if normalized_path.startswith("/api/v1/executions/") and isinstance(data, dict):
        compact["data"] = _execution_summary(data)
        return compact

    if isinstance(data, dict):
        compact["data"] = {"keys": list(data.keys())[:20]}
        return compact

    compact["data"] = {"length": len(data)} if isinstance(data, list) else data
    return compact


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    method = str(args.get("method", "")).upper().strip()
    path_raw = args.get("path")
    payload = args.get("payload")
    compact = _as_bool(args.get("compact"), default=True)

    if method not in ALLOWED_METHODS:
        return [TextContent(type="text", text=f"Invalid method. Allowed: {', '.join(sorted(ALLOWED_METHODS))}")]

    if not isinstance(path_raw, str) or not path_raw.strip():
        return [TextContent(type="text", text="Missing required arg: path")]

    path = _normalize_path(path_raw)
    if not path:
        return [TextContent(type="text", text="Missing required arg: path")]
    if path.startswith("http://") or path.startswith("https://"):
        return [TextContent(type="text", text="Arg 'path' must be a path, not a full URL")]

    payload_error = _validate_payload(method, payload)
    if payload_error:
        return [TextContent(type="text", text=payload_error)]

    try:
        base_url, api_key, insecure_tls = resolve_n8n_config(args)
    except OptionalFeatureNotConfigured as e:
        return [TextContent(type="text", text=str(e))]
    except ValueError as e:
        return [TextContent(type="text", text=str(e))]

    result = request_json(
        base_url=base_url,
        api_key=api_key,
        method=method,
        path=path,
        payload=payload,
        insecure_tls=insecure_tls,
    )
    output = _compact_get_response(path, result) if compact and method == "GET" else result
    return [TextContent(type="text", text=json.dumps(output, ensure_ascii=False, indent=2))]
