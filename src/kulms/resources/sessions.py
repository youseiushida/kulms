from __future__ import annotations

from kulms.models.session import SessionInfo
from kulms.resources.base import BaseResource


class SessionsResource(BaseResource):
    def current(self) -> SessionInfo:
        return SessionInfo.model_validate(self.direct.get_json("/direct/session/current"))

