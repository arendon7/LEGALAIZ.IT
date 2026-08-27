from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from docx import Document

from legalai_platform.document_quality import validate_docx


class M387OoxmlHardeningTests(unittest.TestCase):
    def _valid_docx(self, folder: Path) -> Path:
        path = folder / "valid.docx"
        document = Document()
        document.add_paragraph(
            "LegalAIZ.it CO-EM-003. Documento jurídico editable con contenido suficiente para validar la estructura OOXML y sus relaciones internas."
        )
        document.core_properties.subject = "CO-EM-003"
        document.save(path)
        return path

    @staticmethod
    def _rewrite(source: Path, target: Path, transform) -> None:
        with ZipFile(source) as incoming, ZipFile(target, "w", ZIP_DEFLATED) as outgoing:
            for info in incoming.infolist():
                payload = incoming.read(info.filename)
                payload = transform(info.filename, payload)
                outgoing.writestr(info, payload)

    def test_duplicate_zip_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = self._valid_docx(folder)
            target = folder / "duplicate-entry.docx"
            with ZipFile(source) as incoming, ZipFile(target, "w", ZIP_DEFLATED) as outgoing:
                for info in incoming.infolist():
                    outgoing.writestr(info, incoming.read(info.filename))
                outgoing.writestr("word/document.xml", incoming.read("word/document.xml"))

            report = validate_docx(target, expected_product="CO-EM-003")
            self.assertFalse(report["valid"])
            self.assertTrue(any("entradas ZIP duplicadas" in error for error in report["errors"]))

    def test_duplicate_relationship_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = self._valid_docx(folder)
            target = folder / "duplicate-rel-id.docx"

            def transform(name: str, payload: bytes) -> bytes:
                if name != "word/_rels/document.xml.rels":
                    return payload
                root = ET.fromstring(payload)
                relationships = list(root)
                self.assertTrue(relationships)
                root.append(deepcopy(relationships[0]))
                return ET.tostring(root, encoding="utf-8", xml_declaration=True)

            self._rewrite(source, target, transform)
            report = validate_docx(target, expected_product="CO-EM-003")
            self.assertFalse(report["valid"])
            self.assertTrue(any("IDs de relación OOXML duplicados" in error for error in report["errors"]))

    def test_duplicate_content_type_default_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = self._valid_docx(folder)
            target = folder / "duplicate-content-type.docx"

            def transform(name: str, payload: bytes) -> bytes:
                if name != "[Content_Types].xml":
                    return payload
                root = ET.fromstring(payload)
                default = next(child for child in list(root) if child.tag.rsplit("}", 1)[-1] == "Default")
                root.append(deepcopy(default))
                return ET.tostring(root, encoding="utf-8", xml_declaration=True)

            self._rewrite(source, target, transform)
            report = validate_docx(target, expected_product="CO-EM-003")
            self.assertFalse(report["valid"])
            self.assertTrue(any("Default duplicadas" in error for error in report["errors"]))

    def test_existing_well_formed_docx_still_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._valid_docx(Path(tmp))
            report = validate_docx(source, expected_product="CO-EM-003")
            self.assertTrue(report["valid"], report["errors"])


if __name__ == "__main__":
    unittest.main()
