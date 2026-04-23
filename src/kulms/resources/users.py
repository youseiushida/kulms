from __future__ import annotations

from kulms.models.user import User
from kulms.resources.base import BaseResource


class UsersResource(BaseResource):
    def current(self) -> User:
        return User.model_validate(self.direct.get_json("/direct/user/current"))

