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
        "https://yuxi.example.com/api/",
    )

    assert secret == BrowserCookieRuntimeSecret(
        header="session=abc; theme=dark; session=path-specific",
        origin="https://yuxi.example.com",
    )


@pytest.mark.parametrize(
    ("base_url", "expected_origin"),
    [
        ("http://yuxi.example.com:80/api/", "http://yuxi.example.com"),
        ("https://yuxi.example.com:443/api/", "https://yuxi.example.com"),
        ("https://yuxi.example.com:8443/api/", "https://yuxi.example.com:8443"),
        ("http://[2001:db8::1]:8080/api/", "http://[2001:db8::1]:8080"),
    ],
)
def test_build_browser_cookie_secret_normalizes_http_origin(base_url: str, expected_origin: str):
    secret = agent_run_service.build_browser_cookie_runtime_secret("sid=abc", base_url)

    assert secret is not None
    assert secret.origin == expected_origin


def test_build_browser_cookie_secret_prefers_configured_public_origin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("YUXI_ENV", "production")
    monkeypatch.setenv("YUXI_PUBLIC_ORIGIN", "https://yuxi.example.com:443/app/")

    secret = agent_run_service.build_browser_cookie_runtime_secret(
        "sid=abc",
        "http://api:5050/api/",
    )

    assert secret is not None
    assert secret.origin == "https://yuxi.example.com"


def test_build_browser_cookie_secret_requires_public_origin_in_production(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("YUXI_ENV", "production")
    monkeypatch.delenv("YUXI_PUBLIC_ORIGIN", raising=False)

    with pytest.raises(ValueError, match="YUXI_PUBLIC_ORIGIN is required"):
        agent_run_service.build_browser_cookie_runtime_secret(
            "sid=abc",
            "http://api:5050/api/",
        )


def test_build_browser_cookie_secret_skips_empty_header():
    assert agent_run_service.build_browser_cookie_runtime_secret(None, "https://yuxi.example.com") is None
    assert agent_run_service.build_browser_cookie_runtime_secret("", "https://yuxi.example.com") is None


def test_build_browser_cookie_secret_rejects_header_over_32_kib():
    oversized = "a=" + "x" * 32_767

    assert agent_run_service.build_browser_cookie_runtime_secret(oversized, "https://yuxi.example.com") is None


def test_agent_run_router_passes_exact_cookie_header_and_request_origin(monkeypatch: pytest.MonkeyPatch):
    calls = {}

    async def fake_create_agent_run_view(**kwargs):
        calls["kwargs"] = kwargs
        return {"run_id": "run-1", "status": "pending", "request_id": "req-1"}

    monkeypatch.setattr(agent_router_module, "create_agent_run_view", fake_create_agent_run_view)
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
    assert calls["kwargs"]["browser_cookie"] == BrowserCookieRuntimeSecret(
        header="session=abc; theme=dark; session=path-specific",
        origin="http://testserver",
    )
