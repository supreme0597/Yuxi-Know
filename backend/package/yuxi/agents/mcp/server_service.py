from __future__ import annotations

import logging
import traceback
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from yuxi.agents.mcp.mcp_auth.config_models import MCPAuthConfig
from yuxi.agents.mcp.mcp_auth.orchestrator import AuthContext, resolve_runtime_mcp_config
from yuxi.agents.mcp.server_repository import MCPServerRepository
from yuxi.storage.postgres.models_business import Agent, MCPConnection, MCPServer, Skill

logger = logging.getLogger("yuxi.mcp.server_service")


class MCPConnectionRequiredError(Exception):
    """当 MCP 鉴权配置要求绑定连接但用户尚未创建活跃连接时抛出。

    携带 server_name 和 binding_scope 信息，供上层返回用户友好的提示。
    """

    def __init__(self, server_name: str, binding_scope: str, scope_id: str | None = None):
        self.server_name = server_name
        self.binding_scope = binding_scope
        self.scope_id = scope_id
        scope_desc = f"{binding_scope}:{scope_id}" if scope_id else binding_scope
        super().__init__(
            f"MCP server '{server_name}' requires an active connection for scope {scope_desc}, "
            f"but none was found. Please create a connection in the MCP management page."
        )


_UNSET = object()

_RETIRED_BUILTIN_MCP_SERVER_SLUGS = ("sequentialthinking",)

_DEFAULT_MCP_SERVERS = {
    "mcp-server-chart": {
        "command": "npx",
        "args": ["-y", "@antv/mcp-server-chart"],
        "transport": "stdio",
        "description": "图表生成工具，支持生成各类图表（柱状图、折线图、饼图等）",
        "icon": "📊",
        "tags": ["内置", "图表"],
    },
}

_SYNCED_MCP_FIELDS = (
    "description",
    "transport",
    "url",
    "command",
    "args",
    "env",
    "headers",
    "timeout",
    "sse_read_timeout",
    "tags",
    "icon",
)


async def ensure_builtin_mcp_servers_in_db() -> None:
    """同步代码预置的内置 MCP 服务器至数据库中"""
    from yuxi.storage.postgres.manager import pg_manager

    try:
        async with pg_manager.get_async_session_context() as session:
            repo = MCPServerRepository(session)
            any_changed = False

            # 清理已退役的内置服务器
            for slug in _RETIRED_BUILTIN_MCP_SERVER_SLUGS:
                retired = await repo.get_by_slug(slug)
                if retired and getattr(retired, "created_by", None) == "system":
                    await repo.delete(retired)
                    any_changed = True
                    logger.info(f"Removed retired built-in MCP server '{slug}' from database")

            count = await repo.count()

            if count == 0:
                logger.info("No MCP servers in database, importing default configurations...")
                for slug, config in _DEFAULT_MCP_SERVERS.items():
                    server = MCPServer(
                        slug=slug,
                        name=config.get("name", slug),
                        description=config.get("description"),
                        transport=config["transport"],
                        url=config.get("url"),
                        command=config.get("command"),
                        args=config.get("args"),
                        env=config.get("env"),
                        headers=config.get("headers"),
                        timeout=config.get("timeout"),
                        sse_read_timeout=config.get("sse_read_timeout"),
                        tags=config.get("tags"),
                        icon=config.get("icon"),
                        enabled=0,
                        created_by="system",
                        updated_by="system",
                    )
                    await repo.add(server)
                any_changed = True
                logger.info(f"Imported {len(_DEFAULT_MCP_SERVERS)} default MCP servers to database")
            else:
                for slug, config in _DEFAULT_MCP_SERVERS.items():
                    existing = await repo.get_by_slug(slug)
                    if not existing:
                        server = MCPServer(
                            slug=slug,
                            name=config.get("name", slug),
                            description=config.get("description"),
                            transport=config["transport"],
                            url=config.get("url"),
                            command=config.get("command"),
                            args=config.get("args"),
                            env=config.get("env"),
                            headers=config.get("headers"),
                            timeout=config.get("timeout"),
                            sse_read_timeout=config.get("sse_read_timeout"),
                            tags=config.get("tags"),
                            icon=config.get("icon"),
                            enabled=0,
                            created_by="system",
                            updated_by="system",
                        )
                        await repo.add(server)
                        any_changed = True
                        logger.info(f"Added built-in MCP server '{slug}' to database")
                    else:
                        changed = False
                        for field in _SYNCED_MCP_FIELDS:
                            next_value = config.get(field)
                            if getattr(existing, field) != next_value:
                                setattr(existing, field, next_value)
                                changed = True
                        if changed:
                            existing.updated_by = "system"
                            any_changed = True
                            await session.commit()

    except Exception as e:
        logger.error(f"Failed to ensure builtin MCP servers in database: {e}, traceback: {traceback.format_exc()}")


async def _load_enabled_mcp_server_configs(
    *,
    slugs: list[str] | None = None,
    db: AsyncSession | None = None,
) -> dict[str, dict[str, Any]]:
    """从数据库中加载已启用的服务器 MCP 配置"""
    if db is not None:
        repo = MCPServerRepository(db)
        servers = await repo.list_enabled(slugs=slugs)
        return {server.slug: server.to_mcp_config() for server in servers}

    from yuxi.storage.postgres.manager import pg_manager

    async with pg_manager.get_async_session_context() as session:
        return await _load_enabled_mcp_server_configs(slugs=slugs, db=session)


async def get_enabled_mcp_server_config(server_slug: str, *, db: AsyncSession | None = None) -> dict[str, Any] | None:
    """获取最新启用的指定服务器的 MCP 配置"""
    configs = await _load_enabled_mcp_server_configs(slugs=[server_slug], db=db)
    return configs.get(server_slug)


async def _get_enabled_mcp_server_record(server_slug: str, *, db: AsyncSession) -> MCPServer | None:
    repo = MCPServerRepository(db)
    return await repo.get_enabled_by_slug(server_slug)


def _apply_runtime_tool_cache_policy(
    config: dict[str, Any],
    *,
    auth_config: MCPAuthConfig,
    auth_context: AuthContext | None,
    connection: MCPConnection | None,
) -> dict[str, Any]:
    """利用 CachePolicy 模式获取缓存 key 的隔离区划并应用"""
    from yuxi.agents.mcp.cache_policy import CachePolicyFactory

    policy = CachePolicyFactory.get_policy(auth_config.provider)
    partition, is_shared = policy.resolve_cache_partition(
        auth_context or AuthContext(),
        connection,
    )
    config["__yuxi_cache_partition"] = partition
    config["__yuxi_allow_global_cache"] = is_shared
    return config


async def get_runtime_mcp_server_config(
    server_slug: str,
    *,
    auth_context: AuthContext | None = None,
    db: AsyncSession | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """解析获取附带运行时鉴权与租户范围的 MCP 服务配置"""
    if db is None and auth_context is None:
        return await get_enabled_mcp_server_config(server_slug)

    if db is not None:
        server = await _get_enabled_mcp_server_record(server_slug, db=db)
        if server is None:
            return None
        if not server.auth_config_json:
            return server.to_mcp_config()

        auth_config = MCPAuthConfig.model_validate(server.auth_config_json)
        from yuxi.agents.mcp.connection_service import _resolve_scope_id, requires_bound_mcp_connection

        scope_id = _resolve_scope_id(auth_config.binding_scope, auth_context)
        if scope_id is None:
            return server.to_mcp_config()

        from yuxi.agents.mcp.connection_repository import MCPConnectionRepository

        conn_repo = MCPConnectionRepository(db)
        connection = await conn_repo.find_active(
            server_name=server_slug, scope_type=auth_config.binding_scope, scope_id=scope_id
        )
        if connection is None:
            # 尝试自动重授权：如果连接状态为 reauth_required，清除 token 缓存后重置为 active
            reauth_conn = await conn_repo.find_requiring_reauth(
                server_name=server_slug, scope_type=auth_config.binding_scope, scope_id=scope_id
            )
            if reauth_conn is not None:
                from yuxi.agents.mcp.connection_service import reauthorize_mcp_connection

                try:
                    connection = await reauthorize_mcp_connection(db, reauth_conn.id)
                except Exception as exc:
                    logger.warning(f"Auto-reauthorize failed for '{server_slug}': {exc}")
            elif requires_bound_mcp_connection(auth_config):
                raise MCPConnectionRequiredError(server_slug, auth_config.binding_scope, scope_id)
            # 无需长期密钥的鉴权机制无需强制绑定连接即可生成运行时配置
        config = await resolve_runtime_mcp_config(
            server,
            auth_context=auth_context or AuthContext(),
            connection=connection,
            http_client=http_client,
        )
        # 透传 connection.id 供 DynamicMCPTokenAuth 缓存隔离使用
        if connection is not None and getattr(connection, "id", None) is not None:
            config["__yuxi_connection_id"] = connection.id
        return _apply_runtime_tool_cache_policy(
            config,
            auth_config=auth_config,
            auth_context=auth_context,
            connection=connection,
        )

    from yuxi.storage.postgres.manager import pg_manager

    async with pg_manager.get_async_session_context() as session:
        return await get_runtime_mcp_server_config(
            server_slug,
            auth_context=auth_context,
            db=session,
            http_client=http_client,
        )


async def get_enabled_mcp_server_slugs(*, db: AsyncSession | None = None) -> list[str]:
    """获取所有已启用的服务器 slug"""
    configs = await _load_enabled_mcp_server_configs(db=db)
    return list(configs.keys())


async def get_mcp_server(db: AsyncSession, slug: str) -> MCPServer | None:
    """获取单个服务器对象记录"""
    repo = MCPServerRepository(db)
    return await repo.get_by_slug(slug)


async def get_all_mcp_servers(db: AsyncSession) -> list[MCPServer]:
    """获取所有配置的服务器对象列表"""
    repo = MCPServerRepository(db)
    return await repo.get_all()


async def create_mcp_server(
    db: AsyncSession,
    slug: str,
    name: str | None = None,
    transport: str = None,
    url: str = None,
    command: str = None,
    args: list = None,
    env: dict = None,
    description: str = None,
    headers: dict = None,
    timeout: int = None,
    sse_read_timeout: int = None,
    tags: list = None,
    icon: str = None,
    auth_config: dict | None = None,
    created_by: str = None,
) -> MCPServer:
    """创建 MCP 服务器配置"""
    repo = MCPServerRepository(db)
    existing = await repo.get_by_slug(slug)
    if existing:
        raise ValueError(f"Server slug '{slug}' already exists")

    server = MCPServer(
        slug=slug,
        name=name or slug,
        description=description,
        transport=transport,
        url=url,
        command=command,
        args=args,
        env=env,
        headers=headers,
        auth_config_json=auth_config,
        timeout=timeout,
        sse_read_timeout=sse_read_timeout,
        tags=tags,
        icon=icon,
        enabled=1,
        created_by=created_by,
        updated_by=created_by,
    )
    await repo.add(server)

    from yuxi.agents.mcp.tool_registry_service import (
        _clear_mcp_server_runtime_auth_cache,
        invalidate_mcp_server_tools_cache,
    )

    await _clear_mcp_server_runtime_auth_cache(db, slug)
    await invalidate_mcp_server_tools_cache(slug)

    logger.info(f"Created MCP server '{slug}'")
    return server


async def update_mcp_server(
    db: AsyncSession,
    slug: str,
    description: str = None,
    transport: str = None,
    url: str = None,
    command: str = None,
    args: list = None,
    env: Any = _UNSET,
    headers: dict = None,
    timeout: int = None,
    sse_read_timeout: int = None,
    tags: list = None,
    icon: str = None,
    name: str | None = None,
    auth_config: Any = _UNSET,
    updated_by: str = None,
) -> MCPServer:
    """更新服务器配置"""
    repo = MCPServerRepository(db)
    server = await repo.get_by_slug(slug)
    if not server:
        raise ValueError(f"Server '{slug}' does not exist")

    if description is not None:
        server.description = description
    if transport is not None:
        server.transport = transport
    if url is not None:
        server.url = url
    if command is not None:
        server.command = command
    if args is not None:
        server.args = args
    if env is not _UNSET:
        server.env = env
    if headers is not None:
        server.headers = headers
    if auth_config is not _UNSET:
        server.auth_config_json = auth_config
    if timeout is not None:
        server.timeout = timeout
    if sse_read_timeout is not None:
        server.sse_read_timeout = sse_read_timeout
    if tags is not None:
        server.tags = tags
    if icon is not None:
        server.icon = icon
    if updated_by is not None:
        server.updated_by = updated_by

    await repo.commit_refresh(server)

    from yuxi.agents.mcp.tool_registry_service import (
        _clear_mcp_server_runtime_auth_cache,
        invalidate_mcp_server_tools_cache,
    )

    if auth_config is not _UNSET:
        await _clear_mcp_server_runtime_auth_cache(db, slug)
    await invalidate_mcp_server_tools_cache(slug)

    logger.info(f"Updated MCP server '{slug}'")
    return server


async def delete_mcp_server(db: AsyncSession, slug: str) -> bool:
    """删除服务器"""
    repo = MCPServerRepository(db)
    server = await repo.get_by_slug(slug)
    if not server:
        return False

    from yuxi.agents.mcp.tool_registry_service import (
        _clear_mcp_server_runtime_auth_cache,
        invalidate_mcp_server_tools_cache,
    )

    # NOTE: 必须在级联删除前执行 Redis 缓存清理，否则关联的 connection 行被删除后将无法提取 ID
    await _clear_mcp_server_runtime_auth_cache(db, slug)

    await repo.delete(server)

    await invalidate_mcp_server_tools_cache(slug)

    logger.info(f"Deleted MCP server '{slug}'")
    return True


async def get_mcp_server_dependency_summary(db: AsyncSession, slug: str) -> dict[str, Any]:
    """获取依赖于该 MCP 服务器的智能体、技能和连接概要"""
    from yuxi.agents.mcp.connection_repository import MCPConnectionRepository

    conn_repo = MCPConnectionRepository(db)
    connections = await conn_repo.list(server_name=slug)

    skill_rows = (await db.execute(select(Skill))).scalars().all()
    matched_skills = [
        {"slug": item.slug, "name": item.name} for item in skill_rows if slug in (item.mcp_dependencies or [])
    ]

    agent_config_rows = (await db.execute(select(Agent))).scalars().all()
    matched_agent_configs = []
    for item in agent_config_rows:
        config_json = item.config_json or {}
        if slug in (config_json.get("mcps") or []):
            matched_agent_configs.append({"id": item.id, "name": item.name, "agent_id": item.slug})

    connection_refs = [
        {"scope_type": item.scope_type, "scope_id": item.scope_id, "status": item.status} for item in connections
    ]

    return {
        "has_references": bool(connection_refs or matched_skills or matched_agent_configs),
        "connections": connection_refs,
        "skills": matched_skills,
        "agent_configs": matched_agent_configs,
    }


async def set_server_enabled(
    db: AsyncSession, slug: str, enabled: bool, updated_by: str = None
) -> tuple[bool, MCPServer]:
    """设置服务器的启用状态"""
    repo = MCPServerRepository(db)
    server = await repo.get_by_slug(slug)
    if not server:
        raise ValueError(f"Server '{slug}' does not exist")

    server.enabled = 1 if enabled else 0
    if updated_by is not None:
        server.updated_by = updated_by
    await repo.commit_refresh(server)

    is_enabled = bool(server.enabled)
    from yuxi.agents.mcp.tool_registry_service import (
        _clear_mcp_server_runtime_auth_cache,
        invalidate_mcp_server_tools_cache,
    )

    if not is_enabled:
        await _clear_mcp_server_runtime_auth_cache(db, slug)
    await invalidate_mcp_server_tools_cache(slug)

    logger.info(f"Set MCP server '{slug}' enabled={is_enabled}")
    return is_enabled, server


async def get_servers_config(slugs: list[str]) -> dict[str, dict[str, Any]]:
    """批量获取服务器配置"""
    return await _load_enabled_mcp_server_configs(slugs=slugs)
