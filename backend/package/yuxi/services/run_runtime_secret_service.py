from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

from yuxi.storage.redis import RedisConfig, create_async_redis_client

RUN_RUNTIME_SECRET_KEY_PREFIX = "agent-run:runtime-secret:"
DEFAULT_RUN_RUNTIME_SECRET_TTL_SECONDS = 14_400
DEFAULT_RUN_RUNTIME_SECRET_REDIS_URL = "redis://runtime-secret-redis:6379/0"

_runtime_secret_redis_client: Any | None = None
_runtime_secret_redis_lock: asyncio.Lock | None = None


@dataclass(frozen=True, slots=True)
class BrowserCookieRuntimeSecret:
    header: str
    origin: str


def _secret_key(run_id: str) -> str:
    return f"{RUN_RUNTIME_SECRET_KEY_PREFIX}{run_id}"


def _secret_ttl_seconds() -> int:
    return int(
        os.getenv(
            "AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS",
            str(DEFAULT_RUN_RUNTIME_SECRET_TTL_SECONDS),
        )
    )


def _runtime_secret_redis_config() -> RedisConfig:
    return RedisConfig(
        url=os.getenv(
            "AGENT_RUN_RUNTIME_SECRET_REDIS_URL",
            DEFAULT_RUN_RUNTIME_SECRET_REDIS_URL,
        )
    )


def _get_runtime_secret_redis_lock() -> asyncio.Lock:
    global _runtime_secret_redis_lock
    if _runtime_secret_redis_lock is None:
        _runtime_secret_redis_lock = asyncio.Lock()
    return _runtime_secret_redis_lock


async def get_run_runtime_secret_redis_client() -> Any:
    global _runtime_secret_redis_client
    if _runtime_secret_redis_client is not None:
        return _runtime_secret_redis_client

    async with _get_runtime_secret_redis_lock():
        if _runtime_secret_redis_client is None:
            _runtime_secret_redis_client = await create_async_redis_client(_runtime_secret_redis_config())
        return _runtime_secret_redis_client


async def store_run_browser_cookie_secret(
    run_id: str,
    secret: BrowserCookieRuntimeSecret | None,
) -> None:
    redis = await get_run_runtime_secret_redis_client()
    key = _secret_key(run_id)
    if secret is None:
        await redis.delete(key)
        return

    async with redis.pipeline(transaction=True) as pipeline:
        pipeline.hset(key, mapping={"header": secret.header, "origin": secret.origin})
        pipeline.expire(key, _secret_ttl_seconds())
        await pipeline.execute()


async def load_run_browser_cookie_secret(run_id: str) -> BrowserCookieRuntimeSecret | None:
    redis = await get_run_runtime_secret_redis_client()
    value = await redis.hgetall(_secret_key(run_id))
    header = value.get("header")
    origin = value.get("origin")
    if not header or not origin:
        return None
    return BrowserCookieRuntimeSecret(header=str(header), origin=str(origin))


async def delete_run_browser_cookie_secret(run_id: str) -> None:
    redis = await get_run_runtime_secret_redis_client()
    await redis.delete(_secret_key(run_id))
