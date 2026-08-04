"""Conversation share repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.storage.postgres.models_business import ConversationShare
from yuxi.utils.datetime_utils import utc_now_naive


class ConversationShareRepository:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create(
        self,
        *,
        thread_id: str,
        token: str,
        created_by: str,
        expires_at: datetime,
    ) -> ConversationShare:
        """创建一条对话分享记录。"""
        item = ConversationShare(
            thread_id=thread_id,
            token=token,
            created_by=str(created_by),
            expires_at=expires_at,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_active_by_thread(self, thread_id: str) -> ConversationShare | None:
        """查询指定会话当前有效（未撤销且未过期）的分享。"""
        now = utc_now_naive()
        result = await self.db.execute(
            select(ConversationShare).where(
                ConversationShare.thread_id == thread_id,
                ConversationShare.is_revoked.is_(False),
                ConversationShare.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, thread_id: str, token: str) -> ConversationShare | None:
        """按会话与 token 查询分享记录（不校验有效性，由调用方判断）。"""
        result = await self.db.execute(
            select(ConversationShare).where(
                ConversationShare.thread_id == thread_id,
                ConversationShare.token == token,
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, share_id: int) -> None:
        """撤销分享，标记 is_revoked。"""
        item = await self.db.get(ConversationShare, share_id)
        if item is not None:
            item.is_revoked = True
            await self.db.flush()
