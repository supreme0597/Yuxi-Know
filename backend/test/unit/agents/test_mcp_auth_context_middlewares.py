from __future__ import annotations

import os
import traceback
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from yuxi.agents.middlewares import runtime_config_middleware
from yuxi.agents.middlewares.runtime_config_middleware import RuntimeConfigMiddleware
from yuxi.agents.middlewares.skills_middleware import SkillsMiddleware
from yuxi.services.mcp_auth.orchestrator import AuthContext, RuntimeMCPAuthError, mcp_auth_context_var

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


class DummyTool:
    name = "mcp_tool"


async def test_runtime_config_middleware_sets_auth_context_for_mcp_loading(monkeypatch):
    captured: list[AuthContext | None] = []

    async def fake_get_enabled_mcp_tools(server_name: str):
        captured.append(mcp_auth_context_var.get())
        assert server_name == "billing"
        return [DummyTool()]

    monkeypatch.setattr(runtime_config_middleware, "get_enabled_mcp_tools", fake_get_enabled_mcp_tools)
    middleware = RuntimeConfigMiddleware(
        extra_tools=[], enable_model_override=False, enable_system_prompt_override=False
    )
    context = SimpleNamespace(user_id="42", work_id="W-7", department_id=9, tools=[], mcps=["billing"])

    tools = await middleware.get_tools_from_context(context)

    assert [tool.name for tool in tools] == ["mcp_tool"]
    assert captured == [AuthContext(user_id="42", work_id="W-7", department_id="9")]
    assert mcp_auth_context_var.get() is None


async def test_runtime_config_middleware_loads_static_mcp_without_auth_context(monkeypatch):
    captured: list[AuthContext | None] = []

    async def fake_get_enabled_mcp_tools(server_name: str):
        captured.append(mcp_auth_context_var.get())
        assert server_name == "static-mcp"
        return [DummyTool()]

    monkeypatch.setattr(runtime_config_middleware, "get_enabled_mcp_tools", fake_get_enabled_mcp_tools)
    middleware = RuntimeConfigMiddleware(
        extra_tools=[], enable_model_override=False, enable_system_prompt_override=False
    )
    context = SimpleNamespace(tools=[], mcps=["static-mcp"])

    tools = await middleware.get_tools_from_context(context)

    assert [tool.name for tool in tools] == ["mcp_tool"]
    assert captured == [None]
    assert mcp_auth_context_var.get() is None


async def test_runtime_config_middleware_redacts_sensitive_mcp_auth_errors(monkeypatch):
    sensitive_value = "Authorization=Bearer runtime-secret; STDIO_TOKEN=env-secret"
    warning_messages: list[str] = []

    async def fake_get_enabled_mcp_tools(server_name: str):
        assert server_name == "billing"
        raise RuntimeMCPAuthError(sensitive_value)

    monkeypatch.setattr(runtime_config_middleware, "get_enabled_mcp_tools", fake_get_enabled_mcp_tools)
    monkeypatch.setattr(
        runtime_config_middleware,
        "logger",
        SimpleNamespace(warning=warning_messages.append),
    )
    middleware = RuntimeConfigMiddleware(
        extra_tools=[], enable_model_override=False, enable_system_prompt_override=False
    )
    context = SimpleNamespace(user_id="42", work_id="W-7", department_id=9, tools=[], mcps=["billing"])

    with pytest.raises(RuntimeMCPAuthError) as exc_info:
        await middleware.get_tools_from_context(context)

    rendered_error = "".join(traceback.format_exception(exc_info.type, exc_info.value, exc_info.tb))
    assert sensitive_value not in "\n".join(warning_messages)
    assert sensitive_value not in rendered_error
    assert warning_messages == [
        "RuntimeConfigMiddleware: MCP authentication unavailable for dependency 'billing' (RuntimeMCPAuthError)"
    ]
    assert str(exc_info.value) == 'MCP "billing" authentication is unavailable'
    assert mcp_auth_context_var.get() is None


async def test_runtime_config_middleware_redacts_sensitive_mcp_loading_logs(monkeypatch):
    sensitive_value = "Authorization=Bearer runtime-secret; STDIO_TOKEN=env-secret"
    warning_messages: list[str] = []

    async def fake_get_enabled_mcp_tools(server_name: str):
        assert server_name == "billing"
        raise RuntimeError(sensitive_value)

    monkeypatch.setattr(runtime_config_middleware, "get_enabled_mcp_tools", fake_get_enabled_mcp_tools)
    monkeypatch.setattr(
        runtime_config_middleware,
        "logger",
        SimpleNamespace(warning=warning_messages.append),
    )
    middleware = RuntimeConfigMiddleware(
        extra_tools=[], enable_model_override=False, enable_system_prompt_override=False
    )
    context = SimpleNamespace(user_id="42", work_id="W-7", department_id=9, tools=[], mcps=["billing"])

    tools = await middleware.get_tools_from_context(context)

    assert tools == []
    assert sensitive_value not in "\n".join(warning_messages)
    assert warning_messages == ["RuntimeConfigMiddleware: failed to load MCP dependency 'billing' (RuntimeError)"]
    assert mcp_auth_context_var.get() is None


async def test_skills_middleware_sets_auth_context_for_dependency_mcp_loading(monkeypatch):
    captured: list[AuthContext | None] = []

    async def fake_get_enabled_mcp_tools(server_name: str):
        captured.append(mcp_auth_context_var.get())
        assert server_name == "skill-mcp"
        return [DummyTool()]

    import yuxi.agents.middlewares.skills_middleware as skills_middleware_module

    monkeypatch.setattr(skills_middleware_module, "get_enabled_mcp_tools", fake_get_enabled_mcp_tools)
    middleware = SkillsMiddleware()
    context = SimpleNamespace(user_id="42", work_id="W-7", department_id=9, mcps=[])

    tools = await middleware._get_mcp_tools_from_context(context, extra_mcps=["skill-mcp"])

    assert [tool.name for tool in tools] == ["mcp_tool"]
    assert captured == [AuthContext(user_id="42", work_id="W-7", department_id="9")]
    assert mcp_auth_context_var.get() is None


async def test_skills_middleware_loads_static_dependency_without_auth_context(monkeypatch):
    captured: list[AuthContext | None] = []

    async def fake_get_enabled_mcp_tools(server_name: str):
        captured.append(mcp_auth_context_var.get())
        assert server_name == "static-skill-mcp"
        return [DummyTool()]

    import yuxi.agents.middlewares.skills_middleware as skills_middleware_module

    monkeypatch.setattr(skills_middleware_module, "get_enabled_mcp_tools", fake_get_enabled_mcp_tools)
    middleware = SkillsMiddleware()
    context = SimpleNamespace(mcps=[])

    tools = await middleware._get_mcp_tools_from_context(context, extra_mcps=["static-skill-mcp"])

    assert [tool.name for tool in tools] == ["mcp_tool"]
    assert captured == [None]
    assert mcp_auth_context_var.get() is None


async def test_skills_middleware_redacts_sensitive_mcp_auth_errors(monkeypatch):
    sensitive_value = "X-Api-Key=skills-secret; MCP_TOKEN=env-secret"
    warning_messages: list[str] = []

    async def fake_get_enabled_mcp_tools(server_name: str):
        assert server_name == "skill-mcp"
        raise RuntimeMCPAuthError(sensitive_value)

    import yuxi.agents.middlewares.skills_middleware as skills_middleware_module

    monkeypatch.setattr(skills_middleware_module, "get_enabled_mcp_tools", fake_get_enabled_mcp_tools)
    monkeypatch.setattr(
        skills_middleware_module,
        "logger",
        SimpleNamespace(warning=warning_messages.append),
    )
    middleware = SkillsMiddleware()
    context = SimpleNamespace(user_id="42", work_id="W-7", department_id=9, mcps=[])

    with pytest.raises(RuntimeMCPAuthError) as exc_info:
        await middleware._get_mcp_tools_from_context(context, extra_mcps=["skill-mcp"])

    rendered_error = "".join(traceback.format_exception(exc_info.type, exc_info.value, exc_info.tb))
    assert sensitive_value not in "\n".join(warning_messages)
    assert sensitive_value not in rendered_error
    assert warning_messages == [
        "SkillsMiddleware: MCP authentication unavailable for dependency 'skill-mcp' (RuntimeMCPAuthError)"
    ]
    assert str(exc_info.value) == 'MCP "skill-mcp" authentication is unavailable'
    assert mcp_auth_context_var.get() is None


async def test_skills_middleware_redacts_sensitive_mcp_loading_logs(monkeypatch):
    sensitive_value = "X-Api-Key=skills-secret; MCP_TOKEN=env-secret"
    warning_messages: list[str] = []

    async def fake_get_enabled_mcp_tools(server_name: str):
        assert server_name == "skill-mcp"
        raise RuntimeError(sensitive_value)

    import yuxi.agents.middlewares.skills_middleware as skills_middleware_module

    monkeypatch.setattr(skills_middleware_module, "get_enabled_mcp_tools", fake_get_enabled_mcp_tools)
    monkeypatch.setattr(
        skills_middleware_module,
        "logger",
        SimpleNamespace(warning=warning_messages.append),
    )
    middleware = SkillsMiddleware()
    context = SimpleNamespace(user_id="42", work_id="W-7", department_id=9, mcps=[])

    tools = await middleware._get_mcp_tools_from_context(context, extra_mcps=["skill-mcp"])

    assert tools == []
    assert sensitive_value not in "\n".join(warning_messages)
    assert warning_messages == ["SkillsMiddleware: failed to load MCP dependency 'skill-mcp' (RuntimeError)"]
    assert mcp_auth_context_var.get() is None
