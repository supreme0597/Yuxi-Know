from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from yuxi.services.run_runtime_secret_service import BrowserCookieRuntimeSecret
from yuxi.utils.logging_config import logger

SANDBOX_COOKIE_HEADER_FILE = "/home/gem/.yuxi-runtime/browser-cookie-header.txt"


@dataclass(frozen=True, slots=True)
class SandboxRuntimeCredentials:
    run_id: str
    browser_cookie: BrowserCookieRuntimeSecret | None


_credentials_var = ContextVar[SandboxRuntimeCredentials | None](
    "sandbox_runtime_credentials",
    default=None,
)
_cleanup_callbacks_var = ContextVar[dict[str, Callable[[], None]] | None](
    "sandbox_runtime_cleanup_callbacks",
    default=None,
)


def get_sandbox_runtime_credentials() -> SandboxRuntimeCredentials | None:
    return _credentials_var.get()


def register_sandbox_runtime_cleanup(key: str, callback: Callable[[], None]) -> None:
    callbacks = _cleanup_callbacks_var.get()
    if callbacks is not None:
        callbacks.setdefault(key, callback)


@asynccontextmanager
async def sandbox_runtime_scope(credentials: SandboxRuntimeCredentials) -> AsyncIterator[None]:
    credentials_token = _credentials_var.set(credentials)
    callbacks_token = _cleanup_callbacks_var.set({})
    try:
        yield
    finally:
        for callback in tuple((_cleanup_callbacks_var.get() or {}).values()):
            try:
                await asyncio.to_thread(callback)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed to clean sandbox runtime credential file: {exc}")
        _cleanup_callbacks_var.reset(callbacks_token)
        _credentials_var.reset(credentials_token)
