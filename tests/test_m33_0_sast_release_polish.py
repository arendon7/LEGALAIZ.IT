from __future__ import annotations

import unittest

from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_wave3 import PRODUCTS, sast_fixture


def _specs():
    answers, result = sast_fixture()
    return document_specs_m33_all(
        "CASE-SAST-POLISH",
        "CO-TR-001",
        answers,
        result,
        PRODUCTS["CO-TR-001"],
        "2026-08-08T15:30:00-05:00",
        [],
    )


def _visible(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


class SastReleasePolishM330Tests(unittest.TestCase):
    def test_operation_rule_has_natural_sentence_boundary(self):
        report = next(spec for spec in _specs() if spec.get("kind") == "sast_report")
        body = _visible(report)
        self.assertNotIn("señalización, Cuando el equipo", body)
        self.assertIn("evidencia de señalización. Cuando el equipo mide velocidad", body)

    def test_unverified_capacity_is_not_printed_inside_sast_signature_blocks(self):
        specs = _specs()
        signatures = []
        for spec in specs:
            for section in spec.get("sections") or []:
                if isinstance(section, dict) and str(section.get("_type") or "") == "signature":
                    signatures.append((spec.get("kind"), section))
        self.assertTrue(signatures)
        for kind, signature in signatures:
            for party in signature.get("parties") or []:
                self.assertNotEqual(str(party.get("role") or "").casefold(), "calidad por acreditar", kind)
        inspection = next(spec for spec in specs if spec.get("kind") == "sast_inspection")
        self.assertNotIn("Calidad por acreditar", _visible(inspection))


if __name__ == "__main__":
    unittest.main()
