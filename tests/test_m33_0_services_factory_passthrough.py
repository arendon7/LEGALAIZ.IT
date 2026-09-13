from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from docx import Document

from legalai_runtime_modules.co_em_003_document_factory_v245 import CoEm003DocumentFactoryV245
from tests.test_m33_0_services_reference import ControlledEvaluator, services_answers, _primary_path


class ServicesFactoryPassthroughM330Tests(unittest.TestCase):
    def test_original_object_result_and_termination_survive_legacy_normalization(self):
        answers = services_answers()
        answers["termination"] = {
            "rules": "incumplimiento grave, imposibilidad prolongada, acuerdo o terminación sin causa con preaviso de treinta días",
            "cure_period": "diez días hábiles",
        }

        with tempfile.TemporaryDirectory() as tmp:
            factory = CoEm003DocumentFactoryV245(
                Path(tmp),
                ControlledEvaluator(["DOC-EM-CONTRACT-001"], ["EM-BASE-001", "EM-SCOPE-001", "EM-FEES-001"]),
            )
            manifest = factory.generate(answers, actor={"id": "qa-m33", "role": "qa"})
            contract, _ = _primary_path(factory, manifest, "DOC-EM-CONTRACT-001")
            document = Document(contract)
            text = "\n".join(paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip())

        self.assertIn("EL CONTRATISTA se obliga a prestar servicios independientes de diagnóstico, diseño y mejora", text)
        self.assertIn("El resultado verificable esperado corresponde a la entrega de una arquitectura documentada", text)
        self.assertIn("preaviso de treinta días", text)
        self.assertIn("diez días hábiles", text)
        self.assertNotIn("se obliga a servicios independientes", text)
        self.assertNotIn("las causales previstas en este contrato y en la ley", text)


if __name__ == "__main__":
    unittest.main()
