from __future__ import annotations

from yuxi.storage.postgres.models_business import ModelProvider


def _build(api_key):
    return ModelProvider(
        provider_id="openai-test",
        display_name="Test",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key=api_key,
        capabilities=["chat"],
        enabled_models=[],
    )


def test_to_dict_default_masks_api_key():
    p = _build("sk-abcdefghijklmnop1234567890")
    data = p.to_dict()
    assert data["api_key"] == "sk-***7890"
    assert data["api_key_masked"] == "sk-***7890"
    assert data["share_config"] == {"access_level": "global", "department_ids": [], "user_uids": []}


def test_to_dict_with_include_api_key_returns_plaintext():
    p = _build("sk-abcdefghijklmnop1234567890")
    data = p.to_dict(include_api_key=True)
    assert data["api_key"] == "sk-abcdefghijklmnop1234567890"
    assert data["api_key_masked"] == "sk-***7890"


def test_to_dict_handles_short_api_key():
    p = _build("abc")
    data = p.to_dict()
    assert data["api_key"] == "***"
    assert data["api_key_masked"] == "***"


def test_to_dict_handles_none_api_key():
    p = _build(None)
    data = p.to_dict()
    assert data["api_key"] is None
    assert data["api_key_masked"] is None
