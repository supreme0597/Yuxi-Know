"""对话分享服务 - 匿名只读访问与分享管理。"""

from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.repositories.conversation_repository import ConversationRepository
from yuxi.repositories.conversation_share_repository import ConversationShareRepository
from yuxi.repositories.user_repository import UserRepository
from yuxi.services.chat_service import get_agent_state_view
from yuxi.services.conversation_service import get_thread_history_view
from yuxi.services.thread_files_service import (
    list_thread_files_view,
    read_thread_file_content_view,
    resolve_thread_artifact_view,
)
from yuxi.storage.postgres.models_business import ConversationShare, User
from yuxi.utils.datetime_utils import format_utc_datetime, utc_now_naive

MAX_SHARE_EXPIRES_DAYS = 365
SHARE_ARTIFACT_PREFIX_TEMPLATE = "/api/chat/thread/{thread_id}/artifacts/"


def _share_artifact_url(thread_id: str, path: str, token: str) -> str:
    """把需登录的 chat artifact URL 改写为公开 share artifact URL。"""
    path = path.lstrip("/")
    return f"/api/share/{thread_id}/artifacts/{path}?token={token}"


def _rewrite_artifact_urls(history: list[dict], thread_id: str, token: str) -> list[dict]:
    """改写历史消息中附件的 artifact_url / original_artifact_url 指向公开分享端点。"""
    old_prefix = SHARE_ARTIFACT_PREFIX_TEMPLATE.format(thread_id=thread_id)
    for msg in history:
        extra_metadata = msg.get("extra_metadata") or {}
        attachments = extra_metadata.get("attachments") or []
        for attachment in attachments:
            for field in ("artifact_url", "original_artifact_url"):
                url = attachment.get(field)
                if url and url.startswith(old_prefix):
                    relative = url[len(old_prefix) :]
                    attachment[field] = _share_artifact_url(thread_id, relative, token)
    return history


async def _validate_share(*, thread_id: str, token: str, db: AsyncSession) -> ConversationShare:
    """校验分享 token 有效性，失败统一 404（避免枚举）。"""
    share_repo = ConversationShareRepository(db)
    share = await share_repo.get_by_token(thread_id=thread_id, token=token)
    if not share or share.is_revoked or share.expires_at <= utc_now_naive():
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")
    return share


async def _get_owner_user(*, db: AsyncSession, owner_uid: str) -> User:
    user = await UserRepository().get_by_uid_with_db(db, owner_uid)
    if user is None:
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")
    return user


async def _require_owner_conversation(*, thread_id: str, owner_uid: str, db: AsyncSession):
    """校验当前用户是该会话的拥有者，否则 404。"""
    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get_conversation_by_thread_id(thread_id)
    if not conversation or conversation.uid != str(owner_uid) or conversation.status == "deleted":
        raise HTTPException(status_code=404, detail="对话线程不存在")
    return conversation


async def create_share(*, thread_id: str, owner_uid: str, expires_days: int, db: AsyncSession) -> dict:
    """创建分享，若已存在有效分享则复用返回（幂等）。仅会话拥有者可操作。"""
    if expires_days < 1 or expires_days > MAX_SHARE_EXPIRES_DAYS:
        raise HTTPException(status_code=400, detail=f"有效期需在 1~{MAX_SHARE_EXPIRES_DAYS} 天之间")

    await _require_owner_conversation(thread_id=thread_id, owner_uid=owner_uid, db=db)

    share_repo = ConversationShareRepository(db)
    existing = await share_repo.get_active_by_thread(thread_id)
    if existing:
        return {
            "token": existing.token,
            "expires_at": format_utc_datetime(existing.expires_at),
        }

    token = secrets.token_urlsafe(32)
    expires_at = utc_now_naive() + timedelta(days=expires_days)
    await share_repo.create(
        thread_id=thread_id,
        token=token,
        created_by=str(owner_uid),
        expires_at=expires_at,
    )
    return {
        "token": token,
        "expires_at": format_utc_datetime(expires_at),
    }


async def get_share(*, thread_id: str, owner_uid: str, db: AsyncSession) -> dict | None:
    """查询当前有效分享（owner 视角）。"""
    await _require_owner_conversation(thread_id=thread_id, owner_uid=owner_uid, db=db)

    share_repo = ConversationShareRepository(db)
    share = await share_repo.get_active_by_thread(thread_id)
    if not share:
        return None
    return {
        "token": share.token,
        "expires_at": format_utc_datetime(share.expires_at),
    }


async def revoke_share(*, thread_id: str, owner_uid: str, db: AsyncSession) -> None:
    """撤销分享。"""
    await _require_owner_conversation(thread_id=thread_id, owner_uid=owner_uid, db=db)

    share_repo = ConversationShareRepository(db)
    share = await share_repo.get_active_by_thread(thread_id)
    if share:
        await share_repo.revoke(share.id)


async def get_shared_thread_view(*, thread_id: str, token: str, db: AsyncSession) -> dict:
    """公开读：会话元信息 + 历史消息（含工具调用，不含 feedback）。"""
    await _validate_share(thread_id=thread_id, token=token, db=db)

    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get_conversation_by_thread_id(thread_id)
    if not conversation or conversation.status == "deleted":
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")

    history = await get_thread_history_view(
        thread_id=thread_id,
        current_uid=str(conversation.uid),
        db=db,
        include_feedback=False,
        require_owner=False,
    )
    history["history"] = _rewrite_artifact_urls(history["history"], thread_id, token)

    return {
        "thread_id": conversation.thread_id,
        "title": conversation.title,
        "agent_id": conversation.agent_id,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
        "history": history["history"],
    }


async def get_shared_thread_state(*, thread_id: str, token: str, db: AsyncSession) -> dict:
    """公开读：agent_state（去除需登录的子代理运行 URL）。"""
    await _validate_share(thread_id=thread_id, token=token, db=db)

    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get_conversation_by_thread_id(thread_id)
    if not conversation or conversation.status == "deleted":
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")

    owner_user = await _get_owner_user(db=db, owner_uid=str(conversation.uid))
    state_response = await get_agent_state_view(
        thread_id=thread_id,
        current_user=owner_user,
        db=db,
    )
    agent_state = state_response.get("agent_state") or {}
    subagent_runs = agent_state.get("subagent_runs") or []
    for run in subagent_runs:
        run.pop("events_url", None)
        run.pop("result_url", None)
    return {"agent_state": agent_state}


async def list_shared_thread_files(
    *,
    thread_id: str,
    token: str,
    db: AsyncSession,
    path: str | None = None,
    recursive: bool = False,
) -> dict:
    """公开读：线程文件列表，artifact_url 改写为公开分享端点。"""
    await _validate_share(thread_id=thread_id, token=token, db=db)

    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get_conversation_by_thread_id(thread_id)
    if not conversation or conversation.status == "deleted":
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")

    result = await list_thread_files_view(
        thread_id=thread_id,
        current_uid=str(conversation.uid),
        db=db,
        path=path,
        recursive=recursive,
    )
    old_prefix = SHARE_ARTIFACT_PREFIX_TEMPLATE.format(thread_id=thread_id)
    for entry in result.get("files", []):
        url = entry.get("artifact_url")
        if url and url.startswith(old_prefix):
            relative = url[len(old_prefix) :]
            entry["artifact_url"] = _share_artifact_url(thread_id, relative, token)
    return result


async def read_shared_thread_file_content(
    *,
    thread_id: str,
    token: str,
    db: AsyncSession,
    path: str,
    offset: int = 0,
    limit: int = 2000,
) -> dict:
    """公开读：文件内容。"""
    await _validate_share(thread_id=thread_id, token=token, db=db)

    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get_conversation_by_thread_id(thread_id)
    if not conversation or conversation.status == "deleted":
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")

    result = await read_thread_file_content_view(
        thread_id=thread_id,
        current_uid=str(conversation.uid),
        db=db,
        path=path,
        offset=offset,
        limit=limit,
    )
    artifact_url = result.get("artifact_url")
    if artifact_url and artifact_url.startswith(SHARE_ARTIFACT_PREFIX_TEMPLATE.format(thread_id=thread_id)):
        result["artifact_url"] = _share_artifact_url(thread_id, path, token)
    return result


async def resolve_shared_thread_artifact(*, thread_id: str, token: str, db: AsyncSession, path: str):
    """公开读：解析交付件文件路径（返回 Path，由路由返回 FileResponse）。"""
    await _validate_share(thread_id=thread_id, token=token, db=db)

    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get_conversation_by_thread_id(thread_id)
    if not conversation or conversation.status == "deleted":
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")

    return await resolve_thread_artifact_view(
        thread_id=thread_id,
        current_uid=str(conversation.uid),
        db=db,
        path=path,
    )


async def resolve_shared_thread_preview(*, thread_id: str, token: str, db: AsyncSession, path: str):
    """公开读：返回与聊天页 viewer 一致的预览响应（文本→JSON payload，二进制→带预览头的流）。"""
    import asyncio
    import io
    from urllib.parse import quote as _quote

    from fastapi.responses import StreamingResponse
    from yuxi.services.file_preview import (
        MAX_BINARY_PREVIEW_SIZE_BYTES,
        detect_media_type,
        is_binary_preview_type,
        render_preview_payload,
        render_preview_too_large_payload,
    )

    resolved = await resolve_shared_thread_artifact(
        thread_id=thread_id,
        token=token,
        db=db,
        path=path,
    )

    if resolved.stat().st_size > MAX_BINARY_PREVIEW_SIZE_BYTES:
        return render_preview_too_large_payload()

    raw_content = await asyncio.to_thread(resolved.read_bytes)
    payload = render_preview_payload(path, raw_content)
    if is_binary_preview_type(payload["preview_type"]) and payload["supported"]:
        file_name = resolved.name or "preview"
        media_type = await asyncio.to_thread(detect_media_type, file_name, raw_content)
        headers = {
            "Content-Disposition": f"inline; filename*=UTF-8''{_quote(file_name)}",
            "X-Yuxi-Preview-Type": payload["preview_type"],
            "X-Yuxi-Preview-Filename": _quote(file_name),
        }
        return StreamingResponse(io.BytesIO(raw_content), media_type=media_type, headers=headers)
    return payload
