"""
认证器单元测试
"""

import pytest
import base64
from unittest.mock import AsyncMock, patch, MagicMock

from yuxi.plugins.auth.base import (
    AuthConfig,
    RequestModifiers,
    FetcherContext,
    AuthenticationError,
    FetcherConfigurationError,
)
from yuxi.plugins.auth.fetchers import (
    NoAuthFetcher,
    BasicAuthFetcher,
    BearerAuthFetcher,
    CookieFetcher,
    CookieLoginFetcher,
    CustomFetcher,
)
from yuxi.plugins.auth.registry import AuthFetcherRegistry, create_fetcher, register_fetcher


class TestRequestModifiers:
    """测试 RequestModifiers 类"""

    def test_resolve_variables(self):
        """测试变量替换功能"""
        template = "Bearer {token}"
        credentials = {"token": "abc123"}
        result = RequestModifiers._resolve_variables(template, credentials)
        assert result == "Bearer abc123"

    def test_resolve_multiple_variables(self):
        """测试多个变量替换"""
        template = "{username}@{domain}"
        credentials = {"username": "admin", "domain": "example.com"}
        result = RequestModifiers._resolve_variables(template, credentials)
        assert result == "admin@example.com"

    def test_apply_headers(self):
        """测试 headers 应用"""
        import httpx
        modifiers = RequestModifiers(
            headers={"X-User-ID": "{employee_id}"}
        )
        request = httpx.Request("GET", "https://example.com")
        context = FetcherContext(url="https://example.com")
        context.headers = {}

        modifiers.apply(request, {"employee_id": "12345"})
        assert request.headers["X-User-ID"] == "12345"


class TestAuthConfig:
    """测试 AuthConfig 配置模型"""

    def test_create_auth_config(self):
        """测试创建认证配置"""
        config = AuthConfig(
            domain_pattern="*.example.com",
            auth_type="basic",
            credentials={"username": "user", "password": "pass"}
        )
        assert config.domain_pattern == "*.example.com"
        assert config.auth_type == "basic"
        assert config.credentials["username"] == "user"


class TestNoAuthFetcher:
    """测试 NoAuthFetcher"""

    @pytest.mark.asyncio
    async def test_prepare(self):
        """测试 prepare 方法"""
        config = AuthConfig(domain_pattern="example.com", auth_type="none")
        fetcher = NoAuthFetcher(config)
        context = FetcherContext(url="https://example.com")
        result = await fetcher.prepare(context)
        assert result.url == "https://example.com"


class TestBasicAuthFetcher:
    """测试 BasicAuthFetcher"""

    @pytest.mark.asyncio
    async def test_prepare_with_valid_credentials(self):
        """测试有效的凭据"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="basic",
            credentials={"username": "user", "password": "pass"}
        )
        fetcher = BasicAuthFetcher(config)
        context = await fetcher.prepare(FetcherContext(url="https://example.com"))

        # 验证 Authorization header
        assert "Authorization" in context.headers
        assert context.headers["Authorization"].startswith("Basic ")

        # 验证 base64 编码
        encoded = context.headers["Authorization"].split(" ")[1]
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "user:pass"

    @pytest.mark.asyncio
    async def test_prepare_missing_username(self):
        """测试缺少 username 抛出异常"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="basic",
            credentials={"password": "pass"}
        )
        fetcher = BasicAuthFetcher(config)

        with pytest.raises(FetcherConfigurationError) as exc_info:
            await fetcher.prepare(FetcherContext(url="https://example.com"))
        assert "username" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_prepare_missing_password(self):
        """测试缺少 password 抛出异常"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="basic",
            credentials={"username": "user"}
        )
        fetcher = BasicAuthFetcher(config)

        with pytest.raises(FetcherConfigurationError) as exc_info:
            await fetcher.prepare(FetcherContext(url="https://example.com"))
        assert "password" in str(exc_info.value)


class TestBearerAuthFetcher:
    """测试 BearerAuthFetcher"""

    @pytest.mark.asyncio
    async def test_prepare_with_valid_token(self):
        """测试有效的 token"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="bearer",
            credentials={"token": "abc123xyz"}
        )
        fetcher = BearerAuthFetcher(config)
        context = await fetcher.prepare(FetcherContext(url="https://example.com"))

        assert context.headers["Authorization"] == "Bearer abc123xyz"

    @pytest.mark.asyncio
    async def test_prepare_missing_token(self):
        """测试缺少 token 抛出异常"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="bearer",
            credentials={}
        )
        fetcher = BearerAuthFetcher(config)

        with pytest.raises(FetcherConfigurationError) as exc_info:
            await fetcher.prepare(FetcherContext(url="https://example.com"))
        assert "token" in str(exc_info.value)


class TestCookieFetcher:
    """测试 CookieFetcher"""

    @pytest.mark.asyncio
    async def test_prepare_with_modifiers(self):
        """测试带 modifiers 的 prepare"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="cookie",
            credentials={"session_id": "abc123"},
            request_modifiers=RequestModifiers(
                cookies={"sessionid": "{session_id}"}
            )
        )
        fetcher = CookieFetcher(config)
        context = await fetcher.prepare(FetcherContext(url="https://example.com"))

        assert context.cookies["sessionid"] == "abc123"


class TestCookieLoginFetcher:
    """测试 CookieLoginFetcher"""

    @pytest.mark.asyncio
    async def test_is_expired_no_cookies(self):
        """测试没有 cookie 时过期"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="cookie_login",
            credentials={
                "login_url": "https://example.com/login",
                "username": "user",
                "password": "pass"
            }
        )
        fetcher = CookieLoginFetcher(config)
        assert fetcher.is_expired() is True

    @pytest.mark.asyncio
    async def test_refresh_missing_login_url(self):
        """测试缺少 login_url 抛出异常"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="cookie_login",
            credentials={"username": "user", "password": "pass"}
        )
        fetcher = CookieLoginFetcher(config)

        with pytest.raises(FetcherConfigurationError) as exc_info:
            await fetcher.refresh()
        assert "login_url" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_missing_username(self):
        """测试缺少 username 抛出异常"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="cookie_login",
            credentials={"login_url": "https://example.com/login", "password": "pass"}
        )
        fetcher = CookieLoginFetcher(config)

        with pytest.raises(FetcherConfigurationError) as exc_info:
            await fetcher.refresh()
        assert "username" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_missing_password(self):
        """测试缺少 password 抛出异常"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="cookie_login",
            credentials={"login_url": "https://example.com/login", "username": "user"}
        )
        fetcher = CookieLoginFetcher(config)

        with pytest.raises(FetcherConfigurationError) as exc_info:
            await fetcher.refresh()
        assert "password" in str(exc_info.value)


class TestCustomFetcher:
    """测试 CustomFetcher"""

    @pytest.mark.asyncio
    async def test_prepare_with_custom_headers(self):
        """测试自定义 headers"""
        config = AuthConfig(
            domain_pattern="example.com",
            auth_type="custom",
            credentials={"api_key": "xyz", "tenant_id": "t1"},
            request_modifiers=RequestModifiers(
                headers={
                    "X-API-Key": "{api_key}",
                    "X-Tenant-ID": "{tenant_id}"
                }
            )
        )
        fetcher = CustomFetcher(config)
        context = await fetcher.prepare(FetcherContext(url="https://example.com"))

        assert context.headers["X-API-Key"] == "xyz"
        assert context.headers["X-Tenant-ID"] == "t1"


class TestAuthFetcherRegistry:
    """测试 AuthFetcherRegistry 工厂"""

    def test_create_no_auth(self):
        """测试创建 NoAuthFetcher"""
        config = AuthConfig(domain_pattern="example.com", auth_type="none")
        fetcher = AuthFetcherRegistry.create(config)
        assert isinstance(fetcher, NoAuthFetcher)

    def test_create_basic_auth(self):
        """测试创建 BasicAuthFetcher"""
        config = AuthConfig(domain_pattern="example.com", auth_type="basic")
        fetcher = AuthFetcherRegistry.create(config)
        assert isinstance(fetcher, BasicAuthFetcher)

    def test_create_bearer_auth(self):
        """测试创建 BearerAuthFetcher"""
        config = AuthConfig(domain_pattern="example.com", auth_type="bearer")
        fetcher = AuthFetcherRegistry.create(config)
        assert isinstance(fetcher, BearerAuthFetcher)

    def test_create_cookie_auth(self):
        """测试创建 CookieFetcher"""
        config = AuthConfig(domain_pattern="example.com", auth_type="cookie")
        fetcher = AuthFetcherRegistry.create(config)
        assert isinstance(fetcher, CookieFetcher)

    def test_create_cookie_login_auth(self):
        """测试创建 CookieLoginFetcher"""
        config = AuthConfig(domain_pattern="example.com", auth_type="cookie_login")
        fetcher = AuthFetcherRegistry.create(config)
        assert isinstance(fetcher, CookieLoginFetcher)

    def test_create_custom_auth(self):
        """测试创建 CustomFetcher"""
        config = AuthConfig(domain_pattern="example.com", auth_type="custom")
        fetcher = AuthFetcherRegistry.create(config)
        assert isinstance(fetcher, CustomFetcher)

    def test_create_unknown_auth_type(self):
        """测试未知 auth_type 抛出异常"""
        config = AuthConfig(domain_pattern="example.com", auth_type="unknown")

        with pytest.raises(FetcherConfigurationError) as exc_info:
            AuthFetcherRegistry.create(config)
        assert "unknown" in str(exc_info.value)

    def test_register_custom_fetcher(self):
        """测试注册自定义认证器"""
        class TestFetcher(NoAuthFetcher):
            pass

        AuthFetcherRegistry.register("test", TestFetcher)
        assert AuthFetcherRegistry.is_registered("test")

        config = AuthConfig(domain_pattern="example.com", auth_type="test")
        fetcher = AuthFetcherRegistry.create(config)
        assert isinstance(fetcher, TestFetcher)

    def test_get_registered_types(self):
        """测试获取已注册类型列表"""
        types = AuthFetcherRegistry.get_registered_types()
        assert "none" in types
        assert "basic" in types
        assert "bearer" in types
        assert "cookie" in types
        assert "cookie_login" in types
        assert "custom" in types
