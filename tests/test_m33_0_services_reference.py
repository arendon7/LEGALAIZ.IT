from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
if str(RUNTIME_MODULES) not in sys.path:
    sys.path.insert(0, str(RUNTIME_MODULES))

from co_em_003_document_factory_v244 import CoEm003DocumentFactoryV244
from document_standard_v33 import audit_docx_legal_standard
from scripts.generate_m32_3_full_portfolio import ControlledEvaluator, _services_answers


class ServicesReferenceM330Tests(unittest.TestCase):
    def test_primary_services_contract_is_recomposed_under_m33(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factory = CoEm003DocumentFactoryV244(
                root,
                ControlledEvaluator(
                    ["DOC-EM-CONTRACT-001"],
                    ["EM-BASE-001", "EM-SCOPE-001", "EM-FEES-001"],
                ),
            )
            manifest = factory.generate(_services_answers(), actor={"id": "qa-m33", "role": "qa"})
            primary = next(item for item in manifest["documents"] if item["id"] == "DOC-EM-CONTRACT-001")
            candidates = sorted((factory.output_dir / manifest["generation_id"]).rglob(primary["filename"]))
            self.assertEqual(len(candidates), 1, candidates)
            contract = candidates[0]

            report = audit_docx_legal_standard(contract)
            self.assertTrue(report["valid"], report["findings"])
            self.assertEqual(primary.get("document_standard"), "M33.0")

            document = Document(contract)
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            self.assertIn("CONTRATO DE PRESTACIÓN DE SERVICIOS PROFESIONALES INDEPENDIENTES", text)
            self.assertIn("PRIMERA: OBJETO", text)
            self.assertIn("ANEXO NO. 1", text.upper())
            self.assertIn("CONTROL DE USO, FUENTES Y REVISIÓN", text)
            self.assertNotIn("________", text)
            self.assertGreater(len(text.split()), 4_000)

            with ZipFile(contract) as archive:
                styles = archive.read("word/styles.xml").decode("utf-8")
                body = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("Times New Roman", styles)
            self.assertNotIn("Arial", styles)
            self.assertIn('w:tblDescription w:val="LegalAIZ-SignatureTable"', body)

    def test_manifest_remains_pending_for_both_human_approvals(self):
        with tempfile.TemporaryDirectory() as tmp:
            factory = CoEm003DocumentFactoryV244(
                Path(tmp),
                ControlledEvaluator(["DOC-EM-CONTRACT-001"], ["EM-BASE-001"]),
            )
            manifest = factory.generate(_services_answers(), actor={"id": "qa-m33", "role": "qa"})
            legal = manifest.get("legal_approval")
            qa = manifest.get("qa_approval")
            legal_status = legal.get("status") if isinstance(legal, dict) else legal
            qa_status = qa.get("status") if isinstance(qa, dict) else qa
            self.assertEqual(str(legal_status).casefold(), "pending")
            self.assertEqual(str(qa_status).casefold(), "pending")
            self.assertFalse(bool(manifest.get("released", False)))


if __name__ == "__main__":
    unittest.main()
