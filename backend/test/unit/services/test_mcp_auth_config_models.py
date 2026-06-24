from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from yuxi.services.mcp_auth.config_models import MCPAuthConfig


def _auth_config(*, value_template: str, binding_scope: str = "user") -> MCPAuthConfig:
    return MCPAuthConfig.model_validate(
        {
            "version": 1,
            "provider": "bound_secret",
            "binding_scope": binding_scope,
            "inject": {
                "target": "headers",
                "entries": [{"name": "Authorization", "value_template": value_template}],
            },
        }
    )


def test_mcp_auth_config_applies_legacy_static_defaults():
    config = MCPAuthConfig.model_validate(
        {
            "version": 1,
            "provider": "legacy_static",
            "inject": {
                "target": "headers",
                "entries": [],
            },
        }
    )

    assert config.binding_scope == "inline"
    assert config.manifest_scope == "server"
    assert config.refresh_policy.pre_refresh_seconds == 0
    assert config.refresh_policy.retry_once_on_401 is False


def test_mcp_auth_config_requires_token_request_for_dynamic_http_provider():
    with pytest.raises(ValidationError, match="token_request"):
        MCPAuthConfig.model_validate(
            {
                "version": 1,
                "provider": "custom_http_token",
                "binding_scope": "department",
                "inject": {
                    "target": "headers",
                    "entries": [{"name": "Authorization", "value_template": "Bearer ${access_token}"}],
                },
            }
        )


@pytest.mark.parametrize(
    "value_template",
    [
        "Bearer ${secret.access_token}",
        "Bearer ${token.access_token}",
        "Bearer ${access_token}",
    ],
)
def test_mcp_auth_config_requires_connection_for_connection_backed_templates(value_template):
    config = _auth_config(value_template=value_template)

    assert config.requires_bound_connection() is True


def test_mcp_auth_config_does_not_require_connection_for_context_only_template():
    config = _auth_config(value_template="${context.user_id}")

    assert config.requires_bound_connection() is False


def test_mcp_auth_config_inline_scope_does_not_require_connection():
    config = _auth_config(value_template="${secret.access_token}", binding_scope="inline")

    assert config.requires_bound_connection() is False
