from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from yuxi.services.mcp import server_service
from yuxi.storage.postgres.models_business import MCPConnection, MCPServer

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


@pytest_asyncio.fixture
async def server_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(MCPServer.__table__.create)
        await conn.run_sync(MCPConnection.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_server_mutations_bump_server_cache_revision(server_session, monkeypatch):
    server = MCPServer(
        name="billing",
        transport="streamable_http",
        url="http://billing.local/mcp",
        enabled=1,
        created_by="tester",
        updated_by="tester",
    )
    server_session.add(server)
    await server_session.commit()
    connection = MCPConnection(
        server_name="billing",
        scope_type="system",
        scope_id="global",
        status="active",
        created_by="tester",
        updated_by="tester",
    )
    server_session.add(connection)
    await server_session.commit()
    calls: list[str] = []
    connection_calls: list[tuple[str, int]] = []

    async def fake_invalidate(server_name: str):
        calls.append(server_name)

    async def fake_connection_invalidate(server_name: str, connection_id: int):
        connection_calls.append((server_name, connection_id))

    monkeypatch.setattr(server_service, "_invalidate_mcp_server_caches", fake_invalidate, raising=False)
    monkeypatch.setattr(
        server_service,
        "_invalidate_mcp_connection_caches",
        fake_connection_invalidate,
        raising=False,
    )

    await server_service.update_mcp_server(server_session, "billing", description="updated")
    await server_service.set_server_enabled(server_session, "billing", False)
    await server_service.delete_mcp_server(server_session, "billing")

    assert calls == ["billing", "billing", "billing"]
    assert connection_calls == [("billing", connection.id)]
