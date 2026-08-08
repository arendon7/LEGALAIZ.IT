from __future__ import annotations

import unittest

from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_procedural_wave import PRODUCTS, labor_fixture


def calculation_spec() -> dict:
    answers, result = labor_fixture()
    specs = document_specs_m33_all(
        "CASE-M33-LABOR-PRESENTATION",
        "CO-LA-001",
        answers,
        result,
        PRODUCTS["CO-LA-001"],
        "2026-08-08T08:15:00-05:00",
        [],
    )
    return next(spec for spec in specs if spec.get("kind") == "calculation")


def section(spec: dict, fragment: str) -> dict:
    return next(item for item in spec.get("sections") or [] if fragment.casefold() in str(item.get("heading") or "").casefold())


class LaborPresentationFinalizeM330Tests(unittest.TestCase):
    def test_input_table_is_two_columns_with_separate_verification_controls(self):
        spec = calculation_spec()
        data = section(spec, "2. DATOS UTILIZADOS")
        self.assertTrue(data.get("table"))
        self.assertTrue(all(len(row) == 2 for row in data["table"]))
        self.assertGreaterEqual(len(data.get("bullets") or []), 3)

    def test_money_and_formula_tables_are_split_for_legibility(self):
        spec = calculation_spec()
        money = section(spec, "3. LIQUIDACIÓN REPRODUCIBLE")
        formulas = section(spec, "3.1 BASES, DÍAS Y FÓRMULAS")
        self.assertTrue(all(len(row) == 4 for row in money.get("table") or []))
        self.assertTrue(all(len(row) == 4 for row in formulas.get("table") or []))
        self.assertEqual(["Concepto", "Bruto", "Pagado", "Saldo"], money["table"][0])
        self.assertEqual(["Concepto", "Días / parámetro", "Base", "Fórmula o criterio"], formulas["table"][0])

    def test_reproducible_annex_does_not_force_a_sparse_page(self):
        spec = calculation_spec()
        annex = section(spec, "ANEXO No. 1 — TRAZA REPRODUCIBLE")
        self.assertFalse(bool(annex.get("page_break_before")))
        self.assertIn("misma revisión", " ".join(annex.get("paragraphs") or []))


if __name__ == "__main__":
    unittest.main()
