from __future__ import annotations

import json
import uuid

import pytest

from yuxi.agents.backends.sandbox.backend import ProvisionerSandboxBackend
from yuxi.agents.backends.sandbox.runtime_context import (
    SANDBOX_COOKIE_HEADER_FILE,
    SandboxRuntimeCredentials,
    sandbox_runtime_scope,
)
from yuxi.services.run_runtime_secret_service import BrowserCookieRuntimeSecret


def _shell(client, command: str) -> tuple[int | None, str]:
    result = client.shell.exec_command(command=command, timeout=10)
    return result.data.exit_code, (result.data.output or "").strip()


def _connection(backend: ProvisionerSandboxBackend):
    connection = backend._provider.get(
        backend._thread_id,
        uid=backend._uid,
        create_if_missing=False,
        file_thread_id=backend._file_thread_id,
        skills_thread_id=backend._skills_thread_id,
    )
    assert connection is not None
    return connection


@pytest.mark.integration
@pytest.mark.asyncio
async def test_runtime_cookie_header_file_reinjects_after_sandbox_recreate():
    suffix = uuid.uuid4().hex[:12]
    thread_id = f"cookie-thread-{suffix}"
    uid = f"cookie-user-{suffix}"
    cookie_header = "session=cookie-integration-marker; theme=dark; session=path-specific"
    secret = BrowserCookieRuntimeSecret(header=cookie_header)
    backend = ProvisionerSandboxBackend(thread_id=thread_id, uid=uid)
    client = None

    try:
        async with sandbox_runtime_scope(SandboxRuntimeCredentials("run-a", secret)):
            client = backend._get_client()
            assert _shell(client, f"cat {SANDBOX_COOKIE_HEADER_FILE}") == (0, cookie_header)
            assert _shell(client, f"stat -c %a {SANDBOX_COOKIE_HEADER_FILE}") == (0, "600")
            assert _shell(client, f"stat -c %a {SANDBOX_COOKIE_HEADER_FILE.rsplit('/', 1)[0]}") == (0, "700")
            with pytest.raises(json.JSONDecodeError):
                json.loads(cookie_header)

            first_connection = _connection(backend)
            backend._provider._client.delete(backend.id)
            backend._provider._last_touch_at[first_connection.cache_key] = 0

            client = backend._get_client()
            second_connection = _connection(backend)
            assert second_connection.instance_id != first_connection.instance_id
            assert _shell(client, f"cat {SANDBOX_COOKIE_HEADER_FILE}") == (0, cookie_header)

        assert client is not None
        assert _shell(client, f"test -e {SANDBOX_COOKIE_HEADER_FILE}")[0] == 1

        stale_write = client.file.write_file(file=SANDBOX_COOKIE_HEADER_FILE, content="stale-cookie-marker")
        assert stale_write.success
        async with sandbox_runtime_scope(SandboxRuntimeCredentials("run-b", None)):
            backend._get_client()
            assert _shell(client, f"test -e {SANDBOX_COOKIE_HEADER_FILE}")[0] == 1
    finally:
        backend._provider._client.delete(backend.id)
