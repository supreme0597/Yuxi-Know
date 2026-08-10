from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import SystemMessage

from yuxi.agents.backends.sandbox.runtime_context import SandboxRuntimeCredentials, sandbox_runtime_scope
from yuxi.agents.middlewares.sandbox_cookie import (
    SANDBOX_COOKIE_PROMPT_MARKER,
    SandboxCookiePromptMiddleware,
    _system_message_text,
)
from yuxi.services.run_runtime_secret_service import BrowserCookieRuntimeSecret


class FakeRequest:
    def __init__(self, system_message=None):
        self.system_message = system_message or SystemMessage(content="base")
        self.runtime = SimpleNamespace()

    def override(self, **kwargs):
        return FakeRequest(system_message=kwargs.get("system_message", self.system_message))


@pytest.mark.asyncio
async def test_sandbox_cookie_prompt_describes_only_the_runtime_header_file():
    captured = {}
    secret = BrowserCookieRuntimeSecret(
        header="session=secret-value; theme=dark",
    )

    async def handler(request):
        captured["request"] = request
        return "ok"

    async with sandbox_runtime_scope(SandboxRuntimeCredentials("run-1", secret)):
        result = await SandboxCookiePromptMiddleware().awrap_model_call(FakeRequest(), handler)

    text = _system_message_text(captured["request"].system_message)
    assert result == "ok"
    assert "原始 Cookie Header" in text
    assert "/home/gem/.yuxi-runtime/browser-cookie-header.txt" in text
    assert "SANDBOX_COOKIE_HEADER_FILE" not in text
    assert "环境变量" not in text
    assert "不是 JSON" in text
    assert "session=secret-value" not in text
    assert "origin" not in text


@pytest.mark.asyncio
async def test_sandbox_cookie_prompt_skips_without_runtime_secret():
    captured = {}

    async def handler(request):
        captured["request"] = request
        return "ok"

    await SandboxCookiePromptMiddleware().awrap_model_call(FakeRequest(), handler)

    assert _system_message_text(captured["request"].system_message) == "base"


@pytest.mark.asyncio
async def test_sandbox_cookie_prompt_skips_context_without_cookie():
    captured = {}

    async def handler(request):
        captured["request"] = request
        return "ok"

    async with sandbox_runtime_scope(SandboxRuntimeCredentials("run-1", None)):
        await SandboxCookiePromptMiddleware().awrap_model_call(FakeRequest(), handler)

    assert _system_message_text(captured["request"].system_message) == "base"


@pytest.mark.asyncio
async def test_sandbox_cookie_prompt_is_injected_only_once():
    middleware = SandboxCookiePromptMiddleware()
    secret = BrowserCookieRuntimeSecret(header="session=secret-value")
    captured = {}

    async def first_handler(request):
        captured["first"] = request
        return "ok"

    async def second_handler(request):
        captured["second"] = request
        return "ok"

    async with sandbox_runtime_scope(SandboxRuntimeCredentials("run-1", secret)):
        await middleware.awrap_model_call(FakeRequest(), first_handler)
        await middleware.awrap_model_call(
            FakeRequest(system_message=captured["first"].system_message),
            second_handler,
        )

    text = _system_message_text(captured["second"].system_message)
    assert text.count(SANDBOX_COOKIE_PROMPT_MARKER) == 1
