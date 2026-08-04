import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from yuxi.models.providers.builtin import BUILTIN_PROVIDERS
from yuxi.models.providers.service import (
    check_credential_status,
    _normalize_payload,
    _normalize_remote_model,
    fetch_remote_models,
)
from yuxi.storage.postgres.models_business import ModelProvider, User


def test_normalize_payload_accepts_enabled_chat_model():
    payload = _normalize_payload(
        {
            "provider_id": "openrouter-local",
            "display_name": "OpenRouter Local",
            "base_url": "https://openrouter.ai/api/v1",
            "enabled_models": [{"id": "anthropic/claude-sonnet-4.5", "type": "chat"}],
        }
    )

    assert payload["provider_id"] == "openrouter-local"
    assert payload["provider_type"] == "openai"
    assert "models_endpoint" not in payload
    assert "embedding_models_endpoint" not in payload
    assert payload["enabled_models"][0]["display_name"] == "anthropic/claude-sonnet-4.5"


def test_normalize_payload_accepts_anthropic_provider_type():
    payload = _normalize_payload(
        {
            "provider_id": "xiaomi-token-plan",
            "display_name": "Xiaomi Token Plan",
            "provider_type": "anthropic",
            "base_url": "https://token-plan-cn.xiaomimimo.com/anthropic",
            "capabilities": ["chat"],
            "enabled_models": [{"id": "mimo-v2.5-pro", "type": "chat", "source": "manual"}],
        }
    )

    assert payload["provider_type"] == "anthropic"
    assert payload["enabled_models"][0]["id"] == "mimo-v2.5-pro"


def test_normalize_payload_rejects_unknown_enabled_model_type():
    with pytest.raises(ValueError, match="type 必须是"):
        _normalize_payload(
            {
                "provider_id": "openrouter-local",
                "display_name": "OpenRouter Local",
                "base_url": "https://openrouter.ai/api/v1",
                "enabled_models": [{"id": "unknown-model", "type": "unknown"}],
            }
        )


def test_normalize_payload_allows_embedding_without_dimension():
    """embedding 模型的 dimension 是可选字段，不提供也不会报错。"""
    payload = _normalize_payload(
        {
            "provider_id": "embedding-local",
            "display_name": "Embedding Local",
            "base_url": "https://example.com/v1",
            "capabilities": ["embedding"],
            "embedding_base_url": "https://example.com/v1/embeddings",
            "enabled_models": [{"id": "text-embedding", "type": "embedding"}],
        }
    )
    assert payload["provider_id"] == "embedding-local"
    assert payload["enabled_models"][0].get("dimension") is None


def test_normalize_remote_model_preserves_detailed_model_config():
    model = _normalize_remote_model(
        {
            "id": "xiaomi/mimo-v2-omni",
            "name": "Xiaomi: MiMo-V2-Omni",
            "context_length": 262144,
            "architecture": {
                "input_modalities": ["text", "audio", "image", "video"],
                "output_modalities": ["text"],
            },
            "top_provider": {"max_completion_tokens": 65536},
            "supported_parameters": ["temperature", "tools"],
        }
    )

    assert model["id"] == "xiaomi/mimo-v2-omni"
    assert model["display_name"] == "Xiaomi: MiMo-V2-Omni"
    assert model["type"] == "chat"
    assert model["input_modalities"] == ["text", "audio", "image", "video"]
    assert model["max_completion_tokens"] == 65536
    assert model["raw_metadata"]["supported_parameters"] == ["temperature", "tools"]


def test_normalize_remote_model_uses_endpoint_model_type():
    model = _normalize_remote_model({"id": "BAAI/bge-m3", "object": "model"}, "embedding")

    assert model["id"] == "BAAI/bge-m3"
    assert model["type"] == "embedding"


@pytest.mark.asyncio
async def test_fetch_remote_models_loads_embedding_only_when_capability_enabled(monkeypatch):
    calls = []

    async def fake_fetch(client, provider, headers, endpoint, model_type):
        calls.append((endpoint, model_type))
        return [{"id": f"{model_type}-model", "type": model_type}]

    monkeypatch.setattr("yuxi.models.providers.service._fetch_models_from_endpoint", fake_fetch)

    class Provider:
        base_url = "https://example.com/v1"
        api_key = None
        api_key_env = None
        headers_json = {}
        capabilities = ["chat", "embedding", "rerank"]
        models_endpoint = "/models"
        embedding_models_endpoint = "/embeddings/models"
        rerank_models_endpoint = None

    models = await fetch_remote_models(Provider())

    assert calls == [("/models", "chat"), ("/embeddings/models", "embedding")]
    assert [model["type"] for model in models] == ["chat", "embedding"]


def test_normalize_payload_rejects_ollama_provider_type():
    with pytest.raises(ValueError, match="provider_type 必须是"):
        _normalize_payload(
            {
                "provider_id": "ollama-local",
                "display_name": "Ollama Local",
                "provider_type": "ollama",
                "base_url": "http://localhost:11434",
            }
        )


def test_builtin_provider_templates_default_to_openai_provider_type():
    assert len(BUILTIN_PROVIDERS) >= 16
    provider_types = {
        _normalize_payload(
            {
                "provider_id": provider["provider_id"],
                "display_name": provider["display_name"],
                "base_url": provider["base_url"],
                "provider_type": provider.get("provider_type"),
            }
        )["provider_type"]
        for provider in BUILTIN_PROVIDERS
    }
    assert provider_types == {"openai"}
    assert all("ollama" not in provider["provider_id"] for provider in BUILTIN_PROVIDERS)


def test_builtin_siliconflow_provider_includes_default_runnable_models():
    provider = next(item for item in BUILTIN_PROVIDERS if item["provider_id"] == "siliconflow-cn")
    models = {model["id"]: model for model in provider["enabled_models"]}

    assert provider["capabilities"] == ["chat", "embedding", "rerank"]
    assert provider["embedding_base_url"] == "https://api.siliconflow.cn/v1/embeddings"
    assert provider["rerank_base_url"] == "https://api.siliconflow.cn/v1/rerank"
    assert models["Pro/BAAI/bge-m3"]["type"] == "embedding"
    assert models["Pro/BAAI/bge-m3"]["dimension"] == 1024
    assert "base_url_override" not in models["Pro/BAAI/bge-m3"]
    assert models["Pro/BAAI/bge-reranker-v2-m3"]["type"] == "rerank"
    assert "base_url_override" not in models["Pro/BAAI/bge-reranker-v2-m3"]


def test_builtin_dashscope_provider_includes_default_embedding_and_rerank_models():
    provider = next(item for item in BUILTIN_PROVIDERS if item["provider_id"] == "alibaba")
    models = {model["id"]: model for model in provider["enabled_models"]}

    assert provider["capabilities"] == ["chat", "embedding", "rerank"]
    assert provider["embedding_base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    assert provider["rerank_base_url"] == "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"
    assert "embedding_models_endpoint" not in provider
    assert "rerank_models_endpoint" not in provider
    assert models["text-embedding-v4"]["type"] == "embedding"
    assert models["text-embedding-v4"]["dimension"] == 1024
    assert models["qwen3-rerank"]["type"] == "rerank"


def testcheck_credential_status_disabled_provider_always_ok():
    """未启用的 provider 无论凭证如何配置，状态始终为 ok。"""

    class Provider:
        is_enabled = False
        api_key = None
        api_key_env = None

    assert check_credential_status(Provider()) == "ok"


def testcheck_credential_status_direct_api_key_ok():
    """直接配置了 api_key 的启用 provider 状态为 ok。"""

    class Provider:
        is_enabled = True
        api_key = "sk-test"
        api_key_env = None

    assert check_credential_status(Provider()) == "ok"


def testcheck_credential_status_env_key_exists_ok(monkeypatch):
    """api_key_env 对应的环境变量存在时状态为 ok。"""
    monkeypatch.setenv("TEST_API_KEY", "exists")

    class Provider:
        is_enabled = True
        api_key = None
        api_key_env = "TEST_API_KEY"

    assert check_credential_status(Provider()) == "ok"


def testcheck_credential_status_env_key_missing_warning(monkeypatch):
    """api_key_env 对应的环境变量不存在时状态为 warning。"""
    monkeypatch.delenv("MISSING_KEY", raising=False)

    class Provider:
        is_enabled = True
        api_key = None
        api_key_env = "MISSING_KEY"

    assert check_credential_status(Provider()) == "warning"


def testcheck_credential_status_both_empty_warning():
    """api_key 和 api_key_env 都未配置时状态为 warning。"""

    class Provider:
        is_enabled = True
        api_key = None
        api_key_env = None

    assert check_credential_status(Provider()) == "warning"


# ==================== 手动添加模型 / source 字段 ====================


def test_normalize_payload_default_model_source_is_remote():
    """未显式指定 source 时，规范化后默认填入 remote，向后兼容旧数据。"""
    payload = _normalize_payload(
        {
            "provider_id": "openrouter-local",
            "display_name": "OpenRouter Local",
            "base_url": "https://openrouter.ai/api/v1",
            "enabled_models": [{"id": "anthropic/claude-sonnet-4.5", "type": "chat"}],
        }
    )

    assert payload["enabled_models"][0]["source"] == "remote"


def test_normalize_payload_accepts_manual_source():
    """source=manual 表示管理员手动添加的模型，规范化保留该标签。"""
    payload = _normalize_payload(
        {
            "provider_id": "custom-local",
            "display_name": "Custom Local",
            "base_url": "https://example.com/v1",
            "capabilities": ["chat"],
            "enabled_models": [{"id": "my-chat-model", "type": "chat", "source": "manual"}],
        }
    )

    assert payload["enabled_models"][0]["source"] == "manual"


def test_normalize_payload_rejects_invalid_source():
    """source 仅允许 manual 或 remote，其他取值视为非法。"""
    with pytest.raises(ValueError, match="source 必须是"):
        _normalize_payload(
            {
                "provider_id": "custom-local",
                "display_name": "Custom Local",
                "base_url": "https://example.com/v1",
                "enabled_models": [{"id": "x", "type": "chat", "source": "custom"}],
            }
        )


def test_normalize_payload_rejects_model_type_not_in_capabilities():
    """provider 仅声明 chat 能力时，不允许写入 embedding 类型的模型。"""
    with pytest.raises(ValueError, match="不在 provider 能力"):
        _normalize_payload(
            {
                "provider_id": "chat-only",
                "display_name": "Chat Only",
                "base_url": "https://example.com/v1",
                "capabilities": ["chat"],
                "enabled_models": [{"id": "rogue-embedding", "type": "embedding", "dimension": 1024}],
            }
        )


def test_normalize_payload_allows_model_type_within_capabilities():
    """provider 同时声明 chat + embedding 时，两类模型均可正常写入。"""
    payload = _normalize_payload(
        {
            "provider_id": "multi-cap",
            "display_name": "Multi Cap",
            "base_url": "https://example.com/v1",
            "capabilities": ["chat", "embedding"],
            "embedding_base_url": "https://example.com/v1/embeddings",
            "embedding_models_endpoint": "/embeddings/models",
            "enabled_models": [
                {"id": "chat-1", "type": "chat", "source": "manual"},
                {
                    "id": "embed-1",
                    "type": "embedding",
                    "source": "manual",
                    "dimension": 1024,
                },
            ],
        }
    )

    types = [model["type"] for model in payload["enabled_models"]]
    sources = [model["source"] for model in payload["enabled_models"]]
    assert types == ["chat", "embedding"]
    assert sources == ["manual", "manual"]


# ==================== update_provider_config 回归测试 ====================


def _user(uid: str, role: str = "user", department_id: int | None = 1) -> User:
    return User(
        username=uid,
        uid=uid,
        password_hash="x",
        role=role,
        department_id=department_id,
    )


def _provider(provider_id: str = "openai-test", created_by: str = "creator") -> ModelProvider:
    return ModelProvider(
        provider_id=provider_id,
        display_name="Test",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        capabilities=["chat"],
        enabled_models=[],
        created_by=created_by,
        share_config={"access_level": "global", "department_ids": [], "user_uids": []},
    )


@pytest.mark.asyncio
async def test_update_provider_config_writes_updated_by_uid(monkeypatch):
    """编辑保存供应商不应因未定义变量报错，updated_by 应记录当前操作用户的 uid。"""
    from unittest.mock import MagicMock

    from yuxi.models.providers import service
    from yuxi.models.providers.service import update_provider_config

    provider = _provider(created_by="u1")
    captured = {}

    async def fake_get(db, provider_id):
        return provider

    async def fake_update(db, provider, payload):
        captured["payload"] = payload
        return provider

    monkeypatch.setattr(service, "get_model_provider", fake_get)
    monkeypatch.setattr(service, "update_model_provider", fake_update)

    user = _user("u1")
    result = await update_provider_config(MagicMock(), provider.provider_id, {"display_name": "新名称"}, user)

    assert result is provider
    assert captured["payload"]["updated_by"] == "u1"


# ==================== user_can_use_model_spec 消费侧可见性 ====================


class _FakeModelInfo:
    def __init__(self, provider_id):
        self.provider_id = provider_id


@pytest.mark.asyncio
async def test_user_can_use_model_spec_allows_visible_provider(monkeypatch):
    """模型所属 provider 对用户可见时返回 True，缓存未命中时从 DB 计算并回填。"""
    from unittest.mock import MagicMock

    from yuxi.models.providers import repository
    from yuxi.models.providers.cache import model_cache, visibility_cache
    from yuxi.models.providers.service import user_can_use_model_spec

    async def fake_list(db, user):
        return [MagicMock(provider_id="shared-provider")]

    visibility_cache.invalidate()
    monkeypatch.setattr(model_cache, "get_model_info", lambda spec: _FakeModelInfo("shared-provider"))
    monkeypatch.setattr(repository, "list_visible_model_providers", fake_list)

    user = _user("u1")
    assert await user_can_use_model_spec(MagicMock(), user, "shared-provider:gpt-4o") is True
    # 回填后缓存命中，二次调用不再查询 DB
    assert visibility_cache.get("u1") == frozenset({"shared-provider"})


@pytest.mark.asyncio
async def test_user_can_use_model_spec_denies_hidden_provider(monkeypatch):
    """模型所属 provider 对用户不可见时返回 False。"""
    from unittest.mock import MagicMock

    from yuxi.models.providers.cache import model_cache, visibility_cache
    from yuxi.models.providers.service import user_can_use_model_spec

    visibility_cache.invalidate()
    visibility_cache.set("u1", {"shared-provider"})
    monkeypatch.setattr(model_cache, "get_model_info", lambda spec: _FakeModelInfo("private-provider"))

    user = _user("u1")
    assert await user_can_use_model_spec(MagicMock(), user, "private-provider:gpt-4o") is False


@pytest.mark.asyncio
async def test_user_can_use_model_spec_unknown_model_allows(monkeypatch):
    """模型不存在时不做可见性拦截，由下游负责报"模型不存在"错误。"""
    from unittest.mock import MagicMock

    from yuxi.models.providers.cache import model_cache, visibility_cache
    from yuxi.models.providers.service import user_can_use_model_spec

    visibility_cache.invalidate()
    monkeypatch.setattr(model_cache, "get_model_info", lambda spec: None)

    user = _user("u1")
    assert await user_can_use_model_spec(MagicMock(), user, "ghost-provider:model") is True
