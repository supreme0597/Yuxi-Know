from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlsplit, urlunsplit

import httpx
import uvicorn

logger = logging.getLogger("mcp_streamable_fault_proxy")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

_HOP_BY_HOP_HEADERS = {
    b"connection",
    b"keep-alive",
    b"proxy-authenticate",
    b"proxy-authorization",
    b"te",
    b"trailer",
    b"transfer-encoding",
    b"upgrade",
}
_VALID_MODES = {
    "passthrough",
    "abort_tool_response",
    "stateful_non_sticky",
    "tool_timeout",
}


class InjectedDownstreamAbort(RuntimeError):
    """Raised after a partial ASGI response so Uvicorn closes the socket."""


@dataclass
class FaultState:
    mode: str = "passthrough"
    remaining_failures: int = 0
    timeout_seconds: float = 0.5
    faults_triggered: int = 0
    last_fault: str | None = None
    last_fault_upstream_completed: bool | None = None
    method_counts: Counter[str] = field(default_factory=Counter)
    route_counts: Counter[str] = field(default_factory=Counter)
    session_routes: dict[str, int] = field(default_factory=dict)
    plan_version: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def reset(self) -> dict[str, Any]:
        async with self.lock:
            self.mode = "passthrough"
            self.remaining_failures = 0
            self.timeout_seconds = 0.5
            self.faults_triggered = 0
            self.last_fault = None
            self.last_fault_upstream_completed = None
            self.plan_version += 1
            self.method_counts.clear()
            self.route_counts.clear()
            self.session_routes.clear()
            return self.snapshot()

    async def configure(self, *, mode: str, failures: int, timeout_seconds: float | None) -> dict[str, Any]:
        if mode not in _VALID_MODES:
            raise ValueError(f"Unsupported fault mode: {mode}")
        if failures not in {0, 1}:
            raise ValueError("failures must be 0 or 1")
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        async with self.lock:
            self.mode = mode
            self.remaining_failures = failures
            if timeout_seconds is not None:
                self.timeout_seconds = timeout_seconds
            self.faults_triggered = 0
            self.last_fault = None
            self.last_fault_upstream_completed = None
            self.plan_version += 1
            self.method_counts.clear()
            self.route_counts.clear()
            return self.snapshot()

    async def select_route(
        self,
        *,
        jsonrpc_method: str | None,
        session_id: str | None,
    ) -> tuple[int, str, int | None, float | None]:
        async with self.lock:
            if jsonrpc_method:
                self.method_counts[jsonrpc_method] += 1

            target = self.session_routes.get(session_id, 0) if session_id else 0
            action = "passthrough"
            fault_token = None
            fault_timeout_seconds = None
            if jsonrpc_method == "tools/call" and self.remaining_failures > 0 and self.mode != "passthrough":
                self.remaining_failures -= 1
                self.faults_triggered += 1
                self.last_fault = self.mode
                self.last_fault_upstream_completed = False
                action = self.mode
                fault_token = self.plan_version
                if self.mode == "stateful_non_sticky":
                    target = 1 - target
                elif self.mode == "tool_timeout":
                    fault_timeout_seconds = self.timeout_seconds

            self.route_counts[str(target)] += 1
            return target, action, fault_token, fault_timeout_seconds

    async def bind_session(self, session_id: str, target: int) -> None:
        async with self.lock:
            self.session_routes[session_id] = target

    async def mark_fault_upstream_completed(self, fault_token: int | None) -> None:
        async with self.lock:
            if fault_token is not None and fault_token == self.plan_version and self.last_fault is not None:
                self.last_fault_upstream_completed = True

    async def get_snapshot(self) -> dict[str, Any]:
        async with self.lock:
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "remaining_failures": self.remaining_failures,
            "timeout_seconds": self.timeout_seconds,
            "faults_triggered": self.faults_triggered,
            "last_fault": self.last_fault,
            "last_fault_upstream_completed": self.last_fault_upstream_completed,
            "method_counts": dict(self.method_counts),
            "route_counts": dict(self.route_counts),
            "session_mappings": len(self.session_routes),
        }


class FaultStateRegistry:
    def __init__(self) -> None:
        self._states: dict[str, FaultState] = {}
        self._lock = asyncio.Lock()

    async def get(self, case_id: str) -> FaultState:
        async with self._lock:
            state = self._states.get(case_id)
            if state is None:
                state = FaultState()
                self._states[case_id] = state
            return state


class MCPStreamableFaultProxy:
    def __init__(self, upstreams: list[str]) -> None:
        if len(upstreams) != 2:
            raise ValueError("Exactly two upstreams are required")
        self._upstreams = [value.rstrip("/") for value in upstreams]
        self._states = FaultStateRegistry()
        self._client: httpx.AsyncClient | None = None

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(receive, send)
            return
        if scope["type"] != "http":
            return

        path = scope.get("path") or ""
        if path.startswith("/test/faults/"):
            await self._handle_control(scope, receive, send)
            return
        if path == "/mcp" or path.startswith("/mcp/"):
            await self._handle_proxy(scope, receive, send)
            return
        await self._send_json(send, 404, {"detail": "Not found"})

    async def _handle_lifespan(self, receive, send) -> None:
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, read=None),
                    follow_redirects=False,
                )
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                if self._client is not None:
                    await self._client.aclose()
                    self._client = None
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def _handle_control(self, scope, receive, send) -> None:
        path = scope.get("path") or ""
        method = scope.get("method") or "GET"
        try:
            if method == "GET" and path == "/test/faults/state":
                case_id = self._query_case_id(scope)
                state = await self._states.get(case_id)
                await self._send_json(send, 200, await state.get_snapshot())
                return
            if method == "POST" and path == "/test/faults/reset":
                payload = json.loads(await self._read_body(receive) or b"{}")
                state = await self._states.get(str(payload.get("case_id") or "default"))
                await self._send_json(send, 200, await state.reset())
                return
            if method == "POST" and path == "/test/faults/configure":
                body = await self._read_body(receive)
                payload = json.loads(body or b"{}")
                fault_state = await self._states.get(str(payload.get("case_id") or "default"))
                state = await fault_state.configure(
                    mode=str(payload.get("mode") or "passthrough"),
                    failures=int(payload.get("failures", 1)),
                    timeout_seconds=(
                        float(payload["timeout_seconds"]) if payload.get("timeout_seconds") is not None else None
                    ),
                )
                await self._send_json(send, 200, state)
                return
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            await self._send_json(send, 400, {"detail": str(exc)})
            return

        await self._send_json(send, 404, {"detail": "Not found"})

    async def _handle_proxy(self, scope, receive, send) -> None:
        client = self._client
        if client is None:
            await self._send_json(send, 503, {"detail": "Proxy is not ready"})
            return

        body = await self._read_body(receive)
        jsonrpc_method = self._jsonrpc_method(body)
        headers = scope.get("headers") or []
        case_id = self._header_value(headers, b"x-fault-case-id") or "default"
        state = await self._states.get(case_id)
        session_id = self._header_value(headers, b"mcp-session-id")
        target, action, fault_token, fault_timeout_seconds = await state.select_route(
            jsonrpc_method=jsonrpc_method,
            session_id=session_id,
        )
        upstream_url = self._build_upstream_url(target, scope)
        request = client.build_request(
            scope.get("method") or "GET",
            upstream_url,
            headers=self._request_headers(scope.get("headers") or []),
            content=body,
        )

        if action == "tool_timeout":
            assert fault_timeout_seconds is not None
            await self._proxy_with_timeout_abort(
                client,
                request,
                send,
                state,
                fault_token,
                fault_timeout_seconds,
            )
            return

        response: httpx.Response | None = None
        response_started = False
        try:
            response = await client.send(request, stream=True)
            response_session_id = response.headers.get("mcp-session-id")
            if response_session_id:
                await state.bind_session(response_session_id, target)

            if action == "abort_tool_response":
                raw_body = await self._read_raw_response(response)
                await state.mark_fault_upstream_completed(fault_token)
                await self._abort_response(
                    send,
                    response.status_code,
                    response.headers.raw,
                    raw_body,
                    reason="abort_tool_response",
                )
                return

            await send(
                {
                    "type": "http.response.start",
                    "status": response.status_code,
                    "headers": self._response_headers(response.headers.raw),
                }
            )
            response_started = True
            async for chunk in response.aiter_raw():
                await send({"type": "http.response.body", "body": chunk, "more_body": True})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            if action != "passthrough":
                await state.mark_fault_upstream_completed(fault_token)
        except InjectedDownstreamAbort:
            raise
        except httpx.HTTPError as exc:
            logger.warning("Upstream request failed: %s", exc)
            if response_started:
                raise InjectedDownstreamAbort("upstream_stream_error") from exc
            await self._send_json(send, 502, {"detail": type(exc).__name__})
        finally:
            if response is not None:
                await response.aclose()

    async def _proxy_with_timeout_abort(
        self,
        client: httpx.AsyncClient,
        request: httpx.Request,
        send,
        state: FaultState,
        fault_token: int | None,
        timeout_seconds: float,
    ) -> None:
        response: httpx.Response | None = None
        response_started = False
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        try:
            response = await asyncio.wait_for(
                client.send(request, stream=True),
                timeout=timeout_seconds,
            )

            await send(
                {
                    "type": "http.response.start",
                    "status": response.status_code,
                    "headers": self._response_headers(response.headers.raw, aborting=True),
                }
            )
            response_started = True
            chunks = response.aiter_raw().__aiter__()
            while True:
                remaining = max(0.0, deadline - asyncio.get_running_loop().time())
                try:
                    chunk = await asyncio.wait_for(anext(chunks), timeout=remaining)
                except StopAsyncIteration:
                    break
                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True,
                    }
                )
            await state.mark_fault_upstream_completed(fault_token)
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        except TimeoutError as exc:
            if not response_started:
                await self._abort_response(
                    send,
                    200,
                    [(b"content-type", b"text/event-stream"), (b"cache-control", b"no-cache")],
                    b"",
                    reason="tool_timeout",
                )
            raise InjectedDownstreamAbort("tool_timeout") from exc
        except httpx.HTTPError as exc:
            logger.warning("Upstream timeout-scenario request failed: %s", exc)
            if response_started:
                raise InjectedDownstreamAbort("upstream_stream_error") from exc
            await self._send_json(send, 502, {"detail": type(exc).__name__})
        finally:
            if response is not None:
                await response.aclose()

    async def _abort_response(
        self,
        send,
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
        *,
        reason: str,
    ) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": self._response_headers(headers, aborting=True),
            }
        )
        prefix_length = max(1, min(len(body) // 2, 32))
        prefix = body[:prefix_length] if body else b"x"
        await send({"type": "http.response.body", "body": prefix, "more_body": True})
        raise InjectedDownstreamAbort(reason)

    def _build_upstream_url(self, target: int, scope) -> str:
        base = urlsplit(self._upstreams[target])
        request_path = scope.get("path") or "/mcp"
        path = "/mcp/" if request_path in {"/mcp", "/mcp/"} else request_path
        query = (scope.get("query_string") or b"").decode("latin-1")
        return urlunsplit((base.scheme, base.netloc, path, query, ""))

    @staticmethod
    def _query_case_id(scope) -> str:
        query = parse_qs((scope.get("query_string") or b"").decode("latin-1"))
        values = query.get("case_id") or []
        return str(values[0]) if values else "default"

    @staticmethod
    async def _read_body(receive) -> bytes:
        chunks: list[bytes] = []
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.disconnect":
                break
            chunks.append(message.get("body") or b"")
            more_body = bool(message.get("more_body"))
        return b"".join(chunks)

    @staticmethod
    async def _read_raw_response(response: httpx.Response) -> bytes:
        return b"".join([chunk async for chunk in response.aiter_raw()])

    @staticmethod
    def _jsonrpc_method(body: bytes) -> str | None:
        if not body:
            return None
        try:
            payload = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if isinstance(payload, dict) and isinstance(payload.get("method"), str):
            return payload["method"]
        return None

    @staticmethod
    def _header_value(headers: list[tuple[bytes, bytes]], name: bytes) -> str | None:
        for key, value in headers:
            if key.lower() == name:
                return value.decode("latin-1")
        return None

    @classmethod
    def _request_headers(cls, headers: list[tuple[bytes, bytes]]) -> list[tuple[bytes, bytes]]:
        connection_tokens = cls._connection_tokens(headers)
        blocked = _HOP_BY_HOP_HEADERS | connection_tokens | {b"host", b"content-length", b"x-fault-case-id"}
        return [(key, value) for key, value in headers if key.lower() not in blocked]

    @classmethod
    def _response_headers(
        cls,
        headers: list[tuple[bytes, bytes]],
        *,
        aborting: bool = False,
    ) -> list[tuple[bytes, bytes]]:
        connection_tokens = cls._connection_tokens(headers)
        blocked = _HOP_BY_HOP_HEADERS | connection_tokens
        if aborting:
            blocked = blocked | {b"content-length"}
        return [(key, value) for key, value in headers if key.lower() not in blocked]

    @staticmethod
    def _connection_tokens(headers: list[tuple[bytes, bytes]]) -> set[bytes]:
        tokens: set[bytes] = set()
        for key, value in headers:
            if key.lower() == b"connection":
                tokens.update(part.strip().lower() for part in value.split(b",") if part.strip())
        return tokens

    @staticmethod
    async def _send_json(send, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})


def _parse_upstreams() -> list[str]:
    raw = os.getenv(
        "MCP_STREAMABLE_FAULT_PROXY_UPSTREAMS",
        "http://mcp-streamable-demo-a:9001,http://mcp-streamable-demo-b:9002",
    )
    return [value.strip() for value in raw.split(",") if value.strip()]


app = MCPStreamableFaultProxy(_parse_upstreams())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Streamable HTTP MCP fault proxy")
    parser.add_argument("--port", type=int, default=8998)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port, http="h11", workers=1)
