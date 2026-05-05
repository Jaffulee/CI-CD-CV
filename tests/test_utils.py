from __future__ import annotations

import unittest
from pathlib import Path

from src.utils.formatting import (
    compact_whitespace,
    flatten_contact,
    format_labelled_url,
    format_tools,
    latex_date_range,
    latex_escape,
    latex_quotes,
    markdown_escape_table_cell,
    normalise_block,
    sort_by_priority,
    typographic_date_range,
    typographic_quotes,
)
from src.utils.paths import RepoPaths, ensure_directory, ensure_parent_dir, find_repo_root, repo_paths


REPO_ROOT = Path(__file__).resolve().parents[1]


class PathUtilityTests(unittest.TestCase):
    def test_find_repo_root_from_tests_directory(self) -> None:
        self.assertEqual(find_repo_root(Path(__file__)), REPO_ROOT)
        self.assertEqual(repo_paths(REPO_ROOT / "tests").root, REPO_ROOT)

    def test_repo_paths_builds_output_paths(self) -> None:
        paths = RepoPaths(REPO_ROOT)

        self.assertEqual(paths.content_dir, REPO_ROOT / "data" / "content")
        self.assertEqual(paths.documents_dir, REPO_ROOT / "data" / "documents")
        self.assertEqual(paths.output_path("example_cv", "markdown"), REPO_ROOT / "output" / "markdown" / "example_cv.md")
        self.assertEqual(paths.output_path("example_cv", "latex"), REPO_ROOT / "output" / "latex" / "example_cv.tex")
        self.assertEqual(paths.output_path("example_cv", "pdf"), REPO_ROOT / "output" / "latex" / "example_cv.pdf")
        self.assertEqual(paths.resolve_repo_path("styles/latex/macros.tex"), REPO_ROOT / "styles" / "latex" / "macros.tex")

    def test_rejects_invalid_output_names_and_formats(self) -> None:
        paths = RepoPaths(REPO_ROOT)

        with self.assertRaisesRegex(ValueError, "Unsupported output format"):
            paths.output_path("example_cv", "rtf")
        with self.assertRaisesRegex(ValueError, "filename stem"):
            paths.output_path("nested/example_cv", "markdown")

    def test_ensure_directory_helpers(self) -> None:
        directory = ensure_directory(REPO_ROOT / "output" / "markdown")
        file_path = ensure_parent_dir(REPO_ROOT / "output" / "latex" / "example_cv.tex")

        self.assertTrue(directory.is_dir())
        self.assertTrue(file_path.parent.is_dir())


class FormattingUtilityTests(unittest.TestCase):
    def test_text_normalisation(self) -> None:
        self.assertEqual(compact_whitespace("  hello   there\nworld  "), "hello there world")
        self.assertEqual(normalise_block(" first line \n\n second   line "), "first line\n\nsecond line")

    def test_contact_and_list_formatting(self) -> None:
        contact = {
            "mobile": "07123 456789",
            "email": "your.name@example.com",
            "address": ["10 Example Street", "London"],
        }

        self.assertEqual(
            flatten_contact(contact),
            [
                ("Mobile", "07123 456789"),
                ("Email", "your.name@example.com"),
                ("Address", "10 Example Street, London"),
            ],
        )
        self.assertEqual(format_tools(["Python", "Snowflake", "Docker"]), "Python, Snowflake, Docker")
        self.assertEqual(
            format_labelled_url("Profile", "https://example.com/profile"),
            "Profile: https://example.com/profile",
        )

    def test_priority_sorting(self) -> None:
        self.assertEqual(
            [item["label"] for item in sort_by_priority([{"label": "b", "priority": 1}, {"label": "a", "priority": 10}])],
            ["a", "b"],
        )

    def test_escaping(self) -> None:
        self.assertEqual(latex_escape("Snowflake & Python_3"), r"Snowflake \& Python\_3")
        self.assertEqual(markdown_escape_table_cell("a|b\nc"), "a\\|b c")

    def test_typographic_date_range(self) -> None:
        self.assertEqual(typographic_date_range("March 2026 -- April 2026"), "March 2026 \u2014 April 2026")
        self.assertEqual(latex_date_range("March 2026 -- April 2026"), r"March 2026 \textemdash{} April 2026")

    def test_quote_formatting(self) -> None:
        text = "He said \"hello\" and ``goodbye''"
        self.assertEqual(typographic_quotes(text), "He said \u201chello\u201d and \u201cgoodbye\u201d")
        self.assertEqual(latex_quotes(text), "He said ``hello'' and ``goodbye''")


if __name__ == "__main__":
    unittest.main()
