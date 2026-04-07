"""
认证插件 - 支持多内网系统鉴权适配

提供可扩展的认证器框架，支持:
- HTTP Basic Auth
- Bearer Token
- Cookie Session
- OIDC/OAuth2
- 自定义认证方式

设计模式：
- 策略模式：不同认证算法封装为独立的 Fetcher 类
- 工厂模式：AuthFetcherRegistry 根据 auth_type 创建实例
- 注册表模式：支持动态注册新的认证器类型
"""

from yuxi.plugins.auth.base import (
    AuthenticatedFetcher,
    AuthConfig,
    RequestModifiers,
    FetcherContext,
)
from yuxi.plugins.auth.registry import AuthFetcherRegistry
from yuxi.plugins.auth.fetchers import (
    NoAuthFetcher,
    BasicAuthFetcher,
    BearerAuthFetcher,
    CookieFetcher,
    CookieLoginFetcher,
    CustomFetcher,
)

__all__ = [
    # 基类和配置
    "AuthenticatedFetcher",
    "AuthConfig",
    "RequestModifiers",
    "FetcherContext",
    # 工厂
    "AuthFetcherRegistry",
    # 具体认证器
    "NoAuthFetcher",
    "BasicAuthFetcher",
    "BearerAuthFetcher",
    "CookieFetcher",
    "CookieLoginFetcher",
    "CustomFetcher",
]
