"""
认证配置模型 - 用于存储内网系统的认证配置
"""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from yuxi.storage.postgres.models_business import Base
from yuxi.utils.datetime_utils import utc_now_naive

JSON_VALUE = JSON().with_variant(JSONB, "postgresql")


class AuthConfigModel(Base):
    """认证配置模型"""

    __tablename__ = "auth_configs"
    __table_args__ = (
        UniqueConstraint("id", name="uq_auth_configs_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 域名匹配 pattern，支持通配符 *.example.com
    domain_pattern = Column(String(255), nullable=False, index=True)

    # 认证类型：none, basic, bearer, cookie, cookie_login, custom
    auth_type = Column(String(32), nullable=False)

    # 加密存储的凭据 (使用 Fernet 加密)
    # 存储为 JSON 字符串格式
    encrypted_credentials = Column(Text, nullable=False)

    # 请求修饰配置 (headers, cookies, query_params)
    request_modifiers = Column(JSON_VALUE)

    # 认证配置描述
    description = Column(Text)

    # 创建者
    created_by = Column(String(64), nullable=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), default=utc_now_naive)
    updated_at = Column(DateTime(timezone=True), default=utc_now_naive, onupdate=utc_now_naive)

    def __repr__(self):
        return f"<AuthConfigModel id={self.id} domain={self.domain_pattern} type={self.auth_type}>"
