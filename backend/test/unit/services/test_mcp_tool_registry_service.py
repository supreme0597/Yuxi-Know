from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from anyio import ClosedResourceError

from yuxi.agents.mcp import server_service
from yuxi.agents.mcp import tool_registry_service
from yuxi.agents.mcp.client_pool import (
    MCPConnectionRecoveringError,
    ReconnectRequestStatus,
    mcp_client_pool,
)
from yuxi.agents.mcp.mcp_tool_cache import RedisMcpToolCache


class _FakeClient:
    def __init__(self, tools):
        self._tools = tools

    async def get_tools(self):
        return self._tools


class _FakeRedis:
    def __init__(self):
        self.data: dict[str, str] = {}
        self.expire_calls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.data[key] = value
        if ex is not None:
            self.expire_calls[key] = ex

    async def incr(self, key: str) -> int:
        next_value = int(self.data.get(key) or "0") + 1
        self.data[key] = str(next_value)
        return next_value


async def test_get_enabled_mcp_tools_loads_latest_config_from_db(monkeypatch):
    captured: list[dict] = []

    async def fake_get_enabled_mcp_server_config(server_name: str, db=None):
        del db
        assert server_name == "demo"
        return {"transport": "stdio", "command": "demo", "disabled_tools": ["tool_b"]}

    async def fake_get_mcp_tools(server_name: str, additional_servers=None, disabled_tools=None, **kwargs):
        del kwargs
        captured.append(
            {
                "server_name": server_name,
                "additional_servers": additional_servers,
                "disabled_tools": list(disabled_tools or []),
            }
        )
        return ["tool-a"]

    monkeypatch.setattr(server_service, "get_enabled_mcp_server_config", fake_get_enabled_mcp_server_config)
    monkeypatch.setattr(tool_registry_service, "get_mcp_tools", fake_get_mcp_tools)

    tools = await tool_registry_service.get_enabled_mcp_tools("demo")

    assert tools == ["tool-a"]
    assert captured == [
        {
            "server_name": "demo",
            "additional_servers": {"demo": {"transport": "stdio", "command": "demo", "disabled_tools": ["tool_b"]}},
            "disabled_tools": ["tool_b"],
        }
    ]


async def test_get_mcp_tools_rebuilds_cache_when_config_hash_changes(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    configs = [
        {"transport": "stdio", "command": "demo-v1", "disabled_tools": []},
        {"transport": "stdio", "command": "demo-v2", "disabled_tools": []},
    ]
    build_calls: list[str] = []

    async def fake_get_enabled_mcp_server_config(server_name: str, db=None):
        del db
        assert server_name == "demo"
        return configs[0]

    async def fake_get_mcp_client(server_configs):
        config = server_configs["demo"]
        build_calls.append(config["command"])
        tool = SimpleNamespace(name=f"tool_for_{config['command']}", metadata={})
        return _FakeClient([tool])

    monkeypatch.setattr(server_service, "get_enabled_mcp_server_config", fake_get_enabled_mcp_server_config)
    monkeypatch.setattr(mcp_client_pool, "_get_mcp_client", fake_get_mcp_client)

    tools_v1_first = await tool_registry_service.get_mcp_tools("demo")
    tools_v1_second = await tool_registry_service.get_mcp_tools("demo")

    configs[0] = configs[1]
    tools_v2 = await tool_registry_service.get_mcp_tools("demo")

    assert [tool.name for tool in tools_v1_first] == ["tool_for_demo-v1"]
    assert [tool.name for tool in tools_v1_second] == ["tool_for_demo-v1"]
    assert [tool.name for tool in tools_v2] == ["tool_for_demo-v2"]
    assert build_calls == ["demo-v1", "demo-v2"]

    await tool_registry_service.clear_mcp_cache()


async def test_get_tools_from_all_servers_loads_names_from_db_once(monkeypatch):
    server_configs = {
        "alpha": {"transport": "stdio", "command": "cmd-a", "disabled_tools": []},
        "beta": {"transport": "stdio", "command": "cmd-b", "disabled_tools": []},
    }
    calls: list[tuple[str, dict[str, dict]]] = []

    async def fake_load_enabled_mcp_server_configs(*, names=None, db=None):
        del names, db
        return server_configs

    async def fake_get_mcp_tools(server_name: str, additional_servers=None, **kwargs):
        del kwargs
        calls.append((server_name, additional_servers or {}))
        return [server_name]

    monkeypatch.setattr(server_service, "_load_enabled_mcp_server_configs", fake_load_enabled_mcp_server_configs)
    monkeypatch.setattr(tool_registry_service, "get_mcp_tools", fake_get_mcp_tools)

    tools = await tool_registry_service.get_tools_from_all_servers()

    assert tools == ["alpha", "beta"]
    assert calls == [
        ("alpha", {"alpha": server_configs["alpha"]}),
        ("beta", {"beta": server_configs["beta"]}),
    ]


async def test_get_tools_from_all_servers_limits_preload_to_selected_names(monkeypatch):
    server_configs = {
        "alpha": {"transport": "stdio", "command": "cmd-a", "disabled_tools": []},
        "beta": {"transport": "stdio", "command": "cmd-b", "disabled_tools": []},
    }
    loaded_names: list[list[str] | None] = []
    calls: list[str] = []

    async def fake_load_enabled_mcp_server_configs(*, names=None, db=None):
        del db
        loaded_names.append(names)
        if not names:
            return server_configs
        return {name: server_configs[name] for name in names if name in server_configs}

    async def fake_get_mcp_tools(server_name: str, additional_servers=None, **kwargs):
        del additional_servers, kwargs
        calls.append(server_name)
        return [server_name]

    monkeypatch.setattr(server_service, "_load_enabled_mcp_server_configs", fake_load_enabled_mcp_server_configs)
    monkeypatch.setattr(tool_registry_service, "get_mcp_tools", fake_get_mcp_tools)

    tools = await tool_registry_service.get_tools_from_all_servers(["alpha", "alpha", "missing"])
    empty_tools = await tool_registry_service.get_tools_from_all_servers([])

    assert tools == ["alpha"]
    assert empty_tools == []
    assert loaded_names == [["alpha", "missing"]]
    assert calls == ["alpha"]


async def test_get_mcp_tools_sets_handle_tool_error(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    config = {"transport": "stdio", "command": "demo-tool", "disabled_tools": []}

    async def fake_get_enabled_mcp_server_config(server_name: str, db=None):
        del db
        return config

    async def fake_get_mcp_client(server_configs):
        tool = SimpleNamespace(name="demo_tool", metadata={})
        return _FakeClient([tool])

    monkeypatch.setattr(server_service, "get_enabled_mcp_server_config", fake_get_enabled_mcp_server_config)
    monkeypatch.setattr(mcp_client_pool, "_get_mcp_client", fake_get_mcp_client)

    tools = await tool_registry_service.get_mcp_tools("demo")
    assert len(tools) == 1
    assert tools[0].handle_tool_error is True

    await tool_registry_service.clear_mcp_cache()


async def test_get_mcp_tools_installs_recovery_interceptor_and_binds_annotations(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    config = {"transport": "sse", "url": "http://demo.local/sse", "disabled_tools": []}
    session_proxy = SimpleNamespace(generation=1, is_connected=True)
    captured: dict[str, object] = {}

    class FakeRecoveryInterceptor:
        def __init__(self, *, session_proxy, reconnect_wait_seconds):
            captured["interceptor_session"] = session_proxy
            captured["reconnect_wait_seconds"] = reconnect_wait_seconds
            captured["recovery"] = self
            self.bound_tool_names = None

        def bind_retryable_tools(self, tool_names):
            self.bound_tool_names = frozenset(tool_names)
            captured["bound_tool_names"] = self.bound_tool_names

    async def fake_get_session(server_name, partition_key, runtime_config):
        assert server_name == "demo"
        assert partition_key == "server:s0:p0"
        assert runtime_config == {"transport": "sse", "url": "http://demo.local/sse"}
        return session_proxy

    async def fake_load_mcp_tools(session, *, server_name, tool_interceptors):
        captured["adapter_session"] = session
        captured["server_name"] = server_name
        captured["tool_interceptors"] = tool_interceptors
        return [
            SimpleNamespace(name="read_tool", metadata={"readOnlyHint": True}),
            SimpleNamespace(name="idempotent_tool", metadata={"idempotentHint": True}),
            SimpleNamespace(name="write_tool", metadata=None),
        ]

    monkeypatch.setattr(mcp_client_pool, "get_session", fake_get_session)
    monkeypatch.setattr(tool_registry_service, "MCPToolCallRecoveryInterceptor", FakeRecoveryInterceptor)
    monkeypatch.setattr("langchain_mcp_adapters.tools.load_mcp_tools", fake_load_mcp_tools)

    tools = await tool_registry_service.get_mcp_tools(
        "demo",
        additional_servers={"demo": config},
        cache=False,
    )

    assert captured["interceptor_session"] is session_proxy
    assert captured["adapter_session"] is session_proxy
    assert captured["server_name"] == "demo"
    assert captured["tool_interceptors"] == [captured["recovery"]]
    assert captured["bound_tool_names"] == frozenset({"read_tool", "idempotent_tool"})
    assert [tool.metadata["id"] for tool in tools] == [
        "mcp__demo__readTool",
        "mcp__demo__idempotentTool",
        "mcp__demo__writeTool",
    ]
    assert all(tool.metadata["mcp_server_name"] == "demo" for tool in tools)
    assert all(tool.handle_tool_error is True for tool in tools)

    await tool_registry_service.clear_mcp_cache()


async def test_get_mcp_tools_keeps_pool_entry_when_connection_is_recovering(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    config = {"transport": "sse", "url": "http://demo.local/sse", "disabled_tools": []}
    record_failure = MagicMock()
    remove_session = AsyncMock()
    remove_sessions_by_server = AsyncMock()

    async def recovering_get_session(server_name, partition_key, runtime_config):
        del partition_key, runtime_config
        raise MCPConnectionRecoveringError(server_name, 0.01)

    monkeypatch.setattr(mcp_client_pool, "get_session", recovering_get_session)
    monkeypatch.setattr(mcp_client_pool, "remove_session", remove_session)
    monkeypatch.setattr(mcp_client_pool, "remove_sessions_by_server", remove_sessions_by_server)
    monkeypatch.setattr(tool_registry_service, "_record_mcp_tool_failure", record_failure)

    tools = await tool_registry_service.get_mcp_tools(
        "demo",
        additional_servers={"demo": config},
        cache=False,
    )

    assert tools == []
    record_failure.assert_not_called()
    remove_session.assert_not_awaited()
    remove_sessions_by_server.assert_not_awaited()

    await tool_registry_service.clear_mcp_cache()


async def test_get_mcp_tools_requests_reconnect_when_adapter_list_tools_disconnects(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    config = {"transport": "sse", "url": "http://demo.local/sse", "disabled_tools": []}
    reconnect_requests: list[int] = []
    session_proxy = SimpleNamespace(
        generation=7,
        is_connected=True,
        request_reconnect=lambda generation: (
            reconnect_requests.append(generation) or ReconnectRequestStatus.ACCEPTED
        ),
    )
    record_failure = MagicMock()
    remove_session = AsyncMock()
    remove_sessions_by_server = AsyncMock()

    async def fake_get_session(server_name, partition_key, runtime_config):
        del server_name, partition_key, runtime_config
        return session_proxy

    async def disconnected_load_mcp_tools(session, *, server_name, tool_interceptors):
        del session, server_name, tool_interceptors
        raise ClosedResourceError

    monkeypatch.setattr(mcp_client_pool, "get_session", fake_get_session)
    monkeypatch.setattr(mcp_client_pool, "remove_session", remove_session)
    monkeypatch.setattr(mcp_client_pool, "remove_sessions_by_server", remove_sessions_by_server)
    monkeypatch.setattr(tool_registry_service, "_record_mcp_tool_failure", record_failure)
    monkeypatch.setattr("langchain_mcp_adapters.tools.load_mcp_tools", disconnected_load_mcp_tools)

    tools = await tool_registry_service.get_mcp_tools(
        "demo",
        additional_servers={"demo": config},
        cache=False,
    )

    assert tools == []
    assert reconnect_requests == [7]
    record_failure.assert_not_called()
    remove_session.assert_not_awaited()
    remove_sessions_by_server.assert_not_awaited()

    await tool_registry_service.clear_mcp_cache()


async def test_get_mcp_tools_requests_reconnect_for_list_generation_when_owner_advanced(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    config = {"transport": "sse", "url": "http://demo.local/sse", "disabled_tools": []}
    reconnect_requests: list[int] = []
    session_proxy = SimpleNamespace(generation=7, is_connected=True)

    def request_reconnect(generation):
        reconnect_requests.append(generation)
        return ReconnectRequestStatus.STALE_GENERATION

    session_proxy.request_reconnect = request_reconnect
    record_failure = MagicMock()
    remove_session = AsyncMock()

    async def fake_get_session(server_name, partition_key, runtime_config):
        del server_name, partition_key, runtime_config
        return session_proxy

    async def disconnected_load_mcp_tools(session, *, server_name, tool_interceptors):
        del server_name, tool_interceptors
        session.generation = 8
        raise ClosedResourceError

    monkeypatch.setattr(mcp_client_pool, "get_session", fake_get_session)
    monkeypatch.setattr(mcp_client_pool, "remove_session", remove_session)
    monkeypatch.setattr(tool_registry_service, "_record_mcp_tool_failure", record_failure)
    monkeypatch.setattr("langchain_mcp_adapters.tools.load_mcp_tools", disconnected_load_mcp_tools)

    tools = await tool_registry_service.get_mcp_tools(
        "demo",
        additional_servers={"demo": config},
        cache=False,
    )

    assert tools == []
    assert reconnect_requests == [7]
    record_failure.assert_not_called()
    remove_session.assert_not_awaited()

    await tool_registry_service.clear_mcp_cache()


async def test_get_mcp_tools_retries_connection_errors_without_cooldown(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    config = {"transport": "stdio", "command": "offline-demo", "disabled_tools": []}
    build_calls: list[dict] = []

    async def fail_get_mcp_client(server_configs):
        build_calls.append(server_configs)
        raise ConnectionError("mcp service offline")

    monkeypatch.setattr(mcp_client_pool, "_get_mcp_client", fail_get_mcp_client)

    tools_first = await tool_registry_service.get_mcp_tools("offline", additional_servers={"offline": config})
    tools_second = await tool_registry_service.get_mcp_tools("offline", additional_servers={"offline": config})
    tools_forced = await tool_registry_service.get_mcp_tools(
        "offline",
        additional_servers={"offline": config},
        force_refresh=True,
    )

    assert tools_first == []
    assert tools_second == []
    assert tools_forced == []
    assert len(build_calls) == 3

    await tool_registry_service.clear_mcp_cache()


async def test_get_mcp_tools_keeps_connection_partitions_separate(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    configs = [
        {
            "transport": "streamable_http",
            "url": "http://finance.local/mcp",
            "headers": {"X-App": "yuxi"},
            "__yuxi_cache_partition": "connection:101",
            "__yuxi_allow_global_cache": False,
        },
        {
            "transport": "streamable_http",
            "url": "http://finance.local/mcp",
            "headers": {"X-App": "yuxi"},
            "__yuxi_cache_partition": "connection:202",
            "__yuxi_allow_global_cache": False,
        },
    ]
    build_count = 0

    async def fake_get_mcp_client(server_configs):
        nonlocal build_count
        assert server_configs["demo"]["url"] == "http://finance.local/mcp"
        build_count += 1
        tool = SimpleNamespace(name=f"tool_for_connection_{build_count}", metadata={})
        return _FakeClient([tool])

    monkeypatch.setattr(mcp_client_pool, "_get_mcp_client", fake_get_mcp_client)

    tools_a = await tool_registry_service.get_mcp_tools("demo", additional_servers={"demo": configs[0]})
    tools_b = await tool_registry_service.get_mcp_tools("demo", additional_servers={"demo": configs[1]})

    assert [tool.name for tool in tools_a] == ["tool_for_connection_1"]
    assert [tool.name for tool in tools_b] == ["tool_for_connection_2"]
    assert build_count == 2

    await tool_registry_service.clear_mcp_cache()


async def test_get_mcp_tools_caches_dynamic_token_tool_objects(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    config = {
        "transport": "streamable_http",
        "url": "http://finance.local/mcp",
        "headers": {"X-App": "yuxi"},
        "auth_config": {
            "version": 1,
            "provider": "custom_http_token",
            "binding_scope": "user",
            "inject": {
                "target": "headers",
                "entries": [{"name": "Authorization", "value_template": "Bearer ${access_token}"}],
            },
            "token_request": {
                "url": "http://gateway.local/auth/token",
                "method": "POST",
                "response_map": {"access_token": "access_token"},
            },
        },
        "__yuxi_cache_partition": "connection:101",
        "__yuxi_allow_global_cache": False,
    }
    build_count = 0

    async def fake_get_mcp_client(server_configs):
        nonlocal build_count
        assert server_configs["demo"]["url"] == "http://finance.local/mcp"
        build_count += 1
        return _FakeClient([SimpleNamespace(name="finance_tool", metadata={})])

    monkeypatch.setattr(mcp_client_pool, "_get_mcp_client", fake_get_mcp_client)

    tools_first = await tool_registry_service.get_mcp_tools("demo", additional_servers={"demo": config})
    tools_second = await tool_registry_service.get_mcp_tools("demo", additional_servers={"demo": config})

    assert [tool.name for tool in tools_first] == ["finance_tool"]
    assert tools_second is tools_first
    assert build_count == 1

    await tool_registry_service.clear_mcp_cache()


async def test_get_tools_from_all_servers_skips_runtime_auth_servers_without_context(monkeypatch):
    server_configs = {
        "shared": {"transport": "stdio", "command": "cmd-shared", "disabled_tools": []},
        "bound": {
            "transport": "streamable_http",
            "url": "http://bound.local/mcp",
            "auth_config": {
                "version": 1,
                "provider": "custom_http_token",
                "binding_scope": "department",
                "inject": {
                    "target": "headers",
                    "entries": [{"name": "Authorization", "value_template": "Bearer ${access_token}"}],
                },
                "token_request": {
                    "url": "http://bound.local/token",
                    "method": "POST",
                    "response_map": {"access_token": "access_token"},
                },
            },
            "disabled_tools": [],
        },
    }
    calls: list[tuple[str, dict[str, dict]]] = []

    async def fake_load_enabled_mcp_server_configs(*, names=None, db=None):
        del names, db
        return server_configs

    async def fake_get_mcp_tools(server_name: str, additional_servers=None, **kwargs):
        del kwargs
        calls.append((server_name, additional_servers or {}))
        return [server_name]

    monkeypatch.setattr(server_service, "_load_enabled_mcp_server_configs", fake_load_enabled_mcp_server_configs)
    monkeypatch.setattr(tool_registry_service, "get_mcp_tools", fake_get_mcp_tools)

    tools = await tool_registry_service.get_tools_from_all_servers()

    assert tools == ["shared"]
    assert calls == [
        ("shared", {"shared": server_configs["shared"]}),
    ]


async def test_get_mcp_tools_rebuilds_when_redis_server_revision_changes(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    fake_redis = _FakeRedis()

    async def fake_redis_factory():
        return fake_redis

    monkeypatch.setattr(tool_registry_service, "_mcp_tool_cache_store",
                        RedisMcpToolCache(redis_client_factory=fake_redis_factory),
                        )

    config = {"transport": "stdio", "command": "demo-tool", "disabled_tools": []}
    build_calls: list[str] = []

    async def fake_get_mcp_client(server_configs):
        build_calls.append(server_configs["demo"]["command"])
        tool = SimpleNamespace(name=f"tool_{len(build_calls)}", metadata={})
        return _FakeClient([tool])

    monkeypatch.setattr(mcp_client_pool, "_get_mcp_client", fake_get_mcp_client)

    tools_first = await tool_registry_service.get_mcp_tools("demo", additional_servers={"demo": config})
    tools_second = await tool_registry_service.get_mcp_tools("demo", additional_servers={"demo": config})
    await tool_registry_service._mcp_tool_cache_store.bump_server_revision("demo")
    tools_third = await tool_registry_service.get_mcp_tools("demo", additional_servers={"demo": config})

    assert [tool.name for tool in tools_first] == ["tool_1"]
    assert [tool.name for tool in tools_second] == ["tool_1"]
    assert [tool.name for tool in tools_third] == ["tool_2"]
    assert build_calls == ["demo-tool", "demo-tool"]

    await tool_registry_service.clear_mcp_cache()


async def test_get_all_mcp_tools_uses_redis_manifest_when_local_cache_is_empty(monkeypatch):
    await tool_registry_service.clear_mcp_cache()

    fake_redis = _FakeRedis()

    async def fake_redis_factory():
        return fake_redis

    monkeypatch.setattr(tool_registry_service, "_mcp_tool_cache_store",
                        RedisMcpToolCache(redis_client_factory=fake_redis_factory),
                        )

    config = {"transport": "stdio", "command": "demo-tool", "disabled_tools": []}

    async def fake_get_mcp_client(server_configs):
        del server_configs
        tool = SimpleNamespace(
            name="alpha_tool",
            description="alpha",
            metadata={},
            args_schema=SimpleNamespace(
                schema=lambda: {
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                }
            ),
        )
        return _FakeClient([tool])

    async def fake_get_enabled_mcp_server_config(server_name: str, db=None):
        del server_name, db
        return config

    monkeypatch.setattr(server_service, "get_enabled_mcp_server_config", fake_get_enabled_mcp_server_config)
    monkeypatch.setattr(mcp_client_pool, "_get_mcp_client", fake_get_mcp_client)

    tools_first = await tool_registry_service.get_all_mcp_tools("demo")
    assert [tool.name for tool in tools_first] == ["alpha_tool"]

    await tool_registry_service.clear_mcp_cache()

    async def fail_get_mcp_client(server_configs):
        raise AssertionError(f"should not fetch live tools when redis manifest is available: {server_configs}")

    monkeypatch.setattr(mcp_client_pool, "_get_mcp_client", fail_get_mcp_client)

    tools_second = await tool_registry_service.get_all_mcp_tools("demo")

    assert [tool.name for tool in tools_second] == ["alpha_tool"]
    assert tools_second[0].metadata["id"] == "mcp__demo__alphaTool"
