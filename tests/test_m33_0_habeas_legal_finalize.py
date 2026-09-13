from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from docx_builder import build_docx
from document_standard_v33 import validate_rendered_sections
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_procedural_wave import PRODUCTS, habeas_fixture


EXPECTED_KINDS = {
    "habeas_consultation",
    "habeas_claim",
    "habeas_reiteration",
    "identity_theft_protocol",
    "habeas_authority_escalation",
    "habeas_evidence_matrix",
    "habeas_deadline_calendar",
}


def _specs(answers: dict, result: dict):
    return document_specs_m33_all(
        "CASE-M33-HABEAS",
        "CO-CD-001",
        answers,
        result,
        PRODUCTS["CO-CD-001"],
        "2026-08-08T09:00:00-05:00",
        [],
    )


def _plain(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


class HabeasLegalFinalizeM330Tests(unittest.TestCase):
    def test_package_rewrites_all_seven_coordinated_documents(self):
        answers, result = habeas_fixture()
        specs = _specs(answers, result)
        kinds = {spec.get("kind") for spec in specs}
        self.assertTrue(EXPECTED_KINDS.issubset(kinds))

        for spec in specs:
            if spec.get("kind") not in EXPECTED_KINDS:
                continue
            self.assertTrue(spec.get("internal_controls_externalized"), spec.get("kind"))
            self.assertEqual(spec.get("legal_approval"), "pending")
            self.assertEqual(spec.get("qa_approval"), "pending")
            self.assertIs(spec.get("released"), False)
            visible = _plain(spec).casefold()
            self.assertNotIn("control de uso", visible)
            self.assertNotIn("mismo hash", visible)
            self.assertNotIn("aprobación jurídica y qa", visible)
            internal = " ".join(str(section) for section in spec.get("internal_review_sections") or []).casefold()
            self.assertIn("control jurídico co-cd-001", internal)

    def test_reiteration_does_not_claim_silence_while_ordinary_term_is_open(self):
        answers, result = habeas_fixture()
        specs = _specs(answers, result)
        reiteration = next(spec for spec in specs if spec.get("kind") == "habeas_reiteration")
        text = _plain(reiteration)
        self.assertIn("EN TÉRMINO ORDINARIO", text)
        self.assertIn("11 de agosto de 2026", text)
        self.assertIn("no puede afirmarse todavía incumplimiento del término ni silencio", text)
        self.assertIn("no se reutiliza la fecha de una actuación distinta", text)
        self.assertNotIn("control de silencio", reiteration.get("title", "").casefold())
        self.assertNotIn("se entiende aceptad", text.casefold())

    def test_claim_separates_paid_obligation_from_identity_theft_track(self):
        answers, result = habeas_fixture()
        specs = _specs(answers, result)
        claim = next(spec for spec in specs if spec.get("kind") == "habeas_claim")
        text = _plain(claim)
        self.assertIn("Producto adicional desconocido por el titular", text)
        self.assertIn("no transforma automáticamente la obligación reconocida o pagada", text)
        self.assertIn("20 de noviembre de 2026", text)
        self.assertIn("artículo 12 de la Ley 1266 de 2008", text)
        self.assertIn("quince (15) días hábiles", text)
        self.assertIn("ocho (8) días hábiles", text)
        self.assertIn("dos (2) días hábiles", text)

    def test_identity_protocol_uses_current_regime_without_anticipating_law_2573(self):
        answers, result = habeas_fixture()
        specs = _specs(answers, result)
        protocol = next(spec for spec in specs if spec.get("kind") == "identity_theft_protocol")
        text = _plain(protocol)
        self.assertIn("20 de noviembre de 2026", text)
        self.assertIn("sin anticipar términos, cargas o efectos futuros", text)
        self.assertIn("posible suplantación", text.casefold())
        self.assertIn("preservación inmediata de evidencia", text.casefold())

    def test_evidence_and_calendar_are_no_longer_legacy_only(self):
        answers, result = habeas_fixture()
        specs = _specs(answers, result)
        evidence = next(spec for spec in specs if spec.get("kind") == "habeas_evidence_matrix")
        calendar = next(spec for spec in specs if spec.get("kind") == "habeas_deadline_calendar")
        evidence_text = _plain(evidence)
        calendar_text = _plain(calendar)
        self.assertIn("HD-EV-013", evidence_text)
        self.assertIn("ruta de posible suplantación", evidence_text)
        self.assertIn("10 días hábiles", calendar_text)
        self.assertIn("15 días hábiles", calendar_text)
        self.assertIn("Hasta 8 días hábiles adicionales", calendar_text)
        self.assertIn("EN TÉRMINO ORDINARIO", calendar_text)

    def test_red_case_preserves_risk_gate_and_is_not_habeas_finalized(self):
        answers, result = habeas_fixture()
        result["risk"] = "red"
        specs = _specs(answers, result)
        self.assertFalse(any(spec.get("internal_controls_externalized") for spec in specs))

    def test_all_client_documents_pass_semantic_validation_and_render_without_internal_control(self):
        answers, result = habeas_fixture()
        specs = _specs(answers, result)
        selected = [spec for spec in specs if spec.get("kind") in EXPECTED_KINDS]
        self.assertEqual(len(selected), 7)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, spec in enumerate(selected, 1):
                report = validate_rendered_sections(spec["sections"], product_code="CO-CD-001")
                self.assertTrue(report["valid"], (spec.get("kind"), report.get("errors")))
                target = root / f"{index:02d}_{spec['kind']}.docx"
                build_docx(
                    target,
                    spec["title"],
                    spec.get("subtitle", ""),
                    [],
                    spec["sections"],
                    product_code="CO-CD-001",
                    enforce_legal_standard=True,
                    append_default_control=not bool(spec.get("internal_controls_externalized")),
                )
                self.assertTrue(target.is_file())
                with ZipFile(target) as archive:
                    xml = archive.read("word/document.xml").decode("utf-8")
                self.assertNotIn("CONTROL DE USO", xml)
                self.assertNotIn("mismo hash", xml.casefold())


if __name__ == "__main__":
    unittest.main()
