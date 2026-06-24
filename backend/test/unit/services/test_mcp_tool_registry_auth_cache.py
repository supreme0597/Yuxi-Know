from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from yuxi.services.mcp import tool_registry_service
from yuxi.services.mcp_auth.orchestrator import AuthContext, mcp_auth_context_var

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


class FakeClient:
    async def get_tools(self):
        return [SimpleNamespace(name="lookup", metadata=None)]


async def test_get_mcp_tools_bypasses_global_cache_for_runtime_credentials(monkeypatch):
    tool_registry_service.clear_mcp_cache()
    captured_configs: list[dict] = []

    async def fake_get_mcp_client(server_configs):
        captured_configs.append(server_configs["billing"])
        return FakeClient()

    async def fake_resolve_runtime_mcp_config(server_name, server_config, *, auth_context=None, db=None):
        assert server_name == "billing"
        assert auth_context is not None
        resolved = {key: value for key, value in server_config.items() if key != "auth_config"}
        resolved["headers"] = {"Authorization": f"Bearer user-{auth_context.user_id}"}
        return resolved

    monkeypatch.setattr(tool_registry_service, "get_mcp_client", fake_get_mcp_client)
    monkeypatch.setattr(
        tool_registry_service, "resolve_runtime_mcp_config", fake_resolve_runtime_mcp_config, raising=False
    )

    server_config = {
        "transport": "streamable_http",
        "url": "http://billing.local/mcp",
        "auth_config": {
            "version": 1,
            "provider": "bound_secret",
            "binding_scope": "user",
            "inject": {
                "target": "headers",
                "entries": [{"name": "Authorization", "value_template": "Bearer ${secret.access_token}"}],
            },
        },
    }

    token = mcp_auth_context_var.set(AuthContext(user_id="1", work_id="W-1", department_id="9"))
    try:
        await tool_registry_service.get_mcp_tools("billing", additional_servers={"billing": server_config})
    finally:
        mcp_auth_context_var.reset(token)

    token = mcp_auth_context_var.set(AuthContext(user_id="2", work_id="W-2", department_id="9"))
    try:
        await tool_registry_service.get_mcp_tools("billing", additional_servers={"billing": server_config})
    finally:
        mcp_auth_context_var.reset(token)

    assert [config["headers"]["Authorization"] for config in captured_configs] == [
        "Bearer user-1",
        "Bearer user-2",
    ]


async def test_get_mcp_tools_uses_sanitized_error_log(monkeypatch):
    tool_registry_service.clear_mcp_cache()
    logged_messages: list[str] = []

    class DummyLogger:
        def warning(self, *args, **kwargs):
            del args, kwargs

        def debug(self, *args, **kwargs):
            del args, kwargs

        def info(self, *args, **kwargs):
            del args, kwargs

        def error(self, *args, **kwargs):
            del kwargs
            logged_messages.append(" ".join(str(arg) for arg in args))

    async def fake_get_mcp_client(server_configs):
        del server_configs
        raise RuntimeError("adapter failed with token secret-token")

    monkeypatch.setattr(tool_registry_service, "logger", DummyLogger())
    monkeypatch.setattr(tool_registry_service, "get_mcp_client", fake_get_mcp_client)

    tools = await tool_registry_service.get_mcp_tools(
        "billing",
        additional_servers={"billing": {"transport": "stdio", "command": "cmd", "env": {"API_TOKEN": "secret-token"}}},
        force_refresh=True,
    )

    assert tools == []
    assert logged_messages
    assert "secret-token" not in "\n".join(logged_messages)
