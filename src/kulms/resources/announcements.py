from __future__ import annotations

from urllib.parse import quote

from kulms.models.announcement import Announcement
from kulms.resources.base import BaseResource
from kulms.timeutils import DateLike, is_date_in_range


class AnnouncementsResource(BaseResource):
    def list(
        self,
        site_id: str | None = None,
        *,
        days: int | None = None,
        limit: int | None = None,
        from_date: DateLike = None,
        to_date: DateLike = None,
    ) -> list[Announcement]:
        path = "/direct/announcement/user" if site_id is None else f"/direct/announcement/site/{quote(site_id, safe='')}"
        data = self.direct.get_json(path, params=self._params(d=days, n=limit))
        announcements = [Announcement.model_validate(item) for item in self._items(data, "announcement_collection")]
        return [
            announcement
            for announcement in announcements
            if is_date_in_range(announcement.created_on, from_date=from_date, to_date=to_date)
        ]

    def motd(self, *, days: int | None = None, limit: int | None = None) -> list[Announcement]:
        data = self.direct.get_json("/direct/announcement/motd", params=self._params(d=days, n=limit))
        return [Announcement.model_validate(item) for item in self._items(data, "announcement_collection")]
