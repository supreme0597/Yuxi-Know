from __future__ import annotations

import os
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from yuxi.services.mcp import connection_service
from yuxi.services.mcp_auth.crypto import encrypt_credential_blob
from yuxi.services.mcp_auth.orchestrator import (
    AuthContext,
    RuntimeMCPAuthError,
    resolve_runtime_mcp,
    resolve_runtime_mcp_config,
)
from yuxi.storage.postgres.models_business import Department, MCPConnection, MCPServer, User

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


@pytest.fixture(autouse=True)
def mcp_credentials_master_key(monkeypatch):
    monkeypatch.setenv("MCP_CREDENTIALS_MASTER_KEY", "local-test-master-key")


@pytest_asyncio.fixture
async def conn_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Department.__table__.create)
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(MCPServer.__table__.create)
        await conn.run_sync(MCPConnection.__table__.create)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _add_server(session, name: str, auth_config: dict, transport: str = "streamable_http") -> MCPServer:
    server = MCPServer(
        name=name,
        transport=transport,
        url=f"http://{name}.local/mcp" if transport != "stdio" else None,
        command="node" if transport == "stdio" else None,
        args=["server.js"] if transport == "stdio" else None,
        env={"BASE_ENV": "base"} if transport == "stdio" else None,
        headers={"X-Static": "static"} if transport != "stdio" else None,
        auth_config_json=auth_config,
        created_by="tester",
        updated_by="tester",
    )
    session.add(server)
    await session.commit()
    return server


async def _ensure_user(session, scope_id: str) -> User:
    conditions = [User.user_id == scope_id]
    if scope_id.isdigit():
        conditions.append(User.id == int(scope_id))
    existing = (await session.execute(select(User).where(or_(*conditions)))).scalar_one_or_none()
    if existing is not None:
        return existing

    user_kwargs = {
        "username": f"user-{scope_id}",
        "user_id": scope_id,
        "password_hash": "x",
        "role": "user",
    }
    if scope_id.isdigit():
        user_kwargs["id"] = int(scope_id)
    user = User(**user_kwargs)
    session.add(user)
    await session.commit()
    return user


async def _create_active_connection(
    session,
    server_name: str,
    *,
    scope_type: str,
    scope_id: str,
    token: str,
    status: str = "active",
):
    if scope_type == "user":
        await _ensure_user(session, scope_id)
    return await connection_service.create_mcp_connection(
        session,
        server_name=server_name,
        scope_type=scope_type,
        scope_id=scope_id,
        credential_blob=f'{{"secrets":{{"access_token":"{token}"}}}}',
        status=status,
        created_by="tester",
    )


def _bound_header_auth_config(scope: str = "user") -> dict:
    return {
        "version": 1,
        "provider": "bound_secret",
        "binding_scope": scope,
        "inject": {
            "target": "headers",
            "entries": [
                {"name": "Authorization", "value_template": "Bearer ${secret.access_token}"},
                {"name": "X-User-Id", "value_template": "${context.user_id}"},
                {"name": "X-Work-Id", "value_template": "${context.work_id}"},
                {"name": "X-Department-Id", "value_template": "${context.department_id}"},
            ],
        },
    }


async def test_resolve_runtime_mcp_config_injects_user_bound_secret_headers(conn_session):
    server = await _add_server(conn_session, "billing", _bound_header_auth_config("user"))
    await _create_active_connection(conn_session, "billing", scope_type="user", scope_id="42", token="user-token")

    resolved = await resolve_runtime_mcp_config(
        "billing",
        server.to_mcp_config(),
        auth_context=AuthContext(user_id="42", work_id="W-7", department_id="9"),
        db=conn_session,
    )

    assert resolved["headers"] == {
        "X-Static": "static",
        "Authorization": "Bearer user-token",
        "X-User-Id": "42",
        "X-Work-Id": "W-7",
        "X-Department-Id": "9",
    }
    assert "auth_config" not in resolved


async def test_resolve_runtime_mcp_config_does_not_mutate_source_headers(conn_session):
    server = await _add_server(conn_session, "immutable", _bound_header_auth_config("user"))
    await _create_active_connection(conn_session, "immutable", scope_type="user", scope_id="42", token="user-token")
    server_config = server.to_mcp_config()

    resolved = await resolve_runtime_mcp_config(
        "immutable",
        server_config,
        auth_context=AuthContext(user_id="42", work_id="W-7", department_id="9"),
        db=conn_session,
    )

    assert server_config["headers"] == {"X-Static": "static"}
    assert resolved["headers"] is not server_config["headers"]
    assert resolved["headers"]["Authorization"] == "Bearer user-token"


async def test_resolve_runtime_mcp_config_uses_department_scope_connection(conn_session):
    server = await _add_server(conn_session, "dept-docs", _bound_header_auth_config("department"))
    conn_session.add(Department(id=9, name="finance"))
    await conn_session.commit()
    await _create_active_connection(
        conn_session,
        "dept-docs",
        scope_type="department",
        scope_id="9",
        token="dept-token",
    )

    resolved = await resolve_runtime_mcp_config(
        "dept-docs",
        server.to_mcp_config(),
        auth_context=AuthContext(user_id="42", work_id="W-7", department_id="9"),
        db=conn_session,
    )

    assert resolved["headers"]["Authorization"] == "Bearer dept-token"


async def test_resolve_runtime_mcp_config_raises_when_active_connection_missing(conn_session):
    server = await _add_server(conn_session, "missing-user", _bound_header_auth_config("user"))
    await _create_active_connection(
        conn_session,
        "missing-user",
        scope_type="user",
        scope_id="42",
        token="disabled-token",
        status="disabled",
    )

    with pytest.raises(RuntimeMCPAuthError, match='MCP "missing-user".*active connection.*user'):
        await resolve_runtime_mcp_config(
            "missing-user",
            server.to_mcp_config(),
            auth_context=AuthContext(user_id="42", work_id="W-7", department_id="9"),
            db=conn_session,
        )


async def test_resolve_runtime_mcp_config_raises_when_auth_context_missing(conn_session):
    server = await _add_server(conn_session, "missing-context", _bound_header_auth_config("user"))

    with pytest.raises(RuntimeMCPAuthError, match="runtime auth context is missing"):
        await resolve_runtime_mcp_config(
            "missing-context",
            server.to_mcp_config(),
            db=conn_session,
        )


async def test_resolve_runtime_mcp_config_does_not_fall_back_to_work_id_connection(conn_session):
    server = await _add_server(conn_session, "work-id-user", _bound_header_auth_config("user"))
    conn_session.add(User(id=42, username="user-42", user_id="W-7", password_hash="x", role="user"))
    conn_session.add(
        MCPConnection(
            server_name="work-id-user",
            scope_type="user",
            scope_id="W-7",
            status="active",
            credential_blob=encrypt_credential_blob('{"secrets":{"access_token":"wrong-user-token"}}'),
            created_by="tester",
            updated_by="tester",
        )
    )
    await conn_session.commit()

    with pytest.raises(
        RuntimeMCPAuthError,
        match='MCP "work-id-user" has no active connection for user scope "42"',
    ):
        await resolve_runtime_mcp_config(
            "work-id-user",
            server.to_mcp_config(),
            auth_context=AuthContext(user_id="42", work_id="W-7", department_id="9"),
            db=conn_session,
        )


async def test_resolve_runtime_mcp_config_prefers_database_user_id_connection(conn_session):
    server = await _add_server(conn_session, "dual-user", _bound_header_auth_config("user"))
    conn_session.add(User(id=42, username="user-42", user_id="W-7", password_hash="x", role="user"))
    conn_session.add_all(
        [
            MCPConnection(
                server_name="dual-user",
                scope_type="user",
                scope_id="W-7",
                status="active",
                credential_blob=encrypt_credential_blob('{"secrets":{"access_token":"legacy-token"}}'),
                created_by="tester",
                updated_by="tester",
            ),
            MCPConnection(
                server_name="dual-user",
                scope_type="user",
                scope_id="42",
                status="active",
                credential_blob=encrypt_credential_blob('{"secrets":{"access_token":"canonical-token"}}'),
                created_by="tester",
                updated_by="tester",
            ),
        ]
    )
    await conn_session.commit()

    resolved = await resolve_runtime_mcp_config(
        "dual-user",
        server.to_mcp_config(),
        auth_context=AuthContext(user_id="42", work_id="W-7", department_id="9"),
        db=conn_session,
    )

    assert resolved["headers"]["Authorization"] == "Bearer canonical-token"


async def test_resolve_runtime_mcp_config_injects_context_only_config_without_connection(conn_session):
    auth_config = _bound_header_auth_config("user")
    auth_config["inject"]["entries"] = [
        {"name": "X-User-Id", "value_template": "${context.user_id}"},
    ]
    server = await _add_server(conn_session, "context-only", auth_config)

    resolved = await resolve_runtime_mcp_config(
        "context-only",
        server.to_mcp_config(),
        auth_context=AuthContext(user_id="42"),
        db=conn_session,
    )

    assert resolved["headers"] == {"X-Static": "static", "X-User-Id": "42"}
    assert "auth_config" not in resolved


async def test_resolve_runtime_mcp_config_treats_inline_config_as_static(conn_session):
    server = await _add_server(conn_session, "inline", _bound_header_auth_config("inline"))

    resolved = await resolve_runtime_mcp_config("inline", server.to_mcp_config(), db=conn_session)

    assert resolved["headers"] == {"X-Static": "static"}
    assert "auth_config" not in resolved


async def test_resolve_runtime_mcp_config_injects_stdio_env(conn_session):
    auth_config = {
        "version": 1,
        "provider": "stdio_env",
        "binding_scope": "system",
        "inject": {
            "target": "env",
            "entries": [
                {"name": "API_TOKEN", "value_template": "${secret.access_token}"},
                {"name": "WORK_ID", "value_template": "${context.work_id}"},
            ],
        },
    }
    server = await _add_server(conn_session, "stdio-srv", auth_config, transport="stdio")
    await _create_active_connection(
        conn_session,
        "stdio-srv",
        scope_type="system",
        scope_id="global",
        token="system-token",
    )

    resolved = await resolve_runtime_mcp_config(
        "stdio-srv",
        server.to_mcp_config(),
        auth_context=AuthContext(user_id="42", work_id="W-7", department_id="9"),
        db=conn_session,
    )

    assert resolved["env"] == {"BASE_ENV": "base", "API_TOKEN": "system-token", "WORK_ID": "W-7"}


async def test_auth_context_from_runtime_context_uses_backend_owned_fields():
    runtime_context = SimpleNamespace(user_id="42", work_id="W-7", department_id=9)

    auth_context = AuthContext.from_runtime_context(runtime_context)

    assert auth_context == AuthContext(user_id="42", work_id="W-7", department_id="9")


def _dynamic_header_auth_config(provider: str = "custom_http_token") -> dict:
    return {
        "version": 1,
        "provider": provider,
        "binding_scope": "user",
        "inject": {
            "target": "headers",
            "entries": [{"name": "Authorization", "value_template": "Bearer ${access_token}"}],
        },
        "refresh_policy": {"pre_refresh_seconds": 30},
        "token_request": {"url": "https://auth.example/token"},
    }


async def test_resolve_runtime_mcp_injects_dynamic_token_and_returns_connection_partition(conn_session):
    server = await _add_server(conn_session, "dynamic", _dynamic_header_auth_config())
    connection = await _create_active_connection(
        conn_session,
        "dynamic",
        scope_type="user",
        scope_id="42",
        token="stale",
    )

    async def token_fetcher(**kwargs):
        assert kwargs["connection_id"] == connection.id
        return {"access_token": "fresh", "expires_in": 300}

    resolved = await resolve_runtime_mcp(
        "dynamic",
        server.to_mcp_config(),
        auth_context=AuthContext(user_id="42"),
        db=conn_session,
        token_resolver=token_fetcher,
    )

    assert resolved.config["headers"]["Authorization"] == "Bearer fresh"
    assert resolved.cache_policy.partition == f"connection:{connection.id}"
    assert resolved.cache_policy.cache_tool_objects is False
    serialized_identity = json.dumps(resolved.cache_identity, sort_keys=True)
    assert '"fresh"' not in serialized_identity
    assert '"stale"' not in serialized_identity


async def test_authorization_code_without_refresh_token_marks_connection_reauth_required(conn_session):
    server = await _add_server(conn_session, "oauth", _dynamic_header_auth_config("authorization_code"))
    connection = await _create_active_connection(
        conn_session,
        "oauth",
        scope_type="user",
        scope_id="42",
        token="access-only",
    )

    with pytest.raises(RuntimeMCPAuthError, match="refresh_token"):
        await resolve_runtime_mcp_config(
            "oauth",
            server.to_mcp_config(),
            auth_context=AuthContext(user_id="42"),
            db=conn_session,
        )

    await conn_session.refresh(connection)
    assert connection.status == "reauth_required"


async def test_dynamic_cache_identity_changes_with_token_request_config(conn_session):
    server = await _add_server(conn_session, "identity", _dynamic_header_auth_config())
    await _create_active_connection(
        conn_session,
        "identity",
        scope_type="user",
        scope_id="42",
        token="stale",
    )

    async def token_fetcher(**kwargs):
        return {"access_token": "fresh", "expires_in": 300}

    first_config = server.to_mcp_config()
    second_config = deepcopy(server.to_mcp_config())
    second_config["auth_config"]["token_request"] = {"url": "https://other.example/token"}
    first = await resolve_runtime_mcp(
        "identity",
        first_config,
        auth_context=AuthContext(user_id="42"),
        db=conn_session,
        token_resolver=token_fetcher,
    )
    second = await resolve_runtime_mcp(
        "identity",
        second_config,
        auth_context=AuthContext(user_id="42"),
        db=conn_session,
        token_resolver=token_fetcher,
    )

    assert first.cache_identity != second.cache_identity
