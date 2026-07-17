from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from yuxi.services.mcp import tool_registry_service
from yuxi.services.mcp.cache_policy import MCPCachePolicy
from yuxi.services.mcp_auth.orchestrator import (
    AuthContext,
    ResolvedMCPRuntime,
    mcp_auth_context_var,
)

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

    async def fake_resolve_runtime_mcp(server_name, server_config, *, auth_context=None, db=None):
        del db
        assert server_name == "billing"
        assert auth_context is not None
        resolved = {key: value for key, value in server_config.items() if key != "auth_config"}
        resolved["headers"] = {"Authorization": f"Bearer user-{auth_context.user_id}"}
        return ResolvedMCPRuntime(
            config=resolved,
            cache_policy=MCPCachePolicy(f"context:user:{auth_context.user_id}", True, True, False),
            cache_identity={"transport": "streamable_http", "user": auth_context.user_id},
        )

    monkeypatch.setattr(tool_registry_service, "get_mcp_client", fake_get_mcp_client)
    monkeypatch.setattr(tool_registry_service, "resolve_runtime_mcp", fake_resolve_runtime_mcp, raising=False)

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


async def test_get_all_mcp_tools_passes_explicit_auth_context(monkeypatch):
    auth_context = AuthContext(user_id="42", work_id="W-7", department_id="9")
    captured: list[AuthContext | None] = []

    async def fake_get_enabled_mcp_server_config(server_name):
        assert server_name == "billing"
        return {"transport": "streamable_http", "url": "http://billing.local/mcp"}

    async def fake_get_mcp_tools(server_name, **kwargs):
        assert server_name == "billing"
        captured.append(kwargs.get("auth_context"))
        return []

    monkeypatch.setattr(
        tool_registry_service,
        "get_enabled_mcp_server_config",
        fake_get_enabled_mcp_server_config,
    )
    monkeypatch.setattr(tool_registry_service, "get_mcp_tools", fake_get_mcp_tools)

    await tool_registry_service.get_all_mcp_tools("billing", auth_context=auth_context)

    assert captured == [auth_context]


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


class FakeManifestCache:
    def __init__(self):
        self.manifests: dict[str, dict] = {}

    async def get_revisions(self, server_name, partition):
        return (0, 0)

    def build_cache_key(self, server_name, partition, revisions, config_hash):
        return f"{server_name}:{partition}:s{revisions[0]}:p{revisions[1]}:{config_hash}"

    async def get_manifest(self, cache_key):
        return self.manifests.get(cache_key)

    async def set_manifest(self, cache_key, manifest):
        self.manifests[cache_key] = manifest


async def test_dynamic_provider_uses_manifest_without_caching_tool_object(monkeypatch):
    tool_registry_service.clear_mcp_cache()
    manifest_cache = FakeManifestCache()
    discovery_calls = 0

    async def fake_resolve_runtime_mcp(server_name, server_config, **kwargs):
        del server_name, server_config, kwargs
        return ResolvedMCPRuntime(
            config={
                "transport": "streamable_http",
                "url": "http://billing.local/mcp",
                "headers": {"Authorization": "Bearer short"},
            },
            cache_policy=MCPCachePolicy("connection:31", False, True, False),
            cache_identity={
                "transport": "streamable_http",
                "url": "http://billing.local/mcp",
                "auth": {"provider": "client_credentials"},
            },
            connection_id=31,
        )

    class DiscoveryClient:
        async def get_tools(self):
            nonlocal discovery_calls
            discovery_calls += 1

            async def ainvoke(payload):
                return payload

            return [
                SimpleNamespace(
                    name="lookup",
                    description="Lookup",
                    metadata=None,
                    args_schema={"type": "object", "properties": {"q": {"type": "string"}}},
                    ainvoke=ainvoke,
                )
            ]

    monkeypatch.setattr(tool_registry_service, "resolve_runtime_mcp", fake_resolve_runtime_mcp, raising=False)
    monkeypatch.setattr(
        tool_registry_service,
        "get_mcp_client",
        lambda configs: __import__("asyncio").sleep(0, result=DiscoveryClient()),
    )
    monkeypatch.setattr(tool_registry_service, "_manifest_cache", manifest_cache, raising=False)

    server_config = {
        "transport": "streamable_http",
        "url": "http://billing.local/mcp",
        "auth_config": {
            "provider": "client_credentials",
            "binding_scope": "user",
            "inject": {"target": "headers", "entries": []},
            "token_request": {"url": "http://auth.local/token"},
        },
    }
    first = await tool_registry_service.get_mcp_tools("billing", additional_servers={"billing": server_config})
    second = await tool_registry_service.get_mcp_tools("billing", additional_servers={"billing": server_config})

    assert [tool.name for tool in first] == ["lookup"]
    assert [tool.name for tool in second] == ["lookup"]
    assert discovery_calls == 1
    assert tool_registry_service._mcp_tools_cache == {}
    assert manifest_cache.manifests


async def test_manifest_backed_tool_resolves_current_runtime_before_invocation(monkeypatch):
    tool_registry_service.clear_mcp_cache()
    manifest_cache = FakeManifestCache()
    resolve_calls = 0
    client_calls = 0

    async def fake_resolve_runtime_mcp(server_name, server_config, **kwargs):
        nonlocal resolve_calls
        del server_name, server_config, kwargs
        resolve_calls += 1
        return ResolvedMCPRuntime(
            config={
                "transport": "streamable_http",
                "url": "http://billing.local/mcp",
                "headers": {"Authorization": f"Bearer token-{resolve_calls}"},
            },
            cache_policy=MCPCachePolicy("connection:31", False, True, False),
            cache_identity={
                "transport": "streamable_http",
                "url": "http://billing.local/mcp",
                "auth": {"provider": "client_credentials"},
            },
            connection_id=31,
        )

    class InvokeClient:
        async def get_tools(self):
            nonlocal client_calls
            client_calls += 1

            class UpstreamTool:
                name = "lookup"
                description = "Lookup"
                metadata = None
                args_schema = {"type": "object", "properties": {"q": {"type": "string"}}}

                async def ainvoke(self, payload):
                    return {"query": payload["q"], "auth": f"token-{resolve_calls}"}

            return [UpstreamTool()]

    async def fake_get_mcp_client(configs):
        del configs
        return InvokeClient()

    monkeypatch.setattr(tool_registry_service, "resolve_runtime_mcp", fake_resolve_runtime_mcp, raising=False)
    monkeypatch.setattr(tool_registry_service, "get_mcp_client", fake_get_mcp_client)
    monkeypatch.setattr(tool_registry_service, "_manifest_cache", manifest_cache, raising=False)

    server_config = {
        "transport": "streamable_http",
        "url": "http://billing.local/mcp",
        "auth_config": {
            "provider": "client_credentials",
            "binding_scope": "user",
            "inject": {"target": "headers", "entries": []},
            "token_request": {"url": "http://auth.local/token"},
        },
    }
    await tool_registry_service.get_mcp_tools("billing", additional_servers={"billing": server_config})
    client_calls = 0
    tools = await tool_registry_service.get_mcp_tools("billing", additional_servers={"billing": server_config})
    result = await tools[0].ainvoke({"q": "invoice"})

    assert client_calls == 1
    assert resolve_calls == 3
    assert result == {"query": "invoice", "auth": "token-3"}
