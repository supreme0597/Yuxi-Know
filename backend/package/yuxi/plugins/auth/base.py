"""
认证器基类和配置模型

设计原则:
- 抽象基类定义统一接口
- 数据模型支持声明式配置
- 支持变量替换语法
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field
import httpx
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class RequestModifiers(BaseModel):
    """
    定义如何将认证信息注入到 HTTP 请求中

    三类 modifier:
    1. headers: 添加/覆盖 HTTP headers
    2. cookies: 添加 cookies
    3. query_params: 添加 URL 查询参数
    """

    headers: dict[str, str] = Field(default_factory=dict)
    cookies: dict[str, str] = Field(default_factory=dict)
    query_params: dict[str, str] = Field(default_factory=dict)

    def apply(
        self,
        request: httpx.Request,
        credentials: dict[str, str]
    ) -> httpx.Request:
        """
        应用 request_modifiers 到请求，支持 {credential_key} 变量替换

        示例:
          headers: {"X-User-ID": "{employee_id}"}
          credentials: {"employee_id": "12345"}
          → 实际 headers: {"X-User-ID": "12345"}
        """
        # 替换 headers 中的变量
        for key, value in self.headers.items():
            resolved_value = self._resolve_variables(value, credentials)
            request.headers[key] = resolved_value

        # 设置 cookies
        for key, value in self.cookies.items():
            resolved_value = self._resolve_variables(value, credentials)
            request.cookies[key] = resolved_value

        # 添加 query params
        if self.query_params:
            url_parts = list(urlparse(str(request.url)))
            query = parse_qs(url_parts[4]) if url_parts[4] else {}
            for key, value in self.query_params.items():
                resolved_value = self._resolve_variables(value, credentials)
                query[key] = [resolved_value]
            url_parts[4] = urlencode(query, doseq=True)
            request.url = httpx.URL(urlunparse(url_parts))

        return request

    @staticmethod
    def _resolve_variables(template: str, credentials: dict[str, str]) -> str:
        """
        替换 {key} 形式的变量

        示例："{employee_id}" → "12345"
        """
        result = template
        for key, value in credentials.items():
            result = result.replace(f"{{{key}}}", value)
        return result


class AuthConfig(BaseModel):
    """
    通用认证配置 - 用户声明式配置

    配置示例:
    ```json
    {
      "domain_pattern": "internal-api.example.com",
      "auth_type": "custom",
      "credentials": {
        "employee_id": "12345"
      },
      "request_modifiers": {
        "headers": {
          "X-User-ID": "{employee_id}",
          "X-Auth-Source": "yuxi-system"
        }
      }
    }
    ```
    """

    domain_pattern: str = Field(..., description="域名匹配 pattern，支持通配符 *.example.com")
    auth_type: str = Field(..., description="认证类型：none, basic, bearer, cookie, cookie_login, custom")
    credentials: dict[str, str] = Field(default_factory=dict, description="认证凭据，key-value 形式")
    request_modifiers: RequestModifiers | None = Field(None, description="请求修饰配置")
    description: str | None = Field(None, description="认证配置描述")


class FetcherContext(BaseModel):
    """
    请求上下文，用于认证器之间的信息传递
    """
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    cookies: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthenticatedFetcher(ABC):
    """
    认证器抽象基类

    所有具体认证器必须继承此类并实现抽象方法。

    生命周期:
    1. 构造函数接收 AuthConfig
    2. prepare() 在请求前被调用，注入认证信息
    3. fetch() 执行实际的 HTTP 请求
    4. is_expired() 检查认证是否过期 (有状态认证器)
    5. refresh() 刷新认证状态 (有状态认证器)
    """

    def __init__(self, config: AuthConfig):
        self.config = config

    @abstractmethod
    async def prepare(self, context: FetcherContext) -> FetcherContext:
        """
        在请求发出前注入认证信息

        Args:
            context: 请求上下文

        Returns:
            FetcherContext: 注入认证后的上下文
        """
        pass

    @abstractmethod
    async def fetch(self, url: str) -> tuple[bytes, str]:
        """
        执行 HTTP 请求

        Args:
            url: 目标 URL

        Returns:
            tuple[bytes, str]: (内容字节，最终 URL)

        Raises:
            ValueError: 认证失败或请求失败
        """
        pass

    def is_expired(self) -> bool:
        """
        检查认证是否过期

        默认实现返回 False，有状态认证器应重写此方法。

        Returns:
            bool: 是否过期
        """
        return False

    async def refresh(self) -> None:
        """
        刷新认证状态

        默认实现为空，有状态认证器应重写此方法。

        Raises:
            ValueError: 刷新失败
        """
        pass

    def _apply_config_modifiers(self, context: FetcherContext) -> FetcherContext:
        """
        应用配置中的 request_modifiers

        如果配置中没有 modifiers，返回原上下文。
        """
        if not self.config.request_modifiers:
            return context

        # 使用 httpx.Request 作为中间载体应用 modifiers
        request = httpx.Request(
            method="GET",
            url=context.url,
            headers=context.headers,
            cookies=context.cookies,
            params=context.params,
        )

        # 创建一个临时的 modifiers 实例来应用
        modifiers = self.config.request_modifiers
        modifiers.apply(request, self.config.credentials)

        # 提取结果
        return FetcherContext(
            url=str(request.url),
            headers=dict(request.headers),
            cookies=dict(request.cookies),
            params=dict(request.params),
            metadata=context.metadata,
        )


class FetcherException(Exception):
    """认证器异常基类"""

    def __init__(self, message: str, auth_type: str | None = None):
        super().__init__(message)
        self.message = message
        self.auth_type = auth_type

    def __str__(self):
        if self.auth_type:
            return f"[{self.auth_type}] {self.message}"
        return self.message


class AuthenticationError(FetcherException):
    """认证失败异常"""
    pass


class FetcherConfigurationError(FetcherException):
    """配置错误异常"""
    pass
