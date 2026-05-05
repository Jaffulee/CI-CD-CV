"""Path helpers for repository inputs and generated outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_OUTPUT_FORMATS = {"markdown": ".md", "latex": ".tex", "html": ".html", "pdf": ".pdf", "docx": ".docx"}


@dataclass(frozen=True)
class RepoPaths:
    """Canonical paths used by the CV generator."""

    root: Path

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def content_dir(self) -> Path:
        return self.data_dir / "content"

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    @property
    def styles_dir(self) -> Path:
        return self.root / "styles"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"

    def output_format_dir(self, output_format: str) -> Path:
        validate_output_format(output_format)
        return self.output_dir / output_format

    def output_path(self, output_name: str, output_format: str) -> Path:
        validate_output_name(output_name)
        validate_output_format(output_format)
        suffix = SUPPORTED_OUTPUT_FORMATS[output_format]
        if output_format == "pdf":
            return self.output_format_dir("latex") / f"{output_name}{suffix}"
        return self.output_format_dir(output_format) / f"{output_name}{suffix}"

    def resolve_repo_path(self, path: str | Path) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return self.root / candidate


def find_repo_root(start: str | Path | None = None) -> Path:
    """Find the repository root by walking upward from ``start``."""

    current = Path(start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "cv_design_doc.md").exists():
            return candidate

    raise FileNotFoundError(f"Could not find repository root from {current}")


def repo_paths(start: str | Path | None = None) -> RepoPaths:
    return RepoPaths(root=find_repo_root(start))


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_parent_dir(path: str | Path) -> Path:
    output_path = Path(path)
    ensure_directory(output_path.parent)
    return output_path


def write_text_atomic(path: str | Path, content: str, encoding: str = "utf-8") -> Path:
    output_path = ensure_parent_dir(path)
    output_path.write_text(content, encoding=encoding)
    return output_path


def validate_output_format(output_format: str) -> None:
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_OUTPUT_FORMATS))
        raise ValueError(f"Unsupported output format {output_format!r}; expected one of: {supported}")


def validate_output_name(output_name: str) -> None:
    if not output_name:
        raise ValueError("output_name cannot be empty")
    if any(separator in output_name for separator in ("/", "\\")):
        raise ValueError("output_name must be a filename stem, not a path")
    if output_name in {".", ".."}:
        raise ValueError("output_name cannot be . or ..")
