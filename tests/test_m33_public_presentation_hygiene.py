from __future__ import annotations

import json
import re
import unittest

from m33_public_presentation_hygiene import finalize_public_presentation_hygiene
from m33_document_presentation import split_internal_review_sections
from tests.test_m33_4_portfolio_source_coverage import _contract_compositions, _runtime_specs


_INTERNAL_STANDARD = re.compile(r"\bM33(?:\.\d+)?\b", re.IGNORECASE)
_INTERNAL_JARGON = re.compile(r"\bruleset\b", re.IGNORECASE)


class PublicPresentationHygieneTests(unittest.TestCase):
    def assert_public_text_is_clean(self, label: str, public) -> None:
        text = json.dumps(public, ensure_ascii=False)
        self.assertIsNone(_INTERNAL_STANDARD.search(text), f"{label}: fuga de estándar interno")
        self.assertIsNone(_INTERNAL_JARGON.search(text), f"{label}: fuga de jargon técnico")

    def test_known_m33_3_phrases_are_rewritten_without_touching_metadata(self):
        original = [{
            "kind": "sample",
            "calendar_standard": "M33.3",
            "sections": [{
                "heading": "CONTROL",
                "paragraphs": [
                    "M33.3 separa la permanencia del dato de la existencia de la obligación.",
                    "Control M33.3 de comunicación previa: envío soportado.",
                    "Trazabilidad M33.3: ruleset colombiano verificado al 10 de agosto de 2026.",
                ],
                "table": [["Fecha aplicable / corte M33.3", "Calendario nacional M33.3 · verificado 10 de agosto de 2026"]],
            }],
        }]
        cleaned = finalize_public_presentation_hygiene(original)
        self.assertEqual("M33.3", cleaned[0]["calendar_standard"])
        self.assert_public_text_is_clean("sample", cleaned[0]["sections"])
        self.assertIn("control temporal", json.dumps(cleaned, ensure_ascii=False).casefold())
        self.assertIn("calendario normativo colombiano", json.dumps(cleaned, ensure_ascii=False).casefold())

    def test_labor_engine_identifier_stays_out_of_client_facing_table(self):
        original = [{
            "kind": "labor_diagnostic",
            "engine_version": "M33-test",
            "sections": [{
                "heading": "4. RESULTADO PRELIMINAR DEL MOTOR",
                "table": [["Control", "Resultado"], ["Motor", "M33-test"]],
            }],
        }]
        cleaned = finalize_public_presentation_hygiene(original)
        self.assertEqual("M33-test", cleaned[0]["engine_version"])
        text = json.dumps(cleaned[0]["sections"], ensure_ascii=False)
        self.assertNotIn("M33-test", text)
        self.assertNotIn("RESULTADO PRELIMINAR DEL MOTOR", text)
        self.assertIn("RESULTADO PRELIMINAR DEL CÁLCULO", text)
        self.assertIn("Método de cálculo", text)
        self.assertIn("Liquidación determinística reproducible", text)

    def test_all_eleven_products_keep_internal_standard_out_of_deliverable_sections(self):
        covered = set()
        for code, composition in _contract_compositions().items():
            public, _internal = split_internal_review_sections(composition.get("sections") or [])
            self.assert_public_text_is_clean(code, public)
            covered.add(code)

        for code, (specs, kinds) in _runtime_specs().items():
            selected = [spec for spec in specs if str(spec.get("kind") or "") in kinds]
            self.assertTrue(selected, code)
            for spec in selected:
                public, _controls = split_internal_review_sections(spec.get("sections") or [])
                self.assert_public_text_is_clean(f"{code}/{spec.get('kind')}", public)
            covered.add(code)

        self.assertEqual(11, len(covered))


if __name__ == "__main__":
    unittest.main()
