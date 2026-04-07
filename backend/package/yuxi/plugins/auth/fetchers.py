"""
具体认证器实现

包含:
- NoAuthFetcher: 无认证
- BasicAuthFetcher: HTTP Basic 认证
- BearerAuthFetcher: Bearer Token 认证
- CookieFetcher: 静态 Cookie 注入
- CookieLoginFetcher: 需要先登录获取 Cookie
- CustomFetcher: 完全自定义配置
"""

import httpx
from typing import override

from yuxi.plugins.auth.base import (
    AuthenticatedFetcher,
    AuthConfig,
    FetcherContext,
    AuthenticationError,
    FetcherConfigurationError,
)
from yuxi.utils import logger


class NoAuthFetcher(AuthenticatedFetcher):
    """
    无认证 Fetcher

    用于公开 URL 或不需要认证的请求。
    """

    @override
    async def prepare(self, context: FetcherContext) -> FetcherContext:
        # 应用配置的 modifiers（如果有）
        return self._apply_config_modifiers(context)

    @override
    async def fetch(self, url: str) -> tuple[bytes, str]:
        context = FetcherContext(url=url)
        context = await self.prepare(context)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                context.url,
                headers=context.headers,
                cookies=context.cookies,
                params=context.params,
            )
            response.raise_for_status()
            return response.content, str(response.url)


class BasicAuthFetcher(AuthenticatedFetcher):
    """
    HTTP Basic 认证 Fetcher

    配置示例:
    ```json
    {
      "auth_type": "basic",
      "credentials": {
        "username": "user123",
        "password": "pass456"
      }
    }
    ```
    """

    @override
    async def prepare(self, context: FetcherContext) -> FetcherContext:
        # 验证凭据
        if "username" not in self.config.credentials:
            raise FetcherConfigurationError("Basic auth requires 'username' credential", "basic")
        if "password" not in self.config.credentials:
            raise FetcherConfigurationError("Basic auth requires 'password' credential", "basic")

        # 应用配置的 modifiers
        context = self._apply_config_modifiers(context)

        # 设置 Basic Auth header
        import base64
        username = self.config.credentials["username"]
        password = self.config.credentials["password"]
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        context.headers["Authorization"] = f"Basic {encoded}"

        return context

    @override
    async def fetch(self, url: str) -> tuple[bytes, str]:
        context = await self.prepare(FetcherContext(url=url))

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                context.url,
                headers=context.headers,
                cookies=context.cookies,
                params=context.params,
            )
            response.raise_for_status()
            return response.content, str(response.url)


class BearerAuthFetcher(AuthenticatedFetcher):
    """
    Bearer Token 认证 Fetcher

    配置示例:
    ```json
    {
      "auth_type": "bearer",
      "credentials": {
        "token": "ghp_xxxxxxxxxxxx"
      }
    }
    ```
    """

    @override
    async def prepare(self, context: FetcherContext) -> FetcherContext:
        # 验证凭据
        if "token" not in self.config.credentials:
            raise FetcherConfigurationError("Bearer auth requires 'token' credential", "bearer")

        # 应用配置的 modifiers
        context = self._apply_config_modifiers(context)

        # 设置 Bearer Auth header
        token = self.config.credentials["token"]
        context.headers["Authorization"] = f"Bearer {token}"

        return context

    @override
    async def fetch(self, url: str) -> tuple[bytes, str]:
        context = await self.prepare(FetcherContext(url=url))

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                context.url,
                headers=context.headers,
                cookies=context.cookies,
                params=context.params,
            )
            response.raise_for_status()
            return response.content, str(response.url)


class CookieFetcher(AuthenticatedFetcher):
    """
    静态 Cookie 注入 Fetcher

    适用于已有 session cookie 的场景。

    配置示例:
    ```json
    {
      "auth_type": "cookie",
      "credentials": {
        "session_id": "abc123xyz",
        "employee_id": "12345"
      },
      "request_modifiers": {
        "cookies": {
          "sessionid": "{session_id}"
        },
        "headers": {
          "X-User-ID": "{employee_id}"
        }
      }
    }
    ```
    """

    @override
    async def prepare(self, context: FetcherContext) -> FetcherContext:
        # 应用配置的 modifiers
        return self._apply_config_modifiers(context)

    @override
    async def fetch(self, url: str) -> tuple[bytes, str]:
        context = await self.prepare(FetcherContext(url=url))

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                context.url,
                headers=context.headers,
                cookies=context.cookies,
                params=context.params,
            )
            response.raise_for_status()
            return response.content, str(response.url)


class CookieLoginFetcher(AuthenticatedFetcher):
    """
    需要先登录获取 Cookie 的 Fetcher

    流程:
    1. 调用登录接口获取 session cookie
    2. 使用 cookie 访问目标 URL
    3. 检测 cookie 过期时自动重新登录

    配置示例:
    ```json
    {
      "auth_type": "cookie_login",
      "credentials": {
        "login_url": "https://example.com/api/login",
        "username": "user123",
        "password": "pass456",
        "employee_id": "12345"
      },
      "request_modifiers": {
        "headers": {
          "X-User-ID": "{employee_id}"
        }
      }
    }
    ```
    """

    def __init__(self, config: AuthConfig):
        super().__init__(config)
        self._session_cookies: dict[str, str] = {}
        self._cookie_expires_at: float | None = None

    def _extract_cookies_from_response(self, response: httpx.Response) -> dict[str, str]:
        """从响应中提取 cookies"""
        cookies = {}
        for cookie in response.cookies.jar:
            cookies[cookie.name] = cookie.value
        return cookies

    async def _login(self) -> dict[str, str]:
        """
        执行登录获取 session cookie

        Returns:
            dict[str, str]: session cookies
        """
        if "login_url" not in self.config.credentials:
            raise FetcherConfigurationError("CookieLogin requires 'login_url' credential", "cookie_login")
        if "username" not in self.config.credentials:
            raise FetcherConfigurationError("CookieLogin requires 'username' credential", "cookie_login")
        if "password" not in self.config.credentials:
            raise FetcherConfigurationError("CookieLogin requires 'password' credential", "cookie_login")

        login_url = self.config.credentials["login_url"]
        username = self.config.credentials["username"]
        password = self.config.credentials["password"]

        logger.info(f"Executing login to {login_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                login_url,
                data={"username": username, "password": password},
            )
            response.raise_for_status()

            # 提取 cookies
            cookies = self._extract_cookies_from_response(response)

            if not cookies:
                logger.warning("Login response contained no cookies")

            return cookies

    @override
    def is_expired(self) -> bool:
        """检查 session 是否过期"""
        if not self._session_cookies:
            return True
        if self._cookie_expires_at is None:
            return False  # 没有设置过期时间，假设一直有效
        import time
        return time.time() >= self._cookie_expires_at

    @override
    async def refresh(self) -> None:
        """重新登录刷新 session"""
        logger.info("Refreshing cookie session via login")
        self._session_cookies = await self._login()
        # 设置默认的过期时间（如 1 小时）
        import time
        self._cookie_expires_at = time.time() + 3600

    @override
    async def prepare(self, context: FetcherContext) -> FetcherContext:
        # 确保有有效的 session
        if self.is_expired():
            await self.refresh()

        # 应用配置的 modifiers
        context = self._apply_config_modifiers(context)

        # 注入 session cookies
        for key, value in self._session_cookies.items():
            if key not in context.cookies:
                context.cookies[key] = value

        return context

    @override
    async def fetch(self, url: str) -> tuple[bytes, str]:
        context = await self.prepare(FetcherContext(url=url))

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                context.url,
                headers=context.headers,
                cookies=context.cookies,
                params=context.params,
            )
            response.raise_for_status()
            return response.content, str(response.url)


class CustomFetcher(AuthenticatedFetcher):
    """
    完全自定义配置的 Fetcher

    所有认证行为由用户通过 request_modifiers 配置决定。
    适用于不符合标准认证模式的场景。

    配置示例:
    ```json
    {
      "auth_type": "custom",
      "credentials": {
        "api_key": "xxx",
        "tenant_id": "yyy",
        "employee_id": "12345"
      },
      "request_modifiers": {
        "headers": {
          "X-API-Key": "{api_key}",
          "X-Tenant-ID": "{tenant_id}",
          "X-User-ID": "{employee_id}",
          "X-Custom-Sign": "{api_key}-{tenant_id}"
        }
      }
    }
    ```
    """

    @override
    async def prepare(self, context: FetcherContext) -> FetcherContext:
        # 完全依赖配置的 modifiers
        return self._apply_config_modifiers(context)

    @override
    async def fetch(self, url: str) -> tuple[bytes, str]:
        context = await self.prepare(FetcherContext(url=url))

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                context.url,
                headers=context.headers,
                cookies=context.cookies,
                params=context.params,
            )
            response.raise_for_status()
            return response.content, str(response.url)
