from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from document_standard_v33 import validate_rendered_sections
from docx_builder import build_docx
from m33_procedural_runtime import document_specs_m33_runtime


PRODUCTS = {
    "CO-LA-001": {"code": "CO-LA-001", "title": "Liquidación laboral y reclamación"},
    "CO-CD-001": {"code": "CO-CD-001", "title": "Hábeas data financiero"},
    "CO-CD-003": {"code": "CO-CD-003", "title": "Protección al consumidor"},
    "CO-CD-004": {"code": "CO-CD-004", "title": "Cobro y acuerdo de pago"},
}


def _strict_render_all(code: str, specs: list[dict]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for index, spec in enumerate(specs, 1):
            report = validate_rendered_sections(spec["sections"], product_code=code)
            if not report["valid"]:
                raise AssertionError((spec["kind"], report["errors"]))
            path = Path(tmp) / f"{index:02d}_{spec['kind']}.docx"
            build_docx(
                path,
                spec["title"],
                spec.get("subtitle", ""),
                [],
                spec["sections"],
                product_code=code,
                enforce_legal_standard=True,
            )
            if not path.is_file():
                raise AssertionError(f"No se generó {spec['kind']}")


def labor_fixture():
    answers = {
        "employee_name": "Laura Isabel Gómez Pérez",
        "employee_id": "1.000.000.202",
        "employer_name": "Servicios Administrativos Demo S.A.S.",
        "start_date": "2026-01-01",
        "end_date": "2026-07-31",
        "contract_type": "Término indefinido",
        "termination": "Terminación unilateral sin justa causa informada",
        "monthly_salary": 3_000_000,
        "transport_aid": 249_095,
        "prior_paid_total": 0,
        "stability_protection": "No reportada",
    }
    line_items = [
        {"key": "cesantias", "label": "Cesantías", "gross": 1_895_305, "prior_paid": 0, "net": 1_895_305, "formula": "base × días ÷ 360"},
        {"key": "intereses_cesantias", "label": "Intereses a las cesantías", "gross": 132_671, "prior_paid": 0, "net": 132_671, "formula": "cesantías × tasa × días ÷ 360"},
        {"key": "prima", "label": "Prima de servicios", "gross": 270_758, "prior_paid": 0, "net": 270_758, "formula": "base × días ÷ 360"},
        {"key": "vacaciones", "label": "Vacaciones", "gross": 875_000, "prior_paid": 0, "net": 875_000, "formula": "salario × días ÷ 720"},
        {"key": "indemnizacion", "label": "Indemnización", "gross": 3_000_000, "prior_paid": 0, "net": 3_000_000, "formula": "30 días de salario bajo el supuesto informado"},
    ]
    result = {
        "risk": "yellow",
        "calculation": {
            "engine_version": "M33-test",
            "link_days": 210,
            "cesantias_days": 210,
            "prima_days": 30,
            "vacation_pending_days": 210,
            "indemnity_days": 30,
            "cesantias_base": 3_249_095,
            "prima_base": 3_249_095,
            "vacation_base": 3_000_000,
            "indemnity_base": 3_000_000,
            "gross_total": 6_173_734,
            "prior_paid_total": 0,
            "total": 6_173_734,
            "line_items": line_items,
            "assumptions": ["La prima del primer semestre fue pagada y soportada."],
            "exclusions": ["La sanción moratoria no se suma automáticamente."],
            "issues": [],
        },
    }
    return answers, result


def habeas_fixture():
    answers = {
        "data_subject_name": "Andrés Felipe Morales Ruiz",
        "data_subject_id": "1.000.000.701",
        "source_name": "Crédito Comercial Demostrativo S.A.S.",
        "operator_name": "Central de Información Crediticia Demo S.A.",
        "request_mode": "Corregir o retirar información negativa",
        "facts_detail": "La obligación fue pagada y el titular solicita verificar permanencia, actualización y comunicación previa.",
        "mora_start_date": "2023-10-15",
        "payment_or_extinction_date": "2024-01-15",
        "report_date": "2023-11-10",
        "report_discovery_date": "2026-08-01",
        "filing_date": "2026-08-07",
        "prior_claim": "Sí",
        "prior_claim_date": "2026-07-20",
        "prior_claim_radicado": "HD-DEMO-001",
        "prior_claim_result": "Sin respuesta de fondo",
        "identity_theft": "Sí",
        "identity_theft_discovery_date": "2026-08-01",
        "identity_theft_obligation": "Producto adicional desconocido por el titular",
        "identity_theft_report_detail": "Se solicita investigación especializada y preservación de evidencia.",
        "authority_escalation": "Sí",
        "competent_authority": "Superintendencia de Industria y Comercio",
    }
    result = {
        "risk": "yellow",
        "calculation": {
            "reference_date": "2026-08-07",
            "filing_date": "2026-08-07",
            "preliminary_due_date": "2026-08-31",
            "preliminary_due_with_extension": "2026-09-10",
            "claim_legend_due_date": "2026-08-11",
            "mora_start_date": "2023-10-15",
            "payment_or_extinction_date": "2024-01-15",
            "mora_duration_days": 92,
            "paid_negative_expiry_preliminary": "2024-07-17",
            "unpaid_negative_expiry_preliminary": "2031-10-15",
            "prior_claim_date": "2026-07-20",
            "prior_preliminary_due_date": "2026-08-11",
            "prior_max_due_date": "2026-08-21",
            "term_category": "Reclamo especial de hábeas data",
            "law_2573_status_at_reference": "Vigencia parcial; verificar disposición concreta",
            "law_2573_immediate_scope": "Aplicar únicamente las disposiciones efectivamente vigentes a la fecha del caso",
            "issues": [],
            "assumptions": [],
        },
    }
    return answers, result


def consumer_fixture(selected="warranty_claim"):
    answers = {
        "consumer_name": "Valentina María Suárez Gómez",
        "consumer_id": "43.000.801",
        "supplier_name": "Tecnología Digital Demostrativa S.A.S.",
        "product_or_service": "Computador portátil NovaBook Pro 14",
        "request_mode": "Garantía legal",
        "purchase_date": "2026-07-02",
        "delivery_date": "2026-07-04",
        "amount": 4_800_000,
        "defect_detail": "Apagado repentino y batería no reconocida después de una primera reparación.",
        "facts_detail": "La falla reapareció pocos días después de la intervención técnica.",
        "repeated_failure": "Sí",
        "purchase_channel": "Comercio electrónico",
        "withdrawal_exception": "No",
        "reversal_cause": "Producto defectuoso",
        "promised_delivery_date": "2026-07-04",
        "delivery_status": "Entregado",
    }
    result = {
        "risk": "yellow",
        "calculation": {
            "selected_document": selected,
            "mechanism_eligibility": {
                "warranty_claim": True,
                "withdrawal_notice": False,
                "payment_reversal_request": False,
                "recurring_debit_revocation": False,
                "ecommerce_non_delivery_termination": False,
            },
            "issues": [],
            "assumptions": [],
        },
    }
    return answers, result


def debt_fixture(stage="Acordar un plan de pago"):
    answers = {
        "package_stage": stage,
        "creditor_name": "Insumos Empresariales Andinos S.A.S.",
        "creditor_id": "900.000.901-1",
        "debtor_name": "Comercializadora Horizonte S.A.S.",
        "debtor_id": "900.000.902-2",
        "document_date": "2026-08-15",
        "principal": 36_000_000,
        "partial_payments_total": 8_000_000,
        "other_charges": -2_000_000,
        "reported_balance": 26_000_000,
        "agreement_total": 26_000_000,
        "installments": 13,
        "first_payment_date": "2026-09-15",
        "frequency": "Mensual",
        "interest_agreed": "Sí",
        "interest_rate": 18,
        "interest_period": "E.A.",
        "interest_modality": "consumo y ordinario",
        "promissory_note_required": "Sí",
        "promissory_note_blank_spaces": "Sí",
        "maturity_form": "Vencimientos ciertos sucesivos con aceleración condicionada",
        "agreement_signed": "Sí",
        "signer_role": "Representante legal",
        "has_existing_security": "No",
        "credit_reporting": "No",
        "data_authorization": "Sí",
    }
    schedule = [
        {"number": number, "due_date": f"2026-{9 + number - 1:02d}-15" if number <= 4 else f"2027-{number - 4:02d}-15", "amount": 2_000_000, "status": "Pendiente"}
        for number in range(1, 14)
    ]
    result = {
        "risk": "yellow",
        "calculation": {
            "principal": 36_000_000,
            "partial_payments_total": 8_000_000,
            "expected_principal_balance": 28_000_000,
            "other_charges": -2_000_000,
            "explained_balance": 26_000_000,
            "reported_balance": 26_000_000,
            "balance_difference": 0,
            "balance_reconciled": True,
            "agreement_total": 26_000_000,
            "agreement_difference": 0,
            "agreement_reconciled": True,
            "installments": 13,
            "first_payment_date": "2026-09-15",
            "frequency": "Mensual",
            "interest_rate_input": 18,
            "interest_period": "E.A.",
            "interest_modality": "consumo y ordinario",
            "effective_annual_rate": 18,
            "maximum_reference_ea": 25,
            "interest_valid_from": "2026-08-01",
            "interest_valid_to": "2026-08-31",
            "interest_resolution": "Parámetro demostrativo; revalidar en producción",
            "payment_schedule": {"rows": schedule, "total": 26_000_000, "reconciled": True, "warnings": []},
            "issues": [],
            "assumptions": [],
        },
    }
    return answers, result


class ProceduralWaveM330Tests(unittest.TestCase):
    def specs(self, code: str, answers: dict, result: dict):
        return document_specs_m33_runtime(
            "CASE-M33",
            code,
            answers,
            result,
            PRODUCTS[code],
            "2026-08-07T15:00:00-05:00",
            [],
        )

    def test_labor_package_contains_seven_coordinated_documents_and_renders_strict(self):
        answers, result = labor_fixture()
        specs = self.specs("CO-LA-001", answers, result)
        kinds = {spec["kind"] for spec in specs}
        self.assertGreaterEqual(len(kinds), 7)
        self.assertTrue({"calculation", "claim", "evidence_matrix", "labor_diagnostic", "labor_support_request", "labor_deadline_calendar", "labor_evidence_index"}.issubset(kinds))
        calculation = next(spec for spec in specs if spec["kind"] == "calculation")
        text = " ".join(str(section) for section in calculation["sections"])
        self.assertIn("6.173.734", text)
        _strict_render_all("CO-LA-001", specs)

    def test_habeas_package_sanitizes_legacy_signature_lines_and_keeps_identity_theft_conditional(self):
        answers, result = habeas_fixture()
        specs = self.specs("CO-CD-001", answers, result)
        kinds = {spec["kind"] for spec in specs}
        self.assertIn("identity_theft_protocol", kinds)
        self.assertIn("habeas_authority_escalation", kinds)
        plain = " ".join(str(spec["sections"]) for spec in specs)
        self.assertNotIn("________", plain)
        self.assertIn("Vigencia parcial", plain)
        _strict_render_all("CO-CD-001", specs)

    def test_consumer_package_emits_only_selected_substantive_mechanism(self):
        answers, result = consumer_fixture("warranty_claim")
        specs = self.specs("CO-CD-003", answers, result)
        kinds = {spec["kind"] for spec in specs}
        self.assertIn("warranty_claim", kinds)
        self.assertNotIn("withdrawal_notice", kinds)
        self.assertNotIn("payment_reversal_request", kinds)
        self.assertNotIn("recurring_debit_revocation", kinds)
        self.assertNotIn("ecommerce_non_delivery_termination", kinds)
        self.assertEqual(sum(kind in {"warranty_claim", "withdrawal_notice", "payment_reversal_request", "recurring_debit_revocation", "ecommerce_non_delivery_termination"} for kind in kinds), 1)
        _strict_render_all("CO-CD-003", specs)

    def test_debt_agreement_package_reconciles_note_and_instructions_under_same_amount(self):
        answers, result = debt_fixture()
        specs = self.specs("CO-CD-004", answers, result)
        kinds = {spec["kind"] for spec in specs}
        self.assertTrue({"debt_diagnostic", "account_statement", "collection_evidence_matrix", "payment_agreement", "payment_schedule", "promissory_note", "instruction_letter"}.issubset(kinds))
        combined = " ".join(str(spec["sections"]) for spec in specs if spec["kind"] in {"payment_agreement", "payment_schedule", "promissory_note"})
        self.assertIn("26.000.000", combined)
        self.assertNotIn("36.000.000", " ".join(str(spec["sections"]) for spec in specs if spec["kind"] == "promissory_note"))
        _strict_render_all("CO-CD-004", specs)

    def test_red_case_is_not_recomposed(self):
        answers, result = consumer_fixture("warranty_claim")
        result["risk"] = "red"
        specs = self.specs("CO-CD-003", answers, result)
        self.assertTrue(all(spec.get("document_standard") != "M33.0" for spec in specs))


if __name__ == "__main__":
    unittest.main()
