"""ScheduleRepository 纯 CRUD 仓储方法的单元测试。

owner 过滤以「按 uid 带入查询条件」的方式由仓储实现（get_by_id(uid=...) /
list_schedules(uid=...)）；admin/超管可见范围等角色逻辑仍留在路由/工具层。
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

# 必须在 import yuxi.* 之前设置，避免 yuxi/__init__.py 中的 config 加载抛错。
os.environ.setdefault("YUXI_SKIP_APP_INIT", "1")
os.environ.setdefault("OPENAI_API_KEY", "test-dummy-key")

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from yuxi.repositories.schedule_repository import ScheduleRepository
from yuxi.storage.postgres.models_business import (
    Base as BusinessBase,
)
from yuxi.storage.postgres.models_business import ScheduleDefinition, ScheduleLog


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def db_session():
    """Provide an async SQLAlchemy session backed by an isolated SQLite in-memory DB.

    Foreign-key enforcement is disabled so tests can create rows without seeding
    the full parent table graph (users / departments / agent_configs). Each test
    gets a fresh, isolated schema.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk_off(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(BusinessBase.metadata.create_all)

    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with Session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(BusinessBase.metadata.drop_all)
    await engine.dispose()


async def _make_schedule(db: AsyncSession, *, schedule_id: str, user_id: str) -> ScheduleDefinition:
    sched = ScheduleDefinition(
        id=schedule_id,
        name=f"s-{schedule_id}",
        uid=user_id,
        agent_slug="agent-1",
        cron_expr="0 * * * *",
        timezone="Asia/Shanghai",
        query="hi",
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    return sched


async def _make_log(db: AsyncSession, *, schedule_id: str) -> ScheduleLog:
    log = ScheduleLog(
        id=str(uuid.uuid4()),
        schedule_id=schedule_id,
        run_id=str(uuid.uuid4()),
        thread_id=str(uuid.uuid4()),
        status="triggered",
        execution_status="pending",
        trigger_delay_ms=0,
        created_at=datetime.now(UTC),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# 纯 CRUD（owner 过滤已上移到路由/工具层，仓储只做无歧义的数据访问）
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_row(db_session: AsyncSession) -> None:
    repo = ScheduleRepository(db_session)
    await _make_schedule(db_session, schedule_id="s1", user_id="u1")

    result = await repo.get_by_id("s1")

    assert result is not None
    assert result.id == "s1"


async def test_get_by_id_returns_none_for_missing(db_session: AsyncSession) -> None:
    repo = ScheduleRepository(db_session)
    assert await repo.get_by_id("nope") is None


async def test_get_by_id_with_uid_filters_by_owner(db_session: AsyncSession) -> None:
    repo = ScheduleRepository(db_session)
    await _make_schedule(db_session, schedule_id="s1", user_id="u1")
    await _make_schedule(db_session, schedule_id="s2", user_id="u2")

    own = await repo.get_by_id("s1", uid="u1")
    assert own is not None and own.id == "s1"

    # 非 owner：SQL 层直接返回 None
    assert await repo.get_by_id("s1", uid="u2") is None
    # 不存在的 id
    assert await repo.get_by_id("nope", uid="u1") is None
    # 不带 uid 时不限归属
    assert await repo.get_by_id("s2") is not None


async def test_update_schedule_modifies_row(db_session: AsyncSession) -> None:
    repo = ScheduleRepository(db_session)
    await _make_schedule(db_session, schedule_id="s2", user_id="u1")

    result = await repo.update_schedule("s2", {"name": "renamed"})

    assert result is not None
    assert result.name == "renamed"


async def test_update_schedule_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = ScheduleRepository(db_session)
    assert await repo.update_schedule("s2", {"name": "renamed"}) is None


async def test_delete_schedule_removes_row(db_session: AsyncSession) -> None:
    repo = ScheduleRepository(db_session)
    await _make_schedule(db_session, schedule_id="s3", user_id="u1")

    deleted = await repo.delete_schedule("s3")

    assert deleted is True
    assert await repo.get_by_id("s3") is None


async def test_delete_schedule_returns_false_when_missing(db_session: AsyncSession) -> None:
    repo = ScheduleRepository(db_session)
    assert await repo.delete_schedule("s3") is False


async def test_list_schedules_filters_by_owner_uid(db_session: AsyncSession) -> None:
    repo = ScheduleRepository(db_session)
    await _make_schedule(db_session, schedule_id="s1", user_id="u1")
    await _make_schedule(db_session, schedule_id="s2", user_id="u2")

    own = await repo.list_schedules(uid="u1")
    assert {s.id for s in own} == {"s1"}

    all_rows = await repo.list_schedules(uid=None)
    assert {s.id for s in all_rows} == {"s1", "s2"}


async def test_get_logs_by_schedule_id(db_session: AsyncSession) -> None:
    repo = ScheduleRepository(db_session)
    await _make_schedule(db_session, schedule_id="s4", user_id="u1")
    await _make_log(db_session, schedule_id="s4")

    logs = await repo.get_logs_by_schedule_id("s4", limit=20, offset=0)
    assert len(logs) == 1

    assert await repo.get_logs_by_schedule_id("s9") == []
