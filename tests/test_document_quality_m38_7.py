from __future__ import annotations

import tempfile
import unittest
import warnings
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from docx import Document

from legalai_platform.document_quality import CONTENT_TYPES_NS, validate_docx


class M387DocumentPackageIntegrityTests(unittest.TestCase):
    def _source_docx(self, folder: Path) -> Path:
        path = folder / "source.docx"
        document = Document()
        document.add_paragraph(
            "LegalAIZ.it CO-EM-003. Contrato jurídico editable con contenido suficiente para validar "
            "la integridad estructural del paquete OOXML sin depender de una reparación de Microsoft Word."
        )
        document.core_properties.subject = "CO-EM-003"
        document.save(path)
        return path

    def _rewrite(self, source: Path, target: Path, transform) -> None:
        with ZipFile(source) as incoming, ZipFile(target, "w", ZIP_DEFLATED) as outgoing:
            for info in incoming.infolist():
                payload = incoming.read(info.filename)
                payload = transform(info.filename, payload)
                outgoing.writestr(info, payload)

    def test_standard_python_docx_package_still_passes_strict_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._source_docx(Path(tmp))
            report = validate_docx(source, expected_product="CO-EM-003")
            self.assertTrue(report["valid"], report["errors"])

    def test_duplicate_package_part_is_rejected_even_if_zip_is_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = self._source_docx(folder)
            target = folder / "duplicate-part.docx"
            with ZipFile(source) as incoming, ZipFile(target, "w", ZIP_DEFLATED) as outgoing:
                for info in incoming.infolist():
                    outgoing.writestr(info, incoming.read(info.filename))
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    outgoing.writestr("word/document.xml", incoming.read("word/document.xml"))
            report = validate_docx(target, expected_product="CO-EM-003")
            self.assertFalse(report["valid"])
            self.assertTrue(any("duplicadas" in error and "word/document.xml" in error for error in report["errors"]))

    def test_orphan_content_type_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = self._source_docx(folder)
            target = folder / "orphan-override.docx"

            def transform(name: str, payload: bytes) -> bytes:
                if name != "[Content_Types].xml":
                    return payload
                root = ET.fromstring(payload)
                ET.SubElement(
                    root,
                    f"{{{CONTENT_TYPES_NS}}}Override",
                    {
                        "PartName": "/word/missing.xml",
                        "ContentType": "application/xml",
                    },
                )
                return ET.tostring(root, encoding="utf-8", xml_declaration=True)

            self._rewrite(source, target, transform)
            report = validate_docx(target, expected_product="CO-EM-003")
            self.assertFalse(report["valid"])
            self.assertTrue(any("Override huérfano" in error for error in report["errors"]))

    def test_duplicate_content_type_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = self._source_docx(folder)
            target = folder / "duplicate-override.docx"

            def transform(name: str, payload: bytes) -> bytes:
                if name != "[Content_Types].xml":
                    return payload
                root = ET.fromstring(payload)
                existing = root.find(f"{{{CONTENT_TYPES_NS}}}Override")
                self.assertIsNotNone(existing)
                ET.SubElement(root, existing.tag, dict(existing.attrib))
                return ET.tostring(root, encoding="utf-8", xml_declaration=True)

            self._rewrite(source, target, transform)
            report = validate_docx(target, expected_product="CO-EM-003")
            self.assertFalse(report["valid"])
            self.assertTrue(any("Override duplicada" in error for error in report["errors"]))

    def test_undeclared_package_part_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = self._source_docx(folder)
            target = folder / "undeclared-part.docx"
            with ZipFile(source) as incoming, ZipFile(target, "w", ZIP_DEFLATED) as outgoing:
                for info in incoming.infolist():
                    outgoing.writestr(info, incoming.read(info.filename))
                outgoing.writestr("word/opaque.legalaiz", b"not declared")
            report = validate_docx(target, expected_product="CO-EM-003")
            self.assertFalse(report["valid"])
            self.assertTrue(any("no tiene tipo de contenido declarado" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
