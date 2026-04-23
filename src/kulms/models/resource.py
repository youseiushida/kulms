from __future__ import annotations

from pathlib import Path

from pydantic import Field

from kulms.models.base import KULMSModel


class ResourceItem(KULMSModel):
    id: str | None = None
    title: str | None = None
    name: str | None = None
    type: str | None = None
    url: str | None = None
    entity_url: str | None = Field(default=None, alias="entityURL")
    reference: str | None = None
    path: str | None = None
    container: str | None = None
    size: int | None = None
    num_children: int | None = Field(default=None, alias="numChildren")
    modified_date: str | None = Field(default=None, alias="modifiedDate")
    web_link_url: str | None = Field(default=None, alias="webLinkUrl")
    children: list["ResourceItem"] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.title or self.name or self.id or "resource"

    @property
    def download_url(self) -> str | None:
        extras = self.model_extra or {}
        candidates = [
            self.web_link_url,
            extras.get("downloadUrl"),
            extras.get("download_url"),
            extras.get("contentUrl"),
            extras.get("content_url"),
            self.url,
            self.entity_url,
            extras.get("entityURL"),
        ]
        for value in candidates:
            if isinstance(value, str) and value:
                return value
        return None

    @property
    def is_collection(self) -> bool:
        return self.type == "collection" or bool(self.download_url and self.download_url.endswith("/"))


class DownloadResult(KULMSModel):
    source_url: str | None = None
    path: Path | None = None
    status: str
    bytes: int | None = None
    message: str | None = None
