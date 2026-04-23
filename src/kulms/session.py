from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Protocol

import httpx


class SessionStore(Protocol):
    def load(self) -> list[dict[str, object]]: ...
    def save(self, cookies: list[dict[str, object]]) -> None: ...
    def clear(self) -> None: ...


def export_cookies(cookies: httpx.Cookies) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for cookie in cookies.jar:
        records.append(
            {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "expires": cookie.expires,
                "secure": cookie.secure,
            }
        )
    return records


def import_cookies(cookies: httpx.Cookies, records: list[dict[str, object]]) -> int:
    imported = 0
    now = int(time.time())
    for record in records:
        expires = record.get("expires")
        if isinstance(expires, int | float) and expires < now:
            continue
        name = str(record.get("name") or "")
        value = str(record.get("value") or "")
        domain = str(record.get("domain") or "")
        path = str(record.get("path") or "/")
        if not name or not domain:
            continue
        cookies.set(name, value, domain=domain, path=path)
        secure = bool(record.get("secure"))
        for cookie in cookies.jar:
            if cookie.name == name and cookie.domain == domain and cookie.path == path:
                cookie.secure = secure
        imported += 1
    return imported


class JsonFileSessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, cookies: list[dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(cookies, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        fd, tmp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                fp.write(payload)
            _chmod_private(tmp_path)
            os.replace(tmp_path, self.path)
            _chmod_private(self.path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


def _chmod_private(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        return
