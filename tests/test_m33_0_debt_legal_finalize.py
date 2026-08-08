from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from document_standard_v33 import validate_rendered_sections
from docx_builder import build_docx
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_procedural_wave import PRODUCTS, debt_fixture


def debt_stage_fixture(stage: str, *, zero_balance: bool = False, reconciled: bool = True):
    answers, result = debt_fixture()
    answers["package_stage"] = stage
    answers["promissory_note_required"] = "Sí"
    answers["promissory_note_blank_spaces"] = "Sí"
    answers["last_payment_date"] = "2026-10-15"
    answers["last_payment_amount"] = 2_000_000
    answers["balance_before_payment"] = 26_000_000
    answers["balance_after_payment"] = 24_000_000

    calc = result["calculation"]
    calc["balance_reconciled"] = reconciled
    calc["agreement_reconciled"] = reconciled
    if not reconciled:
        calc["balance_difference"] = 1_000_000
        calc["agreement_difference"] = 1_000_000
    if zero_balance:
        answers["partial_payments_total"] = 34_000_000
        answers["reported_balance"] = 0
        answers["agreement_total"] = 0
        calc["partial_payments_total"] = 34_000_000
        calc["expected_principal_balance"] = 2_000_000
        calc["other_charges"] = -2_000_000
        calc["explained_balance"] = 0
        calc["reported_balance"] = 0
        calc["balance_difference"] = 0
        calc["balance_reconciled"] = True
        calc["agreement_total"] = 0
        calc["agreement_difference"] = 0
        calc["agreement_reconciled"] = True
    return answers, result


def specs_for(stage: str, *, zero_balance: bool = False, reconciled: bool = True, risk: str = "yellow") -> list[dict]:
    answers, result = debt_stage_fixture(stage, zero_balance=zero_balance, reconciled=reconciled)
    result["risk"] = risk
    return document_specs_m33_all(
        "CASE-DEBT-M33",
        "CO-CD-004",
        answers,
        result,
        PRODUCTS["CO-CD-004"],
        "2026-08-08T08:30:00-05:00",
        [],
    )


def text(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


def strict_render(specs: list[dict]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for index, spec in enumerate(specs, 1):
            report = validate_rendered_sections(spec["sections"], product_code="CO-CD-004")
            if not report["valid"]:
                raise AssertionError((spec["kind"], report["errors"]))
            target = Path(tmp) / f"{index:02d}_{spec['kind']}.docx"
            build_docx(
                target,
                spec["title"],
                spec.get("subtitle", ""),
                [],
                spec["sections"],
                product_code="CO-CD-004",
                enforce_legal_standard=True,
                append_default_control=not bool(spec.get("internal_controls_externalized")),
            )
            if not target.is_file():
                raise AssertionError(f"No se generó {spec['kind']}")


class DebtLegalFinalizeM330Tests(unittest.TestCase):
    def test_stage_selection_is_preserved_and_all_routes_are_available(self):
        expectations = {
            "Enviar un cobro inicial": {"collection_letter"},
            "Negociar una solución": {"payment_agreement", "payment_schedule"},
            "Acordar un plan de pago": {"payment_agreement", "payment_schedule", "promissory_note", "instruction_letter"},
            "Registrar o seguir pagos": {"payment_receipt"},
            "Cerrar la obligación": {"settlement_certificate"},
        }
        common = {"debt_diagnostic", "account_statement", "collection_evidence_matrix"}
        for stage, expected in expectations.items():
            with self.subTest(stage=stage):
                current = specs_for(stage, zero_balance=stage == "Cerrar la obligación")
                kinds = {spec["kind"] for spec in current}
                self.assertTrue(common.issubset(kinds))
                self.assertTrue(expected.issubset(kinds))

    def test_all_stage_outputs_pass_semantic_validation_and_docx_generation(self):
        for stage in (
            "Enviar un cobro inicial",
            "Negociar una solución",
            "Acordar un plan de pago",
            "Registrar o seguir pagos",
            "Cerrar la obligación",
        ):
            with self.subTest(stage=stage):
                strict_render(specs_for(stage, zero_balance=stage == "Cerrar la obligación"))

    def test_client_copy_externalizes_internal_controls_and_metadata_language(self):
        for spec in specs_for("Acordar un plan de pago"):
            if spec.get("kind") not in {
                "debt_diagnostic", "account_statement", "collection_evidence_matrix",
                "payment_agreement", "payment_schedule", "promissory_note", "instruction_letter",
            }:
                continue
            self.assertTrue(spec.get("internal_controls_externalized"))
            self.assertEqual(spec.get("legal_approval"), "pending")
            self.assertEqual(spec.get("qa_approval"), "pending")
            self.assertFalse(spec.get("released"))
            visible = (spec.get("title", "") + " " + spec.get("subtitle", "") + " " + text(spec)).casefold()
            self.assertNotIn("control de uso, fuentes y revisión", visible)
            self.assertNotIn("candidato sujeto a revisión jurídica y qa", visible)
            self.assertNotIn("composición jurídica profunda m33.0", visible)
            self.assertNotIn("producto': 'co-cd-004", visible)

    def test_formalization_reconciles_same_base_amount_without_reusing_original_principal_in_note(self):
        current = specs_for("Acordar un plan de pago")
        agreement = next(spec for spec in current if spec["kind"] == "payment_agreement")
        schedule = next(spec for spec in current if spec["kind"] == "payment_schedule")
        note = next(spec for spec in current if spec["kind"] == "promissory_note")
        instructions = next(spec for spec in current if spec["kind"] == "instruction_letter")
        combined = " ".join(text(spec) for spec in (agreement, schedule, note, instructions))
        self.assertIn("26.000.000", combined)
        self.assertNotIn("36.000.000", text(note))
        self.assertIn("A la orden de", text(note))
        self.assertIn("promete pagar incondicionalmente", text(note))

    def test_interest_is_not_falsely_presented_as_fully_amortized_or_officially_certified(self):
        current = specs_for("Acordar un plan de pago")
        agreement = next(spec for spec in current if spec["kind"] == "payment_agreement")
        schedule = next(spec for spec in current if spec["kind"] == "payment_schedule")
        diagnostic = next(spec for spec in current if spec["kind"] == "debt_diagnostic")
        combined = (text(agreement) + " " + text(schedule) + " " + text(diagnostic)).casefold()
        self.assertIn("no puede asumirse que las cuotas ya incorporan intereses", combined)
        self.assertIn("parámetro demostrativo", combined)
        self.assertIn("superintendencia financiera", combined)
        self.assertIn("no se pacta anatocismo automático", text(agreement).casefold())

    def test_agreement_has_dual_signatures_and_does_not_make_representative_personally_liable(self):
        agreement = next(spec for spec in specs_for("Acordar un plan de pago") if spec["kind"] == "payment_agreement")
        signatures = [section for section in agreement["sections"] if section.get("_type") == "signature"]
        self.assertEqual(len(signatures), 1)
        self.assertEqual(len(signatures[0].get("parties") or []), 2)
        agreement_text = text(agreement).casefold()
        self.assertIn("no transforma al representante en deudor", agreement_text)
        self.assertIn("firma en calidad representativa", agreement_text)

    def test_novation_clause_preserves_third_party_guarantee_warning(self):
        agreement = next(spec for spec in specs_for("Acordar un plan de pago") if spec["kind"] == "payment_agreement")
        agreement_text = text(agreement).casefold()
        self.assertIn("no constituye novación por sí sola", agreement_text)
        self.assertIn("fiadores, prendas, hipotecas u otras garantías de terceros", agreement_text)
        self.assertIn("consentimiento expreso", agreement_text)

    def test_blank_note_instructions_are_restrictive_and_traceable(self):
        current = specs_for("Acordar un plan de pago")
        instructions = next(spec for spec in current if spec["kind"] == "instruction_letter")
        body = text(instructions).casefold()
        self.assertIn("saldo realmente insoluto", body)
        self.assertIn("fecha real de la actuación", body)
        self.assertIn("no se incluyen intereses futuros no causados", body)
        self.assertIn("cambiar identidad", body)
        self.assertIn("antedatar", body)

    def test_unreconciled_balance_is_visibly_blocked_from_formalization(self):
        current = specs_for("Acordar un plan de pago", reconciled=False)
        agreement = next(spec for spec in current if spec["kind"] == "payment_agreement")
        body = text(agreement)
        self.assertIn("BLOQUEO DE FORMALIZACIÓN", body)
        self.assertIn("no es apta para firma como reconocimiento de deuda", body)

    def test_collection_law_2300_is_conditional_not_assumed_for_every_company_debt(self):
        letter = next(spec for spec in specs_for("Enviar un cobro inicial") if spec["kind"] == "collection_letter")
        body = text(letter).casefold()
        self.assertIn("cuando el destinatario y la gestión se encuentren dentro del ámbito", body)
        self.assertIn("no se presume para toda relación empresarial", body)
        self.assertIn("no es una demanda", body)

    def test_positive_balance_closure_is_not_labeled_as_paz_y_salvo(self):
        certificate = next(spec for spec in specs_for("Cerrar la obligación", zero_balance=False) if spec["kind"] == "settlement_certificate")
        body = text(certificate)
        self.assertIn("CONSTANCIA DE CIERRE PENDIENTE — NO ES PAZ Y SALVO", body)
        self.assertIn("Cierre bloqueado", body)

    def test_zero_balance_closure_can_be_presented_as_conditioned_paz_y_salvo(self):
        certificate = next(spec for spec in specs_for("Cerrar la obligación", zero_balance=True) if spec["kind"] == "settlement_certificate")
        body = text(certificate).casefold()
        self.assertIn("paz y salvo y constancia de cierre", body)
        self.assertIn("saldo cero acreditado preliminarmente", body)
        self.assertIn("cancelar, devolver o inutilizar jurídicamente el pagaré", body)

    def test_red_case_preserves_historical_risk_gate(self):
        current = specs_for("Acordar un plan de pago", risk="red")
        self.assertTrue(current)
        self.assertTrue(all(not spec.get("internal_controls_externalized") for spec in current))


if __name__ == "__main__":
    unittest.main()
