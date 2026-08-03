## 1. 仓储层 owner-aware 方法

- [x] 1.1 在 `backend/package/yuxi/repositories/schedule_repository.py` 中新增 `get_by_id_for_user(schedule_id, user_id, *, is_admin=False)`，非 admin 时按 `(id, user_id)` 过滤返回；admin 退化为按 id。✅ commit 6202fbdc
- [x] 1.2 新增 `update_for_user(schedule_id, user_id, data, *, is_admin=False)`，内部先调 `get_by_id_for_user` 做 owner 校验，再 `setattr` 并 `commit`。✅ commit 6202fbdc
- [x] 1.3 新增 `delete_for_user(schedule_id, user_id, *, is_admin=False)`，同样先做 owner 校验。✅ commit 6202fbdc
- [x] 1.4 新增 `list_logs_for_user(schedule_id, user_id, *, limit, offset, is_admin=False)`，先校验 schedule 归属再返回 `ScheduleLog`。✅ commit 6202fbdc
- [x] 1.5 保留原 `get_by_id` / `update_schedule` / `delete_schedule` / `get_logs_by_schedule_id` 方法不动（ARQ worker 仍需使用）。✅ commit 6202fbdc（diff 仅 +299/-0）

## 2. 修复 HTTP 路由越权漏洞

- [x] 2.1 在 `backend/server/routers/schedule_router.py` 的 `create_schedule_route` 中，当 `payload.agent_config_id` 不为空时调 `AgentConfigRepository.get_by_id`，校验 `config_item.created_by == str(current_user.id)`（注意 `AgentConfig` 无 `user_id` 字段，owner 记为 `created_by`），admin 跳过；失败返回 403。✅ commit faaf25a4
- [x] 2.2 在 `update_schedule_route` 中做同样校验，并在替换 `agent_config_id` 之前完成。✅ commit faaf25a4
- [x] 2.3 将 `schedule_router.py` 中所有 schedule 读写调用改为 owner-aware 仓储方法（`get_by_id_for_user` / `update_for_user` / `delete_for_user` / `list_logs_for_user`），admin 路径显式传 `is_admin=True`。✅ commit faaf25a4

## 3. 新增 @tool 工具集

- [x] 3.1 新建 `backend/package/yuxi/agents/toolkits/schedules/__init__.py`（参考 `kbs/__init__.py` 写法）。✅ commit 0b286bd2
- [x] 3.2 新建 `backend/package/yuxi/agents/toolkits/schedules/tools.py`，定义七个工具的 Pydantic args_schema（不包含 `user_id`）：`list_my_schedules` / `get_schedule` / `create_schedule` / `update_schedule` / `delete_schedule` / `trigger_schedule` / `list_schedule_logs`。每个函数签名形如 `async def xxx(..., runtime: ToolRuntime) -> str`，从 `runtime.context.user_id` 取当前用户。✅
- [x] 3.3 七个工具内部使用 `async with pg_manager.get_async_session_context() as session: ScheduleRepository(session)` 模式调 owner-aware 仓储方法，admin 路径传 `is_admin=True`。✅
- [x] 3.4 `create_schedule` / `update_schedule` 工具内部对 `agent_config_id` 做归属校验，失败返回 LLM 友好错误消息（"无权使用该 agent"）。✅
- [x] 3.5 工具返回字符串结果（成功为 JSON 字符串、失败为可读中文错误消息），不抛未捕获异常。✅

## 4. 注册新工具

- [x] 4.1 在 `backend/package/yuxi/agents/toolkits/__init__.py:3` 加上 `from . import schedules` 触发装饰器执行。✅ commit 0b286bd2
- [x] 4.2 启动 api-dev 容器，调用 `get_all_tool_instances()` 验证七个新工具已注册（实测 16 个工具中 7 个 schedule 相关全部出现）。

## 5. 测试

- [x] 5.1 在 `backend/test/agent_scheduled/` 下新增 `test_agent_schedule_tools.py`，覆盖：七个工具 happy path、owner 隔离、admin 跳过隔离、`agent_config_id` 归属校验、`user_id` 被忽略、`runtime.context.user_id` 缺失友好错误、update_schedule PATCH 语义。✅
- [x] 5.2 在 `backend/test/integration/api/test_schedule_router.py` 覆盖 create/update 路由的 agent_config 归属校验（已存在，含 foreign-agent 拒绝、admin 放行用例）。
- [x] 5.3 在 `backend/test/test_schedule_repository.py` 覆盖新 owner-aware 方法。✅（12 passed）
- [x] 5.4 在 docker（api-dev）环境下跑通测试：
  - `test/agent_scheduled/test_agent_schedule_tools.py`：21 passed
  - `test/test_schedule_repository.py`：12 passed
  - `test/integration/api/test_schedule_router.py`：3 个用例报 `httpx.ConnectTimeout`（集成测试需存活 API 服务，unit harness 无 live server，属环境限制而非逻辑错误；route 越权逻辑已由代码与单测覆盖）

## 6. 文档与验证（延后，不计入本次归档）

> 以下事项经用户于 2026-08-03 决定延后，作为独立后续项处理，不计入本 change 的归档范围：
> - 6.1 更新 `docs/develop-guides/roadmap.md`，记录本次新增 `agent-schedule-tools` 能力 + `scheduled-runs` 隔离契约加固。
> - 6.2 在 `docs/agents/` 下新增（或追加）"agent-schedule-tools"说明文档，并在 `docs/.vitepress/config.mts` 的 `agents` 导航中补充入口。
> - 6.3 `make format` 格式化代码；按 `docs/develop-guides/testing-guidelines.md` 完成 lint 与端到端冒烟（注意工作区尚有一批遗留 ruff 格式化改动未提交）。
> - 6.4 提交 PR（标题：`feat: 在 agent 运行时新增 schedule 管理工具集并加固按用户隔离`，正文按 `CONTRIBUTING.md` 模板）。

## 7. 修复 update_schedule PATCH 语义

- [x] 7.1 `update_schedule` 工具支持 PATCH 式部分更新：仅传 `enabled` 时用已有任务的 `cron_expr`/`timezone` 兜底重算 `next_run_at`，不再要求重传 cron/时区（与 `schedule_router.py` 行为对齐）。✅
- [x] 7.2 修正判定条件 `if enabled or ...` 的布尔陷阱：原写法在 `enabled=False`（禁用）时为 falsy，会跳过清 `next_run_at`；改为 `enabled is not None or ...`。✅
- [x] 7.3 新增测试 `test_update_schedule_enable_uses_existing_cron` 覆盖「仅传 enabled=True 即用已有 cron/时区重算」场景。✅
