from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from kulms.models import Announcement, Assignment, CalendarEvent
import kulms_cli.main as cli


runner = CliRunner()
HEAVY_TABLE_CHARS = set("┏┓┗┛┃┡┩╇")


def assert_no_heavy_table_border(output: str) -> None:
    assert not HEAVY_TABLE_CHARS.intersection(output)


class FakeCourse:
    id = "s1"
    title = "Course 1"
    entity_title = None
    type = "course"
    description = "desc"

    def model_dump(self, **_kwargs):
        return {"id": self.id, "title": self.title, "type": self.type}


class FakeTab:
    title = "Resources"
    tools = []

    def model_dump(self, **_kwargs):
        return {"title": self.title, "tools": []}


class FakeCourses:
    def list(self, **_kwargs):
        return [FakeCourse()]

    def get(self, site_id):
        course = FakeCourse()
        course.id = site_id
        return course

    def tabs(self, site_id):
        return [FakeTab()]


class FakeAssignments:
    def __init__(self):
        self.calls = []

    def list(self, course_id=None, **kwargs):
        self.calls.append((course_id, kwargs))
        if course_id is None and not kwargs:
            return [Assignment(id="a1", title="Assignment", context="s1", dueTimeString="2026-04-30T01:30:00Z")]
        return []


class FakeAnnouncements:
    def list(self, **_kwargs):
        return [Announcement(id="n1", title="Announcement", siteId="s1")]


class FakeCalendar:
    def list(self, **_kwargs):
        return [CalendarEvent(eventId="e1", title="Event", siteId="s1")]


class FakeClient:
    def __init__(self):
        self.courses = FakeCourses()
        self.assignments = FakeAssignments()
        self.announcements = FakeAnnouncements()
        self.calendar = FakeCalendar()


def test_display_path_uses_visible_relative_separator() -> None:
    assert cli._display_path(Path("KULMS") / "Course" / "file.pdf") == "./KULMS/Course/file.pdf"


def test_courses_command(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_client", lambda *args, **kwargs: FakeClient())

    result = runner.invoke(cli.app, ["courses"])

    assert result.exit_code == 0
    assert "Course 1" in result.output
    assert_no_heavy_table_border(result.output)


def test_course_tabs_command(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_client", lambda *args, **kwargs: FakeClient())

    result = runner.invoke(cli.app, ["course", "tabs", "s1"])

    assert result.exit_code == 0
    assert "Resources" in result.output
    assert_no_heavy_table_border(result.output)


def test_assignments_filters_are_passed(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(cli, "_client", lambda *args, **kwargs: fake)

    result = runner.invoke(
        cli.app,
        ["assignments", "s1", "--status", "OPEN", "--from", "2026-04-20", "--to", "2026-04-30"],
    )

    assert result.exit_code == 0
    assert_no_heavy_table_border(result.output)
    assert fake.assignments.calls == [
        ("s1", {"status": ["OPEN"], "from_date": "2026-04-20", "to_date": "2026-04-30"})
    ]


def test_dashboard_json_serializes_nested_models(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_client", lambda *args, **kwargs: FakeClient())

    result = runner.invoke(cli.app, ["dashboard", "--json"])

    assert result.exit_code == 0
    assert '"assignments"' in result.output
    assert '"title": "Assignment"' in result.output


def test_auth_profiles_lists_registered_and_cached_profiles(monkeypatch, tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    state_dir = tmp_path / "state"
    cache_dir.mkdir()
    state_dir.mkdir()
    monkeypatch.setattr(cli, "user_cache_dir", lambda _app: str(cache_dir))
    monkeypatch.setattr(cli, "user_state_dir", lambda _app: str(state_dir))
    (state_dir / "profiles.json").write_text(json.dumps(["main"], ensure_ascii=False), encoding="utf-8")
    (cache_dir / "legacy.cookies.json").write_text("[]", encoding="utf-8")

    secrets = {
        ("default", "username"): "default-user",
        ("default", "password"): "pw",
        ("main", "username"): "main-user",
        ("main", "password"): "pw",
        ("main", "totp_secret"): "totp",
        ("legacy", "username"): "legacy-user",
    }

    monkeypatch.setattr(
        cli,
        "_get_secret",
        lambda key, profile=None: secrets.get((profile or cli.state.profile, key)),
    )

    result = runner.invoke(cli.app, ["auth", "profiles"])

    assert result.exit_code == 0
    assert "default" in result.output
    assert "main" in result.output
    assert "legacy" in result.output
    assert "default-user" in result.output
    assert "main-user" in result.output
    assert "legacy-user" in result.output
    assert "stored" in result.output
    assert_no_heavy_table_border(result.output)


def test_auth_forget_removes_profile_from_registry(monkeypatch, tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    state_dir = tmp_path / "state"
    cache_dir.mkdir()
    state_dir.mkdir()
    monkeypatch.setattr(cli, "user_cache_dir", lambda _app: str(cache_dir))
    monkeypatch.setattr(cli, "user_state_dir", lambda _app: str(state_dir))
    (state_dir / "profiles.json").write_text(json.dumps(["main"], ensure_ascii=False), encoding="utf-8")
    (cache_dir / "main.cookies.json").write_text("[]", encoding="utf-8")

    secrets = {
        ("main", "username"): "main-user",
        ("main", "password"): "pw",
        ("main", "totp_secret"): "totp",
    }

    def fake_get_secret(key, *, profile=None):
        return secrets.get((profile or cli.state.profile, key))

    def fake_delete_secret(key, *, profile=None):
        secrets.pop((profile or cli.state.profile, key), None)

    monkeypatch.setattr(cli, "_get_secret", fake_get_secret)
    monkeypatch.setattr(cli, "_delete_secret", fake_delete_secret)

    result = runner.invoke(cli.app, ["--profile", "main", "auth", "forget"])

    assert result.exit_code == 0
    assert not (cache_dir / "main.cookies.json").exists()
    assert not (state_dir / "profiles.json").exists()


def test_profile_registry_migrates_legacy_cache_file_without_stripping(monkeypatch, tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    state_dir = tmp_path / "state"
    cache_dir.mkdir()
    state_dir.mkdir()
    monkeypatch.setattr(cli, "user_cache_dir", lambda _app: str(cache_dir))
    monkeypatch.setattr(cli, "user_state_dir", lambda _app: str(state_dir))
    (cache_dir / "profiles.json").write_text(json.dumps(["main "], ensure_ascii=False), encoding="utf-8")

    profiles = cli._load_registered_profiles()

    assert profiles == {"main "}
    assert not (cache_dir / "profiles.json").exists()
    assert json.loads((state_dir / "profiles.json").read_text(encoding="utf-8")) == ["main "]
