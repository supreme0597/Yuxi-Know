from __future__ import annotations

import asyncio
import copy
import json
import uuid

import httpx
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.e2e, pytest.mark.slow]

_DEMO_BASE_URL = "http://mcp-demo-server:8999"


async def _create_server(client: httpx.AsyncClient, headers: dict[str, str], server_name: str) -> None:
    response = await client.post(
        "/api/system/mcp-servers",
        json={
            "name": server_name,
            "transport": "sse",
            "url": f"{_DEMO_BASE_URL}/sse",
            "description": "E2E MCP reconnect server",
            "timeout": 30,
            "sse_read_timeout": 30,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text


async def _create_agent_config(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    agent_id: str,
    base_config_id: int,
    server_name: str,
    delayed_tool_name: str,
) -> int:
    response = await client.get(f"/api/chat/agent/{agent_id}/configs/{base_config_id}", headers=headers)
    assert response.status_code == 200, response.text
    source_config = response.json()["config"]
    config_json = copy.deepcopy(source_config.get("config_json") or {})
    context = config_json.setdefault("context", {})
    assert isinstance(context, dict), source_config

    if delayed_tool_name == "echo_delayed_safe":
        recovery_rule = (
            "当用户消息是 RECOVERY_TEST 时，只调用 echo_delayed_safe 一次，参数 message 必须是 "
            "e2e-safe-reconnect，delay_seconds 必须是 12；工具返回后直接回答工具结果。"
        )
    else:
        recovery_rule = (
            "当用户消息是 RECOVERY_TEST 时，只调用 echo_delayed_unannotated 一次，参数 message 必须是 "
            "e2e-unannotated-reconnect，delay_seconds 必须是 12；如果工具返回错误，不得再次调用任何工具，"
            "直接说明工具未自动重试且执行结果可能已经生效。"
        )

    context.update(
        {
            "system_prompt": (
                "你正在执行 MCP 断线恢复端到端测试，必须严格遵守以下规则。"
                f"{recovery_rule}"
                "当用户消息是 FOLLOW_UP 时，只调用 echo_global 一次，参数 message 必须是 after-reconnect，"
                "然后直接回答工具结果。不要调用未指定的工具。"
            ),
            "tools": [],
            "knowledges": [],
            "mcps": [server_name],
            "skills": [],
            "subagents": [],
        }
    )

    response = await client.post(
        f"/api/chat/agent/{agent_id}/configs",
        json={
            "name": f"mcp-reconnect-e2e-{uuid.uuid4().hex[:8]}",
            "description": "Dedicated MCP reconnect E2E config",
            "config_json": config_json,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return int(response.json()["config"]["id"])


async def _create_thread(client: httpx.AsyncClient, headers: dict[str, str], agent_id: str) -> str:
    response = await client.post(
        "/api/chat/thread",
        json={"agent_id": agent_id, "title": f"mcp-reconnect-e2e-{uuid.uuid4().hex[:8]}", "metadata": {}},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    thread_id = payload.get("thread_id") or payload.get("id")
    assert thread_id, payload
    return str(thread_id)


async def _stream_chat(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    thread_id: str,
    agent_config_id: int,
    query: str,
) -> list[dict]:
    async with client.stream(
        "POST",
        "/api/chat/agent",
        json={"query": query, "agent_config_id": agent_config_id, "thread_id": thread_id},
        headers=headers,
    ) as response:
        if response.status_code != 200:
            body = (await response.aread()).decode(errors="replace")
            pytest.fail(f"Streaming chat failed before body consumption: status={response.status_code}, body={body}")
        return [json.loads(line) async for line in response.aiter_lines() if line]


async def _restart_demo_during_tool_call(
    demo_client: httpx.AsyncClient,
    chat_task: asyncio.Task[list[dict]],
    tool_name: str,
    *,
    timeout: float = 60.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if chat_task.done():
            events = await chat_task
            raise AssertionError(f"Chat completed before {tool_name} became active: {events}")
        try:
            response = await demo_client.get("/test/faults/state")
            if response.status_code == 200:
                active_tools = response.json().get("active_tools") or {}
                if int(active_tools.get(tool_name) or 0) > 0:
                    restart_response = await demo_client.post("/test/faults/restart")
                    assert restart_response.status_code == 200, restart_response.text
                    return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.1)
    raise AssertionError(f"MCP demo tool did not become active: {tool_name}")


async def _wait_for_demo_ready(client: httpx.AsyncClient, *, timeout: float = 20.0) -> None:
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


def _assert_finished_without_stream_error(events: list[dict]) -> None:
    assert events, "Streaming chat response should not be empty"
    event_text = json.dumps(events, ensure_ascii=False)
    assert "Error streaming messages" not in event_text, event_text
    assert not any(event.get("status") == "error" for event in events), event_text
    assert any(event.get("status") == "finished" for event in events), event_text


def _tool_call_ids(events: list[dict], tool_name: str) -> set[str]:
    call_ids: set[str] = set()
    for event in events:
        message = event.get("msg") or {}
        for tool_call in message.get("tool_calls") or []:
            if tool_call.get("name") == tool_name and tool_call.get("id"):
                call_ids.add(str(tool_call["id"]))
    return call_ids


def _tool_message_contents(events: list[dict], tool_call_ids: set[str]) -> list[str]:
    contents: list[str] = []
    for event in events:
        message = event.get("msg") or {}
        if message.get("type") != "tool" or str(message.get("tool_call_id") or "") not in tool_call_ids:
            continue
        content = message.get("content")
        if isinstance(content, str):
            contents.append(content)
        elif isinstance(content, list):
            contents.extend(
                block["text"]
                for block in content
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            )
    return contents


async def _run_reconnect_scenario(
    e2e_client: httpx.AsyncClient,
    e2e_headers: dict[str, str],
    e2e_agent_context: dict[str, str | int],
    *,
    delayed_tool_name: str,
) -> None:
    agent_id = str(e2e_agent_context["agent_id"])
    base_config_id = int(e2e_agent_context["agent_config_id"])
    server_name = f"e2e-mcp-reconnect-{uuid.uuid4().hex[:8]}"
    config_id: int | None = None
    thread_id: str | None = None
    chat_task: asyncio.Task[list[dict]] | None = None

    await _create_server(e2e_client, e2e_headers, server_name)
    try:
        config_id = await _create_agent_config(
            e2e_client,
            e2e_headers,
            agent_id=agent_id,
            base_config_id=base_config_id,
            server_name=server_name,
            delayed_tool_name=delayed_tool_name,
        )
        thread_id = await _create_thread(e2e_client, e2e_headers, agent_id)

        async with httpx.AsyncClient(base_url=_DEMO_BASE_URL, timeout=30.0) as demo_client:
            await _wait_for_demo_ready(demo_client)
            chat_task = asyncio.create_task(
                _stream_chat(
                    e2e_client,
                    e2e_headers,
                    thread_id=thread_id,
                    agent_config_id=config_id,
                    query="RECOVERY_TEST",
                )
            )
            await _restart_demo_during_tool_call(demo_client, chat_task, delayed_tool_name)
            events = await asyncio.wait_for(chat_task, timeout=120.0)
            await _wait_for_demo_ready(demo_client)

        _assert_finished_without_stream_error(events)
        event_text = json.dumps(events, ensure_ascii=False)
        tool_call_ids = _tool_call_ids(events, delayed_tool_name)
        assert len(tool_call_ids) == 1, event_text
        if delayed_tool_name == "echo_delayed_safe":
            expected_tool_output = "[Delayed Output] 回显内容: e2e-safe-reconnect"
            assert expected_tool_output in _tool_message_contents(events, tool_call_ids), event_text
            assert "未自动重试" not in event_text, event_text
            assert "执行结果可能已经生效" not in event_text, event_text
        else:
            assert "执行结果可能已经生效" in event_text, event_text

        follow_up_events = await _stream_chat(
            e2e_client,
            e2e_headers,
            thread_id=thread_id,
            agent_config_id=config_id,
            query="FOLLOW_UP",
        )
        _assert_finished_without_stream_error(follow_up_events)
        follow_up_text = json.dumps(follow_up_events, ensure_ascii=False)
        assert "after-reconnect" in follow_up_text, follow_up_text
        assert len(_tool_call_ids(follow_up_events, "echo_global")) == 1, follow_up_text
    finally:
        if chat_task is not None:
            if not chat_task.done():
                chat_task.cancel()
            await asyncio.gather(chat_task, return_exceptions=True)
        if thread_id is not None:
            await e2e_client.delete(f"/api/chat/thread/{thread_id}", headers=e2e_headers)
        if config_id is not None:
            await e2e_client.delete(
                f"/api/chat/agent/{agent_id}/configs/{config_id}",
                headers=e2e_headers,
            )
        await e2e_client.delete(f"/api/system/mcp-servers/{server_name}", headers=e2e_headers)
        await e2e_client.delete(
            f"/api/system/mcp-servers/{server_name}",
            params={"hard": "true"},
            headers=e2e_headers,
        )


async def test_safe_mcp_tool_restart_keeps_chat_stream_alive(
    e2e_client: httpx.AsyncClient,
    e2e_headers: dict[str, str],
    e2e_agent_context: dict[str, str | int],
):
    await _run_reconnect_scenario(
        e2e_client,
        e2e_headers,
        e2e_agent_context,
        delayed_tool_name="echo_delayed_safe",
    )


async def test_unannotated_mcp_tool_restart_returns_conservative_error_without_ending_stream(
    e2e_client: httpx.AsyncClient,
    e2e_headers: dict[str, str],
    e2e_agent_context: dict[str, str | int],
):
    await _run_reconnect_scenario(
        e2e_client,
        e2e_headers,
        e2e_agent_context,
        delayed_tool_name="echo_delayed_unannotated",
    )
