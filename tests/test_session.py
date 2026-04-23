from __future__ import annotations

import json

import httpx

from kulms import KULMSClient
from kulms.session import JsonFileSessionStore, export_cookies, import_cookies


def test_cookie_roundtrip(tmp_path) -> None:
    cookies = httpx.Cookies()
    cookies.set("_shibsession_test", "value", domain="lms.gakusei.kyoto-u.ac.jp", path="/")
    next(cookie for cookie in cookies.jar if cookie.name == "_shibsession_test").secure = True

    records = export_cookies(cookies)
    store = JsonFileSessionStore(tmp_path / "cookies.json")
    store.save(records)

    assert json.loads((tmp_path / "cookies.json").read_text(encoding="utf-8"))[0]["name"] == "_shibsession_test"

    imported = httpx.Cookies()
    assert import_cookies(imported, store.load()) == 1
    assert imported.get("_shibsession_test") == "value"
    assert next(cookie for cookie in imported.jar if cookie.name == "_shibsession_test").secure is True


class FakeService:
    def __init__(self) -> None:
        self.http = type("HTTP", (), {"cookies": httpx.Cookies()})()
        self._sp_ready = False


def test_client_trusts_loaded_session_without_reauth(tmp_path) -> None:
    store = JsonFileSessionStore(tmp_path / "cookies.json")
    store.save(
        [
            {
                "name": "_shibsession_test",
                "value": "value",
                "domain": "lms.gakusei.kyoto-u.ac.jp",
                "path": "/",
                "expires": None,
                "secure": True,
            }
        ]
    )
    service = FakeService()

    client = KULMSClient(service, session_store=store, load_session=True)

    assert client.has_cached_session is True
    assert service._sp_ready is True
    assert service.http.cookies.get("_shibsession_test") == "value"
