from __future__ import annotations

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
