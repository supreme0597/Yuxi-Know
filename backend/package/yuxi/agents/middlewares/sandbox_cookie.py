from __future__ import annotations

from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

from yuxi.agents.backends.sandbox.backend import SANDBOX_COOKIE_HEADER_FILE
from yuxi.agents.backends.sandbox.runtime_context import get_sandbox_runtime_credentials

SANDBOX_COOKIE_PROMPT_MARKER = "<!-- sandbox_cookie_context -->"


def _system_message_text(system_message) -> str:
    if system_message is None:
        return ""
    content = system_message.content
    if isinstance(content, str):
        return content
    return "\n".join(
        str(block.get("text") or "") for block in content if isinstance(block, dict) and block.get("type") == "text"
    )


def _build_sandbox_cookie_prompt() -> str:
    return f"""{SANDBOX_COOKIE_PROMPT_MARKER}
<| 沙盒 Cookie Header 文件:重要 |>
当前运行提供了浏览器发送给 Yuxi 的原始 Cookie Header。
Header 文件固定在 `{SANDBOX_COOKIE_HEADER_FILE}`，文件内容是原始 Cookie 请求头字符串，不是 JSON。

- 需要使用当前浏览器登录态时，从该文件读取内容并设置 HTTP Cookie Header。
- 禁止打印、回显、记录、总结或向用户展示文件内容。
- 禁止把 Header 复制到 workspace、uploads、outputs、代码文件或其它持久化位置。
- 文件不存在或不可读时，视为当前运行没有可用登录态。
"""


class SandboxCookiePromptMiddleware(AgentMiddleware):
    async def awrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        credentials = get_sandbox_runtime_credentials()
        secret = credentials.browser_cookie if credentials is not None else None
        if secret is None:
            return await handler(request)

        existing = _system_message_text(request.system_message)
        if SANDBOX_COOKIE_PROMPT_MARKER in existing:
            return await handler(request)

        system_message = append_to_system_message(
            request.system_message,
            _build_sandbox_cookie_prompt(),
        )
        return await handler(request.override(system_message=system_message))


sandbox_cookie_prompt = SandboxCookiePromptMiddleware()
