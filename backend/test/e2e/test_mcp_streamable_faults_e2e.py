from __future__ import annotations

import asyncio
import copy
import json
import os
import uuid

import httpx
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.e2e, pytest.mark.slow]

_FAULT_PROXY_BASE_URL = os.getenv(
    "TEST_MCP_STREAMABLE_FAULT_PROXY_URL",
    "http://mcp-streamable-fault-proxy:8998",
).rstrip("/")
_DEMO_A_BASE_URL = os.getenv("TEST_MCP_STREAMABLE_DEMO_A_URL", "http://mcp-streamable-demo-a:9001").rstrip("/")
_DEMO_B_BASE_URL = os.getenv("TEST_MCP_STREAMABLE_DEMO_B_URL", "http://mcp-streamable-demo-b:9002").rstrip("/")


async def _create_server(client: httpx.AsyncClient, headers: dict[str, str], server_name: str) -> None:
    response = await client.post(
        "/api/system/mcp-servers",
        json={
            "name": server_name,
            "transport": "streamable_http",
            "url": f"{_FAULT_PROXY_BASE_URL}/mcp",
            "description": "E2E streamable HTTP fault proxy",
            "headers": {"X-Fault-Case-ID": server_name},
            "timeout": 10,
            "sse_read_timeout": 10,
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
    scenario: str,
) -> int:
    response = await client.get(f"/api/chat/agent/{agent_id}/configs/{base_config_id}", headers=headers)
    assert response.status_code == 200, response.text
    source_config = response.json()["config"]
    config_json = copy.deepcopy(source_config.get("config_json") or {})
    context = config_json.setdefault("context", {})
    assert isinstance(context, dict), source_config

    scenario_rules = {
        "abort_tool_response": (
            "当用户消息是 FAULT_TEST 时，只调用 echo_delayed_safe 一次，参数 message 必须是 "
            f"e2e-abort-{server_name}，delay_seconds 必须是 0；工具返回后直接回答工具结果。"
        ),
        "stateful_non_sticky": (
            "当用户消息是 FAULT_TEST 时，只调用 echo_delayed_safe 一次，参数 message 必须是 "
            f"e2e-non-sticky-{server_name}，delay_seconds 必须是 0；如果调用失败，不得再次调用工具。"
        ),
        "tool_timeout": (
            "当用户消息是 FAULT_TEST 时，只调用 echo_delayed_safe 一次，参数 message 必须是 "
            f"e2e-timeout-{server_name}，delay_seconds 必须是 2；如果工具返回错误，不得再次调用任何工具，"
            "直接说明未自动重试且执行结果可能已经生效。"
        ),
    }
    context.update(
        {
            "system_prompt": (
                "你正在执行 MCP Streamable HTTP 故障端到端测试，必须严格遵守以下规则。"
                f"{scenario_rules[scenario]}"
                "当用户消息是 FOLLOW_UP 时，只调用 echo_global 一次，参数 message 必须是 after-fault，"
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
            "name": f"mcp-streamable-fault-e2e-{uuid.uuid4().hex[:8]}",
            "description": f"Dedicated MCP streamable fault E2E config: {scenario}",
            "config_json": config_json,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return int(response.json()["config"]["id"])


async def _create_thread(client: httpx.AsyncClient, headers: dict[str, str], agent_id: str) -> str:
    response = await client.post(
        "/api/chat/thread",
        json={
            "agent_id": agent_id,
            "title": f"mcp-streamable-fault-e2e-{uuid.uuid4().hex[:8]}",
            "metadata": {},
        },
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


async def _configure_proxy(client: httpx.AsyncClient, case_id: str, scenario: str) -> None:
    payload: dict[str, object] = {"case_id": case_id, "mode": scenario, "failures": 1}
    if scenario == "tool_timeout":
        payload["timeout_seconds"] = 0.2
    response = await client.post("/test/faults/configure", json=payload)
    assert response.status_code == 200, response.text


async def _proxy_state(client: httpx.AsyncClient, case_id: str) -> dict:
    response = await client.get("/test/faults/state", params={"case_id": case_id})
    assert response.status_code == 200, response.text
    return response.json()


async def _demo_message_count(base_url: str, message: str) -> int:
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        response = await client.get("/test/faults/state")
    assert response.status_code == 200, response.text
    return int((response.json().get("tool_call_messages") or {}).get(message) or 0)


def _assert_finished_without_stream_error(events: list[dict]) -> None:
    assert events, "Streaming chat response should not be empty"
    event_text = json.dumps(events, ensure_ascii=False)
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
                block["text"] for block in content if isinstance(block, dict) and isinstance(block.get("text"), str)
            )
    return contents


async def _setup_scenario(
    e2e_client: httpx.AsyncClient,
    e2e_headers: dict[str, str],
    e2e_agent_context: dict[str, str | int],
    proxy_client: httpx.AsyncClient,
    scenario: str,
) -> tuple[str, int, str, str]:
    agent_id = str(e2e_agent_context["agent_id"])
    server_name = f"e2e-mcp-streamable-fault-{uuid.uuid4().hex[:8]}"
    server_created = False
    config_id: int | None = None
    thread_id: str | None = None
    await _reset_proxy(proxy_client, server_name)
    try:
        await _create_server(e2e_client, e2e_headers, server_name)
        server_created = True
        config_id = await _create_agent_config(
            e2e_client,
            e2e_headers,
            agent_id=agent_id,
            base_config_id=int(e2e_agent_context["agent_config_id"]),
            server_name=server_name,
            scenario=scenario,
        )
        thread_id = await _create_thread(e2e_client, e2e_headers, agent_id)
        await _configure_proxy(proxy_client, server_name, scenario)
        return agent_id, config_id, thread_id, server_name
    except Exception as setup_error:
        cleanup_errors: list[str] = []
        cleanup_requests = []
        if thread_id is not None:
            cleanup_requests.append(
                ("thread", lambda: e2e_client.delete(f"/api/chat/thread/{thread_id}", headers=e2e_headers))
            )
        if config_id is not None:
            cleanup_requests.append(
                (
                    "agent config",
                    lambda: e2e_client.delete(
                        f"/api/chat/agent/{agent_id}/configs/{config_id}",
                        headers=e2e_headers,
                    ),
                )
            )
        if server_created:
            cleanup_requests.extend(
                [
                    (
                        "MCP server",
                        lambda: e2e_client.delete(f"/api/system/mcp-servers/{server_name}", headers=e2e_headers),
                    ),
                    (
                        "MCP server hard delete",
                        lambda: e2e_client.delete(
                            f"/api/system/mcp-servers/{server_name}",
                            params={"hard": "true"},
                            headers=e2e_headers,
                        ),
                    ),
                ]
            )
        try:
            for label, request in cleanup_requests:
                try:
                    response = await request()
                except httpx.HTTPError as exc:
                    cleanup_errors.append(f"{label}: {type(exc).__name__}: {exc}")
                    continue
                if response.status_code not in {200, 404}:
                    cleanup_errors.append(f"{label}: status={response.status_code}, body={response.text}")
        finally:
            try:
                await _reset_proxy(proxy_client, server_name)
            except Exception as exc:
                cleanup_errors.append(f"proxy reset: {type(exc).__name__}: {exc}")
        if cleanup_errors:
            setup_error.add_note("Scenario cleanup errors: " + "; ".join(cleanup_errors))
        raise


async def _cleanup_scenario(
    e2e_client: httpx.AsyncClient,
    e2e_headers: dict[str, str],
    proxy_client: httpx.AsyncClient,
    *,
    agent_id: str,
    config_id: int,
    thread_id: str,
    server_name: str,
) -> None:
    cleanup_errors: list[str] = []
    requests = [
        ("thread", lambda: e2e_client.delete(f"/api/chat/thread/{thread_id}", headers=e2e_headers)),
        (
            "agent config",
            lambda: e2e_client.delete(
                f"/api/chat/agent/{agent_id}/configs/{config_id}",
                headers=e2e_headers,
            ),
        ),
        (
            "MCP server",
            lambda: e2e_client.delete(f"/api/system/mcp-servers/{server_name}", headers=e2e_headers),
        ),
        (
            "MCP server hard delete",
            lambda: e2e_client.delete(
                f"/api/system/mcp-servers/{server_name}",
                params={"hard": "true"},
                headers=e2e_headers,
            ),
        ),
    ]
    try:
        for label, request in requests:
            try:
                response = await request()
            except httpx.HTTPError as exc:
                cleanup_errors.append(f"{label}: {type(exc).__name__}: {exc}")
                continue
            if response.status_code not in {200, 404}:
                cleanup_errors.append(f"{label}: status={response.status_code}, body={response.text}")
    finally:
        await _reset_proxy(proxy_client, server_name)

    assert not cleanup_errors, "; ".join(cleanup_errors)


async def test_streamable_tools_call_response_abort_returns_timeout_without_replay(
    e2e_client: httpx.AsyncClient,
    e2e_headers: dict[str, str],
    e2e_agent_context: dict[str, str | int],
):
    async with httpx.AsyncClient(base_url=_FAULT_PROXY_BASE_URL, timeout=20.0) as proxy_client:
        agent_id, config_id, thread_id, server_name = await _setup_scenario(
            e2e_client,
            e2e_headers,
            e2e_agent_context,
            proxy_client,
            "abort_tool_response",
        )
        try:
            events = await _stream_chat(
                e2e_client,
                e2e_headers,
                thread_id=thread_id,
                agent_config_id=config_id,
                query="FAULT_TEST",
            )

            _assert_finished_without_stream_error(events)
            event_text = json.dumps(events, ensure_ascii=False)
            tool_call_ids = _tool_call_ids(events, "echo_delayed_safe")
            assert len(tool_call_ids) == 1, event_text
            tool_contents = _tool_message_contents(events, tool_call_ids)
            assert len(tool_contents) == 1, event_text
            assert "调用超时，未自动重试；执行结果可能已经生效" in tool_contents[0], event_text
            state = await _proxy_state(proxy_client, server_name)
            assert state["faults_triggered"] == 1
            assert state["last_fault_upstream_completed"] is True
            assert state["method_counts"]["tools/call"] == 1
            assert await _demo_message_count(_DEMO_A_BASE_URL, f"e2e-abort-{server_name}") == 1

            follow_up_events = await _stream_chat(
                e2e_client,
                e2e_headers,
                thread_id=thread_id,
                agent_config_id=config_id,
                query="FOLLOW_UP",
            )
            _assert_finished_without_stream_error(follow_up_events)
            follow_up_text = json.dumps(follow_up_events, ensure_ascii=False)
            follow_up_call_ids = _tool_call_ids(follow_up_events, "echo_global")
            assert len(follow_up_call_ids) == 1, follow_up_text
            assert _tool_message_contents(follow_up_events, follow_up_call_ids) == [
                "[Global Output] 回显内容: after-fault"
            ]
        finally:
            await _cleanup_scenario(
                e2e_client,
                e2e_headers,
                proxy_client,
                agent_id=agent_id,
                config_id=config_id,
                thread_id=thread_id,
                server_name=server_name,
            )


async def test_streamable_stateful_non_sticky_exposes_session_terminated_agent_stream_error(
    e2e_client: httpx.AsyncClient,
    e2e_headers: dict[str, str],
    e2e_agent_context: dict[str, str | int],
):
    async with httpx.AsyncClient(base_url=_FAULT_PROXY_BASE_URL, timeout=20.0) as proxy_client:
        agent_id, config_id, thread_id, server_name = await _setup_scenario(
            e2e_client,
            e2e_headers,
            e2e_agent_context,
            proxy_client,
            "stateful_non_sticky",
        )
        try:
            events = await _stream_chat(
                e2e_client,
                e2e_headers,
                thread_id=thread_id,
                agent_config_id=config_id,
                query="FAULT_TEST",
            )

            event_text = json.dumps(events, ensure_ascii=False)
            assert len(_tool_call_ids(events, "echo_delayed_safe")) == 1, event_text
            error_events = [event for event in events if event.get("status") == "error"]
            assert len(error_events) == 1, event_text
            assert "Session terminated" in str(error_events[0].get("error_message") or ""), event_text
            assert not any(event.get("status") == "finished" for event in events), event_text
            state = await _proxy_state(proxy_client, server_name)
            assert state["faults_triggered"] == 1
            assert state["last_fault_upstream_completed"] is True
            assert state["method_counts"]["tools/call"] == 1
            assert state["route_counts"]["1"] == 1
            assert await _demo_message_count(_DEMO_B_BASE_URL, f"e2e-non-sticky-{server_name}") == 0
        finally:
            await _cleanup_scenario(
                e2e_client,
                e2e_headers,
                proxy_client,
                agent_id=agent_id,
                config_id=config_id,
                thread_id=thread_id,
                server_name=server_name,
            )


async def test_streamable_proxy_timeout_is_not_replayed_and_next_agent_call_still_works(
    e2e_client: httpx.AsyncClient,
    e2e_headers: dict[str, str],
    e2e_agent_context: dict[str, str | int],
):
    async with httpx.AsyncClient(base_url=_FAULT_PROXY_BASE_URL, timeout=20.0) as proxy_client:
        agent_id, config_id, thread_id, server_name = await _setup_scenario(
            e2e_client,
            e2e_headers,
            e2e_agent_context,
            proxy_client,
            "tool_timeout",
        )
        try:
            events = await _stream_chat(
                e2e_client,
                e2e_headers,
                thread_id=thread_id,
                agent_config_id=config_id,
                query="FAULT_TEST",
            )

            _assert_finished_without_stream_error(events)
            event_text = json.dumps(events, ensure_ascii=False)
            tool_call_ids = _tool_call_ids(events, "echo_delayed_safe")
            assert len(tool_call_ids) == 1, event_text
            tool_contents = _tool_message_contents(events, tool_call_ids)
            assert len(tool_contents) == 1, event_text
            assert "调用超时，未自动重试；执行结果可能已经生效" in tool_contents[0], event_text
            state = await _proxy_state(proxy_client, server_name)
            assert state["faults_triggered"] == 1
            assert state["last_fault_upstream_completed"] is False
            assert state["method_counts"]["tools/call"] == 1
            assert await _demo_message_count(_DEMO_A_BASE_URL, f"e2e-timeout-{server_name}") == 1

            follow_up_events = await _stream_chat(
                e2e_client,
                e2e_headers,
                thread_id=thread_id,
                agent_config_id=config_id,
                query="FOLLOW_UP",
            )
            _assert_finished_without_stream_error(follow_up_events)
            follow_up_text = json.dumps(follow_up_events, ensure_ascii=False)
            follow_up_call_ids = _tool_call_ids(follow_up_events, "echo_global")
            assert len(follow_up_call_ids) == 1, follow_up_text
            assert _tool_message_contents(follow_up_events, follow_up_call_ids) == [
                "[Global Output] 回显内容: after-fault"
            ]
        finally:
            await _cleanup_scenario(
                e2e_client,
                e2e_headers,
                proxy_client,
                agent_id=agent_id,
                config_id=config_id,
                thread_id=thread_id,
                server_name=server_name,
            )
