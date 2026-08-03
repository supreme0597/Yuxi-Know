"""模型供应商路由权限矩阵测试。"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _unique_id() -> str:
    return f"pytest_perm_{uuid.uuid4().hex[:8]}"


async def test_normal_user_list_sees_only_visible_providers(test_client, admin_headers, standard_user):
    """标准用户创建私有 provider 后，admin 看不到这个用户的私有 provider。"""
    pid = _unique_id()
    try:
        # 用标准用户创建私有 provider
        resp = await test_client.post(
            "/api/system/model-providers",
            json={
                "provider_id": pid,
                "display_name": pid,
                "provider_type": "openai",
                "base_url": "https://api.example.com/v1",
                "capabilities": ["chat"],
                "enabled_models": [
                    {"id": "demo", "display_name": "Demo", "type": "chat", "source": "manual"}
                ],
            },
            headers=standard_user["headers"],
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["share_config"]["access_level"] == "user"

        # admin 拉列表（admin 角色不是 superadmin，所以 user 级别 provider 不可见）
        admin_resp = await test_client.get(
            "/api/system/model-providers", headers=admin_headers
        )
        assert admin_resp.status_code == 200
        admin_ids = {p["provider_id"] for p in admin_resp.json()["data"]}
        assert pid not in admin_ids
    finally:
        await test_client.delete(f"/api/system/model-providers/{pid}", headers=standard_user["headers"])


async def test_normal_user_cannot_edit_others_provider(test_client, admin_headers, standard_user):
    """标准用户不可编辑 admin 创建的 provider（404，因为不可见）。"""
    pid = _unique_id()
    try:
        c_resp = await test_client.post(
            "/api/system/model-providers",
            json={
                "provider_id": pid,
                "display_name": pid,
                "provider_type": "openai",
                "base_url": "https://api.example.com/v1",
                "capabilities": ["chat"],
                "enabled_models": [],
            },
            headers=admin_headers,
        )
        assert c_resp.status_code == 200, c_resp.text

        resp = await test_client.put(
            f"/api/system/model-providers/{pid}",
            json={"display_name": "Hacked"},
            headers=standard_user["headers"],
        )
        # 不可见 → 404
        assert resp.status_code == 404
    finally:
        await test_client.delete(f"/api/system/model-providers/{pid}", headers=admin_headers)


async def test_cache_refresh_admin_only(test_client, standard_user):
    """缓存刷新端点保留 admin only。"""
    resp = await test_client.post(
        "/api/system/model-providers/models/cache/refresh",
        headers=standard_user["headers"],
    )
    assert resp.status_code == 403


async def test_models_v2_filters_by_visibility(test_client, admin_headers, standard_user):
    """v2 模型列表按可见性过滤。"""
    pid = _unique_id()
    try:
        await test_client.post(
            "/api/system/model-providers",
            json={
                "provider_id": pid,
                "display_name": pid,
                "provider_type": "openai",
                "base_url": "https://api.example.com/v1",
                "capabilities": ["chat"],
                "enabled_models": [
                    {"id": "demo", "display_name": "Demo", "type": "chat", "source": "manual"}
                ],
                "share_config": {"access_level": "user", "department_ids": [], "user_uids": [standard_user["user"]["uid"]]},
            },
            headers=admin_headers,
        )
        resp = await test_client.get(
            "/api/system/model-providers/models/v2?model_type=chat",
            headers=standard_user["headers"],
        )
        assert resp.status_code == 200
        assert pid in resp.json()["data"]
    finally:
        await test_client.delete(f"/api/system/model-providers/{pid}", headers=admin_headers)
