from __future__ import annotations

import asyncio
import logging
import runpy
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from yuxi.agents.mcp import client_pool as client_pool_module
from yuxi.agents.mcp.client_pool import MCPClientPool, LongLivedSession, _SessionProxy


@pytest.mark.asyncio
async def test_long_lived_session_lifecycle():
    """测试 LongLivedSession 正常的启动与停止流程"""
    mock_client = MagicMock()
    mock_session = MagicMock()

    # 模拟 client.session() 返回一个 AsyncContextManager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    mock_client.session.return_value = mock_context

    ll_session = LongLivedSession(mock_client, "test_server")

    # 启动
    await ll_session.start()
    assert ll_session._running is True
    assert ll_session.session.is_connected is True
    assert ll_session.session._session == mock_session
    mock_client.session.assert_called_once_with("test_server")

    # 停止
    await ll_session.stop()
    assert ll_session._running is False
    assert ll_session.session.is_connected is False


@pytest.mark.asyncio
async def test_long_lived_session_start_cancellation_stops_created_run_loop():
    connect_entered = asyncio.Event()

    class SessionContext:
        async def __aenter__(self):
            connect_entered.set()
            await asyncio.Event().wait()

        async def __aexit__(self, exc_type, exc, traceback):
            del exc_type, exc, traceback

    client = MagicMock()
    client.session.return_value = SessionContext()
    ll_session = LongLivedSession(client, "test_server")

    start_task = asyncio.create_task(ll_session.start())
    await connect_entered.wait()
    start_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await start_task

    assert ll_session._loop_task is None
    assert ll_session.is_running is False
    assert ll_session.session.is_connected is False


@pytest.mark.asyncio
async def test_long_lived_session_stop_cleans_up_already_cancelled_run_loop():
    mock_client = MagicMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = _FakeSession()
    mock_client.session.return_value = mock_context
    ll_session = LongLivedSession(mock_client, "test_server")
    await ll_session.start()

    loop_task = ll_session._loop_task
    assert loop_task is not None
    loop_task.cancel()
    await asyncio.gather(loop_task, return_exceptions=True)

    await ll_session.stop()

    assert ll_session._loop_task is None
    assert ll_session.is_running is False
    assert ll_session.session.is_connected is False


@pytest.mark.asyncio
async def test_long_lived_session_stop_preserves_external_cancellation():
    blocker = asyncio.create_task(asyncio.Event().wait())
    ll_session = LongLivedSession(MagicMock(), "test_server")
    ll_session._running = True
    ll_session._loop_task = blocker

    stop_task = asyncio.create_task(ll_session.stop())
    await asyncio.sleep(0)
    stop_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await stop_task

    await asyncio.gather(blocker, return_exceptions=True)


@pytest.mark.asyncio
async def test_pool_shutdown_continues_after_owner_run_loop_was_cancelled():
    mock_client = MagicMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = _FakeSession()
    mock_client.session.return_value = mock_context
    cancelled_owner = LongLivedSession(mock_client, "cancelled")
    await cancelled_owner.start()
    assert cancelled_owner._loop_task is not None
    cancelled_owner._loop_task.cancel()
    await asyncio.gather(cancelled_owner._loop_task, return_exceptions=True)

    other_owner = MagicMock()
    other_owner.stop = AsyncMock()
    pool = MCPClientPool()
    pool._sessions[("cancelled", "p1")] = (cancelled_owner, "hash-1")
    pool._sessions[("other", "p1")] = (other_owner, "hash-2")

    await pool.shutdown()

    other_owner.stop.assert_awaited_once()


class _FakeSession:
    def __init__(self):
        self._response_streams = {}


@pytest.mark.asyncio
async def test_session_proxy_tracks_generation_and_wakes_all_new_session_waiters():
    proxy = _SessionProxy()
    first_session = _FakeSession()
    second_session = _FakeSession()

    assert proxy.generation == 0

    proxy.set_session(first_session)
    first_generation = proxy.generation
    assert first_generation == 1

    await proxy.disconnect()
    assert proxy.is_connected is False
    assert proxy.generation == first_generation

    waiters = [
        asyncio.create_task(proxy.wait_for_new_session(first_generation, timeout=0.5))
        for _ in range(2)
    ]
    await asyncio.sleep(0)
    proxy.set_session(second_session)

    assert await asyncio.gather(*waiters) == [True, True]
    assert proxy.generation == first_generation + 1
    assert proxy._session is second_session


@pytest.mark.asyncio
async def test_session_proxy_wait_for_new_session_times_out_without_generation_change():
    proxy = _SessionProxy()
    proxy.set_session(_FakeSession())

    generation = proxy.generation

    assert await proxy.wait_for_new_session(generation, timeout=0.01) is False
    assert proxy.generation == generation


@pytest.mark.asyncio
async def test_session_proxy_wait_for_session_ignores_transient_connection_before_timeout():
    proxy = _SessionProxy()

    waiter = asyncio.create_task(proxy.wait_for_session(timeout=0.5))
    await asyncio.sleep(0)
    proxy.set_session(_FakeSession())
    await proxy.disconnect()
    await asyncio.sleep(0)

    assert waiter.done() is False

    proxy.set_session(_FakeSession())
    assert await waiter is True


@pytest.mark.asyncio
async def test_session_proxy_disconnect_marks_unavailable_before_closing_pending_streams():
    proxy = _SessionProxy()
    stream = AsyncMock()
    stream.aclose.side_effect = lambda: assert_proxy_disconnected(proxy)
    session = _FakeSession()
    session._response_streams[1] = stream
    proxy.set_session(session)

    await proxy.disconnect()

    stream.aclose.assert_awaited_once()


def assert_proxy_disconnected(proxy: _SessionProxy) -> None:
    assert proxy.is_connected is False


def test_request_reconnect_distinguishes_accepted_merged_stale_and_stopped():
    client = MagicMock()
    ll_session = LongLivedSession(client, "test_server")
    ll_session._running = True
    ll_session.session.set_session(_FakeSession())
    generation = ll_session.session.generation

    assert (
        ll_session.session.request_reconnect(generation)
        is client_pool_module.ReconnectRequestStatus.ACCEPTED
    )
    assert ll_session._reconnect_event.is_set()

    ll_session._reconnect_event.clear()
    assert (
        ll_session.session.request_reconnect(generation)
        is client_pool_module.ReconnectRequestStatus.MERGED
    )
    assert ll_session._reconnect_event.is_set() is False

    ll_session.session.set_session(_FakeSession())
    assert (
        ll_session.session.request_reconnect(generation)
        is client_pool_module.ReconnectRequestStatus.STALE_GENERATION
    )
    assert ll_session._reconnect_event.is_set() is False

    ll_session._stop_event.set()
    assert (
        ll_session.session.request_reconnect(ll_session.session.generation)
        is client_pool_module.ReconnectRequestStatus.STOPPED
    )

    ll_session._stop_event.clear()
    ll_session._running = False
    assert (
        ll_session.session.request_reconnect(ll_session.session.generation)
        is client_pool_module.ReconnectRequestStatus.STOPPED
    )


@pytest.mark.asyncio
async def test_request_reconnect_returns_stopped_without_background_session_owner():
    ll_session = LongLivedSession(object(), "test_server")
    await ll_session.start()

    assert (
        ll_session.session.request_reconnect(ll_session.session.generation)
        is client_pool_module.ReconnectRequestStatus.STOPPED
    )

    await ll_session.stop()


@pytest.mark.asyncio
async def test_long_lived_session_recovers_after_consecutive_reconnect_failures():
    sessions = [_FakeSession(), _FakeSession()]
    attempts = 0

    class SessionContext:
        async def __aenter__(self):
            nonlocal attempts
            attempts += 1
            if attempts in {2, 3}:
                raise ConnectionError(f"reconnect attempt {attempts} failed")
            return sessions[0] if attempts == 1 else sessions[1]

        async def __aexit__(self, exc_type, exc, traceback):
            del exc_type, exc, traceback

    class FakeClient:
        def session(self, server_name):
            assert server_name == "test_server"
            return SessionContext()

    ll_session = LongLivedSession(FakeClient(), "test_server")
    ll_session._RECONNECT_INITIAL_DELAY = 0
    ll_session._RECONNECT_MAX_DELAY = 0

    await ll_session.start()
    original_proxy = ll_session.session
    first_generation = original_proxy.generation

    assert (
        original_proxy.request_reconnect(first_generation)
        is client_pool_module.ReconnectRequestStatus.ACCEPTED
    )
    assert await original_proxy.wait_for_new_session(first_generation, timeout=0.5) is True
    assert attempts == 4
    assert ll_session.session is original_proxy
    assert original_proxy.generation == first_generation + 1
    assert ll_session.is_running is True

    await ll_session.stop()


@pytest.mark.asyncio
async def test_long_lived_session_reconnects_when_reader_error_event_is_set():
    sessions = [_FakeSession(), _FakeSession()]
    attempts = 0
    reader_error_event = asyncio.Event()

    class SessionContext:
        async def __aenter__(self):
            nonlocal attempts
            attempts += 1
            return sessions[min(attempts - 1, 1)]

        async def __aexit__(self, exc_type, exc, traceback):
            del exc_type, exc, traceback

    class FakeClient:
        def session(self, server_name):
            assert server_name == "test_server"
            return SessionContext()

    client = FakeClient()
    ll_session = LongLivedSession(client, "test_server", reader_error_event=reader_error_event)
    ll_session._RECONNECT_INITIAL_DELAY = 0
    ll_session._RECONNECT_MAX_DELAY = 0

    await ll_session.start()
    first_generation = ll_session.session.generation
    reader_error_event.set()

    assert await ll_session.session.wait_for_new_session(first_generation, timeout=0.5) is True
    assert attempts == 2

    await ll_session.stop()


@pytest.mark.asyncio
async def test_long_lived_session_keeps_reader_error_reported_during_session_enter():
    reader_error_event = asyncio.Event()
    second_session_entered = asyncio.Event()
    release_second_session = asyncio.Event()
    attempts = 0

    class SessionContext:
        async def __aenter__(self):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                reader_error_event.set()
            else:
                second_session_entered.set()
                await release_second_session.wait()
            return _FakeSession()

        async def __aexit__(self, exc_type, exc, traceback):
            del exc_type, exc, traceback

    class FakeClient:
        def session(self, server_name):
            assert server_name == "test_server"
            return SessionContext()

    ll_session = LongLivedSession(
        FakeClient(),
        "test_server",
        reader_error_event=reader_error_event,
    )
    ll_session._RECONNECT_INITIAL_DELAY = 0
    ll_session._RECONNECT_MAX_DELAY = 0

    start_task = asyncio.create_task(ll_session.start())
    await second_session_entered.wait()

    assert start_task.done() is False
    assert attempts == 2

    release_second_session.set()
    await asyncio.wait_for(start_task, timeout=0.5)

    await ll_session.stop()


@pytest.mark.asyncio
async def test_long_lived_session_keeps_retrying_after_initial_reader_disconnect():
    reader_error_event = asyncio.Event()
    attempts = 0

    class SessionContext:
        async def __aenter__(self):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                reader_error_event.set()
                return _FakeSession()
            if attempts in {2, 3}:
                raise ConnectionError(f"reconnect attempt {attempts} failed")
            return _FakeSession()

        async def __aexit__(self, exc_type, exc, traceback):
            del exc_type, exc, traceback

    class FakeClient:
        def session(self, server_name):
            assert server_name == "test_server"
            return SessionContext()

    ll_session = LongLivedSession(
        FakeClient(),
        "test_server",
        reader_error_event=reader_error_event,
    )
    ll_session._RECONNECT_INITIAL_DELAY = 0
    ll_session._RECONNECT_MAX_DELAY = 0

    await ll_session.start()

    assert attempts == 4
    assert ll_session.session.is_connected is True

    await ll_session.stop()


@pytest.mark.asyncio
async def test_client_pool_sse_reader_handler_preserves_existing_handler_and_signals_owner():
    observed_messages = []

    async def existing_message_handler(message):
        observed_messages.append(message)

    original_session_kwargs = {"message_handler": existing_message_handler}
    runtime_config = {
        "transport": "sse",
        "url": "http://mcp.test/sse",
        "session_kwargs": original_session_kwargs,
    }
    mock_client = MagicMock()
    mock_session = MagicMock(is_connected=True)
    mock_owner = MagicMock(session=mock_session)
    mock_owner.start = AsyncMock()
    mock_owner.stop = AsyncMock()
    pool = MCPClientPool()

    with (
        patch("yuxi.agents.mcp.client_pool.MultiServerMCPClient", return_value=mock_client) as client_class,
        patch("yuxi.agents.mcp.client_pool.LongLivedSession", return_value=mock_owner) as owner_class,
    ):
        assert await pool.get_session("test_server", "p1", runtime_config) is mock_session

    client_config = client_class.call_args.args[0]["test_server"]
    message_handler = client_config["session_kwargs"]["message_handler"]
    reader_error_event = owner_class.call_args.kwargs["reader_error_event"]
    error = httpx.RemoteProtocolError(
        "peer closed connection without sending complete message body (incomplete chunked read)"
    )

    await message_handler(error)

    assert observed_messages == [error]
    assert reader_error_event.is_set()
    assert client_config["session_kwargs"] is not original_session_kwargs
    assert runtime_config["session_kwargs"] is original_session_kwargs


def test_mcp_sse_restart_disconnect_log_is_downgraded_without_traceback(caplog):
    sdk_logger = logging.getLogger("mcp.client.sse")
    error = httpx.RemoteProtocolError(
        "peer closed connection without sending complete message body (incomplete chunked read)"
    )

    with caplog.at_level(logging.WARNING, logger="mcp.client.sse"):
        try:
            raise error
        except httpx.RemoteProtocolError:
            sdk_logger.exception("Error in sse_reader")

    record = caplog.records[-1]
    assert record.levelno == logging.WARNING
    assert record.exc_info is None
    assert record.getMessage() == "MCP SSE connection closed by peer; reconnecting"


def test_mcp_sse_unexpected_reader_error_keeps_error_traceback(caplog):
    sdk_logger = logging.getLogger("mcp.client.sse")

    with caplog.at_level(logging.ERROR, logger="mcp.client.sse"):
        try:
            raise ValueError("invalid event payload")
        except ValueError:
            sdk_logger.exception("Error in sse_reader")

    record = caplog.records[-1]
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert record.getMessage() == "Error in sse_reader"


def test_mcp_sse_similar_protocol_error_keeps_error_traceback(caplog):
    sdk_logger = logging.getLogger("mcp.client.sse")

    with caplog.at_level(logging.ERROR, logger="mcp.client.sse"):
        try:
            raise httpx.RemoteProtocolError("proxy returned incomplete chunked read metadata")
        except httpx.RemoteProtocolError:
            sdk_logger.exception("Error in sse_reader")

    record = caplog.records[-1]
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert record.getMessage() == "Error in sse_reader"


@pytest.mark.parametrize(
    "sdk_message",
    ["Encountered SSE exception", "Error parsing server message", "Error in post_writer"],
)
def test_mcp_sse_other_sdk_error_messages_keep_error_traceback(caplog, sdk_message):
    sdk_logger = logging.getLogger("mcp.client.sse")

    with caplog.at_level(logging.ERROR, logger="mcp.client.sse"):
        try:
            raise httpx.RemoteProtocolError(
                "peer closed connection without sending complete message body (incomplete chunked read)"
            )
        except httpx.RemoteProtocolError:
            sdk_logger.exception(sdk_message)

    record = caplog.records[-1]
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert record.getMessage() == sdk_message


def test_mcp_sse_disconnect_filter_installation_is_reload_safe():
    sdk_logger = logging.getLogger("mcp.client.sse")
    marker = client_pool_module._MCP_SSE_FILTER_MARKER
    before = sum(bool(getattr(log_filter, marker, False)) for log_filter in sdk_logger.filters)

    runpy.run_path(client_pool_module.__file__, run_name="client_pool_filter_reload_test")

    after = sum(bool(getattr(log_filter, marker, False)) for log_filter in sdk_logger.filters)
    assert before == after == 1


@pytest.mark.asyncio
async def test_client_pool_reuse_and_recreate():
    """测试 MCPClientPool 的复用逻辑与配置脏变重构逻辑"""
    pool = MCPClientPool()

    config_1 = {
        "transport": "stdio",
        "command": "node",
        "args": ["file1.js"],
        "__yuxi_cache_partition": "p1",
    }

    config_2 = {
        "transport": "stdio",
        "command": "node",
        "args": ["file1.js"],
        "__yuxi_cache_partition": "p1",
    }

    config_changed = {
        "transport": "stdio",
        "command": "node",
        "args": ["file2.js"],  # 配置发生改变
        "__yuxi_cache_partition": "p1",
    }

    mock_client_instance = MagicMock()
    mock_session_instance = MagicMock()

    # Mock LongLivedSession 的 start/stop 以防真实建连
    with patch("yuxi.agents.mcp.client_pool.MultiServerMCPClient", return_value=mock_client_instance), \
         patch("yuxi.agents.mcp.client_pool.LongLivedSession") as MockLongLivedSession:

        mock_ll_instance = MagicMock()
        mock_ll_instance.session = mock_session_instance
        mock_ll_instance.session.is_connected = True
        mock_ll_instance.start = AsyncMock()
        mock_ll_instance.stop = AsyncMock()
        MockLongLivedSession.return_value = mock_ll_instance

        # 1. 首次获取，创建新 Session
        session_1 = await pool.get_session("test_server", "p1", config_1)
        assert session_1 == mock_session_instance
        assert MockLongLivedSession.call_count == 1
        mock_ll_instance.start.assert_called_once()

        # 2. 相同配置获取，直接复用
        session_2 = await pool.get_session("test_server", "p1", config_2)
        assert session_2 == mock_session_instance
        assert MockLongLivedSession.call_count == 1  # 没增加，说明复用了

        # 3. 配置改变获取，销毁旧的，重新创建
        session_changed = await pool.get_session("test_server", "p1", config_changed)
        assert session_changed == mock_session_instance
        # 销毁被调用了
        mock_ll_instance.stop.assert_called_once()
        # 创建计数增加
        assert MockLongLivedSession.call_count == 2

        # 4. 清空现有连接后，连接池仍可继续创建连接
        await pool.clear_sessions()
        assert mock_ll_instance.stop.call_count == 2  # 新增的那个也被 stop
        assert len(pool._sessions) == 0

        session_after_clear = await pool.get_session("test_server", "p1", config_1)
        assert session_after_clear == mock_session_instance
        assert MockLongLivedSession.call_count == 3

        # 5. 应用退出时永久关闭连接池
        await pool.shutdown()
        assert mock_ll_instance.stop.call_count == 3
        with pytest.raises(RuntimeError, match="MCPClientPool is shut down"):
            await pool.get_session("test_server", "p1", config_1)


@pytest.mark.asyncio
async def test_client_pool_waits_for_same_owner_to_recover_without_replacing_it(monkeypatch):
    monkeypatch.setattr("yuxi.agents.mcp.client_pool.MCP_TOOL_RECONNECT_WAIT_SECONDS", 0.5)
    pool = MCPClientPool()
    config = {"transport": "stdio", "command": "node", "args": ["server.js"]}
    config_hash = pool._calculate_config_hash(config)
    proxy = _SessionProxy()
    owner = MagicMock(session=proxy, is_running=True)
    owner.stop = AsyncMock()
    cache_key = ("test_server", "p1")
    pool._sessions[cache_key] = (owner, config_hash)

    get_session_task = asyncio.create_task(pool.get_session("test_server", "p1", config))
    await asyncio.sleep(0)
    assert get_session_task.done() is False

    proxy.set_session(_FakeSession())

    assert await get_session_task is proxy
    assert pool._sessions[cache_key] == (owner, config_hash)
    owner.stop.assert_not_awaited()


@pytest.mark.asyncio
async def test_client_pool_recovery_timeout_preserves_running_owner(monkeypatch):
    monkeypatch.setattr("yuxi.agents.mcp.client_pool.MCP_TOOL_RECONNECT_WAIT_SECONDS", 0.01)
    pool = MCPClientPool()
    config = {"transport": "stdio", "command": "node", "args": ["server.js"]}
    config_hash = pool._calculate_config_hash(config)
    proxy = _SessionProxy()
    owner = MagicMock(session=proxy, is_running=True)
    owner.stop = AsyncMock()
    cache_key = ("test_server", "p1")
    pool._sessions[cache_key] = (owner, config_hash)

    with pytest.raises(client_pool_module.MCPConnectionRecoveringError, match="test_server"):
        await pool.get_session("test_server", "p1", config)

    assert pool._sessions[cache_key] == (owner, config_hash)
    owner.stop.assert_not_awaited()


@pytest.mark.asyncio
async def test_client_pool_waits_for_recovery_outside_dictionary_lock(monkeypatch):
    monkeypatch.setattr("yuxi.agents.mcp.client_pool.MCP_TOOL_RECONNECT_WAIT_SECONDS", 0.5)
    pool = MCPClientPool()
    config = {"transport": "stdio", "command": "node", "args": ["server.js"]}
    config_hash = pool._calculate_config_hash(config)
    recovering_proxy = _SessionProxy()
    recovering_owner = MagicMock(session=recovering_proxy, is_running=True)
    connected_proxy = _SessionProxy()
    connected_proxy.set_session(_FakeSession())
    connected_owner = MagicMock(session=connected_proxy, is_running=True)
    pool._sessions[("recovering", "p1")] = (recovering_owner, config_hash)
    pool._sessions[("connected", "p1")] = (connected_owner, config_hash)

    recovering_task = asyncio.create_task(pool.get_session("recovering", "p1", config))
    await asyncio.sleep(0)

    assert await asyncio.wait_for(pool.get_session("connected", "p1", config), timeout=0.1) is connected_proxy
    assert recovering_task.done() is False

    recovering_proxy.set_session(_FakeSession())
    assert await recovering_task is recovering_proxy


@pytest.mark.asyncio
async def test_client_pool_waiter_cancellation_does_not_cancel_shared_initialization():
    pool = MCPClientPool()
    start_entered = asyncio.Event()
    release_start = asyncio.Event()
    created_sessions = []

    class FakeLongLivedSession:
        def __init__(self, client, server_name):
            del client, server_name
            self.session = MagicMock(is_connected=True)
            self.stop = AsyncMock()
            created_sessions.append(self)

        async def start(self):
            start_entered.set()
            await release_start.wait()

    async def fake_get_mcp_client(server_configs):
        del server_configs
        return MagicMock()

    pool._get_mcp_client = fake_get_mcp_client
    config = {"transport": "stdio", "command": "node", "args": ["server.js"]}
    cache_key = ("test_server", "p1")

    with patch("yuxi.agents.mcp.client_pool.LongLivedSession", FakeLongLivedSession):
        owner_task = asyncio.create_task(pool.get_session("test_server", "p1", config))
        await start_entered.wait()
        waiter_task = asyncio.create_task(pool.get_session("test_server", "p1", config))
        await asyncio.sleep(0)

        waiter_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter_task

        init_future = pool._sessions[cache_key]
        assert isinstance(init_future, asyncio.Future)
        assert init_future.cancelled() is False

        release_start.set()
        session = await owner_task

    assert session is created_sessions[0].session
    created_sessions[0].stop.assert_not_awaited()
    await pool.shutdown()


@pytest.mark.asyncio
async def test_client_pool_owner_cancellation_stops_unpublished_session():
    pool = MCPClientPool()
    start_entered = asyncio.Event()
    created_sessions = []

    class FakeLongLivedSession:
        def __init__(self, client, server_name):
            del client, server_name
            self.session = MagicMock(is_connected=True)
            self.stop = AsyncMock()
            created_sessions.append(self)

        async def start(self):
            start_entered.set()
            await asyncio.Event().wait()

    async def fake_get_mcp_client(server_configs):
        del server_configs
        return MagicMock()

    pool._get_mcp_client = fake_get_mcp_client
    config = {"transport": "stdio", "command": "node", "args": ["server.js"]}

    with patch("yuxi.agents.mcp.client_pool.LongLivedSession", FakeLongLivedSession):
        owner_task = asyncio.create_task(pool.get_session("test_server", "p1", config))
        await start_entered.wait()
        owner_task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await owner_task

    created_sessions[0].stop.assert_awaited_once()
    assert pool._sessions == {}


@pytest.mark.asyncio
async def test_client_pool_evicts_stopped_owner_before_recreating_session():
    pool = MCPClientPool()
    config = {"transport": "stdio", "command": "node", "args": ["server.js"]}
    config_hash = pool._calculate_config_hash(config)
    stopped_owner = MagicMock(is_running=False)
    stopped_owner.session = _SessionProxy()
    stopped_owner.stop = AsyncMock()
    replacement_session = MagicMock(is_connected=True)
    replacement_owner = MagicMock(session=replacement_session, is_running=True)
    replacement_owner.start = AsyncMock()
    replacement_owner.stop = AsyncMock()
    pool._sessions[("test_server", "p1")] = (stopped_owner, config_hash)

    with (
        patch.object(pool, "_get_mcp_client", new=AsyncMock(return_value=MagicMock())),
        patch("yuxi.agents.mcp.client_pool.LongLivedSession", return_value=replacement_owner),
    ):
        session = await pool.get_session("test_server", "p1", config)

    assert session is replacement_session
    stopped_owner.stop.assert_awaited_once()
    replacement_owner.start.assert_awaited_once()

    await pool.shutdown()


@pytest.mark.asyncio
async def test_clear_sessions_discards_connection_initializing_during_cleanup():
    pool = MCPClientPool()
    start_entered = asyncio.Event()
    release_start = asyncio.Event()
    created_sessions = []

    class FakeLongLivedSession:
        def __init__(self, client, server_name):
            del client, server_name
            self.session = MagicMock(is_connected=True)
            self.stop = AsyncMock()
            created_sessions.append(self)

        async def start(self):
            if len(created_sessions) == 1:
                start_entered.set()
                await release_start.wait()

    async def fake_get_mcp_client(server_configs):
        del server_configs
        return MagicMock()

    pool._get_mcp_client = fake_get_mcp_client
    config = {"transport": "stdio", "command": "node", "args": ["server.js"]}

    with patch("yuxi.agents.mcp.client_pool.LongLivedSession", FakeLongLivedSession):
        get_session_task = asyncio.create_task(pool.get_session("test_server", "p1", config))
        await start_entered.wait()

        await pool.clear_sessions()
        release_start.set()

        session = await get_session_task

    assert len(created_sessions) == 2
    created_sessions[0].stop.assert_awaited_once()
    assert session is created_sessions[1].session

    await pool.shutdown()


@pytest.mark.parametrize("invalid_value", ["-0.1", "nan", "inf", "-inf"])
def test_reconnect_wait_seconds_rejects_invalid_values(monkeypatch, invalid_value):
    monkeypatch.setenv("YUXI_MCP_TOOL_RECONNECT_WAIT_SECONDS", invalid_value)

    with pytest.raises(ValueError, match="finite non-negative"):
        runpy.run_path(client_pool_module.__file__, run_name=f"client_pool_invalid_{invalid_value}")


@pytest.mark.asyncio
async def test_calculate_config_hash_with_non_serializable():
    """测试配置中包含非 JSON 序列化对象时配置哈希计算不崩溃"""
    from datetime import datetime
    pool = MCPClientPool()

    class DummyObj:
        def __str__(self):
            return "dummy"

    config = {
        "transport": "sse",
        "url": "http://example.com/sse",
        "custom_obj": DummyObj(),
        "created_at": datetime(2026, 6, 5),
    }

    # 验证在含有不可 JSON 序列化的对象时依然能正常计算出哈希，不抛出异常
    config_hash = pool._calculate_config_hash(config)
    assert isinstance(config_hash, str)
    assert len(config_hash) == 16


def test_calculate_config_hash_ignores_dynamic_authorization_header():
    """直连模式下动态 Authorization 变化不应触发长连接重建"""
    pool = MCPClientPool()
    config_a = {
        "transport": "streamable_http",
        "url": "http://finance.local/mcp",
        "headers": {
            "X-App": "yuxi",
            "Authorization": "Bearer upstream-a",
        },
    }
    config_b = {
        "transport": "streamable_http",
        "url": "http://finance.local/mcp",
        "headers": {
            "X-App": "yuxi",
            "Authorization": "Bearer upstream-b",
        },
    }

    assert pool._calculate_config_hash(config_a) == pool._calculate_config_hash(config_b)


@pytest.mark.asyncio
async def test_dynamic_mcp_token_auth_cache():
    """测试 DynamicMCPTokenAuth 的 in-memory 缓存及联动清除逻辑"""
    from yuxi.agents.mcp.client_pool import (
        DynamicMCPTokenAuth,
        clear_resolved_headers_cache,
        clear_server_resolved_headers_cache,
        _resolved_headers_cache,
    )
    from yuxi.agents.mcp.mcp_auth.orchestrator import mcp_auth_context_var, AuthContext

    # 清空可能存在的全局缓存
    clear_resolved_headers_cache()

    auth = DynamicMCPTokenAuth("test_server")
    mock_req = MagicMock(headers={})

    auth_ctx = AuthContext(user_id="u1", department_id="d1")
    cache_key = ("test_server", "u1", "d1")

    # 模拟 get_runtime_mcp_server_config 返回的数据
    mock_runtime_config = {"headers": {"Authorization": "Bearer token123"}}

    token = mcp_auth_context_var.set(auth_ctx)
    try:
        with (
            patch("yuxi.storage.postgres.manager.pg_manager.get_async_session_context") as mock_session_ctx,
            patch(
                "yuxi.agents.mcp.server_service.get_runtime_mcp_server_config",
                return_value=mock_runtime_config,
            ) as mock_get_config,
        ):

            # 模拟 async with pg_manager.get_async_session_context() as session
            mock_session = MagicMock()
            mock_ctx_mgr = AsyncMock()
            mock_ctx_mgr.__aenter__.return_value = mock_session
            mock_session_ctx.return_value = mock_ctx_mgr

            # 1. 第一次请求：应该执行 DB 查询，获取最新运行时配置
            generator = auth.async_auth_flow(mock_req)
            results = [r async for r in generator]
            assert len(results) == 1
            assert results[0].headers["Authorization"] == "Bearer token123"
            assert mock_get_config.call_count == 1

            # 2. 第二次请求（+5秒）：应该命中缓存，不会执行 DB 查询
            mock_req_2 = MagicMock(headers={})
            generator_2 = auth.async_auth_flow(mock_req_2)
            results_2 = [r async for r in generator_2]
            assert len(results_2) == 1
            assert results_2[0].headers["Authorization"] == "Bearer token123"
            # call_count 依然是 1，说明命中了缓存
            assert mock_get_config.call_count == 1

            # 3. 细粒度清除缓存：清除指定 server_name
            clear_server_resolved_headers_cache("test_server")

            # 4. 第三次请求（+10秒）：清除缓存后，应该再次执行 DB 查询
            mock_req_3 = MagicMock(headers={})
            generator_3 = auth.async_auth_flow(mock_req_3)
            results_3 = [r async for r in generator_3]
            assert len(results_3) == 1
            assert mock_get_config.call_count == 2
            # 4. 测试 clear_mcp_cache / clear_mcp_server_tools_cache 联动清除所有 resolved_headers 缓存
            from yuxi.agents.mcp import clear_mcp_cache, invalidate_mcp_server_tools_cache
            # 确保当前有缓存项
            _resolved_headers_cache[cache_key] = {"Auth": "Bearer test"}
            await invalidate_mcp_server_tools_cache("test_server")
            assert len(_resolved_headers_cache) == 0

            _resolved_headers_cache[cache_key] = {"Auth": "Bearer test"}
            await clear_mcp_cache()
            assert len(_resolved_headers_cache) == 0
    finally:
        mcp_auth_context_var.reset(token)
