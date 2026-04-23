from __future__ import annotations

import re
import os
import tempfile
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import quote
from urllib.parse import urlsplit

from kulms.models.resource import DownloadResult, ResourceItem
from kulms.resources.base import BaseResource


WINDOWS_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
DEFAULT_MAX_FILE_SIZE = 512 * 1024 * 1024
ALLOWED_DOWNLOAD_HOST = "lms.gakusei.kyoto-u.ac.jp"
ALLOWED_DOWNLOAD_PATH_PREFIX = "/access/content/"


class ResourcesResource(BaseResource):
    def list(self, site_id: str) -> list[ResourceItem]:
        data = self.direct.get_json(f"/direct/content/site/{quote(site_id, safe='')}")
        return [ResourceItem.model_validate(item) for item in self._items(data, "content_collection")]

    def list_my(self) -> list[ResourceItem]:
        data = self.direct.get_json("/direct/content/my")
        return [ResourceItem.model_validate(item) for item in self._items(data, "content_collection")]

    def download(
        self,
        site_id: str,
        *,
        dest: str | Path = "KULMS",
        overwrite: bool = False,
        dry_run: bool = False,
        allow_external: bool = False,
        max_file_size: int | None = DEFAULT_MAX_FILE_SIZE,
    ) -> list[DownloadResult]:
        course = self._client.courses.get(site_id)
        course_dir = _safe_name(course.title or course.id or site_id)
        base_dir = Path(dest) / course_dir
        results: list[DownloadResult] = []
        raw_data = self.direct.get_json(f"/direct/content/site/{quote(site_id, safe='')}")
        for raw in self._flatten_dicts(raw_data):
            item = ResourceItem.model_validate(raw)
            if item.is_collection:
                continue
            source_url = item.download_url
            if not source_url:
                continue
            if not allow_external and not _is_allowed_download_url(source_url):
                results.append(
                    DownloadResult(
                        source_url=source_url,
                        path=None,
                        status="skipped",
                        message="external URL skipped",
                    )
                )
                continue
            relative = _resource_relative_path(item, site_id)
            target = base_dir / relative
            if target.exists() and not overwrite:
                results.append(DownloadResult(source_url=source_url, path=target, status="skipped"))
                continue
            if dry_run:
                results.append(DownloadResult(source_url=source_url, path=target, status="planned"))
                continue
            results.append(_download_file(self.direct, source_url, target, max_file_size=max_file_size))
        return results


def _safe_name(value: str) -> str:
    cleaned = WINDOWS_INVALID.sub("_", value).strip().strip(".")
    return cleaned or "untitled"


def _safe_relative_path(value: str) -> Path:
    parts = [_safe_name(part) for part in re.split(r"[/\\]+", value) if part not in {"", ".", ".."}]
    return Path(*parts) if parts else Path("resource")


def _resource_relative_path(item: ResourceItem, site_id: str) -> Path:
    if item.path:
        return _safe_relative_path(item.path)
    container = unquote(item.container or "")
    marker = f"/content/group/{site_id}/"
    folder = ""
    if marker in container:
        folder = container.split(marker, 1)[1]
    name = item.display_name
    return _safe_relative_path(f"{folder}/{name}" if folder else name)


def _is_allowed_download_url(value: str) -> bool:
    parts = urlsplit(value)
    if not parts.scheme and not parts.netloc:
        return parts.path.startswith(ALLOWED_DOWNLOAD_PATH_PREFIX)
    return (
        parts.scheme == "https"
        and parts.hostname == ALLOWED_DOWNLOAD_HOST
        and parts.path.startswith(ALLOWED_DOWNLOAD_PATH_PREFIX)
    )


def _download_file(direct, source_url: str, target: Path, *, max_file_size: int | None) -> DownloadResult:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with direct.stream("GET", source_url) as response:
            if response.status_code >= 400:
                return DownloadResult(
                    source_url=source_url,
                    path=target,
                    status="failed",
                    message=f"HTTP {response.status_code}",
                )
            content_length = response.headers.get("content-length")
            if max_file_size is not None and content_length and content_length.isdigit():
                if int(content_length) > max_file_size:
                    return DownloadResult(
                        source_url=source_url,
                        path=target,
                        status="failed",
                        message=f"file exceeds max size ({max_file_size} bytes)",
                    )

            fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
            tmp_path = Path(tmp_name)
            written = 0
            with os.fdopen(fd, "wb") as fp:
                for chunk in response.iter_bytes():
                    if not chunk:
                        continue
                    written += len(chunk)
                    if max_file_size is not None and written > max_file_size:
                        return DownloadResult(
                            source_url=source_url,
                            path=target,
                            status="failed",
                            message=f"file exceeds max size ({max_file_size} bytes)",
                        )
                    fp.write(chunk)
            os.replace(tmp_path, target)
            tmp_path = None
            return DownloadResult(source_url=source_url, path=target, status="downloaded", bytes=written)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
