from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

import httpx
from cachetools import LRUCache
from sqlalchemy.ext.asyncio import AsyncSession
from yuxi.agents.mcp.mcp_auth.config_models import MCPAuthConfig
from yuxi.agents.mcp.mcp_auth.orchestrator import AuthContext
from yuxi.agents.mcp.mcp_tool_cache import RedisMcpToolCache
from yuxi.storage.postgres.models_business import MCPConnection, MCPServer

logger = logging.getLogger("yuxi.mcp.tool_registry_service")

# 全局共享状态（直接在本模块维护，供外部和测试使用）
_mcp_tools_cache: LRUCache = LRUCache(maxsize=128)
_mcp_tools_stats: LRUCache = LRUCache(maxsize=128)
_mcp_tools_failure_cache: LRUCache = LRUCache(maxsize=256)
_mcp_tool_cache_store = RedisMcpToolCache()
_mcp_lock = asyncio.Lock()
_MCP_TOOL_FAILURE_COOLDOWN_SECONDS = float(os.getenv("YUXI_MCP_TOOL_FAILURE_COOLDOWN_SECONDS", "30"))


def to_camel_case(s: str) -> str:
    """转换字符串为 lowerCamelCase 命名格式"""
    import re

    s = re.sub(r"[-_]+(.)", lambda m: m.group(1).upper(), s)
    if len(s) > 0:
        s = s[0].lower() + s[1:]
    return s


def _extract_cache_identity(server_config: dict[str, Any]) -> tuple[dict[str, Any], str, bool]:
    """提取用于缓存 key 比较的标识配置"""
    cache_partition = str(server_config.get("__yuxi_cache_partition") or "server")
    allow_global_cache = bool(server_config.get("__yuxi_allow_global_cache", True))

    cache_identity = {
        key: value
        for key, value in server_config.items()
        if key
        not in {
            "__yuxi_cache_partition",
            "__yuxi_allow_global_cache",
            "disabled_tools",
        }
    }

    headers = dict(cache_identity.get("headers") or {})
    if headers:
        cache_identity["headers"] = headers
    elif "headers" in cache_identity:
        cache_identity["headers"] = {}
    return cache_identity, cache_partition, allow_global_cache


async def _build_mcp_tool_cache_descriptor(server_name: str, server_config: dict[str, Any]) -> dict[str, Any]:
    """生成缓存 Key 描述信息字典"""
    cache_identity, cache_partition, allow_global_cache = _extract_cache_identity(server_config)
    config_payload = json.dumps(cache_identity, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    config_hash = hashlib.sha256(config_payload.encode("utf-8")).hexdigest()[:16]

    server_revision = await _mcp_tool_cache_store.get_server_revision(server_name)
    partition_revision = 0
    if not allow_global_cache:
        partition_revision = await _mcp_tool_cache_store.get_partition_revision(server_name, cache_partition)
    revision_token = f"s{server_revision}:p{partition_revision}"
    cache_prefix = f"{server_name}:{cache_partition}:{revision_token}:"

    return {
        "cache_identity": cache_identity,
        "cache_partition": cache_partition,
        "allow_global_cache": allow_global_cache,
        "config_hash": config_hash,
        "cache_prefix": cache_prefix,
        "cache_key": f"{cache_prefix}{config_hash}",
        "server_revision": server_revision,
        "partition_revision": partition_revision,
    }


def _serialize_mcp_tools_manifest(
    *,
    server_name: str,
    cache_partition: str,
    cache_key: str,
    tools: list[Callable[..., Any]],
) -> dict[str, Any]:
    """将 Langchain 运行态 Tool 转换为 Manifest 字典以缓存到 Redis 中"""
    entries = []
    for tool in tools:
        if hasattr(tool, "args_schema") and tool.args_schema:
            schema = tool.args_schema.schema() if hasattr(tool.args_schema, "schema") else {}
            parameters = schema.get("properties", {})
            required = schema.get("required", [])
        else:
            parameters = {}
            required = []
        metadata = dict(getattr(tool, "metadata", {}) or {})
        entries.append(
            {
                "name": tool.name,
                "id": metadata.get("id") or tool.name,
                "mcp_server_name": metadata.get("mcp_server_name") or server_name,
                "description": getattr(tool, "description", ""),
                "parameters": parameters,
                "required": required,
            }
        )
    return {
        "server_name": server_name,
        "cache_partition": cache_partition,
        "cache_key": cache_key,
        "tools": entries,
    }


def _deserialize_mcp_tool_manifest(manifest: dict[str, Any]) -> list[Callable[..., Any]]:
    """反序列化 Redis 中的 Manifest 字典还原为本地 Tool 对象结构"""
    tools: list[Callable[..., Any]] = []
    for entry in manifest.get("tools", []):
        args_schema = None
        parameters = entry.get("parameters") or {}
        required = entry.get("required") or []
        if parameters or required:
            args_schema = SimpleNamespace(
                schema=lambda parameters=parameters, required=required: {
                    "properties": parameters,
                    "required": required,
                }
            )
        # 从 manifest 的顶层 server_name 和条目级 mcp_server_name 恢复
        mcp_server_name = entry.get("mcp_server_name") or manifest.get("server_name") or ""
        tools.append(
            SimpleNamespace(
                name=entry.get("name") or "",
                description=entry.get("description") or "",
                metadata={
                    "id": entry.get("id") or entry.get("name") or "",
                    "mcp_server_name": mcp_server_name,
                },
                args_schema=args_schema,
            )
        )
    return tools


def _get_mcp_auth_config(server_config: dict[str, Any]) -> MCPAuthConfig | None:
    auth_payload = server_config.get("auth_config") or {}
    if not auth_payload:
        return None
    try:
        return MCPAuthConfig.model_validate(auth_payload)
    except Exception as exc:
        logger.warning(f"Invalid MCP auth config while resolving tool preload strategy: {exc}")
        return None


def _can_preload_mcp_server_tools_without_runtime_auth(server_config: dict[str, Any]) -> bool:
    if not (server_config.get("auth_config") or {}):
        return True
    auth_config = _get_mcp_auth_config(server_config)
    if auth_config is None:
        return False
    return auth_config.provider == "legacy_static"


def _get_cached_mcp_tool_failure(cache_key: str) -> dict[str, Any] | None:
    entry = _mcp_tools_failure_cache.get(cache_key)
    if not entry:
        return None
    retry_at = float(entry.get("retry_at") or 0)
    if retry_at <= time.monotonic():
        _mcp_tools_failure_cache.pop(cache_key, None)
        return None
    return entry


def _record_mcp_tool_failure(cache_key: str, exc: BaseException) -> None:
    if _MCP_TOOL_FAILURE_COOLDOWN_SECONDS <= 0:
        return
    # 同时清除工具对象缓存，避免缓存命中绕过故障冷却
    _mcp_tools_cache.pop(cache_key, None)
    _mcp_tools_failure_cache[cache_key] = {
        "retry_at": time.monotonic() + _MCP_TOOL_FAILURE_COOLDOWN_SECONDS,
        "message": str(exc) or exc.__class__.__name__,
    }


def _clear_mcp_tool_failure(cache_key: str) -> None:
    _mcp_tools_failure_cache.pop(cache_key, None)


def _clear_mcp_tool_failure_cache_for_server(server_name: str) -> None:
    prefix = f"{server_name}:"
    stale_keys = [key for key in _mcp_tools_failure_cache if key.startswith(prefix)]
    for key in stale_keys:
        _mcp_tools_failure_cache.pop(key, None)


async def get_mcp_tools(
    server_name: str,
    additional_servers: dict[str, dict[str, Any]] | None = None,
    disabled_tools: list[str] | None = None,
    cache: bool = True,
    force_refresh: bool = False,
) -> list[Callable[..., Any]]:
    """
    获取指定 MCP 服务器的工具列表。

    优化生命周期：
    - 集成缓存策略模式 (CachePolicy)，动态决策是否在进程内容许缓存 Tool 对象。
    - 集成客户端连接池 (MCPClientPool)，复用 Stdio 长期子进程及 HTTP Keep-Alive 连接。
    """
    if additional_servers and server_name in additional_servers:
        server_config = additional_servers[server_name]
    else:
        from yuxi.agents.mcp.server_service import get_enabled_mcp_server_config

        server_config = await get_enabled_mcp_server_config(server_name)

    if server_config is None:
        logger.warning(f"MCP server '{server_name}' not found in database or disabled")
        return []

    cache_descriptor = await _build_mcp_tool_cache_descriptor(server_name, server_config)
    cache_partition = cache_descriptor["cache_partition"]
    cache_prefix = cache_descriptor["cache_prefix"]
    cache_key = cache_descriptor["cache_key"]

    # 策略模式：根据 AuthProvider 确认是否容许内存缓存 Tool 实例对象
    from yuxi.agents.mcp.cache_policy import CachePolicyFactory

    auth_config = _get_mcp_auth_config(server_config)
    policy = CachePolicyFactory.get_policy(auth_config.provider if auth_config else None)
    use_tool_object_cache = cache and policy.should_cache_tool_object()

    all_processed_tools: list[Callable[..., Any]] = []

    async with _mcp_lock:
        if not force_refresh and use_tool_object_cache and cache_key in _mcp_tools_cache:
            all_processed_tools = _mcp_tools_cache[cache_key]

    if not all_processed_tools:
        if not force_refresh:
            failure_entry = _get_cached_mcp_tool_failure(cache_key)
            if failure_entry is not None:
                retry_in = max(0.0, float(failure_entry.get("retry_at") or 0) - time.monotonic())
                logger.debug(
                    f"Skip loading MCP tools for '{server_name}' during failure cooldown "
                    f"({retry_in:.1f}s left): {failure_entry.get('message')}"
                )
                return []

        try:
            # 剥离所有内部字段：__yuxi_ 前缀的内部透传键 + 非 SDK 字段
            _STRIPPED_KEYS = frozenset({
                "disabled_tools", "description", "icon", "enabled", "tags", "auth_config",
            })
            client_config = {
                k: v
                for k, v in server_config.items()
                if not k.startswith("__yuxi_") and k not in _STRIPPED_KEYS
            }

            # NOTE: 从长连接池中提取 ClientSession 实例
            # （对 Stdio 而言子进程被挂起复用，避免频繁启停；HTTP 协议亦保持 Keep-Alive）
            from yuxi.agents.mcp.client_pool import mcp_client_pool

            session = await mcp_client_pool.get_session(
                server_name,
                partition_key=f"{cache_partition}:s{cache_descriptor['server_revision']}:p{cache_descriptor['partition_revision']}",
                runtime_config=client_config,
            )

            # 如果 session 是 Fake Client (有 get_tools 方法)，我们直接调用它获取工具列表，避免 load_mcp_tools 报错
            if hasattr(session, "get_tools"):
                raw_tools = cast(list[Any], await session.get_tools())
            else:
                # 调用 langchain 官方加载工具，直接传入已预备并建立好的 session
                from langchain_mcp_adapters.tools import load_mcp_tools

                raw_tools = cast(list[Any], await load_mcp_tools(session, server_name=server_name))

            server_cc = to_camel_case(server_name)
            for tool in raw_tools:
                original_name = tool.name
                tool_cc = to_camel_case(original_name)
                unique_id = f"mcp__{server_cc}__{tool_cc}"

                if tool.metadata is None:
                    tool.metadata = {}
                tool.metadata["id"] = unique_id
                tool.metadata["mcp_server_name"] = server_name
                tool.handle_tool_error = True
                all_processed_tools.append(tool)

            if cache:
                if use_tool_object_cache:
                    async with _mcp_lock:
                        stale_keys = [
                            key for key in _mcp_tools_cache if key.startswith(cache_prefix) and key != cache_key
                        ]
                        for stale_key in stale_keys:
                            _mcp_tools_cache.pop(stale_key, None)
                        _mcp_tools_cache[cache_key] = all_processed_tools

                await _mcp_tool_cache_store.set_manifest(
                    cache_key,
                    _serialize_mcp_tools_manifest(
                        server_name=server_name,
                        cache_partition=cache_partition,
                        cache_key=cache_key,
                        tools=all_processed_tools,
                    ),
                )

                global_config_disabled = server_config.get("disabled_tools") or []
                enabled_count = len([t for t in all_processed_tools if t.name not in global_config_disabled])
                _mcp_tools_stats[server_name] = {
                    "total": len(all_processed_tools),
                    "enabled": enabled_count,
                    "disabled": len(all_processed_tools) - enabled_count,
                }

                logger.info(
                    f"Refreshed MCP tools cache for '{server_name}' with key '{cache_key}': "
                    f"{len(all_processed_tools)} tools loaded."
                )

            _clear_mcp_tool_failure(cache_key)

        except Exception as e:
            # 连接类错误（session 断开）不进入故障冷却：session 已被移除，下次调用可立即重建
            is_connection_err = isinstance(e, (ConnectionError, ConnectionResetError, BrokenPipeError, OSError))
            if not is_connection_err:
                _record_mcp_tool_failure(cache_key, e)
                logger.warning(
                    f"MCP server '{server_name}' temporarily unavailable; "
                    f"suppress retries for {_MCP_TOOL_FAILURE_COOLDOWN_SECONDS:.0f}s: {e}"
                )
            else:
                # 连接类错误只清缓存不进冷却，允许立即重试
                _mcp_tools_cache.pop(cache_key, None)
                logger.info(
                    f"MCP server '{server_name}' connection error; session removed, "
                    f"no cooldown applied (ready for immediate retry): {e}"
                )
            logger.debug(f"Failed to load tools from MCP server '{server_name}'", exc_info=True)
            try:
                partition_key = (
                    f"{cache_partition}:s{cache_descriptor['server_revision']}:"
                    f"p{cache_descriptor['partition_revision']}"
                )
                from yuxi.agents.mcp.client_pool import mcp_client_pool

                await mcp_client_pool.remove_session(server_name, partition_key)
            except Exception as pool_err:
                logger.warning(f"Failed to remove stale session for {server_name}: {pool_err}")
            # 连接类错误时 partition_key 可能已过期（revision 被 bump），
            # remove_session 可能未命中，再兜底全量清理该 server 的 session
            if is_connection_err:
                try:
                    from yuxi.agents.mcp.client_pool import mcp_client_pool

                    await mcp_client_pool.remove_sessions_by_server(server_name)
                except Exception as pool_err:
                    logger.warning(f"Failed to remove all server sessions for {server_name}: {pool_err}")
            return []

    if disabled_tools:
        filtered_tools = [t for t in all_processed_tools if t.name not in disabled_tools]
        return filtered_tools

    return all_processed_tools


async def get_tools_from_all_servers(server_names: list[str] | None = None) -> list[Callable[..., Any]]:
    """批量载入指定或所有可用服务的工具（用于系统初始化及预热）"""
    from yuxi.agents.mcp.server_service import _load_enabled_mcp_server_configs

    names: list[str] | None = None
    if server_names is not None:
        names = []
        seen: set[str] = set()
        for value in server_names:
            if not isinstance(value, str):
                continue
            name = value.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)
        if not names:
            return []

    server_configs = await _load_enabled_mcp_server_configs(names=names)

    preload_items = [
        (name, config)
        for name, config in server_configs.items()
        if _can_preload_mcp_server_tools_without_runtime_auth(config)
    ]
    for name, config in server_configs.items():
        if name not in {item[0] for item in preload_items}:
            logger.info(f"Skip MCP tool preload for '{name}' because runtime auth context is required")

    results = await asyncio.gather(
        *[
            get_mcp_tools(name, additional_servers={name: config})
            for name, config in preload_items
        ]
    )
    all_tools: list[Callable[..., Any]] = []
    for tools in results:
        all_tools.extend(tools)
    return all_tools


async def clear_mcp_cache() -> None:
    """清空本地内存工具缓存"""
    global _mcp_tools_cache, _mcp_tools_failure_cache
    _mcp_tools_cache = LRUCache(maxsize=128)
    _mcp_tools_failure_cache = LRUCache(maxsize=256)

    try:
        from yuxi.agents.mcp.client_pool import clear_resolved_headers_cache, mcp_client_pool

        await mcp_client_pool.clear_sessions()
        clear_resolved_headers_cache()
    except Exception:
        pass


def clear_mcp_server_tools_cache(server_name: str) -> None:
    """清空指定服务器下的所有本地缓存"""
    global _mcp_tools_cache
    prefix = f"{server_name}:"
    stale_keys = [k for k in _mcp_tools_cache if k.startswith(prefix)]
    for key in stale_keys:
        _mcp_tools_cache.pop(key, None)
    _clear_mcp_tool_failure_cache_for_server(server_name)

    try:
        from yuxi.agents.mcp.client_pool import clear_server_resolved_headers_cache

        clear_server_resolved_headers_cache(server_name)
    except Exception:
        pass


def clear_mcp_connection_tools_cache(server_name: str, connection_id: int | None) -> None:
    """清空指定连接下的本地内存缓存"""
    if connection_id is None:
        return
    global _mcp_tools_cache
    suffix = f":connection:{connection_id}:"
    stale_keys = [k for k in _mcp_tools_cache if suffix in k and k.startswith(f"{server_name}:")]
    for key in stale_keys:
        _mcp_tools_cache.pop(key, None)
    stale_failure_keys = [
        key for key in _mcp_tools_failure_cache if suffix in key and key.startswith(f"{server_name}:")
    ]
    for key in stale_failure_keys:
        _mcp_tools_failure_cache.pop(key, None)

    try:
        from yuxi.agents.mcp.client_pool import clear_server_resolved_headers_cache

        clear_server_resolved_headers_cache(server_name)
    except Exception:
        pass


async def invalidate_mcp_server_tools_cache(server_name: str) -> None:
    """全局失效指定服务器的全部二级缓存"""
    clear_mcp_server_tools_cache(server_name)
    await _mcp_tool_cache_store.bump_server_revision(server_name)
    # 清理连接池中该 server 的旧 revision session，避免孤儿 entry 累积
    try:
        from yuxi.agents.mcp.client_pool import mcp_client_pool

        await mcp_client_pool.remove_sessions_by_server(server_name)
    except Exception as exc:
        logger.warning(f"Failed to clean pool sessions during server cache invalidation for '{server_name}': {exc}")


async def invalidate_mcp_connection_tools_cache(server_name: str, connection_id: int | None) -> None:
    """失效指定连接下的二级缓存区划"""
    if connection_id is None:
        return
    clear_mcp_connection_tools_cache(server_name, connection_id)
    await _mcp_tool_cache_store.bump_partition_revision(server_name, f"connection:{connection_id}")
    # 清理连接池中该连接分区的旧 revision session
    try:
        from yuxi.agents.mcp.client_pool import mcp_client_pool

        await mcp_client_pool.remove_sessions_by_partition(server_name, f"connection:{connection_id}")
    except Exception as exc:
        logger.warning(
            f"Failed to clean pool sessions during connection cache invalidation "
            f"for '{server_name}/{connection_id}': {exc}"
        )


async def _invalidate_mcp_tools_cache_for_connection(connection: MCPConnection) -> None:
    """依据 Scope 类别自动刷新并失效缓存"""
    if connection.scope_type == "system":
        await invalidate_mcp_server_tools_cache(connection.server_name)
    else:
        await invalidate_mcp_connection_tools_cache(connection.server_name, connection.id)


async def _clear_mcp_connection_runtime_auth_cache(connection_id: int | None) -> None:
    """清理 Redis 中缓存的 Access Token 与锁状态"""
    if connection_id is None:
        return
    from yuxi.agents.mcp.mcp_auth.redis_token_cache import RedisTokenCache

    cache = RedisTokenCache()
    try:
        await cache.delete_access_token(connection_id)
    except Exception as exc:
        logger.warning(f"Failed to clear MCP token cache for connection {connection_id}: {exc}")
    try:
        await cache.release_refresh_lock(connection_id)
    except Exception as exc:
        logger.warning(f"Failed to clear MCP refresh lock for connection {connection_id}: {exc}")


async def _clear_mcp_server_runtime_auth_cache(db: AsyncSession, server_name: str) -> None:
    """清理服务器下所有关联连接的 Token 缓存"""
    from yuxi.agents.mcp.connection_service import list_mcp_connections

    connections = await list_mcp_connections(db, server_name=server_name)
    for connection in connections:
        await _clear_mcp_connection_runtime_auth_cache(getattr(connection, "id", None))


def get_mcp_tools_stats(server_name: str) -> dict[str, int] | None:
    return _mcp_tools_stats.get(server_name)


async def _load_connection_required_placeholder_tools(
    server_name: str,
    exc: MCPConnectionRequiredError,  # noqa: F821
    *,
    auth_context: AuthContext | None = None,
    db: AsyncSession | None = None,
) -> list[Callable[..., Any]]:
    """当用户未配置 MCP 连接时，回退到基础配置获取真实工具名并包装为提示替身。

    用 server 的基础连接配置（不含鉴权）尝试连接 MCP 服务器获取工具列表，
    将每个真实工具包装成「调用时返回配置指引」的替身工具，
    让 Agent 看到真实的工具名并自然地转达给用户。
    """
    from langchain_core.tools import StructuredTool
    from yuxi.agents.mcp.server_service import get_enabled_mcp_server_config

    scope_info = getattr(exc, "binding_scope", "") or ""
    scope_label = {"user": "个人", "department": "部门", "system": "全局"}.get(scope_info, scope_info)
    if scope_info == "user":
        config_path = f"左下角头像 → 系统设置 → MCP连接 → {server_name}"
    else:
        config_path = f"扩展 → MCP → {server_name} → 连接"
    prompt_message = (
        f"MCP 服务「{server_name}」需要{scope_label}连接才能使用，"
        f"但当前未找到有效的连接。请前往「{config_path}」页面创建连接后即可使用该服务的所有工具。"
    )

    # 尝试用基础配置（不含鉴权）连接 MCP 服务器获取真实工具列表
    raw_tools: list[Callable[..., Any]] = []
    try:
        base_config = await get_enabled_mcp_server_config(server_name, db=db)
        if base_config is not None:
            # 移除 auth_config，避免客户端尝试注入不存在的鉴权信息导致连接失败
            listing_config = {k: v for k, v in base_config.items() if k != "auth_config"}
            # 清除故障冷却，确保基础配置路径不被旧故障阻断
            _clear_mcp_tool_failure_cache_for_server(server_name)
            raw_tools = await get_mcp_tools(
                server_name,
                additional_servers={server_name: listing_config},
                disabled_tools=listing_config.get("disabled_tools") or [],
                cache=False,
                force_refresh=True,
            )
    except Exception:
        logger.debug(f"Failed to load base tools for '{server_name}' without auth, falling back to prompt tool")

    if not raw_tools:
        # 回退：无法获取真实工具名时，生成单一提示工具
        tool_name = f"mcp__{to_camel_case(server_name)}__请先配置连接"
        tool = StructuredTool.from_function(
            func=lambda: prompt_message,
            name=tool_name,
            description=(
                f"MCP 服务「{server_name}」需要{scope_label}连接才能使用，"
                f"但当前未找到有效的连接。调用此工具可获取配置指引。"
            ),
            metadata={
                "id": tool_name,
                "mcp_server_name": server_name,
                "_mcp_connection_required": True,
            },
        )
        tool.handle_tool_error = True
        return [tool]

    # 用真实工具名生成替身工具，保留原始描述和参数 schema，调用时返回配置指引
    placeholder_tools: list[Callable[..., Any]] = []
    for raw_tool in raw_tools:
        original_name = raw_tool.name
        original_description = getattr(raw_tool, "description", "") or ""
        original_args_schema = getattr(raw_tool, "args_schema", None)

        # 闭包捕获 prompt_message，函数接受任意参数但忽略，返回提示信息
        def _make_prompt_fn(msg: str):
            def fn(**kwargs) -> str:
                return msg

            return fn

        proxy = StructuredTool.from_function(
            func=_make_prompt_fn(prompt_message),
            name=original_name,
            description=original_description,
            args_schema=original_args_schema,
            metadata={
                "id": original_name,
                "mcp_server_name": server_name,
                "_mcp_connection_required": True,
            },
        )
        proxy.handle_tool_error = True
        placeholder_tools.append(proxy)

    return placeholder_tools


async def get_enabled_mcp_tools(
    server_name: str,
    *,
    auth_context: AuthContext | None = None,
    db: AsyncSession | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list:
    from yuxi.agents.mcp.server_service import MCPConnectionRequiredError, get_runtime_mcp_server_config

    token = None
    if auth_context:
        from yuxi.agents.mcp.mcp_auth.orchestrator import mcp_auth_context_var

        token = mcp_auth_context_var.set(auth_context)

    try:
        config = await get_runtime_mcp_server_config(
            server_name,
            auth_context=auth_context,
            db=db,
            http_client=http_client,
        )
        if config is None:
            logger.warning(f"MCP server '{server_name}' not found in database or disabled")
            return []

        disabled_tools = config.get("disabled_tools") or []
        return await get_mcp_tools(
            server_name,
            additional_servers={server_name: config},
            disabled_tools=disabled_tools,
        )
    except MCPConnectionRequiredError as exc:
        # 用户尚未配置连接，用基础配置获取真实工具名并生成提示替身
        # 重置 auth context，避免 DynamicMCPTokenAuth 尝试解析鉴权导致循环失败
        logger.info(f"MCP server '{server_name}' requires connection: {exc}")
        if token:
            from yuxi.agents.mcp.mcp_auth.orchestrator import mcp_auth_context_var

            mcp_auth_context_var.reset(token)
            token = None
        return await _load_connection_required_placeholder_tools(
            server_name,
            exc,
            auth_context=None,
            db=db,
        )
    finally:
        if token:
            from yuxi.agents.mcp.mcp_auth.orchestrator import mcp_auth_context_var

            mcp_auth_context_var.reset(token)


async def get_all_mcp_tools(
    server_name: str,
    *,
    auth_context: AuthContext | None = None,
    db: AsyncSession | None = None,
    http_client: httpx.AsyncClient | None = None,
    force_refresh: bool = False,
) -> list:
    from yuxi.agents.mcp.server_service import (
        MCPConnectionRequiredError,
        get_enabled_mcp_server_config,
        get_runtime_mcp_server_config,
    )

    token = None
    if auth_context:
        from yuxi.agents.mcp.mcp_auth.orchestrator import mcp_auth_context_var

        token = mcp_auth_context_var.set(auth_context)

    try:
        if auth_context is None and db is None:
            config = await get_enabled_mcp_server_config(server_name)
        else:
            config = await get_runtime_mcp_server_config(
                server_name,
                auth_context=auth_context,
                db=db,
                http_client=http_client,
            )
        if config is None:
            logger.warning(f"MCP server '{server_name}' not found in database or disabled")
            return []

        if not force_refresh:
            cache_descriptor = await _build_mcp_tool_cache_descriptor(server_name, config)
            manifest = await _mcp_tool_cache_store.get_manifest(cache_descriptor["cache_key"])
            if manifest is not None:
                return _deserialize_mcp_tool_manifest(manifest)

        return await get_mcp_tools(
            server_name,
            additional_servers={server_name: config},
            disabled_tools=[],
            cache=True,
            force_refresh=force_refresh,
        )
    except MCPConnectionRequiredError as exc:
        # 管理端 API 也调用 get_all_mcp_tools，连接缺失时回退到基础配置获取工具列表
        # 基础配置不含鉴权信息，仍可连接 MCP 服务器列出工具（只是调用时需要鉴权）
        # 使用 force_refresh=True 跳过故障冷却，因为基础配置是全新路径，之前的失败不应阻断
        logger.info(
            f"MCP server '{server_name}' requires connection for runtime auth, falling back to base config: {exc}"
        )

        # 重置 auth context，避免 DynamicMCPTokenAuth 尝试解析鉴权导致循环失败
        if token:
            from yuxi.agents.mcp.mcp_auth.orchestrator import mcp_auth_context_var

            mcp_auth_context_var.reset(token)
            token = None

        base_config = await get_enabled_mcp_server_config(server_name)
        if base_config is None:
            return []

        # 清除该 server 的故障冷却，避免基础配置路径被旧故障阻断
        _clear_mcp_tool_failure_cache_for_server(server_name)

        # 移除 auth_config，避免客户端尝试注入不存在的鉴权信息导致连接失败
        # 基础配置仅用于列出工具，实际调用时需要鉴权
        listing_config = {k: v for k, v in base_config.items() if k != "auth_config"}

        if not force_refresh:
            cache_descriptor = await _build_mcp_tool_cache_descriptor(server_name, listing_config)
            manifest = await _mcp_tool_cache_store.get_manifest(cache_descriptor["cache_key"])
            if manifest is not None:
                return _deserialize_mcp_tool_manifest(manifest)

        return await get_mcp_tools(
            server_name,
            additional_servers={server_name: listing_config},
            disabled_tools=listing_config.get("disabled_tools") or [],
            cache=True,
            force_refresh=True,
        )
    finally:
        if token:
            from yuxi.agents.mcp.mcp_auth.orchestrator import mcp_auth_context_var

            mcp_auth_context_var.reset(token)


async def toggle_tool_enabled(
    db: AsyncSession,
    server_name: str,
    tool_name: str,
    updated_by: str | None = None,
) -> tuple[bool, MCPServer]:
    """切换单个工具的启用状态"""
    from yuxi.agents.mcp.server_repository import MCPServerRepository

    repo = MCPServerRepository(db)
    server = await repo.get_by_name(server_name)
    if not server:
        raise ValueError(f"Server '{server_name}' does not exist")

    disabled_tools = list(server.disabled_tools or [])

    if tool_name in disabled_tools:
        disabled_tools.remove(tool_name)
        enabled = True
    else:
        disabled_tools.append(tool_name)
        enabled = False

    server.disabled_tools = disabled_tools
    if updated_by is not None:
        server.updated_by = updated_by
    await repo.commit_refresh(server)

    # 清除内存工具缓存
    clear_mcp_server_tools_cache(server_name)

    logger.info(f"Toggled tool '{tool_name}' for server '{server_name}' enabled={enabled}")
    return enabled, server
