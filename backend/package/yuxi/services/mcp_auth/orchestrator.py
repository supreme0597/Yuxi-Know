from __future__ import annotations

import json
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from yuxi.services.mcp_auth.config_models import MCPAuthConfig
from yuxi.services.mcp_auth.crypto import decrypt_credential_blob
from yuxi.services.mcp_auth.template_resolver import TemplateResolutionError, resolve_template_value
from yuxi.services.mcp_auth.token_service import RedisTokenCache, resolve_dynamic_token
from yuxi.storage.postgres.models_business import MCPConnection


class RuntimeMCPAuthError(ValueError):
    """Raised when runtime MCP credentials cannot be resolved safely."""


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    work_id: str | None = None
    department_id: str | None = None

    @classmethod
    def from_runtime_context(cls, runtime_context: Any) -> AuthContext:
        user_id = getattr(runtime_context, "user_id", None)
        if user_id is None or str(user_id).strip() == "":
            raise RuntimeMCPAuthError("MCP runtime auth context is missing user_id")

        work_id = getattr(runtime_context, "work_id", None)
        department_id = getattr(runtime_context, "department_id", None)
        return cls(
            user_id=str(user_id),
            work_id=str(work_id) if work_id is not None else None,
            department_id=str(department_id) if department_id is not None else None,
        )

    @classmethod
    def from_runtime_context_or_none(cls, runtime_context: Any) -> AuthContext | None:
        user_id = getattr(runtime_context, "user_id", None)
        if user_id is None or str(user_id).strip() == "":
            return None
        return cls.from_runtime_context(runtime_context)

    @classmethod
    def from_current_user(cls, current_user: Any) -> AuthContext:
        user_id = getattr(current_user, "id", None)
        if user_id is None or str(user_id).strip() == "":
            raise RuntimeMCPAuthError("MCP current user auth context is missing id")

        work_id = getattr(current_user, "user_id", None)
        department_id = getattr(current_user, "department_id", None)
        return cls(
            user_id=str(user_id),
            work_id=str(work_id) if work_id is not None else None,
            department_id=str(department_id) if department_id is not None else None,
        )

    def to_template_context(self) -> dict[str, str]:
        context = {"user_id": self.user_id}
        if self.work_id is not None:
            context["work_id"] = self.work_id
        if self.department_id is not None:
            context["department_id"] = self.department_id
        return context


mcp_auth_context_var: ContextVar[AuthContext | None] = ContextVar("mcp_auth_context", default=None)


@dataclass(frozen=True)
class ResolvedMCPRuntime:
    config: dict[str, Any]
    cache_policy: Any
    cache_identity: dict[str, Any]
    connection_id: int | None = None


def mcp_config_requires_runtime_credentials(server_config: dict[str, Any]) -> bool:
    auth_payload = server_config.get("auth_config")
    if not auth_payload:
        return False
    auth_config = MCPAuthConfig.model_validate(auth_payload)
    return auth_config.provider != "legacy_static" and auth_config.binding_scope != "inline"


def _scope_for_auth_config(auth_config: MCPAuthConfig, auth_context: AuthContext) -> tuple[str, str]:
    scope_type = auth_config.binding_scope
    if scope_type == "system":
        return "system", "global"
    if scope_type == "department":
        if not auth_context.department_id:
            raise RuntimeMCPAuthError("MCP runtime auth context is missing department_id")
        return "department", auth_context.department_id
    if scope_type == "user":
        return "user", auth_context.user_id
    raise RuntimeMCPAuthError("MCP runtime auth requires a bound credential scope")


async def _get_active_connection(
    db: AsyncSession,
    *,
    server_name: str,
    scope_type: str,
    scope_id: str,
) -> MCPConnection | None:
    result = await db.execute(
        select(MCPConnection)
        .where(
            MCPConnection.server_name == server_name,
            MCPConnection.scope_type == scope_type,
            MCPConnection.scope_id == scope_id,
            MCPConnection.status == "active",
        )
        .order_by(MCPConnection.id.asc())
    )
    return result.scalars().first()


def _load_connection_secret_payload(
    connection: MCPConnection, server_name: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    credential_blob = decrypt_credential_blob(connection.credential_blob)
    if not isinstance(credential_blob, str) or not credential_blob.strip():
        raise RuntimeMCPAuthError(f'MCP "{server_name}" active connection has no credential blob')

    try:
        payload = json.loads(credential_blob)
    except json.JSONDecodeError as exc:
        raise RuntimeMCPAuthError(f'MCP "{server_name}" active connection has invalid credential blob') from exc

    if not isinstance(payload, dict):
        raise RuntimeMCPAuthError(f'MCP "{server_name}" active connection has invalid credential blob')

    secrets = payload.get("secrets", payload)
    token = payload.get("token") or payload.get("tokens") or {}
    if not isinstance(secrets, dict):
        raise RuntimeMCPAuthError(f'MCP "{server_name}" active connection has invalid secret payload')
    if not isinstance(token, dict):
        token = {}
    return secrets, token, payload


def _build_cache_identity(server_config: dict[str, Any], auth_config: MCPAuthConfig | None) -> dict[str, Any]:
    if auth_config is None or auth_config.provider == "legacy_static":
        return {key: value for key, value in server_config.items() if key not in {"disabled_tools", "auth_config"}}
    return {
        key: value
        for key, value in server_config.items()
        if key
        in {
            "transport",
            "url",
            "command",
            "args",
            "timeout",
            "sse_read_timeout",
        }
    } | {
        "auth": {
            "provider": auth_config.provider,
            "binding_scope": auth_config.binding_scope,
            "manifest_scope": auth_config.manifest_scope,
            "inject_target": auth_config.inject.target,
            "inject_entries": [entry.name for entry in auth_config.inject.entries],
        }
    }


def _apply_inject_config(
    server_name: str,
    resolved_config: dict[str, Any],
    auth_config: MCPAuthConfig,
    *,
    auth_context: AuthContext,
    secrets: dict[str, Any],
    token: dict[str, Any],
) -> None:
    target = auth_config.inject.target
    current_target = resolved_config.get(target)
    current_target = dict(current_target) if isinstance(current_target, dict) else {}

    access_token = token.get("access_token") or secrets.get("access_token")
    for entry in auth_config.inject.entries:
        try:
            current_target[entry.name] = resolve_template_value(
                entry.value_template,
                context=auth_context.to_template_context(),
                secret=secrets,
                token=token,
                access_token=str(access_token) if access_token is not None else None,
            )
        except TemplateResolutionError as exc:
            raise RuntimeMCPAuthError(f'MCP "{server_name}" auth template cannot be resolved: {exc}') from exc

    resolved_config[target] = current_target


async def resolve_runtime_mcp(
    server_name: str,
    server_config: dict[str, Any],
    *,
    auth_context: AuthContext | None = None,
    db: AsyncSession | None = None,
    token_cache: RedisTokenCache | None = None,
    token_resolver=resolve_dynamic_token,
    http_client: httpx.AsyncClient | None = None,
) -> ResolvedMCPRuntime:
    from yuxi.services.mcp.cache_policy import MCPCachePolicy, build_cache_policy

    resolved_config = dict(server_config)
    auth_payload = resolved_config.pop("auth_config", None)
    if not auth_payload:
        return ResolvedMCPRuntime(
            config=resolved_config,
            cache_policy=build_cache_policy(None, None),
            cache_identity=_build_cache_identity(server_config, None),
        )

    auth_config = MCPAuthConfig.model_validate(auth_payload)
    if auth_config.provider == "legacy_static" or auth_config.binding_scope == "inline":
        return ResolvedMCPRuntime(
            config=resolved_config,
            cache_policy=build_cache_policy("legacy_static", None),
            cache_identity=_build_cache_identity(server_config, auth_config),
        )
    if auth_context is None:
        raise RuntimeMCPAuthError(f'MCP "{server_name}" runtime auth context is missing')

    async def resolve_with_session(session: AsyncSession) -> ResolvedMCPRuntime:
        secrets: dict[str, Any] = {}
        token: dict[str, Any] = {}
        credential_payload: dict[str, Any] = {}
        connection: MCPConnection | None = None
        dynamic_provider = auth_config.provider in {
            "custom_http_token",
            "client_credentials",
            "authorization_code",
        }
        if auth_config.requires_bound_connection() or dynamic_provider:
            scope_type, scope_id = _scope_for_auth_config(auth_config, auth_context)
            connection = await _get_active_connection(
                session,
                server_name=server_name,
                scope_type=scope_type,
                scope_id=scope_id,
            )
            if connection is None:
                raise RuntimeMCPAuthError(
                    f'MCP "{server_name}" has no active connection for {scope_type} scope "{scope_id}"'
                )

            secrets, token, credential_payload = _load_connection_secret_payload(connection, server_name)

        if dynamic_provider:
            assert connection is not None
            credential_token = dict(token)
            for key in ("access_token", "refresh_token", "expires_at", "expires_in", "scope", "token_type"):
                if key not in credential_token and key in credential_payload:
                    credential_token[key] = credential_payload[key]
                if key not in credential_token and key in secrets:
                    credential_token[key] = secrets[key]
            if auth_config.provider == "authorization_code" and not credential_token.get("refresh_token"):
                connection.status = "reauth_required"
                await session.commit()
                raise RuntimeMCPAuthError(f'MCP "{server_name}" authorization_code connection requires refresh_token')
            try:
                token = await token_resolver(
                    connection_id=connection.id,
                    auth_config=auth_config,
                    context=auth_context.to_template_context(),
                    secrets=secrets,
                    credential_token=credential_token,
                    cache=token_cache,
                    http_client=http_client,
                )
            except RuntimeMCPAuthError:
                raise
            except Exception as exc:
                raise RuntimeMCPAuthError(
                    f'MCP "{server_name}" dynamic token request failed: {type(exc).__name__}'
                ) from exc
        _apply_inject_config(
            server_name,
            resolved_config,
            auth_config,
            auth_context=auth_context,
            secrets=secrets,
            token=token,
        )
        if connection is not None:
            cache_policy = build_cache_policy(auth_config.provider, connection)
        else:
            scope_type, scope_id = _scope_for_auth_config(auth_config, auth_context)
            cache_policy = MCPCachePolicy(
                partition=f"context:{scope_type}:{scope_id}",
                cache_tool_objects=True,
                cache_manifest=True,
                shared_across_users=scope_type == "system",
            )
        return ResolvedMCPRuntime(
            config=resolved_config,
            cache_policy=cache_policy,
            cache_identity=_build_cache_identity(server_config, auth_config),
            connection_id=connection.id if connection is not None else None,
        )

    if db is not None:
        return await resolve_with_session(db)

    from yuxi.storage.postgres.manager import pg_manager

    async with pg_manager.get_async_session_context() as session:
        return await resolve_with_session(session)


async def resolve_runtime_mcp_config(
    server_name: str,
    server_config: dict[str, Any],
    *,
    auth_context: AuthContext | None = None,
    db: AsyncSession | None = None,
    token_cache: RedisTokenCache | None = None,
    token_resolver=resolve_dynamic_token,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    resolved = await resolve_runtime_mcp(
        server_name,
        server_config,
        auth_context=auth_context,
        db=db,
        token_cache=token_cache,
        token_resolver=token_resolver,
        http_client=http_client,
    )
    return resolved.config
