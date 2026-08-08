from __future__ import annotations

from dataclasses import dataclass

from yuxi.services.run_queue_service import agent_run_runtime_secret_ttl_seconds
from yuxi.storage.redis import get_async_redis_client

RUN_RUNTIME_SECRET_KEY_PREFIX = "agent-run:runtime-secret:"


@dataclass(frozen=True, slots=True)
class BrowserCookieRuntimeSecret:
    header: str


def _secret_key(run_id: str) -> str:
    return f"{RUN_RUNTIME_SECRET_KEY_PREFIX}{run_id}"


async def store_run_browser_cookie_secret(
    run_id: str,
    secret: BrowserCookieRuntimeSecret | None,
) -> None:
    redis = await get_async_redis_client()
    key = _secret_key(run_id)
    if secret is None:
        await redis.delete(key)
        return

    async with redis.pipeline(transaction=True) as pipeline:
        pipeline.delete(key)
        pipeline.hset(key, mapping={"header": secret.header})
        pipeline.expire(key, agent_run_runtime_secret_ttl_seconds())
        await pipeline.execute()


async def load_run_browser_cookie_secret(run_id: str) -> BrowserCookieRuntimeSecret | None:
    redis = await get_async_redis_client()
    value = await redis.hgetall(_secret_key(run_id))
    header = value.get("header")
    if not header:
        return None
    return BrowserCookieRuntimeSecret(header=str(header))


async def delete_run_browser_cookie_secret(run_id: str) -> None:
    redis = await get_async_redis_client()
    await redis.delete(_secret_key(run_id))
