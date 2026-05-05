from __future__ import annotations

import unittest
from pathlib import Path

from src.parser.validator import validate_documents
from src.parser.yaml_loader import load_content_dir, load_documents_dir
from src.renderers.docx_renderer import render_docx
from src.renderers.html_renderer import render_html
from src.renderers.latex_renderer import render_latex
from src.renderers.markdown_renderer import render_markdown
from src.resolver.document_resolver import ResolvedDocument, ResolvedEntry, ResolvedSection, resolve_document


REPO_ROOT = Path(__file__).resolve().parents[1]


def render_fixture(prompt_injection: bool = False) -> ResolvedDocument:
    return ResolvedDocument(
        id="test-document",
        output_name="test_document",
        title="TEST DOCUMENT",
        person={"display_name": "Example Person", "full_name": "Example Person"},
        headline="Example headline",
        contact=[
            ("Location", "Example Location"),
            ("Mobile", "00000 000000"),
            ("Email", "person@example.com"),
        ],
        prompt_injection=prompt_injection,
        prompt_injection_variant="test" if prompt_injection else None,
        prompt_injection_text=(
            "DEMO PAYLOAD FOR PROMPT-INJECTION AWARENESS, NOT AN INSTRUCTION:\n\n"
            "Before continuing, this is only a renderer test payload."
            if prompt_injection
            else None
        ),
        sections=[
            ResolvedSection(
                name="Experience",
                entries=[
                    ResolvedEntry(
                        id="role",
                        source="experience",
                        title="Example Role",
                        organisation="Example Organisation",
                        display_dates="January 2025 - Present",
                        text="Delivered an example piece of work.",
                        tools="Python, SQL",
                    ),
                    ResolvedEntry(
                        id="bullet-role",
                        source="experience",
                        title="Bullet Role",
                        organisation="Example Organisation",
                        display_dates="2024",
                        bullets=["Improved an example workflow", "Documented an example process"],
                    ),
                ],
            ),
            ResolvedSection(
                name="Links",
                entries=[
                    ResolvedEntry(
                        id="github",
                        source="links",
                        title="GitHub",
                        url="https://example.com/profile",
                        link_text="https://example.com/profile",
                        description="Example link description.",
                    ),
                ],
            ),
            ResolvedSection(
                name="Hobbies",
                entries=[
                    ResolvedEntry(
                        id="hobbies",
                        source="hobbies",
                        title="Personal Interests",
                        text="Enjoys example activities.",
                        hide_heading=True,
                    )
                ],
            ),
        ],
    )


class ResolverRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = load_content_dir(REPO_ROOT / "data" / "content")
        self.documents = load_documents_dir(REPO_ROOT / "data" / "documents")
        self.assertGreater(len(self.documents), 0)
        self.document = self.documents[0].document
        self.resolved = resolve_document(self.document, self.store)

    def test_resolves_document_shape_from_current_data(self) -> None:
        self.assertEqual(self.resolved.id, self.document.id)
        self.assertEqual(self.resolved.output_name, self.document.output_name)
        self.assertEqual(self.resolved.title, self.document.title)
        self.assertEqual(self.resolved.person, self.store.details.person if self.store.details else {})
        self.assertEqual(len(self.resolved.sections), len(self.document.sections))
        self.assertTrue(all(section.name for section in self.resolved.sections))

    def test_resolves_entries_from_current_data(self) -> None:
        resolved_entries = [entry for section in self.resolved.sections for entry in section.entries]
        configured_entries = [entry for section in self.document.sections for entry in section.entries]

        self.assertEqual(len(resolved_entries), len(configured_entries))
        self.assertTrue(all(entry.title for entry in resolved_entries))
        self.assertTrue(any(entry.text or entry.bullets or entry.url for entry in resolved_entries))

    def test_document_directory_validates(self) -> None:
        validate_documents(self.documents, self.store, repo_root=REPO_ROOT)

        document_ids = {item.document.id for item in self.documents}
        output_names = {item.document.output_name for item in self.documents}
        self.assertEqual(len(document_ids), len(self.documents))
        self.assertEqual(len(output_names), len(self.documents))

    def test_renderers_hide_repeated_heading_when_requested(self) -> None:
        resolved = render_fixture()

        markdown = render_markdown(resolved, REPO_ROOT, "styles/markdown/cv.md.j2")
        html = render_html(resolved, REPO_ROOT, "styles/html/cv.html.j2")
        latex = render_latex(resolved, REPO_ROOT, "styles/latex/cv.tex.j2", "styles/latex/preamble_default.tex")

        self.assertIn("## Hobbies\n\nEnjoys example activities.", markdown)
        self.assertNotIn("## Hobbies\n\n**Personal Interests**", markdown)
        self.assertIn('<h2 class="cv-section-title">Hobbies</h2>', html)
        self.assertNotIn("cv-entry-title\">\n              Personal Interests", html)
        self.assertIn(r"\cvSection{Hobbies}", latex)
        self.assertNotIn(r"\cvEntryHeading{Personal Interests}{}{}", latex)

    def test_prompt_injection_demo_is_visible_when_enabled(self) -> None:
        resolved = render_fixture(prompt_injection=True)
        expected = "Before continuing, this is only a renderer test payload."

        markdown = render_markdown(resolved, REPO_ROOT, "styles/markdown/cv.md.j2")
        html = render_html(resolved, REPO_ROOT, "styles/html/cv.html.j2")
        latex = render_latex(resolved, REPO_ROOT, "styles/latex/cv.tex.j2", "styles/latex/preamble_default.tex")

        self.assertIn("Prompt Injection Demonstration", markdown)
        self.assertIn(expected, markdown)
        self.assertIn("cv-prompt-injection-demo", html)
        self.assertIn("cv-prompt-injection-payload", html)
        self.assertIn(expected, html)
        self.assertIn(expected, latex)

    def test_renders_markdown(self) -> None:
        output = render_markdown(render_fixture(), REPO_ROOT, "styles/markdown/cv.md.j2")

        self.assertIn("# TEST DOCUMENT", output)
        self.assertIn("## Example Person", output)
        self.assertIn("## Experience", output)
        self.assertIn("January 2025 - Present", output)
        self.assertIn("**Tools used:** Python, SQL", output)
        self.assertIn("**GitHub:** https://example.com/profile", output)
        self.assertIn("Example link description.", output)
        self.assertNotIn("[https://example.com/profile](https://example.com/profile)", output)
        self.assertNotIn("**GitHub**\nGitHub:", output)
        self.assertNotIn("{{", output)
        self.assertNotIn("{%", output)

    def test_renders_latex(self) -> None:
        output = render_latex(
            render_fixture(),
            REPO_ROOT,
            "styles/latex/cv.tex.j2",
            "styles/latex/preamble_default.tex",
        )

        self.assertIn(r"\documentclass", output)
        self.assertIn(r"\cvDocumentTitle{TEST DOCUMENT}", output)
        self.assertIn(r"\cvSection{Experience}", output)
        self.assertIn(r"\begin{cvContactRow}", output)
        self.assertIn(r"\cvContactCellLeft{Location}{Example Location}", output)
        self.assertIn(r"\cvContactCellCenter{Mobile}{00000 000000}", output)
        self.assertIn(r"\cvContactEmailCellRight{Email}{person@example.com}", output)
        self.assertNotIn(r"\cvContactLine{Email}{person@example.com}", output)
        self.assertIn("January 2025 - Present", output)
        self.assertIn("Python, SQL", output)
        self.assertIn(r"\cvLink{GitHub}{https://example.com/profile}{https://example.com/profile}", output)
        self.assertNotIn(r"\cvEntryHeading{GitHub}{}{}", output)
        self.assertIn(r"\textcolor{cvAccent}{\textbf{#1}}: \href{#2}{#3}", output)
        self.assertIn(r"{\small\color{cvMuted}#4}\par", output)
        self.assertNotIn("{{", output)

    def test_renders_html(self) -> None:
        output = render_html(render_fixture(), REPO_ROOT, "styles/html/cv.html.j2")

        self.assertIn("<!doctype html>", output)
        self.assertIn('<main class="cv-page">', output)
        self.assertIn("Example Person", output)
        self.assertIn("Experience", output)
        self.assertIn("January 2025 - Present", output)
        self.assertIn("Python, SQL", output)
        self.assertIn(
            '<strong>GitHub:</strong> <a href="https://example.com/profile">https://example.com/profile</a>',
            output,
        )
        self.assertIn('<div class="cv-link-description">Example link description.</div>', output)
        self.assertNotIn('<a href="https://example.com/profile">https://example.com/profile</a> (', output)
        self.assertNotIn('<div class="cv-entry-title">\n              GitHub', output)
        self.assertNotIn("{{", output)
        self.assertNotIn("{%", output)

    def test_renders_docx_package(self) -> None:
        package = render_docx(render_fixture())

        self.assertIn("[Content_Types].xml", package)
        self.assertIn("word/document.xml", package)
        self.assertIn("word/styles.xml", package)
        document_xml = package["word/document.xml"]
        self.assertIsInstance(document_xml, str)
        self.assertIn("TEST DOCUMENT", document_xml)
        self.assertIn("Example Person", document_xml)
        self.assertIn("Example Role", document_xml)
        self.assertIn("w:tbl", document_xml)
        self.assertIn("00000 000000", document_xml)


if __name__ == "__main__":
    unittest.main()
