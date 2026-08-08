# Sandbox Cookie Runtime File Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将浏览器发给 Yuxi 的原始 Cookie Header 作为 run 级短期凭据写入沙盒临时文件，并让 chat、resume、subagent、沙盒复用和沙盒重建遵守同一生命周期。

**Architecture:** API 只保留原始 Cookie Header，并把 Header 写入现有主 Redis 的 run key；ARQ 只传 run_id。Worker 使用共享执行策略决定单次超时、最大尝试次数和 Redis TTL，TTL 固定按 job timeout × max tries × 2 推导，不再维护独立 TTL。Worker 为 chat、resume、subagent 激活 run 级 ContextVar；Agent 第一次实际使用沙盒时，backend 才把 Header 写入 /home/gem/.yuxi-runtime/browser-cookie-header.txt。系统提示词只说明文件路径、原始 Header 格式和不得泄露内容，不包含 Header 内容，也不承担域名授权或网络隔离职责。

**Tech Stack:** Python 3.12+、FastAPI、ARQ、现有 Redis asyncio client、ContextVar、agent-sandbox file/shell API、Docker/Kubernetes provisioner、pytest、ruff。

## Approved Decisions

- 基线提交为 1d8cfbef feat(sandbox): 支持浏览器 Cookie 运行期文件注入。
- 删除独立 runtime-secret-redis；Cookie run secret 复用现有主 Redis。
- 保留 run_id 独立 Redis key、终态主动删除和故障兜底 TTL。
- 删除 AGENT_RUN_RUNTIME_SECRET_REDIS_URL 和 AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS。
- 新增 AGENT_RUN_JOB_TIMEOUT_SECONDS，默认 3600。
- 新增 AGENT_RUN_MAX_TRIES，默认 2。
- Redis secret TTL 固定为 AGENT_RUN_JOB_TIMEOUT_SECONDS × AGENT_RUN_MAX_TRIES × 2；安全系数 2 是代码常量，不暴露为环境变量。
- 删除 YUXI_PUBLIC_ORIGIN 和精确 scheme + host + port 同源限制。
- 不新增 YUXI_COOKIE_ALLOWED_DOMAIN，不在运行期凭据或提示词中维护域名白名单。
- 本功能只负责把浏览器原始 Cookie Header 安全地提供给当前 run 的沙盒，不实现目标 URL、同源、子域或重定向校验。
- 原始 Header 文件、懒写入、0700/0600 权限、原子替换、run 退出清理、无 Cookie run 清理、instance_id 重建检测和 subagent 继承机制继续保留。
- Cookie 文件保留浏览器发来的完整 Header；如何选择目标系统不属于本功能的授权逻辑。

## Current Baseline

当前提交已经实现以下能力，本计划只修正架构，不重复重写已经正确的部分：

- 两个 HTTP Agent 入口读取原始 Cookie Header，而不是 request.cookies 字典。
- ARQ 的 process_agent_run 参数只有 run_id。
- Worker 通过 ContextVar 暴露 run 级凭据。
- subagent 创建 child run 时复制父 run 凭据。
- Header 文件固定为 /home/gem/.yuxi-runtime/browser-cookie-header.txt。
- 沙盒首次实际使用时懒写文件；目录权限 0700，文件权限 0600。
- 写入使用同目录临时文件加原子替换。
- run 退出时 best-effort 删除；无 Cookie run 主动删除旧文件。
- Provisioner 返回真实 instance_id，容器或 Pod 重建后重新同步文件。
- main agent 和 subagent 已安装动态系统提示词中间件。
- 真实 provisioner 集成测试已覆盖写入、权限、重建重新注入和清理。

当前基线中需要撤回的部分：

- 独立 runtime-secret-redis 服务、专用 client cache 和 Compose 依赖。
- BrowserCookieRuntimeSecret.origin。
- YUXI_PUBLIC_ORIGIN 及 request.base_url origin 规范化。
- 精确 origin 提示词。
- 独立 AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS。

## Global Constraints

- 原始 Cookie Header 不得进入 Postgres、AgentRun input_payload/meta、LangGraph state/configurable、系统提示词、事件 payload、日志或异常文本。
- ARQ 的 process_agent_run 签名固定为 process_agent_run(ctx, run_id: str)。
- ARQ 参数和结果不得包含原始 Header。
- Redis key 固定为 agent-run:runtime-secret:{run_id}。
- Redis 使用现有 get_async_redis_client()；不得创建第二个 Redis 服务或第二套 client cache。
- Redis key 必须同时设置 TTL；run 终态、队列投递失败时应主动删除。
- 第一次 retryable 失败不得提前删除 secret；最后一次失败进入终态后删除。
- API 和 worker 必须读取相同的 AGENT_RUN_JOB_TIMEOUT_SECONDS 与 AGENT_RUN_MAX_TRIES；Compose 和其它部署清单必须从同一配置源注入这两个值。
- TTL 和主动删除只保证主 Redis 中的逻辑可见性；已有 AOF、RDB、复制和备份介质中的历史字节按现有 Redis 运维保留策略清理，不为本功能修改全局持久化策略。
- Header 按 Latin-1 字节表示限制为 32 KiB；空 Header 或超限 Header 不创建 secret。
- BrowserCookieRuntimeSecret 只保存 header，不保存 request origin、允许域或其它授权信息。
- 本功能不从 Cookie Header 推导 Domain/Path，不从 request host 推导公司根域，也不增加目标 URL 校验逻辑。
- Header 文件固定为 /home/gem/.yuxi-runtime/browser-cookie-header.txt，内容是原始 Header 文本，不是 JSON。
- SANDBOX_COOKIE_HEADER_FILE 只保存固定文件路径，不保存 Header 内容。
- /home/gem/.yuxi-runtime 必须位于 Docker tmpfs 或 Kubernetes emptyDir。
- 不在 run 创建时启动沙盒；只在 ProvisionerSandboxBackend._get_client() 第一次实际取用沙盒时同步。
- 无 run context 的 viewer/API 沙盒访问不得修改 Header 文件。
- 系统提示词只在当前 run 有 Cookie secret 时注入；main agent 和 subagent 都只收到文件路径、文件格式和保密说明。
- 系统提示词不声明允许域，不执行同源授权，也不等价于网络层强制隔离。
- runtime-contract-version 保持 cookie-header-file-v1；文件契约没有改变。
- Python 测试和 Ruff 必须在 api-dev 容器内运行；第一次执行 RED 测试前先用 docker ps 确认容器已启动，未启动时运行 docker compose up -d。
- Makefile、patch 文件、.agents、.comet 和其它用户无关改动不属于本计划。
- 每个任务遵循 RED 测试、最小实现、GREEN 测试、中文 Conventional Commit 的顺序。

## File Map

- Modify backend/package/yuxi/services/run_queue_service.py
  - 读取并校验 AGENT_RUN_JOB_TIMEOUT_SECONDS 和 AGENT_RUN_MAX_TRIES。
  - 提供共享 worker 执行策略和 secret TTL 计算函数。
- Modify backend/package/yuxi/services/run_worker.py
  - WorkerSettings 使用共享 job timeout 和 max tries。
- Modify backend/package/yuxi/services/run_runtime_secret_service.py
  - 删除专用 Redis client。
  - 使用现有 get_async_redis_client()。
  - 只保存 header。
  - TTL 使用共享计算函数。
- Modify backend/package/yuxi/services/agent_run_service.py
  - 删除 request origin 逻辑。
  - 构造 BrowserCookieRuntimeSecret(header)。
- Modify backend/server/routers/agent_router.py
  - 只传 request.headers.get("cookie")。
- Modify backend/server/routers/agent_invocation_router.py
  - 只传 request.headers.get("cookie")。
- Modify backend/package/yuxi/services/subagent_run_service.py
  - 继续复制父 run 的完整 BrowserCookieRuntimeSecret。
- Modify backend/package/yuxi/agents/middlewares/sandbox_cookie.py
  - 删除 origin 和域名规则，只提示 Header 文件路径与保密要求。
- Modify docker-compose.yml and docker-compose.prod.yml
  - 删除 runtime-secret-redis。
  - 删除其 depends_on 和 URL。
  - 传递 worker timeout 和 max tries。
- Modify .env.template
  - 删除旧 Redis URL、TTL 和 public origin。
  - 增加 worker timeout 和 max tries，不增加 Cookie 域配置。
- Modify related unit and integration tests.
- Modify docs/agents/sandbox-architecture.md and docs/develop-guides/changelog.md.

---

### Task 1: Share Worker Execution Policy and Derive Secret TTL

**Files:**

- Modify: backend/package/yuxi/services/run_queue_service.py
- Modify: backend/package/yuxi/services/run_worker.py
- Test: backend/test/unit/services/test_run_queue_service.py
- Test: backend/test/unit/services/test_run_worker.py

**Interfaces:**

- Produces: AGENT_RUN_JOB_TIMEOUT_SECONDS: int
- Produces: AGENT_RUN_MAX_TRIES: int
- Produces: AGENT_RUN_SECRET_TTL_SAFETY_FACTOR: int
- Produces: agent_run_runtime_secret_ttl_seconds() -> int
- Consumed by: WorkerSettings and run_runtime_secret_service

- [x] **Step 1: Write failing execution-policy tests**

Add reload-based tests so the environment values are evaluated exactly as a process would read them at startup, while restoring both the environment and module globals after every test.

~~~python
import importlib
import os


@pytest.fixture
def reload_execution_policy(monkeypatch):
    names = (
        "AGENT_RUN_JOB_TIMEOUT_SECONDS",
        "AGENT_RUN_MAX_TRIES",
    )
    original = {name: os.environ.get(name) for name in names}

    def reload_with(**values):
        for name in names:
            monkeypatch.delenv(name, raising=False)
        for name, value in values.items():
            monkeypatch.setenv(name, str(value))
        return importlib.reload(run_queue_service)

    try:
        yield reload_with
    finally:
        for name, value in original.items():
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)
        importlib.reload(run_queue_service)


def test_agent_run_execution_policy_defaults(reload_execution_policy):
    module = reload_execution_policy()

    assert module.AGENT_RUN_JOB_TIMEOUT_SECONDS == 3600
    assert module.AGENT_RUN_MAX_TRIES == 2
    assert module.AGENT_RUN_SECRET_TTL_SAFETY_FACTOR == 2
    assert module.agent_run_runtime_secret_ttl_seconds() == 14_400


def test_agent_run_execution_policy_reads_environment(reload_execution_policy):
    module = reload_execution_policy(
        AGENT_RUN_JOB_TIMEOUT_SECONDS="7200",
        AGENT_RUN_MAX_TRIES="3",
    )

    assert module.AGENT_RUN_JOB_TIMEOUT_SECONDS == 7200
    assert module.AGENT_RUN_MAX_TRIES == 3
    assert module.agent_run_runtime_secret_ttl_seconds() == 43_200


@pytest.mark.parametrize("name", ["AGENT_RUN_JOB_TIMEOUT_SECONDS", "AGENT_RUN_MAX_TRIES"])
@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_agent_run_execution_policy_rejects_non_positive_values(
    reload_execution_policy,
    name,
    value,
):
    with pytest.raises(ValueError, match=name):
        reload_execution_policy(**{name: value})
~~~

Extend worker tests:

~~~python
def test_worker_settings_use_shared_execution_policy():
    assert run_worker.WorkerSettings.job_timeout == run_queue_service.AGENT_RUN_JOB_TIMEOUT_SECONDS
    assert run_worker.WorkerSettings.max_tries == run_queue_service.AGENT_RUN_MAX_TRIES
~~~

- [x] **Step 2: Run RED tests**

~~~bash
docker exec api-dev uv run --group test pytest test/unit/services/test_run_queue_service.py test/unit/services/test_run_worker.py -q
~~~

Expected: the shared constants and TTL function do not exist, and WorkerSettings still uses literals.

- [x] **Step 3: Implement the shared execution policy**

Add the following near the existing run queue TTL configuration:

~~~python
def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


AGENT_RUN_JOB_TIMEOUT_SECONDS = _positive_int_env(
    "AGENT_RUN_JOB_TIMEOUT_SECONDS",
    3600,
)
AGENT_RUN_MAX_TRIES = _positive_int_env(
    "AGENT_RUN_MAX_TRIES",
    2,
)
AGENT_RUN_SECRET_TTL_SAFETY_FACTOR = 2


def agent_run_runtime_secret_ttl_seconds() -> int:
    return (
        AGENT_RUN_JOB_TIMEOUT_SECONDS
        * AGENT_RUN_MAX_TRIES
        * AGENT_RUN_SECRET_TTL_SAFETY_FACTOR
    )
~~~

Update WorkerSettings:

~~~python
class WorkerSettings:
    functions = [process_agent_run]
    max_tries = AGENT_RUN_MAX_TRIES
    retry_jobs = True
    job_timeout = AGENT_RUN_JOB_TIMEOUT_SECONDS
~~~

- [x] **Step 4: Run GREEN tests**

Run the command from Step 2.

Expected: all selected tests pass.

- [x] **Step 5: Commit the execution policy**

~~~bash
git add backend/package/yuxi/services/run_queue_service.py backend/package/yuxi/services/run_worker.py backend/test/unit/services/test_run_queue_service.py backend/test/unit/services/test_run_worker.py
git commit -m "refactor(agent): 统一运行超时与重试配置"
~~~

### Task 2: Reuse the Main Redis for Run Cookie Secrets

**Files:**

- Modify: backend/package/yuxi/services/run_runtime_secret_service.py
- Modify: backend/test/unit/services/test_run_runtime_secret_service.py
- Modify: docker-compose.yml
- Modify: docker-compose.prod.yml

**Interfaces:**

- Consumes: get_async_redis_client()
- Consumes: agent_run_runtime_secret_ttl_seconds()
- Produces: BrowserCookieRuntimeSecret(header: str)
- Produces: store_run_browser_cookie_secret(run_id, secret) -> None
- Produces: load_run_browser_cookie_secret(run_id) -> BrowserCookieRuntimeSecret | None
- Produces: delete_run_browser_cookie_secret(run_id) -> None

- [x] **Step 1: Replace dedicated-Redis tests with main-Redis tests**

Keep the fake Redis pipeline and assert that the service uses the existing shared client.

~~~python
class FakePipeline:
    # Add this method beside the existing hset, expire and execute methods.
    def delete(self, key):
        self.commands.append(("delete", key))
        return self


@pytest.mark.asyncio
async def test_runtime_secret_uses_existing_main_redis(monkeypatch):
    redis = FakeRedis()
    shared_client = AsyncMock(return_value=redis)
    monkeypatch.setattr(service, "get_async_redis_client", shared_client)

    await service.store_run_browser_cookie_secret(
        "run-1",
        service.BrowserCookieRuntimeSecret(
            header="sso=abc; theme=dark",
        ),
    )

    shared_client.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_runtime_secret_ttl_is_derived_from_worker_policy(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(service, "get_async_redis_client", AsyncMock(return_value=redis))
    monkeypatch.setattr(service, "agent_run_runtime_secret_ttl_seconds", lambda: 43_200)

    await service.store_run_browser_cookie_secret(
        "run-1",
        service.BrowserCookieRuntimeSecret(
            header="sso=abc",
        ),
    )

    assert redis.pipeline_calls == [
        (
            ("delete", "agent-run:runtime-secret:run-1"),
            (
                "hset",
                "agent-run:runtime-secret:run-1",
                {"header": "sso=abc"},
            ),
            ("expire", "agent-run:runtime-secret:run-1", 43_200),
        )
    ]
~~~

Replace the Compose persistence assertion with:

~~~python
@pytest.mark.parametrize("compose_file", ["docker-compose.yml", "docker-compose.prod.yml"])
def test_compose_does_not_define_a_cookie_specific_redis(compose_file):
    compose = yaml.safe_load((REPOSITORY_ROOT / compose_file).read_text())
    assert "runtime-secret-redis" not in compose["services"]
    assert "runtime-secret-redis" not in compose["services"]["api"].get("depends_on", {})
    assert "runtime-secret-redis" not in compose["services"]["worker"].get("depends_on", {})
~~~

- [x] **Step 2: Run RED tests**

~~~bash
docker exec api-dev uv run --group test pytest test/unit/services/test_run_runtime_secret_service.py -q
~~~

Expected: the service still creates a dedicated client, stores origin, and Compose still contains runtime-secret-redis.

- [x] **Step 3: Simplify the secret service**

The production module should have no global Redis client or asyncio lock.

~~~python
from dataclasses import dataclass

from yuxi.services.run_queue_service import agent_run_runtime_secret_ttl_seconds
from yuxi.storage.redis import get_async_redis_client

RUN_RUNTIME_SECRET_KEY_PREFIX = "agent-run:runtime-secret:"


@dataclass(frozen=True, slots=True)
class BrowserCookieRuntimeSecret:
    header: str


def _secret_key(run_id: str) -> str:
    return f"{RUN_RUNTIME_SECRET_KEY_PREFIX}{run_id}"


async def store_run_browser_cookie_secret(
    run_id: str,
    secret: BrowserCookieRuntimeSecret | None,
) -> None:
    redis = await get_async_redis_client()
    key = _secret_key(run_id)
    if secret is None:
        await redis.delete(key)
        return

    async with redis.pipeline(transaction=True) as pipeline:
        pipeline.delete(key)
        pipeline.hset(
            key,
            mapping={"header": secret.header},
        )
        pipeline.expire(key, agent_run_runtime_secret_ttl_seconds())
        await pipeline.execute()


async def load_run_browser_cookie_secret(run_id: str) -> BrowserCookieRuntimeSecret | None:
    redis = await get_async_redis_client()
    value = await redis.hgetall(_secret_key(run_id))
    header = value.get("header")
    if not header:
        return None
    return BrowserCookieRuntimeSecret(header=str(header))


async def delete_run_browser_cookie_secret(run_id: str) -> None:
    await (await get_async_redis_client()).delete(_secret_key(run_id))
~~~

Deleting and recreating the hash inside the transaction is intentional: it removes the legacy origin field before writing the header-only schema.

- [x] **Step 4: Remove the dedicated Redis service**

In both Compose files:

- Remove AGENT_RUN_RUNTIME_SECRET_REDIS_URL.
- Remove runtime-secret-redis from api.depends_on and worker.depends_on.
- Delete the complete runtime-secret-redis service.
- Keep the existing main redis service unchanged.

- [x] **Step 5: Run GREEN tests and parse Compose**

~~~bash
docker exec api-dev uv run --group test pytest test/unit/services/test_run_runtime_secret_service.py -q
docker compose config --quiet
~~~

For production Compose, first verify that the repository does not already contain .env.prod, create an empty temporary .env.prod only to satisfy the service env_file path, provide all interpolation values inline, then remove the temporary file:

~~~bash
(
  set -eu
  test ! -e .env.prod
  trap 'rm -f .env.prod' EXIT
  touch .env.prod
  env JWT_SECRET_KEY=test-jwt-key YUXI_INSTANCE_ID=test-instance POSTGRES_PASSWORD=test-postgres-password MINIO_ACCESS_KEY=test-minio-access MINIO_SECRET_KEY=test-minio-secret NEO4J_PASSWORD=test-neo4j-password SANDBOX_PROVISIONER_TOKEN=12345678901234567890123456789012 docker compose -f docker-compose.prod.yml config --quiet
)
~~~

Expected: tests and both Compose parses pass.

- [x] **Step 6: Commit the Redis simplification**

~~~bash
git add backend/package/yuxi/services/run_runtime_secret_service.py backend/test/unit/services/test_run_runtime_secret_service.py docker-compose.yml docker-compose.prod.yml
git commit -m "refactor(sandbox): 复用主 Redis 保存运行凭据"
~~~

### Task 3: Capture the Raw Cookie Header Without Origin Metadata

**Files:**

- Modify: backend/package/yuxi/services/agent_run_service.py
- Modify: backend/server/routers/agent_router.py
- Modify: backend/server/routers/agent_invocation_router.py
- Modify: backend/test/unit/routers/test_agent_router_cookie_header.py
- Modify: backend/test/unit/routers/test_agent_invocation_router.py
- Modify: backend/test/unit/services/test_agent_run_service.py

**Interfaces:**

- Produces: build_browser_cookie_runtime_secret(cookie_header: str | None) -> BrowserCookieRuntimeSecret | None
- Removes: request_base_url argument and all YUXI_PUBLIC_ORIGIN logic

- [x] **Step 1: Replace origin tests with header-only tests**

~~~python
def test_build_browser_cookie_secret_preserves_raw_header():
    secret = build_browser_cookie_runtime_secret(
        "yuxi_sso=abc; local_session=xyz",
    )

    assert secret == BrowserCookieRuntimeSecret(
        header="yuxi_sso=abc; local_session=xyz",
    )


def test_build_browser_cookie_secret_skips_empty_header():
    assert build_browser_cookie_runtime_secret(None) is None
    assert build_browser_cookie_runtime_secret("") is None


def test_build_browser_cookie_secret_rejects_header_over_32_kib():
    oversized = "a=" + "x" * 32_767

    assert build_browser_cookie_runtime_secret(oversized) is None
~~~

Update router assertions:

~~~python
response = client.post(
    "/api/agent/runs",
    headers={"Cookie": "yuxi_sso=abc; local_session=xyz"},
    json=payload,
)

assert calls["kwargs"]["browser_cookie"] == BrowserCookieRuntimeSecret(
    header="yuxi_sso=abc; local_session=xyz",
)
~~~

Ensure the patched builder receives only the Cookie Header:

~~~python
assert builder_calls == ["yuxi_sso=abc; local_session=xyz"]
~~~

- [x] **Step 2: Run RED tests**

~~~bash
docker exec api-dev uv run --group test pytest test/unit/routers/test_agent_router_cookie_header.py test/unit/routers/test_agent_invocation_router.py test/unit/services/test_agent_run_service.py -q
~~~

Expected: the builder still requires request_base_url and returns origin.

- [x] **Step 3: Remove origin handling and return a header-only secret**

~~~python
BROWSER_COOKIE_HEADER_MAX_SIZE = 32_768


def build_browser_cookie_runtime_secret(
    cookie_header: str | None,
) -> BrowserCookieRuntimeSecret | None:
    header = str(cookie_header or "")
    if not header:
        return None

    payload_size = len(header.encode("latin-1"))
    if payload_size > BROWSER_COOKIE_HEADER_MAX_SIZE:
        logger.warning(
            f"browser cookie header too large ({payload_size} bytes), "
            "skip sandbox injection"
        )
        return None

    return BrowserCookieRuntimeSecret(header=header)
~~~

Delete _normalize_http_origin(), _browser_cookie_origin() and the now-unused urlsplit import. Keep os because the same module still reads unrelated run settings from environment variables.

Update both routers:

~~~python
browser_cookie=build_browser_cookie_runtime_secret(
    request.headers.get("cookie"),
)
~~~

Do not read request.cookies, request.base_url or request.headers["origin"].

- [x] **Step 4: Run GREEN tests**

Run the command from Step 2.

Expected: all selected tests pass.

- [x] **Step 5: Commit header-only capture**

~~~bash
git add backend/package/yuxi/services/agent_run_service.py backend/server/routers/agent_router.py backend/server/routers/agent_invocation_router.py backend/test/unit/routers/test_agent_router_cookie_header.py backend/test/unit/routers/test_agent_invocation_router.py backend/test/unit/services/test_agent_run_service.py
git commit -m "refactor(sandbox): 简化运行期 Cookie 凭据"
~~~

### Task 4: Simplify the File-Path Prompt and Preserve Subagent Inheritance

**Files:**

- Modify: backend/package/yuxi/agents/middlewares/sandbox_cookie.py
- Modify: backend/test/unit/middlewares/test_sandbox_cookie_middleware.py
- Modify: backend/test/unit/services/test_run_worker.py
- Modify: backend/test/unit/services/test_subagent_run_service.py
- Verify: backend/package/yuxi/services/subagent_run_service.py
- Verify: backend/package/yuxi/agents/backends/sandbox/backend.py

**Interfaces:**

- Consumes: BrowserCookieRuntimeSecret(header)
- Preserves: child run receives the same complete dataclass
- Preserves: Header content never enters the prompt

- [x] **Step 1: Write failing file-path prompt tests**

~~~python
@pytest.mark.asyncio
async def test_cookie_prompt_describes_only_the_runtime_header_file():
    secret = BrowserCookieRuntimeSecret(header="yuxi_sso=secret")

    async with sandbox_runtime_scope(SandboxRuntimeCredentials("run-1", secret)):
        await middleware.awrap_model_call(request, handler)

    text = _system_message_text(captured.system_message)
    assert SANDBOX_COOKIE_HEADER_FILE in text
    assert "原始 Cookie Header" in text
    assert "不是 JSON" in text
    assert "yuxi_sso=secret" not in text
~~~


In the existing test_subagent_run_service_creates_child_relation_run_and_enqueue test, replace the origin-based fixture with:

~~~python
parent_secret = BrowserCookieRuntimeSecret(
    header="yuxi_sso=parent",
)
async with sandbox_runtime_scope(SandboxRuntimeCredentials("parent-run", parent_secret)):
    result = await SubagentRunService(db).start(
        uid="user-1",
        created_by_run_id="parent-run",
        agent_item=_agent(),
        input_message=build_chat_input_message("run in background"),
        tool_call_id="tool-1",
        model_spec="provider:model",
    )

assert result.created is True
assert enqueued == [("child-run", parent_secret)]
~~~

Also keep a direct dataclass example in worker fixtures:

~~~python
secret = BrowserCookieRuntimeSecret(header="yuxi_sso=parent")
~~~

- [x] **Step 2: Run RED tests**

~~~bash
docker exec api-dev uv run --group test pytest test/unit/middlewares/test_sandbox_cookie_middleware.py test/unit/services/test_run_worker.py test/unit/services/test_subagent_run_service.py -q
~~~

Expected: middleware still refers to exact origin and the existing tests construct origin-based secrets.

- [x] **Step 3: Replace the prompt text**

The prompt contains only the runtime file contract and disclosure rules. It must not contain an origin, allowed domain, hostname matcher or redirect policy:

~~~python
def _build_sandbox_cookie_prompt() -> str:
    return f"""
{SANDBOX_COOKIE_PROMPT_MARKER}
<| 沙盒 Cookie Header 文件:重要 |>
当前运行提供了浏览器发送给 Yuxi 的原始 Cookie Header。
Header 文件路径由环境变量 SANDBOX_COOKIE_HEADER_FILE 指向，当前固定为
{SANDBOX_COOKIE_HEADER_FILE}。文件内容是原始 Cookie 请求头字符串，不是 JSON。

- 需要使用当前浏览器登录态时，从该文件读取内容并设置 HTTP Cookie Header。
- 禁止打印、回显、记录、总结或向用户展示文件内容。
- 禁止把 Header 复制到 workspace、uploads、outputs、代码文件或其它持久化位置。
- 文件不存在或不可读时，视为当前运行没有可用登录态。
"""
~~~

Middleware uses:

~~~python
_build_sandbox_cookie_prompt()
~~~

- [x] **Step 4: Update worker and subagent fixtures**

Replace every origin-based construction:

~~~python
BrowserCookieRuntimeSecret(header="yuxi_sso=abc")
~~~

Keep the existing inheritance logic:

~~~python
credentials = get_sandbox_runtime_credentials()
inherited_browser_cookie = (
    credentials.browser_cookie if credentials is not None else None
)
await agent_run_service.enqueue_agent_run(
    run.id,
    inherited_browser_cookie,
)
~~~

- [x] **Step 5: Run GREEN tests**

Run the command from Step 2.

Expected: all selected tests pass.

- [x] **Step 6: Commit prompt and inheritance updates**

~~~bash
git add backend/package/yuxi/agents/middlewares/sandbox_cookie.py backend/test/unit/middlewares/test_sandbox_cookie_middleware.py backend/test/unit/services/test_run_worker.py backend/test/unit/services/test_subagent_run_service.py
git commit -m "refactor(agent): 简化 Cookie 文件提示"
~~~

### Task 5: Update Environment and Architecture Documentation

**Files:**

- Modify: .env.template
- Modify: docker-compose.yml
- Modify: docker-compose.prod.yml
- Modify: docs/agents/sandbox-architecture.md
- Modify: docs/develop-guides/changelog.md
- Modify: docs/superpowers/plans/2026-08-07-sandbox-cookie-runtime-file-inheritance.md

**Interfaces:**

- Documents: AGENT_RUN_JOB_TIMEOUT_SECONDS
- Documents: AGENT_RUN_MAX_TRIES
- Removes: YUXI_PUBLIC_ORIGIN
- Removes: YUXI_COOKIE_ALLOWED_DOMAIN from the draft design; it must not be implemented
- Removes: AGENT_RUN_RUNTIME_SECRET_REDIS_URL
- Removes: AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS

- [x] **Step 1: Update environment examples**

The template should contain:

~~~dotenv
# AgentRun worker 单次执行上限和最大尝试次数
AGENT_RUN_JOB_TIMEOUT_SECONDS=3600
AGENT_RUN_MAX_TRIES=2
~~~

Both Compose API/worker environment anchors should pass:

~~~yaml
AGENT_RUN_JOB_TIMEOUT_SECONDS: ${AGENT_RUN_JOB_TIMEOUT_SECONDS:-3600}
AGENT_RUN_MAX_TRIES: ${AGENT_RUN_MAX_TRIES:-2}
~~~

Do not define a Cookie-specific Redis service.

- [x] **Step 2: Rewrite the architecture description**

Document this final flow:

~~~text
HTTP raw Cookie Header
→ existing main Redis key agent-run:runtime-secret:<run_id>
→ ARQ only carries run_id
→ worker run ContextVar
→ main/subagent dynamic file-path prompt
→ first actual sandbox access
→ /home/gem/.yuxi-runtime/browser-cookie-header.txt
~~~

The documentation must explicitly state:

- Cookie Domain and Path attributes are absent from the HTTP Header.
- The complete Header may also contain host-specific cookies.
- This feature does not infer or configure an allowed domain and does not validate the destination URL.
- The dynamic system prompt only exposes the file path, raw Header format and non-disclosure requirements.
- TTL is derived from worker execution limits and normally does not elapse because terminal cleanup deletes first.
- Main Redis persistence is unchanged.
- API and worker receive the same timeout and max-tries values, so the TTL calculation and ARQ execution policy cannot drift.
- Key expiry and deletion remove logical access, but existing Redis AOF/RDB files, replicas and backups retain historical bytes according to the platform's normal retention policy.
- The exact-origin policy, draft allowed-domain policy and dedicated Redis service were removed intentionally.

- [x] **Step 3: Run documentation and configuration checks**

~~~bash
rg -n "runtime-secret-redis|AGENT_RUN_RUNTIME_SECRET_REDIS_URL|AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS|YUXI_PUBLIC_ORIGIN|YUXI_COOKIE_ALLOWED_DOMAIN|allowed_domain|secret\.origin" .env.template docker-compose.yml docker-compose.prod.yml backend/package/yuxi docs/agents docs/develop-guides
~~~

Expected: no active production configuration or code reference remains; migration prose may mention a removed name only when explaining the change.

~~~bash
git diff --check
docker compose config --quiet
~~~

Expected: both commands exit zero.

- [x] **Step 4: Commit documentation**

~~~bash
git add .env.template docker-compose.yml docker-compose.prod.yml docs/agents/sandbox-architecture.md docs/develop-guides/changelog.md docs/superpowers/plans/2026-08-07-sandbox-cookie-runtime-file-inheritance.md
git commit -m "docs(sandbox): 更新 Cookie 运行期文件架构"
~~~

### Task 6: Run Focused and Real Integration Verification

**Files:**

- Verify: backend/test/integration/test_sandbox_runtime_cookie_header_file.py
- Verify: all files changed by Tasks 1 through 5

**Interfaces:**

- Proves: exact raw Header file content
- Proves: 0700 directory and 0600 file
- Proves: stable proxy URL plus changed instance_id causes reinjection
- Proves: run exit removes the file
- Proves: no-Cookie run clears stale content
- Proves: no extra Redis service is required

- [ ] **Step 1: Update the integration secret fixture**

Use:

~~~python
secret = BrowserCookieRuntimeSecret(
    header="yuxi_sso=cookie-integration-marker; theme=dark",
)
~~~

The file assertions remain unchanged.

- [ ] **Step 2: Run focused unit tests**

~~~bash
docker exec api-dev uv run --group test pytest test/unit/agents/test_summary_graph_config.py test/unit/backends/test_sandbox_backends.py test/unit/backends/test_sandbox_provisioner_client.py test/unit/backends/test_sandbox_provisioner_config.py test/unit/middlewares/test_sandbox_cookie_middleware.py test/unit/routers/test_agent_invocation_router.py test/unit/routers/test_agent_router_cookie_header.py test/unit/services/test_agent_run_service.py test/unit/services/test_run_queue_service.py test/unit/services/test_run_runtime_secret_service.py test/unit/services/test_run_worker.py test/unit/services/test_subagent_run_service.py -q
~~~

Expected: all selected tests pass.

- [ ] **Step 3: Run the real provisioner integration test**

Start the provisioner:

~~~bash
docker compose up -d --force-recreate sandbox-provisioner
~~~

Run the test inside api-dev and address the provisioner through the Compose network. This avoids the OrbStack host-port connection reset that can occur while the provisioner detaches a sandbox network:

~~~bash
docker exec -e SANDBOX_PROVIDER=provisioner -e SANDBOX_PROVISIONER_URL=http://sandbox-provisioner:8002 api-dev uv run --group test pytest test/integration/test_sandbox_runtime_cookie_header_file.py -q -s --durations=10
~~~

Expected: 1 passed. The test's finally block deletes its sandbox. Confirm that no test sandbox container or managed sandbox network remains:

~~~bash
docker ps --filter name=yuxi-sandbox --format '{{.Names}}'
docker network ls --filter name=yuxi-know-sandbox --format '{{.Name}}'
~~~

Expected: both commands print no test resource.

- [ ] **Step 4: Run the complete unit suite**

~~~bash
docker exec api-dev uv run --group test pytest test/unit -q
~~~

Expected: all requirement-related tests pass. If the existing macOS /private/var versus /var remote-skill path-alias failure remains, report it separately and do not modify that unrelated test in this task.

- [ ] **Step 5: Run Ruff**

~~~bash
docker exec api-dev uv run --group dev ruff check package/yuxi/services/run_queue_service.py package/yuxi/services/run_runtime_secret_service.py package/yuxi/services/agent_run_service.py package/yuxi/services/run_worker.py package/yuxi/services/subagent_run_service.py package/yuxi/agents/middlewares/sandbox_cookie.py server/routers/agent_router.py server/routers/agent_invocation_router.py test/unit/services/test_run_queue_service.py test/unit/services/test_run_runtime_secret_service.py test/unit/services/test_agent_run_service.py test/unit/services/test_run_worker.py test/unit/services/test_subagent_run_service.py test/unit/middlewares/test_sandbox_cookie_middleware.py test/unit/routers/test_agent_router_cookie_header.py test/unit/routers/test_agent_invocation_router.py test/integration/test_sandbox_runtime_cookie_header_file.py
~~~

Expected: All checks passed.

- [ ] **Step 6: Run final source and diff checks**

~~~bash
rg -n "runtime-secret-redis|AGENT_RUN_RUNTIME_SECRET_REDIS_URL|AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS|YUXI_PUBLIC_ORIGIN|YUXI_COOKIE_ALLOWED_DOMAIN|allowed_domain|secret\.origin|secret\.header.*logger|secret\.header.*print" backend docker docker-compose.yml docker-compose.prod.yml .env.template docs/agents docs/develop-guides
git diff --check
~~~

Expected: no obsolete production reference or secret logging is found; git diff check exits zero.

- [ ] **Step 7: Review the final diff**

~~~bash
git diff 1d8cfbef -- .env.template backend/package/yuxi/services backend/package/yuxi/agents/middlewares/sandbox_cookie.py backend/server/routers backend/test docker-compose.yml docker-compose.prod.yml docs/agents/sandbox-architecture.md docs/develop-guides/changelog.md docs/superpowers/plans/2026-08-07-sandbox-cookie-runtime-file-inheritance.md
~~~

Confirm:

- runtime-secret-redis is removed.
- Main Redis configuration is otherwise unchanged.
- Worker settings and TTL use the same environment-derived values.
- Cookie prompt only documents the runtime file path, raw Header format and non-disclosure rules.
- No allowed-domain, same-origin, hostname or redirect policy remains in the runtime secret or prompt.
- Header content is absent from prompts, logs, exceptions and shell commands.
- Makefile and unrelated untracked files are absent from the diff.

## Acceptance Checklist

- [ ] No new Redis service, volume, health check or deployment dependency exists for this feature.
- [ ] Cookie run secrets use the existing main Redis client.
- [ ] AGENT_RUN_JOB_TIMEOUT_SECONDS defaults to 3600 and supports a positive integer environment override.
- [ ] AGENT_RUN_MAX_TRIES defaults to 2 and supports a positive integer environment override.
- [ ] API and worker receive identical timeout and max-tries values from the same deployment configuration.
- [ ] Secret TTL equals job timeout × max tries × 2.
- [ ] No independent secret TTL environment variable remains.
- [ ] Main Redis persistence settings are unchanged, and the documentation explains the AOF/RDB/backup retention tradeoff.
- [ ] Raw Cookie Header is preserved exactly and limited to 32 KiB.
- [ ] Redis, ARQ, Postgres, prompts and logs do not receive accidental extra copies beyond the approved run key.
- [ ] No YUXI_COOKIE_ALLOWED_DOMAIN environment variable or allowed_domain field exists.
- [ ] The prompt contains the fixed Header file path and states that the content is a raw Cookie Header, not JSON.
- [ ] The prompt contains no origin, domain whitelist, hostname matcher or redirect policy.
- [ ] Main agent and subagent receive the same file-path prompt only when a secret exists.
- [ ] Subagent copies the complete parent BrowserCookieRuntimeSecret to its child run key.
- [ ] Resume uses the newest request Header and replaces or clears the previous run's file content.
- [ ] Sandbox file creation remains lazy.
- [ ] Directory and file permissions remain 0700 and 0600.
- [ ] Reused sandboxes refresh once per run.
- [ ] Recreated sandboxes receive the active Header again through instance_id detection.
- [ ] Run exit and no-Cookie runs remove stale Header files.
- [ ] Focused unit tests, real integration test, Ruff, Compose parsing, source search and git diff check pass.
