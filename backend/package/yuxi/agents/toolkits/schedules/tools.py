"""agent 运行时 schedule 管理工具

8 个 LangGraph @tool：
  - list_agents
  - list_schedules
  - get_schedule
  - create_schedule
  - update_schedule
  - delete_schedule
  - trigger_schedule
  - list_schedule_logs

所有工具仅操作"当前用户自己的"定时任务（按 runtime.context.uid 强制 owner 隔离），
不做任何角色/权限晋升（admin/superadmin 的越权查看与管控仅由 HTTP router 负责）。
agent 绑定通过 AgentRepository.get_visible_by_slug 复用既有可见性判定
（内部走 user_can_access_agent），可用的智能体清单由 list_agents 提供。
"""

import json
import uuid
from typing import Any

from langgraph.prebuilt.tool_node import ToolRuntime
from pydantic import BaseModel, Field

from yuxi.agents.toolkits.registry import tool
from yuxi.repositories.agent_repository import AgentRepository
from yuxi.repositories.schedule_repository import ScheduleRepository
from yuxi.repositories.user_repository import UserRepository
from yuxi.services.schedule_manager import compute_next_run
from yuxi.services.schedule_service import (
    ScheduleService,
    ScheduleValidationError,
    validate_timezone,
)
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import Agent, ScheduleDefinition
from yuxi.utils import logger


# ========== 内部 helpers ==========


def _resolve_user(runtime: ToolRuntime) -> str | None:
    """从 runtime.context 拿当前用户 uid（BaseContext.uid）；缺失返回 None。"""
    context = getattr(runtime, "context", None)
    if context is None:
        return None
    return getattr(context, "uid", None)


def _json_or_error(obj: Any, err: str) -> str:
    """成功返回 JSON 字符串；obj 为空/异常时返回 err。"""
    if obj is None:
        return err
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as exc:
        logger.warning(f"工具结果 JSON 序列化失败: {exc}")
        return err


async def _resolve_agent(db_session, user_id: str, agent_ref: str) -> tuple[Agent | None, str | None]:
    """按 slug 解析当前用户可见且启用的 Agent。

    可见性复用 AgentRepository.get_visible_by_slug（内部走 user_can_access_agent），
    与 router 保持一致；可用智能体清单由 list_agents 提供。
    返回 (agent, error)；agent 为 None 时 error 为面向 LLM 的中文错误消息。
    """
    user = await UserRepository().get_by_uid_with_db(db_session, user_id)
    if user is None:
        return None, "无法获取用户信息"
    agent = await AgentRepository(db_session).get_visible_by_slug(slug=agent_ref, user=user, kind="any")
    if agent is None:
        return None, f"指定的 Agent 不存在或无权使用: {agent_ref}"
    return agent, None


# ========== list_agents ==========


class ListAgentsInput(BaseModel):
    """列出当前用户可用的智能体输入模型"""

    # Langchain 的 runtime 注入机制要求必须有参数
    dummy: str = Field(default="", description="Dummy parameter - ignore")


@tool(
    category="schedules",
    tags=["查询智能体"],
    display_name="查看可用智能体",
    description="""列出当前用户可用的智能体（slug + 名称）。
当用户用智能体名称（而非 slug）表达想绑定的智能体时，先调用本工具获取清单，
把名称映射到对应的 agent_slug，再传给 create_schedule / update_schedule。""",
    args_schema=ListAgentsInput,
)
async def list_agents(dummy: str, runtime: ToolRuntime) -> str:  # type: ignore[no-redef]
    """列出当前用户可用的智能体（slug + 名称），供选择定时任务绑定的智能体。

    Returns:
        JSON 数组；每条含 slug/name/description/is_subagent。
    """
    user_id = _resolve_user(runtime)
    if not user_id:
        return "无法获取用户信息"

    try:
        async with pg_manager.get_async_session_context() as session:
            user = await UserRepository().get_by_uid_with_db(session, user_id)
            if user is None:
                return "无法获取用户信息"
            agents = await AgentRepository(session).list_visible(user=user)
        payload = [
            {"slug": a.slug, "name": a.name, "description": a.description, "is_subagent": a.is_subagent}
            for a in agents
        ]
        return _json_or_error(payload, "未找到任何可用智能体")
    except Exception as e:
        logger.error(f"list_agents 工具异常: {e}")
        return f"查询失败: {e}"


# ========== list_schedules ==========


LIST_DEFAULT_LIMIT = 20
LIST_MAX_LIMIT = 100


class ListSchedulesInput(BaseModel):
    """列出当前用户的定时任务。"""

    limit: int = LIST_DEFAULT_LIMIT
    offset: int = 0


@tool(
    category="schedules",
    tags=["查询定时任务"],
    display_name="列出定时任务",
    description="""列出当前用户的定时任务（分页）。
创建、修改或删除前，如需确认已有任务，先调用本工具查看现有任务及其 id。""",
    args_schema=ListSchedulesInput,
)  # type: ignore[misc]
async def list_schedules(  # type: ignore[no-redef]
    limit: int,
    offset: int,
    runtime: ToolRuntime,
) -> str:
    """列出当前用户的定时任务列表。

    Args:
        limit: 最多返回条数（默认 20，最大 100）
        offset: 分页偏移

    Returns:
        JSON 数组；每条含 id/name/cron_expr/enabled/next_run_at 等。
    """
    user_id = _resolve_user(runtime)
    if not user_id:
        return "无法获取用户信息"

    limit = min(max(int(limit), 1), LIST_MAX_LIMIT)
    offset = max(int(offset), 0)

    async with pg_manager.get_async_session_context() as session:
        repo = ScheduleRepository(session)
        rows = await repo.list_schedules(uid=user_id, limit=limit, offset=offset)

    payload = [
        {
            "id": r.id,
            "name": r.name,
            "cron_expr": r.cron_expr,
            "timezone": r.timezone,
            "enabled": r.enabled,
            "next_run_at": r.next_run_at,
            "agent_slug": r.agent_slug,
        }
        for r in rows
    ]
    return _json_or_error(payload, "未找到任何定时任务")


# ========== get_schedule ==========


class GetScheduleInput(BaseModel):
    """获取单条定时任务详情。"""

    schedule_id: str


@tool(
    category="schedules",
    tags=["查看定时任务"],
    display_name="查看定时任务详情",
    description="""查看单条定时任务的详情（cron、时区、目标 Agent、下次运行时间、启用状态等）。
需要确认任务当前配置时使用；schedule_id 可来自 list_schedules。""",
    args_schema=GetScheduleInput,
)  # type: ignore[misc]
async def get_schedule(schedule_id: str, runtime: ToolRuntime) -> str:  # type: ignore[no-redef]
    """获取单条定时任务详情（按 owner 隔离）。

    Args:
        schedule_id: 任务 ID

    Returns:
        JSON 字符串；无权访问时返回"未找到该任务"。
    """
    user_id = _resolve_user(runtime)
    if not user_id:
        return "无法获取用户信息"

    async with pg_manager.get_async_session_context() as session:
        repo = ScheduleRepository(session)
        row = await repo.get_by_id(schedule_id, user_id)

    if row is None:
        return "未找到该任务"
    return _json_or_error(row.to_dict(), "未找到该任务")


# ========== create_schedule ==========


class CreateScheduleInput(BaseModel):
    """创建一个新的定时任务。"""

    name: str
    description: str | None = None
    agent_slug: str = Field(..., description="目标 Agent 的 slug（可通过 list_agents 查询可用智能体）")
    cron_expr: str
    timezone: str = "Asia/Shanghai"
    query: str
    enabled: bool = True


@tool(
    category="schedules",
    tags=["创建定时任务"],
    display_name="创建定时任务",
    description="""创建一个定时任务：绑定目标 Agent（agent_slug 来自 list_agents）、cron 表达式、时区与运行内容（query）。
创建后由 cron 表达式与 timezone 决定下次自动执行时间。""",
    args_schema=CreateScheduleInput,
)  # type: ignore[misc]
async def create_schedule(  # type: ignore[no-redef]
    name: str,
    description: str | None,
    agent_slug: str,
    cron_expr: str,
    timezone: str,
    query: str,
    enabled: bool = True,
    runtime: ToolRuntime = None,
) -> str:
    """创建新的定时任务；agent_slug 需为当前用户可见且启用的智能体（可先通过 list_agents 查询）。"""
    user_id = _resolve_user(runtime)
    if not user_id:
        return "无法获取用户信息"

    try:
        async with pg_manager.get_async_session_context() as session:
            agent, err = await _resolve_agent(session, user_id, agent_slug)
            if err:
                return err

            # 校验时区（与启用状态无关，避免脏值延迟到调度才报错）
            try:
                validate_timezone(timezone)
            except ScheduleValidationError as e:
                return str(e.detail)

            # 计算 next_run_at；cron 失败由 compute_next_run 抛
            next_run = None
            if enabled:
                try:
                    next_run = compute_next_run(cron_expr, timezone)
                except Exception as e:
                    return f"cron 表达式无效: {e}"

            schedule = ScheduleDefinition(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                uid=str(user_id),
                agent_slug=agent.slug,
                cron_expr=cron_expr,
                timezone=timezone,
                query=query,
                enabled=enabled,
                next_run_at=next_run,
            )
            repo = ScheduleRepository(session)
            created = await repo.create_schedule(schedule)
            return _json_or_error(created.to_dict(), "创建失败")
    except Exception as e:
        logger.error(f"create_schedule 工具异常: {e}")
        return f"创建失败: {e}"


# ========== update_schedule ==========


class UpdateScheduleInput(BaseModel):
    """更新定时任务字段；只更新提供的字段。"""

    schedule_id: str
    name: str | None = None
    description: str | None = None
    agent_slug: str | None = Field(
        None, description="目标 Agent 的 slug（可通过 list_agents 查询可用智能体）；留空不修改"
    )
    cron_expr: str | None = None
    timezone: str | None = None
    query: str | None = None
    enabled: bool | None = None


@tool(
    category="schedules",
    tags=["修改定时任务"],
    display_name="修改定时任务",
    description="""修改已有定时任务的部分字段（名称、目标 Agent、cron、时区、query、启用状态），只更新提供的字段。
不要臆造 agent_slug，可从 list_agents 获取。""",
    args_schema=UpdateScheduleInput,
)  # type: ignore[misc]
async def update_schedule(  # type: ignore[no-redef]
    schedule_id: str,
    name: str | None,
    description: str | None,
    agent_slug: str | None,
    cron_expr: str | None,
    timezone: str | None,
    query: str | None,
    enabled: bool | None = None,
    runtime: ToolRuntime = None,
) -> str:
    """更新定时任务；agent_slug 需为当前用户可见且启用的智能体（可先通过 list_agents 查询）。"""
    user_id = _resolve_user(runtime)
    if not user_id:
        return "无法获取用户信息"

    try:
        async with pg_manager.get_async_session_context() as session:
            if agent_slug is not None:
                agent, err = await _resolve_agent(session, user_id, agent_slug)
                if err:
                    return err

            # 若显式修改时区，先校验有效性
            if timezone is not None:
                try:
                    validate_timezone(timezone)
                except ScheduleValidationError as e:
                    return str(e.detail)

            repo = ScheduleRepository(session)
            existing = await repo.get_by_id(schedule_id, user_id)
            if existing is None:
                return "未找到该任务"

            update_data: dict[str, Any] = {}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if agent_slug is not None:
                update_data["agent_slug"] = agent.slug
            if cron_expr is not None:
                update_data["cron_expr"] = cron_expr
            if timezone is not None:
                update_data["timezone"] = timezone
            if query is not None:
                update_data["query"] = query
            if enabled is not None:
                update_data["enabled"] = enabled

            # 若改了 cron/时区/启用状态，重算 next_run_at；未提供的字段用已有任务兜底（PATCH 语义）
            if enabled is not None or "cron_expr" in update_data or "timezone" in update_data:
                final_cron = update_data.get("cron_expr", existing.cron_expr)
                final_tz = update_data.get("timezone", existing.timezone)
                final_enabled = update_data.get("enabled", existing.enabled)
                if final_enabled:
                    try:
                        update_data["next_run_at"] = compute_next_run(final_cron, final_tz)
                    except Exception as e:
                        return f"cron 表达式无效: {e}"
                else:
                    update_data["next_run_at"] = None

            updated = await repo.update_schedule(schedule_id, update_data)
            if updated is None:
                return "未找到该任务"
            return _json_or_error(updated.to_dict(), "更新失败")
    except Exception as e:
        logger.error(f"update_schedule 工具异常: {e}")
        return f"更新失败: {e}"


# ========== delete_schedule ==========


class DeleteScheduleInput(BaseModel):
    """删除定时任务。"""

    schedule_id: str


@tool(
    category="schedules",
    tags=["删除定时任务"],
    display_name="删除定时任务",
    description="""删除定时任务（仅限本人创建，按 owner 隔离）。
不可恢复，执行前必须与用户确认。""",
    args_schema=DeleteScheduleInput,
)  # type: ignore[misc]
async def delete_schedule(schedule_id: str, runtime: ToolRuntime) -> str:  # type: ignore[no-redef]
    """删除定时任务（按 owner 隔离）。"""
    user_id = _resolve_user(runtime)
    if not user_id:
        return "无法获取用户信息"

    try:
        async with pg_manager.get_async_session_context() as session:
            repo = ScheduleRepository(session)
            existing = await repo.get_by_id(schedule_id, user_id)
            if existing is None:
                return "未找到该任务"
            ok = await repo.delete_schedule(schedule_id)
        if not ok:
            return "未找到该任务"
        return _json_or_error({"deleted": True, "schedule_id": schedule_id}, "删除失败")
    except Exception as e:
        logger.error(f"delete_schedule 工具异常: {e}")
        return f"删除失败: {e}"


# ========== list_schedule_logs ==========


class ListScheduleLogsInput(BaseModel):
    """列出指定定时任务的执行日志。"""

    schedule_id: str
    limit: int = LIST_DEFAULT_LIMIT
    offset: int = 0


@tool(
    category="schedules",
    tags=["查询执行日志"],
    display_name="查看定时任务执行日志",
    description="""查看某条定时任务的历史执行日志，用于排查任务是否按时触发、运行结果如何。""",
    args_schema=ListScheduleLogsInput,
)  # type: ignore[misc]
async def list_schedule_logs(  # type: ignore[no-redef]
    schedule_id: str,
    limit: int,
    offset: int,
    runtime: ToolRuntime,
) -> str:
    """列出指定任务的执行日志（按 owner 隔离）。"""
    user_id = _resolve_user(runtime)
    if not user_id:
        return "无法获取用户信息"

    limit = min(max(int(limit), 1), LIST_MAX_LIMIT)
    offset = max(int(offset), 0)

    try:
        async with pg_manager.get_async_session_context() as session:
            repo = ScheduleRepository(session)
            existing = await repo.get_by_id(schedule_id, user_id)
            if existing is None:
                return "未找到该任务"
            logs = await repo.get_logs_by_schedule_id(schedule_id, limit=limit, offset=offset)
        return _json_or_error([log.to_dict() for log in logs], "未找到该任务")
    except Exception as e:
        logger.error(f"list_schedule_logs 工具异常: {e}")
        return f"查询失败: {e}"


# ========== trigger_schedule ==========


class TriggerScheduleInput(BaseModel):
    """立即触发一次定时任务。"""

    schedule_id: str


@tool(
    category="schedules",
    tags=["触发定时任务"],
    display_name="手动触发定时任务",
    description="""立即手动触发一次定时任务运行，不影响原有 cron 周期；即使任务处于禁用状态也可触发。""",
    args_schema=TriggerScheduleInput,
)  # type: ignore[misc]
async def trigger_schedule(schedule_id: str, runtime: ToolRuntime) -> str:  # type: ignore[no-redef]
    """立即触发一次定时任务；不影响原 cron 周期。

    即使 schedule 处于 disabled 状态也可触发（与现有 manual_trigger_schedule 行为一致）。
    """
    user_id = _resolve_user(runtime)
    if not user_id:
        return "无法获取用户信息"

    try:
        async with pg_manager.get_async_session_context() as session:
            repo = ScheduleRepository(session)
            schedule = await repo.get_by_id(schedule_id, user_id)
            if schedule is None:
                return "未找到该任务"

            service = ScheduleService()
            thread_id, run_id = await service.manual_trigger_schedule(schedule=schedule, db=session)
        return _json_or_error({"thread_id": thread_id, "run_id": run_id, "schedule_id": schedule_id}, "触发失败")
    except Exception as e:
        logger.error(f"trigger_schedule 工具异常: {e}")
        return f"触发失败: {e}"
