from __future__ import annotations

import unittest

from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_debt_legal_finalize import debt_stage_fixture
from tests.test_m33_0_procedural_wave import PRODUCTS


def specs_for(stage: str, *, zero_balance: bool = False) -> list[dict]:
    answers, result = debt_stage_fixture(stage, zero_balance=zero_balance)
    return document_specs_m33_all(
        "CASE-DEBT-POLISH",
        "CO-CD-004",
        answers,
        result,
        PRODUCTS["CO-CD-004"],
        "2026-08-08T08:45:00-05:00",
        [],
    )


def text(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


class DebtReleasePolishM330Tests(unittest.TestCase):
    def test_negative_adjustment_is_presented_as_reduction_not_negative_currency_syntax(self):
        current = specs_for("Enviar un cobro inicial")
        for kind in ("debt_diagnostic", "account_statement", "collection_letter"):
            spec = next(item for item in current if item.get("kind") == kind)
            visible = text(spec)
            self.assertNotIn("COP $-2.000.000", visible)
            self.assertIn("COP $2.000.000 · disminución del saldo", visible)

        account = next(item for item in current if item.get("kind") == "account_statement")
        account_text = text(account)
        self.assertIn("menos un ajuste neto de COP $2.000.000 que disminuye el saldo", account_text)
        self.assertNotIn("más ajustes netos COP $-2.000.000", account_text)

    def test_sparse_external_endings_receive_substantive_closure_blocks(self):
        initial = specs_for("Enviar un cobro inicial")
        account = next(item for item in initial if item.get("kind") == "account_statement")
        letter = next(item for item in initial if item.get("kind") == "collection_letter")
        self.assertIn("VII. CONTROL PREVIO A FORMALIZACIÓN", text(account))
        self.assertIn("VIII. RESULTADO Y ACTUALIZACIÓN DEL ESTADO", text(account))
        self.assertIn("VII. CONSTANCIA DE RADICACIÓN Y ANEXOS", text(letter))
        self.assertIn("VIII. EFECTO Y SEGUIMIENTO", text(letter))

        formal = specs_for("Acordar un plan de pago")
        agreement = next(item for item in formal if item.get("kind") == "payment_agreement")
        note = next(item for item in formal if item.get("kind") == "promissory_note")
        self.assertIn("DÉCIMA NOVENA: GASTOS, COSTOS Y HONORARIOS", text(agreement))
        self.assertIn("VIGÉSIMA: DOCUMENTOS INTEGRANTES Y CONCORDANCIA ECONÓMICA", text(agreement))
        self.assertIn("VIGÉSIMA PRIMERA: FIRMA, EJEMPLARES Y CONSERVACIÓN", text(agreement))
        self.assertIn("OCTAVA: CUSTODIA, DILIGENCIAMIENTO Y TRAZABILIDAD", text(note))

        receipt = next(item for item in specs_for("Registrar o seguir pagos") if item.get("kind") == "payment_receipt")
        self.assertIn("IV. CONSTANCIAS DEL RECEPTOR", text(receipt))
        self.assertIn("V. ARCHIVO Y TRAZABILIDAD", text(receipt))

        close = next(item for item in specs_for("Cerrar la obligación", zero_balance=True) if item.get("kind") == "settlement_certificate")
        self.assertIn("IV. VERIFICACIONES DE CIERRE", text(close))
        self.assertIn("V. CONSTANCIA DOCUMENTAL", text(close))

    def test_agreement_annex_does_not_force_redundant_page_break(self):
        agreement = next(item for item in specs_for("Acordar un plan de pago") if item.get("kind") == "payment_agreement")
        annex = next(
            section for section in agreement.get("sections") or []
            if str(section.get("heading") or "").startswith("ANEXO ECONÓMICO")
        )
        self.assertFalse(bool(annex.get("page_break_before")))

    def test_polish_preserves_governance_flags(self):
        for stage, zero in (
            ("Enviar un cobro inicial", False),
            ("Acordar un plan de pago", False),
            ("Registrar o seguir pagos", False),
            ("Cerrar la obligación", True),
        ):
            for spec in specs_for(stage, zero_balance=zero):
                if spec.get("internal_controls_externalized"):
                    self.assertEqual(spec.get("legal_approval"), "pending")
                    self.assertEqual(spec.get("qa_approval"), "pending")
                    self.assertFalse(spec.get("released"))

    def test_agreement_cost_clause_does_not_create_automatic_collection_fees(self):
        agreement = next(item for item in specs_for("Acordar un plan de pago") if item.get("kind") == "payment_agreement")
        body = text(agreement).casefold()
        self.assertIn("no se trasladan automáticamente", body)
        self.assertIn("no autoriza porcentajes automáticos de honorarios", body)


if __name__ == "__main__":
    unittest.main()
