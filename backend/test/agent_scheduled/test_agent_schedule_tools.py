"""Tests for yuxi.agents.toolkits.schedules.tools — 8 个 LangGraph @tool。

覆盖 list_agents / list_schedules / get_schedule / create_schedule /
update_schedule / delete_schedule / list_schedule_logs / trigger_schedule。

所有依赖（pg_manager / ScheduleRepository / AgentRepository / UserRepository /
ScheduleService）通过 monkeypatch 注入 fake，避免真实数据库。

权限模型（与 router 一致）：
  - tools 不做任何角色/权限晋升，仅按 runtime.context.uid 操作"自己的"任务。
  - agent 绑定通过 AgentRepository.get_visible_by_slug 复用既有可见性判定
    （内部走 user_can_access_agent）；可用智能体清单由 list_agents 提供。
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from yuxi.agents.toolkits.schedules import tools


pytestmark = pytest.mark.asyncio


# ========== fake session / repo factory ==========


class _FakeRepo:
    def __init__(self, methods: dict[str, AsyncMock]):
        self._methods = methods
        for name, m in methods.items():
            setattr(self, name, m)


def _make_runtime(uid: str | None = "u1") -> SimpleNamespace:
    return SimpleNamespace(context=SimpleNamespace(uid=uid))


def _patch_session(monkeypatch, repo: _FakeRepo) -> None:
    @asynccontextmanager
    async def _ctx():
        yield MagicMock()

    def _factory(_session):
        return repo

    monkeypatch.setattr(tools, "pg_manager", MagicMock(get_async_session_context=_ctx))
    monkeypatch.setattr(tools, "ScheduleRepository", _factory)


def _patch_agent_resolution(
    monkeypatch, *, visible_agent=None, visible_agents: list | None = None
) -> tuple[_FakeRepo, _FakeRepo]:
    """stub UserRepository + AgentRepository（get_visible_by_slug / list_visible），返回 (user_repo, agent_repo)。"""
    user_repo = _FakeRepo(
        {
            "get_by_uid_with_db": AsyncMock(
                return_value=SimpleNamespace(uid="u1", role="user", department_id=None)
            )
        }
    )
    agent_methods: dict[str, AsyncMock] = {"get_visible_by_slug": AsyncMock(return_value=visible_agent)}
    if visible_agents is not None:
        agent_methods["list_visible"] = AsyncMock(return_value=visible_agents)
    agent_repo = _FakeRepo(agent_methods)
    monkeypatch.setattr(tools, "UserRepository", lambda: user_repo)
    monkeypatch.setattr(tools, "AgentRepository", lambda _s: agent_repo)
    return user_repo, agent_repo


def _patch_pg(monkeypatch) -> None:
    @asynccontextmanager
    async def _ctx():
        yield MagicMock()

    monkeypatch.setattr(tools, "pg_manager", MagicMock(get_async_session_context=_ctx))


# ========== list_agents ==========


async def test_list_agents_returns_visible_agents(monkeypatch) -> None:
    visible = [SimpleNamespace(slug="agent-42", name="数据分析助手", description="d", is_subagent=False)]
    user_repo, agent_repo = _patch_agent_resolution(monkeypatch, visible_agents=visible)
    _patch_pg(monkeypatch)

    result = await tools.list_agents.coroutine(  # type: ignore[attr-defined]
        dummy="",
        runtime=_make_runtime(uid="u1"),
    )

    payload = json.loads(result)
    assert payload[0]["slug"] == "agent-42"
    assert payload[0]["name"] == "数据分析助手"
    user_repo._methods["get_by_uid_with_db"].assert_awaited_once()
    agent_repo._methods["list_visible"].assert_awaited_once()


async def test_list_agents_returns_error_when_uid_missing() -> None:
    result = await tools.list_agents.coroutine(  # type: ignore[attr-defined]
        dummy="",
        runtime=_make_runtime(uid=None),
    )
    assert result == "无法获取用户信息"


# ========== list_schedules ==========


async def test_list_schedules_filters_by_current_user(monkeypatch) -> None:
    row = SimpleNamespace(
        id="s1",
        uid="u1",
        name="n1",
        cron_expr="*/5 * * * *",
        timezone="UTC",
        enabled=True,
        next_run_at=None,
        agent_slug="a1",
    )
    repo = _FakeRepo({"list_schedules": AsyncMock(return_value=[row])})
    _patch_session(monkeypatch, repo)

    result = await tools.list_schedules.coroutine(  # type: ignore[attr-defined]
        limit=20,
        offset=0,
        runtime=_make_runtime(uid="u1"),
    )

    repo._methods["list_schedules"].assert_awaited_once()
    kwargs = repo._methods["list_schedules"].await_args.kwargs
    assert kwargs["uid"] == "u1"
    assert kwargs["limit"] == 20
    assert kwargs["offset"] == 0
    payload = json.loads(result)
    assert payload[0]["id"] == "s1"


async def test_list_schedules_clamps_limit(monkeypatch) -> None:
    repo = _FakeRepo({"list_schedules": AsyncMock(return_value=[])})
    _patch_session(monkeypatch, repo)

    await tools.list_schedules.coroutine(  # type: ignore[attr-defined]
        limit=9999,
        offset=0,
        runtime=_make_runtime(uid="u1"),
    )

    kwargs = repo._methods["list_schedules"].await_args.kwargs
    assert kwargs["limit"] == 100  # LIST_MAX_LIMIT


async def test_list_schedules_returns_error_when_uid_missing(monkeypatch) -> None:
    repo = _FakeRepo({"list_schedules": AsyncMock(return_value=[])})
    _patch_session(monkeypatch, repo)

    result = await tools.list_schedules.coroutine(  # type: ignore[attr-defined]
        limit=20,
        offset=0,
        runtime=_make_runtime(uid=None),
    )

    assert result == "无法获取用户信息"
    repo._methods["list_schedules"].assert_not_awaited()


# ========== get_schedule ==========


async def test_get_schedule_returns_row_for_owner(monkeypatch) -> None:
    fake_row = SimpleNamespace(id="s9", uid="u1", to_dict=lambda: {"id": "s9"})
    repo = _FakeRepo({"get_by_id": AsyncMock(return_value=fake_row)})
    _patch_session(monkeypatch, repo)

    result = await tools.get_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="s9",
        runtime=_make_runtime(uid="u1"),
    )

    repo._methods["get_by_id"].assert_awaited_once_with("s9", "u1")
    payload = json.loads(result)
    assert payload["id"] == "s9"


async def test_get_schedule_returns_friendly_error_for_other_user(monkeypatch) -> None:
    # 非 owner 时 SQL 层直接返回 None（get_by_id 带 uid 过滤）
    repo = _FakeRepo({"get_by_id": AsyncMock(return_value=None)})
    _patch_session(monkeypatch, repo)

    result = await tools.get_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="s9",
        runtime=_make_runtime(uid="u2"),
    )

    assert result == "未找到该任务"


# ========== create_schedule ==========


async def test_create_schedule_succeeds_when_agent_visible(monkeypatch) -> None:
    fake_schedule = SimpleNamespace(id="new-1", to_dict=lambda: {"id": "new-1", "name": "demo"})
    sched_repo = _FakeRepo({"create_schedule": AsyncMock(return_value=fake_schedule)})
    _, agent_repo = _patch_agent_resolution(
        monkeypatch, visible_agent=SimpleNamespace(slug="agent-42", enabled=True)
    )
    _patch_pg(monkeypatch)
    monkeypatch.setattr(tools, "ScheduleRepository", lambda _s: sched_repo)

    result = await tools.create_schedule.coroutine(  # type: ignore[attr-defined]
        name="demo",
        description=None,
        agent_slug="agent-42",
        cron_expr="0 * * * *",
        timezone="Asia/Shanghai",
        query="hi",
        enabled=True,
        runtime=_make_runtime(uid="u1"),
    )

    payload = json.loads(result)
    assert payload["id"] == "new-1"
    agent_repo._methods["get_visible_by_slug"].assert_awaited_once()
    sched_repo._methods["create_schedule"].assert_awaited_once()


async def test_create_schedule_rejects_invisible_or_missing_agent(monkeypatch) -> None:
    sched_repo = _FakeRepo({"create_schedule": AsyncMock()})
    _patch_agent_resolution(monkeypatch, visible_agent=None)
    _patch_pg(monkeypatch)
    monkeypatch.setattr(tools, "ScheduleRepository", lambda _s: sched_repo)

    result = await tools.create_schedule.coroutine(  # type: ignore[attr-defined]
        name="demo",
        description=None,
        agent_slug="agent-42",
        cron_expr="0 * * * *",
        timezone="Asia/Shanghai",
        query="hi",
        enabled=True,
        runtime=_make_runtime(uid="u1"),
    )

    assert result == "指定的 Agent 不存在或无权使用: agent-42"
    sched_repo._methods["create_schedule"].assert_not_awaited()


# ========== update_schedule ==========


async def test_update_schedule_rejects_invisible_or_missing_agent(monkeypatch) -> None:
    sched_repo = _FakeRepo({"get_by_id": AsyncMock(return_value=SimpleNamespace(id="sx", uid="u1"))})
    _patch_agent_resolution(monkeypatch, visible_agent=None)
    _patch_pg(monkeypatch)
    monkeypatch.setattr(tools, "ScheduleRepository", lambda _s: sched_repo)

    result = await tools.update_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        name=None,
        description=None,
        agent_slug="agent-99",
        cron_expr=None,
        timezone=None,
        query=None,
        enabled=None,
        runtime=_make_runtime(uid="u1"),
    )

    assert result == "指定的 Agent 不存在或无权使用: agent-99"
    sched_repo._methods["get_by_id"].assert_not_awaited()  # agent 校验在 update 前


async def test_update_schedule_succeeds_when_owner_and_agent_visible(monkeypatch) -> None:
    existing = SimpleNamespace(id="sx", uid="u1", to_dict=lambda: {"id": "sx"})
    updated = SimpleNamespace(id="sx", name="new", to_dict=lambda: {"id": "sx", "name": "new"})
    sched_repo = _FakeRepo(
        {
            "get_by_id": AsyncMock(return_value=existing),
            "update_schedule": AsyncMock(return_value=updated),
        }
    )
    _, agent_repo = _patch_agent_resolution(
        monkeypatch, visible_agent=SimpleNamespace(slug="agent-42", enabled=True)
    )
    _patch_pg(monkeypatch)
    monkeypatch.setattr(tools, "ScheduleRepository", lambda _s: sched_repo)

    result = await tools.update_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        name="new",
        description=None,
        agent_slug="agent-42",
        cron_expr=None,
        timezone=None,
        query=None,
        enabled=None,
        runtime=_make_runtime(uid="u1"),
    )

    payload = json.loads(result)
    assert payload["name"] == "new"
    agent_repo._methods["get_visible_by_slug"].assert_awaited_once()
    sched_repo._methods["update_schedule"].assert_awaited_once()


async def test_update_schedule_skips_agent_check_when_slug_not_provided(monkeypatch) -> None:
    """update_schedule 若 agent_slug=None，应跳过 agent 校验。"""
    existing = SimpleNamespace(id="sx", uid="u1", to_dict=lambda: {"id": "sx"})
    updated = SimpleNamespace(id="sx", name="x", to_dict=lambda: {"id": "sx", "name": "x"})
    sched_repo = _FakeRepo(
        {
            "get_by_id": AsyncMock(return_value=existing),
            "update_schedule": AsyncMock(return_value=updated),
        }
    )
    agent_repo = _FakeRepo({"get_visible_by_slug": AsyncMock()})
    _patch_pg(monkeypatch)
    monkeypatch.setattr(tools, "ScheduleRepository", lambda _s: sched_repo)
    monkeypatch.setattr(tools, "AgentRepository", lambda _s: agent_repo)

    result = await tools.update_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        name="x",
        description=None,
        agent_slug=None,
        cron_expr=None,
        timezone=None,
        query=None,
        enabled=None,
        runtime=_make_runtime(uid="u1"),
    )

    assert json.loads(result)["name"] == "x"
    agent_repo._methods["get_visible_by_slug"].assert_not_awaited()


async def test_update_schedule_enable_uses_existing_cron(monkeypatch) -> None:
    """仅传 enabled=True 时应使用已有任务的 cron/时区重算 next_run_at，而非要求重传。"""
    existing = SimpleNamespace(
        id="sx",
        uid="u1",
        cron_expr="*/5 * * * *",
        timezone="Asia/Shanghai",
        enabled=False,
        to_dict=lambda: {"id": "sx", "enabled": True, "next_run_at": "2099-01-01T00:00:00Z"},
    )
    updated = SimpleNamespace(
        id="sx",
        enabled=True,
        to_dict=lambda: {"id": "sx", "enabled": True, "next_run_at": "2099-01-01T00:00:00Z"},
    )
    sched_repo = _FakeRepo(
        {
            "get_by_id": AsyncMock(return_value=existing),
            "update_schedule": AsyncMock(return_value=updated),
        }
    )
    agent_repo = _FakeRepo({"get_visible_by_slug": AsyncMock()})
    _patch_pg(monkeypatch)
    monkeypatch.setattr(tools, "ScheduleRepository", lambda _s: sched_repo)
    monkeypatch.setattr(tools, "AgentRepository", lambda _s: agent_repo)
    monkeypatch.setattr(tools, "compute_next_run", lambda _c, _t: "2099-01-01T00:00:00Z")

    result = await tools.update_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        name=None,
        description=None,
        agent_slug=None,
        cron_expr=None,
        timezone=None,
        query=None,
        enabled=True,
        runtime=_make_runtime(uid="u1"),
    )

    payload = json.loads(result)
    assert payload["enabled"] is True
    call_args = sched_repo._methods["update_schedule"].call_args
    # update_schedule(self, schedule_id, data)；第 2 个位置参数是 data
    update_data = call_args.args[1]
    # 仅传 enabled=True 时应用已有 cron/时区重算 next_run_at
    assert update_data["next_run_at"] == "2099-01-01T00:00:00Z"
    # cron_expr 未被本次更新覆盖（PATCH 语义：未提供的字段保持原值）
    assert "cron_expr" not in update_data


# ========== delete_schedule ==========


async def test_delete_schedule_succeeds_for_owner(monkeypatch) -> None:
    repo = _FakeRepo(
        {
            "get_by_id": AsyncMock(return_value=SimpleNamespace(id="sx", uid="u1")),
            "delete_schedule": AsyncMock(return_value=True),
        }
    )
    _patch_session(monkeypatch, repo)

    result = await tools.delete_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        runtime=_make_runtime(uid="u1"),
    )

    payload = json.loads(result)
    assert payload["deleted"] is True
    repo._methods["delete_schedule"].assert_awaited_once_with("sx")


async def test_delete_schedule_returns_friendly_error_for_other_user(monkeypatch) -> None:
    repo = _FakeRepo(
        {
            "get_by_id": AsyncMock(return_value=None),
            "delete_schedule": AsyncMock(return_value=False),
        }
    )
    _patch_session(monkeypatch, repo)

    result = await tools.delete_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        runtime=_make_runtime(uid="u2"),
    )

    assert result == "未找到该任务"
    repo._methods["delete_schedule"].assert_not_awaited()


# ========== list_schedule_logs ==========


async def test_list_schedule_logs_returns_logs_for_owner(monkeypatch) -> None:
    fake_logs = [SimpleNamespace(id="l1", to_dict=lambda: {"id": "l1"})]
    repo = _FakeRepo(
        {
            "get_by_id": AsyncMock(return_value=SimpleNamespace(id="sx", uid="u1")),
            "get_logs_by_schedule_id": AsyncMock(return_value=fake_logs),
        }
    )
    _patch_session(monkeypatch, repo)

    result = await tools.list_schedule_logs.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        limit=20,
        offset=0,
        runtime=_make_runtime(uid="u1"),
    )

    payload = json.loads(result)
    assert payload[0]["id"] == "l1"
    repo._methods["get_logs_by_schedule_id"].assert_awaited_once()


async def test_list_schedule_logs_returns_error_for_other_user(monkeypatch) -> None:
    """owner 不匹配时 SQL 层返回 None，工具返回"未找到该任务"，不会查询日志。"""
    repo = _FakeRepo({"get_by_id": AsyncMock(return_value=None)})
    _patch_session(monkeypatch, repo)

    result = await tools.list_schedule_logs.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        limit=20,
        offset=0,
        runtime=_make_runtime(uid="u2"),
    )

    assert result == "未找到该任务"


# ========== trigger_schedule ==========


async def test_trigger_schedule_succeeds_for_owner(monkeypatch) -> None:
    sched_repo = _FakeRepo(
        {"get_by_id": AsyncMock(return_value=SimpleNamespace(id="sx", uid="u1"))}
    )
    _patch_pg(monkeypatch)
    monkeypatch.setattr(tools, "ScheduleRepository", lambda _s: sched_repo)

    class _FakeService:
        async def manual_trigger_schedule(self, *, schedule, db):
            return ("thread-1", "run-1")

    monkeypatch.setattr(tools, "ScheduleService", _FakeService)

    result = await tools.trigger_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        runtime=_make_runtime(uid="u1"),
    )

    payload = json.loads(result)
    assert payload["thread_id"] == "thread-1"
    assert payload["run_id"] == "run-1"


async def test_trigger_schedule_returns_friendly_error_for_other_user(monkeypatch) -> None:
    sched_repo = _FakeRepo({"get_by_id": AsyncMock(return_value=None)})
    _patch_pg(monkeypatch)
    monkeypatch.setattr(tools, "ScheduleRepository", lambda _s: sched_repo)

    result = await tools.trigger_schedule.coroutine(  # type: ignore[attr-defined]
        schedule_id="sx",
        runtime=_make_runtime(uid="u2"),
    )

    assert result == "未找到该任务"
