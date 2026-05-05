from __future__ import annotations

import unittest
from copy import deepcopy
from pathlib import Path

from src.parser.models import Document
from src.parser.validator import CvValidationError, validate_document, validate_documents
from src.parser.yaml_loader import load_content_dir, load_document, load_documents_dir


REPO_ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_loads_content_store(self) -> None:
        store = load_content_dir(REPO_ROOT / "data" / "content")

        self.assertIsNotNone(store.details)
        self.assertGreater(len(store.collections), 0)
        for source, collection in store.collections.items():
            with self.subTest(source=source):
                self.assertEqual(collection.source, source)
                self.assertGreater(len(collection.entries), 0)
                self.assertEqual(len(store.ids_for(source)), len(collection.entries))

    def test_validates_all_documents(self) -> None:
        store = load_content_dir(REPO_ROOT / "data" / "content")
        documents = load_documents_dir(REPO_ROOT / "data" / "documents")

        validate_documents(documents, store, repo_root=REPO_ROOT)

    def test_rejects_missing_document_reference(self) -> None:
        store = load_content_dir(REPO_ROOT / "data" / "content")
        document = next(item.document for item in load_documents_dir(REPO_ROOT / "data" / "documents") if item.document.sections)
        document_data = document.model_dump()
        document_data = deepcopy(document_data)
        document_data["sections"][0]["entries"][0]["id"] = "missing-entry"
        invalid_document = Document.model_validate(document_data)
        source = document_data["sections"][0]["entries"][0].get("source") or document_data["sections"][0]["source"]

        with self.assertRaisesRegex(CvValidationError, f"missing {source}.missing-entry"):
            validate_document(invalid_document, store, repo_root=REPO_ROOT)

    def test_rejects_missing_variant(self) -> None:
        store = load_content_dir(REPO_ROOT / "data" / "content")
        document = next(
            item.document
            for item in load_documents_dir(REPO_ROOT / "data" / "documents")
            if any(entry.mode == "variant" for section in item.document.sections for entry in section.entries)
        )
        document_data = document.model_dump()
        document_data = deepcopy(document_data)
        for section in document_data["sections"]:
            variant_entry = next((entry for entry in section["entries"] if entry["mode"] == "variant"), None)
            if variant_entry is not None:
                variant_entry["variant"] = "missing-variant"
                break
        invalid_document = Document.model_validate(document_data)

        with self.assertRaisesRegex(CvValidationError, "missing variant missing-variant"):
            validate_document(invalid_document, store, repo_root=REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
