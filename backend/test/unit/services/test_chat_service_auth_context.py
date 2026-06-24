from __future__ import annotations

import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from yuxi.services.chat_service import _build_agent_input_context

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


async def test_build_agent_input_context_overwrites_user_owned_auth_fields():
    input_context = await _build_agent_input_context(
        {
            "user_id": "client-user",
            "work_id": "client-work",
            "department_id": "client-department",
            "thread_id": "client-thread",
        },
        thread_id="thread-1",
        user_id="42",
        work_id="W-7",
        department_id=9,
    )

    assert input_context["user_id"] == "42"
    assert input_context["work_id"] == "W-7"
    assert input_context["department_id"] == "9"
    assert input_context["thread_id"] == "thread-1"
