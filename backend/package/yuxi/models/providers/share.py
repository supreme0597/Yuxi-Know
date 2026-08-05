"""模型供应商共享权限工具。"""

from __future__ import annotations

from yuxi.repositories.agent_repository import ADMIN_ROLES
from yuxi.storage.postgres.models_business import ModelProvider, User
from yuxi.utils.share_config import EMPTY_SHARE_CONFIG, normalize_share_config

DEFAULT_PROVIDER_SHARE_CONFIG = EMPTY_SHARE_CONFIG.copy()


def normalize_provider_share_config(
    share_config: dict | None,
    *,
    user_uid: str | None = None,
    department_id: int | str | None = None,
    force_private: bool = False,
) -> dict:
    """规整模型供应商 share_config。非管理员角色创建时默认私有。"""
    if force_private:
        if not user_uid:
            raise ValueError("私有模型供应商必须绑定创建用户")
        return {"access_level": "user", "department_ids": [], "user_uids": [str(user_uid)]}

    return normalize_share_config(
        share_config,
        default_config=DEFAULT_PROVIDER_SHARE_CONFIG,
        default_access_level="global",
        invalid_access_level_message="无效的模型供应商权限等级",
        user_uid=user_uid,
        department_id=department_id,
    )


def user_can_access_provider(user: User, provider: ModelProvider) -> bool:
    """用户是否对该 provider 拥有可见/可使用权。"""
    if user.role == "superadmin":
        return True
    user_uid = str(user.uid)
    if provider.created_by == user_uid:
        return True

    share_config = provider.share_config if provider.share_config is not None else DEFAULT_PROVIDER_SHARE_CONFIG.copy()
    access_level = share_config.get("access_level")

    if access_level == "global":
        return True

    if access_level == "department":
        if user.department_id is None:
            return False
        try:
            return int(user.department_id) in [int(v) for v in share_config.get("department_ids") or []]
        except (TypeError, ValueError):
            return False

    if access_level == "user":
        return user_uid in (share_config.get("user_uids") or [])

    return False


def user_can_manage_provider(user: User, provider: ModelProvider) -> bool:
    """用户是否能修改/删除该 provider。

    superadmin 兜底可管理全部；内置供应商与历史未记录创建人的供应商视为系统级资源，由管理员管理；
    其余供应商管理权仅归属创建人，被共享给其他用户（含 admin）的供应商不可由非创建人编辑。
    """
    if user.role == "superadmin":
        return True
    if provider.is_builtin:
        return user.role in ADMIN_ROLES
    created_by = provider.created_by
    if not created_by:
        return user.role in ADMIN_ROLES
    return created_by == str(user.uid)
