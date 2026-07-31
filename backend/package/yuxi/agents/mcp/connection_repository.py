from __future__ import annotations

from typing import Any

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from yuxi.storage.postgres.models_business import Department, MCPConnection, User


class MCPConnectionRepository:
    """MCP 绑定连接数据访问层，封装 MCPConnection 的 SQLAlchemy 查询。

    遵循项目 Repository 规范：构造函数注入 db_session，不自行管理 session 生命周期。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, connection_id: int) -> MCPConnection | None:
        result = await self.db.execute(select(MCPConnection).where(MCPConnection.id == connection_id))
        return result.scalar_one_or_none()

    async def find_active(
        self, *, server_name: str, scope_type: str, scope_id: str
    ) -> MCPConnection | None:
        result = await self.db.execute(
            select(MCPConnection).where(
                MCPConnection.server_name == server_name,
                MCPConnection.scope_type == scope_type,
                MCPConnection.scope_id == scope_id,
                MCPConnection.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def find_requiring_reauth(
        self, *, server_name: str, scope_type: str, scope_id: str
    ) -> MCPConnection | None:
        """查找 status='reauth_required' 的连接，用于自动重授权尝试"""
        result = await self.db.execute(
            select(MCPConnection).where(
                MCPConnection.server_name == server_name,
                MCPConnection.scope_type == scope_type,
                MCPConnection.scope_id == scope_id,
                MCPConnection.status == "reauth_required",
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        server_name: str | None = None,
        scope_type: str | None = None,
        scope_id: str | None = None,
    ) -> list[MCPConnection]:
        stmt = select(MCPConnection)
        if server_name is not None:
            stmt = stmt.where(MCPConnection.server_name == server_name)
        if scope_type is not None:
            stmt = stmt.where(MCPConnection.scope_type == scope_type)
        if scope_id is not None:
            stmt = stmt.where(MCPConnection.scope_id == scope_id)
        stmt = stmt.order_by(MCPConnection.id.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, conditions: list[Any] | None = None) -> int:
        stmt = select(func.count()).select_from(MCPConnection)
        for condition in conditions or []:
            stmt = stmt.where(condition)
        result = await self.db.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_page(
        self,
        *,
        conditions: list[Any] | None = None,
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[list[MCPConnection], int]:
        normalized_page = max(1, page)
        normalized_page_size = min(max(1, page_size), 100)
        stmt = select(MCPConnection).order_by(MCPConnection.id.asc())
        count_stmt = select(func.count()).select_from(MCPConnection)
        for condition in conditions or []:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)
        stmt = stmt.limit(normalized_page_size).offset((normalized_page - 1) * normalized_page_size)
        total_result = await self.db.execute(count_stmt)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), int(total_result.scalar_one() or 0)

    async def add(self, connection: MCPConnection) -> MCPConnection:
        self.db.add(connection)
        await self.db.commit()
        await self.db.refresh(connection)
        return connection

    async def commit_refresh(self, connection: MCPConnection) -> MCPConnection:
        await self.db.commit()
        await self.db.refresh(connection)
        return connection

    async def delete(self, connection: MCPConnection) -> None:
        await self.db.delete(connection)
        await self.db.commit()

    @staticmethod
    def build_search_conditions(search: str) -> list[Any]:
        """构建全文搜索的 WHERE 条件列表，供 list_page / count 的 conditions 参数使用。"""
        keyword = str(search or "").strip()
        like_keyword = f"%{keyword}%"
        lowered_keyword = keyword.lower()
        conditions: list[Any] = [
            MCPConnection.display_name.ilike(like_keyword),
            MCPConnection.external_subject.ilike(like_keyword),
            MCPConnection.scope_id.ilike(like_keyword),
            MCPConnection.created_by.ilike(like_keyword),
            MCPConnection.updated_by.ilike(like_keyword),
            and_(
                MCPConnection.scope_type == "department",
                select(Department.id)
                .where(
                    cast(Department.id, String) == MCPConnection.scope_id,
                    Department.name.ilike(like_keyword),
                )
                .exists(),
            ),
            and_(
                MCPConnection.scope_type == "user",
                select(User.id)
                .where(
                    or_(
                        cast(User.id, String) == MCPConnection.scope_id,
                        User.uid == MCPConnection.scope_id,
                    ),
                    or_(User.username.ilike(like_keyword), User.uid.ilike(like_keyword)),
                )
                .exists(),
            ),
        ]
        if any(token in lowered_keyword for token in ("system", "global", "全局", "共享", "全部")):
            conditions.append(MCPConnection.scope_type == "system")
        if any(token in lowered_keyword for token in ("department", "dept", "部门")):
            conditions.append(MCPConnection.scope_type == "department")
        if any(token in lowered_keyword for token in ("user", "个人", "用户")):
            conditions.append(MCPConnection.scope_type == "user")
        return conditions
