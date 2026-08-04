from __future__ import annotations

from datetime import timedelta

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from yuxi.repositories.conversation_share_repository import ConversationShareRepository
from yuxi.services.share_service import (
    create_share,
    get_share,
    get_shared_thread_state,
    get_shared_thread_view,
    revoke_share,
)
from yuxi.storage.postgres.models_business import (
    Base,
    Conversation,
    Department,
    Message,
    MessageFeedback,
    User,
)
from yuxi.utils.datetime_utils import utc_now_naive

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


@pytest_asyncio.fixture()
async def share_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        dept = Department(name="Dept")
        owner = User(
            username="Owner",
            uid="owner_uid",
            password_hash="$argon2id$placeholder",
            role="user",
            department=dept,
        )
        other = User(
            username="Other",
            uid="other_uid",
            password_hash="$argon2id$placeholder",
            role="user",
            department=dept,
        )
        now = utc_now_naive()
        conversation = Conversation(
            thread_id="thread-shared",
            uid="owner_uid",
            agent_id="agent-shared",
            title="Shared conversation",
            status="active",
            created_at=now,
            updated_at=now,
        )
        message = Message(conversation=conversation, role="assistant", content="Hello", created_at=now)
        feedback = MessageFeedback(message=message, uid="owner_uid", rating="like", created_at=now)
        db.add_all([dept, owner, other, conversation, message, feedback])
        await db.commit()
        for item in [dept, owner, other, conversation, message, feedback]:
            await db.refresh(item)
        yield {"db": db, "owner": owner, "other": other, "conversation": conversation}
    await engine.dispose()


async def test_create_share_by_owner(share_session):
    result = await create_share(
        thread_id="thread-shared",
        owner_uid="owner_uid",
        expires_days=7,
        db=share_session["db"],
    )
    assert result["token"]
    assert len(result["token"]) >= 32


async def test_create_share_idempotent_reuse(share_session):
    first = await create_share(
        thread_id="thread-shared",
        owner_uid="owner_uid",
        expires_days=7,
        db=share_session["db"],
    )
    second = await create_share(
        thread_id="thread-shared",
        owner_uid="owner_uid",
        expires_days=30,
        db=share_session["db"],
    )
    assert first["token"] == second["token"]
    assert first["expires_at"] == second["expires_at"]


async def test_create_share_rejects_non_owner(share_session):
    with pytest.raises(HTTPException) as exc:
        await create_share(
            thread_id="thread-shared",
            owner_uid="other_uid",
            expires_days=7,
            db=share_session["db"],
        )
    assert exc.value.status_code == 404


async def test_create_share_rejects_invalid_expiry(share_session):
    with pytest.raises(HTTPException) as exc:
        await create_share(
            thread_id="thread-shared",
            owner_uid="owner_uid",
            expires_days=0,
            db=share_session["db"],
        )
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        await create_share(
            thread_id="thread-shared",
            owner_uid="owner_uid",
            expires_days=366,
            db=share_session["db"],
        )
    assert exc.value.status_code == 400


async def test_get_share_owner_view(share_session):
    await create_share(
        thread_id="thread-shared",
        owner_uid="owner_uid",
        expires_days=7,
        db=share_session["db"],
    )
    result = await get_share(thread_id="thread-shared", owner_uid="owner_uid", db=share_session["db"])
    assert result is not None
    assert result["token"]


async def test_get_share_none_when_not_shared(share_session):
    result = await get_share(thread_id="thread-shared", owner_uid="owner_uid", db=share_session["db"])
    assert result is None


async def test_shared_view_valid_token_returns_history_without_feedback(share_session):
    created = await create_share(
        thread_id="thread-shared",
        owner_uid="owner_uid",
        expires_days=7,
        db=share_session["db"],
    )
    result = await get_shared_thread_view(
        thread_id="thread-shared",
        token=created["token"],
        db=share_session["db"],
    )
    assert result["thread_id"] == "thread-shared"
    assert result["title"] == "Shared conversation"
    assert "uid" not in result
    assert len(result["history"]) == 1
    message = result["history"][0]
    assert message["content"] == "Hello"
    assert message["feedback"] is None


async def test_shared_view_wrong_token_returns_404(share_session):
    with pytest.raises(HTTPException) as exc:
        await get_shared_thread_view(
            thread_id="thread-shared",
            token="invalid-token",
            db=share_session["db"],
        )
    assert exc.value.status_code == 404


async def test_shared_view_revoked_share_returns_404(share_session):
    created = await create_share(
        thread_id="thread-shared",
        owner_uid="owner_uid",
        expires_days=7,
        db=share_session["db"],
    )
    await revoke_share(thread_id="thread-shared", owner_uid="owner_uid", db=share_session["db"])
    with pytest.raises(HTTPException) as exc:
        await get_shared_thread_view(
            thread_id="thread-shared",
            token=created["token"],
            db=share_session["db"],
        )
    assert exc.value.status_code == 404


async def test_shared_view_expired_share_returns_404(share_session):
    now = utc_now_naive()
    repo = ConversationShareRepository(share_session["db"])
    share = await repo.create(
        thread_id="thread-shared",
        token="expired-token",
        created_by="owner_uid",
        expires_at=now - timedelta(days=1),
    )
    await share_session["db"].commit()
    assert share.id is not None

    with pytest.raises(HTTPException) as exc:
        await get_shared_thread_view(
            thread_id="thread-shared",
            token="expired-token",
            db=share_session["db"],
        )
    assert exc.value.status_code == 404


async def test_shared_state_invalid_token_returns_404(share_session):
    with pytest.raises(HTTPException) as exc:
        await get_shared_thread_state(
            thread_id="thread-shared",
            token="invalid-token",
            db=share_session["db"],
        )
    assert exc.value.status_code == 404
