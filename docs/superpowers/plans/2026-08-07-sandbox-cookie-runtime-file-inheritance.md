# Sandbox Cookie Runtime File Inheritance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将浏览器发给 Yuxi 的原始 `Cookie` Header 作为短生命周期的 run 凭据写入沙盒临时文件，动态注入同源使用说明，并让 subagent 继承父 run 凭据，同时支持 resume 更新、沙盒复用、超时删除和重建后重新注入。

**Architecture:** API 从当前 Yuxi 请求读取原始 `Cookie` Header；生产环境使用服务端配置的 `YUXI_PUBLIC_ORIGIN`，开发环境未配置时才从 `request.base_url` 规范化 origin。Header 与 origin 以 Redis Hash 按 `run_id` 保存到独立的无持久化 `runtime-secret-redis`，ARQ 消息只携带 `run_id`。Worker 为 chat、resume、subagent 建立统一的 run 级 `ContextVar`；系统提示词中仅注入允许 origin、文件路径和安全规则，不注入 Header 内容；沙盒第一次被实际访问时，backend 才把原始 Header 写入 `/home/gem/.yuxi-runtime/browser-cookie-header.txt`。Provisioner 返回每个真实容器或 Pod 的 `instance_id`，使同一逻辑 sandbox 被删除重建后能够重新同步文件。

**Tech Stack:** Python 3.12+、FastAPI、ARQ、Redis asyncio client、ContextVar、agent-sandbox file/shell API、Docker/Kubernetes provisioner、pytest、ruff。

## Current Worktree Status (2026-08-08)

- 原始 Header 文件方案、main/subagent 动态提示词、run secret 生命周期、实例重建识别、独立无持久化 Redis、生产 canonical origin 及配套文档已在当前工作区实现，尚未提交。
- 聚焦 unit：`192 passed`；真实 provisioner 集成：`1 passed`，已覆盖原始 Header、`0700/0600`、删除重建后的重新注入、run 结束清理和无 Cookie run 清理旧文件。
- 全部本次变更 Python 文件的 `ruff check`、开发/生产 Compose 配置解析、凭据泄露静态搜索与 `git diff --check` 通过。
- 全量 unit：`903 passed, 2 skipped, 1 failed`；唯一失败是未改动的 remote-skill 测试在 macOS 上比较 `/private/var/...` 与 `/var/...` 路径别名。
- OrbStack 在 provisioner 动态解绑沙盒专属网络时会打断“宿主机直连 provisioner 容器”的当前 HTTP 连接；Compose 内网客户端的 DELETE 在 `7.033s` 返回 `200`，随后健康检查正常。宿主机 `uv` 集成测试通过独立 Nginx 测试代理进入 Compose 内网执行，避免把本机端口转发行为误判为产品故障。
- 当前实现和设计尚未提交；`Makefile` 等用户已有无关改动不属于本需求。

## Global Constraints

- 原始 Cookie Header 不得进入 Postgres、AgentRun `input_payload`/meta、LangGraph state/configurable、ARQ 参数/结果、系统提示词、共享持久化 Redis 或持久化 workspace/uploads/outputs。
- ARQ 的 `process_agent_run` 任务参数固定为 `(ctx, run_id: str)`；Header 和 origin 只能通过 Redis run secret 读取。
- 原始 Cookie Header 按 HTTP header 的 Latin-1 字节表示计算，最大 32 KiB；空值或超限值视为无 Cookie，日志只记录字节数。
- Redis secret 只能使用 `AGENT_RUN_RUNTIME_SECRET_REDIS_URL` 指向的独立 volatile Redis；必须关闭 AOF/RDB、不得挂载磁盘卷。默认 TTL 为 14,400 秒，可用 `AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS` 调整。
- Resume 使用本次 HTTP 请求的最新 Header/origin；subagent 复制当前父 run 的完整运行期凭据。
- Header 文件固定为 `/home/gem/.yuxi-runtime/browser-cookie-header.txt`，内容是浏览器发给 Yuxi 的原始 `Cookie` Header，不是 JSON；目录权限 `0700`，文件权限 `0600`。
- `/home/gem/.yuxi-runtime` 位于 Docker `tmpfs` 或 Kubernetes `emptyDir`，不得改到持久化挂载目录。
- 不在 run 启动时创建沙盒；只在 `ProvisionerSandboxBackend._get_client()` 第一次实际取用沙盒时同步文件。
- Provisioner 使用 `runtime-contract-version=cookie-header-file-v1` 标记新实例；升级前创建且缺少该契约的旧实例在首次重新获取时重建一次。
- 无 run runtime context 的 viewer/API 访问不得修改 Header 文件；有 context 且 `browser_cookie is None` 时必须删除旧文件。
- Header 内容不得拼入系统提示词、shell 命令、日志或异常；内容只通过 Redis Hash 和 sandbox file API 传输。
- 历史变量名 `SANDBOX_COOKIES_JSON` 只能作为兼容清理名单出现：创建沙盒前从用户 `agent_env` 中移除，生产代码不得读取或转发其值。
- 系统提示词仅在当前 run 有 Cookie 凭据时动态注入，main agent 与 subagent 使用同一规则；提示中必须包含规范化 Yuxi origin、`SANDBOX_COOKIE_HEADER_FILE` 和禁止泄露/跨 origin 转发的约束。
- 自动重定向不得把 Cookie 带到不同的 `scheme + host + port`；子域名、主机别名和 IP 均不视为同 origin。
- 生产环境必须用服务端 `YUXI_PUBLIC_ORIGIN` 指定浏览器可见的规范 origin；开发环境未配置时才回退 `request.base_url`。不读取用户消息，也不把未经校验的 `Origin` Header 当作授权目标。
- 原始 Header 文件使 Agent 技术上能够读取凭据，因此系统提示属于模型执行约束，不等价于网络层强制隔离；需要硬隔离时应另行设计同源认证代理。
- 每个任务遵循 RED 测试、最小实现、GREEN 测试、中文 Conventional Commit 的顺序。

## File Map

- Create `backend/package/yuxi/services/run_runtime_secret_service.py`: `BrowserCookieRuntimeSecret`、专用 volatile Redis client、Hash key/TTL、存取和删除。
- Create `backend/package/yuxi/agents/backends/sandbox/runtime_context.py`: run 级凭据 ContextVar 和清理回调。
- Modify `backend/server/routers/agent_router.py`, `backend/server/routers/agent_invocation_router.py`, `backend/package/yuxi/services/agent_invocation_service.py`, `backend/package/yuxi/services/agent_run_service.py`: 捕获原始 Header/origin、字节上限和仅含 `run_id` 的 ARQ 投递。
- Modify `backend/package/yuxi/services/run_worker.py`: 所有 run 类型激活 context，终态删除 secret，重试保留。
- Modify `backend/package/yuxi/services/subagent_run_service.py`: 子 run 继承父 run Cookie。
- Modify `docker/sandbox_provisioner/app.py`: 返回 memory/Docker/Kubernetes 的真实 `instance_id`。
- Create `backend/package/yuxi/agents/middlewares/sandbox_cookie.py`: 动态注入同源 Cookie Header 使用规则。
- Modify main/subagent graph 和 middleware exports: 两类 Agent 都安装动态提示中间件。
- Modify `backend/package/yuxi/agents/backends/sandbox/{provisioner_client,provider,backend}.py`: 实例标识、固定 Header 文件指针和懒同步。
- Add/update unit and integration tests under `backend/test/unit` and `backend/test/integration`.
- Modify `docker-compose.yml`, `docker-compose.prod.yml`: 新增关闭 AOF/RDB、使用 tmpfs 且无磁盘卷的 `runtime-secret-redis`。
- Modify `.env.template`, `docs/agents/sandbox-architecture.md`, `docs/develop-guides/changelog.md`.

---

### Task 1: Redis Run Secret Service

**Files:**
- Create: `backend/package/yuxi/services/run_runtime_secret_service.py`
- Create: `backend/test/unit/services/test_run_runtime_secret_service.py`

**Interfaces:**
- Consumes: `yuxi.storage.redis.RedisConfig` and `create_async_redis_client()`，但使用独立 client cache，不复用共享 `get_async_redis_client()`。
- Produces: `BrowserCookieRuntimeSecret(header: str, origin: str)`.
- Produces: `store_run_browser_cookie_secret(run_id: str, secret: BrowserCookieRuntimeSecret | None) -> None`.
- Produces: `load_run_browser_cookie_secret(run_id: str) -> BrowserCookieRuntimeSecret | None`.
- Produces: `delete_run_browser_cookie_secret(run_id: str) -> None`.

- [ ] **Step 1: Write failing secret lifecycle tests**

Use this local fake Redis and cover `hset` preserving the raw Header string, separate `header`/`origin` fields, an expiry of 14,400 seconds, `None` deleting stale data, missing/incomplete hash returning `None`, explicit delete, and key `agent-run:runtime-secret:{run_id}`. Also prove operations use the dedicated client, both Compose files define a no-AOF/no-RDB tmpfs Redis without a volume, and the configured URL comes from `AGENT_RUN_RUNTIME_SECRET_REDIS_URL`.

```python
class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def hset(self, key, *, mapping):
        self.commands.append(("hset", key, dict(mapping)))
        return self

    def expire(self, key, seconds):
        self.commands.append(("expire", key, seconds))
        return self

    async def execute(self):
        self.redis.pipeline_calls.append(tuple(self.commands))


class FakeRedis:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.pipeline_calls = []
        self.delete_calls = []

    def pipeline(self, *, transaction):
        assert transaction is True
        return FakePipeline(self)

    async def hgetall(self, key):
        return dict(self.values.get(key) or {})

    async def delete(self, key):
        self.values.pop(key, None)
        self.delete_calls.append(key)


@pytest.mark.asyncio
async def test_store_run_browser_cookie_secret_preserves_raw_header(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", AsyncMock(return_value=redis))
    secret = service.BrowserCookieRuntimeSecret(
        header="sid=abc; theme=dark",
        origin="https://yuxi.example.com",
    )
    await service.store_run_browser_cookie_secret("run-1", secret)
    assert redis.pipeline_calls == [(
        (
            "hset",
            "agent-run:runtime-secret:run-1",
            {"header": "sid=abc; theme=dark", "origin": "https://yuxi.example.com"},
        ),
        ("expire", "agent-run:runtime-secret:run-1", 14_400),
    )]


@pytest.mark.asyncio
async def test_store_none_deletes_stale_secret(monkeypatch):
    redis = FakeRedis(values={"agent-run:runtime-secret:run-1": {"header": "stale", "origin": "https://old"}})
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", AsyncMock(return_value=redis))
    await service.store_run_browser_cookie_secret("run-1", None)
    assert redis.delete_calls == ["agent-run:runtime-secret:run-1"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [{}, {"header": "sid=abc"}, {"origin": "https://yuxi.example.com"}])
async def test_load_incomplete_secret_returns_none(monkeypatch, stored):
    redis = FakeRedis(values={"agent-run:runtime-secret:run-1": stored})
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", AsyncMock(return_value=redis))
    assert await service.load_run_browser_cookie_secret("run-1") is None
```

- [ ] **Step 2: Run RED test**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_run_runtime_secret_service.py -q
```

Expected: import fails because the service and dataclass do not exist.

- [ ] **Step 3: Implement the minimal service**

```python
@dataclass(frozen=True, slots=True)
class BrowserCookieRuntimeSecret:
    header: str
    origin: str


RUN_RUNTIME_SECRET_KEY_PREFIX = "agent-run:runtime-secret:"
DEFAULT_RUN_RUNTIME_SECRET_TTL_SECONDS = 14_400
DEFAULT_RUN_RUNTIME_SECRET_REDIS_URL = "redis://runtime-secret-redis:6379/0"


def _secret_key(run_id: str) -> str:
    return f"{RUN_RUNTIME_SECRET_KEY_PREFIX}{run_id}"


def _secret_ttl_seconds() -> int:
    return int(os.getenv(
        "AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS",
        str(DEFAULT_RUN_RUNTIME_SECRET_TTL_SECONDS),
    ))


def _runtime_secret_redis_config() -> RedisConfig:
    return RedisConfig(url=os.getenv(
        "AGENT_RUN_RUNTIME_SECRET_REDIS_URL",
        DEFAULT_RUN_RUNTIME_SECRET_REDIS_URL,
    ))


async def get_run_runtime_secret_redis_client():
    # 独立缓存；不得复用共享 get_async_redis_client()，否则 Header 会进入主 Redis AOF。
    ...


async def store_run_browser_cookie_secret(
    run_id: str,
    secret: BrowserCookieRuntimeSecret | None,
) -> None:
    redis = await get_run_runtime_secret_redis_client()
    if secret is None:
        await redis.delete(_secret_key(run_id))
        return
    key = _secret_key(run_id)
    async with redis.pipeline(transaction=True) as pipeline:
        pipeline.hset(key, mapping={"header": secret.header, "origin": secret.origin})
        pipeline.expire(key, _secret_ttl_seconds())
        await pipeline.execute()


async def load_run_browser_cookie_secret(run_id: str) -> BrowserCookieRuntimeSecret | None:
    value = await (await get_run_runtime_secret_redis_client()).hgetall(_secret_key(run_id))
    header = value.get("header")
    origin = value.get("origin")
    if not header or not origin:
        return None
    return BrowserCookieRuntimeSecret(header=str(header), origin=str(origin))


async def delete_run_browser_cookie_secret(run_id: str) -> None:
    await (await get_run_runtime_secret_redis_client()).delete(_secret_key(run_id))
```

Do not use `GETDEL`; worker retry must read the same value again. Add `runtime-secret-redis` to both Compose files with `redis-server --save "" --appendonly no`, `/data` tmpfs and no `volumes` entry; API and worker depend on its health check.

- [ ] **Step 4: Run GREEN test and commit**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_run_runtime_secret_service.py -q
git add backend/package/yuxi/services/run_runtime_secret_service.py backend/test/unit/services/test_run_runtime_secret_service.py
git commit -m "feat(sandbox): 新增运行期 Cookie 临时凭据服务"
```

### Task 2: Capture the Raw Header, Normalize Origin, and Remove It from ARQ

**Files:**
- Modify: `backend/server/routers/agent_router.py`
- Modify: `backend/server/routers/agent_invocation_router.py`
- Modify: `backend/package/yuxi/services/agent_invocation_service.py`
- Modify: `backend/package/yuxi/services/agent_run_service.py`
- Modify: `backend/test/unit/services/test_agent_run_service.py`
- Create: `backend/test/unit/routers/test_agent_router_cookie_header.py`
- Modify: `backend/test/unit/routers/test_agent_invocation_router.py`

**Interfaces:**
- Consumes: Task 1 `BrowserCookieRuntimeSecret` and store/delete functions.
- Produces: `build_browser_cookie_runtime_secret(cookie_header: str | None, request_base_url: str) -> BrowserCookieRuntimeSecret | None`.
- Produces: `enqueue_agent_run(run_id: str, browser_cookie: BrowserCookieRuntimeSecret | None = None) -> None`; ARQ only receives `run_id`.

- [ ] **Step 1: Add failing capture, origin, byte-limit, and queue tests**

```python
def test_build_browser_cookie_secret_preserves_raw_header():
    secret = build_browser_cookie_runtime_secret(
        "session=abc; theme=dark; session=path-specific",
        "https://yuxi.example.com/api/",
    )
    assert secret == BrowserCookieRuntimeSecret(
        header="session=abc; theme=dark; session=path-specific",
        origin="https://yuxi.example.com",
    )


def test_build_browser_cookie_secret_normalizes_default_port():
    secret = build_browser_cookie_runtime_secret("sid=abc", "https://yuxi.example.com:443/api/")
    assert secret.origin == "https://yuxi.example.com"


def test_build_browser_cookie_secret_rejects_header_over_32_kib():
    assert build_browser_cookie_runtime_secret("a=" + "x" * 32_768, "https://yuxi.example.com") is None


@pytest.mark.asyncio
async def test_enqueue_stores_secret_and_queues_only_run_id(monkeypatch):
    secret = BrowserCookieRuntimeSecret("sid=abc", "https://yuxi.example.com")
    await enqueue_agent_run("run-1", secret)
    assert stored == [("run-1", secret)]
    assert queue.calls == [("process_agent_run", "run-1", {"_job_id": "run:run-1"})]
```

Update router/service fakes to expect `browser_cookie`, and assert both HTTP entrypoints call the builder with `request.headers.get("cookie")` and `str(request.base_url)`, never `dict(request.cookies)`.

```python
response = client.post(
    "/api/agent-invocation/agent-call/runs",
    headers={"Cookie": "session=abc; theme=dark; session=path-specific"},
    json={"agent_slug": "translator", "messages": [{"role": "user", "content": "Hello"}]},
)
assert response.status_code == 200
assert calls["kwargs"]["browser_cookie"] == BrowserCookieRuntimeSecret(
    header="session=abc; theme=dark; session=path-specific",
    origin="http://testserver",
)
```

Create the normal agent router test with the same header and assert its patched `create_agent_run_view` receives the identical dataclass.

Add enqueue-failure tests proving secret deletion is attempted and a deletion failure does not mask the queue exception. Make the fake queue reject a third positional argument.

- [ ] **Step 2: Run RED tests**

```bash
docker exec api-dev uv run --group test pytest \
  test/unit/services/test_agent_run_service.py \
  test/unit/routers/test_agent_router_cookie_header.py \
  test/unit/routers/test_agent_invocation_router.py -q
```

Expected: raw-header builder and dataclass plumbing are absent; current code collapses the Header into a dict/JSON string.

- [ ] **Step 3: Implement exact Header preservation and origin normalization**

```python
BROWSER_COOKIE_HEADER_MAX_SIZE = 32_768


def _normalize_http_origin(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("request base URL must contain an HTTP origin")
    port = parsed.port
    default_port = 80 if parsed.scheme == "http" else 443
    port_suffix = f":{port}" if port is not None and port != default_port else ""
    host = parsed.hostname.lower()
    authority_host = f"[{host}]" if ":" in host else host
    return f"{parsed.scheme}://{authority_host}{port_suffix}"


def _browser_cookie_origin(request_base_url: str) -> str:
    configured_origin = (os.getenv("YUXI_PUBLIC_ORIGIN") or "").strip()
    if configured_origin:
        return _normalize_http_origin(configured_origin)
    if (os.getenv("YUXI_ENV") or "development").strip().lower() in {"production", "prod"}:
        raise ValueError("YUXI_PUBLIC_ORIGIN is required for browser Cookie sandbox injection in production")
    return _normalize_http_origin(request_base_url)


def build_browser_cookie_runtime_secret(
    cookie_header: str | None,
    request_base_url: str,
) -> BrowserCookieRuntimeSecret | None:
    header = str(cookie_header or "")
    if not header:
        return None
    payload_size = len(header.encode("latin-1"))
    if payload_size > BROWSER_COOKIE_HEADER_MAX_SIZE:
        logger.warning(f"browser cookie header too large ({payload_size} bytes), skip sandbox injection")
        return None
    return BrowserCookieRuntimeSecret(
        header=header,
        origin=_browser_cookie_origin(request_base_url),
    )
```

The routers call:

```python
browser_cookie=build_browser_cookie_runtime_secret(
    request.headers.get("cookie"),
    str(request.base_url),
)
```

The raw Header is already filtered by the browser for the Yuxi request. Do not attempt to reconstruct Domain/Path metadata that is not present in an HTTP `Cookie` Header.

Use only the server-controlled `YUXI_PUBLIC_ORIGIN` as the production origin source; fail explicitly when it is absent. Development may fall back to `request.base_url`. Do not accept an origin from payload, query parameters, an unvalidated `Origin` Header or Agent messages.

- [ ] **Step 4: Store the secret before enqueue and keep ARQ clean**

```python
async def enqueue_agent_run(
    run_id: str,
    browser_cookie: BrowserCookieRuntimeSecret | None = None,
) -> None:
    await store_run_browser_cookie_secret(run_id, browser_cookie)
    try:
        queue = await get_arq_pool()
        await queue.enqueue_job("process_agent_run", run_id, _job_id=f"run:{run_id}")
    except Exception:
        try:
            await delete_run_browser_cookie_secret(run_id)
        except Exception as cleanup_exc:  # noqa: BLE001
            logger.warning(
                f"Failed to delete runtime secret after enqueue failure for run {run_id}: {cleanup_exc}"
            )
        raise
```

Rename the pass-through parameter in `create_agent_run_view`, `create_agent_call_run_view`, and `create_agent_invocation_run_view` to `browser_cookie`. Keep `db.commit()` before enqueue.

- [ ] **Step 5: Run GREEN tests and commit**

```bash
docker exec api-dev uv run --group test pytest \
  test/unit/services/test_agent_run_service.py \
  test/unit/routers/test_agent_router_cookie_header.py \
  test/unit/routers/test_agent_invocation_router.py -q
git add backend/server/routers/agent_router.py \
  backend/server/routers/agent_invocation_router.py \
  backend/package/yuxi/services/agent_invocation_service.py \
  backend/package/yuxi/services/agent_run_service.py \
  backend/test/unit/services/test_agent_run_service.py \
  backend/test/unit/routers/test_agent_router_cookie_header.py \
  backend/test/unit/routers/test_agent_invocation_router.py
git commit -m "fix(sandbox): 以原始 Cookie Header 建立运行期凭据"
```

### Task 3: Run-Scoped Runtime Context and Worker Lifecycle

**Files:**
- Create: `backend/package/yuxi/agents/backends/sandbox/runtime_context.py`
- Modify: `backend/package/yuxi/services/run_worker.py`
- Modify: `backend/test/unit/services/test_run_worker.py`

**Interfaces:**
- Produces: `SandboxRuntimeCredentials(run_id: str, browser_cookie: BrowserCookieRuntimeSecret | None)`.
- Produces: `get_sandbox_runtime_credentials() -> SandboxRuntimeCredentials | None`.
- Produces: `sandbox_runtime_scope(credentials) -> AsyncContextManager[None]`.
- Produces: `register_sandbox_runtime_cleanup(key: str, callback: Callable[[], None]) -> None`.
- Consumes: Task 1 load/delete functions.

- [ ] **Step 1: Add failing lifecycle tests**

Cover: chat/resume/subagent all see loaded credentials; terminal run deletes Redis secret; retryable first attempt retains it; successful second attempt deletes it; cleanup callbacks run on success, failure, cancellation and retry exit; terminal-state lookup or Redis deletion failure does not mask the original worker result or exception.

```python
def fake_stream_agent_resume(**kwargs):
    captured["credentials"] = get_sandbox_runtime_credentials()
    return _BytesAsyncIter([b'{"status":"finished"}\n'])


assert captured["credentials"] == SandboxRuntimeCredentials(
    run_id="run-1",
    browser_cookie=BrowserCookieRuntimeSecret(
        header="sid=latest",
        origin="https://yuxi.example.com",
    ),
)
```

- [ ] **Step 2: Run RED test**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_run_worker.py -q
```

Expected: new context imports fail and resume lacks credentials.

- [ ] **Step 3: Implement context and cleanup scope**

```python
@dataclass(frozen=True, slots=True)
class SandboxRuntimeCredentials:
    run_id: str
    browser_cookie: BrowserCookieRuntimeSecret | None


_credentials_var = ContextVar[SandboxRuntimeCredentials | None](
    "sandbox_runtime_credentials", default=None
)
_cleanup_callbacks_var = ContextVar[dict[str, Callable[[], None]] | None](
    "sandbox_runtime_cleanup_callbacks", default=None
)


def get_sandbox_runtime_credentials() -> SandboxRuntimeCredentials | None:
    return _credentials_var.get()


def register_sandbox_runtime_cleanup(key: str, callback: Callable[[], None]) -> None:
    callbacks = _cleanup_callbacks_var.get()
    if callbacks is not None:
        callbacks.setdefault(key, callback)


@asynccontextmanager
async def sandbox_runtime_scope(credentials: SandboxRuntimeCredentials):
    credentials_token = _credentials_var.set(credentials)
    callbacks_token = _cleanup_callbacks_var.set({})
    try:
        yield
    finally:
        for callback in tuple((_cleanup_callbacks_var.get() or {}).values()):
            try:
                await asyncio.to_thread(callback)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed to clean sandbox runtime credential file: {exc}")
        _cleanup_callbacks_var.reset(callbacks_token)
        _credentials_var.reset(credentials_token)
```

- [ ] **Step 4: Wrap the existing worker body**

Rename the current body `_process_agent_run(ctx, run_id)`. The public function becomes:

```python
async def process_agent_run(ctx, run_id: str):
    credentials = SandboxRuntimeCredentials(
        run_id=run_id,
        browser_cookie=await load_run_browser_cookie_secret(run_id),
    )
    try:
        async with sandbox_runtime_scope(credentials):
            await _process_agent_run(ctx, run_id)
    finally:
        await _delete_terminal_runtime_secret(run_id)


async def _delete_terminal_runtime_secret(run_id: str) -> None:
    try:
        run = await _get_run(run_id)
        if run is None or run.status in TERMINAL_RUN_STATUSES:
            await delete_run_browser_cookie_secret(run_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to delete terminal runtime secret for run {run_id}: {exc}")
```

Remove `browser_cookies` from worker signatures and remove every use of `sandbox_cookies_var`. The wrapper applies equally to chat, resume and subagent.

- [ ] **Step 5: Run GREEN test and commit**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_run_worker.py -q
git add backend/package/yuxi/agents/backends/sandbox/runtime_context.py backend/package/yuxi/services/run_worker.py backend/test/unit/services/test_run_worker.py
git commit -m "feat(sandbox): 建立统一的运行期凭据上下文"
```

### Task 4: Subagent Cookie Inheritance

**Files:**
- Modify: `backend/package/yuxi/services/subagent_run_service.py` (`SubagentRunService.start`)
- Modify: `backend/test/unit/services/test_subagent_run_service.py`

**Interfaces:**
- Consumes: Task 3 `get_sandbox_runtime_credentials()`.
- Produces: child `enqueue_agent_run(child_run_id, inherited_browser_cookie)`; Redis key remains child run ID.

- [ ] **Step 1: Add failing inheritance tests**

Adapt `test_subagent_run_service_creates_child_relation_run_and_enqueue` so its fake accepts both arguments, then add a second no-context test using the same `_patch_repos`, `_fake_create_run_record`, `_agent`, and `build_chat_input_message` helpers:

```python
enqueued: list[tuple[str, BrowserCookieRuntimeSecret | None]] = []


async def fake_enqueue(run_id: str, browser_cookie: BrowserCookieRuntimeSecret | None = None):
    enqueued.append((run_id, browser_cookie))


async with sandbox_runtime_scope(
    SandboxRuntimeCredentials(
        "parent-run",
        BrowserCookieRuntimeSecret("sid=parent", "https://yuxi.example.com"),
    )
):
    result = await SubagentRunService(db).start(
        uid="user-1",
        created_by_run_id="parent-run",
        agent_item=_agent(),
        input_message=build_chat_input_message("run in background"),
        tool_call_id="tool-1",
        model_spec="provider:model",
    )

assert result.run.id == "child-run"
assert enqueued == [(
    "child-run",
    BrowserCookieRuntimeSecret("sid=parent", "https://yuxi.example.com"),
)]

# In the second test, call start without sandbox_runtime_scope.
assert enqueued == [("child-run", None)]
```

- [ ] **Step 2: Run RED test**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_subagent_run_service.py -q
```

Expected: current code calls `enqueue_agent_run(run.id)` without inherited credentials.

- [ ] **Step 3: Implement inheritance at enqueue**

```python
credentials = get_sandbox_runtime_credentials()
inherited_browser_cookie = credentials.browser_cookie if credentials is not None else None
await agent_run_service.enqueue_agent_run(run.id, inherited_browser_cookie)
```

Only newly created child runs are committed and enqueued; idempotent existing runs remain unchanged.

- [ ] **Step 4: Run GREEN test and commit**

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_subagent_run_service.py -q
git add backend/package/yuxi/services/subagent_run_service.py backend/test/unit/services/test_subagent_run_service.py
git commit -m "feat(subagent): 继承父运行的沙盒 Cookie"
```

### Task 5: Provisioner Instance Identity and Static File Pointer

**Files:**
- Modify: `docker/sandbox_provisioner/app.py`
- Modify: `backend/package/yuxi/agents/backends/sandbox/provisioner_client.py`
- Modify: `backend/package/yuxi/agents/backends/sandbox/provider.py`
- Modify: `backend/test/unit/backends/test_sandbox_provisioner_config.py`
- Modify: `backend/test/unit/backends/test_sandbox_provisioner_client.py`
- Modify: `backend/test/unit/backends/test_sandbox_backends.py`

**Interfaces:**
- Produces: `SandboxRecord.instance_id: str` in provisioner and client.
- Produces: `SandboxConnection.instance_id: str`.
- Produces: sandbox env `SANDBOX_COOKIE_HEADER_FILE=/home/gem/.yuxi-runtime/browser-cookie-header.txt`.

- [ ] **Step 1: Add failing instance identity tests**

Assert the exact identity source for each backend:

```python
# Memory: generated once, stable until delete.
assert len(record.instance_id) == 32
assert backend.discover("sandbox-1").instance_id == record.instance_id

# Docker: real container identity.
assert backend._to_record(container, "sandbox-1").instance_id == container.id

# Kubernetes: real Pod identity.
assert backend.discover("sandbox-1").instance_id == pod.metadata.uid
```

Update management API and client tests to require `instance_id`, and assert `SandboxConnection` copies it. Also assert Docker label and Kubernetes annotation carry `runtime-contract-version=cookie-header-file-v1`; an existing instance without the exact value fails the create-time identity check and is recreated.

- [ ] **Step 2: Add a failing static pointer test**

Patch `load_user_agent_env()` to return a conflicting user value and assert the reserved value wins:

```python
assert load_sandbox_env("user-1") == {
    "USER_VALUE": "ok",
    "SANDBOX_COOKIE_HEADER_FILE": "/home/gem/.yuxi-runtime/browser-cookie-header.txt",
}
```

Assert `SANDBOX_COOKIES_JSON` is absent from all sandbox create payloads.

- [ ] **Step 3: Run RED tests**

```bash
docker exec api-dev uv run --group test pytest \
  test/unit/backends/test_sandbox_provisioner_config.py \
  test/unit/backends/test_sandbox_provisioner_client.py \
  test/unit/backends/test_sandbox_backends.py -q
```

Expected: instance fields and static pointer do not exist.

- [ ] **Step 4: Implement instance IDs in all provisioner backends**

Extend `SandboxResponse` and both `SandboxRecord` dataclasses with required `instance_id: str`.

```python
# MemoryProvisionerBackend.create
instance_id=secrets.token_hex(16)

# LocalContainerProvisionerBackend._to_record
instance_id=str(container.id)

# KubernetesProvisionerBackend.discover
instance_id=str(pod.metadata.uid)
```

Return it from `sandbox_response()`, parse it in `ProvisionerClient.create()/discover()`, and copy it in `ProvisionerSandboxProvider._record_to_connection()`.

Define `SANDBOX_RUNTIME_CONTRACT_VERSION = "cookie-header-file-v1"`. Add it to Docker labels and Kubernetes annotations, and include it in existing-instance validation. This causes one upgrade recreation for legacy sandboxes, not one recreation per run.

- [ ] **Step 5: Replace secret env merging with a reserved path pointer**

Remove `COOKIE_ENV_VAR`, `sandbox_cookies_var`, and `_merge_cookies_env`. Define:

```python
SANDBOX_COOKIE_HEADER_FILE_ENV = "SANDBOX_COOKIE_HEADER_FILE"
SANDBOX_COOKIE_HEADER_FILE = "/home/gem/.yuxi-runtime/browser-cookie-header.txt"


def load_sandbox_env(uid: str) -> dict[str, str]:
    env = load_user_agent_env(uid)
    env[SANDBOX_COOKIE_HEADER_FILE_ENV] = SANDBOX_COOKIE_HEADER_FILE
    return env
```

Use `load_sandbox_env(uid)` in both provider create paths. The system pointer must overwrite a same-named user env value.

- [ ] **Step 6: Run GREEN tests and commit**

```bash
docker exec api-dev uv run --group test pytest \
  test/unit/backends/test_sandbox_provisioner_config.py \
  test/unit/backends/test_sandbox_provisioner_client.py \
  test/unit/backends/test_sandbox_backends.py -q
git add docker/sandbox_provisioner/app.py \
  backend/package/yuxi/agents/backends/sandbox/provisioner_client.py \
  backend/package/yuxi/agents/backends/sandbox/provider.py \
  backend/test/unit/backends/test_sandbox_provisioner_config.py \
  backend/test/unit/backends/test_sandbox_provisioner_client.py \
  backend/test/unit/backends/test_sandbox_backends.py
git commit -m "feat(sandbox): 暴露实例标识和 Header 文件路径"
```

### Task 6: Lazy Atomic Raw Header File Synchronization

**Files:**
- Modify: `backend/package/yuxi/agents/backends/sandbox/backend.py` (`ProvisionerSandboxBackend.__init__`, `_get_client`)
- Modify: `backend/test/unit/backends/test_sandbox_backends.py`

**Interfaces:**
- Consumes: Task 3 runtime context and cleanup registration.
- Consumes: Task 5 `SandboxConnection.instance_id` and file path constant.
- Produces: one successful sync per `(run_id, instance_id)` for each backend object.

- [ ] **Step 1: Add failing lazy synchronization tests**

Add separate tests for:

1. No runtime context: `_get_client()` performs no runtime-file shell/file operation.
2. `browser_cookie` present: directory creation, raw Header temp file write, temp `chmod 600`, atomic `mv -f`.
3. `browser_cookie=None`: target is removed to clear stale content.
4. Same `(run_id, instance_id)`: repeated access does not rewrite.
5. Same run, new `instance_id`, unchanged URL: synchronization runs again.
6. Registered cleanup removes the target.
7. Failed write removes target and temp, and does not set the sync marker.

The fake shell must assert the Cookie marker never appears in command strings.

- [ ] **Step 2: Run RED test**

```bash
docker exec api-dev uv run --group test pytest test/unit/backends/test_sandbox_backends.py -q
```

Expected: no runtime file synchronization exists.

- [ ] **Step 3: Implement path-only runtime file helpers**

Commands may contain only fixed/generated paths:

```text
mkdir -p /home/gem/.yuxi-runtime
chmod 700 /home/gem/.yuxi-runtime
chmod 600 /home/gem/.yuxi-runtime/.browser-cookie-header-<uuid>.tmp
mv -f /home/gem/.yuxi-runtime/.browser-cookie-header-<uuid>.tmp /home/gem/.yuxi-runtime/browser-cookie-header.txt
rm -f /home/gem/.yuxi-runtime/browser-cookie-header.txt
rm -f /home/gem/.yuxi-runtime/.browser-cookie-header-<uuid>.tmp
```

Write content only with:

```python
result = client.file.write_file(file=temp_path, content=credentials.browser_cookie.header)
if not result.success:
    raise RuntimeError(result.message or "failed to write sandbox runtime cookie file")
```

Check shell `exit_code`; do not log secret-bearing file contents or command output.

- [ ] **Step 4: Implement synchronization in `_get_client()`**

After resolving the connection and building/reusing the HTTP client:

```python
credentials = get_sandbox_runtime_credentials()
if credentials is not None:
    sync_key = (credentials.run_id, connection.instance_id)
    if self._runtime_cookie_sync_key != sync_key:
        self._sync_runtime_cookie_header_file(
            self._client,
            credentials.browser_cookie.header if credentials.browser_cookie is not None else None,
        )
        register_sandbox_runtime_cleanup(
            f"{self._id}:{connection.instance_id}",
            lambda client=self._client: self._delete_runtime_cookie_header_file(client),
        )
        self._runtime_cookie_sync_key = sync_key
```

For a present Header, prepare and chmod the temp file before `mv -f`. Write the exact Header string without parsing, JSON encoding or reconstruction. If any preparation step fails, best-effort delete target and temp so an older run's Header cannot survive. For absent credentials, delete only the target. Set the sync marker only after success.

- [ ] **Step 5: Run GREEN test and commit**

```bash
docker exec api-dev uv run --group test pytest test/unit/backends/test_sandbox_backends.py -q
git add backend/package/yuxi/agents/backends/sandbox/backend.py backend/test/unit/backends/test_sandbox_backends.py
git commit -m "feat(sandbox): 懒同步原始 Cookie Header 文件"
```

### Task 7: Dynamic Same-Origin System Prompt Injection

**Files:**
- Create: `backend/package/yuxi/agents/middlewares/sandbox_cookie.py`
- Modify: `backend/package/yuxi/agents/middlewares/__init__.py`
- Modify: `backend/package/yuxi/agents/buildin/chatbot/graph.py`
- Modify: `backend/package/yuxi/agents/buildin/subagent/graph.py`
- Create: `backend/test/unit/middlewares/test_sandbox_cookie_middleware.py`
- Modify: `backend/test/unit/agents/test_summary_graph_config.py`

**Interfaces:**
- Consumes: Task 3 `get_sandbox_runtime_credentials()` and Task 1 `BrowserCookieRuntimeSecret`.
- Produces: `SandboxCookiePromptMiddleware` and singleton `sandbox_cookie_prompt`.
- Injects: origin/path/rules only; never injects `BrowserCookieRuntimeSecret.header`.

- [ ] **Step 1: Write failing middleware tests**

Use a fake request with `SystemMessage(content="base")` and an async handler capturing the final request. Cover no context, active secret, duplicate invocation and secret non-disclosure:

```python
@pytest.mark.asyncio
async def test_sandbox_cookie_prompt_injects_origin_without_header():
    secret = BrowserCookieRuntimeSecret(
        header="session=secret-value; theme=dark",
        origin="https://yuxi.example.com",
    )
    async with sandbox_runtime_scope(SandboxRuntimeCredentials("run-1", secret)):
        await SandboxCookiePromptMiddleware().awrap_model_call(FakeRequest(), handler)

    text = _system_message_text(captured["request"].system_message)
    assert "https://yuxi.example.com" in text
    assert "SANDBOX_COOKIE_HEADER_FILE" in text
    assert "/home/gem/.yuxi-runtime/browser-cookie-header.txt" in text
    assert "scheme + host + port" in text
    assert "session=secret-value" not in text


@pytest.mark.asyncio
async def test_sandbox_cookie_prompt_skips_without_runtime_secret():
    await SandboxCookiePromptMiddleware().awrap_model_call(FakeRequest(), handler)
    assert _system_message_text(captured["request"].system_message) == "base"
```

Call the middleware twice with the already-injected `SystemMessage` and assert `SANDBOX_COOKIE_PROMPT_MARKER` occurs once.

- [ ] **Step 2: Add failing graph composition assertions**

Extend both tests in `test_summary_graph_config.py`:

```python
middleware_names = [type(middleware).__name__ for middleware in middlewares]
assert middleware_names.count("SandboxCookiePromptMiddleware") == 1
assert middleware_names.index("SandboxCookiePromptMiddleware") < middleware_names.index("SkillsMiddleware")
```

This proves both main and subagent graph paths receive the same policy.

- [ ] **Step 3: Run RED tests**

```bash
docker exec api-dev uv run --group test pytest \
  test/unit/middlewares/test_sandbox_cookie_middleware.py \
  test/unit/agents/test_summary_graph_config.py -q
```

Expected: middleware module and graph entries do not exist.

- [ ] **Step 4: Implement the dynamic prompt middleware**

```python
from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

from yuxi.agents.backends.sandbox.provider import SANDBOX_COOKIE_HEADER_FILE
from yuxi.agents.backends.sandbox.runtime_context import get_sandbox_runtime_credentials

SANDBOX_COOKIE_PROMPT_MARKER = "<!-- sandbox_cookie_context -->"


def _system_message_text(system_message) -> str:
    if system_message is None:
        return ""
    content = system_message.content
    if isinstance(content, str):
        return content
    return "\n".join(
        str(block.get("text") or "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def _build_sandbox_cookie_prompt(origin: str) -> str:
    return f"""{SANDBOX_COOKIE_PROMPT_MARKER}
<| 同源 Cookie Header 使用约束:重要 |>
当前运行提供了浏览器发送给 Yuxi 的原始 Cookie Header，仅允许用于 origin `{origin}`。
Header 文件路径由环境变量 `SANDBOX_COOKIE_HEADER_FILE` 指向，当前固定为
`{SANDBOX_COOKIE_HEADER_FILE}`。文件内容是可直接作为 HTTP `Cookie` 请求头使用的原始字符串，不是 JSON。

- 只有目标 URL 规范化后的 `scheme + host + port` 与 `{origin}` 完全一致时才可读取并使用该文件。
- 子域名、主机别名、IP 地址以及不同端口都不视为同 origin。
- 禁止在跨 origin 重定向中继续携带 Cookie；应关闭自动重定向，或逐跳检查 `Location` 后再决定。
- 只在发起请求的进程内读取并设置 `Cookie` Header；禁止打印、回显、记录、总结或向用户展示文件内容。
- 禁止把 Header 复制到 workspace、uploads、outputs、代码文件、命令参数、工具参数或其他持久化位置。
- 文件不存在或不可读时，视为当前运行没有可用登录态，不得猜测、恢复或使用历史 Cookie。
"""


class SandboxCookiePromptMiddleware(AgentMiddleware):
    async def awrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        credentials = get_sandbox_runtime_credentials()
        secret = credentials.browser_cookie if credentials is not None else None
        if secret is None:
            return await handler(request)
        existing = _system_message_text(request.system_message)
        if SANDBOX_COOKIE_PROMPT_MARKER in existing:
            return await handler(request)
        system_message = append_to_system_message(
            request.system_message,
            _build_sandbox_cookie_prompt(secret.origin),
        )
        return await handler(request.override(system_message=system_message))


sandbox_cookie_prompt = SandboxCookiePromptMiddleware()
```

- [ ] **Step 5: Install middleware in main and subagent graphs**

Export `SandboxCookiePromptMiddleware` and `sandbox_cookie_prompt` from `middlewares/__init__.py`. Insert the singleton immediately after the filesystem middleware entry in both `_build_middlewares()` lists, before attachment and Skills prompt injection.

- [ ] **Step 6: Run GREEN tests and commit**

```bash
docker exec api-dev uv run --group test pytest \
  test/unit/middlewares/test_sandbox_cookie_middleware.py \
  test/unit/agents/test_summary_graph_config.py -q
git add backend/package/yuxi/agents/middlewares/sandbox_cookie.py \
  backend/package/yuxi/agents/middlewares/__init__.py \
  backend/package/yuxi/agents/buildin/chatbot/graph.py \
  backend/package/yuxi/agents/buildin/subagent/graph.py \
  backend/test/unit/middlewares/test_sandbox_cookie_middleware.py \
  backend/test/unit/agents/test_summary_graph_config.py
git commit -m "feat(agent): 注入同源 Cookie Header 使用约束"
```

### Task 8: Real Sandbox Integration Regression

**Files:**
- Create: `backend/test/integration/test_sandbox_runtime_cookie_header_file.py`

**Interfaces:**
- Consumes: Tasks 3, 5 and 6 public behavior.
- Verifies: real file content/permissions, cleanup, stale clear and recreation resync.

- [ ] **Step 1: Write the integration test**

Use only a synthetic marker. Define the helpers in the same test module, then run this sequence:

```python
def _shell(client, command: str) -> tuple[int | None, str]:
    result = client.shell.exec_command(command=command, timeout=10)
    return result.data.exit_code, (result.data.output or "").strip()


def _connection(backend: ProvisionerSandboxBackend):
    connection = backend._provider.get(
        backend._thread_id,
        uid=backend._uid,
        create_if_missing=False,
        file_thread_id=backend._file_thread_id,
        skills_thread_id=backend._skills_thread_id,
    )
    assert connection is not None
    return connection


@pytest.mark.asyncio
async def test_runtime_cookie_header_file_reinjects_after_sandbox_recreate():
    suffix = uuid.uuid4().hex[:12]
    thread_id = f"cookie-thread-{suffix}"
    uid = f"cookie-user-{suffix}"
    cookie_header = "session=cookie-integration-marker; theme=dark"
    secret = BrowserCookieRuntimeSecret(cookie_header, "https://yuxi.example.com")
    backend = ProvisionerSandboxBackend(thread_id=thread_id, uid=uid)

    async with sandbox_runtime_scope(SandboxRuntimeCredentials("run-a", secret)):
        client = backend._get_client()
        assert _shell(client, f"cat {SANDBOX_COOKIE_HEADER_FILE}") == (0, cookie_header)
        assert _shell(client, f"stat -c %a {SANDBOX_COOKIE_HEADER_FILE}") == (0, "600")
        first_connection = _connection(backend)

        backend._provider._client.delete(backend.id)
        backend._provider._last_touch_at[first_connection.cache_key] = 0
        client = backend._get_client()
        second_connection = _connection(backend)
        assert second_connection.instance_id != first_connection.instance_id
        assert _shell(client, f"cat {SANDBOX_COOKIE_HEADER_FILE}") == (0, cookie_header)

    assert _shell(client, f"test -e {SANDBOX_COOKIE_HEADER_FILE}")[0] == 1
```

Then seed a synthetic stale raw Header through file API, enter `SandboxRuntimeCredentials("run-b", None)`, call `_get_client()`, and assert absence. This tests next-run clearing independently of normal cleanup. Also assert the file content is exactly the raw Header string and cannot be parsed as the former JSON object representation.

- [ ] **Step 2: Start Docker services and run the integration test alone**

```bash
docker compose up -d
docker ps
docker logs api-dev --tail 100
docker exec api-dev uv run --group test pytest test/integration/test_sandbox_runtime_cookie_header_file.py -q
```

Expected: API, worker, Redis, Postgres and provisioner are running; the test passes serially.

- [ ] **Step 3: Confirm the synthetic value is absent from infrastructure logs**

```bash
docker logs worker-dev --tail 300 | rg "cookie-integration-marker"
docker logs sandbox-provisioner --tail 300 | rg "cookie-integration-marker"
```

Expected: no matches.

- [ ] **Step 4: Commit integration coverage**

```bash
git add backend/test/integration/test_sandbox_runtime_cookie_header_file.py
git commit -m "test(sandbox): 覆盖 Cookie Header 文件复用和重建"
```

### Task 9: Configuration, Documentation, and Full Verification

**Files:**
- Modify: `.env.template`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.prod.yml`
- Modify: `docs/agents/sandbox-architecture.md`
- Modify: `docs/develop-guides/changelog.md`

**Interfaces:**
- Documents: `YUXI_PUBLIC_ORIGIN`, `AGENT_RUN_RUNTIME_SECRET_REDIS_URL`, `AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS=14400`, `SANDBOX_COOKIE_HEADER_FILE`, raw Header format, normalized origin and dynamic system prompt contract.
- Replaces: wording that treats Cookie as JSON, an ARQ argument or `SANDBOX_COOKIES_JSON` value.

- [ ] **Step 1: Update configuration template**

```dotenv
# 生产环境使用浏览器可见的 scheme + host + port。
YUXI_PUBLIC_ORIGIN=https://yuxi.example.com
# 必须指向关闭 AOF/RDB、无磁盘卷的独立 Redis。
# AGENT_RUN_RUNTIME_SECRET_REDIS_URL=redis://runtime-secret-redis:6379/0
# AgentRun 浏览器 Cookie 运行期凭据 TTL；默认覆盖 worker 两次最长执行尝试。
# AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS=14400
```

- [ ] **Step 2: Update sandbox architecture documentation**

Document the exact flow:

```text
HTTP raw Cookie Header + normalized Yuxi origin
-> dedicated volatile Redis Hash agent-run:runtime-secret:<run_id>
-> ARQ(run_id only) -> worker ContextVar
-> dynamic system prompt(origin/path/rules only)
-> first sandbox access -> /home/gem/.yuxi-runtime/browser-cookie-header.txt
```

Document that the browser has already selected only cookies applicable to the Yuxi request; the file preserves the exact Header and does not contain Domain/Path metadata. State that production origin comes from mandatory `YUXI_PUBLIC_ORIGIN`, while development may fall back to normalized `request.base_url`. Explain why the secret Redis must be separate from the AOF-enabled shared Redis, and require no AOF/RDB, tmpfs/no disk volume or an equivalent external volatile deployment. Document resume refresh, subagent child-key inheritance, main/subagent prompt injection, exact-origin comparison, cross-origin redirect handling, `instance_id` recreation detection, one-time `cookie-header-file-v1` legacy-instance replacement, run-end deletion, next-run stale clear, Redis TTL, idle sandbox deletion, and the fact that a run without sandbox tools creates no sandbox/file.

State explicitly that the prompt is a model policy because the raw file is readable; it does not replace a network-layer authenticated proxy if hard same-origin enforcement becomes required.

- [ ] **Step 3: Rewrite the unreleased changelog entry**

Replace the existing JSON/ARQ/environment-variable description in place. State that chat, resume and subagent are supported, the file contains the raw Header, and the system prompt receives only origin/path/safety rules; do not add a second conflicting Cookie section.

- [ ] **Step 4: Run all focused tests**

```bash
docker exec api-dev uv run --group test pytest \
  test/unit/services/test_run_runtime_secret_service.py \
  test/unit/services/test_agent_run_service.py \
  test/unit/services/test_run_worker.py \
  test/unit/services/test_subagent_run_service.py \
  test/unit/routers/test_agent_router_cookie_header.py \
  test/unit/routers/test_agent_invocation_router.py \
  test/unit/backends/test_sandbox_provisioner_config.py \
  test/unit/backends/test_sandbox_provisioner_client.py \
  test/unit/backends/test_sandbox_backends.py \
  test/unit/middlewares/test_sandbox_cookie_middleware.py \
  test/unit/agents/test_summary_graph_config.py -q
docker exec api-dev uv run --group test pytest test/integration/test_sandbox_runtime_cookie_header_file.py -q
```

Expected: all focused unit tests and the serial integration test pass.

- [ ] **Step 5: Run lint and diff checks**

```bash
docker exec api-dev uv run --group dev ruff check \
  server/routers/agent_router.py \
  server/routers/agent_invocation_router.py \
  package/yuxi/services/run_runtime_secret_service.py \
  package/yuxi/services/agent_invocation_service.py \
  package/yuxi/services/agent_run_service.py \
  package/yuxi/services/run_worker.py \
  package/yuxi/services/subagent_run_service.py \
  package/yuxi/agents/backends/sandbox/runtime_context.py \
  package/yuxi/agents/backends/sandbox/provisioner_client.py \
  package/yuxi/agents/backends/sandbox/provider.py \
  package/yuxi/agents/backends/sandbox/backend.py \
  package/yuxi/agents/middlewares/sandbox_cookie.py \
  package/yuxi/agents/buildin/chatbot/graph.py \
  package/yuxi/agents/buildin/subagent/graph.py \
  test/unit/services/test_run_runtime_secret_service.py \
  test/unit/services/test_agent_run_service.py \
  test/unit/services/test_run_worker.py \
  test/unit/services/test_subagent_run_service.py \
  test/unit/routers/test_agent_router_cookie_header.py \
  test/unit/routers/test_agent_invocation_router.py \
  test/unit/backends/test_sandbox_provisioner_config.py \
  test/unit/backends/test_sandbox_provisioner_client.py \
  test/unit/backends/test_sandbox_backends.py \
  test/unit/middlewares/test_sandbox_cookie_middleware.py \
  test/unit/agents/test_summary_graph_config.py \
  test/integration/test_sandbox_runtime_cookie_header_file.py
git diff --check
```

Expected: ruff and diff checks succeed.

- [ ] **Step 6: Run security-shaped source checks**

```bash
rg -n "SANDBOX_COOKIES_JSON|SANDBOX_COOKIES_FILE|browser-cookies.json|sandbox_cookies_var|serialize_browser_cookies|dict\(request.cookies\)" backend docker docs
rg -n "enqueue_job\(\"process_agent_run\"" backend/package/yuxi/services/agent_run_service.py
rg -n "browser-cookie-header.txt|SANDBOX_COOKIE_HEADER_FILE|sandbox_cookie_context" backend docker docs
```

Expected: 第一条命令只允许命中 provider 中用于 `pop` 清理旧用户环境变量的兼容常量、对应回归测试，以及说明“已移除”的文档；生产代码不得读取或转发旧变量值。Enqueue 只能包含 `run_id` 和 `_job_id`；所有 Header 文件路径都必须位于 `/home/gem/.yuxi-runtime`，不得位于 `user-data`；提示词 marker 只能出现在专用 middleware、测试和文档中。

- [ ] **Step 7: Inspect final diff and commit documentation**

```bash
git diff -- backend/package/yuxi/services backend/package/yuxi/agents/backends/sandbox docker/sandbox_provisioner .env.template docs/agents/sandbox-architecture.md docs/develop-guides/changelog.md backend/test
git add .env.template docs/agents/sandbox-architecture.md docs/develop-guides/changelog.md
git commit -m "docs(sandbox): 说明原始 Cookie Header 生命周期"
```

Confirm no Cookie content is added to `input_payload`, metadata, event payloads, logs, exception text, shell command strings or persistent mount paths.

## Acceptance Checklist

- [x] Chat run preserves the exact raw `Cookie` Header and writes it only when it first uses a sandbox.
- [x] Resume uses the resume request's latest Header/origin and replaces or clears the previous file.
- [x] Subagent receives the parent run `BrowserCookieRuntimeSecret` through a child-run Redis key.
- [x] ARQ args/results, AgentRun persistence and system prompts contain no raw Header content.
- [x] Main agent and subagent prompts contain the exact allowed origin, Header file path, non-disclosure rule and cross-origin redirect rule only when a secret exists.
- [x] Reused sandbox refreshes once per run; absent credentials clear stale Header content.
- [x] Deleted/recreated sandbox receives the active raw Header again despite a stable proxy URL.
- [x] Run exit removes the file best-effort; Redis TTL and idle deletion cover crashes.
- [x] Viewer/non-run access does not clear an active run's Cookie.
- [x] Directory/file permissions are `0700`/`0600`, and file content is raw Header text rather than JSON.
- [x] Sandbox creation remains lazy; runs without sandbox tools incur no sandbox startup cost.
- [x] Focused unit tests, real integration test, ruff, source checks and `git diff --check` pass.
