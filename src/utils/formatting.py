"""Shared formatting helpers for renderers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any


LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def compact_whitespace(value: str) -> str:
    """Collapse internal whitespace without stripping meaningful paragraph breaks."""

    return " ".join(value.split())


def normalise_block(value: str) -> str:
    """Trim a multiline YAML block while preserving paragraph separation."""

    paragraphs = [compact_whitespace(part) for part in value.strip().split("\n\n")]
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def format_tools(tools: Iterable[str]) -> str:
    tool_list = [tool for tool in tools if tool]
    return ", ".join(tool_list)


def format_labelled_url(label: str, url: str, description: str | None = None) -> str:
    if description:
        return f"{label}: {url} ({description})"
    return f"{label}: {url}"


def title_from_key(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def flatten_contact(contact: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Flatten contact details into renderer-friendly label/value pairs."""

    rows: list[tuple[str, str]] = []
    for key, value in contact.items():
        label = title_from_key(key)
        if isinstance(value, list):
            rows.append((label, ", ".join(str(item) for item in value)))
        elif isinstance(value, dict):
            rows.append((label, ", ".join(str(item) for item in value.values())))
        else:
            rows.append((label, str(value)))
    return rows


def select_limited_items(items: Iterable[Any], max_items: int | None = None) -> list[Any]:
    selected = list(items)
    if max_items is None:
        return selected
    return selected[:max_items]


def sort_by_priority(items: Iterable[Any]) -> list[Any]:
    """Sort mappings or objects by descending ``priority``."""

    def priority(item: Any) -> int:
        if isinstance(item, Mapping):
            return int(item.get("priority") or 0)
        return int(getattr(item, "priority", None) or 0)

    return sorted(items, key=priority, reverse=True)


def latex_escape(value: str) -> str:
    """Escape LaTeX special characters in plain text."""

    return "".join(LATEX_SPECIAL_CHARS.get(char, char) for char in value)


def typographic_quotes(value: str) -> str:
    """Render plain or TeX-style double quotes as typographic quotes."""

    value = re.sub(r"``(.*?)''", r'"\1"', value)
    result: list[str] = []
    opening = True
    for char in value:
        if char == '"':
            result.append("“" if opening else "”")
            opening = not opening
        else:
            result.append(char)
    return "".join(result)


def latex_quotes(value: str) -> str:
    """Render plain or TeX-style double quotes as LaTeX quote pairs."""

    value = re.sub(r"``(.*?)''", r'"\1"', value)
    result: list[str] = []
    opening = True
    for char in value:
        if char == '"':
            result.append("``" if opening else "''")
            opening = not opening
        else:
            result.append(char)
    return "".join(result)


def markdown_escape_table_cell(value: str) -> str:
    """Escape characters that would break a Markdown table cell."""

    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def typographic_date_range(value: str) -> str:
    """Render YAML date-range separators as an em dash for text outputs."""

    return value.replace(" -- ", " — ")


def latex_date_range(value: str) -> str:
    """Render YAML date-range separators explicitly in LaTeX."""

    return value.replace(" -- ", r" \textemdash{} ")
