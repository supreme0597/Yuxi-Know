"""模型供应商配置数据访问层。"""

import json

from sqlalchemy import select
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


async def count_provider_references(provider_id: str) -> dict[str, list[dict]]:
    """扫描所有可能引用该 provider 的资源，返回 {kind: [{id, name}, ...]}。

    各来源通过各自 repository 的现成查询函数读取（独立会话），
    任一来源异常都不影响删除事务；缺失/不可用的来源直接跳过。
    """
    if not provider_id:
        return {}

    references: dict[str, list[dict]] = {}

    # 知识库：直接复用现成查询函数（独立会话，缺失/异常均被下方 except 吞掉，不依赖环境开关）
    try:
        from yuxi.repositories.knowledge_base_repository import KnowledgeBaseRepository

        for kb in await KnowledgeBaseRepository().get_all():
            if any(spec == provider_id for spec in (kb.embedding_model_spec, kb.llm_model_spec) if spec):
                references.setdefault("knowledge", []).append({"id": kb.id, "name": kb.name})
    except Exception:
        pass

    # 智能体：扫描 config_json 是否包含该 provider_id
    try:
        from yuxi.repositories.agent_repository import AgentRepository

        for agent in await AgentRepository().list_all():
            if agent.config_json and provider_id in json.dumps(agent.config_json, ensure_ascii=False):
                references.setdefault("agent", []).append({"id": agent.id, "name": agent.name})
    except Exception:
        pass

    return references
