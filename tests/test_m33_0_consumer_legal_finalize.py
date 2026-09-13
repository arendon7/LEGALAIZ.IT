from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from document_standard_v33 import validate_rendered_sections
from docx_builder import build_docx
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_procedural_wave import PRODUCTS, consumer_fixture


MECHANISMS = {
    "warranty_claim": "Garantía legal",
    "withdrawal_notice": "Derecho de retracto",
    "payment_reversal_request": "Reversión del pago",
    "recurring_debit_revocation": "Revocación de débito periódico",
    "ecommerce_non_delivery_termination": "Terminación por falta de entrega",
}


def consumer_route_fixture(kind: str):
    answers, result = consumer_fixture("warranty_claim")
    answers = dict(answers)
    result = {**result, "calculation": dict(result.get("calculation") or {})}
    c = result["calculation"]

    answers.update({
        "consumer_relationship": "Sí",
        "request_mode": MECHANISMS[kind],
        "purchase_channel": "Internet o aplicación",
        "electronic_payment": "Sí",
        "payment_instrument": "Débito automático",
        "direct_claim_date": "2026-08-07",
        "withdrawal_exercised_date": "2026-08-05",
        "reversal_event_date": "2026-08-01",
        "debit_revocation_date": "2026-08-07",
    })
    c.update({
        "selected_document": kind,
        "direct_claim_due_date": "2026-08-28",
        "withdrawal_due_date": "2026-08-11",
        "withdrawal_exercised_date": "2026-08-05",
        "withdrawal_refund_due_date": "2026-08-20",
        "reversal_event_date": "2026-08-01",
        "reversal_request_due_date": "2026-08-07",
        "reversal_effective_due_date": "2026-08-28",
        "default_ecommerce_delivery_due_date": "2026-08-01",
        "ecommerce_refund_due_date": "2026-08-22",
        "periodic_debit_control_due_date": "2026-08-14",
        "holiday_calendar_applied": False,
        "deadline_is_preliminary": True,
        "mechanism_eligibility": {
            "warranty": kind == "warranty_claim",
            "withdrawal": kind == "withdrawal_notice",
            "reversal": kind == "payment_reversal_request",
            "periodic_debit": kind == "recurring_debit_revocation",
            "non_delivery": kind == "ecommerce_non_delivery_termination",
        },
    })

    if kind == "ecommerce_non_delivery_termination":
        answers.update({
            "delivery_date": "",
            "promised_delivery_date": "2026-07-20",
            "delivery_status": "No entregado",
            "facts_detail": "El pedido no fue entregado dentro del plazo prometido y continúa sin constancia de disponibilidad cierta.",
        })
    elif kind == "withdrawal_notice":
        answers.update({
            "delivery_date": "2026-08-01",
            "withdrawal_exception": "No",
            "facts_detail": "La persona consumidora decidió desistir dentro del término legal y el bien se conserva en condiciones de restitución.",
        })
    elif kind == "payment_reversal_request":
        answers.update({
            "reversal_cause": "Producto defectuoso",
            "facts_detail": "La persona consumidora solicita reversión por producto defectuoso y conserva la operación y la queja para radicación coordinada.",
        })
    elif kind == "recurring_debit_revocation":
        answers.update({
            "product_or_service": "Suscripción digital con débito periódico",
            "facts_detail": "La persona titular decidió revocar la autorización de cobros periódicos y requiere prueba del cese.",
        })
    return answers, result


def _specs(kind: str):
    answers, result = consumer_route_fixture(kind)
    specs = document_specs_m33_all(
        "CASE-CONSUMER-M33",
        "CO-CD-003",
        answers,
        result,
        PRODUCTS["CO-CD-003"],
        "2026-08-08T07:30:00-05:00",
        [],
    )
    return answers, result, specs


def _public_text(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


def _docx_text(path: Path) -> str:
    texts: list[str] = []
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            root = ET.fromstring(archive.read(name))
            for node in root.iter():
                if node.tag.endswith("}t") and node.text:
                    texts.append(node.text)
    return " ".join(texts)


class ConsumerLegalFinalizeM330Tests(unittest.TestCase):
    def test_each_case_emits_exactly_one_substantive_mechanism(self):
        for selected in MECHANISMS:
            with self.subTest(selected=selected):
                _, _, specs = _specs(selected)
                kinds = {spec.get("kind") for spec in specs}
                emitted = kinds & set(MECHANISMS)
                self.assertEqual(emitted, {selected})
                self.assertTrue({"consumer_mechanism_diagnosis", "consumer_evidence_matrix", "consumer_deadline_calendar"}.issubset(kinds))

    def test_warranty_repeated_failure_preserves_consumer_choice_without_inventing_remedy(self):
        _, _, specs = _specs("warranty_claim")
        spec = next(item for item in specs if item.get("kind") == "warranty_claim")
        text = _public_text(spec)
        self.assertIn("escoger entre una nueva reparación", text)
        self.assertIn("no la inventa ni la presume", text)
        self.assertIn("15 días hábiles", text)
        self.assertIn("30 días hábiles", text)
        self.assertIn("10 días hábiles", text)

    def test_retract_uses_current_fifteen_calendar_day_refund_and_c192(self):
        _, _, specs = _specs("withdrawal_notice")
        spec = next(item for item in specs if item.get("kind") == "withdrawal_notice")
        text = _public_text(spec)
        self.assertIn("cinco días hábiles", text)
        self.assertIn("quince (15) días calendario", text)
        self.assertIn("C-192 de 2026", text)
        self.assertNotIn("reembolso en un máximo de treinta", text.casefold())

    def test_reversal_coordinates_provider_and_issuer_and_forbids_double_recovery(self):
        _, _, specs = _specs("payment_reversal_request")
        spec = next(item for item in specs if item.get("kind") == "payment_reversal_request")
        text = _public_text(spec)
        self.assertIn("cinco (5) días hábiles", text)
        self.assertIn("notificación al emisor", text.casefold())
        self.assertIn("doble recuperación", text.casefold())
        self.assertIn("no incorporar números completos de tarjeta", text.casefold())
        self.assertIn("no promete un resultado definitivo", text.casefold())

    def test_periodic_debit_keeps_three_distinct_time_rules(self):
        _, _, specs = _specs("recurring_debit_revocation")
        spec = next(item for item in specs if item.get("kind") == "recurring_debit_revocation")
        text = _public_text(spec)
        self.assertIn("en cualquier momento y sin necesidad de justificar", text.casefold())
        self.assertIn("dentro de cinco (5) días", text)
        self.assertIn("cinco (5) días hábiles", text)
        self.assertIn("dentro del mes siguiente", text.casefold())
        self.assertIn("ni extingue automáticamente", text.casefold())

    def test_non_delivery_uses_current_thirty_day_delivery_and_fifteen_day_refund(self):
        _, _, specs = _specs("ecommerce_non_delivery_termination")
        spec = next(item for item in specs if item.get("kind") == "ecommerce_non_delivery_termination")
        text = _public_text(spec)
        self.assertIn("treinta (30) días calendario", text)
        self.assertIn("quince (15) días calendario", text)
        self.assertIn("sin retenciones o descuentos", text.casefold())
        self.assertIn("no se presenta como retracto", text.casefold())

    def test_calendar_labels_automatic_business_day_dates_as_preliminary(self):
        for selected in MECHANISMS:
            with self.subTest(selected=selected):
                _, _, specs = _specs(selected)
                calendar = next(item for item in specs if item.get("kind") == "consumer_deadline_calendar")
                text = _public_text(calendar)
                self.assertIn("no descuenta festivos", text.casefold())
                self.assertIn("preliminar", text.casefold())

    def test_external_controls_are_internal_and_client_copy_has_no_release_jargon(self):
        for selected in MECHANISMS:
            with self.subTest(selected=selected):
                _, _, specs = _specs(selected)
                for spec in specs:
                    if spec.get("kind") not in {"consumer_mechanism_diagnosis", selected, "consumer_evidence_matrix", "consumer_deadline_calendar"}:
                        continue
                    self.assertTrue(spec.get("internal_controls_externalized"))
                    self.assertEqual(spec.get("legal_approval"), "pending")
                    self.assertEqual(spec.get("qa_approval"), "pending")
                    self.assertFalse(spec.get("released"))
                    public = (_public_text(spec) + " " + str(spec.get("subtitle") or "")).casefold()
                    self.assertNotIn("control de uso", public)
                    self.assertNotIn("m33.0", public)
                    self.assertNotIn("qa", public)
                    internal = " ".join(str(section) for section in spec.get("internal_review_sections") or []).casefold()
                    self.assertIn("aprobación jurídica", internal)
                    self.assertIn("qa", internal)

    def test_all_five_packages_pass_semantic_validation(self):
        for selected in MECHANISMS:
            with self.subTest(selected=selected):
                _, _, specs = _specs(selected)
                for spec in specs:
                    report = validate_rendered_sections(spec.get("sections") or [], product_code="CO-CD-003")
                    self.assertTrue(report["valid"], (selected, spec.get("kind"), report.get("errors")))

    def test_rendered_client_docx_does_not_print_internal_metadata_or_control(self):
        _, _, specs = _specs("warranty_claim")
        warranty = next(item for item in specs if item.get("kind") == "warranty_claim")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "consumer.docx"
            build_docx(
                target,
                warranty["title"],
                warranty.get("subtitle", ""),
                [],
                warranty["sections"],
                product_code="CO-CD-003",
                enforce_legal_standard=True,
                append_default_control=False,
            )
            text = _docx_text(target)
            forbidden = (
                "CONTROL DE USO",
                "CO-CD-003",
                "M33.0",
                "Estándar documental",
                "Candidato sujeto",
                "legal_approval",
                "qa_approval",
                "mismo hash",
            )
            for token in forbidden:
                self.assertNotIn(token, text)
            self.assertIn("BORRADOR CONTROLADO", text)

    def test_red_case_preserves_historical_gate(self):
        answers, result = consumer_route_fixture("warranty_claim")
        result["risk"] = "red"
        specs = document_specs_m33_all(
            "CASE-CONSUMER-RED",
            "CO-CD-003",
            answers,
            result,
            PRODUCTS["CO-CD-003"],
            "2026-08-08T07:30:00-05:00",
            [],
        )
        self.assertFalse(any(spec.get("internal_controls_externalized") for spec in specs))


if __name__ == "__main__":
    unittest.main()
