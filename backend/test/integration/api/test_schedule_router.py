"""schedule_router 集成测试 — 路由层 agent 归属校验（按 agent_slug）。

测试场景：
1. 普通用户绑定非自己的 agent_slug 创建 schedule 应被 403 拒绝；
2. 普通用户 update 时把 agent_slug 切换为他人拥有的应被 403 拒绝；
3. admin 创建 schedule 时绑定任何 agent 都应成功。
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _get_agent_slug(test_client, headers: dict) -> str:
    """通过当前 agents API 创建一个测试用 agent，返回其 slug。"""
    name = f"pytest_agent_{uuid.uuid4().hex[:6]}"
    res = await test_client.post(
        "/api/agent",
        json={"name": name, "backend_id": "ChatbotAgent"},
        headers=headers,
    )
    assert res.status_code == 200, f"创建测试 agent 失败: {res.text}"
    return res.json()["agent"]["slug"]


async def test_create_schedule_rejects_foreign_agent(test_client, admin_headers, standard_user):
    """普通用户绑定非自己的 agent_slug 创建 schedule 应被 403 拒绝。"""
    user_headers = standard_user["headers"]

    # admin 创建一个 agent（admin-owned）
    admin_owned_slug = await _get_agent_slug(test_client, admin_headers)

    # 普通用户尝试绑定 admin 拥有的 agent
    res = await test_client.post(
        "/api/schedules",
        json={
            "name": "越权测试",
            "agent_slug": admin_owned_slug,
            "cron_expr": "0 9 * * *",
            "timezone": "Asia/Shanghai",
            "query": "hi",
        },
        headers=user_headers,
    )
    assert res.status_code == 403, res.text
    assert "无权" in res.json()["detail"]


async def test_update_schedule_rejects_foreign_agent(test_client, admin_headers, standard_user):
    """普通用户 update 时把 agent_slug 切换为他人拥有的应被 403 拒绝。

    update_schedule_route 中 agent_slug 校验在 schedule 校验之前触发，
    即 schedule_id 可以是任意值（包括不存在的），但 agent_slug 必须是他人拥有的以触发 403。
    """
    user_headers = standard_user["headers"]

    # admin 创建一个 agent（admin-owned）
    admin_slug = await _get_agent_slug(test_client, admin_headers)

    # user 尝试 update schedule 把 agent_slug 切换为 admin 的
    # agent_slug 校验在 schedule 校验之前 → 即使 schedule 不存在也返回 403
    upd_res = await test_client.put(
        "/api/schedules/any-schedule-id-placeholder",
        json={"agent_slug": admin_slug},
        headers=user_headers,
    )
    assert upd_res.status_code == 403, upd_res.text


async def test_admin_can_bind_any_agent_when_creating_schedule(test_client, admin_headers):
    """admin 创建 schedule 时绑定任何 agent 都应成功。"""
    slug = await _get_agent_slug(test_client, admin_headers)

    res = await test_client.post(
        "/api/schedules",
        json={
            "name": "admin 任务",
            "agent_slug": slug,
            "cron_expr": "0 9 * * *",
            "timezone": "Asia/Shanghai",
            "query": "hi",
        },
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
