from __future__ import annotations

import pytest

from src.services import skill_resolver as resolver
from src.storage.postgres.models_business import Skill


def test_expand_skill_closure_and_dependency_bundle():
    dependency_map = {
        "alpha": {"tools": ["t1"], "mcps": ["m1"], "skills": ["beta"]},
        "beta": {"tools": ["t2"], "mcps": ["m2"], "skills": ["gamma"]},
        "gamma": {"tools": ["t3"], "mcps": [], "skills": []},
    }
    snapshot: resolver.SkillSessionSnapshot = {
        "selected_skills": ["alpha"],
        "visible_skills": ["alpha", "beta", "gamma"],
        "prompt_metadata": {},
        "dependency_map": dependency_map,
    }

    closure = resolver.expand_skill_closure(["alpha"], dependency_map)
    assert closure == ["alpha", "beta", "gamma"]

    bundle = resolver.build_dependency_bundle(snapshot, ["alpha"])
    assert bundle["skills"] == ["alpha", "beta", "gamma"]
    assert bundle["tools"] == ["t1", "t2", "t3"]
    assert bundle["mcps"] == ["m1", "m2"]


def test_expand_skill_closure_cycle():
    dependency_map = {
        "alpha": {"tools": [], "mcps": [], "skills": ["beta"]},
        "beta": {"tools": [], "mcps": [], "skills": ["alpha"]},
    }
    assert resolver.expand_skill_closure(["alpha"], dependency_map) == ["alpha", "beta"]


def test_collect_prompt_metadata_order_and_dedup():
    snapshot: resolver.SkillSessionSnapshot = {
        "selected_skills": ["beta", "alpha"],
        "visible_skills": ["beta", "alpha"],
        "prompt_metadata": {
            "beta": {"name": "beta", "description": "beta skill", "path": "/skills/beta/SKILL.md"},
            "alpha": {"name": "alpha", "description": "alpha skill", "path": "/skills/alpha/SKILL.md"},
        },
        "dependency_map": {},
    }
    result = resolver.collect_prompt_metadata(snapshot, ["beta", "missing", "alpha", "beta"])
    assert [item["name"] for item in result] == ["beta", "alpha"]
    assert [item["path"] for item in result] == ["/skills/beta/SKILL.md", "/skills/alpha/SKILL.md"]


@pytest.mark.asyncio
async def test_resolve_session_snapshot_and_selected_change(monkeypatch: pytest.MonkeyPatch):
    async def fake_list_skills(_db=None):
        return [
            Skill(
                slug="alpha",
                name="alpha",
                description="a",
                tool_dependencies=[],
                mcp_dependencies=[],
                skill_dependencies=["beta"],
                dir_path="skills/alpha",
            ),
            Skill(
                slug="beta",
                name="beta",
                description="b",
                tool_dependencies=[],
                mcp_dependencies=[],
                skill_dependencies=[],
                dir_path="skills/beta",
            ),
        ]

    monkeypatch.setattr(resolver, "_list_skills_from_db", fake_list_skills)

    snapshot = await resolver.resolve_session_snapshot([" alpha ", "alpha"])
    assert snapshot["selected_skills"] == ["alpha"]
    assert snapshot["visible_skills"] == ["alpha", "beta"]

    assert resolver.is_snapshot_match_selected_skills(snapshot, ["alpha"]) is True
    assert resolver.is_snapshot_match_selected_skills(snapshot, ["beta"]) is False
