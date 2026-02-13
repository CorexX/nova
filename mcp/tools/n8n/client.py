"""Shared HTTP client helpers for n8n MCP tools."""

from __future__ import annotations

import json
import os
import ssl
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError


class OptionalFeatureNotConfigured(ValueError):
    """Raised when optional n8n integration is not configured."""


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "on"}


def normalize_base_url(base_url: str) -> str:
    """Normalize n8n URL to API base origin.

    Accepts values like:
    - https://n8n.home
    - https://n8n.home/
    - https://n8n.home/workflow/abc
    - https://n8n.home/api/v1
    """
    parsed = parse.urlparse(base_url.strip())
    if not parsed.scheme or not parsed.netloc:
        return base_url.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def resolve_n8n_config(args: dict[str, Any]) -> tuple[str, str, bool]:
    """Resolve n8n base URL, API key and TLS mode from args/env."""
    base_url = args.get("base_url") or os.environ.get("N8N_BASE_URL", "")
    api_key = args.get("api_key") or os.environ.get("N8N_API_KEY", "")
    insecure_tls = _parse_bool(
        args.get("insecure_tls", os.environ.get("N8N_INSECURE_TLS", False))
    )

    if not base_url and not api_key:
        raise OptionalFeatureNotConfigured(
            "Optional feature not configured: n8n is disabled. "
            "Set N8N_BASE_URL and N8N_API_KEY (env) or pass base_url/api_key args."
        )
    if not base_url:
        raise OptionalFeatureNotConfigured(
            "Optional feature not configured: missing n8n base URL "
            "(arg 'base_url' or env N8N_BASE_URL)."
        )
    if not api_key:
        raise OptionalFeatureNotConfigured(
            "Optional feature not configured: missing n8n API key "
            "(arg 'api_key' or env N8N_API_KEY)."
        )

    return normalize_base_url(base_url), api_key, insecure_tls


def sanitize_workflow_payload(workflow: dict[str, Any]) -> dict[str, Any]:
    """Drop read-only workflow fields that n8n API rejects on write."""
    blocked = {
        "id",
        "active",
        "createdAt",
        "updatedAt",
        "versionId",
        "activeVersionId",
        "isArchived",
        "versionCounter",
        "triggerCount",
    }
    return {k: v for k, v in workflow.items() if k not in blocked}


def _ssl_context(insecure_tls: bool):
    if not insecure_tls:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def request_json(
    *,
    base_url: str,
    api_key: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    insecure_tls: bool = False,
    timeout: int = 30,
) -> dict[str, Any]:
    """Perform a JSON request against n8n API and return parsed response."""
    url = f"{base_url}{path}"
    headers = {"X-N8N-API-KEY": api_key, "Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url=url, method=method.upper(), headers=headers, data=data)
    context = _ssl_context(insecure_tls)

    try:
        with request.urlopen(req, timeout=timeout, context=context) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw:
                return {"status": resp.status, "data": None}
            try:
                return {"status": resp.status, "data": json.loads(raw)}
            except json.JSONDecodeError:
                return {"status": resp.status, "data": {"raw": raw}}
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return {"status": e.code, "error": parsed}
    except URLError as e:
        return {"status": 0, "error": {"message": str(e.reason)}}


def workflows_path(limit: int | None = None) -> str:
    """Build the workflows listing path with optional limit parameter."""
    if limit is None:
        return "/api/v1/workflows"
    query = parse.urlencode({"limit": int(limit)})
    return f"/api/v1/workflows?{query}"
