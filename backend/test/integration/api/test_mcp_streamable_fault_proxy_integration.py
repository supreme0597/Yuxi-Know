from __future__ import annotations

import asyncio
import os
import uuid

import httpx
import pytest
from mcp.shared.exceptions import McpError

from yuxi.agents.mcp.client_pool import mcp_client_pool
from yuxi.agents.mcp.tool_call_recovery import is_mcp_connection_error
from yuxi.agents.mcp.tool_registry_service import clear_mcp_cache, get_enabled_mcp_tools

pytestmark = [pytest.mark.asyncio(loop_scope="session"), pytest.mark.integration]

_FAULT_PROXY_BASE_URL = os.getenv(
    "TEST_MCP_STREAMABLE_FAULT_PROXY_URL",
    "http://mcp-streamable-fault-proxy:8998",
).rstrip("/")
_DEMO_A_BASE_URL = os.getenv("TEST_MCP_STREAMABLE_DEMO_A_URL", "http://mcp-streamable-demo-a:9001").rstrip("/")
_DEMO_B_BASE_URL = os.getenv("TEST_MCP_STREAMABLE_DEMO_B_URL", "http://mcp-streamable-demo-b:9002").rstrip("/")


def _build_server_name() -> str:
    return f"pytest-mcp-streamable-fault-{uuid.uuid4().hex[:8]}"


async def _create_server(
    test_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    server_name: str,
) -> None:
    response = await test_client.post(
        "/api/system/mcp-servers",
        json={
            "name": server_name,
            "transport": "streamable_http",
            "url": f"{_FAULT_PROXY_BASE_URL}/mcp",
            "description": "pytest streamable HTTP fault proxy",
            "headers": {"X-Fault-Case-ID": server_name},
            "timeout": 10,
            "sse_read_timeout": 10,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text


async def _cleanup_server(
    test_client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    server_name: str,
) -> None:
    await clear_mcp_cache()
    soft_delete = await test_client.delete(f"/api/system/mcp-servers/{server_name}", headers=admin_headers)
    hard_delete = await test_client.delete(
        f"/api/system/mcp-servers/{server_name}",
        params={"hard": "true"},
        headers=admin_headers,
    )
    assert soft_delete.status_code in {200, 404}, soft_delete.text
    assert hard_delete.status_code in {200, 404}, hard_delete.text


async def _reset_proxy(client: httpx.AsyncClient, case_id: str) -> None:
    deadline = asyncio.get_running_loop().time() + 15.0
    while asyncio.get_running_loop().time() < deadline:
        try:
            response = await client.post("/test/faults/reset", json={"case_id": case_id})
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.1)
    raise AssertionError("MCP streamable fault proxy did not become ready")


async def _configure_proxy(
    client: httpx.AsyncClient,
    case_id: str,
    mode: str,
    *,
    timeout_seconds: float | None = None,
) -> None:
    payload: dict[str, object] = {"case_id": case_id, "mode": mode, "failures": 1}
    if timeout_seconds is not None:
        payload["timeout_seconds"] = timeout_seconds
    response = await client.post("/test/faults/configure", json=payload)
    assert response.status_code == 200, response.text


async def _proxy_state(client: httpx.AsyncClient, case_id: str) -> dict:
    response = await client.get("/test/faults/state", params={"case_id": case_id})
    assert response.status_code == 200, response.text
    return response.json()


async def _demo_fault_state(base_url: str) -> dict:
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        response = await client.get("/test/faults/state")
    assert response.status_code == 200, response.text
    return response.json()


async def _demo_message_count(base_url: str, message: str) -> int:
    state = await _demo_fault_state(base_url)
    return int((state.get("tool_call_messages") or {}).get(message) or 0)


def _find_tool(tools, name: str):
    return next(tool for tool in tools if tool.name == name)


def _tool_texts(result) -> list[str]:
    if isinstance(result, str):
        return [result]
    if isinstance(result, list):
        return [item["text"] for item in result if isinstance(item, dict) and isinstance(item.get("text"), str)]
    return []


def _session_generation(server_name: str) -> int:
    sessions = [
        value[0]
        for (name, _partition), value in mcp_client_pool._sessions.items()
        if name == server_name and not isinstance(value, asyncio.Future)
    ]
    assert len(sessions) == 1, f"Expected one pooled session for {server_name}, got {len(sessions)}"
    return sessions[0].session.generation


async def _load_tools(server_name: str):
    await clear_mcp_cache()
    return await get_enabled_mcp_tools(server_name)


async def test_fault_proxy_control_state_is_isolated_by_case_id():
    case_a = f"case-a-{uuid.uuid4().hex[:8]}"
    case_b = f"case-b-{uuid.uuid4().hex[:8]}"
    async with httpx.AsyncClient(base_url=_FAULT_PROXY_BASE_URL, timeout=10.0) as proxy_client:
        reset_a = await proxy_client.post("/test/faults/reset", json={"case_id": case_a})
        reset_b = await proxy_client.post("/test/faults/reset", json={"case_id": case_b})
        assert reset_a.status_code == 200, reset_a.text
        assert reset_b.status_code == 200, reset_b.text
        response = await proxy_client.post(
            "/test/faults/configure",
            json={"case_id": case_a, "mode": "abort_tool_response", "failures": 1},
        )
        assert response.status_code == 200, response.text

        state_a = await proxy_client.get("/test/faults/state", params={"case_id": case_a})
        state_b = await proxy_client.get("/test/faults/state", params={"case_id": case_b})
        assert state_a.status_code == 200, state_a.text
        assert state_b.status_code == 200, state_b.text
        assert state_a.json()["mode"] == "abort_tool_response"
        assert state_b.json()["mode"] == "passthrough"


async def test_tool_timeout_starts_response_before_aborting_in_flight_body():
    case_id = f"raw-timeout-{uuid.uuid4().hex[:8]}"
    message = f"raw-timeout-message-{case_id}"
    async with httpx.AsyncClient(base_url=_FAULT_PROXY_BASE_URL, timeout=10.0) as proxy_client:
        await _reset_proxy(proxy_client, case_id)
        headers = {
            "X-Fault-Case-ID": case_id,
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        initialize = await proxy_client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest-fault-proxy", "version": "1.0"},
                },
            },
        )
        assert initialize.status_code == 200, initialize.text
        session_id = initialize.headers.get("mcp-session-id")
        assert session_id
        session_headers = {
            **headers,
            "Mcp-Session-Id": session_id,
            "MCP-Protocol-Version": "2025-03-26",
        }
        initialized = await proxy_client.post(
            "/mcp",
            headers=session_headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        assert initialized.status_code == 202, initialized.text
        await _configure_proxy(proxy_client, case_id, "tool_timeout", timeout_seconds=1.5)

        started_at = asyncio.get_running_loop().time()
        try:
            with pytest.raises(httpx.RemoteProtocolError):
                async with proxy_client.stream(
                    "POST",
                    "/mcp",
                    headers=session_headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "echo_delayed_safe",
                            "arguments": {"message": message, "delay_seconds": 3},
                        },
                    },
                ) as response:
                    headers_elapsed = asyncio.get_running_loop().time() - started_at
                    assert response.status_code == 200
                    assert response.headers["content-type"].startswith("text/event-stream")
                    assert response.headers.get("mcp-session-id") == session_id
                    assert "content-length" not in response.headers
                    assert headers_elapsed < 1.0, "Proxy delayed response headers until the injected timeout"
                    await response.aread()
            aborted_elapsed = asyncio.get_running_loop().time() - started_at
            assert 1.3 <= aborted_elapsed < 2.5
            demo_state = await _demo_fault_state(_DEMO_A_BASE_URL)
            assert demo_state["active_tools"]["echo_delayed_safe"] == 1
            assert await _demo_message_count(_DEMO_A_BASE_URL, message) == 1
        finally:
            try:
                deleted = await proxy_client.delete("/mcp", headers=session_headers)
                assert deleted.status_code in {200, 404}, deleted.text
            finally:
                await _reset_proxy(proxy_client, case_id)


async def test_tools_call_response_abort_times_out_after_upstream_completed_without_replay(
    test_client,
    admin_headers,
):
    server_name = _build_server_name()
    message = f"abort-{server_name}"
    async with httpx.AsyncClient(base_url=_FAULT_PROXY_BASE_URL, timeout=10.0) as proxy_client:
        await _reset_proxy(proxy_client, server_name)
        await _create_server(test_client, admin_headers, server_name)
        try:
            tools = await _load_tools(server_name)
            delayed_tool = _find_tool(tools, "echo_delayed_safe")
            global_tool = _find_tool(tools, "echo_global")
            initial_generation = _session_generation(server_name)
            await _configure_proxy(proxy_client, server_name, "abort_tool_response")

            result = await asyncio.wait_for(
                delayed_tool.ainvoke({"message": message, "delay_seconds": 0}),
                timeout=20.0,
            )

            assert _tool_texts(result) == [
                f"MCP server={server_name} tool=echo_delayed_safe: 调用超时，未自动重试；执行结果可能已经生效。"
            ]
            assert _session_generation(server_name) == initial_generation
            state = await _proxy_state(proxy_client, server_name)
            assert state["faults_triggered"] == 1
            assert state["last_fault"] == "abort_tool_response"
            assert state["last_fault_upstream_completed"] is True
            assert state["method_counts"]["tools/call"] == 1
            assert await _demo_message_count(_DEMO_A_BASE_URL, message) == 1

            follow_up = await global_tool.ainvoke({"message": "after-response-abort"})
            assert _tool_texts(follow_up) == ["[Global Output] 回显内容: after-response-abort"]
            assert _session_generation(server_name) == initial_generation
        finally:
            await _cleanup_server(test_client, admin_headers, server_name)
            await _reset_proxy(proxy_client, server_name)


async def test_stateful_non_sticky_routes_to_peer_and_returns_real_session_terminated(test_client, admin_headers):
    server_name = _build_server_name()
    message = f"wrong-instance-{server_name}"
    async with httpx.AsyncClient(base_url=_FAULT_PROXY_BASE_URL, timeout=10.0) as proxy_client:
        await _reset_proxy(proxy_client, server_name)
        await _create_server(test_client, admin_headers, server_name)
        try:
            tools = await _load_tools(server_name)
            delayed_tool = _find_tool(tools, "echo_delayed_safe")
            initial_generation = _session_generation(server_name)
            await _configure_proxy(proxy_client, server_name, "stateful_non_sticky")

            with pytest.raises(McpError, match="Session terminated") as exc_info:
                await delayed_tool.ainvoke({"message": message, "delay_seconds": 0})

            assert not is_mcp_connection_error(exc_info.value)
            assert _session_generation(server_name) == initial_generation
            state = await _proxy_state(proxy_client, server_name)
            assert state["faults_triggered"] == 1
            assert state["last_fault"] == "stateful_non_sticky"
            assert state["last_fault_upstream_completed"] is True
            assert state["method_counts"]["tools/call"] == 1
            assert state["route_counts"]["1"] == 1
            assert await _demo_message_count(_DEMO_B_BASE_URL, message) == 0
        finally:
            await _cleanup_server(test_client, admin_headers, server_name)
            await _reset_proxy(proxy_client, server_name)


async def test_proxy_timeout_returns_conservative_error_without_replaying_long_tool(test_client, admin_headers):
    server_name = _build_server_name()
    message = f"timeout-{server_name}"
    async with httpx.AsyncClient(base_url=_FAULT_PROXY_BASE_URL, timeout=10.0) as proxy_client:
        await _reset_proxy(proxy_client, server_name)
        await _create_server(test_client, admin_headers, server_name)
        try:
            tools = await _load_tools(server_name)
            delayed_tool = _find_tool(tools, "echo_delayed_safe")
            global_tool = _find_tool(tools, "echo_global")
            initial_generation = _session_generation(server_name)
            await _configure_proxy(proxy_client, server_name, "tool_timeout", timeout_seconds=0.2)

            result = await asyncio.wait_for(
                delayed_tool.ainvoke({"message": message, "delay_seconds": 1}),
                timeout=20.0,
            )

            assert _tool_texts(result) == [
                f"MCP server={server_name} tool=echo_delayed_safe: 调用超时，未自动重试；执行结果可能已经生效。"
            ]
            assert _session_generation(server_name) == initial_generation
            state = await _proxy_state(proxy_client, server_name)
            assert state["faults_triggered"] == 1
            assert state["last_fault"] == "tool_timeout"
            assert state["last_fault_upstream_completed"] is False
            assert state["method_counts"]["tools/call"] == 1
            assert await _demo_message_count(_DEMO_A_BASE_URL, message) == 1

            follow_up = await global_tool.ainvoke({"message": "after-timeout"})
            assert _tool_texts(follow_up) == ["[Global Output] 回显内容: after-timeout"]
            assert _session_generation(server_name) == initial_generation
        finally:
            await _cleanup_server(test_client, admin_headers, server_name)
            await _reset_proxy(proxy_client, server_name)
