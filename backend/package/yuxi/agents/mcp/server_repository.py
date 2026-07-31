from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from yuxi.storage.postgres.models_business import MCPServer


class MCPServerRepository:
    """MCP 服务器数据访问层，封装 MCPServer 的 SQLAlchemy 查询。

    遵循项目 Repository 规范：构造函数注入 db_session，不自行管理 session 生命周期。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_slug(self, slug: str) -> MCPServer | None:
        result = await self.db.execute(select(MCPServer).filter(MCPServer.slug == slug))
        return result.scalar_one_or_none()

    async def get_enabled_by_slug(self, slug: str) -> MCPServer | None:
        result = await self.db.execute(
            select(MCPServer).where(MCPServer.enabled == 1, MCPServer.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[MCPServer]:
        result = await self.db.execute(select(MCPServer))
        return list(result.scalars().all())

    async def list_enabled(self, slugs: list[str] | None = None) -> list[MCPServer]:
        stmt = select(MCPServer).where(MCPServer.enabled == 1)
        if slugs:
            stmt = stmt.where(MCPServer.slug.in_(slugs))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.db.execute(select(func.count(MCPServer.slug)))
        return int(result.scalar() or 0)

    async def exists_by_slug(self, slug: str) -> bool:
        result = await self.db.execute(select(MCPServer.id).where(MCPServer.slug == slug))
        return result.scalar_one_or_none() is not None

    async def add(self, server: MCPServer) -> MCPServer:
        self.db.add(server)
        await self.db.commit()
        await self.db.refresh(server)
        return server

    async def delete(self, server: MCPServer) -> None:
        await self.db.delete(server)
        await self.db.commit()

    async def commit_refresh(self, server: MCPServer) -> MCPServer:
        await self.db.commit()
        await self.db.refresh(server)
        return server
