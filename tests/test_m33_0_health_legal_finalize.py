from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from document_standard_v33 import validate_rendered_sections
from docx_builder import build_docx
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_wave3 import PRODUCTS, health_fixture

EXPECTED_KINDS = {
    "health_diagnostic", "health_petition", "health_reiteration",
    "health_supersalud", "health_history_request", "health_evidence",
    "health_calendar",
}


def health_specs(answers=None, result=None):
    if answers is None or result is None:
        answers, result = health_fixture()
    return document_specs_m33_all(
        "CASE-HEALTH-LEGAL", "CO-SA-001", answers, result,
        PRODUCTS["CO-SA-001"], "2026-08-08T12:25:00-05:00", [],
    )


def visible(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


class HealthLegalFinalizeM330Tests(unittest.TestCase):
    def test_all_seven_health_documents_are_client_facing_and_governance_stays_pending(self):
        specs = health_specs()
        kinds = {spec.get("kind") for spec in specs if spec.get("kind") in EXPECTED_KINDS}
        self.assertEqual(kinds, EXPECTED_KINDS)
        for spec in specs:
            if spec.get("kind") not in EXPECTED_KINDS:
                continue
            self.assertTrue(spec.get("internal_controls_externalized"))
            self.assertTrue(spec.get("requires_human_review"))
            self.assertEqual(spec.get("legal_approval"), "pending")
            self.assertEqual(spec.get("qa_approval"), "pending")
            self.assertFalse(spec.get("released"))
            self.assertTrue(spec.get("critical_human_review"))
            body = visible(spec)
            self.assertNotIn("CONTROL DE USO, FUENTES Y REVISIÓN", body)
            self.assertNotIn("Composición jurídica profunda M33.0", spec.get("subtitle", ""))
            self.assertNotIn("decisión del motor", body.casefold())
            self.assertNotIn("nivel del motor", body.casefold())

    def test_prioritized_claim_uses_48_continuous_hours_not_generic_fifteen_day_term(self):
        specs = health_specs()
        petition = next(spec for spec in specs if spec.get("kind") == "health_petition")
        calendar = next(spec for spec in specs if spec.get("kind") == "health_calendar")
        self.assertIn("máximo 48 horas corridas", visible(petition).casefold())
        self.assertNotIn("15 días", visible(petition).casefold())
        self.assertIn("no usar como término rector del reclamo sectorial", visible(calendar).casefold())
        self.assertIn("horas corridas", visible(calendar).casefold())

    def test_vital_risk_never_turns_deadline_into_waiting_period(self):
        answers, result = health_fixture()
        answers, result = deepcopy(answers), deepcopy(result)
        answers["vital_risk"] = "Sí, peligro inminente para la vida"
        answers["priority"] = "Riesgo vital"
        result["calculation"]["priority"] = "vital"
        specs = health_specs(answers, result)
        diagnostic = next(spec for spec in specs if spec.get("kind") == "health_diagnostic")
        petition = next(spec for spec in specs if spec.get("kind") == "health_petition")
        self.assertIn("atención asistencial inmediata", visible(diagnostic).casefold())
        self.assertIn("máximo 24 horas corridas", visible(petition).casefold())
        self.assertIn("no puede condicionarse a autorización administrativa previa", visible(diagnostic).casefold())

    def test_simple_risk_keeps_72_hour_sector_rule(self):
        answers, result = health_fixture()
        answers, result = deepcopy(answers), deepcopy(result)
        answers["priority"] = "Riesgo simple"
        answers["vital_risk"] = "No reportado"
        result["calculation"]["priority"] = "simple"
        petition = next(spec for spec in health_specs(answers, result) if spec.get("kind") == "health_petition")
        self.assertIn("máximo 72 horas corridas", visible(petition).casefold())

    def test_supersalud_pqrd_is_not_presented_as_jurisdictional_demand_or_tutela_prerequisite(self):
        authority = next(spec for spec in health_specs() if spec.get("kind") == "health_supersalud")
        body = visible(authority).casefold()
        self.assertIn("no constituye automáticamente una demanda", body)
        self.assertIn("función jurisdiccional", body)
        self.assertIn("no obliga a suspender una tutela ni a esperar su respuesta", body)

    def test_existing_tutela_is_respected_and_calendar_has_no_automatic_pqrd_exhaustion(self):
        answers, result = health_fixture()
        answers = deepcopy(answers)
        answers["active_tutela"] = "Sí"
        specs = health_specs(answers, deepcopy(result))
        diagnostic = next(spec for spec in specs if spec.get("kind") == "health_diagnostic")
        calendar = next(spec for spec in specs if spec.get("kind") == "health_calendar")
        self.assertIn("revisarse el expediente judicial", visible(diagnostic).casefold())
        self.assertIn("sin agotamiento automático de pqrd", visible(calendar).casefold())

    def test_history_request_uses_current_reserve_access_and_retention_rules(self):
        history = next(spec for spec in health_specs() if spec.get("kind") == "health_history_request")
        body = visible(history).casefold()
        self.assertIn("documento privado, obligatorio y sometido a reserva", body)
        self.assertIn("obtener copia", body)
        self.assertIn("quince (15) años", body)
        self.assertIn("diez (10) días", body)
        self.assertNotIn("veinte (20) años", body)

    def test_reiteration_requires_receipt_and_does_not_invent_exact_hour_or_silence(self):
        reiteration = next(spec for spec in health_specs() if spec.get("kind") == "health_reiteration")
        body = visible(reiteration).casefold()
        self.assertIn("verificarse el acuse completo", body)
        self.assertIn("que no exista respuesta o actuación posterior", body)
        self.assertIn("incluida la hora cuando sea relevante", body)

    def test_all_health_outputs_pass_semantic_validation_and_docx_generation(self):
        specs = health_specs()
        with tempfile.TemporaryDirectory() as tmp:
            for spec in specs:
                if spec.get("kind") not in EXPECTED_KINDS:
                    continue
                report = validate_rendered_sections(spec["sections"], product_code="CO-SA-001")
                self.assertTrue(report["valid"], (spec.get("kind"), report["errors"]))
                target = Path(tmp) / f"{spec['kind']}.docx"
                build_docx(target, spec["title"], spec.get("subtitle", ""), [], spec["sections"], product_code="CO-SA-001", enforce_legal_standard=True)
                self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
