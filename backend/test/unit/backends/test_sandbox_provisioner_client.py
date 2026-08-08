from __future__ import annotations

from types import SimpleNamespace

import pytest

from yuxi.agents.backends.sandbox.provider import sandbox_provisioner_token
from yuxi.agents.backends.sandbox.provisioner_client import ProvisionerClient


def test_provisioner_client_sends_bearer_token(monkeypatch):
    calls = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status_code=200, json=lambda: {"sandboxes": [], "count": 0})

    monkeypatch.setattr("yuxi.agents.backends.sandbox.provisioner_client.httpx.request", fake_request)
    client = ProvisionerClient(
        "http://sandbox-provisioner:8002",
        token="test-provisioner-token-that-is-long-enough",
    )

    client.health()

    assert calls == [
        {
            "method": "GET",
            "url": "http://sandbox-provisioner:8002/health",
            "timeout": client._timeout,
            "headers": {"Authorization": "Bearer test-provisioner-token-that-is-long-enough"},
        }
    ]


def test_sandbox_provisioner_token_reads_environment(monkeypatch):
    monkeypatch.setenv("SANDBOX_PROVISIONER_TOKEN", "test-provisioner-token-that-is-long-enough")

    assert sandbox_provisioner_token() == "test-provisioner-token-that-is-long-enough"


def test_sandbox_provisioner_token_is_required(monkeypatch):
    monkeypatch.delenv("SANDBOX_PROVISIONER_TOKEN", raising=False)

    with pytest.raises(ValueError, match="at least 32 characters"):
        sandbox_provisioner_token()


def test_provisioner_client_parses_instance_id_for_create_and_discover(monkeypatch):
    responses = iter(
        [
            SimpleNamespace(
                status_code=200,
                json=lambda: {
                    "sandbox_id": "sandbox-1",
                    "sandbox_url": "http://sandbox/1",
                    "status": "Running",
                    "instance_id": "instance-create",
                },
            ),
            SimpleNamespace(
                status_code=200,
                json=lambda: {
                    "sandbox_id": "sandbox-1",
                    "sandbox_url": "http://sandbox/1",
                    "status": "Running",
                    "instance_id": "instance-discover",
                },
            ),
        ]
    )
    monkeypatch.setattr(
        "yuxi.agents.backends.sandbox.provisioner_client.httpx.request",
        lambda **kwargs: next(responses),
    )
    client = ProvisionerClient(
        "http://sandbox-provisioner:8002",
        token="test-provisioner-token-that-is-long-enough",
    )

    created = client.create("sandbox-1", "thread-1", "user-1")
    discovered = client.discover("sandbox-1")

    assert created.instance_id == "instance-create"
    assert discovered is not None
    assert discovered.instance_id == "instance-discover"
