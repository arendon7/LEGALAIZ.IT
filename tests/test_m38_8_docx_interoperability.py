from __future__ import annotations

from copy import deepcopy
import tempfile
import unittest
import warnings
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from docx import Document

from legalai_platform.document_quality import (
    CONTENT_TYPES_NS,
    DOCX_MAIN_CONTENT_TYPE,
    RELATIONSHIP_NS,
    validate_docx,
)


class M388DocxInteroperabilityTests(unittest.TestCase):
    def _valid_docx(self, folder: Path) -> Path:
        path = folder / "CO-EM-003_interoperability.docx"
        document = Document()
        document.add_paragraph(
            "LegalAIZ.it CO-EM-003. Contrato de prueba con contenido jurídico suficiente para validar "
            "la integridad estructural, las relaciones internas y la interoperabilidad del paquete OOXML."
        )
        document.core_properties.subject = "CO-EM-003"
        document.save(path)
        return path

    @staticmethod
    def _rewrite_package(source: Path, target: Path, transform) -> None:
        with ZipFile(source) as incoming, ZipFile(target, "w", ZIP_DEFLATED) as outgoing:
            for info in incoming.infolist():
                name, payload = transform(info.filename, incoming.read(info.filename))
                outgoing.writestr(name, payload)

    def test_valid_python_docx_package_still_passes_strengthened_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._valid_docx(Path(tmp))
            report = validate_docx(path, expected_product="CO-EM-003")
            self.assertTrue(report["valid"], report["errors"])
            self.assertEqual(report["metrics"]["package_entries"], report["metrics"]["package_parts"])

    def test_duplicate_zip_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._valid_docx(root)
            target = root / "duplicate.docx"
            with ZipFile(source) as incoming, ZipFile(target, "w", ZIP_DEFLATED) as outgoing:
                for info in incoming.infolist():
                    outgoing.writestr(info.filename, incoming.read(info.filename))
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    outgoing.writestr("word/document.xml", incoming.read("word/document.xml"))
            report = validate_docx(target)
            self.assertFalse(report["valid"])
            self.assertTrue(any("entradas ZIP duplicadas" in error for error in report["errors"]))

    def test_case_insensitive_part_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._valid_docx(root)
            target = root / "case-collision.docx"
            with ZipFile(source) as incoming, ZipFile(target, "w", ZIP_DEFLATED) as outgoing:
                for info in incoming.infolist():
                    outgoing.writestr(info.filename, incoming.read(info.filename))
                outgoing.writestr("Word/document.xml", incoming.read("word/document.xml"))
            report = validate_docx(target)
            self.assertFalse(report["valid"])
            self.assertTrue(any("colisiones de nombres" in error for error in report["errors"]))

    def test_unsafe_package_part_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._valid_docx(root)
            target = root / "unsafe-part.docx"
            with ZipFile(source) as incoming, ZipFile(target, "w", ZIP_DEFLATED) as outgoing:
                for info in incoming.infolist():
                    outgoing.writestr(info.filename, incoming.read(info.filename))
                outgoing.writestr("../outside.xml", b"<outside/>")
            report = validate_docx(target)
            self.assertFalse(report["valid"])
            self.assertTrue(any("Entrada OOXML insegura" in error for error in report["errors"]))

    def test_relationship_that_escapes_package_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._valid_docx(root)
            target = root / "escaping-relationship.docx"

            def transform(name: str, payload: bytes):
                if name == "_rels/.rels":
                    rels = ET.fromstring(payload)
                    ET.SubElement(
                        rels,
                        f"{{{RELATIONSHIP_NS}}}Relationship",
                        {
                            "Id": "rIdEscape",
                            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
                            "Target": "../word/document.xml",
                        },
                    )
                    payload = ET.tostring(rels, encoding="utf-8", xml_declaration=True)
                return name, payload

            self._rewrite_package(source, target, transform)
            report = validate_docx(target)
            self.assertFalse(report["valid"])
            self.assertTrue(any("Relación interna insegura" in error for error in report["errors"]))

    def test_duplicate_relationship_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._valid_docx(root)
            target = root / "duplicate-relationship-id.docx"

            def transform(name: str, payload: bytes):
                if name == "word/_rels/document.xml.rels":
                    rels = ET.fromstring(payload)
                    existing = list(rels)
                    self.assertTrue(existing)
                    rels.append(deepcopy(existing[0]))
                    payload = ET.tostring(rels, encoding="utf-8", xml_declaration=True)
                return name, payload

            self._rewrite_package(source, target, transform)
            report = validate_docx(target)
            self.assertFalse(report["valid"])
            self.assertTrue(any("IDs de relación OOXML duplicados" in error for error in report["errors"]))

    def test_duplicate_content_type_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._valid_docx(root)
            target = root / "duplicate-content-type.docx"

            def transform(name: str, payload: bytes):
                if name == "[Content_Types].xml":
                    types = ET.fromstring(payload)
                    ET.SubElement(
                        types,
                        f"{{{CONTENT_TYPES_NS}}}Override",
                        {"PartName": "/word/document.xml", "ContentType": DOCX_MAIN_CONTENT_TYPE},
                    )
                    payload = ET.tostring(types, encoding="utf-8", xml_declaration=True)
                return name, payload

            self._rewrite_package(source, target, transform)
            report = validate_docx(target)
            self.assertFalse(report["valid"])
            self.assertTrue(any("Override duplicado" in error for error in report["errors"]))

    def test_wrong_main_document_content_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._valid_docx(root)
            target = root / "wrong-main-content-type.docx"

            def transform(name: str, payload: bytes):
                if name == "[Content_Types].xml":
                    types = ET.fromstring(payload)
                    for child in types.findall(f"{{{CONTENT_TYPES_NS}}}Override"):
                        if child.attrib.get("PartName") == "/word/document.xml":
                            child.set("ContentType", "application/octet-stream")
                    payload = ET.tostring(types, encoding="utf-8", xml_declaration=True)
                return name, payload

            self._rewrite_package(source, target, transform)
            report = validate_docx(target)
            self.assertFalse(report["valid"])
            self.assertTrue(any("ContentType no válido" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
