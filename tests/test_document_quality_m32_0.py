from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
if str(RUNTIME_MODULES) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULES))

from legalai_platform.document_quality import validate_docx
from co_em_003_document_factory_v244 import CoEm003DocumentFactoryV244
from co_la_002_document_factory_v239 import CoLa002DocumentFactoryV239


class FakeLaborEvaluator:
    def evaluate(self, answers):
        return {
            "blocked": False,
            "missing_fields": [],
            "documents": ["DOC-LA-CONTRACT-001"],
            "readiness": "ready_for_human_review",
            "review_requirements": [],
            "warnings": [],
            "blocks": ["LABOR_BASE"],
        }


class DocumentQualityTests(unittest.TestCase):
    def _docx(self, folder: Path, text: str, subject: str = "CO-EM-003") -> Path:
        path = folder / "document.docx"
        document = Document()
        document.add_paragraph(text)
        document.core_properties.subject = subject
        document.save(path)
        return path

    def test_valid_docx_passes_ooxml_and_python_docx_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._docx(
                Path(tmp),
                "LegalAIZ.it CO-EM-003. Documento jurídico editable con contenido suficiente para validar integridad.",
            )
            report = validate_docx(path, expected_product="CO-EM-003")
            self.assertTrue(report["valid"], report["errors"])
            self.assertGreater(report["metrics"]["package_parts"], 5)
            self.assertEqual(report["sha256"], report["sha256"].lower())

    def test_unresolved_variable_blocks_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._docx(
                Path(tmp),
                "LegalAIZ.it CO-EM-003. El contratista será {{contractor.name}} y este texto completa la prueba.",
            )
            report = validate_docx(path, expected_product="CO-EM-003")
            self.assertFalse(report["valid"])
            self.assertTrue(any("sin resolver" in error for error in report["errors"]))

    def test_corrupt_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corrupt.docx"
            path.write_bytes(b"not-a-docx")
            report = validate_docx(path)
            self.assertFalse(report["valid"])
            self.assertTrue(any("DOCX/ZIP" in error for error in report["errors"]))

    def test_broken_internal_relationship_is_rejected(self):
        namespace = "http://schemas.openxmlformats.org/package/2006/relationships"
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = self._docx(
                folder,
                "LegalAIZ.it CO-EM-003. Documento suficientemente extenso para probar una relación OOXML rota.",
            )
            broken = folder / "broken.docx"
            with ZipFile(source) as incoming, ZipFile(broken, "w", ZIP_DEFLATED) as outgoing:
                for info in incoming.infolist():
                    payload = incoming.read(info.filename)
                    if info.filename == "word/_rels/document.xml.rels":
                        root = ET.fromstring(payload)
                        ET.SubElement(
                            root,
                            f"{{{namespace}}}Relationship",
                            {
                                "Id": "rId999",
                                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                                "Target": "media/missing.png",
                            },
                        )
                        payload = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                    outgoing.writestr(info, payload)
            report = validate_docx(broken, expected_product="CO-EM-003")
            self.assertFalse(report["valid"])
            self.assertTrue(any("Relación rota" in error for error in report["errors"]))

    def test_co_em_003_aliases_are_normalized_without_overwriting_canonical_values(self):
        source = {
            "customer": {"name": "Cliente legado", "identification": "900123456-7"},
            "provider": {"name": "Proveedor legado", "identification": "1012345678"},
            "contract": {"object": "Objeto desde formulario legado"},
            "scope": {"object": "Este valor no debe desplazar al objeto contractual"},
        }
        normalized = CoEm003DocumentFactoryV244._normalize_answers(source)
        self.assertEqual(normalized["client"]["identification"]["name"], "Cliente legado")
        self.assertEqual(normalized["contractor"]["identification"]["identification_number"], "1012345678")
        self.assertEqual(normalized["service"]["object"], "Objeto desde formulario legado")
        self.assertNotIn("client", source)

    def test_active_co_la_002_generator_produces_openable_quality_checked_contract(self):
        answers = {
            "employer": {
                "type": "legal_person",
                "legalName": "Empresa Demo S.A.S.",
                "identificationNumber": "900123456-7",
            },
            "employerSignatory": {
                "fullName": "Ana Representante",
                "positionOrCapacity": "representante legal",
            },
            "worker": {"fullName": "Carlos Trabajador", "identificationNumber": "1012345678"},
            "role": {
                "jobTitle": "Analista jurídico",
                "purpose": "apoyar la gestión contractual y documental",
                "functionsPlacement": "full_in_contract",
                "essentialFunctions": ["Revisar contratos", "Mantener trazabilidad documental"],
            },
            "work": {"mainWorkplace": "Medellín", "modality": "onsite", "actualStartDate": "2026-08-05"},
            "schedule": {"weeklyHours": 42, "type": "fixed"},
            "compensation": {"baseSalary": 3500000, "salaryType": "ordinary"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factory = CoLa002DocumentFactoryV239(root, FakeLaborEvaluator())
            manifest = factory.generate(answers, actor={"id": "qa", "role": "qa"})
            contract = (
                root
                / "data"
                / "generated"
                / "co-la-002-v239"
                / manifest["generation_id"]
                / "CO-LA-002_Contrato_Indefinido.docx"
            )
            report = validate_docx(contract, expected_product="CO-LA-002")
            self.assertTrue(report["valid"], report["errors"])
            self.assertGreater(report["metrics"]["characters"], 1_000)
            self.assertEqual(manifest["legal_approval"], "pending")
            self.assertEqual(manifest["qa_approval"], "pending")


if __name__ == "__main__":
    unittest.main()
