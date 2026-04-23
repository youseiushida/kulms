from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from kulms.exceptions import APIError, AuthExpiredError, NotFoundError


class DirectClient:
    """Low-level client for Sakai Direct API paths."""

    AUTH_HOST_MARKERS = ("auth.iimc.kyoto-u.ac.jp", "authidp1.iimc.kyoto-u.ac.jp")
    AUTH_HTML_MARKERS = (
        'name="username"',
        'name="j_username"',
        "login.cgi",
        "otplogin.cgi",
    )

    def __init__(self, service: Any) -> None:
        self._service = service

    @property
    def service(self) -> Any:
        return self._service

    def request(self, method: str, path_or_url: str, **kwargs: Any) -> httpx.Response:
        response = self._service.request(method, self._normalize_path(path_or_url), **kwargs)
        self._raise_if_auth_expired(response)
        return response

    @contextmanager
    def stream(self, method: str, path_or_url: str, **kwargs: Any) -> Iterator[httpx.Response]:
        path = self._normalize_path(path_or_url)
        ensure_session = getattr(self._service, "_ensure_session", None)
        if callable(ensure_session):
            ensure_session()
        resolve = getattr(self._service, "_resolve", None)
        url = resolve(path) if callable(resolve) else path
        with self._service.http.stream(method, url, **kwargs) as response:
            self._raise_if_auth_expired(response, read_body=False)
            yield response

    def get_json(
        self,
        path_or_url: str,
        *,
        params: Mapping[str, Any] | None = None,
        ensure_json_suffix: bool = True,
    ) -> Any:
        path = self._json_path(path_or_url) if ensure_json_suffix else path_or_url
        response = self.request("GET", path, params=self._clean_params(params))
        self._raise_for_status(response)
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type.lower():
            raise APIError(
                f"Expected JSON from {response.url}, got {content_type or 'unknown'}",
                status_code=response.status_code,
            )
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise APIError(f"Invalid JSON from {response.url}: {exc}") from exc

    def post_json(
        self,
        path_or_url: str,
        *,
        data: Mapping[str, Any] | None = None,
        json_data: Any | None = None,
        params: Mapping[str, Any] | None = None,
        ensure_json_suffix: bool = True,
    ) -> Any:
        path = self._json_path(path_or_url) if ensure_json_suffix else path_or_url
        response = self.request(
            "POST",
            path,
            params=self._clean_params(params),
            data=self._clean_params(data),
            json=json_data,
        )
        self._raise_for_status(response)
        if not response.content:
            return None
        return response.json()

    def _normalize_path(self, path_or_url: str) -> str:
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url
        if path_or_url.startswith(("/direct/", "/access/", "/portal/")):
            return path_or_url
        if path_or_url.startswith("/"):
            return "/direct" + path_or_url
        return "/direct/" + path_or_url

    def _json_path(self, path_or_url: str) -> str:
        if path_or_url.startswith(("http://", "https://")):
            parts = urlsplit(path_or_url)
            path = self._append_json_suffix(parts.path)
            return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
        path, sep, query = path_or_url.partition("?")
        return self._append_json_suffix(path) + (sep + query if sep else "")

    @staticmethod
    def _append_json_suffix(path: str) -> str:
        last_segment = path.rstrip("/").rsplit("/", 1)[-1]
        if "." in last_segment:
            return path
        return path.rstrip("/") + ".json"

    @staticmethod
    def _clean_params(params: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if not params:
            return None
        return {key: value for key, value in params.items() if value is not None}

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code == 404:
            raise NotFoundError(f"Not found: {response.url}", status_code=404)
        if response.status_code in {401, 403}:
            raise AuthExpiredError(f"KULMS session expired or unauthorized: {response.url}")
        raise APIError(
            f"KULMS Direct API returned HTTP {response.status_code}: {response.url}",
            status_code=response.status_code,
        )

    def _raise_if_auth_expired(self, response: httpx.Response, *, read_body: bool = True) -> None:
        if response.status_code in {401, 403}:
            raise AuthExpiredError(f"KULMS session expired or unauthorized: {response.url}")
        host = response.url.host or ""
        if any(marker in host for marker in self.AUTH_HOST_MARKERS):
            raise AuthExpiredError(f"KULMS session expired; redirected to authentication: {response.url}")
        if not read_body:
            return
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type.lower():
            return
        text = response.text[:5000].lower()
        if any(marker in text for marker in self.AUTH_HTML_MARKERS):
            raise AuthExpiredError(f"KULMS session expired; received authentication page: {response.url}")
