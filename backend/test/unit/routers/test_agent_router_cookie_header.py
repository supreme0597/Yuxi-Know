from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.services import agent_run_service
from yuxi.services.run_runtime_secret_service import BrowserCookieRuntimeSecret

agent_router_module = importlib.import_module("server.routers.agent_router")


def _build_app() -> TestClient:
    app = FastAPI()
    app.include_router(agent_router_module.agent_router, prefix="/api")

    async def fake_db():
        return object()

    async def fake_user():
        return SimpleNamespace(uid="user-1", role="user", department_id=1)

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_required_user] = fake_user
    return TestClient(app)


def test_build_browser_cookie_secret_preserves_raw_header():
    secret = agent_run_service.build_browser_cookie_runtime_secret(
        "session=abc; theme=dark; session=path-specific",
    )

    assert secret == BrowserCookieRuntimeSecret(
        header="session=abc; theme=dark; session=path-specific",
    )


def test_build_browser_cookie_secret_skips_empty_header():
    assert agent_run_service.build_browser_cookie_runtime_secret(None) is None
    assert agent_run_service.build_browser_cookie_runtime_secret("") is None


def test_build_browser_cookie_secret_rejects_header_over_32_kib():
    oversized = "a=" + "x" * 32_767

    assert agent_run_service.build_browser_cookie_runtime_secret(oversized) is None


def test_agent_run_router_passes_exact_cookie_header(monkeypatch: pytest.MonkeyPatch):
    calls = {}
    builder_calls = []

    async def fake_create_agent_run_view(**kwargs):
        calls["kwargs"] = kwargs
        return {"run_id": "run-1", "status": "pending", "request_id": "req-1"}

    def fake_build_browser_cookie_runtime_secret(cookie_header):
        builder_calls.append(cookie_header)
        return BrowserCookieRuntimeSecret(header=cookie_header)

    monkeypatch.setattr(agent_router_module, "create_agent_run_view", fake_create_agent_run_view)
    monkeypatch.setattr(
        agent_router_module,
        "build_browser_cookie_runtime_secret",
        fake_build_browser_cookie_runtime_secret,
    )
    client = _build_app()

    response = client.post(
        "/api/agent/runs",
        headers={"Cookie": "session=abc; theme=dark; session=path-specific"},
        json={
            "query": "Hello",
            "agent_slug": "default",
            "thread_id": "thread-1",
            "meta": {"request_id": "req-1"},
        },
    )

    assert response.status_code == 200, response.text
    assert builder_calls == ["session=abc; theme=dark; session=path-specific"]
    assert calls["kwargs"]["browser_cookie"] == BrowserCookieRuntimeSecret(
        header="session=abc; theme=dark; session=path-specific",
    )
