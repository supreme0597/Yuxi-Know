from __future__ import annotations

import pytest

from yuxi.models.providers.share import (
    DEFAULT_PROVIDER_SHARE_CONFIG,
    normalize_provider_share_config,
    user_can_access_provider,
    user_can_manage_provider,
)
from yuxi.storage.postgres.models_business import ModelProvider, User


def _user(uid: str, role: str = "user", department_id: int | None = 1) -> User:
    return User(
        username=uid,
        uid=uid,
        password_hash="x",
        role=role,
        department_id=department_id,
    )


def _provider(
    provider_id: str = "openai-test",
    created_by: str = "creator",
    share_config: dict | None = None,
    is_builtin: bool = False,
) -> ModelProvider:
    return ModelProvider(
        provider_id=provider_id,
        display_name="Test",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        capabilities=["chat"],
        enabled_models=[],
        created_by=created_by,
        is_builtin=is_builtin,
        share_config=share_config or DEFAULT_PROVIDER_SHARE_CONFIG.copy(),
    )


# ---------- normalize ----------

def test_normalize_global_default():
    out = normalize_provider_share_config(None, user_uid="u1", department_id=1)
    assert out == {"access_level": "global", "department_ids": [], "user_uids": []}


def test_normalize_department_appends_user_dept():
    out = normalize_provider_share_config(
        {"access_level": "department", "department_ids": [2]},
        user_uid="u1",
        department_id=1,
    )
    assert out == {"access_level": "department", "department_ids": [1, 2], "user_uids": []}


def test_normalize_user_appends_user_uid():
    out = normalize_provider_share_config(
        {"access_level": "user", "user_uids": ["other"]},
        user_uid="u1",
    )
    assert out == {"access_level": "user", "department_ids": [], "user_uids": ["other", "u1"]}


def test_normalize_force_private_returns_user_only():
    out = normalize_provider_share_config(
        {"access_level": "global", "department_ids": [], "user_uids": []},
        user_uid="u1",
        force_private=True,
    )
    assert out == {"access_level": "user", "department_ids": [], "user_uids": ["u1"]}


def test_normalize_force_private_without_uid_raises():
    with pytest.raises(ValueError, match="私有"):
        normalize_provider_share_config(None, force_private=True)


def test_normalize_invalid_access_level_raises():
    with pytest.raises(ValueError, match="无效"):
        normalize_provider_share_config({"access_level": "public"})


# ---------- access ----------

def test_superadmin_can_access_anything():
    admin = _user("admin", role="superadmin")
    p = _provider(created_by="other", share_config={"access_level": "user", "department_ids": [], "user_uids": ["someone"]})
    assert user_can_access_provider(admin, p) is True


def test_creator_can_access_own_provider():
    u = _user("u1")
    p = _provider(created_by="u1", share_config={"access_level": "user", "department_ids": [], "user_uids": []})
    assert user_can_access_provider(u, p) is True


def test_global_access_for_any_user():
    u = _user("u1", department_id=2)
    p = _provider(created_by="other", share_config={"access_level": "global", "department_ids": [], "user_uids": []})
    assert user_can_access_provider(u, p) is True


def test_department_access_same_dept():
    u = _user("u1", department_id=1)
    p = _provider(created_by="other", share_config={"access_level": "department", "department_ids": [1], "user_uids": []})
    assert user_can_access_provider(u, p) is True


def test_department_access_other_dept_denied():
    u = _user("u1", department_id=2)
    p = _provider(created_by="other", share_config={"access_level": "department", "department_ids": [1], "user_uids": []})
    assert user_can_access_provider(u, p) is False


def test_department_access_no_dept_denied():
    u = _user("u1", department_id=None)
    p = _provider(created_by="other", share_config={"access_level": "department", "department_ids": [1], "user_uids": []})
    assert user_can_access_provider(u, p) is False


def test_user_access_in_list():
    u = _user("u1")
    p = _provider(created_by="other", share_config={"access_level": "user", "department_ids": [], "user_uids": ["u1"]})
    assert user_can_access_provider(u, p) is True


def test_user_access_not_in_list_denied():
    u = _user("u1")
    p = _provider(created_by="other", share_config={"access_level": "user", "department_ids": [], "user_uids": ["u2"]})
    assert user_can_access_provider(u, p) is False


# ---------- manage ----------

def test_admin_cannot_manage_others_non_builtin():
    """管理权仅归属创建人：admin 对被共享的普通供应商也不可管理。"""
    u = _user("admin", role="admin")
    p = _provider(created_by="other")
    assert user_can_manage_provider(u, p) is False


def test_admin_can_manage_builtin_provider():
    """内置供应商视为系统级资源，由管理员管理。"""
    u = _user("admin", role="admin")
    p = _provider(created_by="system", is_builtin=True)
    assert user_can_manage_provider(u, p) is True


def test_normal_user_cannot_manage_builtin_provider():
    """普通用户不能管理内置供应商。"""
    u = _user("u1")
    p = _provider(created_by="system", is_builtin=True)
    assert user_can_manage_provider(u, p) is False


def test_admin_can_manage_provider_without_creator():
    """历史数据未记录创建人的供应商视为系统级资源，由管理员管理。"""
    u = _user("admin", role="admin")
    p = _provider(created_by=None)
    assert user_can_manage_provider(u, p) is True


def test_normal_user_cannot_manage_provider_without_creator():
    """历史数据未记录创建人的供应商，普通用户不可管理。"""
    u = _user("u1")
    p = _provider(created_by=None)
    assert user_can_manage_provider(u, p) is False


def test_superadmin_can_manage_others_non_builtin():
    """superadmin 兜底可管理任何普通供应商。"""
    u = _user("admin", role="superadmin")
    p = _provider(created_by="other")
    assert user_can_manage_provider(u, p) is True


def test_normal_user_can_manage_own():
    u = _user("u1")
    p = _provider(created_by="u1")
    assert user_can_manage_provider(u, p) is True


def test_normal_user_cannot_manage_others():
    u = _user("u1")
    p = _provider(created_by="other")
    assert user_can_manage_provider(u, p) is False
