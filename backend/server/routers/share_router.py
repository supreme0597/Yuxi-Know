"""公开对话分享读接口 - 匿名只读访问（token 走查询参数）。"""

from __future__ import annotations

import aiofiles
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db
from yuxi.services.file_preview import detect_media_type
from yuxi.services.share_service import (
    get_shared_thread_state,
    get_shared_thread_view,
    list_shared_thread_files,
    read_shared_thread_file_content,
    resolve_shared_thread_artifact,
    resolve_shared_thread_preview,
)

share = APIRouter(prefix="/share", tags=["share"])


@share.get("/{thread_id}")
async def get_shared_thread(
    thread_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """匿名查看分享会话的元信息与历史消息（含工具调用）。"""
    return await get_shared_thread_view(thread_id=thread_id, token=token, db=db)


@share.get("/{thread_id}/state")
async def get_shared_thread_state_endpoint(
    thread_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """匿名查看分享会话的 agent_state（待办/文件/交付件/子代理/用量）。"""
    return await get_shared_thread_state(thread_id=thread_id, token=token, db=db)


@share.get("/{thread_id}/files")
async def list_shared_thread_files_endpoint(
    thread_id: str,
    token: str = Query(...),
    path: str | None = Query(None),
    recursive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """匿名查看分享会话的文件列表。"""
    return await list_shared_thread_files(
        thread_id=thread_id,
        token=token,
        db=db,
        path=path,
        recursive=recursive,
    )


@share.get("/{thread_id}/files/content")
async def read_shared_thread_file_content_endpoint(
    thread_id: str,
    token: str = Query(...),
    path: str = Query(...),
    offset: int = Query(0),
    limit: int = Query(2000),
    db: AsyncSession = Depends(get_db),
):
    """匿名查看分享会话的文件内容。"""
    return await read_shared_thread_file_content(
        thread_id=thread_id,
        token=token,
        db=db,
        path=path,
        offset=offset,
        limit=limit,
    )


@share.get("/{thread_id}/artifacts/{path:path}")
async def get_shared_thread_artifact(
    thread_id: str,
    path: str,
    token: str = Query(...),
    download: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """匿名预览/下载分享会话的交付件文件。

    download=false（默认）时返回与聊天页 viewer 一致的预览响应（文本→JSON payload，二进制→带预览头的流）；
    download=true 时返回原始文件（attachment）。
    """
    if download:
        file_path = await resolve_shared_thread_artifact(
            thread_id=thread_id,
            token=token,
            db=db,
            path=path,
        )
        async with aiofiles.open(file_path, "rb") as artifact_file:
            file_head = await artifact_file.read(512)
        media_type = detect_media_type(file_path.name, file_head)
        headers = {"Content-Disposition": f'attachment; filename="{file_path.name}"'}
        return FileResponse(path=file_path, media_type=media_type, headers=headers)

    return await resolve_shared_thread_preview(
        thread_id=thread_id,
        token=token,
        db=db,
        path=path,
    )
