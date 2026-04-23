from __future__ import annotations

from pydantic import Field

from kulms.models.base import KULMSModel


class User(KULMSModel):
    id: str | None = None
    eid: str | None = None
    display_id: str | None = Field(default=None, alias="displayId")
    display_name: str | None = Field(default=None, alias="displayName")
    email: str | None = None
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    type: str | None = None

