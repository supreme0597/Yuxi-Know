from __future__ import annotations

import asyncio
import json
import secrets as secrets_module
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from yuxi.services.mcp_auth.config_models import MCPAuthConfig
from yuxi.services.mcp_auth.template_resolver import resolve_template_value
from yuxi.services.run_queue_service import get_redis_client
from yuxi.utils import logger

TOKEN_KEY_PREFIX = "yuxi:mcp:token:v1:connection"
LOCK_KEY_PREFIX = "yuxi:mcp:token-refresh-lock:v1:connection"
LOCK_TTL_SECONDS = 30
LOCK_WAIT_SECONDS = LOCK_TTL_SECONDS + 1.0
LOCK_POLL_SECONDS = 0.02

_LOCK_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


def _parse_expiry(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    return None


def normalize_token_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    token = dict(payload)
    expires_at = _parse_expiry(token.get("expires_at"))
    if expires_at is None:
        expires_in = token.get("expires_in")
        if isinstance(expires_in, (int, float)) and float(expires_in) > 0:
            expires_at = datetime.now(tz=UTC) + timedelta(seconds=float(expires_in))
    if expires_at is not None:
        token["expires_at"] = expires_at.isoformat()
    return token


def token_is_expiring(token: Mapping[str, Any], *, pre_refresh_seconds: int) -> bool:
    if not token.get("access_token"):
        return True
    expires_at = _parse_expiry(token.get("expires_at"))
    if expires_at is None:
        return True
    return expires_at <= datetime.now(tz=UTC) + timedelta(seconds=pre_refresh_seconds)


class RedisTokenCache:
    def __init__(self, redis_client_factory: Callable[[], Awaitable[Any]] | None = None):
        self._redis_client_factory = redis_client_factory or get_redis_client

    @staticmethod
    def _token_key(connection_id: int) -> str:
        return f"{TOKEN_KEY_PREFIX}:{connection_id}"

    @staticmethod
    def _lock_key(connection_id: int) -> str:
        return f"{LOCK_KEY_PREFIX}:{connection_id}"

    async def _redis(self):
        return await self._redis_client_factory()

    async def get(self, connection_id: int) -> dict[str, Any] | None:
        raw = await (await self._redis()).get(self._token_key(connection_id))
        if not raw:
            return None
        if isinstance(raw, dict):
            return normalize_token_payload(raw)
        return normalize_token_payload(json.loads(raw))

    async def set(self, connection_id: int, payload: Mapping[str, Any]) -> dict[str, Any]:
        token = normalize_token_payload(payload)
        expires_at = _parse_expiry(token.get("expires_at"))
        if expires_at is None:
            return token
        ttl = max(1, int((expires_at - datetime.now(tz=UTC)).total_seconds()))
        await (await self._redis()).set(
            self._token_key(connection_id),
            json.dumps(token, ensure_ascii=False, separators=(",", ":")),
            ex=ttl,
        )
        return token

    async def delete(self, connection_id: int) -> None:
        await (await self._redis()).delete(self._token_key(connection_id))

    async def acquire_lock(self, connection_id: int) -> str | None:
        value = secrets_module.token_urlsafe(18)
        acquired = await (await self._redis()).set(self._lock_key(connection_id), value, ex=LOCK_TTL_SECONDS, nx=True)
        return value if acquired else None

    async def release_lock(self, connection_id: int, value: str) -> None:
        redis = await self._redis()
        await redis.eval(_LOCK_RELEASE_SCRIPT, 1, self._lock_key(connection_id), value)


def _extract_response(payload: Mapping[str, Any], response_map: Mapping[str, str] | None) -> dict[str, Any]:
    mapping = response_map or {
        "access_token": "access_token",
        "refresh_token": "refresh_token",
        "expires_in": "expires_in",
        "expires_at": "expires_at",
        "token_type": "token_type",
        "scope": "scope",
    }
    result: dict[str, Any] = {}
    for output_name, dotted_path in mapping.items():
        current: Any = payload
        try:
            for segment in dotted_path.split("."):
                current = current[segment]
        except (KeyError, TypeError):
            continue
        result[output_name] = current
    return normalize_token_payload(result)


async def fetch_dynamic_token(
    auth_config: MCPAuthConfig,
    *,
    context: Mapping[str, Any],
    secrets: Mapping[str, Any],
    current_token: Mapping[str, Any],
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    request_config = dict(auth_config.token_request or {})
    refresh_config = request_config.get("refresh")
    refresh_token = current_token.get("refresh_token")

    if auth_config.provider == "authorization_code" and not refresh_token:
        raise ValueError("authorization_code provider requires an existing refresh_token")
    if refresh_token and isinstance(refresh_config, dict):
        request_config = dict(refresh_config)
    elif auth_config.provider == "authorization_code":
        request_config.setdefault("body_type", "form")
        body = dict(request_config.get("body_template") or {})
        body.setdefault("grant_type", "refresh_token")
        body.setdefault("refresh_token", "${token.refresh_token}")
        request_config["body_template"] = body

    created_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
    try:
        headers = resolve_template_value(
            request_config.get("headers") or {},
            context=context,
            secret=secrets,
            token=current_token,
            access_token=current_token.get("access_token"),
        )
        body = resolve_template_value(
            request_config.get("body_template") or {},
            context=context,
            secret=secrets,
            token=current_token,
            access_token=current_token.get("access_token"),
        )
        kwargs: dict[str, Any] = {"headers": headers}
        if request_config.get("body_type", "json") == "form":
            kwargs["data"] = body
        else:
            kwargs["json"] = body
        response = await client.request(
            str(request_config.get("method") or "POST").upper(),
            str(request_config["url"]),
            **kwargs,
        )
        response.raise_for_status()
        token = _extract_response(response.json(), request_config.get("response_map"))
        if not token.get("access_token"):
            raise ValueError("token endpoint response missing access_token")
        if refresh_token and not token.get("refresh_token"):
            token["refresh_token"] = refresh_token
        return token
    finally:
        if created_client:
            await client.aclose()


async def resolve_dynamic_token(
    connection_id: int,
    auth_config: MCPAuthConfig,
    *,
    context: Mapping[str, Any],
    secrets: Mapping[str, Any],
    credential_token: Mapping[str, Any],
    cache: RedisTokenCache | None = None,
    fetcher: Callable[..., Awaitable[dict[str, Any]]] = fetch_dynamic_token,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    cache = cache or RedisTokenCache()
    pre_refresh = auth_config.refresh_policy.pre_refresh_seconds

    try:
        cached = await cache.get(connection_id)
    except Exception as exc:
        logger.warning("MCP token cache unavailable for connection {}: {}", connection_id, type(exc).__name__)
        cached = None
    if cached and not token_is_expiring(cached, pre_refresh_seconds=pre_refresh):
        return cached

    seed = normalize_token_payload(cached or credential_token)
    if seed and not token_is_expiring(seed, pre_refresh_seconds=pre_refresh):
        return seed

    try:
        lock_value = await cache.acquire_lock(connection_id)
    except Exception:
        lock_value = None
        cache = None

    if cache is not None and lock_value is None:
        deadline = asyncio.get_running_loop().time() + LOCK_WAIT_SECONDS
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(LOCK_POLL_SECONDS)
            try:
                refreshed = await cache.get(connection_id)
            except Exception:
                cache = None
                break
            if refreshed and not token_is_expiring(refreshed, pre_refresh_seconds=pre_refresh):
                return refreshed
            try:
                lock_value = await cache.acquire_lock(connection_id)
            except Exception:
                cache = None
                break
            if lock_value is not None:
                break

    try:
        token = normalize_token_payload(
            await fetcher(
                auth_config=auth_config,
                context=context,
                secrets=secrets,
                current_token=seed,
                http_client=http_client,
            )
        )
        if cache is not None:
            try:
                token = await cache.set(connection_id, token)
            except Exception as exc:
                logger.warning("MCP token cache write failed for connection {}: {}", connection_id, type(exc).__name__)
        return token
    finally:
        if cache is not None and lock_value is not None:
            try:
                await cache.release_lock(connection_id, lock_value)
            except Exception:
                pass
