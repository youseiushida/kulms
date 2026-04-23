from __future__ import annotations

from pydantic import Field

from kulms.models.base import KULMSModel


class Announcement(KULMSModel):
    id: str | None = None
    announcement_id: str | None = Field(default=None, alias="announcementId")
    title: str | None = None
    body: str | None = None
    site_id: str | None = Field(default=None, alias="siteId")
    site_title: str | None = Field(default=None, alias="siteTitle")
    created_on: object | None = Field(default=None, alias="createdOn")
    created_by_display_name: str | None = Field(default=None, alias="createdByDisplayName")
