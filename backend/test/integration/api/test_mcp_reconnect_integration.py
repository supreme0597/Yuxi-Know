from __future__ import annotations

import asyncio
import uuid

import httpx
import pytest

from yuxi.agents.mcp.tool_registry_service import clear_mcp_cache, get_enabled_mcp_tools

pytestmark = [pytest.mark.asyncio(loop_scope="session"), pytest.mark.integration]

_DEMO_BASE_URL = "http://mcp-demo-server:8999"


def _build_server_name() -> str:
    return f"pytest-mcp-reconnect-{uuid.uuid4().hex[:8]}"


async def _create_server(test_client: httpx.AsyncClient, admin_headers: dict[str, str], server_name: str) -> None:
    response = await test_client.post(
        "/api/system/mcp-servers",
        json={
            "name": server_name,
            "transport": "sse",
            "url": f"{_DEMO_BASE_URL}/sse",
            "description": "pytest real MCP reconnect server",
            "timeout": 30,
            "sse_read_timeout": 30,
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
    await test_client.delete(f"/api/system/mcp-servers/{server_name}", headers=admin_headers)
    await test_client.delete(
        f"/api/system/mcp-servers/{server_name}",
        params={"hard": "true"},
        headers=admin_headers,
    )


async def _wait_for_demo_ready(client: httpx.AsyncClient, *, timeout: float = 15.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        try:
            response = await client.get("/test/faults/state")
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.1)
    raise AssertionError("MCP demo server did not become ready after restart")


async def _wait_for_active_tool(
    client: httpx.AsyncClient,
    tool_name: str,
    *,
    timeout: float = 5.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get("/test/faults/state")
        response.raise_for_status()
        active_tools = response.json().get("active_tools") or {}
        if int(active_tools.get(tool_name) or 0) > 0:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"MCP demo tool did not become active: {tool_name}")


def _find_tool(tools, name: str):
    return next(tool for tool in tools if tool.name == name)


async def test_safe_mcp_tool_recovers_after_real_server_restart(test_client, admin_headers):
    server_name = _build_server_name()
    await _create_server(test_client, admin_headers, server_name)
    call_task: asyncio.Task | None = None

    try:
        await clear_mcp_cache()
        tools = await get_enabled_mcp_tools(server_name)
        delayed_tool = _find_tool(tools, "echo_delayed_safe")
        global_tool = _find_tool(tools, "echo_global")

        async with httpx.AsyncClient(base_url=_DEMO_BASE_URL, timeout=20.0) as demo_client:
            await _wait_for_demo_ready(demo_client)
            call_task = asyncio.create_task(
                delayed_tool.ainvoke(
                    {
                        "message": "safe-reconnect-result",
                        "delay_seconds": 5,
                    }
                )
            )
            await _wait_for_active_tool(demo_client, "echo_delayed_safe")

            restart_response = await demo_client.post("/test/faults/restart")
            assert restart_response.status_code == 200, restart_response.text
            assert restart_response.json() == {"restarting": True}

            result = await asyncio.wait_for(call_task, timeout=20.0)
            assert "safe-reconnect-result" in str(result)

            await _wait_for_demo_ready(demo_client)
            follow_up = await global_tool.ainvoke({"message": "after-reconnect"})
            assert "after-reconnect" in str(follow_up)
    finally:
        if call_task is not None:
            if not call_task.done():
                call_task.cancel()
            await asyncio.gather(call_task, return_exceptions=True)
        await _cleanup_server(test_client, admin_headers, server_name)


async def test_unannotated_mcp_tool_is_not_replayed_after_real_server_restart(test_client, admin_headers):
    server_name = _build_server_name()
    await _create_server(test_client, admin_headers, server_name)
    call_task: asyncio.Task | None = None

    try:
        await clear_mcp_cache()
        tools = await get_enabled_mcp_tools(server_name)
        delayed_tool = _find_tool(tools, "echo_delayed_unannotated")
        global_tool = _find_tool(tools, "echo_global")

        async with httpx.AsyncClient(base_url=_DEMO_BASE_URL, timeout=20.0) as demo_client:
            await _wait_for_demo_ready(demo_client)
            call_task = asyncio.create_task(
                delayed_tool.ainvoke(
                    {
                        "message": "must-not-be-replayed",
                        "delay_seconds": 5,
                    }
                )
            )
            await _wait_for_active_tool(demo_client, "echo_delayed_unannotated")

            restart_response = await demo_client.post("/test/faults/restart")
            assert restart_response.status_code == 200, restart_response.text

            result = await asyncio.wait_for(call_task, timeout=10.0)
            result_text = str(result)
            assert "未自动重试" in result_text
            assert "执行结果可能已经生效" in result_text
            assert "must-not-be-replayed" not in result_text

            await _wait_for_demo_ready(demo_client)
            follow_up = await global_tool.ainvoke({"message": "after-unannotated-error"})
            assert "after-unannotated-error" in str(follow_up)
    finally:
        if call_task is not None:
            if not call_task.done():
                call_task.cancel()
            await asyncio.gather(call_task, return_exceptions=True)
        await _cleanup_server(test_client, admin_headers, server_name)
