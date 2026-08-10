from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
import yuxi.services.run_queue_service as run_queue_service
import yuxi.services.run_worker as run_worker
from yuxi.agents.backends.sandbox.runtime_context import (
    SandboxRuntimeCredentials,
    get_sandbox_runtime_credentials,
    register_sandbox_runtime_cleanup,
    sandbox_runtime_scope,
)
from yuxi.services.run_runtime_secret_service import BrowserCookieRuntimeSecret


def test_worker_settings_use_shared_execution_policy():
    assert run_worker.WorkerSettings.job_timeout == run_queue_service.AGENT_RUN_JOB_TIMEOUT_SECONDS
    assert run_worker.WorkerSettings.max_tries == run_queue_service.AGENT_RUN_MAX_TRIES


class _RaisingAsyncIter:
    def __init__(self, exc: Exception):
        self._exc = exc

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise self._exc


class _BytesAsyncIter:
    def __init__(self, values: list[bytes]):
        self._values = list(values)
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._values):
            raise StopAsyncIteration
        value = self._values[self._idx]
        self._idx += 1
        return value


def _build_run() -> SimpleNamespace:
    return SimpleNamespace(
        id="run-1",
        status="pending",
        request_id="req-1",
        input_payload={"model_spec": "provider:model"},
        input_message_id=10,
        run_type="chat",
        agent_slug="ChatbotAgent",
        uid="user-1",
        conversation_thread_id="thread-1",
        created_by_run_id=None,
    )


def _patch_common(monkeypatch: pytest.MonkeyPatch, run_obj: SimpleNamespace):
    @asynccontextmanager
    async def fake_session_ctx():
        yield object()

    async def fake_noop(*args, **kwargs):
        del args, kwargs
        return None

    async def fake_get_run(run_id: str):
        del run_id
        return run_obj

    async def fake_load_user(uid: str):
        del uid
        return SimpleNamespace(id=1, uid="user-1")

    async def fake_load_input_message(message_id: int | None):
        assert message_id == 10
        return SimpleNamespace(content="hello", image_content=None, extra_metadata={})

    async def fake_not_cancelled(self):
        del self
        return False

    async def fake_load_runtime_secret(run_id: str):
        del run_id
        return None

    async def fake_delete_runtime_secret(run_id: str):
        del run_id

    monkeypatch.setattr(run_worker.pg_manager, "get_async_session_context", fake_session_ctx)
    monkeypatch.setattr(run_worker, "_get_run", fake_get_run)
    monkeypatch.setattr(run_worker, "_load_user", fake_load_user)
    monkeypatch.setattr(run_worker, "_load_input_message", fake_load_input_message)
    monkeypatch.setattr(run_worker, "mark_run_running", fake_noop)
    monkeypatch.setattr(run_worker, "clear_cancel_signal", fake_noop)
    monkeypatch.setattr(run_worker, "stream_agent_chat", lambda **kwargs: object())
    monkeypatch.setattr(run_worker.RunContext, "start", fake_noop)
    monkeypatch.setattr(run_worker.RunContext, "close", fake_noop)
    monkeypatch.setattr(run_worker.RunContext, "is_cancelled", fake_not_cancelled)
    monkeypatch.setattr(run_worker, "load_run_browser_cookie_secret", fake_load_runtime_secret, raising=False)
    monkeypatch.setattr(run_worker, "delete_run_browser_cookie_secret", fake_delete_runtime_secret, raising=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("run_type", ["chat", "resume", "subagent"])
async def test_process_agent_run_exposes_loaded_runtime_credentials(
    monkeypatch: pytest.MonkeyPatch,
    run_type: str,
):
    run_obj = _build_run()
    run_obj.run_type = run_type
    if run_type == "subagent":
        run_obj.input_payload = {
            "model_spec": "provider:model",
            "runtime": {
                "parent_thread_id": "parent-thread",
                "file_thread_id": "shared-file-thread",
                "skills_thread_id": "thread-1",
            },
        }
    _patch_common(monkeypatch, run_obj)
    secret = BrowserCookieRuntimeSecret(header="sid=latest")
    captured = {}
    deleted = []

    async def fake_load_runtime_secret(run_id: str):
        assert run_id == "run-1"
        return secret

    async def fake_delete_runtime_secret(run_id: str):
        deleted.append(run_id)

    async def fake_load_input_message(message_id: int | None):
        assert message_id == 10
        metadata = {"resume": {"answer": "continue"}} if run_type == "resume" else {}
        return SimpleNamespace(content="hello", image_content=None, extra_metadata=metadata)

    async def fake_append_event(*args, **kwargs):
        del args, kwargs

    async def fake_mark_terminal(run_id: str, status: str, **kwargs):
        del run_id, kwargs
        run_obj.status = status

    def fake_stream(**kwargs):
        del kwargs
        captured["credentials"] = get_sandbox_runtime_credentials()
        return _BytesAsyncIter([b'{"status":"finished","request_id":"req-1","thread_id":"thread-1"}\n'])

    monkeypatch.setattr(run_worker, "load_run_browser_cookie_secret", fake_load_runtime_secret, raising=False)
    monkeypatch.setattr(run_worker, "delete_run_browser_cookie_secret", fake_delete_runtime_secret, raising=False)
    monkeypatch.setattr(run_worker, "_load_input_message", fake_load_input_message)
    monkeypatch.setattr(run_worker, "append_run_event", fake_append_event)
    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(run_worker, "stream_agent_chat", fake_stream)
    monkeypatch.setattr(run_worker, "stream_agent_resume", fake_stream)

    await run_worker.process_agent_run({"job_try": 1}, "run-1")

    assert captured["credentials"] == SandboxRuntimeCredentials(run_id="run-1", browser_cookie=secret)
    assert deleted == ["run-1"]
    assert get_sandbox_runtime_credentials() is None


@pytest.mark.asyncio
async def test_process_agent_run_retries_when_runtime_secret_load_fails(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)
    deleted = []

    async def failing_load(run_id: str):
        assert run_id == "run-1"
        raise ConnectionError("redis unavailable")

    async def fake_delete_runtime_secret(run_id: str):
        deleted.append(run_id)

    def fail_stream_agent_chat(**kwargs):
        del kwargs
        raise AssertionError("secret load failure must not start the agent")

    monkeypatch.setattr(run_worker, "load_run_browser_cookie_secret", failing_load)
    monkeypatch.setattr(run_worker, "delete_run_browser_cookie_secret", fake_delete_runtime_secret)
    monkeypatch.setattr(run_worker, "stream_agent_chat", fail_stream_agent_chat)

    with pytest.raises(run_worker.RetryableRunError, match="runtime secret load failed"):
        await run_worker.process_agent_run({"job_try": 1}, "run-1")

    assert run_obj.status == "pending"
    assert deleted == []


@pytest.mark.asyncio
async def test_process_agent_run_fails_terminally_when_runtime_secret_load_exhausts_retries(
    monkeypatch: pytest.MonkeyPatch,
):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)
    terminal_errors = []
    events = []
    deleted = []

    async def failing_load(run_id: str):
        assert run_id == "run-1"
        raise ConnectionError("redis unavailable")

    async def fake_mark_terminal(run_id: str, status: str, error_type=None, error_message=None):
        terminal_errors.append(
            {
                "run_id": run_id,
                "status": status,
                "error_type": error_type,
                "error_message": error_message,
            }
        )
        run_obj.status = status

    async def fake_append_event(run_id: str, event_type: str, payload: dict, **kwargs):
        events.append({"run_id": run_id, "event_type": event_type, "payload": payload, "kwargs": kwargs})

    async def fake_delete_runtime_secret(run_id: str):
        deleted.append(run_id)

    monkeypatch.setattr(run_worker, "load_run_browser_cookie_secret", failing_load)
    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(run_worker, "append_run_event", fake_append_event)
    monkeypatch.setattr(run_worker, "delete_run_browser_cookie_secret", fake_delete_runtime_secret)

    await run_worker.process_agent_run({"job_try": run_worker.WorkerSettings.max_tries}, "run-1")

    assert terminal_errors == [
        {
            "run_id": "run-1",
            "status": "failed",
            "error_type": "runtime_secret_load_failed",
            "error_message": "运行期 Cookie 凭据加载失败",
        }
    ]
    assert events == [
        {
            "run_id": "run-1",
            "event_type": "error",
            "payload": {
                "chunk": {
                    "status": "error",
                    "error_type": "runtime_secret_load_failed",
                    "error_message": "运行期 Cookie 凭据加载失败",
                    "retryable": False,
                },
                "retryable": False,
            },
            "kwargs": {"thread_id": None},
        },
        {
            "run_id": "run-1",
            "event_type": "end",
            "payload": {
                "status": "failed",
                "chunk": {
                    "status": "error",
                    "error_type": "runtime_secret_load_failed",
                    "error_message": "运行期 Cookie 凭据加载失败",
                    "retryable": False,
                },
            },
            "kwargs": {"thread_id": None},
        },
    ]
    assert deleted == ["run-1"]


@pytest.mark.asyncio
async def test_process_agent_run_keeps_terminal_failure_when_secret_error_event_write_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)
    terminal_statuses = []
    deleted = []

    async def failing_load(run_id: str):
        assert run_id == "run-1"
        raise ConnectionError("redis unavailable")

    async def fake_mark_terminal(run_id: str, status: str, **kwargs):
        del run_id, kwargs
        terminal_statuses.append(status)
        run_obj.status = status

    async def failing_append_event(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("event redis unavailable")

    async def fake_delete_runtime_secret(run_id: str):
        deleted.append(run_id)

    monkeypatch.setattr(run_worker, "load_run_browser_cookie_secret", failing_load)
    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(run_worker, "append_run_event", failing_append_event)
    monkeypatch.setattr(run_worker, "delete_run_browser_cookie_secret", fake_delete_runtime_secret)

    await run_worker.process_agent_run({"job_try": run_worker.WorkerSettings.max_tries}, "run-1")

    assert terminal_statuses == ["failed"]
    assert deleted == ["run-1"]


@pytest.mark.asyncio
async def test_sandbox_runtime_scope_runs_cleanup_on_error_and_cancellation():
    credentials = SandboxRuntimeCredentials(run_id="run-1", browser_cookie=None)
    cleaned = []

    with pytest.raises(ValueError, match="boom"):
        async with sandbox_runtime_scope(credentials):
            register_sandbox_runtime_cleanup("sandbox-1", lambda: cleaned.append("error"))
            raise ValueError("boom")

    with pytest.raises(asyncio.CancelledError):
        async with sandbox_runtime_scope(credentials):
            register_sandbox_runtime_cleanup("sandbox-1", lambda: cleaned.append("cancel"))
            raise asyncio.CancelledError

    assert cleaned == ["error", "cancel"]
    assert get_sandbox_runtime_credentials() is None


@pytest.mark.asyncio
async def test_process_agent_run_retry_exit_runs_cleanup_and_retains_secret(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)
    cleaned = []
    deleted = []

    async def fake_append_event(*args, **kwargs):
        del args, kwargs

    async def fake_delete_runtime_secret(run_id: str):
        deleted.append(run_id)

    def fake_stream_agent_chat(**kwargs):
        del kwargs
        register_sandbox_runtime_cleanup("sandbox-1", lambda: cleaned.append("retry"))
        return _RaisingAsyncIter(run_worker.RetryableRunError("temporary failure"))

    monkeypatch.setattr(run_worker, "append_run_event", fake_append_event)
    monkeypatch.setattr(run_worker, "stream_agent_chat", fake_stream_agent_chat)
    monkeypatch.setattr(run_worker, "delete_run_browser_cookie_secret", fake_delete_runtime_secret, raising=False)

    with pytest.raises(run_worker.RetryableRunError, match="temporary failure"):
        await run_worker.process_agent_run({"job_try": 1}, "run-1")

    assert cleaned == ["retry"]
    assert deleted == []


@pytest.mark.asyncio
async def test_terminal_secret_cleanup_failures_do_not_mask_worker_outcome(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)

    async def fake_append_event(*args, **kwargs):
        del args, kwargs

    async def fake_mark_terminal(run_id: str, status: str, **kwargs):
        del run_id, kwargs
        run_obj.status = status

    async def failing_delete(run_id: str):
        del run_id
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(run_worker, "append_run_event", fake_append_event)
    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(
        run_worker,
        "stream_agent_chat",
        lambda **kwargs: _BytesAsyncIter([b'{"status":"finished"}\n']),
    )
    monkeypatch.setattr(run_worker, "delete_run_browser_cookie_secret", failing_delete, raising=False)

    await run_worker.process_agent_run({"job_try": 1}, "run-1")


@pytest.mark.asyncio
async def test_terminal_state_lookup_failure_does_not_mask_retry_error(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)
    calls = 0

    async def flaky_get_run(run_id: str):
        nonlocal calls
        assert run_id == "run-1"
        calls += 1
        if calls == 1:
            return run_obj
        raise RuntimeError("database unavailable")

    async def fake_append_event(*args, **kwargs):
        del args, kwargs

    monkeypatch.setattr(run_worker, "_get_run", flaky_get_run)
    monkeypatch.setattr(run_worker, "append_run_event", fake_append_event)
    monkeypatch.setattr(
        run_worker,
        "stream_agent_chat",
        lambda **kwargs: _RaisingAsyncIter(run_worker.RetryableRunError("retry me")),
    )

    with pytest.raises(run_worker.RetryableRunError, match="retry me"):
        await run_worker.process_agent_run({"job_try": 1}, "run-1")


@pytest.mark.asyncio
async def test_process_agent_run_restores_invocation_meta(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)

    captured: dict[str, object] = {}
    events: list[dict] = []
    terminal_statuses: list[str] = []

    async def fake_load_input_message(message_id: int | None):
        assert message_id == 10
        return SimpleNamespace(
            content="hello",
            image_content=None,
            extra_metadata={
                "source": "agent_call",
                "agent_invocation_meta": {"trace_id": "trace-1"},
                "evaluation": {"dataset_name": "legacy-top-level"},
                "custom_variables": {"system_prompt": "legacy"},
            },
        )

    async def fake_append_event(run_id: str, event_type: str, payload: dict, **kwargs):
        del kwargs
        events.append({"run_id": run_id, "event_type": event_type, "payload": payload})

    async def fake_mark_terminal(run_id: str, status: str, error_type=None, error_message=None):
        del run_id, error_type, error_message
        terminal_statuses.append(status)

    def fake_stream_agent_chat(**kwargs):
        captured.update(kwargs)
        return _BytesAsyncIter([b'{"status":"finished","request_id":"req-1","thread_id":"thread-1"}\n'])

    monkeypatch.setattr(run_worker, "_load_input_message", fake_load_input_message)
    monkeypatch.setattr(run_worker, "append_run_event", fake_append_event)
    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(run_worker, "stream_agent_chat", fake_stream_agent_chat)

    await run_worker.process_agent_run({"job_try": 1}, "run-1")

    meta = captured["meta"]
    assert meta["source"] == "agent_call"
    assert meta["agent_invocation_meta"] == {"trace_id": "trace-1"}
    assert "evaluation" not in meta
    assert "custom_variables" not in meta
    metadata_event = next(event for event in events if event["event_type"] == "metadata")
    assert metadata_event["payload"]["agent_invocation_meta"] == {"trace_id": "trace-1"}
    assert "evaluation" not in metadata_event["payload"]
    assert "custom_variables" not in metadata_event["payload"]
    assert terminal_statuses == ["completed"]


@pytest.mark.asyncio
async def test_process_agent_run_non_retryable_error_marks_failed(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)

    terminal_statuses: list[str] = []
    events: list[str] = []

    async def fake_append_event(run_id: str, event_type: str, payload: dict, **kwargs):
        del run_id, payload, kwargs
        events.append(event_type)

    async def fake_mark_terminal(run_id: str, status: str, error_type=None, error_message=None):
        del run_id, error_type, error_message
        terminal_statuses.append(status)

    monkeypatch.setattr(run_worker, "append_run_event", fake_append_event)
    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(
        run_worker,
        "_consume_stream_with_cancel",
        lambda stream, run_ctx: _RaisingAsyncIter(RuntimeError("boom")),
    )

    await run_worker.process_agent_run({"job_try": 1}, "run-1")

    assert "error" in events
    assert terminal_statuses == ["failed"]


@pytest.mark.asyncio
async def test_process_agent_run_retryable_error_retries_then_completes(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)

    terminal_statuses: list[str] = []
    events: list[dict] = []
    attempts = {"count": 0}

    async def fake_append_event(run_id: str, event_type: str, payload: dict, **kwargs):
        del run_id, kwargs
        events.append({"event_type": event_type, "payload": payload})

    async def fake_mark_terminal(run_id: str, status: str, error_type=None, error_message=None):
        del run_id, error_type, error_message
        terminal_statuses.append(status)

    def fake_consume(stream, run_ctx):
        del stream, run_ctx
        attempts["count"] += 1
        if attempts["count"] == 1:
            return _RaisingAsyncIter(run_worker.RetryableRunError("temporary failure"))
        return _BytesAsyncIter([b'{"status":"finished","request_id":"req-1"}\n'])

    monkeypatch.setattr(run_worker, "append_run_event", fake_append_event)
    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(run_worker, "_consume_stream_with_cancel", fake_consume)

    with pytest.raises(run_worker.RetryableRunError):
        await run_worker.process_agent_run({"job_try": 1}, "run-1")

    assert terminal_statuses == []
    assert any(
        item["event_type"] == "error" and item["payload"]["chunk"].get("error_type") == "retryable_worker_error"
        for item in events
    )

    await run_worker.process_agent_run({"job_try": 2}, "run-1")
    assert terminal_statuses == ["completed"]


@pytest.mark.asyncio
async def test_process_subagent_run_restores_runtime_context(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    run_obj.run_type = "subagent"
    run_obj.agent_slug = "worker"
    run_obj.conversation_thread_id = "child-thread"
    run_obj.created_by_run_id = "parent-run"
    run_obj.input_payload = {
        "model_spec": "provider:model",
        "runtime": {
            "parent_thread_id": "parent-thread",
            "file_thread_id": "shared-file-thread",
            "skills_thread_id": "child-thread",
        },
    }
    _patch_common(monkeypatch, run_obj)

    captured: dict[str, object] = {}
    terminal_statuses: list[str] = []

    async def fake_append_event(run_id: str, event_type: str, payload: dict, **kwargs):
        del run_id, event_type, payload, kwargs

    async def fake_mark_terminal(run_id: str, status: str, error_type=None, error_message=None):
        del run_id, error_type, error_message
        terminal_statuses.append(status)

    def fake_stream_agent_chat(**kwargs):
        captured.update(kwargs)
        return _BytesAsyncIter([b'{"status":"finished","request_id":"req-1","thread_id":"child-thread"}\n'])

    monkeypatch.setattr(run_worker, "append_run_event", fake_append_event)
    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(run_worker, "stream_agent_chat", fake_stream_agent_chat)

    await run_worker.process_agent_run({"job_try": 1}, "run-1")

    meta = captured["meta"]
    assert meta["run_type"] == "subagent"
    assert meta["parent_thread_id"] == "parent-thread"
    assert meta["file_thread_id"] == "shared-file-thread"
    assert meta["skills_thread_id"] == "child-thread"
    assert captured["agent_slug"] == "worker"
    assert captured["thread_id"] == "child-thread"
    assert captured["input_message"].content == "hello"
    assert captured["input_message"].langchain_message.content == "hello"
    assert "image_content" not in captured
    assert terminal_statuses == ["completed"]


@pytest.mark.asyncio
async def test_process_agent_run_rejects_unknown_run_type(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    run_obj.run_type = "unknown"
    _patch_common(monkeypatch, run_obj)

    terminal_errors: list[dict] = []

    async def fake_mark_terminal(run_id: str, status: str, error_type=None, error_message=None):
        terminal_errors.append(
            {
                "run_id": run_id,
                "status": status,
                "error_type": error_type,
                "error_message": error_message,
            }
        )

    def fail_stream_agent_chat(**kwargs):
        del kwargs
        raise AssertionError("unknown run_type must not enter chat stream")

    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(run_worker, "stream_agent_chat", fail_stream_agent_chat)

    await run_worker.process_agent_run({"job_try": 1}, "run-1")

    assert terminal_errors == [
        {
            "run_id": "run-1",
            "status": "failed",
            "error_type": "invalid_run_type",
            "error_message": "不支持的 run_type: unknown",
        }
    ]


@pytest.mark.asyncio
async def test_process_agent_run_rejects_invalid_raw_input_message(monkeypatch: pytest.MonkeyPatch):
    run_obj = _build_run()
    _patch_common(monkeypatch, run_obj)

    terminal_errors: list[dict] = []

    async def fake_load_input_message(message_id: int | None):
        assert message_id == 10
        return SimpleNamespace(
            content="hello",
            image_content=None,
            extra_metadata={"raw_message": {"type": "human", "content": object()}},
        )

    async def fake_mark_terminal(run_id: str, status: str, error_type=None, error_message=None):
        terminal_errors.append(
            {
                "run_id": run_id,
                "status": status,
                "error_type": error_type,
                "error_message": error_message,
            }
        )

    def fail_stream_agent_chat(**kwargs):
        del kwargs
        raise AssertionError("invalid input message must not enter chat stream")

    monkeypatch.setattr(run_worker, "_load_input_message", fake_load_input_message)
    monkeypatch.setattr(run_worker, "mark_run_terminal", fake_mark_terminal)
    monkeypatch.setattr(run_worker, "stream_agent_chat", fail_stream_agent_chat)

    await run_worker.process_agent_run({"job_try": 1}, "run-1")

    assert terminal_errors == [
        {
            "run_id": "run-1",
            "status": "failed",
            "error_type": "invalid_input_message",
            "error_message": "invalid raw_message for chat input message",
        }
    ]


@pytest.mark.asyncio
async def test_chunked_event_writer_flushes_loading_chunks_by_thread(monkeypatch: pytest.MonkeyPatch):
    events: list[dict] = []

    async def fake_append_run_event(run_id: str, event_type: str, payload: dict, *, thread_id: str | None = None):
        events.append({"run_id": run_id, "event_type": event_type, "payload": payload, "thread_id": thread_id})

    monkeypatch.setattr(run_worker, "append_run_event", fake_append_run_event)

    writer = run_worker.ChunkedEventWriter("run-1", "parent-thread")
    await writer.append({"status": "loading", "response": "parent", "thread_id": "parent-thread"})
    await writer.append({"status": "loading", "response": "child", "thread_id": "child-thread"})
    await writer.flush()

    assert events == [
        {
            "run_id": "run-1",
            "event_type": "messages",
            "payload": {"items": [{"status": "loading", "response": "parent", "thread_id": "parent-thread"}]},
            "thread_id": "parent-thread",
        },
        {
            "run_id": "run-1",
            "event_type": "messages",
            "payload": {"items": [{"status": "loading", "response": "child", "thread_id": "child-thread"}]},
            "thread_id": "child-thread",
        },
    ]


@pytest.mark.asyncio
async def test_chunked_event_writer_flushes_semantic_tool_call_immediately(monkeypatch: pytest.MonkeyPatch):
    events: list[dict] = []

    async def fake_append_run_event(run_id: str, event_type: str, payload: dict, *, thread_id: str | None = None):
        events.append({"run_id": run_id, "event_type": event_type, "payload": payload, "thread_id": thread_id})

    monkeypatch.setattr(run_worker, "append_run_event", fake_append_run_event)

    writer = run_worker.ChunkedEventWriter("run-1", "parent-thread")
    chunk = {
        "status": "loading",
        "response": "",
        "thread_id": "parent-thread",
        "stream_event": {
            "type": "tool_call",
            "message_id": "msg-1",
            "tool_call_id": "call-1",
            "name": "task",
            "args": {"description": "do work"},
            "index": 0,
            "thread_id": "parent-thread",
            "namespace": [],
        },
    }
    await writer.append(chunk)

    assert events == [
        {
            "run_id": "run-1",
            "event_type": "messages",
            "payload": {"items": [chunk]},
            "thread_id": "parent-thread",
        }
    ]


def test_chunk_thread_id_uses_fallback_for_unstable_nested_metadata():
    assert (
        run_worker._chunk_thread_id(
            {"metadata": {"configurable": {"thread_id": "child-thread"}}},
            "parent-thread",
        )
        == "parent-thread"
    )


@pytest.mark.asyncio
async def test_worker_startup_ensures_builtin_mcp_servers(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def fake_initialize():
        calls.append("initialize")

    async def fake_create_business_tables():
        calls.append("create_business_tables")

    async def fake_ensure_business_schema():
        calls.append("ensure_business_schema")

    async def fake_ensure_builtin_mcp_servers_in_db():
        calls.append("ensure_builtin_mcp_servers_in_db")

    @asynccontextmanager
    async def fake_session_ctx():
        yield object()

    async def fake_init_builtin_skills(session):
        del session
        calls.append("init_builtin_skills")

    def fake_start_runtime_sync():
        calls.append("start_runtime_sync")

    monkeypatch.setattr(run_worker.pg_manager, "initialize", fake_initialize)
    monkeypatch.setattr(run_worker.pg_manager, "create_business_tables", fake_create_business_tables)
    monkeypatch.setattr(run_worker.pg_manager, "ensure_business_schema", fake_ensure_business_schema)
    monkeypatch.setattr(run_worker.pg_manager, "get_async_session_context", fake_session_ctx)
    monkeypatch.setattr(run_worker, "ensure_builtin_mcp_servers_in_db", fake_ensure_builtin_mcp_servers_in_db)
    monkeypatch.setattr(run_worker, "init_builtin_skills", fake_init_builtin_skills)
    monkeypatch.setattr(run_worker.sys_config, "start_runtime_sync", fake_start_runtime_sync)

    await run_worker._worker_startup({})

    assert calls == [
        "initialize",
        "create_business_tables",
        "ensure_business_schema",
        "ensure_builtin_mcp_servers_in_db",
        "init_builtin_skills",
        "start_runtime_sync",
    ]
