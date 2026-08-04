"""
Integration tests for conversation share endpoints.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_share_requires_authentication(test_client):
    assert (await test_client.get("/api/chat/thread/x/share")).status_code == 401
    assert (await test_client.post("/api/chat/thread/x/share", json={"expires_days": 7})).status_code == 401


async def test_share_full_flow(test_client, admin_headers, standard_user):
    # 1. 拥有者创建线程
    agents_resp = await test_client.get("/api/agent", headers=standard_user["headers"])
    assert agents_resp.status_code == 200, agents_resp.text
    agents = agents_resp.json().get("agents", [])
    if not agents:
        pytest.skip("No agents available for share integration tests.")
    agent_id = agents[0].get("agent_id") or agents[0].get("slug")
    if not agent_id:
        pytest.skip("Agent payload missing slug field.")

    create_resp = await test_client.post(
        "/api/chat/thread",
        json={
            "agent_id": agent_id,
            "title": f"share-test-{uuid.uuid4().hex[:8]}",
            "metadata": {},
        },
        headers=standard_user["headers"],
    )
    assert create_resp.status_code == 200, create_resp.text
    thread_id = create_resp.json().get("thread_id") or create_resp.json().get("id")
    assert thread_id

    # 2. 创建分享
    share_resp = await test_client.post(
        f"/api/chat/thread/{thread_id}/share",
        json={"expires_days": 7},
        headers=standard_user["headers"],
    )
    assert share_resp.status_code == 200, share_resp.text
    share_payload = share_resp.json()
    token = share_payload.get("token")
    assert token

    # 3. 幂等复用
    repeat_resp = await test_client.post(
        f"/api/chat/thread/{thread_id}/share",
        json={"expires_days": 30},
        headers=standard_user["headers"],
    )
    assert repeat_resp.status_code == 200, repeat_resp.text
    assert repeat_resp.json()["token"] == token

    # 4. 匿名访问历史
    anon_resp = await test_client.get(f"/api/share/{thread_id}?token={token}")
    assert anon_resp.status_code == 200, anon_resp.text
    payload = anon_resp.json()
    assert payload["thread_id"] == thread_id
    assert "uid" not in payload
    assert isinstance(payload["history"], list)

    # 5. 错误 token → 404
    bad_resp = await test_client.get(f"/api/share/{thread_id}?token=invalid")
    assert bad_resp.status_code == 404

    # 6. 撤销后匿名访问 → 404
    revoke_resp = await test_client.delete(
        f"/api/chat/thread/{thread_id}/share",
        headers=standard_user["headers"],
    )
    assert revoke_resp.status_code == 200, revoke_resp.text

    revoked_resp = await test_client.get(f"/api/share/{thread_id}?token={token}")
    assert revoked_resp.status_code == 404


async def test_share_rejects_non_owner(test_client, admin_headers, standard_user):
    agents_resp = await test_client.get("/api/agent", headers=standard_user["headers"])
    assert agents_resp.status_code == 200, agents_resp.text
    agents = agents_resp.json().get("agents", [])
    if not agents:
        pytest.skip("No agents available for share integration tests.")
    agent_id = agents[0].get("agent_id") or agents[0].get("slug")
    if not agent_id:
        pytest.skip("Agent payload missing slug field.")

    create_resp = await test_client.post(
        "/api/chat/thread",
        json={
            "agent_id": agent_id,
            "title": f"share-non-owner-{uuid.uuid4().hex[:8]}",
            "metadata": {},
        },
        headers=standard_user["headers"],
    )
    assert create_resp.status_code == 200, create_resp.text
    thread_id = create_resp.json().get("thread_id") or create_resp.json().get("id")
    assert thread_id

    # admin 不是该会话拥有者 → 404
    non_owner_resp = await test_client.post(
        f"/api/chat/thread/{thread_id}/share",
        json={"expires_days": 7},
        headers=admin_headers,
    )
    assert non_owner_resp.status_code == 404

    # 无 token 匿名请求创建分享 → 401（未登录）
    anon_resp = await test_client.post(
        f"/api/chat/thread/{thread_id}/share",
        json={"expires_days": 7},
    )
    assert anon_resp.status_code == 401
