"""Tests for n8n MCP tools."""

from pathlib import Path

import pytest
from mcp.types import TextContent, Tool

from tools.n8n import (
    client,
    create_workflow,
    delete_workflow,
    get_workflow,
    list_workflows,
    update_workflow,
)


class TestToolDefinitions:
    @pytest.mark.parametrize(
        ("module", "name"),
        [
            (list_workflows, "nova_n8n_list_workflows"),
            (get_workflow, "nova_n8n_get_workflow"),
            (create_workflow, "nova_n8n_create_workflow"),
            (update_workflow, "nova_n8n_update_workflow"),
            (delete_workflow, "nova_n8n_delete_workflow"),
        ],
    )
    def test_definition_shape(self, module, name, tmp_path: Path):
        tool = module.get_tool_definition(tmp_path)
        assert isinstance(tool, Tool)
        assert tool.name == name
        assert tool.description
        assert tool.inputSchema


class TestClientHelpers:
    def test_resolve_n8n_config_from_args(self):
        base_url, api_key, insecure_tls = client.resolve_n8n_config(
            {"base_url": "https://n8n.home/", "api_key": "key", "insecure_tls": True}
        )
        assert base_url == "https://n8n.home"
        assert api_key == "key"
        assert insecure_tls is True

    def test_resolve_n8n_config_from_env(self, monkeypatch):
        monkeypatch.setenv("N8N_BASE_URL", "https://n8n.env/")
        monkeypatch.setenv("N8N_API_KEY", "env-key")

        base_url, api_key, insecure_tls = client.resolve_n8n_config({})
        assert base_url == "https://n8n.env"
        assert api_key == "env-key"
        assert insecure_tls is False

    def test_resolve_n8n_config_normalizes_workflow_url(self):
        base_url, api_key, insecure_tls = client.resolve_n8n_config(
            {
                "base_url": "https://n8n.home/workflow/GxNB0qbA3EBZh3Dz",
                "api_key": "key",
            }
        )
        assert base_url == "https://n8n.home"
        assert api_key == "key"
        assert insecure_tls is False

    def test_resolve_n8n_config_insecure_from_env(self, monkeypatch):
        monkeypatch.setenv("N8N_BASE_URL", "https://n8n.env")
        monkeypatch.setenv("N8N_API_KEY", "env-key")
        monkeypatch.setenv("N8N_INSECURE_TLS", "true")
        _, _, insecure_tls = client.resolve_n8n_config({})
        assert insecure_tls is True

    def test_resolve_n8n_config_requires_base_url(self, monkeypatch):
        monkeypatch.delenv("N8N_BASE_URL", raising=False)
        monkeypatch.setenv("N8N_API_KEY", "env-key")
        with pytest.raises(ValueError, match="Optional feature not configured: missing n8n base URL"):
            client.resolve_n8n_config({})

    def test_resolve_n8n_config_requires_api_key(self, monkeypatch):
        monkeypatch.setenv("N8N_BASE_URL", "https://n8n.env")
        monkeypatch.delenv("N8N_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Optional feature not configured: missing n8n API key"):
            client.resolve_n8n_config({})

    def test_resolve_n8n_config_optional_when_not_set(self, monkeypatch):
        monkeypatch.delenv("N8N_BASE_URL", raising=False)
        monkeypatch.delenv("N8N_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Optional feature not configured: n8n is disabled"):
            client.resolve_n8n_config({})

    def test_workflows_path(self):
        assert client.workflows_path() == "/api/v1/workflows"
        assert client.workflows_path(25) == "/api/v1/workflows?limit=25"

    def test_sanitize_workflow_payload(self):
        payload = {
            "name": "wf",
            "nodes": [],
            "connections": {},
            "active": True,
            "id": "abc",
            "updatedAt": "now",
        }
        cleaned = client.sanitize_workflow_payload(payload)
        assert cleaned["name"] == "wf"
        assert "active" not in cleaned
        assert "id" not in cleaned
        assert "updatedAt" not in cleaned


class TestExecute:
    @pytest.mark.asyncio
    async def test_list_workflows_execute(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(
            list_workflows,
            "resolve_n8n_config",
            lambda args: ("https://n8n.home", "key", True),
        )
        monkeypatch.setattr(
            list_workflows,
            "request_json",
            lambda **kwargs: {"status": 200, "data": {"data": []}},
        )

        result = await list_workflows.execute({}, tmp_path)
        assert isinstance(result[0], TextContent)
        assert '"status": 200' in result[0].text

    @pytest.mark.asyncio
    async def test_list_workflows_uses_default_limit(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(
            list_workflows,
            "resolve_n8n_config",
            lambda args: ("https://n8n.home", "key", False),
        )
        called = {}

        def fake_request_json(**kwargs):
            called.update(kwargs)
            return {"status": 200, "data": {"data": []}}

        monkeypatch.setattr(list_workflows, "request_json", fake_request_json)

        await list_workflows.execute({}, tmp_path)
        assert called["method"] == "GET"
        assert called["path"] == "/api/v1/workflows?limit=20"

    @pytest.mark.asyncio
    async def test_list_bubbles_config_error(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(
            list_workflows,
            "resolve_n8n_config",
            lambda args: (_ for _ in ()).throw(ValueError("Optional feature not configured: missing n8n API key")),
        )
        result = await list_workflows.execute({}, tmp_path)
        assert "Optional feature not configured: missing n8n API key" in result[0].text

    @pytest.mark.asyncio
    async def test_get_requires_id(self, tmp_path: Path):
        result = await get_workflow.execute({}, tmp_path)
        assert "workflow_id" in result[0].text

    @pytest.mark.asyncio
    async def test_get_calls_get(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(
            get_workflow,
            "resolve_n8n_config",
            lambda args: ("https://n8n.home", "key", False),
        )
        called = {}

        def fake_request_json(**kwargs):
            called.update(kwargs)
            return {"status": 200, "data": {"id": "wf1"}}

        monkeypatch.setattr(get_workflow, "request_json", fake_request_json)

        await get_workflow.execute({"workflow_id": "wf1"}, tmp_path)
        assert called["method"] == "GET"
        assert called["path"] == "/api/v1/workflows/wf1"

    @pytest.mark.asyncio
    async def test_create_requires_object(self, tmp_path: Path):
        result = await create_workflow.execute({"workflow": "bad"}, tmp_path)
        assert "must be an object" in result[0].text

    @pytest.mark.asyncio
    async def test_create_calls_post_with_payload(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(
            create_workflow,
            "resolve_n8n_config",
            lambda args: ("https://n8n.home", "key", True),
        )
        called = {}
        payload = {"name": "flow-x", "nodes": [], "connections": {}}

        def fake_request_json(**kwargs):
            called.update(kwargs)
            return {"status": 201, "data": {"id": "wf-new"}}

        monkeypatch.setattr(create_workflow, "request_json", fake_request_json)

        await create_workflow.execute({"workflow": payload}, tmp_path)
        assert called["method"] == "POST"
        assert called["path"] == "/api/v1/workflows"
        assert called["payload"] == payload
        assert called["insecure_tls"] is True

    @pytest.mark.asyncio
    async def test_create_strips_readonly_fields(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(
            create_workflow,
            "resolve_n8n_config",
            lambda args: ("https://n8n.home", "key", False),
        )
        called = {}

        def fake_request_json(**kwargs):
            called.update(kwargs)
            return {"status": 201, "data": {"id": "wf-new"}}

        monkeypatch.setattr(create_workflow, "request_json", fake_request_json)

        await create_workflow.execute(
            {"workflow": {"name": "x", "nodes": [], "connections": {}, "active": False}},
            tmp_path,
        )
        assert called["payload"]["name"] == "x"
        assert "active" not in called["payload"]

    @pytest.mark.asyncio
    async def test_update_requires_id(self, tmp_path: Path):
        result = await update_workflow.execute({"workflow": {}}, tmp_path)
        assert "workflow_id" in result[0].text

    @pytest.mark.asyncio
    async def test_update_calls_put(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(
            update_workflow,
            "resolve_n8n_config",
            lambda args: ("https://n8n.home", "key", False),
        )
        called = {}

        def fake_request_json(**kwargs):
            called.update(kwargs)
            return {"status": 200, "data": {"id": "wf1"}}

        monkeypatch.setattr(update_workflow, "request_json", fake_request_json)

        result = await update_workflow.execute(
            {"workflow_id": "wf1", "workflow": {"name": "x"}},
            tmp_path,
        )

        assert called["method"] == "PUT"
        assert called["path"] == "/api/v1/workflows/wf1"
        assert '"status": 200' in result[0].text

    @pytest.mark.asyncio
    async def test_update_strips_readonly_fields(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(
            update_workflow,
            "resolve_n8n_config",
            lambda args: ("https://n8n.home", "key", False),
        )
        called = {}

        def fake_request_json(**kwargs):
            called.update(kwargs)
            return {"status": 200, "data": {"id": "wf1"}}

        monkeypatch.setattr(update_workflow, "request_json", fake_request_json)

        await update_workflow.execute(
            {
                "workflow_id": "wf1",
                "workflow": {"name": "x", "active": True, "updatedAt": "now"},
            },
            tmp_path,
        )
        assert called["payload"]["name"] == "x"
        assert "active" not in called["payload"]
        assert "updatedAt" not in called["payload"]

    @pytest.mark.asyncio
    async def test_delete_calls_delete(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(
            delete_workflow,
            "resolve_n8n_config",
            lambda args: ("https://n8n.home", "key", False),
        )
        called = {}

        def fake_request_json(**kwargs):
            called.update(kwargs)
            return {"status": 204, "data": None}

        monkeypatch.setattr(delete_workflow, "request_json", fake_request_json)

        result = await delete_workflow.execute({"workflow_id": "wf1"}, tmp_path)
        assert called["method"] == "DELETE"
        assert called["path"] == "/api/v1/workflows/wf1"
        assert '"status": 204' in result[0].text

    @pytest.mark.asyncio
    async def test_delete_requires_id(self, tmp_path: Path):
        result = await delete_workflow.execute({}, tmp_path)
        assert "workflow_id" in result[0].text
