"""模型供应商配置数据访问层。"""

import os

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.storage.postgres.models_business import ModelProvider


async def list_model_providers(db: AsyncSession) -> list[ModelProvider]:
    """获取全部模型供应商配置。"""
    result = await db.execute(
        select(ModelProvider).order_by(ModelProvider.is_enabled.desc(), ModelProvider.provider_id.asc())
    )
    return list(result.scalars().all())


async def get_model_provider(db: AsyncSession, provider_id: str) -> ModelProvider | None:
    """按 provider_id 获取模型供应商配置。"""
    result = await db.execute(select(ModelProvider).where(ModelProvider.provider_id == provider_id))
    return result.scalar_one_or_none()


async def create_model_provider(db: AsyncSession, data: dict) -> ModelProvider:
    """创建模型供应商配置。"""
    provider = ModelProvider(**data)
    db.add(provider)
    await db.flush()
    await db.refresh(provider)
    return provider


async def update_model_provider(db: AsyncSession, provider: ModelProvider, data: dict) -> ModelProvider:
    """更新模型供应商配置。"""
    for key, value in data.items():
        if key != "provider_id":
            setattr(provider, key, value)
    await db.flush()
    await db.refresh(provider)
    return provider


async def delete_model_provider(db: AsyncSession, provider: ModelProvider) -> None:
    """删除模型供应商配置。"""
    await db.delete(provider)
    await db.flush()


async def list_visible_model_providers(db: AsyncSession, user) -> list[ModelProvider]:
    """按当前用户可见性过滤后的供应商列表。superadmin 短路。"""
    providers = await list_model_providers(db)
    if user.role == "superadmin":
        return providers
    from yuxi.models.providers.share import user_can_access_provider

    return [p for p in providers if user_can_access_provider(user, p)]


async def get_visible_model_provider(db: AsyncSession, provider_id: str, user) -> ModelProvider | None:
    """按 provider_id 拉取并按可见性过滤；不可见返回 None。"""
    provider = await get_model_provider(db, provider_id)
    if provider is None:
        return None
    from yuxi.models.providers.share import user_can_access_provider

    if not user_can_access_provider(user, provider):
        return None
    return provider


async def count_provider_references(db: AsyncSession, provider_id: str) -> dict[str, list[dict]]:
    """扫描所有可能引用该 provider 的资源，返回 {kind: [{id, name}, ...]}。"""
    if not provider_id:
        return {}

    references: dict[str, list[dict]] = {}
    spec_pattern = f"%{provider_id}%"

    if os.getenv("LITE_MODE", "").lower() not in {"true", "1"}:
        kb_sql = (
            "SELECT id, name FROM knowledges "
            "WHERE embedding_model_spec = :spec OR llm_model_spec = :spec OR query_llm_model_spec = :spec"
        )
        try:
            result = await db.execute(text(kb_sql), {"spec": provider_id})
            rows = list(result.all())
            if rows:
                references["knowledge"] = [{"id": int(r[0]), "name": r[1]} for r in rows]
        except Exception:
            pass

    agent_sql = "SELECT id, name FROM agents WHERE config_json::text LIKE :pattern"
    try:
        result = await db.execute(text(agent_sql), {"pattern": spec_pattern})
        rows = list(result.all())
        if rows:
            references["agent"] = [{"id": int(r[0]), "name": r[1]} for r in rows]
    except Exception:
        pass

    config_sql = "SELECT id, key FROM config_options WHERE value::text LIKE :pattern"
    try:
        result = await db.execute(text(config_sql), {"pattern": spec_pattern})
        rows = list(result.all())
        if rows:
            references["config_option"] = [{"id": int(r[0]), "name": r[1]} for r in rows]
    except Exception:
        pass

    return references
