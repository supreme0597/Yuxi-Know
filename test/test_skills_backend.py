from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.agents.common.backends import skills_backend


def _prepare_skills_dir(root: Path) -> None:
    (root / "alpha").mkdir(parents=True, exist_ok=True)
    (root / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: alpha\n---\n# alpha\n",
        encoding="utf-8",
    )
    (root / "beta").mkdir(parents=True, exist_ok=True)
    (root / "beta" / "SKILL.md").write_text(
        "---\nname: beta\ndescription: beta\n---\n# beta\n",
        encoding="utf-8",
    )


def test_selected_skills_backend_readonly_and_visible_only_selected(tmp_path, monkeypatch):
    _prepare_skills_dir(tmp_path)
    monkeypatch.setattr(skills_backend, "get_skills_root_dir", lambda: tmp_path)

    backend = skills_backend.SelectedSkillsReadonlyBackend(selected_slugs=["alpha"])

    root_entries = backend.ls_info("/")
    paths = sorted(entry.get("path") for entry in root_entries)
    assert paths == ["/alpha/"]

    ok_read = backend.read("/alpha/SKILL.md")
    assert "alpha" in ok_read

    denied_read = backend.read("/beta/SKILL.md")
    assert "Access denied" in denied_read

    write_result = backend.write("/alpha/new.md", "x")
    assert write_result.error and "read-only" in write_result.error

    edit_result = backend.edit("/alpha/SKILL.md", "alpha", "changed")
    assert edit_result.error and "read-only" in edit_result.error

    upload_result = backend.upload_files([("/alpha/a.txt", b"a")])
    assert len(upload_result) == 1
    assert upload_result[0].error == "permission_denied"


def test_composite_backend_mounts_skills_under_prefix(tmp_path, monkeypatch):
    _prepare_skills_dir(tmp_path)
    monkeypatch.setattr(skills_backend, "get_skills_root_dir", lambda: tmp_path)

    runtime = SimpleNamespace(
        context=SimpleNamespace(
            skills=["alpha"],
            skill_session_snapshot={
                "selected_skills": ["alpha"],
                "visible_skills": ["alpha", "beta"],
                "prompt_metadata": {},
                "dependency_map": {},
            },
        ),
        state={},
    )
    composite = skills_backend.create_agent_composite_backend(runtime)

    root = composite.ls_info("/")
    all_paths = [entry.get("path") for entry in root]
    assert "/skills/" in all_paths

    skills_root = composite.ls_info("/skills/")
    skill_paths = sorted(entry.get("path") for entry in skills_root)
    assert skill_paths == ["/skills/alpha/", "/skills/beta/"]

    denied = composite.write("/skills/alpha/new.md", "x")
    assert denied.error and "read-only" in denied.error


def test_composite_backend_fallbacks_to_context_skills_when_snapshot_missing(tmp_path, monkeypatch):
    _prepare_skills_dir(tmp_path)
    monkeypatch.setattr(skills_backend, "get_skills_root_dir", lambda: tmp_path)

    runtime = SimpleNamespace(
        context=SimpleNamespace(skills=["alpha"]),
        state={},
    )
    composite = skills_backend.create_agent_composite_backend(runtime)
    skills_root = composite.ls_info("/skills/")
    skill_paths = sorted(entry.get("path") for entry in skills_root)
    assert skill_paths == ["/skills/alpha/"]


def test_composite_backend_reads_visible_skills_from_runtime_context(tmp_path, monkeypatch):
    _prepare_skills_dir(tmp_path)
    monkeypatch.setattr(skills_backend, "get_skills_root_dir", lambda: tmp_path)

    runtime = SimpleNamespace(
        context=SimpleNamespace(
            skills=["alpha"],
            skill_session_snapshot={
                "selected_skills": ["alpha"],
                "visible_skills": ["alpha", "beta"],
                "prompt_metadata": {},
                "dependency_map": {},
            },
        ),
        state=None,
    )
    composite = skills_backend.create_agent_composite_backend(runtime)
    skills_root = composite.ls_info("/skills/")
    skill_paths = sorted(entry.get("path") for entry in skills_root)
    assert skill_paths == ["/skills/alpha/", "/skills/beta/"]
