from unittest.mock import AsyncMock

import pytest

from yuxi.services import run_runtime_secret_service as service


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

    def delete(self, key):
        self.commands.append(("delete", key))
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
async def test_runtime_secret_uses_existing_main_redis(monkeypatch: pytest.MonkeyPatch):
    redis = FakeRedis()
    shared_client = AsyncMock(return_value=redis)
    monkeypatch.setattr(service, "get_async_redis_client", shared_client, raising=False)

    await service.store_run_browser_cookie_secret(
        "run-1",
        service.BrowserCookieRuntimeSecret(header="sso=abc; theme=dark"),
    )

    shared_client.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_store_run_browser_cookie_secret_preserves_raw_header(monkeypatch: pytest.MonkeyPatch):
    redis = FakeRedis()
    monkeypatch.setattr(service, "get_async_redis_client", AsyncMock(return_value=redis), raising=False)
    monkeypatch.setattr(service, "agent_run_runtime_secret_ttl_seconds", lambda: 43_200, raising=False)
    secret = service.BrowserCookieRuntimeSecret(
        header="sid=abc; theme=dark; sid=path-specific",
    )

    await service.store_run_browser_cookie_secret("run-1", secret)

    assert redis.pipeline_calls == [
        (
            ("delete", "agent-run:runtime-secret:run-1"),
            (
                "hset",
                "agent-run:runtime-secret:run-1",
                {"header": "sid=abc; theme=dark; sid=path-specific"},
            ),
            ("expire", "agent-run:runtime-secret:run-1", 43_200),
        )
    ]


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
    monkeypatch.setattr(service, "get_async_redis_client", AsyncMock(return_value=redis), raising=False)

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
    monkeypatch.setattr(service, "get_async_redis_client", AsyncMock(return_value=redis), raising=False)

    secret = await service.load_run_browser_cookie_secret("run-1")

    assert secret == service.BrowserCookieRuntimeSecret(header="sid=abc; theme=dark")


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [{}, {"origin": "https://yuxi.example.com"}])
async def test_load_incomplete_secret_returns_none(monkeypatch: pytest.MonkeyPatch, stored: dict[str, str]):
    redis = FakeRedis(values={"agent-run:runtime-secret:run-1": stored})
    monkeypatch.setattr(service, "get_async_redis_client", AsyncMock(return_value=redis), raising=False)

    assert await service.load_run_browser_cookie_secret("run-1") is None


@pytest.mark.asyncio
async def test_delete_run_browser_cookie_secret_uses_run_key(monkeypatch: pytest.MonkeyPatch):
    redis = FakeRedis()
    monkeypatch.setattr(service, "get_async_redis_client", AsyncMock(return_value=redis), raising=False)

    await service.delete_run_browser_cookie_secret("run-delete")

    assert redis.delete_calls == ["agent-run:runtime-secret:run-delete"]
