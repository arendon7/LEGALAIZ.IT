from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from docx_builder import build_docx
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_procedural_wave import PRODUCTS, labor_fixture


def labor_specs():
    answers, result = labor_fixture()
    specs = document_specs_m33_all(
        "CASE-M33-LABOR-FINAL",
        "CO-LA-001",
        answers,
        result,
        PRODUCTS["CO-LA-001"],
        "2026-08-08T08:00:00-05:00",
        [],
    )
    return answers, result, specs


def spec_of(specs: list[dict], kind: str) -> dict:
    return next(spec for spec in specs if spec.get("kind") == kind)


class LaborProceduralFinalizeM330Tests(unittest.TestCase):
    def test_calculation_has_one_reconciled_data_layer(self):
        _, _, specs = labor_specs()
        calculation = spec_of(specs, "calculation")
        text = json.dumps(calculation, ensure_ascii=False)
        self.assertIn("COP $6.173.734", text)
        self.assertIn("Laura Isabel Gómez Pérez", text)
        self.assertIn("210", text)
        self.assertIn("ANEXO No. 1 — TRAZA REPRODUCIBLE DE ESTA LIQUIDACIÓN", text)
        self.assertNotIn("ANEXO No. 1 — MATRICES DEL MOTOR DE LIQUIDACIÓN", text)
        self.assertNotIn("No informado", text)
        self.assertNotIn("Dato pendiente de verificación", text)
        self.assertNotIn("0 días", text)

    def test_calculation_reconciles_gross_prior_payments_and_net(self):
        _, result, specs = labor_specs()
        calculation = spec_of(specs, "calculation")
        text = json.dumps(calculation, ensure_ascii=False)
        c = result["calculation"]
        self.assertEqual(c["gross_total"] - c["prior_paid_total"], c["total"])
        self.assertIn("COP $6.173.734 - COP $0 = COP $6.173.734", text)
        self.assertIn("Número de líneas calculadas", text)
        self.assertIn('"5"', text)

    def test_claim_individualizes_amounts_and_prescription_control(self):
        _, _, specs = labor_specs()
        claim = spec_of(specs, "claim")
        text = json.dumps(claim, ensure_ascii=False)
        self.assertIn("COP $6.173.734", text)
        self.assertIn("artículo 488", text)
        self.assertIn("artículo 489", text)
        self.assertIn("prueba verificable de contenido, fecha de envío", text)
        self.assertIn("La sola preparación o envío de este documento no permite afirmar que el efecto interruptivo se produjo", text)
        self.assertIn("pagar oportunamente los valores que sean reconocidos como ciertos y debidos", text.casefold())

    def test_visible_subtitles_are_client_facing(self):
        _, _, specs = labor_specs()
        for kind in ("calculation", "claim"):
            subtitle = str(spec_of(specs, kind).get("subtitle") or "")
            self.assertNotIn("Composición jurídica profunda", subtitle)
            self.assertNotIn("Modelo madurado", subtitle)
            self.assertNotIn("M33.0", subtitle)

    def test_internal_control_keeps_legal_sources(self):
        _, _, specs = labor_specs()
        calculation = spec_of(specs, "calculation")
        controls = [section for section in calculation["sections"] if section.get("_type") == "control"]
        self.assertEqual(1, len(controls))
        internal = json.dumps(controls[0], ensure_ascii=False)
        self.assertIn("Código Sustantivo del Trabajo", internal)
        self.assertIn("Ley 52 de 1975", internal)
        self.assertIn("Ley 2466 de 2025", internal)

    def test_calculation_and_claim_render_strictly(self):
        _, _, specs = labor_specs()
        with tempfile.TemporaryDirectory() as tmp:
            for kind in ("calculation", "claim"):
                spec = spec_of(specs, kind)
                path = Path(tmp) / f"{kind}.docx"
                build_docx(
                    path,
                    spec["title"],
                    spec.get("subtitle", ""),
                    [],
                    spec["sections"],
                    product_code="CO-LA-001",
                    enforce_legal_standard=True,
                )
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()
