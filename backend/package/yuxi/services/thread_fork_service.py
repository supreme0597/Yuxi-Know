"""会话分叉 (Fork) 服务 —— 克隆 checkpoint 状态 + 复制业务消息到新会话

全部使用 SQLAlchemy ORM / expression language，无 text() 裸 SQL。
"""

import uuid as uuid_lib

from sqlalchemy import insert as sa_insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.repositories.checkpoint_repository import (
    build_ancestors_cte,
    select_checkpoint_parent,
)
from yuxi.repositories.conversation_repository import ConversationRepository
from yuxi.storage.postgres.checkpoint_tables import (
    checkpoint_blobs,
    checkpoints,
    checkpoint_writes,
)
from yuxi.storage.postgres.models_business import (
    Conversation,
    ConversationStats,
    Message,
    MessageFeedback,
    ToolCall,
)
from yuxi.utils.datetime_utils import utc_now_naive
from yuxi.utils.logging_config import logger


class ForkValidationError(Exception):
    """Fork 请求参数无效"""


async def _get_message(db: AsyncSession, message_id: int) -> Message | None:
    result = await db.execute(select(Message).where(Message.id == message_id))
    return result.scalar_one_or_none()


async def _clone_physical_files(thread_id_a: str, thread_id_b: str) -> None:
    """Phase 1: 克隆物理文件（Sandbox + MinIO）。

    当前为占位实现，等待 Sandbox Provisioner / MinIO 集成。
    """
    logger.info("Physical file clone skipped (not yet implemented): %s -> %s", thread_id_a, thread_id_b)


async def _cleanup_cloned_files(thread_id_b: str) -> None:
    """Best-effort 清理克隆失败后的残留物理文件。"""
    logger.info("Physical file cleanup skipped (not yet implemented): %s", thread_id_b)


async def fork_thread(
    db: AsyncSession,
    thread_id_a: str,
    message_id: int,
    title: str | None,
    user_id: str,
) -> dict:
    """执行 Fork 操作：从原会话指定消息处分叉出新会话。

    流程：Phase 1 物理文件克隆 → Phase 2 数据库事务克隆。
    """
    conv_repo = ConversationRepository(db)
    thread_id_b = str(uuid_lib.uuid4())

    # ---- Phase 1: 物理资源克隆 ----
    try:
        await _clone_physical_files(thread_id_a, thread_id_b)
    except Exception as e:
        raise ForkValidationError(f"文件克隆失败: {e}")

    # ---- 校验原会话 ----
    conversation_a = await conv_repo.get_conversation_by_thread_id(thread_id_a)
    if not conversation_a or conversation_a.user_id != str(user_id) or conversation_a.status == "deleted":
        await _cleanup_cloned_files(thread_id_b)
        raise ForkValidationError("对话线程不存在")
    conv_id_a = conversation_a.id

    # ---- 加锁原会话 ----
    await db.execute(
        select(Conversation.id).where(Conversation.thread_id == thread_id_a).with_for_update()
    )

    # ---- 定位目标消息与 request_id ----
    target_msg = await _get_message(db, message_id)
    if not target_msg or target_msg.conversation_id != conv_id_a:
        await _cleanup_cloned_files(thread_id_b)
        raise ForkValidationError("消息不存在或不属于该会话")

    if target_msg.role == "assistant":
        user_msgs = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv_id_a, Message.role == "user", Message.id <= message_id)
            .order_by(Message.id.desc())
            .limit(1),
        )
        target_msg = user_msgs.scalar_one_or_none()
        if not target_msg:
            await _cleanup_cloned_files(thread_id_b)
            raise ForkValidationError("未找到对应的用户消息")
        message_id = target_msg.id

    target_request_id = (target_msg.extra_metadata or {}).get("request_id")
    if not target_request_id:
        await _cleanup_cloned_files(thread_id_b)
        raise ForkValidationError("目标消息缺少 request_id，无法定位 checkpoint")

    # ---- 定位分叉回档起点 ----
    entry_result = await db.execute(select_checkpoint_parent(thread_id_a, target_request_id))
    entry_row = entry_result.fetchone()
    if not entry_row or not entry_row[0]:
        await _cleanup_cloned_files(thread_id_b)
        raise ForkValidationError("该消息之前没有可用的 AI 推理状态")
    target_checkpoint_id = entry_row[0]

    # ---- 递归 CTE 向上查找所有祖先 checkpoint ----
    ancestors_cte = build_ancestors_cte(thread_id_a, target_checkpoint_id)
    ancestors_result = await db.execute(select(ancestors_cte.c.checkpoint_id))
    ancestor_ids = [row[0] for row in ancestors_result.fetchall()]
    cloned_checkpoint_count = len(ancestor_ids)

    # ---- Phase 2: 数据库事务级克隆 ----
    try:
        # 1. 创建新会话
        fork_title = title or f"{conversation_a.title or '未命名'}_分叉"
        new_conversation = Conversation(
            thread_id=thread_id_b,
            user_id=str(user_id),
            agent_id=conversation_a.agent_id,
            title=fork_title,
            status="active",
            extra_metadata=dict(conversation_a.extra_metadata or {}),
        )
        db.add(new_conversation)
        await db.flush()
        conv_id_b = new_conversation.id

        # 2. 克隆 checkpoints —— INSERT ... SELECT via from_select()
        ckpt_cols = [
            "thread_id", "checkpoint_ns", "checkpoint_id",
            "parent_checkpoint_id", "type", "checkpoint", "metadata",
        ]
        await db.execute(
            sa_insert(checkpoints).from_select(
                ckpt_cols,
                select(
                    *[checkpoints.c[col] for col in ckpt_cols]
                ).where(
                    checkpoints.c.thread_id == thread_id_a,
                    checkpoints.c.checkpoint_id.in_(ancestor_ids),
                ),
            )
        )

        # 3. 克隆 checkpoint_writes
        cw_cols = [
            "thread_id", "checkpoint_ns", "checkpoint_id",
            "task_id", "idx", "channel", "type", "blob", "task_path",
        ]
        await db.execute(
            sa_insert(checkpoint_writes).from_select(
                cw_cols,
                select(
                    *[checkpoint_writes.c[col] for col in cw_cols]
                ).where(
                    checkpoint_writes.c.thread_id == thread_id_a,
                    checkpoint_writes.c.checkpoint_id.in_(ancestor_ids),
                ),
            )
        )

        # 4. 克隆 checkpoint_blobs —— 从祖先 checkpoint 提取 (channel, version)，去重后克隆
        ancestor_ckpts_result = await db.execute(
            select(checkpoints.c.checkpoint).where(
                checkpoints.c.thread_id == thread_id_a,
                checkpoints.c.checkpoint_id.in_(ancestor_ids),
            )
        )
        blob_pairs: set[tuple[str, str]] = set()
        for (ckpt_json,) in ancestor_ckpts_result.fetchall():
            channel_versions = (ckpt_json or {}).get("channel_versions", {}) or {}
            for ch, ver in channel_versions.items():
                blob_pairs.add((ch, ver))

        if blob_pairs:
            # 查询原 thread 下匹配的 blobs
            conditions = []
            for ch, ver in blob_pairs:
                conditions.append((checkpoint_blobs.c.channel == ch) & (checkpoint_blobs.c.version == ver))
            blob_rows_result = await db.execute(
                select(checkpoint_blobs).where(
                    checkpoint_blobs.c.thread_id == thread_id_a,
                    conditions[0] if len(conditions) == 1 else None,
                )
            )
            # 对多种 pair 的情况，逐对查询
            if len(blob_pairs) > 1:
                all_rows = []
                for ch, ver in blob_pairs:
                    pair_result = await db.execute(
                        select(checkpoint_blobs).where(
                            checkpoint_blobs.c.thread_id == thread_id_a,
                            checkpoint_blobs.c.channel == ch,
                            checkpoint_blobs.c.version == ver,
                        )
                    )
                    all_rows.extend(pair_result.fetchall())
            else:
                all_rows = blob_rows_result.fetchall()

            # 插入新 thread_id
            for row in all_rows:
                await db.execute(
                    sa_insert(checkpoint_blobs).values(
                        thread_id=thread_id_b,
                        checkpoint_ns=row.checkpoint_ns,
                        channel=row.channel,
                        version=row.version,
                        type=row.type,
                        blob=row.blob,
                    )
                )

        # 5. 查询源消息（Python 侧过滤已删除）
        src_messages_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv_id_a, Message.id <= message_id)
            .order_by(Message.id.asc()),
        )
        src_messages = [
            m for m in src_messages_result.scalars().all()
            if (m.extra_metadata or {}).get("is_deleted") != "true"
        ]

        # 6. 逐条克隆消息，建立 old_id → new_id 映射
        id_map: dict[int, int] = {}
        for msg in src_messages:
            new_msg = Message(
                conversation_id=conv_id_b,
                role=msg.role,
                content=msg.content,
                message_type=msg.message_type,
                image_content=msg.image_content,
                extra_metadata=dict(msg.extra_metadata or {}),
                token_count=msg.token_count,
                created_at=msg.created_at,
            )
            db.add(new_msg)
            await db.flush()
            id_map[msg.id] = new_msg.id

        # 7. 克隆 tool_calls
        if src_messages:
            old_ids = list(id_map.keys())
            src_tool_calls_result = await db.execute(
                select(ToolCall).where(ToolCall.message_id.in_(old_ids))
            )
            for tc in src_tool_calls_result.scalars().all():
                db.add(ToolCall(
                    message_id=id_map[tc.message_id],
                    tool_name=tc.tool_name,
                    tool_input=tc.tool_input,
                    tool_output=tc.tool_output,
                    status=tc.status,
                    error_message=tc.error_message,
                    langgraph_tool_call_id=tc.langgraph_tool_call_id,
                    created_at=tc.created_at,
                ))

        # 8. 克隆 message_feedbacks
        if src_messages:
            src_feedbacks_result = await db.execute(
                select(MessageFeedback).where(MessageFeedback.message_id.in_(old_ids))
            )
            for fb in src_feedbacks_result.scalars().all():
                db.add(MessageFeedback(
                    message_id=id_map[fb.message_id],
                    user_id=fb.user_id,
                    rating=fb.rating,
                    reason=fb.reason,
                    created_at=fb.created_at,
                ))

        # 9. 计算克隆统计（Python 侧）
        cloned_msg_count = len(src_messages)
        cloned_token_count = sum(m.token_count or 0 for m in src_messages)

        # 10. 初始化新会话统计
        stats_a_result = await db.execute(
            select(ConversationStats).where(ConversationStats.conversation_id == conv_id_a)
        )
        stats_a = stats_a_result.scalar_one_or_none()

        db.add(ConversationStats(
            conversation_id=conv_id_b,
            message_count=cloned_msg_count,
            total_tokens=cloned_token_count,
            model_used=stats_a.model_used if stats_a else None,
            created_at=utc_now_naive(),
            updated_at=utc_now_naive(),
        ))

        await db.flush()

        logger.info(
            "Fork thread %s -> %s, cloned %d messages, %d checkpoints",
            thread_id_a, thread_id_b, cloned_msg_count, cloned_checkpoint_count,
        )

        return {
            "message": "分叉成功",
            "new_thread_id": thread_id_b,
            "cloned_message_count": cloned_msg_count,
            "cloned_checkpoint_count": cloned_checkpoint_count,
        }

    except Exception:
        await _cleanup_cloned_files(thread_id_b)
        raise
