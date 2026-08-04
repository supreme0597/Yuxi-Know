import pytest

from server.routers import model_provider_router
from server.routers.model_provider_router import ModelProviderPayload


def test_model_provider_payload_accepts_embedding_and_rerank_urls():
    payload = ModelProviderPayload(
        provider_id="mixed-provider",
        display_name="Mixed Provider",
        base_url="https://api.example.com/v1",
        embedding_base_url="https://api.example.com/v1/embeddings",
        rerank_base_url="https://api.example.com/v1/rerank",
        capabilities=["chat", "embedding", "rerank"],
    )

    data = payload.model_dump(exclude_none=True)

    assert data["embedding_base_url"] == "https://api.example.com/v1/embeddings"
    assert data["rerank_base_url"] == "https://api.example.com/v1/rerank"


@pytest.mark.asyncio
async def test_update_provider_commits_before_refreshing_cache(monkeypatch):
    calls = []

    class Db:
        async def commit(self):
            calls.append("commit")

    class User:
        username = "admin"
        uid = "admin-uid"

    class Provider:
        def to_dict(self, *, include_api_key=False):
            return {"provider_id": "alibaba"}

        is_enabled = True
        api_key = "sk-test"
        api_key_env = None

    async def fake_get_visible(db, provider_id, user):
        calls.append("visible")
        return Provider()

    async def fake_update_provider_config(db, provider_id, data, current_user):
        calls.append("update")
        return Provider()

    async def fake_refresh_model_cache():
        calls.append("refresh")

    monkeypatch.setattr(model_provider_router, "get_visible_model_provider", fake_get_visible)
    monkeypatch.setattr(model_provider_router, "user_can_manage_provider", lambda *a, **k: True)
    monkeypatch.setattr(model_provider_router, "user_can_access_provider", lambda *a, **k: True)
    monkeypatch.setattr(model_provider_router, "update_provider_config", fake_update_provider_config)
    monkeypatch.setattr(model_provider_router, "_refresh_model_cache", fake_refresh_model_cache)

    result = await model_provider_router.update_provider(
        "alibaba",
        ModelProviderPayload(enabled_models=[]),
        current_user=User(),
        db=Db(),
    )

    assert result == {
        "success": True,
        "data": {
            "provider_id": "alibaba",
            "credential_status": "ok",
            "can_manage": True,
            "can_view": True,
        },
    }
    assert calls == ["visible", "update", "commit", "refresh"]
