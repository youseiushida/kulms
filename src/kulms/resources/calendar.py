from __future__ import annotations

from urllib.parse import quote

from kulms.models.calendar import CalendarEvent
from kulms.resources.base import BaseResource


class CalendarResource(BaseResource):
    def list(
        self,
        site_id: str | None = None,
        *,
        first_date: str | None = None,
        last_date: str | None = None,
    ) -> list[CalendarEvent]:
        path = "/direct/calendar/my" if site_id is None else f"/direct/calendar/site/{quote(site_id, safe='')}"
        data = self.direct.get_json(path, params=self._params(firstDate=first_date, lastDate=last_date))
        return [CalendarEvent.model_validate(item) for item in self._items(data, "calendar_collection")]

