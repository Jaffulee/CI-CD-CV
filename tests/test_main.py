from __future__ import annotations

import shutil
import unittest
from zipfile import ZipFile
from pathlib import Path

from src.main import generate_all
from src.parser.yaml_loader import load_documents_dir
from src.utils.paths import RepoPaths


REPO_ROOT = Path(__file__).resolve().parents[1]


class MainPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.test_output_dir = REPO_ROOT / "output" / "_test_main"
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)

    def tearDown(self) -> None:
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)

    def _first_document(self):
        documents = load_documents_dir(REPO_ROOT / "data" / "documents")
        self.assertGreater(len(documents), 0)
        return documents[0].document

    def test_generates_selected_document_and_format(self) -> None:
        document = self._first_document()

        class TestRepoPaths(RepoPaths):
            @property
            def output_dir(inner_self) -> Path:
                return self.test_output_dir

        rendered_files = generate_all(
            TestRepoPaths(REPO_ROOT),
            document_filters=[document.output_name],
            format_filters=["markdown"],
            compile_pdf=False,
        )

        self.assertEqual(len(rendered_files), 1)
        rendered = rendered_files[0]
        self.assertEqual(rendered.document_id, document.id)
        self.assertEqual(rendered.output_format, "markdown")
        self.assertTrue(rendered.path.exists())
        if document.title:
            self.assertIn(document.title, rendered.path.read_text(encoding="utf-8"))

    def test_generates_html_assets(self) -> None:
        document = self._first_document()

        class TestRepoPaths(RepoPaths):
            @property
            def output_dir(inner_self) -> Path:
                return self.test_output_dir

        generate_all(
            TestRepoPaths(REPO_ROOT),
            document_filters=[document.output_name],
            format_filters=["html"],
            compile_pdf=False,
        )

        html_dir = self.test_output_dir / "html"
        self.assertTrue((html_dir / f"{document.output_name}.html").exists())
        self.assertTrue((html_dir / "cv.css").exists())
        self.assertTrue((html_dir / "print.css").exists())

    def test_latex_rendering_can_skip_pdf_compilation(self) -> None:
        document = self._first_document()

        class TestRepoPaths(RepoPaths):
            @property
            def output_dir(inner_self) -> Path:
                return self.test_output_dir

        rendered_files = generate_all(
            TestRepoPaths(REPO_ROOT),
            document_filters=[document.output_name],
            format_filters=["latex"],
            compile_pdf=False,
        )

        self.assertEqual([item.output_format for item in rendered_files], ["latex"])
        self.assertTrue((self.test_output_dir / "latex" / f"{document.output_name}.tex").exists())
        self.assertFalse((self.test_output_dir / "latex" / f"{document.output_name}.pdf").exists())

    def test_generates_docx(self) -> None:
        document = self._first_document()

        class TestRepoPaths(RepoPaths):
            @property
            def output_dir(inner_self) -> Path:
                return self.test_output_dir

        rendered_files = generate_all(
            TestRepoPaths(REPO_ROOT),
            document_filters=[document.output_name],
            format_filters=["docx"],
            compile_pdf=False,
        )

        self.assertEqual(len(rendered_files), 1)
        rendered = rendered_files[0]
        self.assertEqual(rendered.output_format, "docx")
        self.assertTrue(rendered.path.exists())
        with ZipFile(rendered.path) as archive:
            names = set(archive.namelist())
            self.assertIn("[Content_Types].xml", names)
            self.assertIn("word/document.xml", names)
            document_xml = archive.read("word/document.xml").decode("utf-8")
            styles_xml = archive.read("word/styles.xml").decode("utf-8")

        if document.title:
            self.assertIn(document.title, document_xml)
        self.assertIn('w:styleId="Name"', styles_xml)
        self.assertIn('w:styleId="SectionTitle"', styles_xml)


if __name__ == "__main__":
    unittest.main()
