"""Pydantic models for content and document schemas.

The content YAML files are intentionally heterogeneous: experience entries,
links, skills, hobbies, and research have different fields. These models keep
that flexibility while validating the common contract the generator depends on:
stable IDs, variant names, bullet sets, and document section references.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


EntryMode = Literal["variant", "bullets", "label", "link"]


class FlexibleModel(BaseModel):
    """Base model that accepts forward-compatible YAML fields."""

    model_config = ConfigDict(extra="allow")


class Bullet(FlexibleModel):
    text: str
    priority: int | None = None


class ContentEntry(FlexibleModel):
    id: str
    type: str | None = None
    title: str | None = None
    organisation: str | None = None
    start: str | int | None = None
    end: str | int | None = None
    display_dates: str | None = None
    tools: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)
    variants: dict[str, str] = Field(default_factory=dict)
    bullets: dict[str, list[Bullet]] = Field(default_factory=dict)


class LinkEntry(FlexibleModel):
    id: str
    label: str
    url: str
    description: str | None = None
    domains: list[str] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)


class SkillEntry(FlexibleModel):
    id: str
    label: str
    category: str
    priority: int | None = None
    profiles: list[str] = Field(default_factory=list)


class SkillGroup(FlexibleModel):
    label: str
    skill_ids: list[str] = Field(default_factory=list)


class Details(FlexibleModel):
    person: dict[str, Any]
    address: dict[str, Any] = Field(default_factory=dict)
    contact_variants: dict[str, dict[str, Any]]
    headline_variants: dict[str, str]


class ContentCollection(FlexibleModel):
    source: str
    entries: list[ContentEntry | LinkEntry | SkillEntry]


class ContentStore(FlexibleModel):
    details: Details | None = None
    collections: dict[str, ContentCollection] = Field(default_factory=dict)
    skill_groups: dict[str, SkillGroup] = Field(default_factory=dict)

    def ids_for(self, source: str) -> set[str]:
        collection = self.collections.get(source)
        if collection is None:
            return set()
        return {entry.id for entry in collection.entries}

    def entry_for(self, source: str, entry_id: str) -> ContentEntry | LinkEntry | SkillEntry | None:
        collection = self.collections.get(source)
        if collection is None:
            return None
        return next((entry for entry in collection.entries if entry.id == entry_id), None)


class RenderingFormat(FlexibleModel):
    template_file: str | None = None
    preamble_file: str | None = None
    stylesheets: list[str] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list)


class DocumentDetails(FlexibleModel):
    contact_variant: str
    headline_variant: str


class DocumentEntry(FlexibleModel):
    id: str
    mode: EntryMode
    source: str | None = None
    variant: str | None = None
    bullet_set: str | None = None
    fallback_bullet_set: str | None = None
    max_bullets: int | None = None
    show_tools: bool = False
    show_description: bool = False
    hide_heading: bool = False
    display_text: str | None = None

    @field_validator("max_bullets")
    @classmethod
    def max_bullets_must_be_positive(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("max_bullets must be positive")
        return value


class DocumentSection(FlexibleModel):
    name: str
    source: str
    entries: list[DocumentEntry] = Field(default_factory=list)


class Document(FlexibleModel):
    id: str
    output_name: str
    title: str | None = None
    prompt_injection: bool = False
    prompt_injection_variant: str | None = None
    prompt_injection_text: str | None = None
    details: DocumentDetails
    rendering: dict[str, RenderingFormat] = Field(default_factory=dict)
    sections: list[DocumentSection] = Field(default_factory=list)


class LoadedDocument(FlexibleModel):
    path: Path
    document: Document
