from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import httpx
from anyio import ClosedResourceError
from langchain_mcp_adapters.client import MultiServerMCPClient
from yuxi.agents.mcp.mcp_auth.orchestrator import mcp_auth_context_var

if TYPE_CHECKING:
    from mcp import ClientSession

from cachetools import TTLCache

# 缓存存储格式: (server_name, user_id, department_id) -> (resolved_headers, connection_id)
_MCP_HEADERS_CACHE_TTL = float(os.environ.get("YUXI_MCP_HEADERS_CACHE_TTL", "60"))

# 长连接心跳间隔（秒）：定期 send_ping 防止远端 idle timeout 断连；0 表示关闭
_SESSION_PING_INTERVAL = float(os.environ.get("YUXI_MCP_SESSION_PING_INTERVAL", "30"))
_resolved_headers_cache: TTLCache = TTLCache(maxsize=1024, ttl=_MCP_HEADERS_CACHE_TTL)

# 逐请求变化的 headers，不应缓存——否则 Content-Length / Transfer-Encoding
# 会被旧值覆盖，导致 h11 检测到协议违规。
_PER_REQUEST_HEADERS = frozenset({"content-length", "transfer-encoding"})


def clear_resolved_headers_cache() -> None:
    """清除解析后的 headers 缓存"""
    _resolved_headers_cache.clear()


def clear_server_resolved_headers_cache(server_name: str) -> None:
    """清除指定服务器的解析后 headers 缓存"""
    stale_keys = [k for k in _resolved_headers_cache if k[0] == server_name]
    for key in stale_keys:
        _resolved_headers_cache.pop(key, None)


logger = logging.getLogger("yuxi.mcp.client_pool")


def _is_auth_error(exc: BaseException) -> bool:
    """检测异常是否为 401 鉴权错误"""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 401
    return False


async def _mark_mcp_connection_reauth_required(server_name: str) -> None:
    """标记对应 server_name + 当前 auth_context 的 MCPConnection 为 reauth_required"""
    auth_context = mcp_auth_context_var.get()
    if not auth_context:
        return

    try:
        from yuxi.agents.mcp.connection_service import _resolve_scope_id
        from yuxi.storage.postgres.manager import pg_manager
        from yuxi.storage.postgres.models_business import MCPConnection, MCPServer

        from sqlalchemy import select

        async with pg_manager.get_async_session_context() as session:
            # 查 server 获取 auth_config 以确定 binding_scope
            server_stmt = select(MCPServer).where(MCPServer.name == server_name)
            server_result = await session.execute(server_stmt)
            server = server_result.scalar_one_or_none()
            if server is None or not server.auth_config_json:
                return

            from yuxi.agents.mcp.mcp_auth.config_models import MCPAuthConfig

            auth_config = MCPAuthConfig.model_validate(server.auth_config_json)
            scope_id = _resolve_scope_id(auth_config.binding_scope, auth_context)
            if scope_id is None:
                return

            # 查找匹配的 active 连接
            stmt = select(MCPConnection).where(
                MCPConnection.server_name == server_name,
                MCPConnection.scope_type == auth_config.binding_scope,
                MCPConnection.scope_id == scope_id,
                MCPConnection.status == "active",
            )
            result = await session.execute(stmt)
            connection = result.scalar_one_or_none()
            if connection:
                connection.status = "reauth_required"
                connection.meta_json = connection.meta_json or {}
                connection.meta_json["last_error"] = "Authentication failed after retry"
                await session.commit()
                logger.info(f"Marked MCPConnection for '{server_name}' as reauth_required")
    except Exception as exc:
        logger.debug(f"Failed to mark MCPConnection reauth_required for '{server_name}': {exc}")


class DynamicMCPTokenAuth(httpx.Auth):
    """动态 MCP Token 认证拦截器，每次 HTTP 请求前从 ContextVar 动态读取并注入 Authorization 头部

    支持 401 自动重试：当上游 MCP 服务器返回 401 时，清除本地缓存并强制刷新 token，
    通过 httpx.Auth 二次 yield 机制重发请求。
    """

    def __init__(self, server_name: str):
        self.server_name = server_name

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        # 1. 解析并注入 headers
        headers = await self._resolve_token_headers(self.server_name, request)
        logger.info(
            f"DynamicMCPTokenAuth auth_flow for '{self.server_name}': "
            f"resolved {len(headers)} headers, url={request.url}"
        )
        for k, v in headers.items():
            request.headers[k] = str(v)

        # 2. 发出请求
        response = yield request

        # 3. 401 重试（httpx.Auth 原生机制：二次 yield 触发重发）
        if response is not None and response.status_code == 401:
            # 清除缓存，强制刷新 token
            clear_server_resolved_headers_cache(self.server_name)
            await self._clear_redis_token_cache(self.server_name)
            headers = await self._resolve_token_headers(self.server_name, request, force_refresh=True)
            for k, v in headers.items():
                request.headers[k] = str(v)
            yield request

    async def _resolve_token_headers(
        self, server_name: str, request: httpx.Request, force_refresh: bool = False
    ) -> dict:
        """解析当前上下文对应的鉴权 headers

        Args:
            server_name: MCP 服务器名称
            request: 当前 HTTP 请求（用于可能的请求级别判断）
            force_refresh: 为 True 时跳过缓存，强制从 DB 重新获取

        Returns:
            需注入的 headers dict（已排除 per-request headers）
        """
        auth_context = mcp_auth_context_var.get()
        if not auth_context:
            logger.warning(f"_resolve_token_headers for '{server_name}': no auth_context, returning empty")
            return {}

        cache_key = (server_name, auth_context.user_id, auth_context.department_id)

        # 缓存查找
        if not force_refresh:
            cached = _resolved_headers_cache.get(cache_key)
            if cached is not None:
                cached_headers, _ = cached
                logger.info(f"_resolve_token_headers for '{server_name}': cache hit with {len(cached_headers)} headers")
                return {k: v for k, v in cached_headers.items() if k.lower() not in _PER_REQUEST_HEADERS}

        # 缓存未命中：查 DB
        try:
            from yuxi.storage.postgres.manager import pg_manager

            async with pg_manager.get_async_session_context() as session:
                from yuxi.agents.mcp.server_service import get_runtime_mcp_server_config

                runtime_config = await get_runtime_mcp_server_config(
                    server_name,
                    auth_context=auth_context,
                    db=session,
                )
                if runtime_config:
                    headers = dict(runtime_config.get("headers") or {})
                    connection_id = runtime_config.get("__yuxi_connection_id")
                    _resolved_headers_cache[cache_key] = (headers, connection_id)
                    logger.info(
                        f"_resolve_token_headers for '{server_name}': DB lookup got {len(headers)} headers, "
                        f"connection_id={connection_id}, url={runtime_config.get('url')}"
                    )
                    return {k: v for k, v in headers.items() if k.lower() not in _PER_REQUEST_HEADERS}
                else:
                    logger.debug(f"_resolve_token_headers for '{server_name}': DB lookup returned no runtime_config")
        except Exception as exc:
            logger.warning(f"DynamicMCPTokenAuth failed to resolve token headers for '{server_name}': {exc}")

        return {}

    async def _clear_redis_token_cache(self, server_name: str) -> None:
        """401 重试时清除 Redis token cache（需要缓存的 connection_id）"""
        auth_context = mcp_auth_context_var.get()
        if not auth_context:
            return

        cache_key = (server_name, auth_context.user_id, auth_context.department_id)
        cached = _resolved_headers_cache.get(cache_key)
        if cached is not None:
            _, connection_id = cached
            if connection_id is not None:
                try:
                    from yuxi.agents.mcp.mcp_auth.redis_token_cache import RedisTokenCache

                    await RedisTokenCache().delete_access_token(connection_id)
                except Exception as exc:
                    logger.debug(f"Failed to clear Redis token cache for connection {connection_id}: {exc}")


class _SessionProxy:
    """ClientSession 代理：将方法调用委托给当前活跃的 ClientSession。

    当 LongLivedSession 检测到连接断开并自动重连后，通过 set_session() 切换到
    新的 ClientSession。工具闭包捕获的是代理对象，切换后无需重新加载工具即可
    使用新 session。
    """

    def __init__(self):
        self._session: ClientSession | None = None

    def set_session(self, session: ClientSession | None) -> None:
        self._session = session

    async def disconnect(self) -> None:
        """断开当前 session，关闭 pending response streams 使 in-flight call_tool 快速失败。

        BaseSession.__aexit__ 只取消 task group，不关闭 per-request 的 response_stream，
        导致 response_stream_reader.receive() 无限阻塞。此方法主动关闭写端，
        让等在 receive() 的 call_tool 立刻收到 ClosedResourceError。
        """
        if self._session is None:
            return
        try:
            for stream in list(self._session._response_streams.values()):  # type: ignore[attr-defined]
                try:
                    await stream.aclose()
                except Exception:
                    pass
        except Exception:
            pass
        self._session = None

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    def __getattr__(self, name: str):
        session = self._session
        if session is None:
            raise ClosedResourceError()
        return getattr(session, name)


class LongLivedSession:
    """长期存活的 MCP Client 及其 Session 生命周期管理器

    支持 SSE/streamable_http 连接断开后自动重连：当底层 session 因网络中断、
    服务端关闭 SSE 流等原因退出时，_run_loop 会以指数退避重试，直到重建连接
    或收到 stop 信号。重连后通过 _SessionProxy 切换到新 session，工具闭包
    无需重建即可继续使用。
    """

    _RECONNECT_INITIAL_DELAY = 1.0
    _RECONNECT_MAX_DELAY = 30.0

    def __init__(self, client: MultiServerMCPClient, server_name: str):
        self.client = client
        self.server_name = server_name
        self._session_proxy = _SessionProxy()
        self._running = False
        self._loop_task: asyncio.Task | None = None
        self._ready_event = asyncio.Event()
        self._stop_event = asyncio.Event()

    @property
    def session(self) -> _SessionProxy:
        return self._session_proxy

    async def start(self):
        """在后台启动长连接 Session"""
        if not hasattr(self.client, "session"):
            self._session_proxy.set_session(self.client)
            self._ready_event.set()
            return

        self._running = True
        self._stop_event.clear()
        self._ready_event.clear()
        self._loop_task = asyncio.create_task(self._run_loop())
        # 等待 Session 成功连接并完成 initialize()
        await self._ready_event.wait()
        if not self._session_proxy.is_connected:
            raise RuntimeError(f"Failed to startup MCP ClientSession for {self.server_name}")

    async def _run_loop(self):
        reconnect_delay = self._RECONNECT_INITIAL_DELAY
        first_connect = True

        while not self._stop_event.is_set():
            try:
                async with self.client.session(self.server_name) as session:
                    self._session_proxy.set_session(session)
                    self._ready_event.set()
                    if not first_connect:
                        logger.info(f"MCP session reconnected for {self.server_name}")
                    first_connect = False
                    reconnect_delay = self._RECONNECT_INITIAL_DELAY
                    # 等待停止指令，期间定期 send_ping 防止远端 idle timeout 断连
                    await self._keep_alive_until_stopped(session)
                    break  # 正常退出（stop 请求）
            except BaseException as exc:
                if self._stop_event.is_set():
                    break
                if not self._session_proxy.is_connected:
                    # 首次连接失败，不重试，记录完整异常以辅助排查
                    logger.warning(f"Failed to start MCP session for {self.server_name}: {exc}", exc_info=True)
                    break
                sub_exc = exc
                # ExceptionGroup 可能包含子异常，展开显示根因
                if isinstance(exc, BaseExceptionGroup):
                    sub_exc = exc.exceptions[0] if exc.exceptions else exc
                    logger.warning(
                        f"MCP session loop stopped for {self.server_name}: "
                        f"{type(sub_exc).__name__}: {sub_exc}, "
                        f"reconnecting in {reconnect_delay:.0f}s"
                    )
                    logger.debug(f"MCP session ExceptionGroup details for {self.server_name}", exc_info=True)
                else:
                    logger.warning(
                        f"MCP session loop stopped for {self.server_name}: {exc}, "
                        f"reconnecting in {reconnect_delay:.0f}s"
                    )
                # 检测 401 鉴权错误，标记连接状态
                if _is_auth_error(sub_exc):
                    await _mark_mcp_connection_reauth_required(self.server_name)
                await self._session_proxy.disconnect()
                # 等待退避时间，期间如果收到 stop 信号则立即退出
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=reconnect_delay)
                    break
                except TimeoutError:
                    pass
                reconnect_delay = min(reconnect_delay * 2, self._RECONNECT_MAX_DELAY)

        self._session_proxy.set_session(None)
        self._running = False
        self._ready_event.set()

    async def _keep_alive_until_stopped(self, session: ClientSession) -> None:
        """定期发送 ping 保活长连接，直到收到 stop 信号。

        解决远端 MCP 服务器（如 Nginx 网关）idle timeout 关闭空闲 SSE 流的问题。
        ping 失败时抛出异常，由 _run_loop 的重连逻辑接管。
        """
        if _SESSION_PING_INTERVAL <= 0:
            await self._stop_event.wait()
            return

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=_SESSION_PING_INTERVAL)
                return  # stop 请求，正常退出
            except TimeoutError:
                pass

            try:
                await session.send_ping()
                logger.debug(f"MCP session ping OK for {self.server_name}")
            except Exception as e:
                logger.warning(f"MCP session ping failed for {self.server_name}: {type(e).__name__}: {e}")
                raise

    async def stop(self):
        """停止长连接，回收子进程与 TCP 连接资源"""
        self._stop_event.set()
        if self._loop_task:
            try:
                await asyncio.wait_for(self._loop_task, timeout=5.0)
            except TimeoutError:
                logger.warning(f"Timeout waiting for long-lived session of {self.server_name} to stop.")
                self._loop_task.cancel()
            except Exception as exc:
                logger.debug(f"Exception during long-lived session cleanup of {self.server_name}: {exc}")
            self._loop_task = None


class MCPClientPool:
    """MCP 客户端连接池实现"""

    def __init__(self):
        # 缓存键格式: (server_name, partition_key) -> tuple[LongLivedSession, str] | asyncio.Future
        self._sessions: dict[tuple[str, str], Any] = {}
        self._dict_lock = asyncio.Lock()
        self._closed = False

    def _calculate_config_hash(self, config: dict[str, Any]) -> str:
        """根据配置计算 Hash 用于比对配置是否脏变"""
        clean_config = {
            k: v
            for k, v in config.items()
            if k
            not in {
                "__yuxi_cache_partition",
                "__yuxi_allow_global_cache",
                "disabled_tools",
            }
        }
        # 剔除 header 中可能随时变化的 token，以便准确比对静态配置
        transient_header_names = {"authorization"}
        headers = dict(clean_config.get("headers") or {})
        headers = {key: value for key, value in headers.items() if key.lower() not in transient_header_names}
        if headers:
            clean_config["headers"] = headers
        elif "headers" in clean_config:
            clean_config["headers"] = {}

        payload = json.dumps(clean_config, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    async def _get_mcp_client(self, server_configs: dict[str, Any] | None = None) -> MultiServerMCPClient | None:
        try:
            client = MultiServerMCPClient(server_configs)  # pyright: ignore[reportArgumentType]
            logger.info(f"Initialized MCP client with servers: {list(server_configs.keys() or [])}")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            return None

    async def get_session(
        self,
        server_name: str,
        partition_key: str,
        runtime_config: dict[str, Any],
    ) -> ClientSession:
        """获取或重建匹配当前配置的 ClientSession"""
        config_hash = self._calculate_config_hash(runtime_config)
        cache_key = (server_name, partition_key)

        while True:
            async with self._dict_lock:
                if self._closed:
                    raise RuntimeError("MCPClientPool is shut down")
                existing = self._sessions.get(cache_key)

                if existing is not None:
                    if isinstance(existing, asyncio.Future):
                        future = existing
                        stale_session = None
                    else:
                        ll_session, cached_hash = existing
                        if cached_hash == config_hash and ll_session.session.is_connected:
                            return ll_session.session

                        self._sessions.pop(cache_key, None)
                        stale_session = ll_session
                        future = None
                else:
                    future = None
                    stale_session = None

                    # 仅驱逐同分区内的旧 revision 条目，不跨分区驱逐
                    base_partition = partition_key.split(":s", 1)[0]
                    stale_keys = [
                        k
                        for k in self._sessions
                        if k[0] == server_name and k != cache_key and k[1].startswith(base_partition + ":s")
                    ]
                    stale_other_sessions: list[LongLivedSession] = []
                    for stale_key in stale_keys:
                        stale_val = self._sessions.pop(stale_key)
                        if not isinstance(stale_val, asyncio.Future):
                            stale_other_sessions.append(stale_val[0])

                    init_future = asyncio.get_running_loop().create_future()
                    self._sessions[cache_key] = init_future
                    break

            if future is not None:
                await future
                continue

            if stale_session is not None:
                logger.info(f"Destroying stale/disconnected MCP session for {cache_key}")
                await stale_session.stop()
                continue

        for s_session in stale_other_sessions:
            logger.info("Evicting stale MCP session")
            await s_session.stop()

        try:
            client_config = dict(runtime_config)
            # 仅动态 token provider 需要挂载 DynamicMCPTokenAuth
            # （legacy_static / bound_secret / stdio_env 的 headers 已在 resolve_runtime_mcp_config 中静态注入）
            auth_config_payload = client_config.get("auth_config")
            needs_dynamic_auth = False
            if auth_config_payload:
                from yuxi.agents.mcp.mcp_auth.config_models import MCPAuthConfig

                try:
                    provider = MCPAuthConfig.model_validate(auth_config_payload).provider
                    needs_dynamic_auth = provider in MCPAuthConfig.DYNAMIC_TOKEN_PROVIDERS
                except Exception:
                    pass
            # 剥离所有内部字段：__yuxi_ 前缀的内部透传键 + 非 SDK 字段
            client_config = {
                k: v for k, v in client_config.items()
                if not k.startswith("__yuxi_") and k not in ("disabled_tools", "auth_config")
            }

            if client_config.get("transport") in ("sse", "http", "streamable_http", "streamable-http"):
                if needs_dynamic_auth:
                    client_config["auth"] = DynamicMCPTokenAuth(server_name)
                # langchain_mcp_adapters 的 _create_streamable_http_session 不会把
                # sse_read_timeout 传给 ClientSession.read_timeout_seconds，
                # 导致 send_request 的 fail_after(timeout=None) 无限等待。
                # 此处通过 session_kwargs 显式传递，使 call_tool 在超时内必须返回。
                sse_read_timeout = client_config.get("sse_read_timeout")
                timeout = client_config.get("timeout")
                # 优先使用 sse_read_timeout，其次 timeout，最后默认 300s
                read_timeout = sse_read_timeout or timeout or 300
                from datetime import timedelta

                client_config.setdefault("session_kwargs", {})
                client_config["session_kwargs"]["read_timeout_seconds"] = timedelta(seconds=float(read_timeout))

            logger.info(
                f"Creating new long-lived MCP session for {cache_key} (transport: {client_config.get('transport')})"
            )
            client = await self._get_mcp_client({server_name: client_config})
            if client is None:
                raise RuntimeError(f"Failed to initialize MCP client for {server_name}")
            ll_session = LongLivedSession(client, server_name)
            await ll_session.start()

            result = (ll_session, config_hash)
            published = False
            async with self._dict_lock:
                # 清缓存或移除连接可能已取消/移除本次初始化，不能再发布该 session。
                if self._sessions.get(cache_key) is init_future and not init_future.done():
                    init_future.set_result(result)
                    self._sessions[cache_key] = result
                    published = True
                elif not init_future.done():
                    # 并发 remove_session 已移除该 future，唤醒等待者后由其重新获取。
                    init_future.set_result(result)

                pool_closed = self._closed

            if not published:
                await ll_session.stop()
                if pool_closed:
                    raise RuntimeError("MCPClientPool is shut down")
                return await self.get_session(server_name, partition_key, runtime_config)

            return ll_session.session

        except BaseException as exc:
            if not init_future.done():
                init_future.set_exception(exc)
                init_future.exception()
            async with self._dict_lock:
                if self._sessions.get(cache_key) is init_future:
                    self._sessions.pop(cache_key, None)
            raise

    async def remove_session(self, server_name: str, partition_key: str):
        """移除指定 key 的连接，强制下一次请求重新创建"""
        cache_key = (server_name, partition_key)
        ll_session: LongLivedSession | None = None
        async with self._dict_lock:
            val = self._sessions.pop(cache_key, None)
            if val is not None and not isinstance(val, asyncio.Future):
                ll_session = val[0]
                logger.info(f"Removing invalid session for {cache_key} from pool")
        # 在锁外执行 stop()，避免阻塞其他池操作
        if ll_session is not None:
            try:
                await ll_session.stop()
            except Exception as exc:
                logger.debug(f"Exception during session cleanup of {cache_key}: {exc}")

    async def remove_sessions_by_server(self, server_name: str) -> None:
        """移除指定 server 下的所有连接，用于连接类错误后的全量恢复"""
        keys_to_remove: list[tuple[str, str]] = []
        async with self._dict_lock:
            for key in list(self._sessions):
                if key[0] == server_name:
                    keys_to_remove.append(key)
        for key in keys_to_remove:
            await self.remove_session(key[0], key[1])

    async def remove_sessions_by_partition(self, server_name: str, base_partition: str) -> None:
        """移除指定 server 下匹配 base_partition 前缀的所有连接

        Args:
            server_name: 服务器名称
            base_partition: 分区前缀，如 "connection:101" 或 "server"
        """
        partition_prefix = base_partition + ":s"
        keys_to_remove: list[tuple[str, str]] = []
        async with self._dict_lock:
            for key in list(self._sessions):
                if key[0] == server_name and key[1].startswith(partition_prefix):
                    keys_to_remove.append(key)
        for key in keys_to_remove:
            await self.remove_session(key[0], key[1])

    async def ensure_prewarm(
        self,
        server_name: str,
        partition_key: str,
        runtime_config: dict[str, Any],
    ):
        """后台异步预热加载，减少首次访问时的冷启动卡顿"""
        try:
            await self.get_session(server_name, partition_key, runtime_config)
        except Exception as exc:
            logger.warning(f"Failed to pre-warm MCP server '{server_name}': {exc}")

    async def clear_sessions(self) -> None:
        """关闭并清空现有连接，连接池保持可用。"""
        async with self._dict_lock:
            sessions_to_stop = []
            for cache_key, val in list(self._sessions.items()):
                if isinstance(val, asyncio.Future):
                    val.cancel()
                else:
                    ll_session, _ = val
                    sessions_to_stop.append((cache_key, ll_session))
            self._sessions.clear()

        for cache_key, ll_session in sessions_to_stop:
            logger.info(f"Stopping MCP session for {cache_key} during pool cleanup")
            await ll_session.stop()

    async def shutdown(self) -> None:
        """永久关闭连接池并回收全部连接。"""
        async with self._dict_lock:
            self._closed = True
        await self.clear_sessions()


# 全局单例连接池
mcp_client_pool = MCPClientPool()
