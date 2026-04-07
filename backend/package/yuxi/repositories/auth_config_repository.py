"""
认证配置 Repository

提供认证配置的增删改查操作，支持域名匹配查询。
"""

from __future__ import annotations

import fnmatch
from typing import Any

from sqlalchemy import select

from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_auth import AuthConfigModel
from yuxi.utils import logger

# 加密相关
from cryptography.fernet import Fernet
import os


class AuthConfigRepository:
    """
    认证配置数据访问层

    功能:
    - CRUD 操作
    - 域名匹配查询（支持通配符）
    - 凭据加密/解密
    """

    def __init__(self):
        self._encryption_key = self._get_encryption_key()
        self._cipher = Fernet(self._encryption_key) if self._encryption_key else None

    def _get_encryption_key(self) -> bytes | None:
        """
        获取加密密钥

        从环境变量 AUTH_ENCRYPTION_KEY 读取，如果未设置则返回 None（不加密）
        """
        key = os.getenv("AUTH_ENCRYPTION_KEY")
        if key:
            # 确保 key 是有效的 Fernet key
            try:
                return key.encode() if isinstance(key, str) else key
            except Exception:
                logger.warning("Invalid AUTH_ENCRYPTION_KEY format, encryption disabled")
        return None

    def _encrypt_credentials(self, credentials: dict[str, str]) -> str:
        """加密凭据"""
        import json
        if self._cipher:
            json_data = json.dumps(credentials, ensure_ascii=False).encode()
            encrypted = self._cipher.encrypt(json_data)
            return encrypted.decode()
        else:
            # 不加密，直接存储 JSON
            import json
            return json.dumps(credentials, ensure_ascii=False)

    def _decrypt_credentials(self, encrypted_data: str) -> dict[str, str]:
        """解密凭据"""
        import json
        if self._cipher:
            try:
                decrypted = self._cipher.decrypt(encrypted_data.encode())
                return json.loads(decrypted.decode())
            except Exception as e:
                logger.error(f"Failed to decrypt credentials: {e}")
                return {}
        else:
            # 不加密，直接解析 JSON
            try:
                return json.loads(encrypted_data)
            except Exception:
                return {}

    async def get_all(self) -> list[AuthConfigModel]:
        """获取所有认证配置"""
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(AuthConfigModel))
            return list(result.scalars().all())

    async def get_by_id(self, config_id: int) -> AuthConfigModel | None:
        """根据 ID 获取认证配置"""
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(AuthConfigModel).where(AuthConfigModel.id == config_id))
            return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> AuthConfigModel | None:
        """
        根据域名获取匹配的认证配置

        支持通配符匹配，如 *.example.com 匹配 api.example.com
        按照最具体匹配原则：完全匹配 > 通配符匹配 > 无匹配

        Args:
            domain: 目标域名

        Returns:
            AuthConfigModel | None: 匹配的认证配置
        """
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(AuthConfigModel))
            all_configs = list(result.scalars().all())

        if not all_configs:
            return None

        # 1. 尝试完全匹配
        for config in all_configs:
            if config.domain_pattern == domain:
                logger.debug(f"Auth config matched domain {domain} (exact match)")
                return config

        # 2. 尝试通配符匹配
        matching_configs = []
        for config in all_configs:
            if fnmatch.fnmatch(domain, config.domain_pattern):
                matching_configs.append(config)

        if matching_configs:
            # 选择最具体的匹配（通配符部分最少的）
            best_match = max(matching_configs, key=lambda c: len(c.domain_pattern) - c.domain_pattern.count("*"))
            logger.debug(f"Auth config matched domain {domain} (wildcard: {best_match.domain_pattern})")
            return best_match

        logger.debug(f"No auth config matched domain {domain}")
        return None

    async def create(self, data: dict[str, Any]) -> AuthConfigModel:
        """
        创建认证配置

        Args:
            data: 配置数据，应包含 domain_pattern, auth_type, credentials 等

        Returns:
            AuthConfigModel: 创建的配置对象
        """
        # 加密凭据
        if "credentials" in data:
            data["encrypted_credentials"] = self._encrypt_credentials(data.pop("credentials"))

        config = AuthConfigModel(**data)
        async with pg_manager.get_async_session_context() as session:
            session.add(config)
            await session.commit()
            await session.refresh(config)
        return config

    async def update(self, config_id: int, data: dict[str, Any]) -> AuthConfigModel | None:
        """
        更新认证配置

        Args:
            config_id: 配置 ID
            data: 更新数据

        Returns:
            AuthConfigModel | None: 更新后的配置对象
        """
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(AuthConfigModel).where(AuthConfigModel.id == config_id))
            config = result.scalar_one_or_none()

            if config is None:
                return None

            # 处理凭据加密
            if "credentials" in data:
                data["encrypted_credentials"] = self._encrypt_credentials(data.pop("credentials"))

            for key, value in data.items():
                setattr(config, key, value)

            await session.commit()
            await session.refresh(config)
        return config

    async def delete(self, config_id: int) -> bool:
        """
        删除认证配置

        Args:
            config_id: 配置 ID

        Returns:
            bool: 是否成功删除
        """
        async with pg_manager.get_async_session_context() as session:
            result = await session.execute(select(AuthConfigModel).where(AuthConfigModel.id == config_id))
            config = result.scalar_one_or_none()

            if config is None:
                return False

            await session.delete(config)
            await session.commit()
        return True

    def get_credentials(self, config: AuthConfigModel) -> dict[str, str]:
        """
        获取解密后的凭据

        Args:
            config: 认证配置对象

        Returns:
            dict[str, str]: 解密后的凭据
        """
        return self._decrypt_credentials(config.encrypted_credentials)

    def get_credentials_masked(self, config: AuthConfigModel) -> dict[str, str]:
        """
        获取脱敏后的凭据（用于 API 响应）

        Args:
            config: 认证配置对象

        Returns:
            dict[str, str]: 脱敏后的凭据（值显示为 ***）
        """
        credentials = self.get_credentials(config)
        return {key: "***" * (len(val) // 3) if len(val) > 3 else "***" for key, val in credentials.items()}
