from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile

from document_standard_v33 import validate_rendered_sections
from docx_builder import build_docx
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_wave3 import PRODUCTS, traffic_fixture

KINDS = {
    "traffic_diagnostic", "traffic_record_request", "traffic_notification_claim",
    "traffic_hearing_request", "traffic_revocation_request",
    "traffic_registry_correction", "traffic_evidence_matrix", "traffic_filing_guide",
}


def specs(answers=None, result=None):
    if answers is None or result is None:
        answers, result = traffic_fixture()
    return document_specs_m33_all(
        "CASE-TRAFFIC-LEGAL", "CO-TR-002", answers, result,
        PRODUCTS["CO-TR-002"], "2026-08-09T12:00:00-05:00", [],
    )


def body(spec):
    return " ".join(str(x) for x in spec.get("sections") or [])


class TrafficLegalFinalizeM330Tests(unittest.TestCase):
    def test_eight_client_documents_keep_governance_pending(self):
        output = specs()
        self.assertEqual({x.get("kind") for x in output}, KINDS)
        for item in output:
            self.assertTrue(item.get("internal_controls_externalized"))
            self.assertTrue(item.get("requires_human_review"))
            self.assertTrue(item.get("critical_human_review"))
            self.assertEqual(item.get("legal_approval"), "pending")
            self.assertEqual(item.get("qa_approval"), "pending")
            self.assertFalse(item.get("released"))
            visible = (item.get("subtitle", "") + " " + body(item)).casefold()
            for forbidden in ("composición jurídica profunda m33.0", "control de uso", "documento candidato interno", "nivel del motor", "high_risk_record_reconstruction_required"):
                self.assertNotIn(forbidden, visible, item.get("kind"))

    def test_timeline_keeps_detection_validation_shipping_and_notification_distinct(self):
        diag = next(x for x in specs() if x.get("kind") == "traffic_diagnostic")
        text = body(diag).casefold()
        for concept in ("detección", "validación", "envío", "entrega/devolución", "conocimiento real", "sanción", "ejecutoria", "mandamiento"):
            self.assertIn(concept, text)
        self.assertIn("diez (10) días hábiles", text)
        self.assertIn("tres (3) días hábiles", text)
        self.assertIn("once (11) días hábiles", text)

    def test_address_difference_is_apparent_inconsistency_not_nullity(self):
        claim = next(x for x in specs() if x.get("kind") == "traffic_notification_claim")
        text = body(claim).casefold()
        self.assertIn("inconsistencia aparente de dirección", text)
        self.assertIn("certificación histórica runt", text)
        self.assertIn("no produce por sí sola nulidad", text)

    def test_late_actual_knowledge_is_not_automatic_valid_notification(self):
        diag = next(x for x in specs() if x.get("kind") == "traffic_diagnostic")
        text = body(diag).casefold()
        self.assertIn("conocimiento tardío", text)
        self.assertIn("no equivale automáticamente a notificación válida", text)

    def test_article_136_effect_is_precise_and_not_universal_nullity(self):
        claim = next(x for x in specs() if x.get("kind") == "traffic_notification_claim")
        text = body(claim).casefold()
        self.assertIn("términos de reducción", text)
        self.assertIn("notificación válida", text)
        self.assertIn("afectación material", text)
        self.assertIn("no convierte ‘no recibí’ en nulidad automática", text)

    def test_owner_rule_keeps_c038_and_c321_together(self):
        hearing = next(x for x in specs() if x.get("kind") == "traffic_hearing_request")
        text = body(hearing).casefold()
        self.assertIn("c-038/2020", text)
        self.assertIn("solidaridad automática", text)
        self.assertIn("c-321/2022", text)
        self.assertIn("deberes propios del propietario", text)
        self.assertIn("no responsabilidad objetiva", text)
        self.assertIn("culposo", text)

    def test_caducity_and_prescription_are_not_collapsed_or_invented(self):
        diag = next(x for x in specs() if x.get("kind") == "traffic_diagnostic")
        text = body(diag).casefold()
        self.assertIn("caducidad", text)
        self.assertIn("un (1) año", text)
        self.assertIn("sin acto y fecha ciertos no se declara", text)
        self.assertIn("prescripción", text)
        self.assertIn("tres (3) años", text)
        self.assertIn("notificación del mandamiento de pago", text)

    def test_demo_revocation_is_not_radical_ready_without_verified_act(self):
        rev = next(x for x in specs() if x.get("kind") == "traffic_revocation_request")
        text = body(rev).casefold()
        self.assertIn("no radicable todavía", text)
        self.assertIn("no revive términos", text)
        self.assertIn("no suspende automáticamente", text)
        self.assertIn("no produce silencio positivo", text)

    def test_record_request_uses_10_15_and_5_day_petition_controls(self):
        request = next(x for x in specs() if x.get("kind") == "traffic_record_request")
        text = body(request).casefold()
        self.assertIn("diez (10) días", text)
        self.assertIn("quince (15)", text)
        self.assertIn("cinco (5) días", text)
        self.assertIn("reserva", text)

    def test_registry_correction_requires_source_act(self):
        registry = next(x for x in specs() if x.get("kind") == "traffic_registry_correction")
        text = body(registry).casefold()
        self.assertIn("acto fuente por verificar", text)
        self.assertIn("inconsistencia visual no basta", text)
        self.assertIn("correspondencia con el acto fuente", text)

    def test_guide_forbids_automatic_outcomes_and_separates_files(self):
        guide = next(x for x in specs() if x.get("kind") == "traffic_filing_guide")
        text = body(guide).casefold()
        for concept in ("comparendo ≠ sanción", "validación ≠ notificación", "envío ≠ entrega", "caducidad ≠ prescripción", "simit/runt ≠ acto fuente"):
            self.assertIn(concept, text)
        self.assertIn("no concluir automáticamente", text)
        self.assertIn("fotomulta ilegal", text)
        self.assertIn("no tiene que pagar", text)

    def test_all_outputs_validate_and_docx_client_copy_has_no_internal_box(self):
        with tempfile.TemporaryDirectory() as tmp:
            for item in specs():
                report = validate_rendered_sections(item["sections"], product_code="CO-TR-002")
                self.assertTrue(report["valid"], (item.get("kind"), report["errors"]))
                target = Path(tmp) / f"{item['kind']}.docx"
                build_docx(target, item["title"], item.get("subtitle", ""), [], item["sections"], product_code="CO-TR-002", enforce_legal_standard=True, append_default_control=not bool(item.get("internal_controls_externalized")))
                with ZipFile(target) as zf:
                    xml = zf.read("word/document.xml").decode("utf-8", errors="ignore").casefold()
                for forbidden in ("control de uso", "documento candidato interno", "composición jurídica profunda m33.0", "high_risk_record_reconstruction_required"):
                    self.assertNotIn(forbidden, xml, item.get("kind"))


if __name__ == "__main__":
    unittest.main()
