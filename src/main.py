"""Command-line entry point for the CV generation pipeline."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parser.models import Document, LoadedDocument, RenderingFormat
from src.parser.validator import validate_content_store, validate_documents
from src.parser.yaml_loader import load_content_dir, load_documents_dir
from src.renderers.html_renderer import write_html
from src.renderers.latex_renderer import write_latex
from src.renderers.markdown_renderer import write_markdown
from src.renderers.docx_renderer import write_docx
from src.resolver.document_resolver import ResolvedDocument, resolve_document
from src.utils.paths import RepoPaths, repo_paths


RenderWriter = Callable[[ResolvedDocument, Path, Path, str], Path]


@dataclass(frozen=True)
class RenderedFile:
    document_id: str
    output_format: str
    path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate CV documents from YAML content.")
    parser.add_argument(
        "--document",
        action="append",
        dest="documents",
        help="Document id or output_name to render. Can be passed more than once. Defaults to all documents.",
    )
    parser.add_argument(
        "--format",
        action="append",
        dest="formats",
        choices=("markdown", "latex", "html", "pdf", "docx"),
        help="Output format to render. Can be passed more than once. Defaults to all formats configured by each document, with PDFs compiled from LaTeX.",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Render LaTeX .tex files without compiling PDFs.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root. Defaults to auto-discovery from the current working directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = RepoPaths(args.repo_root.resolve()) if args.repo_root else repo_paths()
    os.chdir(paths.root)
    rendered_files = generate_all(
        paths,
        document_filters=args.documents,
        format_filters=args.formats,
        compile_pdf=not args.no_pdf,
    )

    if not rendered_files:
        print("No files rendered.")
        return

    print("Rendered files:")
    for rendered_file in rendered_files:
        relative_path = rendered_file.path.relative_to(paths.root)
        print(f"- {rendered_file.document_id} [{rendered_file.output_format}]: {relative_path}")


def generate_all(
    paths: RepoPaths,
    document_filters: list[str] | None = None,
    format_filters: list[str] | None = None,
    compile_pdf: bool = True,
) -> list[RenderedFile]:
    content_store = load_content_dir(paths.content_dir)
    documents = load_documents_dir(paths.documents_dir)

    selected_documents = _filter_documents(documents, document_filters)
    validate_content_store(content_store)
    validate_documents(selected_documents, content_store, repo_root=paths.root)

    rendered_files: list[RenderedFile] = []
    requested_formats = set(format_filters or [])

    for loaded_document in selected_documents:
        resolved = resolve_document(loaded_document.document, content_store)
        rendering_items = list(loaded_document.document.rendering.items())
        if not requested_formats or "docx" in requested_formats:
            rendering_items.append(("docx", RenderingFormat()))

        for output_format, rendering_config in rendering_items:
            if requested_formats and output_format not in requested_formats and not (output_format == "latex" and "pdf" in requested_formats):
                continue
            rendered_files.extend(
                _render_format(
                    paths,
                    loaded_document.document,
                    resolved,
                    output_format,
                    rendering_config,
                    compile_pdf=compile_pdf,
                    requested_formats=requested_formats,
                )
            )

    return rendered_files


def _filter_documents(
    documents: list[LoadedDocument],
    document_filters: list[str] | None,
) -> list[LoadedDocument]:
    if not document_filters:
        return documents

    requested = set(document_filters)
    selected = [
        loaded_document
        for loaded_document in documents
        if loaded_document.document.id in requested or loaded_document.document.output_name in requested
    ]
    found = {document.document.id for document in selected} | {document.document.output_name for document in selected}
    missing = requested - found
    if missing:
        raise ValueError(f"Unknown document filter(s): {', '.join(sorted(missing))}")
    return selected


def _render_format(
    paths: RepoPaths,
    document: Document,
    resolved: ResolvedDocument,
    output_format: str,
    rendering_config: RenderingFormat,
    compile_pdf: bool,
    requested_formats: set[str],
) -> list[RenderedFile]:
    output_path = paths.output_path(document.output_name, output_format)
    if output_format == "markdown":
        template_file = rendering_config.template_file
        if template_file is None:
            raise ValueError(f"{document.id}: rendering.{output_format}.template_file is required")
        path = write_markdown(resolved, paths.root, output_path, template_file)
        return [RenderedFile(document_id=document.id, output_format=output_format, path=path)]
    elif output_format == "latex":
        template_file = rendering_config.template_file
        if template_file is None:
            raise ValueError(f"{document.id}: rendering.{output_format}.template_file is required")
        if rendering_config.preamble_file is None:
            raise ValueError(f"{document.id}: rendering.latex.preamble_file is required")
        path = write_latex(resolved, paths.root, output_path, template_file, rendering_config.preamble_file)
        rendered = [RenderedFile(document_id=document.id, output_format=output_format, path=path)]
        if compile_pdf:
            pdf_path = paths.output_path(document.output_name, "pdf")
            try:
                rendered.append(
                    RenderedFile(
                        document_id=document.id,
                        output_format="pdf",
                        path=compile_latex_to_pdf(path, pdf_path),
                    )
                )
            except LatexCompilationError as exc:
                print(f"Warning: {exc}", file=sys.stderr)
        return rendered
    elif output_format == "html":
        template_file = rendering_config.template_file
        if template_file is None:
            raise ValueError(f"{document.id}: rendering.{output_format}.template_file is required")
        path = write_html(resolved, paths.root, output_path, template_file)
        _copy_html_assets(paths, output_path.parent, rendering_config)
        return [RenderedFile(document_id=document.id, output_format=output_format, path=path)]
    elif output_format == "docx":
        path = write_docx(resolved, output_path)
        return [RenderedFile(document_id=document.id, output_format=output_format, path=path)]
    else:
        raise ValueError(f"Unsupported renderer: {output_format}")


def _copy_html_assets(paths: RepoPaths, output_dir: Path, rendering_config: RenderingFormat) -> None:
    for stylesheet in rendering_config.stylesheets:
        source = paths.resolve_repo_path(stylesheet)
        destination = output_dir / source.name
        shutil.copyfile(source, destination)

    for script in rendering_config.scripts:
        source = paths.resolve_repo_path(script)
        destination = output_dir / source.name
        shutil.copyfile(source, destination)


class LatexCompilationError(RuntimeError):
    """Raised when a LaTeX document cannot be compiled to PDF."""


def compile_latex_to_pdf(tex_path: Path, pdf_path: Path) -> Path:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")
    if latexmk:
        command = [
            latexmk,
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-outdir={pdf_path.parent}",
            str(tex_path),
        ]
    elif pdflatex:
        command = [
            pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={pdf_path.parent}",
            str(tex_path),
        ]
    else:
        raise LatexCompilationError("Could not compile PDF because neither latexmk nor pdflatex is available on PATH.")

    result = subprocess.run(command, cwd=tex_path.parent, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        last_line = detail[-1] if detail else "no compiler output"
        raise LatexCompilationError(f"LaTeX compilation failed for {tex_path}: {last_line}")

    expected_pdf = pdf_path.parent / f"{tex_path.stem}.pdf"
    if expected_pdf != pdf_path and expected_pdf.exists():
        expected_pdf.replace(pdf_path)

    if not pdf_path.exists():
        raise LatexCompilationError(f"LaTeX compilation did not produce expected PDF: {pdf_path}")

    return pdf_path


if __name__ == "__main__":
    main()
