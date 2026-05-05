"""LaTeX renderer for resolved CV documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src.resolver.document_resolver import ResolvedDocument
from src.utils.formatting import latex_date_range, latex_escape, latex_quotes
from src.utils.paths import write_text_atomic


def render_latex(
    document: ResolvedDocument,
    repo_root: str | Path,
    template_file: str = "styles/latex/cv.tex.j2",
    preamble_file: str = "styles/latex/preamble_default.tex",
) -> str:
    env = Environment(
        loader=FileSystemLoader(Path(repo_root)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.filters["latex_date_range"] = latex_date_range
    template = env.get_template(template_file)
    context = _escape_latex_context(document.model_dump())
    context["preamble_file"] = preamble_file
    context["latex_preamble"] = (Path(repo_root) / preamble_file).read_text(encoding="utf-8").strip()
    context["latex_macros"] = (Path(repo_root) / "styles" / "latex" / "macros.tex").read_text(encoding="utf-8").strip()
    return template.render(**context).strip() + "\n"


def write_latex(
    document: ResolvedDocument,
    repo_root: str | Path,
    output_path: str | Path,
    template_file: str = "styles/latex/cv.tex.j2",
    preamble_file: str = "styles/latex/preamble_default.tex",
) -> Path:
    return write_text_atomic(output_path, render_latex(document, repo_root, template_file, preamble_file), encoding="utf-8")


def _escape_latex_context(value: Any) -> Any:
    if isinstance(value, str):
        return latex_escape(latex_quotes(value))
    if isinstance(value, list):
        return [_escape_latex_context(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_escape_latex_context(item) for item in value)
    if isinstance(value, dict):
        return {key: _escape_latex_context(item) for key, item in value.items()}
    return value
