from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kuauth import KULMS as KuauthKULMS
from kuauth import KyotoUAuth

from kulms.direct import DirectClient
from kulms.resources import (
    AnnouncementsResource,
    AssignmentsResource,
    CalendarResource,
    CoursesResource,
    ResourcesResource,
    SessionsResource,
    UsersResource,
)
from kulms.session import SessionStore, export_cookies, import_cookies


class KULMSClient:
    def __init__(
        self,
        service: KuauthKULMS,
        *,
        session_store: SessionStore | None = None,
        load_session: bool = False,
        trust_loaded_session: bool = True,
    ) -> None:
        self._service = service
        self._session_store = session_store
        self.has_cached_session = False
        if session_store is not None and load_session:
            self.has_cached_session = import_cookies(self._service.http.cookies, session_store.load()) > 0
            if self.has_cached_session and trust_loaded_session:
                # kuauth only knows process-local login state. Cached cookies are
                # already the session, so avoid silently walking the SSO flow.
                self._service._sp_ready = True

        self.direct = DirectClient(service)
        self.courses = CoursesResource(self)
        self.resources = ResourcesResource(self)
        self.assignments = AssignmentsResource(self)
        self.announcements = AnnouncementsResource(self)
        self.calendar = CalendarResource(self)
        self.users = UsersResource(self)
        self.sessions = SessionsResource(self)

    @classmethod
    def from_auth(
        cls,
        auth: KyotoUAuth,
        *,
        session_store: SessionStore | None = None,
        load_session: bool = False,
        trust_loaded_session: bool = True,
    ) -> "KULMSClient":
        return cls(
            KuauthKULMS(auth),
            session_store=session_store,
            load_session=load_session,
            trust_loaded_session=trust_loaded_session,
        )

    @classmethod
    def from_credentials(
        cls,
        username: str,
        password: str,
        *,
        totp_secret: str | None = None,
        onetime_password: str | None = None,
        otp_callback: Callable[[], str] | None = None,
        timeout: float = 60.0,
        session_store: SessionStore | None = None,
        load_session: bool = False,
        trust_loaded_session: bool = True,
    ) -> "KULMSClient":
        auth = KyotoUAuth(
            username,
            password,
            totp_secret=totp_secret,
            onetime_password=onetime_password,
            otp_callback=otp_callback,
            timeout=timeout,
        )
        return cls.from_auth(
            auth,
            session_store=session_store,
            load_session=load_session,
            trust_loaded_session=trust_loaded_session,
        )

    @property
    def service(self) -> KuauthKULMS:
        return self._service

    def save_session(self) -> None:
        if self._session_store is None:
            return
        self._session_store.save(export_cookies(self._service.http.cookies))
        self.has_cached_session = True

    def clear_session(self) -> None:
        if self._session_store is not None:
            self._session_store.clear()
        self.has_cached_session = False

    def close(self) -> None:
        auth = getattr(self._service, "_auth", None)
        if auth is not None:
            auth.close()

    def __enter__(self) -> "KULMSClient":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()
