from __future__ import annotations

import httpx
import pytest

from kulms.direct import DirectClient
from kulms.exceptions import APIError, AuthExpiredError, NotFoundError


class FakeService:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.calls = []

    def request(self, method: str, path: str, **kwargs):
        self.calls.append((method, path, kwargs))
        return self.response


def response(status: int = 200, json_data=None, *, content_type: str = "application/json") -> httpx.Response:
    request = httpx.Request("GET", "https://lms.gakusei.kyoto-u.ac.jp/direct/site.json")
    if json_data is not None:
        return httpx.Response(status, json=json_data, headers={"content-type": content_type}, request=request)
    return httpx.Response(status, text="body", headers={"content-type": content_type}, request=request)


def test_get_json_normalizes_direct_path() -> None:
    service = FakeService(response(json_data={"ok": True}))
    client = DirectClient(service)

    assert client.get_json("site") == {"ok": True}
    assert service.calls[0][1] == "/direct/site.json"


def test_get_json_preserves_access_path_for_downloads() -> None:
    service = FakeService(response(json_data={"ok": True}))
    client = DirectClient(service)

    client.request("GET", "/access/content/site/file.pdf")
    assert service.calls[0][1] == "/access/content/site/file.pdf"


def test_get_json_rejects_non_json() -> None:
    client = DirectClient(FakeService(response(content_type="text/html")))

    with pytest.raises(APIError):
        client.get_json("/direct/site")


def test_not_found_maps_to_not_found_error() -> None:
    client = DirectClient(FakeService(response(404, json_data={"error": "no"})))

    with pytest.raises(NotFoundError):
        client.get_json("/direct/site/nope")


def test_auth_redirect_maps_to_auth_expired() -> None:
    request = httpx.Request("GET", "https://auth.iimc.kyoto-u.ac.jp/login.cgi")
    auth_response = httpx.Response(200, text="<html>login.cgi</html>", headers={"content-type": "text/html"}, request=request)
    client = DirectClient(FakeService(auth_response))

    with pytest.raises(AuthExpiredError):
        client.request("GET", "/direct/site.json")

