---
name: schedules
slug: schedules
description: "让 Agent 管理定时任务：创建、修改、删除周期性运行的任务，查看任务详情与执行日志，并支持手动触发一次运行。当用户希望让某个 Agent 按固定节奏（如每天、每周）自动执行，或需要查询/维护已有的定时任务时使用此技能。"
---

# 定时任务技能

当用户要求「让 Agent 定时运行」「每天自动执行某件事」「查看/取消已有的定时任务」或「立即跑一次定时任务」时，使用此技能。定时任务由调度器按 cron 周期触发对应的 Agent 运行。

## 可用工具

- `list_agents`：列出当前用户可用的智能体（slug + 名称），用于确认用户想绑定哪个 Agent。
- `create_schedule`：创建一个定时任务，指定任务名、目标 Agent（`agent_slug`）、cron 表达式、时区与运行内容（`query`）。
- `update_schedule`：修改已有定时任务的名称、cron 表达式、时区或运行内容（`query`）。
- `delete_schedule`：删除定时任务（按 owner 隔离）。**不可恢复，请先与用户确认。**
- `list_schedules`：列出当前用户可见的定时任务（分页），用于先确认有哪些任务可用。
- `get_schedule`：查看单条定时任务的详情（cron、时区、目标 Agent、下次运行时间等）。
- `list_schedule_logs`：查看某条定时任务的历史执行日志，用于排查是否按时运行、运行结果如何。
- `trigger_schedule`：立即手动触发一次运行，不影响原有的 cron 周期。

## 操作流程

1. 先确认用户要操作的是哪个 Agent（需要其 `agent_slug`）；调用 `list_agents` 获取可用的智能体清单，把用户口中的智能体名称映射到对应的 `agent_slug`，不要臆造。
2. 创建任务前，若需确认已有任务，调用 `list_schedules`；需要详情时调用 `get_schedule`。
3. 用 `create_schedule` 创建任务，cron 表达式与 `timezone` 务必与用户预期一致；不确定时向用户确认周期语义。
4. 创建或运行后，可用 `list_schedule_logs` 核验是否按预期触发与执行。
5. 修改用 `update_schedule`，取消/清理用 `delete_schedule`（删除为危险操作，需用户确认）。
6. 用户要求「现在就跑一次」时，用 `trigger_schedule` 手动触发，不改变既定周期。

## 关键约束

- 只能访问当前用户拥有或有权限的 Agent 与定时任务（按 owner 隔离）。
- 不要编造 `agent_slug` 或 `schedule_id`；优先从 `list_agents` / `list_schedules` / `get_schedule` 的返回中获取。
- cron 表达式与 `timezone` 是任务能否按时执行的关键，创建/修改后建议向用户复述一次周期含义。
- `delete_schedule` 为危险操作，执行前必须确认；`trigger_schedule` 会真实发起一次 Agent 运行，注意其成本与副作用。
