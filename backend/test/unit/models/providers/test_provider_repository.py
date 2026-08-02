"""模型供应商仓库层单元测试 - 可见性过滤与引用计数。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from yuxi.models.providers.repository import (
    count_provider_references,
    get_visible_model_provider,
    list_visible_model_providers,
)
from yuxi.models.providers.share import DEFAULT_PROVIDER_SHARE_CONFIG
from yuxi.storage.postgres.models_business import ModelProvider, User


def _user(uid, role="user", department_id=1):
    return User(username=uid, uid=uid, password_hash="x", role=role, department_id=department_id)


def _provider(provider_id, created_by="creator", share=None):
    return ModelProvider(
        provider_id=provider_id,
        display_name=provider_id,
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        capabilities=["chat"],
        enabled_models=[],
        created_by=created_by,
        share_config=share or DEFAULT_PROVIDER_SHARE_CONFIG.copy(),
    )


def _make_db(rows):
    """构造一个支持 await db.execute(...).scalars().all() 以及 .scalar_one_or_none() 的 mock。"""
    scalars = MagicMock()
    scalars.all.return_value = rows
    scalars.scalar_one_or_none.return_value = rows[0] if rows else None
    result = MagicMock()
    result.scalars.return_value = scalars
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    execute = AsyncMock(return_value=result)
    db = MagicMock()
    db.execute = execute
    return db


# ---------- list_visible ----------


@pytest.mark.asyncio
async def test_list_visible_superadmin_returns_all():
    db = _make_db([_provider("p1"), _provider("p2")])
    admin = _user("admin", role="superadmin")
    result = await list_visible_model_providers(db, admin)
    assert {p.provider_id for p in result} == {"p1", "p2"}


@pytest.mark.asyncio
async def test_list_visible_normal_user_filters_by_access():
    rows = [
        _provider("global", share={"access_level": "global", "department_ids": [], "user_uids": []}),
        _provider("private", share={"access_level": "user", "department_ids": [], "user_uids": ["u1"]}),
        _provider("hidden", share={"access_level": "user", "department_ids": [], "user_uids": ["other"]}),
    ]
    db = _make_db(rows)
    u = _user("u1")
    result = await list_visible_model_providers(db, u)
    assert {p.provider_id for p in result} == {"global", "private"}


# ---------- get_visible ----------


@pytest.mark.asyncio
async def test_get_visible_returns_none_for_inaccessible():
    db = _make_db(
        [
            _provider(
                "p1",
                created_by="other",
                share={"access_level": "user", "department_ids": [], "user_uids": ["someone"]},
            )
        ]
    )
    u = _user("u1")
    result = await get_visible_model_provider(db, "p1", u)
    assert result is None


@pytest.mark.asyncio
async def test_get_visible_returns_provider_when_accessible():
    db = _make_db([_provider("p1", share=DEFAULT_PROVIDER_SHARE_CONFIG.copy())])
    u = _user("u1")
    result = await get_visible_model_provider(db, "p1", u)
    assert result is not None
    assert result.provider_id == "p1"
