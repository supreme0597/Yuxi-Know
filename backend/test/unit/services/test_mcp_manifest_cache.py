from __future__ import annotations

import asyncio

import pytest

from yuxi.services.mcp.manifest_cache import RedisMCPManifestCache

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


class FakeRedis:
    def __init__(self):
        self.data: dict[str, str] = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        del ex
        self.data[key] = value

    async def incr(self, key):
        value = int(self.data.get(key) or 0) + 1
        self.data[key] = str(value)
        return value


async def test_manifest_revision_and_partition_roundtrip():
    redis = FakeRedis()
    cache = RedisMCPManifestCache(redis_client_factory=lambda: asyncio.sleep(0, result=redis))

    revisions = await cache.get_revisions("billing", "connection:7")
    key = cache.build_cache_key("billing", "connection:7", revisions, "abc123")
    await cache.set_manifest(key, {"tools": [{"name": "lookup", "description": "safe"}]})

    assert key == "billing:connection:7:s0:p0:abc123"
    assert await cache.get_manifest(key) == {"tools": [{"name": "lookup", "description": "safe"}]}
    assert await cache.bump_partition_revision("billing", "connection:7") == 1
    assert await cache.bump_server_revision("billing") == 1
    assert await cache.get_revisions("billing", "connection:7") == (1, 1)


async def test_manifest_cache_does_not_cross_connection_partition():
    redis = FakeRedis()
    cache = RedisMCPManifestCache(redis_client_factory=lambda: asyncio.sleep(0, result=redis))
    key_a = cache.build_cache_key("billing", "connection:1", (0, 0), "same")
    key_b = cache.build_cache_key("billing", "connection:2", (0, 0), "same")

    await cache.set_manifest(key_a, {"tools": [{"name": "a"}]})

    assert await cache.get_manifest(key_a) is not None
    assert await cache.get_manifest(key_b) is None


async def test_manifest_cache_redis_failure_is_a_cache_miss():
    async def broken_redis():
        raise RuntimeError("redis unavailable")

    cache = RedisMCPManifestCache(redis_client_factory=broken_redis)

    assert await cache.get_manifest("billing:global:s0:p0:abc") is None
    assert await cache.get_revisions("billing", "global") == (0, 0)
