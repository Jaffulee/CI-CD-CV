"""Validation helpers for content IDs, document references, and variants."""

from __future__ import annotations

from pathlib import Path

from src.parser.models import (
    ContentEntry,
    ContentStore,
    Document,
    DocumentEntry,
    LoadedDocument,
    SkillEntry,
)


class CvValidationError(ValueError):
    """Raised when YAML is structurally valid but semantically inconsistent."""


def validate_content_store(store: ContentStore) -> None:
    errors: list[str] = []

    if store.details is None:
        errors.append("Missing details.yml")
    else:
        if not store.details.contact_variants:
            errors.append("details.yml has no contact_variants")
        if not store.details.headline_variants:
            errors.append("details.yml has no headline_variants")

    for source, collection in store.collections.items():
        seen: set[str] = set()
        for entry in collection.entries:
            if entry.id in seen:
                errors.append(f"{source}: duplicate id {entry.id}")
            seen.add(entry.id)

    skill_ids = store.ids_for("skills")
    for group_id, group in store.skill_groups.items():
        for skill_id in group.skill_ids:
            if skill_id not in skill_ids:
                errors.append(f"skill_groups.{group_id}: missing skill id {skill_id}")

    if errors:
        raise CvValidationError("\n".join(errors))


def validate_document(document: Document, store: ContentStore, repo_root: str | Path | None = None) -> None:
    errors: list[str] = []

    if store.details is None:
        errors.append(f"{document.id}: cannot validate document without details.yml")
    else:
        if document.details.contact_variant not in store.details.contact_variants:
            errors.append(
                f"{document.id}: missing contact variant {document.details.contact_variant}"
            )
        if document.details.headline_variant not in store.details.headline_variants:
            errors.append(
                f"{document.id}: missing headline variant {document.details.headline_variant}"
            )

    if repo_root is not None:
        root = Path(repo_root)
        for format_name, config in document.rendering.items():
            for field_name in ("template_file", "preamble_file"):
                path_value = getattr(config, field_name)
                if path_value and not (root / path_value).exists():
                    errors.append(
                        f"{document.id}: rendering.{format_name}.{field_name} does not exist: {path_value}"
                    )
            for field_name in ("stylesheets", "scripts"):
                for path_value in getattr(config, field_name):
                    if not (root / path_value).exists():
                        errors.append(
                            f"{document.id}: rendering.{format_name}.{field_name} does not exist: {path_value}"
                        )

    if document.prompt_injection and not document.prompt_injection_variant:
        errors.append(f"{document.id}: prompt_injection requires prompt_injection_variant")

    for section in document.sections:
        if not section.entries:
            errors.append(f"{document.id}: section {section.name} has no entries")
        for entry in section.entries:
            source = entry.source or section.source
            if source == "mixed":
                errors.append(f"{document.id}: section {section.name} entry {entry.id} needs a source")
                continue

            content_entry = store.entry_for(source, entry.id)
            if content_entry is None:
                errors.append(f"{document.id}: section {section.name} references missing {source}.{entry.id}")
                continue

            errors.extend(_validate_entry_mode(document.id, section.name, source, entry, content_entry))

    if errors:
        raise CvValidationError("\n".join(errors))


def validate_documents(
    documents: list[LoadedDocument] | list[Document],
    store: ContentStore,
    repo_root: str | Path | None = None,
) -> None:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_outputs: set[str] = set()

    for item in documents:
        document = item.document if isinstance(item, LoadedDocument) else item
        if document.id in seen_ids:
            errors.append(f"Duplicate document id {document.id}")
        seen_ids.add(document.id)

        if document.output_name in seen_outputs:
            errors.append(f"Duplicate document output_name {document.output_name}")
        seen_outputs.add(document.output_name)

        try:
            validate_document(document, store, repo_root=repo_root)
        except CvValidationError as exc:
            errors.append(str(exc))

    if errors:
        raise CvValidationError("\n".join(errors))


def _validate_entry_mode(
    document_id: str,
    section_name: str,
    source: str,
    document_entry: DocumentEntry,
    content_entry: ContentEntry | SkillEntry,
) -> list[str]:
    location = f"{document_id}: section {section_name} entry {source}.{document_entry.id}"
    errors: list[str] = []

    if document_entry.mode == "variant":
        if not isinstance(content_entry, ContentEntry):
            errors.append(f"{location}: variant mode is only valid for content entries")
        elif not document_entry.variant:
            errors.append(f"{location}: variant mode requires variant")
        elif document_entry.variant not in content_entry.variants:
            errors.append(f"{location}: missing variant {document_entry.variant}")

    if document_entry.mode == "bullets":
        if not isinstance(content_entry, ContentEntry):
            errors.append(f"{location}: bullets mode is only valid for content entries")
        elif not document_entry.bullet_set:
            errors.append(f"{location}: bullets mode requires bullet_set")
        elif (
            document_entry.bullet_set not in content_entry.bullets
            and document_entry.fallback_bullet_set not in content_entry.bullets
        ):
            errors.append(
                f"{location}: missing bullet_set {document_entry.bullet_set}"
                f" and fallback_bullet_set {document_entry.fallback_bullet_set}"
            )

    if document_entry.mode == "label" and not isinstance(content_entry, SkillEntry):
        errors.append(f"{location}: label mode is only valid for skills")

    if document_entry.mode == "link" and source != "links":
        errors.append(f"{location}: link mode is only valid for links")

    return errors
