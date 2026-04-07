"""
认证器注册表和工厂

单例模式，全局访问。
支持动态注册新的认证器类型。
"""

from typing import Type

from yuxi.plugins.auth.base import AuthenticatedFetcher, AuthConfig, FetcherConfigurationError
from yuxi.plugins.auth.fetchers import (
    NoAuthFetcher,
    BasicAuthFetcher,
    BearerAuthFetcher,
    CookieFetcher,
    CookieLoginFetcher,
    CustomFetcher,
)
from yuxi.utils import logger


class AuthFetcherRegistry:
    """
    认证器注册表和工厂

    使用示例:
    ```python
    # 创建认证器
    config = AuthConfig(
        domain_pattern="*.example.com",
        auth_type="basic",
        credentials={"username": "user", "password": "pass"}
    )
    fetcher = AuthFetcherRegistry.create(config)

    # 注册自定义认证器
    class MyCustomFetcher(AuthenticatedFetcher):
        ...

    AuthFetcherRegistry.register("my_custom", MyCustomFetcher)
    ```
    """

    # 内置认证器映射
    _fetcher_classes: dict[str, Type[AuthenticatedFetcher]] = {
        "none": NoAuthFetcher,
        "basic": BasicAuthFetcher,
        "bearer": BearerAuthFetcher,
        "cookie": CookieFetcher,
        "cookie_login": CookieLoginFetcher,
        "custom": CustomFetcher,
    }

    @classmethod
    def register(cls, auth_type: str, fetcher_class: Type[AuthenticatedFetcher]) -> None:
        """
        注册新的认证器类型

        支持第三方扩展注册自定义认证器。

        Args:
            auth_type: 认证类型名称
            fetcher_class: 认证器类

        Raises:
            ValueError: auth_type 已存在
        """
        if auth_type in cls._fetcher_classes:
            logger.warning(f"Overwriting existing auth_type: {auth_type}")
        cls._fetcher_classes[auth_type] = fetcher_class
        logger.info(f"Registered auth_type: {auth_type}")

    @classmethod
    def unregister(cls, auth_type: str) -> bool:
        """
        注销认证器类型

        Args:
            auth_type: 认证类型名称

        Returns:
            bool: 是否成功注销
        """
        if auth_type in cls._fetcher_classes:
            del cls._fetcher_classes[auth_type]
            logger.info(f"Unregistered auth_type: {auth_type}")
            return True
        return False

    @classmethod
    def create(cls, config: AuthConfig) -> AuthenticatedFetcher:
        """
        根据配置创建对应的认证器实例

        Args:
            config: 认证配置

        Returns:
            AuthenticatedFetcher: 认证器实例

        Raises:
            FetcherConfigurationError: 未知的 auth_type
        """
        fetcher_class = cls._fetcher_classes.get(config.auth_type)
        if not fetcher_class:
            available = ", ".join(sorted(cls._fetcher_classes.keys()))
            raise FetcherConfigurationError(
                f"Unknown auth_type: {config.auth_type}. Available types: {available}",
                config.auth_type,
            )
        return fetcher_class(config)

    @classmethod
    def get_registered_types(cls) -> list[str]:
        """
        获取所有已注册的认证类型

        Returns:
            list[str]: 认证类型列表
        """
        return list(cls._fetcher_classes.keys())

    @classmethod
    def is_registered(cls, auth_type: str) -> bool:
        """
        检查认证类型是否已注册

        Args:
            auth_type: 认证类型名称

        Returns:
            bool: 是否已注册
        """
        return auth_type in cls._fetcher_classes


# 全局单例实例
_registry = AuthFetcherRegistry()


def get_registry() -> AuthFetcherRegistry:
    """获取全局认证器注册表实例"""
    return _registry


def create_fetcher(config: AuthConfig) -> AuthenticatedFetcher:
    """快捷函数：根据配置创建认证器"""
    return _registry.create(config)


def register_fetcher(auth_type: str, fetcher_class: Type[AuthenticatedFetcher]) -> None:
    """快捷函数：注册新的认证器类型"""
    _registry.register(auth_type, fetcher_class)
