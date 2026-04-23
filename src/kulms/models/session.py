from __future__ import annotations

from pydantic import Field

from kulms.models.base import KULMSModel


class SessionInfo(KULMSModel):
    id: str | None = None
    active: bool | None = None
    user_id: str | None = Field(default=None, alias="userId")
    user_eid: str | None = Field(default=None, alias="userEid")
    creation_time: int | None = Field(default=None, alias="creationTime")
    current_time: int | None = Field(default=None, alias="currentTime")
    last_accessed_time: int | None = Field(default=None, alias="lastAccessedTime")
    max_inactive_interval: int | None = Field(default=None, alias="maxInactiveInterval")

