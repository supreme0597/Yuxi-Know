from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from time import monotonic

import httpx
from anyio import BrokenResourceError, ClosedResourceError, EndOfStream
from langchain_mcp_adapters.interceptors import MCPToolCallRequest, MCPToolCallResult
from mcp.shared.exceptions import McpError
from mcp.types import CONNECTION_CLOSED, CallToolResult, TextContent

from yuxi.agents.mcp.client_pool import ReconnectRequestStatus, _SessionProxy

logger = logging.getLogger("yuxi.mcp.tool_call_recovery")

_MCP_CONNECTION_ERRORS = (
    EndOfStream,
    ClosedResourceError,
    BrokenResourceError,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.RemoteProtocolError,
    ConnectionResetError,
    BrokenPipeError,
)


def is_mcp_connection_error(exc: BaseException) -> bool:
    """Return whether every failure leaf is an explicit MCP transport disconnect."""
    if isinstance(exc, BaseExceptionGroup):
        return bool(exc.exceptions) and all(is_mcp_connection_error(child) for child in exc.exceptions)
    if isinstance(exc, McpError):
        return exc.error.code == CONNECTION_CLOSED and exc.error.message == "Connection closed"
    return isinstance(exc, _MCP_CONNECTION_ERRORS)


def _is_mcp_call_timeout(exc: BaseException) -> bool:
    return isinstance(exc, TimeoutError) or (
        isinstance(exc, McpError) and exc.error.code == httpx.codes.REQUEST_TIMEOUT
    )


def _error_result(request: MCPToolCallRequest, message: str) -> CallToolResult:
    text = f"MCP server={request.server_name} tool={request.name}: {message}"
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        isError=True,
    )


def _log_recovery(
    request: MCPToolCallRequest,
    *,
    generation: int,
    exception_type: str,
    reconnect_status: ReconnectRequestStatus | str,
    retried: bool,
) -> None:
    status = reconnect_status.value if isinstance(reconnect_status, ReconnectRequestStatus) else reconnect_status
    logger.info(
        "server=%s tool=%s generation=%d exception=%s reconnect_status=%s retried=%s",
        request.server_name,
        request.name,
        generation,
        exception_type,
        status,
        str(retried).lower(),
    )


class MCPToolCallRecoveryInterceptor:
    """Recover one Adapter tool call without creating or owning MCP sessions."""

    def __init__(self, *, session_proxy: _SessionProxy, reconnect_wait_seconds: float) -> None:
        self._session_proxy = session_proxy
        self._reconnect_wait_seconds = max(0.0, reconnect_wait_seconds)
        self._retryable_tool_names: frozenset[str] | None = None

    def bind_retryable_tools(self, tool_names: frozenset[str]) -> None:
        """Bind the immutable read-only/idempotent retry policy exactly once."""
        if self._retryable_tool_names is not None:
            raise RuntimeError("MCP retry policy is already bound")
        self._retryable_tool_names = frozenset(tool_names)

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
    ) -> MCPToolCallResult:
        if self._retryable_tool_names is None:
            raise RuntimeError("MCP retry policy is not bound")

        reconnect_deadline = monotonic() + self._reconnect_wait_seconds
        while not self._session_proxy.is_connected:
            observed_generation = self._session_proxy.generation
            status = self._session_proxy.request_reconnect(observed_generation)
            if status is ReconnectRequestStatus.STOPPED:
                _log_recovery(
                    request,
                    generation=observed_generation,
                    exception_type="None",
                    reconnect_status=status,
                    retried=False,
                )
                return _error_result(
                    request,
                    "reconnect_status=stopped，Session 已停止，请求尚未执行。",
                )

            if status is ReconnectRequestStatus.STALE_GENERATION:
                remaining = max(0.0, reconnect_deadline - monotonic())
                restored = await self._session_proxy.wait_for_session(timeout=remaining)
                if not restored:
                    _log_recovery(
                        request,
                        generation=observed_generation,
                        exception_type="None",
                        reconnect_status="timeout",
                        retried=False,
                    )
                    return _error_result(
                        request,
                        "reconnect_status=timeout，等待可用 Session 超时，请求尚未执行。",
                    )
                continue

            remaining = max(0.0, reconnect_deadline - monotonic())
            restored = await self._session_proxy.wait_for_new_session(
                observed_generation,
                timeout=remaining,
            )
            if not restored:
                _log_recovery(
                    request,
                    generation=observed_generation,
                    exception_type="None",
                    reconnect_status="timeout",
                    retried=False,
                )
                return _error_result(
                    request,
                    "reconnect_status=timeout，等待可用 Session 超时，请求尚未执行。",
                )

        call_generation = self._session_proxy.generation
        try:
            return await handler(request)
        except BaseException as exc:
            if _is_mcp_call_timeout(exc):
                _log_recovery(
                    request,
                    generation=call_generation,
                    exception_type=type(exc).__name__,
                    reconnect_status="not_requested",
                    retried=False,
                )
                return _error_result(
                    request,
                    "调用超时，未自动重试；执行结果可能已经生效。",
                )
            if not is_mcp_connection_error(exc):
                raise

            status = self._session_proxy.request_reconnect(call_generation)
            if status is ReconnectRequestStatus.STOPPED:
                _log_recovery(
                    request,
                    generation=call_generation,
                    exception_type=type(exc).__name__,
                    reconnect_status=status,
                    retried=False,
                )
                return _error_result(
                    request,
                    "reconnect_status=stopped，连接已中断且 Session 已停止，未自动重试；"
                    "执行结果可能已经生效。",
                )

            if request.name not in self._retryable_tool_names:
                _log_recovery(
                    request,
                    generation=call_generation,
                    exception_type=type(exc).__name__,
                    reconnect_status=status,
                    retried=False,
                )
                return _error_result(
                    request,
                    "连接已中断，工具未声明只读或幂等，未自动重试；执行结果可能已经生效。",
                )

            restored = await self._session_proxy.wait_for_new_session(
                call_generation,
                timeout=self._reconnect_wait_seconds,
            )
            if not restored:
                _log_recovery(
                    request,
                    generation=call_generation,
                    exception_type=type(exc).__name__,
                    reconnect_status="timeout",
                    retried=False,
                )
                return _error_result(
                    request,
                    "连接中断后重连超时，未自动重试；执行结果可能已经生效。",
                )

            retry_generation = self._session_proxy.generation
            _log_recovery(
                request,
                generation=retry_generation,
                exception_type=type(exc).__name__,
                reconnect_status=status,
                retried=True,
            )
            try:
                return await handler(request)
            except BaseException as retry_exc:
                if _is_mcp_call_timeout(retry_exc):
                    _log_recovery(
                        request,
                        generation=retry_generation,
                        exception_type=type(retry_exc).__name__,
                        reconnect_status="not_requested",
                        retried=True,
                    )
                    return _error_result(
                        request,
                        "自动重试调用超时，不会再次重试；执行结果可能已经生效。",
                    )
                if not is_mcp_connection_error(retry_exc):
                    raise
                retry_status = self._session_proxy.request_reconnect(retry_generation)
                _log_recovery(
                    request,
                    generation=retry_generation,
                    exception_type=type(retry_exc).__name__,
                    reconnect_status=retry_status,
                    retried=True,
                )
                return _error_result(
                    request,
                    "连接恢复后的自动重试失败，不会再次重试；执行结果可能已经生效。",
                )
