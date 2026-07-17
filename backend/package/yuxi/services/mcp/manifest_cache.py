from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

from yuxi.services.run_queue_service import get_redis_client
from yuxi.utils import logger

MANIFEST_TTL_SECONDS = int(os.getenv("YUXI_MCP_MANIFEST_TTL_SECONDS", "3600"))
_MANIFEST_PREFIX = "yuxi:mcp:manifest:v1"
_SERVER_REVISION_PREFIX = "yuxi:mcp:manifest-server-revision:v1"
_PARTITION_REVISION_PREFIX = "yuxi:mcp:manifest-partition-revision:v1"


class RedisMCPManifestCache:
    def __init__(self, redis_client_factory: Callable[[], Awaitable[Any]] | None = None):
        self._redis_client_factory = redis_client_factory or get_redis_client

    async def _redis(self):
        return await self._redis_client_factory()

    @staticmethod
    def _server_revision_key(server_name: str) -> str:
        return f"{_SERVER_REVISION_PREFIX}:{server_name}"

    @staticmethod
    def _partition_revision_key(server_name: str, partition: str) -> str:
        return f"{_PARTITION_REVISION_PREFIX}:{server_name}:{partition}"

    @staticmethod
    def _manifest_key(cache_key: str) -> str:
        return f"{_MANIFEST_PREFIX}:{cache_key}"

    @staticmethod
    def build_cache_key(
        server_name: str,
        partition: str,
        revisions: tuple[int, int],
        config_hash: str,
    ) -> str:
        server_revision, partition_revision = revisions
        return f"{server_name}:{partition}:s{server_revision}:p{partition_revision}:{config_hash}"

    async def get_revisions(self, server_name: str, partition: str) -> tuple[int, int]:
        try:
            redis = await self._redis()
            server_raw = await redis.get(self._server_revision_key(server_name))
            partition_raw = await redis.get(self._partition_revision_key(server_name, partition))
            return int(server_raw or 0), int(partition_raw or 0)
        except Exception as exc:
            logger.warning("MCP manifest revisions unavailable for '{}': {}", server_name, type(exc).__name__)
            return 0, 0

    async def get_manifest(self, cache_key: str) -> dict[str, Any] | None:
        try:
            raw = await (await self._redis()).get(self._manifest_key(cache_key))
            if not raw:
                return None
            return raw if isinstance(raw, dict) else json.loads(raw)
        except Exception as exc:
            logger.warning("MCP manifest cache miss for '{}': {}", cache_key, type(exc).__name__)
            return None

    async def set_manifest(self, cache_key: str, manifest: dict[str, Any]) -> None:
        try:
            await (await self._redis()).set(
                self._manifest_key(cache_key),
                json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
                ex=MANIFEST_TTL_SECONDS,
            )
        except Exception as exc:
            logger.warning("MCP manifest cache write failed for '{}': {}", cache_key, type(exc).__name__)

    async def bump_server_revision(self, server_name: str) -> int:
        try:
            return int(await (await self._redis()).incr(self._server_revision_key(server_name)))
        except Exception as exc:
            logger.warning("MCP server revision bump failed for '{}': {}", server_name, type(exc).__name__)
            return 0

    async def bump_partition_revision(self, server_name: str, partition: str) -> int:
        try:
            return int(await (await self._redis()).incr(self._partition_revision_key(server_name, partition)))
        except Exception as exc:
            logger.warning("MCP partition revision bump failed for '{}': {}", server_name, type(exc).__name__)
            return 0
