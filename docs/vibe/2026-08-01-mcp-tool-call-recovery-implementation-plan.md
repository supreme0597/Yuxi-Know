# MCP 工具调用断线恢复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MCP Server 重启或连接中断时，由唯一的 `LongLivedSession` 主动重建 Session，并在 Adapter interceptor 内对明确只读或幂等的工具最多安全重试一次，避免连接异常终止聊天流。

**Architecture:** `_SessionProxy` 保存稳定代理、连接状态和 generation；`LongLivedSession` 是唯一建连所有者；新增 `MCPToolCallRecoveryInterceptor` 通过 `langchain-mcp-adapters` 的公开 `tool_interceptors` 接口包围底层 `execute_tool` handler。`tool_registry_service` 只负责装配 interceptor 和一次性绑定 ToolAnnotations 策略，`RuntimeConfigMiddleware` 继续只维护动态工具与 `AuthContext` 生命周期。

**Tech Stack:** Python 3.12、asyncio、AnyIO、MCP SDK 1.27.0、langchain-mcp-adapters 0.2.2、LangChain 1.2.14、LangGraph 1.1.4、pytest、FastAPI、Docker Compose。

---

## 文件职责

- 修改 `backend/package/yuxi/agents/mcp/client_pool.py`：Session generation、主动重连事件、单一建连循环、连接池暂态复用。
- 新建 `backend/package/yuxi/agents/mcp/tool_call_recovery.py`：Adapter 调用级恢复、连接异常分类、安全 MCP 错误结果。
- 修改 `backend/package/yuxi/agents/mcp/tool_registry_service.py`：公开 interceptor 装配、ToolAnnotations 策略绑定、暂态连接异常清理边界。
- 修改 `backend/test/mcp_demo_server.py`：安全与未标注延迟工具、故障状态和真实进程重启接口。
- 扩充 `backend/test/unit/services/test_mcp_client_pool.py`：代理、Session 所有者和连接池生命周期。
- 新建 `backend/test/unit/services/test_mcp_tool_call_recovery.py`：interceptor 状态机和 Adapter 公共契约。
- 扩充 `backend/test/unit/services/test_mcp_tool_registry_service.py`：装配和连接异常处理。
- 扩充 `backend/test/unit/middlewares/test_runtime_config_middleware.py`：外层 handler 次数和 `AuthContext` 生命周期。
- 新建 `backend/test/integration/api/test_mcp_reconnect_integration.py`：真实 API、MCP SDK、Adapter、连接池和 Demo Server 重启。
- 新建 `backend/test/e2e/test_mcp_reconnect_e2e.py`：真实聊天流恢复。
- 修改 `docs/develop-guides/roadmap.md`：记录 MCP 工具调用断线恢复。

### Task 1：为 `_SessionProxy` 增加 generation 与等待契约

**Files:**

- Modify: `backend/package/yuxi/agents/mcp/client_pool.py`
- Test: `backend/test/unit/services/test_mcp_client_pool.py`

- [ ] **Step 1：先写代理状态失败测试**

在测试文件中直接导入 `_SessionProxy` 与 `ReconnectRequestStatus`，覆盖首次发布、断开不递增、新一代发布、多等待者和重连委托：

```python
@pytest.mark.asyncio
async def test_session_proxy_tracks_generation_and_wakes_waiters():
    reconnect_calls: list[int] = []
    proxy = _SessionProxy(lambda generation: reconnect_calls.append(generation) or ReconnectRequestStatus.ACCEPTED)
    first_session = MagicMock()
    second_session = MagicMock()

    assert proxy.generation == 0
    assert proxy.is_connected is False

    proxy.set_session(first_session)
    assert proxy.generation == 1
    assert await proxy.wait_for_session(timeout=0) is True

    await proxy.disconnect()
    assert proxy.generation == 1
    assert proxy.is_connected is False

    waiter_a = asyncio.create_task(proxy.wait_for_new_session(1, timeout=0.5))
    waiter_b = asyncio.create_task(proxy.wait_for_new_session(1, timeout=0.5))
    await asyncio.sleep(0)
    proxy.set_session(second_session)

    assert await waiter_a is True
    assert await waiter_b is True
    assert proxy.generation == 2
    assert proxy.request_reconnect(2) is ReconnectRequestStatus.ACCEPTED
    assert reconnect_calls == [2]


@pytest.mark.asyncio
async def test_session_proxy_wait_timeout_does_not_create_session():
    reconnect = MagicMock(return_value=ReconnectRequestStatus.ACCEPTED)
    proxy = _SessionProxy(reconnect)

    assert await proxy.wait_for_session(timeout=0.01) is False
    assert await proxy.wait_for_new_session(0, timeout=0.01) is False
    reconnect.assert_not_called()
```

- [ ] **Step 2：运行测试并确认 RED**

Run:

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_client_pool.py -k "session_proxy" -q
```

Expected: FAIL，原因是 `_SessionProxy` 尚无 callback 参数、`generation`、`wait_for_session()` 和 `wait_for_new_session()`。

- [ ] **Step 3：实现最小代理状态模型**

在 `client_pool.py` 中增加以下公开给 MCP 内部模块使用的契约：

```python
class ReconnectRequestStatus(StrEnum):
    ACCEPTED = "accepted"
    MERGED = "merged"
    STALE_GENERATION = "stale_generation"
    STOPPED = "stopped"


class _SessionProxy:
    def __init__(self, reconnect_request: Callable[[int], ReconnectRequestStatus]):
        self._session: ClientSession | None = None
        self._generation = 0
        self._connected_event = asyncio.Event()
        self._generation_event = asyncio.Event()
        self._reconnect_request = reconnect_request

    @property
    def generation(self) -> int:
        return self._generation

    def set_session(self, session: ClientSession | None) -> None:
        if session is None:
            self._session = None
            self._connected_event.clear()
            return
        self._session = session
        self._generation += 1
        self._connected_event.set()
        generation_event = self._generation_event
        self._generation_event = asyncio.Event()
        generation_event.set()

    async def wait_for_session(self, *, timeout: float) -> bool:
        if self.is_connected:
            return True
        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=timeout)
        except TimeoutError:
            return False
        return self.is_connected

    async def wait_for_new_session(self, after_generation: int, *, timeout: float) -> bool:
        deadline = asyncio.get_running_loop().time() + timeout
        while not (self.is_connected and self.generation > after_generation):
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return False
            generation_event = self._generation_event
            if self.is_connected and self.generation > after_generation:
                return True
            try:
                await asyncio.wait_for(generation_event.wait(), timeout=remaining)
            except TimeoutError:
                return False
        return True

    def request_reconnect(self, expected_generation: int) -> ReconnectRequestStatus:
        return self._reconnect_request(expected_generation)
```

调整 `disconnect()`：先保存旧 Session，再将代理置为不可用，最后关闭旧 pending streams，generation 不递增。

- [ ] **Step 4：运行代理测试并确认 GREEN**

Run:

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_client_pool.py -k "session_proxy" -q
```

Expected: PASS。

- [ ] **Step 5：提交代理契约**

```bash
git add backend/package/yuxi/agents/mcp/client_pool.py backend/test/unit/services/test_mcp_client_pool.py
git commit -m "feat(mcp): 增加 Session 代次等待契约"
```

### Task 2：修复 `LongLivedSession` 连续重连并增加主动唤醒

**Files:**

- Modify: `backend/package/yuxi/agents/mcp/client_pool.py`
- Test: `backend/test/unit/services/test_mcp_client_pool.py`

- [ ] **Step 1：写连续失败与主动重连失败测试**

使用以下顺序化 AsyncContextManager：第一次连接成功、第二和第三次进入失败、第四次成功。断言同一代理最终 generation 从 1 变为 2，后台循环未在第二次连接失败后退出：

```python
class _SequencedSessionContext:
    def __init__(self, client):
        self._client = client

    async def __aenter__(self):
        self._client.enter_count += 1
        item = self._client.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _SequencedSessionClient:
    def __init__(self, items):
        self.items = list(items)
        self.enter_count = 0

    def session(self, server_name):
        assert server_name == "demo"
        return _SequencedSessionContext(self)


def test_request_reconnect_merges_same_generation_and_rejects_stale_generation():
    owner = LongLivedSession(MagicMock(), "demo")
    owner._running = True
    owner._session_proxy.set_session(MagicMock())

    assert owner.request_reconnect(1) is ReconnectRequestStatus.ACCEPTED
    assert owner.request_reconnect(1) is ReconnectRequestStatus.MERGED

    owner._session_proxy.set_session(MagicMock())
    assert owner.request_reconnect(1) is ReconnectRequestStatus.STALE_GENERATION

    owner._running = False
    assert owner.request_reconnect(2) is ReconnectRequestStatus.STOPPED


@pytest.mark.asyncio
async def test_long_lived_session_keeps_retrying_after_reconnect_failures(monkeypatch):
    sessions = [MagicMock(name="session-1"), RuntimeError("retry-1"), RuntimeError("retry-2"), MagicMock(name="session-2")]
    client = _SequencedSessionClient(sessions)
    owner = LongLivedSession(client, "demo")
    monkeypatch.setattr(owner, "_wait_reconnect_backoff_or_stop", AsyncMock(return_value=False))

    await owner.start()
    assert owner.session.generation == 1
    assert owner.request_reconnect(1) is ReconnectRequestStatus.ACCEPTED
    assert await owner.session.wait_for_new_session(1, timeout=0.5) is True
    assert owner.session.generation == 2
    assert client.enter_count == 4

    await owner.stop()
```

`_SequencedSessionClient` 的 context manager 在元素为异常时从 `__aenter__()` 抛出；成功时保持上下文，直到 owner 请求重连或 stop。

- [ ] **Step 2：运行测试并确认 RED**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_client_pool.py -k "request_reconnect or keeps_retrying" -q
```

Expected: FAIL，当前实现没有主动重连状态，并会把首次重连失败误判为首次连接失败。

- [ ] **Step 3：实现单一所有者重连状态机**

在 `LongLivedSession.__init__()` 中使用绑定方法创建代理，并增加 `_reconnect_event` 与 `_reconnect_generation`：

```python
self._reconnect_event = asyncio.Event()
self._reconnect_generation: int | None = None
self._session_proxy = _SessionProxy(self.request_reconnect)
```

实现同步、无 await 的请求合并：

```python
def request_reconnect(self, expected_generation: int) -> ReconnectRequestStatus:
    if not self._running or self._stop_event.is_set():
        return ReconnectRequestStatus.STOPPED
    if self._session_proxy.generation != expected_generation:
        return ReconnectRequestStatus.STALE_GENERATION
    if self._reconnect_generation == expected_generation:
        return ReconnectRequestStatus.MERGED
    self._reconnect_generation = expected_generation
    self._reconnect_event.set()
    return ReconnectRequestStatus.ACCEPTED
```

把 keepalive 改为同时等待 stop、reconnect 和 ping timeout；主动 reconnect 返回后由 `_run_loop()` 断开代理并退出当前 Session 上下文。`_run_loop()` 使用 `first_connect` 而不是 `is_connected` 判断初次失败：

```python
while not self._stop_event.is_set():
    try:
        async with self.client.session(self.server_name) as session:
            self._session_proxy.set_session(session)
            self._reconnect_generation = None
            self._reconnect_event.clear()
            self._ready_event.set()
            first_connect = False
            reconnect_delay = self._RECONNECT_INITIAL_DELAY
            exit_reason = await self._keep_alive_until_exit(session)
            if exit_reason == "stop":
                break
            self._reconnect_generation = self._session_proxy.generation
            await self._session_proxy.disconnect()
    except asyncio.CancelledError:
        raise
    except BaseException as exc:
        if self._stop_event.is_set():
            break
        failed_generation = self._session_proxy.generation
        await self._session_proxy.disconnect()
        if first_connect:
            self._ready_event.set()
            break
        self._reconnect_generation = failed_generation
        sub_exc = exc.exceptions[0] if isinstance(exc, BaseExceptionGroup) and exc.exceptions else exc
        if _is_auth_error(sub_exc):
            await _mark_mcp_connection_reauth_required(self.server_name)

    stopped = await self._wait_reconnect_backoff_or_stop(reconnect_delay)
    if stopped:
        break
    reconnect_delay = min(reconnect_delay * 2, self._RECONNECT_MAX_DELAY)
```

保留现有 1 秒起始、30 秒最大退避；stop 必须可以中断 keepalive 与退避。

- [ ] **Step 4：运行 LongLivedSession 测试并确认 GREEN**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_client_pool.py -k "long_lived_session or request_reconnect" -q
```

Expected: PASS，且无 pending task warning。

- [ ] **Step 5：提交所有者状态机**

```bash
git add backend/package/yuxi/agents/mcp/client_pool.py backend/test/unit/services/test_mcp_client_pool.py
git commit -m "fix(mcp): 保持长连接连续重连"
```

### Task 3：连接池保留正在恢复的原代理

**Files:**

- Modify: `backend/package/yuxi/agents/mcp/client_pool.py`
- Test: `backend/test/unit/services/test_mcp_client_pool.py`

- [ ] **Step 1：写暂态连接复用与锁外等待测试**

```python
@pytest.mark.asyncio
async def test_pool_waits_for_recovering_session_without_replacing_owner(monkeypatch):
    pool = MCPClientPool()
    config = {"transport": "stdio", "command": "demo"}
    proxy = MagicMock(is_connected=False)
    proxy.wait_for_session = AsyncMock(return_value=True)
    owner = MagicMock(session=proxy, is_running=True)
    pool._sessions[("demo", "server:s1:p0")] = (owner, pool._calculate_config_hash(config))

    async def mark_connected(*, timeout):
        assert timeout == MCP_TOOL_RECONNECT_WAIT_SECONDS
        proxy.is_connected = True
        return True

    proxy.wait_for_session.side_effect = mark_connected
    result = await pool.get_session("demo", "server:s1:p0", config)

    assert result is proxy
    owner.stop.assert_not_called()


@pytest.mark.asyncio
async def test_pool_recovery_timeout_keeps_original_entry():
    pool = MCPClientPool()
    config = {"transport": "stdio", "command": "demo"}
    proxy = MagicMock(is_connected=False)
    proxy.wait_for_session = AsyncMock(return_value=False)
    owner = MagicMock(session=proxy, is_running=True)
    key = ("demo", "server:s1:p0")
    pool._sessions[key] = (owner, pool._calculate_config_hash(config))

    with pytest.raises(MCPConnectionRecoveringError):
        await pool.get_session(*key, config)

    assert pool._sessions[key][0] is owner
    owner.stop.assert_not_called()
```

- [ ] **Step 2：运行测试并确认 RED**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_client_pool.py -k "pool_waits_for_recovering or pool_recovery_timeout" -q
```

Expected: FAIL，当前连接池会淘汰 `is_connected=False` 的 owner。

- [ ] **Step 3：实现恢复中条目的锁外等待**

新增：

```python
class MCPConnectionRecoveringError(RuntimeError):
    pass


MCP_TOOL_RECONNECT_WAIT_SECONDS = float(os.getenv("YUXI_MCP_TOOL_RECONNECT_WAIT_SECONDS", "5"))
```

在 `get_session()` 的同配置分支中：owner 仍运行且代理未连接时，在 `_dict_lock` 内只保存 `recovering_proxy`，随后释放锁并等待。等待成功后重新进入 while 校验池条目；超时抛出 `MCPConnectionRecoveringError`，不 pop、不 stop。配置 hash 改变或 owner 已停止时才保持现有淘汰逻辑。

- [ ] **Step 4：运行连接池测试并确认 GREEN**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_client_pool.py -q
```

Expected: PASS。

- [ ] **Step 5：提交连接池暂态复用**

```bash
git add backend/package/yuxi/agents/mcp/client_pool.py backend/test/unit/services/test_mcp_client_pool.py
git commit -m "fix(mcp): 保留重连中的连接池代理"
```

### Task 4：实现 MCP Adapter 调用恢复 interceptor

**Files:**

- Create: `backend/package/yuxi/agents/mcp/tool_call_recovery.py`
- Create: `backend/test/unit/services/test_mcp_tool_call_recovery.py`

- [ ] **Step 1：写 interceptor 失败测试**

测试文件先提供以下 `_FakeProxy` 与请求构造器，再使用参数化覆盖三类 AnyIO 连接异常：

```python
class _FakeProxy:
    def __init__(
        self,
        *,
        generation: int,
        connected: bool,
        reconnect_status: ReconnectRequestStatus = ReconnectRequestStatus.ACCEPTED,
        wait_result: bool = True,
    ):
        self.generation = generation
        self.is_connected = connected
        self.reconnect_status = reconnect_status
        self.wait_result = wait_result
        self.reconnect_requests: list[int] = []
        self.waited_generations: list[int] = []

    def request_reconnect(self, expected_generation: int) -> ReconnectRequestStatus:
        self.reconnect_requests.append(expected_generation)
        return self.reconnect_status

    async def wait_for_new_session(self, after_generation: int, *, timeout: float) -> bool:
        assert timeout >= 0
        self.waited_generations.append(after_generation)
        if self.wait_result:
            self.generation = after_generation + 1
            self.is_connected = True
        return self.wait_result


def _request(name: str) -> MCPToolCallRequest:
    return MCPToolCallRequest(
        name=name,
        args={"message": "secret-value-not-for-logs"},
        server_name="demo",
        headers={"Authorization": "Bearer secret-token"},
    )


@pytest.mark.parametrize("connection_error", [EndOfStream(), ClosedResourceError(), BrokenResourceError()])
@pytest.mark.asyncio
async def test_retryable_tool_waits_for_new_generation_and_retries_once(connection_error):
    proxy = _FakeProxy(generation=1, connected=True)
    interceptor = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=0.1)
    interceptor.bind_retryable_tools(frozenset({"safe_echo"}))
    handler = AsyncMock(side_effect=[connection_error, CallToolResult(content=[TextContent(type="text", text="ok")])])

    result = await interceptor(_request("safe_echo"), handler)

    assert result.isError is False
    assert handler.await_count == 2
    assert proxy.reconnect_requests == [1]
    assert proxy.waited_generations == [1]


@pytest.mark.asyncio
async def test_unannotated_tool_repairs_connection_without_replaying_request():
    proxy = _FakeProxy(generation=3, connected=True)
    interceptor = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=0.1)
    interceptor.bind_retryable_tools(frozenset())
    handler = AsyncMock(side_effect=ClosedResourceError())

    result = await interceptor(_request("write_once"), handler)

    assert result.isError is True
    assert "未自动重试" in result.content[0].text
    assert "执行结果可能已经生效" in result.content[0].text
    assert handler.await_count == 1
    assert proxy.reconnect_requests == [3]


@pytest.mark.asyncio
async def test_second_connection_failure_never_causes_third_handler_call():
    proxy = _FakeProxy(generation=5, connected=True)
    interceptor = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=0.1)
    interceptor.bind_retryable_tools(frozenset({"safe_echo"}))
    handler = AsyncMock(side_effect=[EndOfStream(), BrokenResourceError()])

    result = await interceptor(_request("safe_echo"), handler)

    assert result.isError is True
    assert handler.await_count == 2
    assert proxy.reconnect_requests == [5, 6]
```

补充以下明确断言：

```python
@pytest.mark.asyncio
async def test_policy_must_be_bound_once_before_handler_runs():
    interceptor = MCPToolCallRecoveryInterceptor(
        session_proxy=_FakeProxy(generation=1, connected=True),
        reconnect_wait_seconds=0.1,
    )
    handler = AsyncMock()

    with pytest.raises(RuntimeError, match="not bound"):
        await interceptor(_request("safe_echo"), handler)
    handler.assert_not_awaited()

    interceptor.bind_retryable_tools(frozenset({"safe_echo"}))
    with pytest.raises(RuntimeError, match="already bound"):
        interceptor.bind_retryable_tools(frozenset())


@pytest.mark.asyncio
async def test_pre_call_disconnect_timeout_never_sends_request():
    proxy = _FakeProxy(generation=2, connected=False, wait_result=False)
    interceptor = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=0.01)
    interceptor.bind_retryable_tools(frozenset({"safe_echo"}))
    handler = AsyncMock()

    result = await interceptor(_request("safe_echo"), handler)

    assert result.isError is True
    assert "请求尚未发送" in result.content[0].text
    handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_timeout_returns_tool_error_without_reconnect():
    proxy = _FakeProxy(generation=4, connected=True)
    interceptor = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=0.1)
    interceptor.bind_retryable_tools(frozenset({"safe_echo"}))

    result = await interceptor(_request("safe_echo"), AsyncMock(side_effect=TimeoutError()))

    assert result.isError is True
    assert "执行结果未知" in result.content[0].text
    assert proxy.reconnect_requests == []


@pytest.mark.asyncio
async def test_mixed_exception_group_and_cancellation_propagate():
    proxy = _FakeProxy(generation=1, connected=True)
    interceptor = MCPToolCallRecoveryInterceptor(session_proxy=proxy, reconnect_wait_seconds=0.1)
    interceptor.bind_retryable_tools(frozenset({"safe_echo"}))
    mixed = ExceptionGroup("mixed", [ClosedResourceError(), ValueError("bug")])

    with pytest.raises(ExceptionGroup):
        await interceptor(_request("safe_echo"), AsyncMock(side_effect=mixed))
    with pytest.raises(asyncio.CancelledError):
        await interceptor(_request("safe_echo"), AsyncMock(side_effect=asyncio.CancelledError()))
```

- [ ] **Step 2：运行测试并确认 RED**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_tool_call_recovery.py -q
```

Expected: ERROR/FAIL，模块尚不存在。

- [ ] **Step 3：实现最小 interceptor**

模块只导出 `MCPToolCallRecoveryInterceptor` 和 `is_mcp_connection_error()`。连接异常集合固定为 AnyIO 三类流异常、HTTPX `ConnectError`/`ReadError`/`RemoteProtocolError`、`ConnectionResetError` 和 `BrokenPipeError`。错误结果统一由以下构造器生成：

```python
def _error_result(message: str) -> CallToolResult:
    return CallToolResult(
        isError=True,
        content=[TextContent(type="text", text=message)],
    )
```

`__call__()` 的线性顺序固定为：

1. 策略未绑定立即抛 `RuntimeError`。
2. 调用前未连接时请求重连并在统一 deadline 内等待；handler 只在连接可用后执行。
3. 第一次 handler 捕获 `TimeoutError` 时直接返回结果未知，不请求重连。
4. 非连接异常继续抛出。
5. 连接异常先 `request_reconnect(call_generation)`。
6. 未标注工具返回执行结果未知，不等待、不重放。
7. 安全工具等待新 generation，最多第二次调用同一 handler。
8. 第二次连接异常请求后台恢复后返回错误，不进行第三次调用。

日志只写 server、tool、generation、异常类型、重连状态和是否重试，不写 `request.args`、`request.headers` 或 Token。

- [ ] **Step 4：运行 interceptor 测试并确认 GREEN**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_tool_call_recovery.py -q
```

Expected: PASS。

- [ ] **Step 5：提交 interceptor**

```bash
git add backend/package/yuxi/agents/mcp/tool_call_recovery.py backend/test/unit/services/test_mcp_tool_call_recovery.py
git commit -m "feat(mcp): 增加工具调用恢复拦截器"
```

### Task 5：通过 Adapter 公共接口完成工具装配

**Files:**

- Modify: `backend/package/yuxi/agents/mcp/tool_registry_service.py`
- Modify: `backend/test/unit/services/test_mcp_tool_registry_service.py`
- Modify: `backend/test/unit/middlewares/test_runtime_config_middleware.py`

- [ ] **Step 1：写公开装配和 `AuthContext` 失败测试**

在 registry 测试中 monkeypatch `langchain_mcp_adapters.tools.load_mcp_tools`，捕获传入的原代理和 interceptor；返回带 metadata 的三个 Tool：只读、幂等、未标注。断言 `bind_retryable_tools()` 在函数返回前收到前两个原始工具名，并保留 `id`、`mcp_server_name`、`handle_tool_error=True`。

再使用真实 Adapter 公共路径创建 FakeSession：`list_tools()` 返回 `readOnlyHint=True` 工具，`call_tool()` 返回 `CallToolResult(isError=True)`；断言 interceptor 被调用一次且最终结果为状态 `error` 的 ToolMessage。

Middleware 测试的 handler 内执行两次模拟 Adapter handler，同时读取 `mcp_auth_context_var`：

```python
@pytest.mark.asyncio
async def test_awrap_tool_call_keeps_auth_context_across_adapter_retry():
    middleware = RuntimeConfigMiddleware()
    observed_user_ids: list[str] = []

    async def adapter_handler():
        observed_user_ids.append(mcp_auth_context_var.get().user_id)

    async def agent_handler(next_request):
        await adapter_handler()
        await adapter_handler()
        return ToolMessage(content="ok", tool_call_id=next_request.tool_call["id"])

    context = SimpleNamespace(user_id="2", work_id="test-common", department_id="1")
    request = ToolCallRequest(
        tool_call={"name": "safe_echo", "args": {}, "id": "call-1"},
        tool=SimpleNamespace(name="safe_echo"),
        state={},
        runtime=SimpleNamespace(context=context),
    )
    result = await middleware.awrap_tool_call(request, agent_handler)

    assert result.content == "ok"
    assert observed_user_ids == ["2", "2"]
    assert mcp_auth_context_var.get() is None
```

- [ ] **Step 2：运行测试并确认 RED**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_tool_registry_service.py test/unit/middlewares/test_runtime_config_middleware.py -k "interceptor or adapter_retry" -q
```

Expected: FAIL，registry 尚未传入 interceptor。

- [ ] **Step 3：实现 `tool_registry_service` 装配**

真实 Adapter 分支使用：

```python
recovery = MCPToolCallRecoveryInterceptor(
    session_proxy=session,
    reconnect_wait_seconds=MCP_TOOL_RECONNECT_WAIT_SECONDS,
)
raw_tools = cast(
    list[Any],
    await load_mcp_tools(
        session,
        server_name=server_name,
        tool_interceptors=[recovery],
    ),
)
retryable_tool_names = frozenset(
    tool.name
    for tool in raw_tools
    if tool.metadata
    and (
        tool.metadata.get("readOnlyHint") is True
        or tool.metadata.get("idempotentHint") is True
    )
)
recovery.bind_retryable_tools(retryable_tool_names)
```

Fake Client 的 `get_tools()` 测试分支不创建 interceptor。`MCPConnectionRecoveringError` 直接返回空列表且不进冷却、不移除 Session；`list_tools` 的连接异常调用原代理 `request_reconnect()`，只有 `STOPPED` 才移除连接池条目。普通配置、鉴权和程序错误保留现有冷却与清理。

`RuntimeConfigMiddleware.awrap_tool_call()` 生产代码不变，只增加回归测试。

- [ ] **Step 4：运行装配测试并确认 GREEN**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_tool_registry_service.py test/unit/middlewares/test_runtime_config_middleware.py -q
```

Expected: PASS。

- [ ] **Step 5：提交 Adapter 装配**

```bash
git add backend/package/yuxi/agents/mcp/tool_registry_service.py backend/test/unit/services/test_mcp_tool_registry_service.py backend/test/unit/middlewares/test_runtime_config_middleware.py
git commit -m "feat(mcp): 接入 Adapter 工具恢复拦截器"
```

### Task 6：让 Demo Server 可稳定复现真实断线

**Files:**

- Modify: `backend/test/mcp_demo_server.py`
- Create: `backend/test/integration/api/test_mcp_reconnect_integration.py`

- [ ] **Step 1：先写 Demo 工具与重启集成测试**

测试通过真实 MCP CRUD API 创建指向 `http://mcp-demo-server:8999/sse` 的 `legacy_static` Server；调用 `get_enabled_mcp_tools()` 找到 `echo_delayed_safe` 和 `echo_delayed_unannotated`。安全工具任务开始后轮询 `http://mcp-demo-server:8999/test/faults/state`，再 POST `/test/faults/restart`。

安全场景断言：工具任务没有抛连接异常、最终返回重连后的结果、同一 `_SessionProxy` generation 增加、后续 `echo_global` 成功。未标注场景断言：返回 Tool 错误、内容包含“未自动重试”和“执行结果可能已经生效”、后续调用恢复。

所有 API 创建数据在 `finally` 中删除连接和 MCP Server；故障接口只访问 Demo Server，不操作生产 API。

- [ ] **Step 2：运行测试并确认 RED**

```bash
docker exec api-dev uv run --group test pytest test/integration/api/test_mcp_reconnect_integration.py -q
```

Expected: FAIL，Demo Server 尚无延迟工具和故障接口。

- [ ] **Step 3：实现 Demo Server 故障能力**

给三个现有 echo 工具添加：

```python
annotations=types.ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
)
```

新增两个工具。`echo_delayed_safe` 带同样 annotations，`echo_delayed_unannotated` 不设置 annotations。执行时用模块级 `active_tool_calls: dict[str, int]` 记录工具名和数量，`finally` 中递减，不保存参数。

新增接口：

```python
@app.get("/test/faults/state")
async def get_fault_state():
    return {"active_tools": dict(active_tool_calls)}


@app.post("/test/faults/restart")
async def restart_demo_server():
    async def terminate_after_response() -> None:
        await asyncio.sleep(0.1)
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(terminate_after_response())
    return {"restarting": True}
```

- [ ] **Step 4：运行真实集成测试并确认 GREEN**

```bash
docker exec api-dev uv run --group test pytest test/integration/api/test_mcp_reconnect_integration.py -q
```

Expected: PASS，过程中 `mcp-demo-server` 会由 Compose 的 `restart: unless-stopped` 自动拉起。

- [ ] **Step 5：提交 Demo 与集成测试**

```bash
git add backend/test/mcp_demo_server.py backend/test/integration/api/test_mcp_reconnect_integration.py
git commit -m "test(mcp): 覆盖真实服务重启恢复"
```

### Task 7：补齐聊天 E2E、回归和文档

**Files:**

- Create: `backend/test/e2e/test_mcp_reconnect_e2e.py`
- Modify: `docs/develop-guides/roadmap.md`

- [ ] **Step 1：写聊天流 E2E**

使用 `e2e_client`、`e2e_headers` 创建专用 MCP Server、Agent Config 和 Thread。Agent Config 只启用目标 MCP，system prompt 要求必须调用指定工具；未标注场景还要求工具错误后不要由模型再次调用。

通过 `client.stream("POST", "/api/chat/agent", ...)` 发起聊天；轮询 Demo fault state 后重启 Server。安全场景断言 SSE 行不含 `Error streaming messages` 且最终 Assistant 正常完成；未标注场景断言聊天继续并包含底层 Tool 错误语义。每个场景最后再发一次普通工具请求验证后续可用。

- [ ] **Step 2：运行 E2E 并确认 RED/GREEN**

首次运行在 E2E 文件创建后、生产修复完整前必须能复现 streaming 失败；完成 Task 1-6 后重新运行：

```bash
docker exec api-dev uv run --group test pytest test/e2e/test_mcp_reconnect_e2e.py -m e2e -q
```

Expected: 2 个场景 PASS；若测试账号未配置，只允许按现有 fixture 明确 skip。

- [ ] **Step 3：更新 roadmap**

在 MCP 相关条目下记录：长连接主动重连、generation 等待、Adapter interceptor 安全重试、未标注工具保守失败，以及真实重启集成/E2E 覆盖。不新增用户配置项或数据库迁移说明。

- [ ] **Step 4：运行完整目标验证**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_mcp_client_pool.py test/unit/services/test_mcp_tool_call_recovery.py test/unit/services/test_mcp_tool_registry_service.py test/unit/middlewares/test_runtime_config_middleware.py -q
```

```bash
docker exec api-dev uv run --group test pytest test/integration/api/test_mcp_reconnect_integration.py -q
```

```bash
docker exec api-dev uv run --group test pytest test/e2e/test_mcp_reconnect_e2e.py -m e2e -q
```

```bash
docker exec api-dev uv run --group dev ruff check package/yuxi/agents/mcp/client_pool.py package/yuxi/agents/mcp/tool_call_recovery.py package/yuxi/agents/mcp/tool_registry_service.py test/mcp_demo_server.py test/unit/services/test_mcp_client_pool.py test/unit/services/test_mcp_tool_call_recovery.py test/unit/services/test_mcp_tool_registry_service.py test/unit/middlewares/test_runtime_config_middleware.py test/integration/api/test_mcp_reconnect_integration.py test/e2e/test_mcp_reconnect_e2e.py
```

Expected: 目标单元、集成、E2E 和 Ruff 全部通过。

- [ ] **Step 5：手工回归现有场景**

确认 `manual_mcp_13_token_pre_refresh` 仍按 15 秒 Token 与配置的提前刷新秒数运行；401 只走 `DynamicMCPTokenAuth` 的原有清缓存重试；普通 SSE、Streamable HTTP 和 `manual_mcp_03_stdio_public` 工具正常调用。

- [ ] **Step 6：提交收尾**

```bash
git add backend/test/e2e/test_mcp_reconnect_e2e.py docs/develop-guides/roadmap.md
git commit -m "test(mcp): 补充断线恢复聊天回归"
```

最后运行 `git status --short`，确认未把已有的 `backend/package/uv.lock` 和根目录 patch 文件纳入提交。
