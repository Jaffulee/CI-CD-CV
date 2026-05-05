from __future__ import annotations

import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


class StyleTests(unittest.TestCase):
    def test_latex_macros_define_renderer_contract(self) -> None:
        macros = (REPO_ROOT / "styles" / "latex" / "macros.tex").read_text(encoding="utf-8")

        for command in (
            r"\cvDocumentTitle",
            r"\cvName",
            r"\cvHeadline",
            r"\cvContactLine",
            r"\cvContactEmail",
            r"\cvSection",
            r"\cvEntryHeading",
            r"\cvEntryText",
            r"\cvTools",
            r"\cvLink",
            "cvBullets",
        ):
            self.assertIn(command, macros)

    def test_latex_preambles_include_required_packages(self) -> None:
        for name in ("preamble_default.tex", "preamble_compact.tex"):
            preamble = (REPO_ROOT / "styles" / "latex" / name).read_text(encoding="utf-8")
            self.assertIn(r"\documentclass", preamble)
            self.assertIn(r"\pdfgentounicode=1", preamble)
            self.assertIn(r"\usepackage{cmap}", preamble)
            self.assertIn(r"\usepackage[hidelinks]{hyperref}", preamble)
            self.assertIn(r"\usepackage{lmodern}", preamble)
            self.assertIn(r"\usepackage{microtype}", preamble)
            self.assertIn(r"\DisableLigatures[f]{encoding = *, family = *}", preamble)
            self.assertIn(r"\definecolor{cvAccent}", preamble)
            self.assertIn(r"\usepackage{titlesec}", preamble)
            self.assertIn(r"\usepackage{enumitem}", preamble)
            self.assertIn(r"\urlstyle{same}", preamble)

    def test_latex_link_macro_uses_display_text(self) -> None:
        macros = (REPO_ROOT / "styles" / "latex" / "macros.tex").read_text(encoding="utf-8")

        self.assertIn(r"\newcommand{\cvLink}[4]", macros)
        self.assertIn(r"\href{#2}{#3}", macros)

    def test_html_styles_are_static_and_print_ready(self) -> None:
        css = (REPO_ROOT / "styles" / "html" / "cv.css").read_text(encoding="utf-8")
        print_css = (REPO_ROOT / "styles" / "html" / "print.css").read_text(encoding="utf-8")

        self.assertIn(".cv-page", css)
        self.assertIn(".cv-entry-heading", css)
        self.assertIn("--cv-accent", css)
        self.assertIn(".cv-entry-organisation", css)
        self.assertIn(".cv-link-description", css)
        self.assertIn("@media (max-width: 640px)", css)
        self.assertIn("@page", print_css)
        self.assertIn("@media print", print_css)

    def test_document_rendering_style_references_exist(self) -> None:
        for path in (REPO_ROOT / "data" / "documents").glob("*.yml"):
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            for config in document["rendering"].values():
                for key in ("template_file", "preamble_file"):
                    if config.get(key):
                        self.assertTrue((REPO_ROOT / config[key]).exists(), f"{path}: missing {config[key]}")
                for key in ("stylesheets", "scripts"):
                    for referenced_path in config.get(key, []):
                        self.assertTrue((REPO_ROOT / referenced_path).exists(), f"{path}: missing {referenced_path}")


if __name__ == "__main__":
    unittest.main()
