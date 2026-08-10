# Sandbox Cookie 生命周期修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让运行期 Cookie Secret 加载失败进入 AgentRun 的重试/终态状态机，并在每次同步时清理遗留 Cookie 临时文件。

**Architecture:** 保留线程级沙盒复用和懒创建。worker 用启动阶段 helper 将 Secret 读取错误转换为 ARQ 重试或稳定的最终失败；sandbox backend 用一个固定路径/前缀的清理入口处理正式文件和所有临时文件。

**Tech Stack:** Python 3.12、FastAPI、ARQ、SQLAlchemy、Redis、pytest、ruff、Docker Compose。

## Global Constraints

- Cookie 保持浏览器发送的原始 Header 字符串，不转为 JSON。
- 不新增 Redis 服务、client cache、独立 TTL、域名、origin 或目标 URL 配置。
- 沙盒仍按 `uid + file_thread_id + skills_thread_id` 复用，仅在首次工具调用时创建。
- Redis key 不存在是无 Cookie 的成功路径；Redis 读取异常不是无 Cookie 的降级路径。
- 事件、数据库错误字段和日志不得包含 Cookie Header 或 Redis 异常原文。
- 同一 `uid + agent_slug + conversation_thread_id` 只有一个非终态 run；临时文件清理以该现有约束为前提。
- 不实现 run 级 sandbox 隔离或后台进程终止。

---

### Task 1: 将 Secret 读取失败接入 worker 状态机

**Files:**

- Modify: `backend/package/yuxi/services/run_worker.py:271-289`
- Test: `backend/test/unit/services/test_run_worker.py`

**Interfaces:**

- Consumes: `load_run_browser_cookie_secret(run_id) -> BrowserCookieRuntimeSecret | None`。
- Produces: `_load_sandbox_runtime_credentials(ctx, run_id) -> SandboxRuntimeCredentials | None`；`None` 仅表示最后一次加载失败已终态化。

- [x] **Step 1: 写入第一次加载失败的红测**

```python
async def test_process_agent_run_retries_when_runtime_secret_load_fails(...):
    monkeypatch.setattr(run_worker, "load_run_browser_cookie_secret", failing_load)
    with pytest.raises(run_worker.RetryableRunError):
        await run_worker.process_agent_run({"job_try": 1}, "run-1")
    assert run_obj.status == "pending"
    assert deleted == []
```

该测试捕获的错误是：普通 `ConnectionError` 直接逃出 `process_agent_run()`，没有成为可重试任务。

- [x] **Step 2: 运行红测**

Run: `docker exec api-dev uv run --group test pytest test/unit/services/test_run_worker.py -q`

Expected: 新测试因 `ConnectionError` 直接逃逸而失败。

- [x] **Step 3: 写入最后一次失败的红测**

```python
async def test_process_agent_run_fails_terminally_when_runtime_secret_load_exhausts_retries(...):
    monkeypatch.setattr(run_worker, "load_run_browser_cookie_secret", failing_load)
    await run_worker.process_agent_run({"job_try": run_worker.WorkerSettings.max_tries}, "run-1")
    assert run_obj.status == "failed"
    assert terminal_error["error_type"] == "runtime_secret_load_failed"
    assert deleted == ["run-1"]
```

追加一个变体令 `append_run_event` 抛出异常，断言 PostgreSQL 的 `failed` 终态和 Secret 删除不受影响。

- [x] **Step 4: 写最小实现**

```python
async def _load_sandbox_runtime_credentials(ctx, run_id: str) -> SandboxRuntimeCredentials | None:
    try:
        return SandboxRuntimeCredentials(run_id, await load_run_browser_cookie_secret(run_id))
    except Exception as exc:
        if not _is_last_try(ctx):
            raise RetryableRunError("runtime secret load failed") from exc
        await mark_run_terminal(run_id, "failed", "runtime_secret_load_failed", "运行期 Cookie 凭据加载失败")
        await _append_runtime_secret_load_failure_events(ctx, run_id)
        return None
```

`process_agent_run()` 的最外层 `try/finally` 覆盖 helper、runtime scope 和 Agent 执行；helper 返回 `None` 时直接返回，finally 仍调用 `_delete_terminal_runtime_secret()`。事件 helper 只写稳定 error type/message，内部吞掉追加事件失败并仅记录 run ID、尝试次数和异常类型。

- [x] **Step 5: 验证 Task 1**

Run: `docker exec api-dev uv run --group test pytest test/unit/services/test_run_worker.py -q`

Expected: 首次失败保留 Secret 并重试；最后一次失败进入终态。

### Task 2: 每次同步清理遗留 Cookie 临时文件

**Files:**

- Modify: `backend/package/yuxi/agents/backends/sandbox/backend.py:270-323`
- Test: `backend/test/unit/backends/test_sandbox_backends.py`

**Interfaces:**

- Consumes: `SANDBOX_COOKIE_HEADER_FILE`。
- Produces: `_delete_runtime_cookie_files(client) -> None`，删除正式文件及 `.browser-cookie-header-*.tmp`。

- [x] **Step 1: 写入无 Cookie run 的红测**

```python
async with sandbox_runtime_scope(SandboxRuntimeCredentials("run-1", None)):
    backend._get_client()
assert commands == [
    "rm -f /home/gem/.yuxi-runtime/browser-cookie-header.txt /home/gem/.yuxi-runtime/.browser-cookie-header-*.tmp",
    "rm -f /home/gem/.yuxi-runtime/browser-cookie-header.txt /home/gem/.yuxi-runtime/.browser-cookie-header-*.tmp",
]
```

该测试捕获的错误是：无 Cookie run 仅删正式文件，崩溃遗留的随机临时文件仍可被后续 Agent 列出。

- [x] **Step 2: 写入有 Cookie 与失败清理的红测**

断言有 Cookie 时在 `mkdir/chmod` 后、`write_file` 前执行同一完整清理；断言 `write_file` 失败后也删除固定前缀的全部临时文件，而不只是本次随机路径。

- [x] **Step 3: 运行红测**

Run: `docker exec api-dev uv run --group test pytest test/unit/backends/test_sandbox_backends.py -q`

Expected: 新断言因现有实现只删除正式文件或当前 `temp_path` 而失败。

- [x] **Step 4: 写最小实现**

```python
_SANDBOX_COOKIE_TEMP_FILE_GLOB = f"{PurePosixPath(SANDBOX_COOKIE_HEADER_FILE).parent}/.browser-cookie-header-*.tmp"

def _delete_runtime_cookie_files(client: Any) -> None:
    _run_runtime_file_command(
        client,
        f"rm -f {SANDBOX_COOKIE_HEADER_FILE} {_SANDBOX_COOKIE_TEMP_FILE_GLOB}",
        "failed to delete sandbox runtime cookie files",
    )
```

无 Header、写入前、写入失败和 runtime scope cleanup 都调用这一个入口。路径和 glob 均来自固定模块常量，不拼接用户输入。

- [x] **Step 5: 验证 Task 2**

Run: `docker exec api-dev uv run --group test pytest test/unit/backends/test_sandbox_backends.py -q`

Expected: Header 内容不出现在 shell command 或异常文本中；全部测试通过。

### Task 3: 对齐文档、回归并提交

**Files:**

- Modify: `docs/agents/sandbox-architecture.md:181-191`
- Modify: `docs/superpowers/plans/2026-08-07-sandbox-cookie-runtime-file-inheritance.md:50-63`
- Modify: `docs/develop-guides/changelog.md`
- Create: `docs/superpowers/plans/2026-08-10-sandbox-cookie-lifecycle-fixes.md`

- [x] **Step 1: 更新文档**

明确沙盒是线程级复用环境：run cleanup 与下一次同步删除正式/临时 Cookie 文件，idle reaper 删除实例后才终止遗留进程；提示词是行为约束，应用代码不得主动写入 Header，但通用 shell 的恶意回显不是技术强保证。

- [x] **Step 2: 运行聚焦回归、集成测试和静态检查**

Run:

```bash
docker exec api-dev uv run --group test pytest test/unit/services/test_run_worker.py test/unit/services/test_run_runtime_secret_service.py test/unit/backends/test_sandbox_backends.py -q
docker exec api-dev uv run --group test pytest test/integration/test_sandbox_runtime_cookie_header_file.py -q
docker exec api-dev uv run --group dev ruff check package/yuxi/services/run_worker.py package/yuxi/agents/backends/sandbox/backend.py
git diff --check
```

Expected: 全部通过。

- [x] **Step 3: 创建聚焦提交**

Run:

```bash
git add backend/package/yuxi/services/run_worker.py backend/package/yuxi/agents/backends/sandbox/backend.py backend/test/unit/services/test_run_worker.py backend/test/unit/backends/test_sandbox_backends.py docs/agents/sandbox-architecture.md docs/develop-guides/changelog.md docs/superpowers/plans/2026-08-07-sandbox-cookie-runtime-file-inheritance.md docs/superpowers/plans/2026-08-10-sandbox-cookie-lifecycle-fixes.md
git commit -m "fix(sandbox): 修复 Cookie 运行期清理"
```

Expected: 不包含 `Makefile` 或现有未跟踪文件。
