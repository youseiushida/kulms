from __future__ import annotations

from urllib.parse import quote

from kulms.models.assignment import Assignment
from kulms.resources.base import BaseResource
from kulms.timeutils import DateLike, is_date_in_range


class AssignmentsResource(BaseResource):
    def list(
        self,
        site_id: str | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: str | list[str] | None = None,
        from_date: DateLike = None,
        to_date: DateLike = None,
    ) -> list[Assignment]:
        path = "/direct/assignment/my" if site_id is None else f"/direct/assignment/site/{quote(site_id, safe='')}"
        data = self.direct.get_json(path, params=self._params(_limit=limit, _start=offset))
        assignments = [Assignment.model_validate(item) for item in self._items(data, "assignment_collection")]
        return [
            assignment
            for assignment in assignments
            if _status_matches(assignment.status, status)
            and is_date_in_range(
                assignment.due_time_string or assignment.due_time,
                from_date=from_date,
                to_date=to_date,
            )
        ]

    def get(self, assignment_id: str) -> Assignment:
        return Assignment.model_validate(self.direct.get_json(f"/direct/assignment/{quote(assignment_id, safe='')}"))


def _status_matches(value: str | None, status: str | list[str] | None) -> bool:
    if status is None:
        return True
    allowed = [status] if isinstance(status, str) else status
    normalized = {item.upper() for item in allowed}
    return (value or "").upper() in normalized
