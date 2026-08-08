from __future__ import annotations

import importlib
import os

import pytest
import yuxi.services.run_queue_service as run_queue_service


class _FakeStreamRedis:
    def __init__(self):
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.expire_calls: list[tuple[str, int]] = []

    async def xadd(self, key: str, fields: dict[str, str], **kwargs):
        del kwargs
        stream = self.streams.setdefault(key, [])
        event_id = f"{1700000000000 + len(stream)}-0"
        stream.append((event_id, dict(fields)))
        return event_id

    async def expire(self, key: str, ttl: int):
        self.expire_calls.append((key, ttl))

    async def xrange(self, key: str, min: str, max: str, count: int):
        del max
        rows = list(self.streams.get(key, []))
        if min.startswith("("):
            cursor = min[1:]
            rows = [(event_id, fields) for event_id, fields in rows if event_id > cursor]
        elif min == "-":
            rows = list(rows)
        return rows[:count]

    async def xrevrange(self, key: str, max: str, min: str, count: int):
        del max, min
        rows = list(reversed(self.streams.get(key, [])))
        return rows[:count]


@pytest.fixture
def reload_execution_policy(monkeypatch: pytest.MonkeyPatch):
    names = (
        "AGENT_RUN_JOB_TIMEOUT_SECONDS",
        "AGENT_RUN_MAX_TRIES",
    )
    original = {name: os.environ.get(name) for name in names}

    def reload_with(**values):
        for name in names:
            monkeypatch.delenv(name, raising=False)
        for name, value in values.items():
            monkeypatch.setenv(name, str(value))
        return importlib.reload(run_queue_service)

    try:
        yield reload_with
    finally:
        for name, value in original.items():
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)
        importlib.reload(run_queue_service)


@pytest.mark.asyncio
async def test_get_redis_client_uses_storage_client(monkeypatch: pytest.MonkeyPatch):
    fake_client = object()

    async def fake_get_async_redis_client():
        return fake_client

    monkeypatch.setattr(run_queue_service, "get_async_redis_client", fake_get_async_redis_client)

    assert await run_queue_service.get_redis_client() is fake_client


@pytest.mark.asyncio
async def test_run_stream_event_roundtrip(monkeypatch: pytest.MonkeyPatch):
    fake_redis = _FakeStreamRedis()

    async def fake_get_async_redis_client():
        return fake_redis

    monkeypatch.setattr(run_queue_service, "get_async_redis_client", fake_get_async_redis_client)

    run_id = "run-1"
    seq1 = await run_queue_service.append_run_stream_event(run_id, "loading", {"items": [1]})
    seq2 = await run_queue_service.append_run_stream_event(
        run_id,
        "finished",
        {"chunk": {"status": "finished", "thread_id": "child-thread"}},
    )

    assert seq1 < seq2

    events = await run_queue_service.list_run_stream_events(run_id, after_seq="0-0", limit=100)
    assert [item["event_type"] for item in events] == ["loading", "finished"]
    assert events[0]["payload"]["schema_version"] == 1
    assert events[0]["payload"]["run_id"] == run_id
    assert events[0]["payload"]["payload"] == {"items": [1]}
    assert events[1]["payload"]["thread_id"] == "child-thread"

    next_events = await run_queue_service.list_run_stream_events(run_id, after_seq=seq1, limit=100)
    assert len(next_events) == 1
    assert next_events[0]["seq"] == seq2

    last_seq = await run_queue_service.get_last_run_stream_seq(run_id)
    assert last_seq == seq2

    recent_events = await run_queue_service.list_recent_run_stream_events(run_id, limit=2)
    assert [item["seq"] for item in recent_events] == [seq2, seq1]
    assert [item["event_type"] for item in recent_events] == ["finished", "loading"]


def test_normalize_after_seq_stream_id_only():
    assert run_queue_service.normalize_after_seq(None) == "0-0"
    assert run_queue_service.normalize_after_seq("1700000000000-3") == "1700000000000-3"
    assert run_queue_service.normalize_after_seq("12") == "0-0"
    assert run_queue_service.normalize_after_seq("bad-value") == "0-0"


def test_agent_run_execution_policy_defaults(reload_execution_policy):
    module = reload_execution_policy()

    assert module.AGENT_RUN_JOB_TIMEOUT_SECONDS == 3600
    assert module.AGENT_RUN_MAX_TRIES == 2
    assert module.AGENT_RUN_SECRET_TTL_SAFETY_FACTOR == 2
    assert module.agent_run_runtime_secret_ttl_seconds() == 14_400


def test_agent_run_execution_policy_reads_environment(reload_execution_policy):
    module = reload_execution_policy(
        AGENT_RUN_JOB_TIMEOUT_SECONDS="7200",
        AGENT_RUN_MAX_TRIES="3",
    )

    assert module.AGENT_RUN_JOB_TIMEOUT_SECONDS == 7200
    assert module.AGENT_RUN_MAX_TRIES == 3
    assert module.agent_run_runtime_secret_ttl_seconds() == 43_200


@pytest.mark.parametrize("name", ["AGENT_RUN_JOB_TIMEOUT_SECONDS", "AGENT_RUN_MAX_TRIES"])
@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_agent_run_execution_policy_rejects_non_positive_values(
    reload_execution_policy,
    name: str,
    value: str,
):
    with pytest.raises(ValueError, match=name):
        reload_execution_policy(**{name: value})
