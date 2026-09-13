from __future__ import annotations

import unittest

from m33_wave3_runtime import document_specs_m33_all
from test_m33_0_procedural_wave import PRODUCTS, labor_fixture


class LaborLegacyTransportM334Tests(unittest.TestCase):
    def _specs(self, transport_aid):
        answers, result = labor_fixture()
        answers["transport_aid"] = transport_aid
        return document_specs_m33_all(
            "CASE-M334-LABOR-LEGACY",
            "CO-LA-001",
            answers,
            result,
            PRODUCTS["CO-LA-001"],
            "2026-08-10T23:20:00-05:00",
            [],
        )

    def test_historical_no_value_does_not_break_document_generation(self):
        specs = self._specs("No")
        labor_specs = [spec for spec in specs if spec.get("legal_source_standard_m334") == "M33.4"]
        self.assertEqual(7, len(labor_specs))
        for spec in labor_specs:
            self.assertIs(False, spec["legal_source_scope_m334"]["transport_aid_used"])

    def test_historical_yes_value_is_normalized_without_numeric_cast(self):
        specs = self._specs("Sí")
        labor_specs = [spec for spec in specs if spec.get("legal_source_standard_m334") == "M33.4"]
        self.assertEqual(7, len(labor_specs))
        for spec in labor_specs:
            self.assertIs(True, spec["legal_source_scope_m334"]["transport_aid_used"])

    def test_unknown_legacy_text_is_explicitly_indeterminate(self):
        specs = self._specs("Por verificar")
        labor_specs = [spec for spec in specs if spec.get("legal_source_standard_m334") == "M33.4"]
        self.assertEqual(7, len(labor_specs))
        for spec in labor_specs:
            self.assertIsNone(spec["legal_source_scope_m334"]["transport_aid_used"])


if __name__ == "__main__":
    unittest.main()
