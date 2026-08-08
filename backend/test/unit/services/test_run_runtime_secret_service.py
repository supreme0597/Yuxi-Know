from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import yaml

from yuxi.services import run_runtime_secret_service as service

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def hset(self, key, *, mapping):
        self.commands.append(("hset", key, dict(mapping)))
        return self

    def expire(self, key, seconds):
        self.commands.append(("expire", key, seconds))
        return self

    async def execute(self):
        self.redis.pipeline_calls.append(tuple(self.commands))


class FakeRedis:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.pipeline_calls = []
        self.delete_calls = []

    def pipeline(self, *, transaction):
        assert transaction is True
        return FakePipeline(self)

    async def hgetall(self, key):
        return dict(self.values.get(key) or {})

    async def delete(self, key):
        self.values.pop(key, None)
        self.delete_calls.append(key)


@pytest.mark.asyncio
async def test_runtime_secret_operations_do_not_use_shared_persistent_redis(monkeypatch: pytest.MonkeyPatch):
    redis = FakeRedis()
    dedicated_client = AsyncMock(return_value=redis)
    shared_client = AsyncMock(return_value=redis)
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", dedicated_client, raising=False)
    monkeypatch.setattr(service, "get_async_redis_client", shared_client, raising=False)

    await service.store_run_browser_cookie_secret("run-volatile", None)

    dedicated_client.assert_awaited_once_with()
    shared_client.assert_not_awaited()


def test_runtime_secret_redis_config_uses_dedicated_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_RUN_RUNTIME_SECRET_REDIS_URL", "redis://volatile-secrets:6380/2")

    build_config = getattr(service, "_runtime_secret_redis_config", lambda: None)
    config = build_config()

    assert config is not None
    assert config.url == "redis://volatile-secrets:6380/2"


@pytest.mark.parametrize("compose_file", ["docker-compose.yml", "docker-compose.prod.yml"])
def test_compose_runtime_secret_redis_has_no_disk_persistence(compose_file: str):
    compose = yaml.safe_load((REPOSITORY_ROOT / compose_file).read_text(encoding="utf-8"))
    runtime_secret_redis = compose["services"]["runtime-secret-redis"]

    assert runtime_secret_redis["command"] == 'redis-server --save "" --appendonly no'
    assert runtime_secret_redis["tmpfs"] == ["/data"]
    assert "volumes" not in runtime_secret_redis


@pytest.mark.asyncio
async def test_store_run_browser_cookie_secret_preserves_raw_header(monkeypatch: pytest.MonkeyPatch):
    redis = FakeRedis()
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", AsyncMock(return_value=redis))
    secret = service.BrowserCookieRuntimeSecret(
        header="sid=abc; theme=dark; sid=path-specific",
        origin="https://yuxi.example.com",
    )

    await service.store_run_browser_cookie_secret("run-1", secret)

    assert redis.pipeline_calls == [
        (
            (
                "hset",
                "agent-run:runtime-secret:run-1",
                {
                    "header": "sid=abc; theme=dark; sid=path-specific",
                    "origin": "https://yuxi.example.com",
                },
            ),
            ("expire", "agent-run:runtime-secret:run-1", 14_400),
        )
    ]


@pytest.mark.asyncio
async def test_store_run_browser_cookie_secret_uses_configured_ttl(monkeypatch: pytest.MonkeyPatch):
    redis = FakeRedis()
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", AsyncMock(return_value=redis))
    monkeypatch.setenv("AGENT_RUN_RUNTIME_SECRET_TTL_SECONDS", "7200")

    await service.store_run_browser_cookie_secret(
        "run-2",
        service.BrowserCookieRuntimeSecret(header="sid=abc", origin="https://yuxi.example.com"),
    )

    assert redis.pipeline_calls[0][1] == ("expire", "agent-run:runtime-secret:run-2", 7200)


@pytest.mark.asyncio
async def test_store_none_deletes_stale_secret(monkeypatch: pytest.MonkeyPatch):
    redis = FakeRedis(
        values={
            "agent-run:runtime-secret:run-1": {
                "header": "stale",
                "origin": "https://old.example.com",
            }
        }
    )
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", AsyncMock(return_value=redis))

    await service.store_run_browser_cookie_secret("run-1", None)

    assert redis.delete_calls == ["agent-run:runtime-secret:run-1"]
    assert redis.pipeline_calls == []


@pytest.mark.asyncio
async def test_load_run_browser_cookie_secret_returns_complete_secret(monkeypatch: pytest.MonkeyPatch):
    redis = FakeRedis(
        values={
            "agent-run:runtime-secret:run-1": {
                "header": "sid=abc; theme=dark",
                "origin": "https://yuxi.example.com",
            }
        }
    )
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", AsyncMock(return_value=redis))

    secret = await service.load_run_browser_cookie_secret("run-1")

    assert secret == service.BrowserCookieRuntimeSecret(
        header="sid=abc; theme=dark",
        origin="https://yuxi.example.com",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stored",
    [{}, {"header": "sid=abc"}, {"origin": "https://yuxi.example.com"}],
)
async def test_load_incomplete_secret_returns_none(monkeypatch: pytest.MonkeyPatch, stored: dict[str, str]):
    redis = FakeRedis(values={"agent-run:runtime-secret:run-1": stored})
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", AsyncMock(return_value=redis))

    assert await service.load_run_browser_cookie_secret("run-1") is None


@pytest.mark.asyncio
async def test_delete_run_browser_cookie_secret_uses_run_key(monkeypatch: pytest.MonkeyPatch):
    redis = FakeRedis()
    monkeypatch.setattr(service, "get_run_runtime_secret_redis_client", AsyncMock(return_value=redis))

    await service.delete_run_browser_cookie_secret("run-delete")

    assert redis.delete_calls == ["agent-run:runtime-secret:run-delete"]
