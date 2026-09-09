from __future__ import annotations

import unittest

from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_consumer_legal_finalize import MECHANISMS, consumer_route_fixture
from tests.test_m33_0_procedural_wave import PRODUCTS


def _specs(kind: str) -> list[dict]:
    answers, result = consumer_route_fixture(kind)
    return document_specs_m33_all(
        "CASE-CONSUMER-POLISH",
        "CO-CD-003",
        answers,
        result,
        PRODUCTS["CO-CD-003"],
        "2026-08-08T07:45:00-05:00",
        [],
    )


def _text(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


class ConsumerReleasePolishM330Tests(unittest.TestCase):
    def test_client_copy_avoids_internal_model_engine_language(self):
        for selected in MECHANISMS:
            with self.subTest(selected=selected):
                for spec in _specs(selected):
                    if not spec.get("internal_controls_externalized"):
                        continue
                    text = (_text(spec) + " " + str(spec.get("subtitle") or "")).casefold()
                    self.assertNotIn("fecha modelada", text)
                    self.assertNotIn("último día modelado", text)
                    self.assertNotIn("fecha supletiva modelada", text)
                    self.assertNotIn("el motor", text)
                    self.assertNotIn("del motor", text)
                    self.assertNotIn("no debe reescribirse", text)
                    self.assertNotIn("ese término no debe presentarse", text)
                    self.assertNotIn("cinco días hábiles cuando la norma", text)

    def test_periodic_debit_has_client_facing_five_day_wording(self):
        spec = next(item for item in _specs("recurring_debit_revocation") if item.get("kind") == "recurring_debit_revocation")
        text = _text(spec)
        self.assertIn("dentro de cinco (5) días y conservarse constancia verificable", text)
        self.assertIn("VII. CONSTANCIAS Y CIERRE", text)
        self.assertNotIn("token de cobro", text)

    def test_sparse_endings_receive_substantive_closure_sections(self):
        warranty_specs = _specs("warranty_claim")
        expected = {
            "consumer_mechanism_diagnosis": "VII. RESULTADO Y PRÓXIMAS ACTUACIONES",
            "consumer_deadline_calendar": "III. REGISTRO DE ACTUALIZACIONES",
            "consumer_evidence_matrix": "IV. CUSTODIA, PRIVACIDAD Y AUTENTICIDAD",
        }
        for kind, heading in expected.items():
            spec = next(item for item in warranty_specs if item.get("kind") == kind)
            self.assertIn(heading, _text(spec))

        route_expectations = {
            "payment_reversal_request": "VIII. ANEXOS Y CIERRE DE LA ACTUACIÓN",
            "recurring_debit_revocation": "VII. CONSTANCIAS Y CIERRE",
            "ecommerce_non_delivery_termination": "VIII. ANEXOS Y CIERRE",
        }
        for route, heading in route_expectations.items():
            spec = next(item for item in _specs(route) if item.get("kind") == route)
            self.assertIn(heading, _text(spec))

    def test_polish_does_not_change_governance_flags(self):
        for selected in MECHANISMS:
            with self.subTest(selected=selected):
                for spec in _specs(selected):
                    if spec.get("internal_controls_externalized"):
                        self.assertEqual(spec.get("legal_approval"), "pending")
                        self.assertEqual(spec.get("qa_approval"), "pending")
                        self.assertFalse(spec.get("released"))


if __name__ == "__main__":
    unittest.main()
