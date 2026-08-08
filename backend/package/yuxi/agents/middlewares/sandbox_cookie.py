from __future__ import annotations

from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

from yuxi.agents.backends.sandbox.provider import SANDBOX_COOKIE_HEADER_FILE
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


def _build_sandbox_cookie_prompt(origin: str) -> str:
    return f"""{SANDBOX_COOKIE_PROMPT_MARKER}
<| 同源 Cookie Header 使用约束:重要 |>
当前运行提供了浏览器发送给 Yuxi 的原始 Cookie Header，仅允许用于 origin `{origin}`。
Header 文件路径由环境变量 `SANDBOX_COOKIE_HEADER_FILE` 指向，当前固定为
`{SANDBOX_COOKIE_HEADER_FILE}`。文件内容是可直接作为 HTTP `Cookie` 请求头使用的原始字符串，不是 JSON。

- 只有目标 URL 规范化后的 `scheme + host + port` 与 `{origin}` 完全一致时才可读取并使用该文件。
- 子域名、主机别名、IP 地址以及不同端口都不视为同 origin。
- 禁止在跨 origin 重定向中继续携带 Cookie；应关闭自动重定向，或逐跳检查 `Location` 后再决定。
- 只在发起请求的进程内读取并设置 `Cookie` Header；禁止打印、回显、记录、总结或向用户展示文件内容。
- 禁止把 Header 复制到 workspace、uploads、outputs、代码文件、命令参数、工具参数或其他持久化位置。
- 文件不存在或不可读时，视为当前运行没有可用登录态，不得猜测、恢复或使用历史 Cookie。
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
            _build_sandbox_cookie_prompt(secret.origin),
        )
        return await handler(request.override(system_message=system_message))


sandbox_cookie_prompt = SandboxCookiePromptMiddleware()
