"""HTML renderer for resolved CV documents."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup, escape

from src.resolver.document_resolver import ResolvedDocument
from src.utils.formatting import typographic_date_range, typographic_quotes
from src.utils.paths import write_text_atomic


def render_html(document: ResolvedDocument, repo_root: str | Path, template_file: str = "styles/html/cv.html.j2") -> str:
    env = Environment(
        loader=FileSystemLoader(Path(repo_root)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.filters["typographic_date_range"] = typographic_date_range
    env.filters["html_paragraphs"] = html_paragraphs
    template = env.get_template(template_file)
    return template.render(**_typographic_context(document.model_dump())).strip() + "\n"


def write_html(document: ResolvedDocument, repo_root: str | Path, output_path: str | Path, template_file: str = "styles/html/cv.html.j2") -> Path:
    return write_text_atomic(output_path, render_html(document, repo_root, template_file), encoding="utf-8")


def _typographic_context(value):
    if isinstance(value, str):
        return typographic_quotes(value)
    if isinstance(value, list):
        return [_typographic_context(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_typographic_context(item) for item in value)
    if isinstance(value, dict):
        return {key: _typographic_context(item) for key, item in value.items()}
    return value


def html_paragraphs(value: str) -> Markup:
    """Render paragraph-separated plain text as escaped HTML paragraphs."""

    paragraphs = [paragraph.strip() for paragraph in value.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return Markup("")
    return Markup("\n".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs))
