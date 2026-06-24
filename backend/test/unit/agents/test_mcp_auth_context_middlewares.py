from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from yuxi.agents.middlewares import runtime_config_middleware
from yuxi.agents.middlewares.runtime_config_middleware import RuntimeConfigMiddleware
from yuxi.agents.middlewares.skills_middleware import SkillsMiddleware
from yuxi.services.mcp_auth.orchestrator import AuthContext, mcp_auth_context_var

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


async def test_skills_middleware_allows_plain_dependency_mcp_loading_without_auth_context(monkeypatch):
    captured: list[AuthContext | None] = []

    async def fake_get_enabled_mcp_tools(server_name: str):
        captured.append(mcp_auth_context_var.get())
        assert server_name == "plain-mcp"
        return [DummyTool()]

    import yuxi.agents.middlewares.skills_middleware as skills_middleware_module

    monkeypatch.setattr(skills_middleware_module, "get_enabled_mcp_tools", fake_get_enabled_mcp_tools)
    middleware = SkillsMiddleware()
    context = SimpleNamespace(mcps=[])

    tools = await middleware._get_mcp_tools_from_context(context, extra_mcps=["plain-mcp"])

    assert [tool.name for tool in tools] == ["mcp_tool"]
    assert captured == [None]
    assert mcp_auth_context_var.get() is None
