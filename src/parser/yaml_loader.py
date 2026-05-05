"""YAML loading helpers for content and document files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.parser.models import (
    ContentCollection,
    ContentEntry,
    ContentStore,
    Details,
    Document,
    LinkEntry,
    LoadedDocument,
    SkillEntry,
    SkillGroup,
)


class YamlLoaderError(RuntimeError):
    """Raised when a YAML file cannot be loaded into the expected structure."""


def load_yaml_file(path: str | Path) -> dict[str, Any]:
    yaml_path = Path(path)
    try:
        with yaml_path.open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise YamlLoaderError(f"Invalid YAML in {yaml_path}: {exc}") from exc
    except OSError as exc:
        raise YamlLoaderError(f"Could not read {yaml_path}: {exc}") from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise YamlLoaderError(f"{yaml_path} must contain a mapping at the top level")
    return data


def load_content_file(path: str | Path) -> tuple[str, Any]:
    content_path = Path(path)
    data = load_yaml_file(content_path)
    if len(data) != 1:
        raise YamlLoaderError(f"{content_path} must contain exactly one top-level key")
    key, value = next(iter(data.items()))
    return key, value


def load_content_dir(content_dir: str | Path) -> ContentStore:
    root = Path(content_dir)
    if not root.exists():
        raise YamlLoaderError(f"Content directory does not exist: {root}")

    store = ContentStore()
    for path in sorted(root.glob("*.yml")):
        data = load_yaml_file(path)

        if path.name == "details.yml":
            store.details = Details.model_validate(data)
            continue

        if len(data) != 1 and path.name != "skills.yml":
            raise YamlLoaderError(f"{path} must contain exactly one top-level key")

        source, value = next(iter(data.items()))

        if source == "skills":
            if not isinstance(value, list):
                raise YamlLoaderError(f"{path}: skills must be a list")
            entries = [SkillEntry.model_validate(item) for item in value]
            store.collections[source] = ContentCollection(source=source, entries=entries)
            groups = data.get("skill_groups", {})
            if not isinstance(groups, dict):
                raise YamlLoaderError(f"{path}: skill_groups must be a mapping")
            store.skill_groups = {
                group_id: SkillGroup.model_validate(group_data)
                for group_id, group_data in groups.items()
            }
            continue

        if source == "links":
            if not isinstance(value, list):
                raise YamlLoaderError(f"{path}: links must be a list")
            entries = [LinkEntry.model_validate(item) for item in value]
        else:
            if not isinstance(value, list):
                raise YamlLoaderError(f"{path}: {source} must be a list")
            entries = [ContentEntry.model_validate(item) for item in value]

        store.collections[source] = ContentCollection(source=source, entries=entries)

    return store


def load_document(path: str | Path) -> Document:
    return Document.model_validate(load_yaml_file(path))


def load_document_file(path: str | Path) -> LoadedDocument:
    document_path = Path(path)
    return LoadedDocument(path=document_path, document=load_document(document_path))


def load_documents_dir(documents_dir: str | Path) -> list[LoadedDocument]:
    root = Path(documents_dir)
    if not root.exists():
        raise YamlLoaderError(f"Documents directory does not exist: {root}")
    return [load_document_file(path) for path in sorted(root.glob("*.yml"))]
