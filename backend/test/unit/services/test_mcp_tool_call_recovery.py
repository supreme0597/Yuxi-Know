from __future__ import annotations

import asyncio
import io
import logging
from collections import deque
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from anyio import BrokenResourceError, ClosedResourceError, EndOfStream
from langchain_core.messages import ToolMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.shared.exceptions import McpError
from mcp.types import CONNECTION_CLOSED, CallToolResult, ErrorData, ListToolsResult, TextContent, Tool

from yuxi.agents.mcp.tool_call_recovery import (
    MCPToolCallRecoveryInterceptor,
    is_mcp_connection_error,
)
from yuxi.agents.mcp.client_pool import ReconnectRequestStatus


def _success_result(text: str = "ok") -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=text)])


def _error_text(result: CallToolResult) -> str:
    assert result.isError is True
    assert len(result.content) == 1
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


def _mcp_error(*, code: int, message: str) -> McpError:
    return McpError(ErrorData(code=code, message=message))


class _FakeSessionProxy:
    def __init__(
        self,
        *,
        connected: bool = True,
        generation: int = 1,
        reconnect_statuses: list[ReconnectRequestStatus] | None = None,
        wait_actions: list[bool | Callable[[_FakeSessionProxy], bool]] | None = None,
        session_wait_actions: list[bool | Callable[[_FakeSessionProxy], bool]] | None = None,
        session_available_event: asyncio.Event | None = None,
    ) -> None:
        self.is_connected = connected
        self.generation = generation
        self._reconnect_statuses = deque(reconnect_statuses or [ReconnectRequestStatus.ACCEPTED])
        self._wait_actions = deque(wait_actions or [])
        self._session_wait_actions = deque(session_wait_actions or [])
        self._session_available_event = session_available_event
        self.request_calls: list[int] = []
        self.wait_calls: list[tuple[int, float]] = []
        self.session_wait_calls: list[float] = []
        self.call_tool_error: BaseException | None = None

    def request_reconnect(self, expected_generation: int) -> ReconnectRequestStatus:
        self.request_calls.append(expected_generation)
        if len(self._reconnect_statuses) > 1:
            return self._reconnect_statuses.popleft()
        return self._reconnect_statuses[0]

    async def wait_for_new_session(self, after_generation: int, *, timeout: float) -> bool:
        self.wait_calls.append((after_generation, timeout))
        if self.is_connected and self.generation > after_generation:
            return True
        if not self._wait_actions:
            return False
        action = self._wait_actions.popleft()
        return action(self) if callable(action) else action

    async def wait_for_session(self, *, timeout: float) -> bool:
        self.session_wait_calls.append(timeout)
        if self.is_connected:
            return True
        if self._session_wait_actions:
            action = self._session_wait_actions.popleft()
            return action(self) if callable(action) else action
        if self._session_available_event is None:
            return False
        try:
            await asyncio.wait_for(self._session_available_event.wait(), timeout=timeout)
        except TimeoutError:
            return False
        return self.is_connected

    def publish_session(self, generation: int) -> None:
        self.generation = generation
        self.is_connected = True
        if self._session_available_event is not None:
            self._session_available_event.set()

    async def list_tools(self, cursor: str | None = None) -> ListToolsResult:
        assert cursor is None
        return ListToolsResult(
            tools=[
                Tool(
                    name="echo",
                    description="echo test tool",
                    inputSchema={
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                    },
                )
            ]
        )

    async def call_tool(self, name: str, args: dict[str, Any], **kwargs: Any) -> CallToolResult:
        del name, args, kwargs
        if self.call_tool_error is not None:
            raise self.call_tool_error
        return _success_result()


def _publish_generation(generation: int) -> Callable[[_FakeSessionProxy], bool]:
    def publish(proxy: _FakeSessionProxy) -> bool:
        proxy.publish_session(generation)
        return True

    return publish


def test_bind_retryable_tools_is_required_and_only_allowed_once():
    proxy = _FakeSessionProxy()
    recovery = MCPToolCallRecoveryInterceptor(
        session_proxy=proxy,
        reconnect_wait_seconds=5,
    )
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        return _success_result()

    request = _request()
    with pytest.raises(RuntimeError, match="not bound"):
        asyncio.run(recovery(request, handler))
    assert handler_calls == 0

    recovery.bind_retryable_tools(frozenset({"echo"}))
    with pytest.raises(RuntimeError, match="already bound"):
        recovery.bind_retryable_tools(frozenset())


def _request(
    *,
    name: str = "echo",
    args: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
):
    from langchain_mcp_adapters.interceptors import MCPToolCallRequest

    return MCPToolCallRequest(
        name=name,
        args=args or {},
        server_name="demo-server",
        headers=headers,
    )


async def test_disconnected_before_call_reconnects_then_calls_handler_once():
    proxy = _FakeSessionProxy(
        connected=False,
        generation=3,
        reconnect_statuses=[ReconnectRequestStatus.ACCEPTED],
        wait_actions=[_publish_generation(4)],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset())
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        assert request.name == "echo"
        handler_calls += 1
        return _success_result("restored")

    result = await recovery(_request(), handler)

    assert result.isError is False
    assert result.content[0].text == "restored"
    assert handler_calls == 1
    assert proxy.request_calls == [3]
    assert [call[0] for call in proxy.wait_calls] == [3]


@pytest.mark.parametrize(
    ("status", "expected_status"),
    [
        (ReconnectRequestStatus.STOPPED, "stopped"),
        (ReconnectRequestStatus.ACCEPTED, "timeout"),
    ],
)
async def test_disconnected_before_call_returns_tool_error_without_sending(status, expected_status):
    proxy = _FakeSessionProxy(
        connected=False,
        generation=2,
        reconnect_statuses=[status],
        wait_actions=[False],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=0.01)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        return _success_result()

    result = await recovery(_request(), handler)
    text = _error_text(result)

    assert handler_calls == 0
    assert "demo-server" in text
    assert "echo" in text
    assert "尚未执行" in text
    assert expected_status in text
    assert proxy.request_calls == [2]
    assert len(proxy.wait_calls) == (0 if status is ReconnectRequestStatus.STOPPED else 1)


async def test_pre_call_recovery_uses_one_total_deadline(monkeypatch):
    from yuxi.agents.mcp import tool_call_recovery

    times = iter([100.0, 100.0, 102.0])
    monkeypatch.setattr(tool_call_recovery, "monotonic", lambda: next(times))
    proxy = _FakeSessionProxy(
        connected=False,
        generation=7,
        reconnect_statuses=[ReconnectRequestStatus.ACCEPTED, ReconnectRequestStatus.MERGED],
        wait_actions=[True, False],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset())

    result = await recovery(_request(), lambda request: _unexpected_handler(request))

    assert result.isError is True
    assert proxy.request_calls == [7, 7]
    assert proxy.wait_calls == [(7, 5.0), (7, 3.0)]


async def _unexpected_handler(request):
    del request
    raise AssertionError("handler must not be called")


async def test_stale_generation_before_call_rechecks_state_before_sending():
    proxy = _FakeSessionProxy(
        connected=False,
        generation=1,
        reconnect_statuses=[ReconnectRequestStatus.STALE_GENERATION],
        session_wait_actions=[_publish_generation(2)],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset())
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        return _success_result()

    result = await recovery(_request(), handler)

    assert result.isError is False
    assert handler_calls == 1
    assert proxy.request_calls == [1]
    assert proxy.session_wait_calls == pytest.approx([5])
    assert proxy.wait_calls == []


async def test_continuous_stale_generation_blocks_on_session_event_without_polling():
    session_available = asyncio.Event()
    proxy = _FakeSessionProxy(
        connected=False,
        generation=1,
        reconnect_statuses=[ReconnectRequestStatus.STALE_GENERATION],
        session_available_event=session_available,
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=0.5)
    recovery.bind_retryable_tools(frozenset())
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        return _success_result("published")

    recovery_task = asyncio.create_task(recovery(_request(), handler))
    await asyncio.sleep(0.01)
    try:
        assert recovery_task.done() is False
        assert proxy.request_calls == [1]
        assert len(proxy.session_wait_calls) == 1
        assert proxy.wait_calls == []
    finally:
        proxy.publish_session(2)

    result = await recovery_task

    assert result.isError is False
    assert result.content[0].text == "published"
    assert handler_calls == 1
    assert proxy.request_calls == [1]
    assert proxy.generation == 2


@pytest.mark.parametrize(
    "exc",
    [
        EndOfStream(),
        ClosedResourceError(),
        BrokenResourceError(),
        httpx.ConnectError("connect failed", request=httpx.Request("GET", "http://mcp.test")),
        httpx.ReadError("read failed", request=httpx.Request("GET", "http://mcp.test")),
        httpx.RemoteProtocolError("protocol failed", request=httpx.Request("GET", "http://mcp.test")),
        ConnectionResetError("reset"),
        BrokenPipeError("broken pipe"),
    ],
    ids=lambda exc: type(exc).__name__,
)
def test_connection_error_classifier_accepts_explicit_transport_errors(exc):
    assert is_mcp_connection_error(exc) is True


def test_connection_error_classifier_accepts_only_exception_groups_with_connection_leaves():
    connection_group = BaseExceptionGroup(
        "outer",
        [
            ClosedResourceError(),
            ExceptionGroup("inner", [EndOfStream(), ConnectionResetError("reset")]),
        ],
    )
    mixed_group = ExceptionGroup("mixed", [ClosedResourceError(), ValueError("bad payload")])

    assert is_mcp_connection_error(connection_group) is True
    assert is_mcp_connection_error(mixed_group) is False
    assert is_mcp_connection_error(ValueError("bad payload")) is False
    assert is_mcp_connection_error(TimeoutError("tool timed out")) is False


def test_connection_error_classifier_accepts_only_sdk_connection_closed_code():
    connection_closed = _mcp_error(code=CONNECTION_CLOSED, message="Connection closed")
    same_message_business_error = _mcp_error(code=-32603, message="Connection closed")
    same_code_business_error = _mcp_error(code=CONNECTION_CLOSED, message="Business operation failed")
    read_timeout = _mcp_error(code=408, message="Timed out while waiting for response")

    assert is_mcp_connection_error(connection_closed) is True
    assert is_mcp_connection_error(same_message_business_error) is False
    assert is_mcp_connection_error(same_code_business_error) is False
    assert is_mcp_connection_error(read_timeout) is False


async def test_sdk_connection_closed_error_reconnects_and_retries_safe_tool_once():
    proxy = _FakeSessionProxy(
        generation=4,
        reconnect_statuses=[ReconnectRequestStatus.ACCEPTED],
        wait_actions=[_publish_generation(5)],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        if handler_calls == 1:
            raise _mcp_error(code=CONNECTION_CLOSED, message="Connection closed")
        return _success_result("retried")

    result = await recovery(_request(), handler)

    assert result.isError is False
    assert result.content[0].text == "retried"
    assert handler_calls == 2
    assert proxy.request_calls == [4]
    assert [call[0] for call in proxy.wait_calls] == [4]


@pytest.mark.parametrize("status", [ReconnectRequestStatus.ACCEPTED, ReconnectRequestStatus.MERGED])
async def test_retryable_tool_waits_for_new_generation_and_retries_once(status):
    proxy = _FakeSessionProxy(
        generation=4,
        reconnect_statuses=[status],
        wait_actions=[_publish_generation(5)],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        if handler_calls == 1:
            raise ClosedResourceError()
        return _success_result("retried")

    result = await recovery(_request(), handler)

    assert result.isError is False
    assert result.content[0].text == "retried"
    assert handler_calls == 2
    assert proxy.request_calls == [4]
    assert [call[0] for call in proxy.wait_calls] == [4]


async def test_retryable_tool_with_stale_generation_verifies_new_session_without_blocking():
    proxy = _FakeSessionProxy(
        generation=8,
        reconnect_statuses=[ReconnectRequestStatus.STALE_GENERATION],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        if handler_calls == 1:
            proxy.generation = 9
            raise EndOfStream()
        return _success_result()

    result = await recovery(_request(), handler)

    assert result.isError is False
    assert handler_calls == 2
    assert proxy.request_calls == [8]
    assert proxy.wait_calls == [(8, 5)]


async def test_retryable_tool_with_stale_but_disconnected_generation_waits_for_next_session():
    proxy = _FakeSessionProxy(
        generation=8,
        reconnect_statuses=[ReconnectRequestStatus.STALE_GENERATION],
        wait_actions=[_publish_generation(10)],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        if handler_calls == 1:
            proxy.generation = 9
            proxy.is_connected = False
            raise EndOfStream()
        assert proxy.is_connected is True
        assert proxy.generation == 10
        return _success_result("retried-on-live-session")

    result = await recovery(_request(), handler)

    assert result.isError is False
    assert result.content[0].text == "retried-on-live-session"
    assert handler_calls == 2
    assert proxy.request_calls == [8]
    assert proxy.wait_calls == [(8, 5)]


async def test_unannotated_tool_requests_background_recovery_without_wait_or_replay():
    proxy = _FakeSessionProxy(generation=2, reconnect_statuses=[ReconnectRequestStatus.ACCEPTED])
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset())
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        raise ClosedResourceError()

    result = await recovery(_request(), handler)
    text = _error_text(result)

    assert handler_calls == 1
    assert proxy.request_calls == [2]
    assert proxy.wait_calls == []
    assert "未自动重试" in text
    assert "执行结果可能已经生效" in text


async def test_stopped_after_connection_failure_does_not_retry():
    proxy = _FakeSessionProxy(generation=3, reconnect_statuses=[ReconnectRequestStatus.STOPPED])
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        raise BrokenResourceError()

    result = await recovery(_request(), handler)
    text = _error_text(result)

    assert handler_calls == 1
    assert proxy.request_calls == [3]
    assert proxy.wait_calls == []
    assert "stopped" in text
    assert "未自动重试" in text


async def test_retryable_tool_reconnect_timeout_does_not_retry():
    proxy = _FakeSessionProxy(
        generation=5,
        reconnect_statuses=[ReconnectRequestStatus.MERGED],
        wait_actions=[False],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=0.01)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        raise ClosedResourceError()

    result = await recovery(_request(), handler)
    text = _error_text(result)

    assert handler_calls == 1
    assert proxy.request_calls == [5]
    assert proxy.wait_calls[0][0] == 5
    assert "重连超时" in text
    assert "未自动重试" in text


async def test_second_connection_failure_requests_recovery_for_retry_generation_without_third_call():
    proxy = _FakeSessionProxy(
        generation=1,
        reconnect_statuses=[ReconnectRequestStatus.ACCEPTED, ReconnectRequestStatus.MERGED],
        wait_actions=[_publish_generation(2)],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        if handler_calls == 1:
            raise ClosedResourceError()
        raise BrokenPipeError("retry connection closed")

    result = await recovery(_request(), handler)
    text = _error_text(result)

    assert handler_calls == 2
    assert proxy.request_calls == [1, 2]
    assert [call[0] for call in proxy.wait_calls] == [1]
    assert "自动重试失败" in text
    assert "不会再次重试" in text


@pytest.mark.parametrize("exc", [ValueError("bad response"), asyncio.CancelledError()])
async def test_non_connection_errors_and_cancellation_propagate(exc):
    proxy = _FakeSessionProxy()
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))

    async def handler(request):
        del request
        raise exc

    with pytest.raises(type(exc)):
        await recovery(_request(), handler)

    assert proxy.request_calls == []
    assert proxy.wait_calls == []


async def test_timeout_error_becomes_tool_error_without_reconnect_or_retry():
    proxy = _FakeSessionProxy()
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        raise TimeoutError("upstream secret timeout detail")

    result = await recovery(_request(), handler)
    text = _error_text(result)

    assert handler_calls == 1
    assert proxy.request_calls == []
    assert proxy.wait_calls == []
    assert "调用超时" in text
    assert "未自动重试" in text
    assert "upstream secret" not in text


async def test_sdk_read_timeout_becomes_tool_error_through_public_adapter_path():
    proxy = _FakeSessionProxy()
    proxy.call_tool_error = _mcp_error(
        code=408,
        message="Timed out while waiting for response; upstream secret detail",
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)

    tools = await load_mcp_tools(
        proxy,
        server_name="demo-server",
        tool_interceptors=[recovery],
    )
    recovery.bind_retryable_tools(frozenset({"echo"}))
    tools[0].handle_tool_error = True

    result = await tools[0].ainvoke(
        {
            "type": "tool_call",
            "name": "echo",
            "args": {"value": "hello"},
            "id": "call-timeout",
        }
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "调用超时" in str(result.content)
    assert "未自动重试" in str(result.content)
    assert "执行结果可能已经生效" in str(result.content)
    assert "upstream secret" not in str(result.content)
    assert proxy.request_calls == []
    assert proxy.wait_calls == []


async def test_sdk_read_timeout_after_safe_retry_returns_tool_error_without_third_call():
    proxy = _FakeSessionProxy(
        generation=6,
        reconnect_statuses=[ReconnectRequestStatus.ACCEPTED],
        wait_actions=[_publish_generation(7)],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        if handler_calls == 1:
            raise ClosedResourceError()
        raise _mcp_error(code=408, message="retry timeout with upstream secret detail")

    result = await recovery(_request(), handler)
    text = _error_text(result)

    assert handler_calls == 2
    assert proxy.request_calls == [6]
    assert [call[0] for call in proxy.wait_calls] == [6]
    assert "自动重试调用超时" in text
    assert "不会再次重试" in text
    assert "执行结果可能已经生效" in text
    assert "upstream secret" not in text


async def test_second_non_connection_error_propagates_after_one_safe_retry():
    proxy = _FakeSessionProxy(
        generation=6,
        reconnect_statuses=[ReconnectRequestStatus.ACCEPTED],
        wait_actions=[_publish_generation(7)],
    )
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset({"echo"}))
    handler_calls = 0

    async def handler(request):
        nonlocal handler_calls
        del request
        handler_calls += 1
        if handler_calls == 1:
            raise ClosedResourceError()
        raise ValueError("invalid MCP response")

    with pytest.raises(ValueError, match="invalid MCP response"):
        await recovery(_request(), handler)

    assert handler_calls == 2
    assert proxy.request_calls == [6]


async def test_logs_do_not_include_arguments_headers_tokens_or_exception_messages():
    target_logger = logging.getLogger("yuxi.mcp.tool_call_recovery")
    log_stream = io.StringIO()
    log_handler = logging.StreamHandler(log_stream)
    target_logger.addHandler(log_handler)
    previous_level = target_logger.level
    target_logger.setLevel(logging.INFO)
    proxy = _FakeSessionProxy(generation=11, reconnect_statuses=[ReconnectRequestStatus.ACCEPTED])
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)
    recovery.bind_retryable_tools(frozenset())

    async def handler(request):
        del request
        raise httpx.ReadError(
            "transport contained exception-secret",
            request=httpx.Request("GET", "http://mcp.test"),
        )

    try:
        result = await recovery(
            _request(
                args={"password": "argument-secret"},
                headers={"Authorization": "Bearer token-secret"},
            ),
            handler,
        )
    finally:
        target_logger.removeHandler(log_handler)
        target_logger.setLevel(previous_level)

    log_text = log_stream.getvalue()

    assert result.isError is True
    assert "server=demo-server" in log_text
    assert "tool=echo" in log_text
    assert "generation=11" in log_text
    assert "exception=ReadError" in log_text
    assert "reconnect_status=accepted" in log_text
    assert "retried=false" in log_text
    assert "argument-secret" not in log_text
    assert "token-secret" not in log_text
    assert "exception-secret" not in log_text


async def test_public_adapter_interceptor_path_converts_error_result_to_tool_message():
    proxy = _FakeSessionProxy(generation=1, reconnect_statuses=[ReconnectRequestStatus.ACCEPTED])
    proxy.call_tool_error = ClosedResourceError()
    recovery = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=5)

    tools = await load_mcp_tools(
        proxy,
        server_name="demo-server",
        tool_interceptors=[recovery],
    )
    recovery.bind_retryable_tools(frozenset())
    tools[0].handle_tool_error = True

    result = await tools[0].ainvoke(
        {
            "type": "tool_call",
            "name": "echo",
            "args": {"value": "hello"},
            "id": "call-1",
        }
    )

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "未自动重试" in str(result.content)
    assert proxy.request_calls == [1]
