from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MCPCachePolicy:
    partition: str
    cache_tool_objects: bool
    cache_manifest: bool
    shared_across_users: bool


def build_cache_policy(provider: str | None, connection: Any | None) -> MCPCachePolicy:
    if not provider or provider == "legacy_static":
        return MCPCachePolicy("global", True, True, True)
    if connection is None:
        raise ValueError("MCP runtime auth requires an active connection before cache policy resolution")

    partition = f"connection:{connection.id}"
    shared = connection.scope_type == "system"
    dynamic = provider in {"custom_http_token", "client_credentials", "authorization_code"}
    return MCPCachePolicy(
        partition=partition,
        cache_tool_objects=not dynamic,
        cache_manifest=True,
        shared_across_users=shared,
    )
