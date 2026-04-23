from __future__ import annotations

from pydantic import Field

from kulms.models.base import KULMSModel


class Assignment(KULMSModel):
    id: str | None = None
    title: str | None = None
    context: str | None = None
    status: str | None = None
    instructions: str | None = None
    due_time: object | None = Field(default=None, alias="dueTime")
    due_time_string: str | None = Field(default=None, alias="dueTimeString")
    open_time: object | None = Field(default=None, alias="openTime")
    close_time: object | None = Field(default=None, alias="closeTime")
