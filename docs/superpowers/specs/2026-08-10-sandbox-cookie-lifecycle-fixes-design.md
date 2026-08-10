# Sandbox Cookie 生命周期修复设计

**状态：** 已确认，采用线程级沙盒复用方案
**日期：** 2026-08-10

## 背景

`feat/sandbox-cookie` 已实现浏览器原始 Cookie Header 的 run 级 Redis 保存、worker ContextVar 传递、沙盒懒写文件、系统提示词说明和 subagent 继承。复核真实生命周期后，当前实现需要修复两个确定问题：Redis Secret 加载异常会绕过 worker 状态机，原子写入中断可能遗留临时 Cookie 文件。

沙盒由 Agent 第一次调用文件或 shell 工具时按需创建。普通 Agent 的沙盒身份由 `uid + file_thread_id + skills_thread_id` 决定，同一线程在 idle reaper 删除前复用同一容器或 Pod。当前方案继续把沙盒视为线程级执行环境，不把每个 run 升级成独立容器安全边界。

## 目标

- Redis Secret 加载失败不得让 AgentRun 永久停留在 `pending`。
- Secret 加载异常不得降级为无 Cookie 执行。
- 可重试加载失败保留 Redis Secret，供后续 ARQ 尝试继续使用。
- 最后一次加载失败必须把 run 标记为 `failed`，并按终态规则删除 Secret。
- 每次沙盒 Cookie 同步都清理历史正式文件和同目录临时文件。
- 保留线程级沙盒复用、沙盒懒创建和现有 idle reaper。
- 文档准确描述提示词约束、线程级信任边界和剩余风险；固定文件路径只由提示词说明，不注入沙盒环境变量。

## 非目标

- 不增加 run 级 sandbox ID，也不在 Cookie run 结束时强制销毁沙盒。
- 不尝试扫描或终止 Agent 在同一线程沙盒中启动的后台进程。
- 不增加 Cookie 域名、origin、目标 URL 或重定向校验。
- 不新增 Redis 服务、Redis client cache 或独立 Secret TTL。
- 不增加通用 shell 输出脱敏器，也不改变 Cookie 原始 Header 文件方案。

## 信任边界

沙盒是线程级信任边界。同一 `uid + file_thread_id + skills_thread_id` 范围内的连续 run 会在 idle 删除前复用同一实例。系统依靠以下机制限制 Cookie 生命周期：

1. Cookie 仅在当前 run 第一次实际使用沙盒时写入 tmpfs 或 `emptyDir`。
2. run 退出时 best-effort 删除正式文件。
3. 下一次存在运行期上下文的 run 会在使用沙盒前重新同步：有 Cookie 时覆盖，无 Cookie 时删除。
4. idle reaper 删除实例后，临时文件和实例内进程一起消失。

因此，本设计不承诺同一线程沙盒内的恶意后台进程与后续 run 相互隔离。若未来要求 run 之间具备严格安全隔离，应单独设计 run 级 sandbox ID，而不是在当前文件清理逻辑上继续增加进程扫描或 `pkill` 保底。

## 设计一：Secret 加载纳入 worker 状态机

### 当前问题

`process_agent_run()` 在进入 `try` 和 `sandbox_runtime_scope()` 前调用 `load_run_browser_cookie_secret()`。Redis 连接或读取异常会直接逃逸，绕过 `_process_agent_run()` 内已有的重试、失败终态和 end event 逻辑。ARQ 不会把普通异常自动转换为项目定义的可重试任务，业务 run 因而可能一直保持 `pending`。

### 修复结构

在 `run_worker.py` 增加一个只负责 worker 启动阶段的 helper：

```python
async def _load_sandbox_runtime_credentials(
    ctx,
    run_id: str,
) -> SandboxRuntimeCredentials | None:
    ...
```

返回规则：

- 加载成功：返回 `SandboxRuntimeCredentials`。Redis key 不存在仍属于成功，`browser_cookie=None`。
- 非最后一次加载异常：抛出 `RetryableRunError`，由 ARQ 发起下一次尝试。
- 最后一次加载异常：将 run 标记为 `failed`，发送稳定的 `runtime_secret_load_failed` 错误和 end event，然后返回 `None`。

`process_agent_run()` 的最外层 `try/finally` 必须覆盖 Secret 加载、runtime scope 和 Agent 执行：

```python
async def process_agent_run(ctx, run_id: str):
    try:
        credentials = await _load_sandbox_runtime_credentials(ctx, run_id)
        if credentials is None:
            return
        async with sandbox_runtime_scope(credentials):
            await _process_agent_run(ctx, run_id)
    finally:
        await _delete_terminal_runtime_secret(run_id)
```

这样可保证：

- 非最后一次失败时 run 仍为非终态，`_delete_terminal_runtime_secret()` 不删除 Secret。
- 最后一次失败时 run 已经进入终态，finally 主动删除 Secret；Redis 仍不可用时由现有 TTL 兜底。
- 加载异常不会被解释为“当前 run 没有 Cookie”。

### 错误信息

事件和 AgentRun 使用稳定值：

- `error_type="runtime_secret_load_failed"`
- `error_message="运行期 Cookie 凭据加载失败"`

不得把 Redis 异常原文或 Cookie Header 放进事件、数据库错误字段。服务端日志仅记录 `run_id`、尝试次数和异常类型；不记录 Secret 内容。

如果最后一次失败时 Redis 事件流仍不可用，应先保证 PostgreSQL 中的 run 进入 `failed`。追加 error/end event 使用 best-effort，不得反过来阻止终态落库。

## 设计二：统一清理 Cookie 正式文件和临时文件

### 当前问题

当前原子写入使用随机文件：

```text
/home/gem/.yuxi-runtime/.browser-cookie-header-<uuid>.tmp
```

异常处理只知道本次生成的 `temp_path`。worker 或进程在 `write_file` 完成后、`mv` 前终止时，历史临时文件会留到 idle reaper 删除实例；下一次无 Cookie run 目前只删除正式文件。

### 修复结构

在 `ProvisionerSandboxBackend` 中保留一个集中清理入口，删除固定路径和固定前缀：

```text
/home/gem/.yuxi-runtime/browser-cookie-header.txt
/home/gem/.yuxi-runtime/.browser-cookie-header-*.tmp
```

调用时机：

1. `header is None`：删除正式文件和全部历史临时文件后返回。
2. `header is not None`：创建并保护运行期目录后，先清理历史文件，再写入新的随机临时文件并原子替换。
3. 当前写入、chmod 或 mv 失败：再次执行同一清理入口，然后抛出同步失败异常。
4. run scope 的 cleanup callback：调用同一清理入口，而不是只删除正式文件。

路径和 glob 都由模块级固定常量生成，不拼接用户输入。项目已有数据库唯一索引保证同一个 `uid + agent_slug + conversation_thread_id` 只有一个非终态 run；普通 Agent 的同线程 Cookie 同步不会并发删除另一个 run 的临时文件。subagent 使用独立的 skills 线程范围，不共享相同 sandbox cache key。

## 设计三：文档与实现边界对齐

更新现有 Cookie 架构文档和变更日志：

- 明确沙盒为线程级复用环境，Cookie 文件清理不等价于 run 级进程隔离。
- 明确 idle reaper 删除实例后才会终止遗留后台进程。
- 明确系统提示词直接提供固定文件路径，是行为约束；应用代码不得主动把 Header 放入 Postgres、事件、日志或提示词，但通用 shell 对恶意回显不提供技术强保证。
- 保留“不增加域名或目标 URL 授权逻辑”的最终决策。
- 不引入新的部署变量或 Compose 服务。

## 修改范围

- `backend/package/yuxi/services/run_worker.py`
  - 增加 Secret 加载状态处理。
  - 扩大终态 Secret 清理的 finally 覆盖范围。
- `backend/package/yuxi/agents/backends/sandbox/backend.py`
  - 统一清理正式文件和临时文件。
- `backend/test/unit/services/test_run_worker.py`
  - 覆盖首次加载失败重试、最后一次失败终态和 Secret 删除时机。
- `backend/test/unit/backends/test_sandbox_backends.py`
  - 覆盖历史临时文件清理和失败路径。
- `docs/agents/sandbox-architecture.md`
  - 更新线程级信任边界和提示词残余风险。
- `docs/develop-guides/changelog.md`
  - 记录 worker 失败恢复和临时文件清理修复。
- `docs/superpowers/plans/2026-08-07-sandbox-cookie-runtime-file-inheritance.md`
  - 修正过强的安全保证，与最终架构保持一致。

## 测试策略

### Worker 单元测试

- 第一次 Secret 加载抛出异常：`process_agent_run()` 抛出 `RetryableRunError`，run 不进入终态，Secret 不删除。
- 最后一次 Secret 加载抛出异常：run 标记为 `failed`，error type 为 `runtime_secret_load_failed`，追加 end event，并触发终态 Secret 删除。
- 最后一次失败且追加 Redis event 失败：PostgreSQL run 仍保持 `failed`，事件失败不覆盖终态结果。
- Redis key 不存在：使用 `SandboxRuntimeCredentials(run_id=..., browser_cookie=None)` 正常执行，不视为加载失败。

### Sandbox backend 单元测试

- 有 Cookie 同步前先删除正式文件和 `.browser-cookie-header-*.tmp`。
- 无 Cookie run 同时删除正式文件和临时文件。
- 写入失败后执行相同的完整清理。
- runtime scope 正常退出、异常和取消时都调用完整清理。
- 同一个 `(run_id, instance_id)` 仍然只同步一次。

### 回归验证

- 运行相关 worker、runtime secret、sandbox backend 单元测试。
- 运行真实 provisioner 集成测试，验证原始 Header、`0700/0600` 权限、沙盒重建重新注入和 run 退出清理仍然成立。
- 对涉及文件运行 Ruff，并执行 `git diff --check`。

## 验收标准

- Secret 加载异常不会产生永久 `pending` run。
- 非最后一次失败保留 Secret，最后一次失败进入 `failed` 并主动清理。
- Secret 加载失败不会以无 Cookie 身份继续执行 Agent。
- 下一次沙盒同步能够清除历史随机临时文件。
- 沙盒仍按线程复用，创建仍为懒执行。
- Cookie 仍是原始 Header 文件，subagent 继承机制不变。
- 不增加 Redis、TTL、域名、origin 或目标 URL 配置。
- 文档不再把线程级复用沙盒描述为严格的 run 级进程隔离。
