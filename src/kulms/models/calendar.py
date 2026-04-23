from __future__ import annotations

from pydantic import Field

from kulms.models.base import KULMSModel


class CalendarEvent(KULMSModel):
    event_id: str | None = Field(default=None, alias="eventId")
    title: str | None = None
    description: str | None = None
    site_id: str | None = Field(default=None, alias="siteId")
    site_name: str | None = Field(default=None, alias="siteName")
    first_time: object | None = Field(default=None, alias="firstTime")
    duration: int | None = None
    type: str | None = None
    reference: str | None = None

