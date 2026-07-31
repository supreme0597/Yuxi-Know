from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from yuxi.agents.mcp.connection_repository import MCPConnectionRepository
from yuxi.agents.mcp.mcp_auth.config_models import MCPAuthConfig
from yuxi.agents.mcp.mcp_auth.crypto import encrypt_credential_blob
from yuxi.agents.mcp.mcp_auth.orchestrator import AuthContext
from yuxi.storage.postgres.models_business import MCPConnection, User

logger = logging.getLogger("yuxi.mcp.connection_service")

_UNSET = object()
_VALID_MCP_CONNECTION_SCOPE_TYPES = {"system", "department", "user"}
_VALID_MCP_CONNECTION_STATUSES = {"active", "disabled", "reauth_required", "invalid"}
_MCP_CONNECTION_SCOPE_LABELS = {
    "system": "全局共享",
    "department": "部门共享",
    "user": "个人专用",
}
_MCP_CONNECTION_HEALTH_FILTERS = {"all", "active", "attention", "disabled"}


def _resolve_scope_id(binding_scope: str, auth_context: AuthContext | None) -> str | None:
    """依据 Scope 类别从 AuthContext 中解出匹配的 ID"""
    if binding_scope == "inline":
        return None
    if binding_scope == "system":
        return "global"
    if auth_context is None:
        raise ValueError(f"auth_context is required for MCP binding scope '{binding_scope}'")
    if binding_scope == "department":
        if not auth_context.department_id:
            raise ValueError("department_id is required for department-scoped MCP auth")
        return str(auth_context.department_id)
    if binding_scope == "user":
        if not auth_context.user_id:
            raise ValueError("user_id is required for user-scoped MCP auth")
        return str(auth_context.user_id)
    raise ValueError(f"Unsupported MCP binding scope: {binding_scope}")


def requires_bound_mcp_connection(auth_config: MCPAuthConfig) -> bool:
    """判断当前鉴权配置是否必须存在 active MCPConnection。"""
    return auth_config.binding_scope != "inline" and bool(auth_config.get_secret_fields())


def _normalize_mcp_connection_scope(scope_type: str, scope_id: str | None) -> tuple[str, str]:
    normalized_scope_type = str(scope_type or "").strip().lower()
    if normalized_scope_type not in _VALID_MCP_CONNECTION_SCOPE_TYPES:
        raise ValueError("scope_type must be one of: system, department, user")

    normalized_scope_id = str(scope_id or "").strip()
    if normalized_scope_type == "system":
        return normalized_scope_type, "global"
    if not normalized_scope_id:
        raise ValueError(f"scope_id is required for {normalized_scope_type}-scoped MCP connections")
    return normalized_scope_type, normalized_scope_id


def _normalize_mcp_connection_status(status: str) -> str:
    normalized_status = str(status or "").strip().lower()
    if normalized_status not in _VALID_MCP_CONNECTION_STATUSES:
        raise ValueError("status must be one of: active, disabled, reauth_required, invalid")
    return normalized_status


def _format_duplicate_connection_message(server_name: str, scope_type: str) -> str:
    scope_label = _MCP_CONNECTION_SCOPE_LABELS.get(scope_type, "绑定")
    return f'MCP "{server_name}" 的{scope_label}连接已存在，请直接编辑现有连接。'


def _configured_connection_scope(server) -> str | None:
    payload = getattr(server, "auth_config_json", None)
    if not payload:
        return None
    try:
        auth_config = MCPAuthConfig.model_validate(payload)
    except Exception:
        return None
    if auth_config.binding_scope in _VALID_MCP_CONNECTION_SCOPE_TYPES:
        return auth_config.binding_scope
    return None


def _ensure_connection_scope_matches_server(server, scope_type: str) -> None:
    configured_scope = _configured_connection_scope(server)
    if not configured_scope or scope_type == configured_scope:
        return
    scope_label = _MCP_CONNECTION_SCOPE_LABELS.get(configured_scope, "当前绑定类型")
    server_name = getattr(server, "name", "")
    raise ValueError(f'MCP "{server_name}" 当前绑定类型是{scope_label}，只能使用{scope_label}连接。')


async def get_mcp_connection(db: AsyncSession, connection_id: int) -> MCPConnection | None:
    """获取单个 Connection 记录"""
    repo = MCPConnectionRepository(db)
    return await repo.get_by_id(connection_id)


def _auth_context_from_connection(connection: MCPConnection) -> AuthContext:
    """基于连接绑定生成对应的 AuthContext 用于模拟联调与测试"""
    if connection.scope_type == "department":
        return AuthContext(department_id=connection.scope_id)
    if connection.scope_type == "user":
        return AuthContext(user_id=connection.scope_id, work_id=connection.scope_id)
    return AuthContext()


async def list_mcp_connections(
    db: AsyncSession,
    *,
    server_name: str | None = None,
    scope_type: str | None = None,
    scope_id: str | None = None,
) -> list[MCPConnection]:
    """多条件列表查询 Connection"""
    repo = MCPConnectionRepository(db)
    return await repo.list(server_name=server_name, scope_type=scope_type, scope_id=scope_id)


def _connection_has_credential_condition():
    return and_(MCPConnection.credential_blob.is_not(None), MCPConnection.credential_blob != "")


def _connection_missing_credential_condition():
    return or_(MCPConnection.credential_blob.is_(None), MCPConnection.credential_blob == "")


def _connection_search_condition(search: str):
    """委托给 MCPConnectionRepository.build_search_conditions 构建搜索条件。"""
    return or_(*MCPConnectionRepository.build_search_conditions(search))


def _connection_health_condition(
    status_filter: str,
    *,
    effective_scope_type: str | None,
    credentials_required: bool,
):
    normalized_filter = str(status_filter or "all").strip().lower()
    if normalized_filter not in _MCP_CONNECTION_HEALTH_FILTERS:
        raise ValueError("status filter must be one of: all, active, attention, disabled")
    if normalized_filter == "all":
        return None
    if normalized_filter == "disabled":
        return MCPConnection.status == "disabled"

    conditions = []
    if normalized_filter == "active":
        conditions.append(MCPConnection.status == "active")
        if effective_scope_type:
            conditions.append(MCPConnection.scope_type == effective_scope_type)
        if credentials_required:
            conditions.append(_connection_has_credential_condition())
        return and_(*conditions)

    conditions.append(MCPConnection.status.in_(("reauth_required", "invalid")))
    if effective_scope_type:
        conditions.append(MCPConnection.scope_type != effective_scope_type)
    if credentials_required:
        conditions.append(_connection_missing_credential_condition())
    return or_(*conditions)


def _build_mcp_connections_query(
    *,
    server_name: str | None = None,
    scope_type: str | None = None,
    scope_id: str | None = None,
    status_filter: str = "all",
    effective_scope_type: str | None = None,
    credentials_required: bool = False,
    search: str | None = None,
):
    conditions = []
    if server_name is not None:
        conditions.append(MCPConnection.server_name == server_name)
    if scope_type is not None:
        conditions.append(MCPConnection.scope_type == scope_type)
    if scope_id is not None:
        conditions.append(MCPConnection.scope_id == scope_id)

    health_condition = _connection_health_condition(
        status_filter,
        effective_scope_type=effective_scope_type,
        credentials_required=credentials_required,
    )
    if health_condition is not None:
        conditions.append(health_condition)

    if search and str(search).strip():
        conditions.append(_connection_search_condition(str(search).strip()))

    return conditions


async def count_mcp_connections(
    db: AsyncSession,
    *,
    server_name: str | None = None,
    scope_type: str | None = None,
    scope_id: str | None = None,
    status_filter: str = "all",
    effective_scope_type: str | None = None,
    credentials_required: bool = False,
    search: str | None = None,
) -> int:
    """统计符合筛选条件的连接数量。"""
    repo = MCPConnectionRepository(db)
    conditions = _build_mcp_connections_query(
        server_name=server_name,
        scope_type=scope_type,
        scope_id=scope_id,
        status_filter=status_filter,
        effective_scope_type=effective_scope_type,
        credentials_required=credentials_required,
        search=search,
    )
    return await repo.count(conditions=conditions)


async def list_mcp_connections_page(
    db: AsyncSession,
    *,
    server_name: str | None = None,
    scope_type: str | None = None,
    scope_id: str | None = None,
    status_filter: str = "all",
    effective_scope_type: str | None = None,
    credentials_required: bool = False,
    search: str | None = None,
    page: int = 1,
    page_size: int = 12,
) -> tuple[list[MCPConnection], int]:
    """分页查询连接列表，供管理员连接页使用。"""
    repo = MCPConnectionRepository(db)
    conditions = _build_mcp_connections_query(
        server_name=server_name,
        scope_type=scope_type,
        scope_id=scope_id,
        status_filter=status_filter,
        effective_scope_type=effective_scope_type,
        credentials_required=credentials_required,
        search=search,
    )
    return await repo.list_page(
        conditions=conditions,
        page=page,
        page_size=page_size,
    )


async def create_mcp_connection(
    db: AsyncSession,
    *,
    server_name: str,
    scope_type: str,
    scope_id: str,
    display_name: str | None = None,
    external_subject: str | None = None,
    status: str = "active",
    credential_blob: str | None = None,
    meta_json: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> MCPConnection:
    """创建 MCP 绑定连接"""
    from yuxi.agents.mcp.server_service import get_mcp_server

    server = await get_mcp_server(db, server_name)
    if server is None:
        raise ValueError(f"Server '{server_name}' does not exist")
    normalized_scope_type, normalized_scope_id = _normalize_mcp_connection_scope(scope_type, scope_id)
    normalized_status = _normalize_mcp_connection_status(status)
    _ensure_connection_scope_matches_server(server, normalized_scope_type)

    encrypted_credential_blob = (
        encrypt_credential_blob(credential_blob)
        if isinstance(credential_blob, str) and credential_blob.strip()
        else credential_blob
    )

    connection = MCPConnection(
        server_name=server_name,
        scope_type=normalized_scope_type,
        scope_id=normalized_scope_id,
        display_name=display_name,
        external_subject=external_subject,
        status=normalized_status,
        credential_blob=encrypted_credential_blob,
        meta_json=meta_json or {},
        created_by=created_by,
        updated_by=created_by,
    )
    repo = MCPConnectionRepository(db)
    from sqlalchemy.exc import IntegrityError

    try:
        await repo.add(connection)
    except IntegrityError:
        await db.rollback()
        raise ValueError(_format_duplicate_connection_message(server_name, normalized_scope_type))
    return connection


async def update_mcp_connection(
    db: AsyncSession,
    connection_id: int,
    *,
    display_name: str | None = None,
    external_subject: str | None = None,
    credential_blob: Any = _UNSET,
    meta_json: dict[str, Any] | None = None,
    status: str | None = None,
    updated_by: str | None = None,
) -> MCPConnection:
    """更新 MCP 绑定连接"""
    connection = await get_mcp_connection(db, connection_id)
    if connection is None:
        raise ValueError(f"MCP connection '{connection_id}' does not exist")

    should_clear_runtime_auth_cache = False
    if display_name is not None:
        connection.display_name = display_name
    if external_subject is not None:
        connection.external_subject = external_subject
    if credential_blob is not _UNSET:
        if isinstance(credential_blob, str) and credential_blob.strip():
            connection.credential_blob = encrypt_credential_blob(credential_blob)
        else:
            connection.credential_blob = credential_blob
        should_clear_runtime_auth_cache = True
    if meta_json is not None:
        connection.meta_json = meta_json
    if status is not None:
        normalized_status = _normalize_mcp_connection_status(status)
        if normalized_status == "active":
            from yuxi.agents.mcp.server_service import get_mcp_server

            server = await get_mcp_server(db, connection.server_name)
            if server is None:
                raise ValueError(f"Server '{connection.server_name}' does not exist")
            _ensure_connection_scope_matches_server(server, connection.scope_type)
        connection.status = normalized_status
        should_clear_runtime_auth_cache = True
    if updated_by is not None:
        connection.updated_by = updated_by

    repo = MCPConnectionRepository(db)
    await repo.commit_refresh(connection)

    from yuxi.agents.mcp.tool_registry_service import (
        _clear_mcp_connection_runtime_auth_cache,
        _invalidate_mcp_tools_cache_for_connection,
    )

    if should_clear_runtime_auth_cache:
        await _clear_mcp_connection_runtime_auth_cache(connection.id)
        await _invalidate_mcp_tools_cache_for_connection(connection)
    return connection


async def delete_mcp_connection(db: AsyncSession, connection_id: int) -> bool:
    """删除 MCP 绑定连接"""
    connection = await get_mcp_connection(db, connection_id)
    if connection is None:
        return False
    deleted_connection_id = connection.id
    deleted_server_name = connection.server_name
    deleted_scope_type = connection.scope_type

    repo = MCPConnectionRepository(db)
    await repo.delete(connection)

    from yuxi.agents.mcp.tool_registry_service import (
        _clear_mcp_connection_runtime_auth_cache,
        invalidate_mcp_connection_tools_cache,
        invalidate_mcp_server_tools_cache,
    )

    await _clear_mcp_connection_runtime_auth_cache(deleted_connection_id)
    if deleted_scope_type == "system":
        await invalidate_mcp_server_tools_cache(deleted_server_name)
    else:
        await invalidate_mcp_connection_tools_cache(deleted_server_name, deleted_connection_id)
    return True


async def set_mcp_connection_status(
    db: AsyncSession,
    connection_id: int,
    *,
    status: str,
    updated_by: str | None = None,
) -> MCPConnection:
    """设置 MCP 绑定状态"""
    connection = await get_mcp_connection(db, connection_id)
    if connection is None:
        raise ValueError(f"MCP connection '{connection_id}' does not exist")

    normalized_status = _normalize_mcp_connection_status(status)
    if normalized_status == "active":
        from yuxi.agents.mcp.server_service import get_mcp_server

        server = await get_mcp_server(db, connection.server_name)
        if server is None:
            raise ValueError(f"Server '{connection.server_name}' does not exist")
        _ensure_connection_scope_matches_server(server, connection.scope_type)

    connection.status = normalized_status
    if updated_by is not None:
        connection.updated_by = updated_by

    repo = MCPConnectionRepository(db)
    await repo.commit_refresh(connection)

    from yuxi.agents.mcp.tool_registry_service import (
        _clear_mcp_connection_runtime_auth_cache,
        _invalidate_mcp_tools_cache_for_connection,
    )

    await _clear_mcp_connection_runtime_auth_cache(connection.id)
    await _invalidate_mcp_tools_cache_for_connection(connection)
    return connection


async def reauthorize_mcp_connection(
    db: AsyncSession,
    connection_id: int,
    *,
    updated_by: str | None = None,
) -> MCPConnection:
    """重置授权连接凭据缓存并重新开启连接"""
    connection = await get_mcp_connection(db, connection_id)
    if connection is None:
        raise ValueError(f"MCP connection '{connection_id}' does not exist")

    from yuxi.agents.mcp.server_service import get_mcp_server

    server = await get_mcp_server(db, connection.server_name)
    if server is None:
        raise ValueError(f"Server '{connection.server_name}' does not exist")
    _ensure_connection_scope_matches_server(server, connection.scope_type)

    from yuxi.agents.mcp.mcp_auth.redis_token_cache import RedisTokenCache

    cache = RedisTokenCache()
    if getattr(connection, "id", None) is not None:
        try:
            await cache.delete_access_token(connection.id)
        except Exception as exc:
            logger.warning(f"Failed to clear MCP token cache for connection {connection.id}: {exc}")
        try:
            await cache.release_refresh_lock(connection.id)
        except Exception as exc:
            logger.warning(f"Failed to clear MCP refresh lock for connection {connection.id}: {exc}")

    from yuxi.agents.mcp.tool_registry_service import _invalidate_mcp_tools_cache_for_connection

    await _invalidate_mcp_tools_cache_for_connection(connection)

    # 清除 agent 端 DynamicMCPTokenAuth 缓存的 headers，
    # 否则重授权后 agent 仍会使用缓存的旧 token 发请求，导致 401 循环
    from yuxi.agents.mcp.client_pool import clear_server_resolved_headers_cache

    clear_server_resolved_headers_cache(connection.server_name)

    connection.status = "active"
    meta_json = dict(connection.meta_json or {})
    meta_json.pop("last_error", None)
    connection.meta_json = meta_json
    if updated_by is not None:
        connection.updated_by = updated_by

    repo = MCPConnectionRepository(db)
    return await repo.commit_refresh(connection)


async def test_mcp_connection(
    db: AsyncSession,
    connection_id: int,
    *,
    updated_by: str | None = None,
) -> dict[str, Any]:
    """测试连接联调可用性，获取可用的工具列表"""
    connection = await get_mcp_connection(db, connection_id)
    if connection is None:
        raise ValueError(f"MCP connection '{connection_id}' does not exist")

    from yuxi.agents.mcp.server_service import get_mcp_server

    server = await get_mcp_server(db, connection.server_name)
    if server is None:
        raise ValueError(f"Server '{connection.server_name}' does not exist")
    _ensure_connection_scope_matches_server(server, connection.scope_type)

    auth_context = _auth_context_from_connection(connection)

    # 对于 user scope，scope_id 存的是 User.id（数据库主键），
    # 但 SSO 鉴权需要的 work_id 是 User.user_id（登录工号），
    # 必须从 User 表查出真实工号，否则 template 中 ${context.work_id} 会解析为主键值
    if connection.scope_type == "user":
        try:
            user_result = await db.execute(select(User).where(User.id == int(connection.scope_id)))
            user_row = user_result.scalar_one_or_none()
            if user_row and user_row.user_id:
                auth_context = AuthContext(user_id=connection.scope_id, work_id=str(user_row.user_id))
        except (ValueError, TypeError):
            pass

    from yuxi.agents.mcp.server_service import get_runtime_mcp_server_config
    from yuxi.agents.mcp.tool_registry_service import get_mcp_tools

    config = await get_runtime_mcp_server_config(server.name, auth_context=auth_context, db=db)
    if config is None:
        raise ValueError(f"MCP server '{server.name}' runtime config unavailable")

    # 直连模式下 DynamicMCPTokenAuth 依赖 mcp_auth_context_var 注入鉴权 headers
    from yuxi.agents.mcp.mcp_auth.orchestrator import mcp_auth_context_var

    _auth_token = mcp_auth_context_var.set(auth_context)
    try:
        tools = await get_mcp_tools(
            server.name,
            additional_servers={server.name: config},
            disabled_tools=[],
            cache=False,
            force_refresh=True,
        )

        meta_json = dict(connection.meta_json or {})
        meta_json["last_success_at"] = datetime.now(tz=UTC).isoformat()
        meta_json.pop("last_error", None)
        connection.meta_json = meta_json
        connection.status = "active"
        if updated_by is not None:
            connection.updated_by = updated_by

        repo = MCPConnectionRepository(db)
        await repo.commit_refresh(connection)
        return {"tool_count": len(tools), "connection": connection}
    finally:
        mcp_auth_context_var.reset(_auth_token)
