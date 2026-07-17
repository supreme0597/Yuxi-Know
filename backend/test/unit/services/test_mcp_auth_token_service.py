from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs

import httpx
import pytest

from yuxi.services.mcp_auth.config_models import MCPAuthConfig
from yuxi.services.mcp_auth.token_service import RedisTokenCache, fetch_dynamic_token, resolve_dynamic_token

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


class FakeRedis:
    def __init__(self):
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.locks: set[str] = set()

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, *, ex=None, nx=False):
        if nx and key in self.locks:
            return False
        self.data[key] = value
        if nx:
            self.locks.add(key)
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def eval(self, script, numkeys, key, value):
        del script, numkeys
        if self.data.get(key) == value:
            self.data.pop(key, None)
            self.locks.discard(key)
            return 1
        return 0

    async def delete(self, key):
        self.data.pop(key, None)
        self.locks.discard(key)


def dynamic_config(pre_refresh_seconds: int = 30) -> MCPAuthConfig:
    return MCPAuthConfig.model_validate(
        {
            "provider": "custom_http_token",
            "binding_scope": "user",
            "inject": {
                "target": "headers",
                "entries": [{"name": "Authorization", "value_template": "Bearer ${access_token}"}],
            },
            "refresh_policy": {"pre_refresh_seconds": pre_refresh_seconds},
            "token_request": {"url": "https://auth.example/token"},
        }
    )


async def test_token_cache_key_and_ttl_are_connection_scoped():
    redis = FakeRedis()
    cache = RedisTokenCache(redis_client_factory=lambda: asyncio.sleep(0, result=redis))
    expires_at = datetime.now(tz=UTC) + timedelta(seconds=120)

    await cache.set(17, {"access_token": "secret", "expires_at": expires_at.isoformat()})

    assert list(redis.data) == ["yuxi:mcp:token:v1:connection:17"]
    assert 1 <= redis.ttls["yuxi:mcp:token:v1:connection:17"] <= 120


async def test_resolve_dynamic_token_reuses_fresh_cached_token():
    redis = FakeRedis()
    cache = RedisTokenCache(redis_client_factory=lambda: asyncio.sleep(0, result=redis))
    await cache.set(7, {"access_token": "cached", "expires_in": 300})
    calls = 0

    async def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return {"access_token": "new", "expires_in": 300}

    token = await resolve_dynamic_token(
        7,
        dynamic_config(),
        context={"user_id": "1"},
        secrets={},
        credential_token={},
        cache=cache,
        fetcher=fetcher,
    )

    assert token["access_token"] == "cached"
    assert calls == 0


async def test_token_without_expiry_is_not_reused_or_cached():
    redis = FakeRedis()
    cache = RedisTokenCache(redis_client_factory=lambda: asyncio.sleep(0, result=redis))
    calls = 0

    async def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return {"access_token": f"token-{calls}"}

    first = await resolve_dynamic_token(
        8,
        dynamic_config(),
        context={"user_id": "1"},
        secrets={},
        credential_token={},
        cache=cache,
        fetcher=fetcher,
    )
    second = await resolve_dynamic_token(
        8,
        dynamic_config(),
        context={"user_id": "1"},
        secrets={},
        credential_token={},
        cache=cache,
        fetcher=fetcher,
    )

    assert first["access_token"] == "token-1"
    assert second["access_token"] == "token-2"
    assert calls == 2
    assert not any(key.startswith("yuxi:mcp:token:v1:connection:8") for key in redis.data)


async def test_concurrent_refresh_is_singleflight_per_connection():
    redis = FakeRedis()
    cache = RedisTokenCache(redis_client_factory=lambda: asyncio.sleep(0, result=redis))
    calls = 0

    async def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return {"access_token": "shared", "expires_in": 300}

    results = await asyncio.gather(
        *[
            resolve_dynamic_token(
                23,
                dynamic_config(),
                context={"user_id": str(index)},
                secrets={},
                credential_token={},
                cache=cache,
                fetcher=fetcher,
            )
            for index in range(10)
        ]
    )

    assert calls == 1
    assert {item["access_token"] for item in results} == {"shared"}


async def test_redis_failure_falls_back_to_request_local_fetch():
    async def broken_redis():
        raise RuntimeError("redis unavailable")

    cache = RedisTokenCache(redis_client_factory=broken_redis)

    async def fetcher(**kwargs):
        return {"access_token": "local", "expires_in": 60}

    token = await resolve_dynamic_token(
        99,
        dynamic_config(),
        context={"user_id": "1"},
        secrets={},
        credential_token={},
        cache=cache,
        fetcher=fetcher,
    )

    assert token["access_token"] == "local"


async def test_custom_http_token_supports_nested_response_mapping():
    config = dynamic_config()
    config.token_request["response_map"] = {
        "access_token": "data.token",
        "expires_in": "data.ttl",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://auth.example/token"
        return httpx.Response(200, json={"data": {"token": "mapped", "ttl": 90}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        token = await fetch_dynamic_token(
            config,
            context={"user_id": "1"},
            secrets={},
            current_token={},
            http_client=client,
        )

    assert token["access_token"] == "mapped"
    assert token["expires_at"]


async def test_authorization_code_uses_existing_refresh_token_only():
    config = MCPAuthConfig.model_validate(
        {
            "provider": "authorization_code",
            "binding_scope": "user",
            "inject": {"target": "headers", "entries": []},
            "token_request": {
                "url": "https://auth.example/oauth/token",
                "body_type": "form",
                "body_template": {"client_id": "${secret.client_id}"},
            },
        }
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode())
        assert form == {
            "client_id": ["client-1"],
            "grant_type": ["refresh_token"],
            "refresh_token": ["refresh-1"],
        }
        return httpx.Response(200, json={"access_token": "renewed", "expires_in": 120})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        token = await fetch_dynamic_token(
            config,
            context={"user_id": "1"},
            secrets={"client_id": "client-1"},
            current_token={"refresh_token": "refresh-1"},
            http_client=client,
        )

    assert token["access_token"] == "renewed"
    assert token["refresh_token"] == "refresh-1"
