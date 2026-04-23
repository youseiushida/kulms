from __future__ import annotations

from urllib.parse import quote

from kulms.exceptions import NotFoundError
from kulms.models.course import Course, CourseTab
from kulms.resources.base import BaseResource


class CoursesResource(BaseResource):
    def list(self, *, limit: int | None = 100, offset: int | None = 0) -> list[Course]:
        data = self.direct.get_json(
            "/direct/site",
            params=self._params(_limit=limit, _start=offset),
        )
        return [Course.model_validate(item) for item in self._items(data, "site_collection")]

    def iter(self, *, page_size: int = 100):
        offset = 0
        while True:
            page = self.list(limit=page_size, offset=offset)
            if not page:
                return
            yield from page
            if len(page) < page_size:
                return
            offset += page_size

    def get(self, site_id: str, *, include_groups: bool = False) -> Course:
        data = self.direct.get_json(
            f"/direct/site/{quote(site_id, safe='')}",
            params=self._params(includeGroups=str(include_groups).lower() if include_groups else None),
        )
        return Course.model_validate(data)

    def tabs(self, site_id: str, *, props: bool = False, config: bool = False) -> list[CourseTab]:
        data = self.direct.get_json(
            f"/direct/site/{quote(site_id, safe='')}/pages",
            params=self._params(
                props=str(props).lower() if props else None,
                config=str(config).lower() if config else None,
            ),
        )
        return [CourseTab.model_validate(item) for item in self._items(data)]

    def exists(self, site_id: str) -> bool:
        try:
            response = self.direct.request("GET", f"/direct/site/{quote(site_id, safe='')}/exists")
            return response.status_code < 400
        except NotFoundError:
            return False

