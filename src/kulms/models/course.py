from __future__ import annotations

from pydantic import Field

from kulms.models.base import KULMSModel


class CourseTool(KULMSModel):
    id: str | None = None
    title: str | None = None
    tool_id: str | None = Field(default=None, alias="toolId")
    placement_id: str | None = Field(default=None, alias="placementId")
    site_id: str | None = Field(default=None, alias="siteId")
    page_id: str | None = Field(default=None, alias="pageId")
    url: str | None = None


class CourseTab(KULMSModel):
    id: str | None = None
    title: str | None = None
    site_id: str | None = Field(default=None, alias="siteId")
    url: str | None = None
    tools: list[CourseTool] = Field(default_factory=list)


class Course(KULMSModel):
    id: str | None = None
    title: str | None = None
    type: str | None = None
    description: str | None = None
    reference: str | None = None
    entity_id: str | None = Field(default=None, alias="entityId")
    entity_title: str | None = Field(default=None, alias="entityTitle")
    entity_reference: str | None = Field(default=None, alias="entityReference")
    entity_url: str | None = Field(default=None, alias="entityURL")

