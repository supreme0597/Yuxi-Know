"""模型供应商删除保护 e2e。"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]


async def _create_provider(test_client, headers, pid: str) -> None:
    response = await test_client.post(
        "/api/system/model-providers",
        json={
            "provider_id": pid,
            "display_name": pid,
            "provider_type": "openai",
            "base_url": "https://api.example.com/v1",
            "capabilities": ["chat", "embedding"],
            "enabled_models": [
                {"id": "embed", "display_name": "Embed", "type": "embedding",
                 "source": "manual", "dimension": 768, "batch_size": 32},
            ],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text


async def _delete_provider(test_client, headers, pid: str) -> int:
    resp = await test_client.delete(f"/api/system/model-providers/{pid}", headers=headers)
    return resp.status_code


async def test_delete_provider_referenced_by_kb_returns_409(test_client, admin_headers):
    """被知识库引用时删除应返回 409。"""
    pid = f"pytest_e2e_{uuid.uuid4().hex[:8]}"
    await _create_provider(test_client, admin_headers, pid)
    try:
        kb_resp = await test_client.post(
            "/api/knowledge/databases",
            json={
                "database_name": f"pytest_kb_{uuid.uuid4().hex[:8]}",
                "description": "e2e",
                "embedding_model_spec": f"{pid}:embed",
                "kb_type": "milvus",
                "additional_params": {},
            },
            headers=admin_headers,
        )
        if kb_resp.status_code != 200:
            pytest.skip(f"Cannot create knowledge base in this environment: {kb_resp.text}")
        kb_id = kb_resp.json()["kb_id"]

        try:
            status = await _delete_provider(test_client, admin_headers, pid)
            assert status == 409, f"Expected 409, got {status}"

            # 第二次删除应仍返回 409，引用列表里能看到知识库引用
            resp = await test_client.delete(
                f"/api/system/model-providers/{pid}", headers=admin_headers
            )
            assert resp.status_code == 409
            detail = resp.json().get("detail", {})
            assert "references" in detail or "knowledge" in str(detail).lower()
        finally:
            await test_client.delete(f"/api/knowledge/databases/{kb_id}", headers=admin_headers)
    finally:
        await _delete_provider(test_client, admin_headers, pid)


async def test_delete_builtin_provider_rejected(test_client, admin_headers):
    """内置 provider 永远不能删（如果环境中有内置 provider）。"""
    list_resp = await test_client.get("/api/system/model-providers", headers=admin_headers)
    assert list_resp.status_code == 200
    builtins = [p for p in list_resp.json()["data"] if p.get("is_builtin")]
    if not builtins:
        pytest.skip("No builtin provider in this environment")
    target = builtins[0]["provider_id"]
    resp = await test_client.delete(
        f"/api/system/model-providers/{target}", headers=admin_headers
    )
    assert resp.status_code == 409
