from __future__ import annotations

from contextlib import contextmanager

from kulms.resources.announcements import AnnouncementsResource
from kulms.resources.assignments import AssignmentsResource
from kulms.resources.calendar import CalendarResource
from kulms.resources.courses import CoursesResource
from kulms.resources.resources import ResourcesResource


class FakeDirect:
    def __init__(self):
        self.calls = []
        self.stream_calls = []

    def get_json(self, path, *, params=None, ensure_json_suffix=True):
        self.calls.append((path, params, ensure_json_suffix))
        if path.startswith("/direct/site/") and path.endswith("/pages"):
            return [{"title": "テスト・クイズ", "tools": [{"toolId": "sakai.samigo"}]}]
        if path == "/direct/site":
            return {"site_collection": [{"id": "s1", "title": "Course"}]}
        if path.startswith("/direct/assignment"):
            return {
                "assignment_collection": [
                    {"id": "a1", "title": "Open Assignment", "status": "OPEN", "dueTimeString": "2026-04-30T01:30:00Z"},
                    {"id": "a2", "title": "Closed Assignment", "status": "CLOSED", "dueTimeString": "2026-04-10T01:30:00Z"},
                ]
            }
        if path.startswith("/direct/announcement"):
            return {
                "announcement_collection": [
                    {"id": "n1", "title": "Recent Announcement", "createdOn": 1776743620543},
                    {"id": "n2", "title": "Old Announcement", "createdOn": 1700000000000},
                ]
            }
        if path.startswith("/direct/calendar"):
            return {"calendar_collection": [{"eventId": "e1", "title": "Event"}]}
        if path.startswith("/direct/content"):
            return {
                "content_collection": [
                    {
                        "title": "folder",
                        "type": "collection",
                        "url": "https://lms.gakusei.kyoto-u.ac.jp/access/content/group/s1/folder/",
                    },
                    {
                        "title": "file.pdf",
                        "type": "application/pdf",
                        "container": "/content/group/s1/folder/",
                        "url": "https://lms.gakusei.kyoto-u.ac.jp/access/content/group/s1/folder/file.pdf",
                    },
                ]
            }
        return {}

    @contextmanager
    def stream(self, method, path, **kwargs):
        self.stream_calls.append((method, path, kwargs))
        yield FakeStreamResponse()


class FakeStreamResponse:
    status_code = 200
    headers = {"content-length": "7"}

    def iter_bytes(self):
        yield b"content"


class FakeClient:
    def __init__(self):
        self.direct = FakeDirect()
        self.courses = type(
            "Courses",
            (),
            {"get": lambda _self, site_id: type("Course", (), {"title": "Course", "id": site_id})()},
        )()


def test_courses_list_uses_sakai_paging_params() -> None:
    client = FakeClient()
    result = CoursesResource(client).list(limit=50, offset=100)

    assert result[0].id == "s1"
    assert client.direct.calls[0] == ("/direct/site", {"_limit": 50, "_start": 100}, True)


def test_courses_tabs_parses_tools() -> None:
    client = FakeClient()
    result = CoursesResource(client).tabs("site id")

    assert result[0].title == "テスト・クイズ"
    assert result[0].tools[0].tool_id == "sakai.samigo"


def test_assignments_global_and_site_paths() -> None:
    client = FakeClient()
    AssignmentsResource(client).list()
    AssignmentsResource(client).list("site id")

    assert client.direct.calls[0][0] == "/direct/assignment/my"
    assert client.direct.calls[1][0] == "/direct/assignment/site/site%20id"


def test_assignments_filter_by_status_and_due_date() -> None:
    client = FakeClient()

    result = AssignmentsResource(client).list(status=["OPEN"], from_date="2026-04-20", to_date="2026-04-30")

    assert [item.title for item in result] == ["Open Assignment"]


def test_announcements_params() -> None:
    client = FakeClient()
    AnnouncementsResource(client).list("s1", days=7, limit=20)

    assert client.direct.calls[0] == ("/direct/announcement/site/s1", {"d": 7, "n": 20}, True)


def test_announcements_filter_by_created_date() -> None:
    client = FakeClient()

    result = AnnouncementsResource(client).list(from_date="2026-04-01", to_date="2026-04-30")

    assert [item.title for item in result] == ["Recent Announcement"]


def test_calendar_global_and_site_paths() -> None:
    client = FakeClient()
    CalendarResource(client).list(first_date="2026-04-01", last_date="2026-04-30")
    CalendarResource(client).list("s1")

    assert client.direct.calls[0][0] == "/direct/calendar/my"
    assert client.direct.calls[0][1] == {"firstDate": "2026-04-01", "lastDate": "2026-04-30"}
    assert client.direct.calls[1][0] == "/direct/calendar/site/s1"


def test_resources_download_skips_collections_and_preserves_folder(tmp_path) -> None:
    client = FakeClient()
    results = ResourcesResource(client).download("s1", dest=tmp_path, dry_run=True)

    assert len(results) == 1
    assert results[0].status == "planned"
    assert str(results[0].path).endswith("Course\\folder\\file.pdf") or str(results[0].path).endswith("Course/folder/file.pdf")


def test_resources_download_streams_allowed_url(tmp_path) -> None:
    client = FakeClient()

    results = ResourcesResource(client).download("s1", dest=tmp_path)

    assert results[0].status == "downloaded"
    assert results[0].bytes == 7
    assert results[0].path.read_bytes() == b"content"
    assert client.direct.stream_calls == [
        ("GET", "https://lms.gakusei.kyoto-u.ac.jp/access/content/group/s1/folder/file.pdf", {})
    ]


def test_resources_download_skips_external_url_by_default(tmp_path) -> None:
    client = FakeClient()
    client.direct.get_json = lambda *_args, **_kwargs: {
        "content_collection": [
            {
                "title": "external.pdf",
                "type": "application/pdf",
                "url": "https://example.test/external.pdf",
            }
        ]
    }

    results = ResourcesResource(client).download("s1", dest=tmp_path)

    assert results[0].status == "skipped"
    assert results[0].message == "external URL skipped"
    assert client.direct.stream_calls == []
