from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile

from document_standard_v33 import validate_rendered_sections
from docx_builder import build_docx
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_wave3 import PRODUCTS, sast_fixture

EXPECTED_KINDS = {
    "sast_report",
    "sast_traceability",
    "sast_registration",
    "sast_record_request",
    "sast_inspection",
    "sast_followup",
    "sast_package",
}


def sast_specs(answers=None, result=None):
    if answers is None or result is None:
        answers, result = sast_fixture()
    return document_specs_m33_all(
        "CASE-SAST-LEGAL",
        "CO-TR-001",
        answers,
        result,
        PRODUCTS["CO-TR-001"],
        "2026-08-08T15:30:00-05:00",
        [],
    )


def visible(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


class SastLegalFinalizeM330Tests(unittest.TestCase):
    def test_all_seven_sast_documents_are_client_facing_and_governance_stays_pending(self):
        specs = sast_specs()
        self.assertEqual({spec.get("kind") for spec in specs}, EXPECTED_KINDS)
        for spec in specs:
            self.assertTrue(spec.get("internal_controls_externalized"), spec.get("kind"))
            self.assertTrue(spec.get("requires_human_review"), spec.get("kind"))
            self.assertEqual(spec.get("legal_approval"), "pending")
            self.assertEqual(spec.get("qa_approval"), "pending")
            self.assertFalse(spec.get("released"))
            self.assertNotIn("Composición jurídica profunda M33.0", spec.get("subtitle", ""))
            body = visible(spec).casefold()
            self.assertNotIn("control de uso, fuentes y revisión", body)
            self.assertNotIn("documento candidato interno", body)
            self.assertNotIn("nivel del motor", body)

    def test_current_2026_case_does_not_treat_performance_concept_as_current_requirement(self):
        report = next(spec for spec in sast_specs() if spec.get("kind") == "sast_report")
        body = visible(report).casefold()
        self.assertIn("fuera del intervalo histórico del concepto de desempeño", body)
        self.assertIn("no es un requisito actual", body)
        self.assertIn("22/03/2018–19/08/2020", visible(report))

    def test_historical_2019_case_activates_temporal_performance_review_without_equating_it_to_authorization(self):
        answers, result = sast_fixture()
        answers = deepcopy(answers)
        answers["observation_date"] = "2019-06-15"
        answers["performance_concept"] = "No existe soporte"
        report = next(spec for spec in sast_specs(answers, deepcopy(result)) if spec.get("kind") == "sast_report")
        body = visible(report).casefold()
        self.assertIn("período histórico 22/03/2018–19/08/2020", body)
        self.assertIn("no equivalía a autorización de funcionamiento", body)

    def test_authorization_does_not_prove_operational_compliance(self):
        answers, result = sast_fixture()
        answers = deepcopy(answers)
        answers["ansv_authorization"] = "Sí"
        answers["authorization_number"] = "ANSV-DEMO-001"
        report = next(spec for spec in sast_specs(answers, deepcopy(result)) if spec.get("kind") == "sast_report")
        body = visible(report).casefold()
        self.assertIn("autorización de instalación no equivale", body)
        self.assertIn("viabilidad para el uso de la infraestructura vial", body)
        self.assertIn("fecha real de inicio de operación", body)

    def test_public_transport_infrastructure_exception_is_recognized_without_blanket_ansv_requirement(self):
        answers, result = sast_fixture()
        answers = deepcopy(answers)
        answers["device_type"] = "SAST fijo para control de carril exclusivo de sistema de transporte público"
        report = next(spec for spec in sast_specs(answers, deepcopy(result)) if spec.get("kind") == "sast_report")
        body = visible(report).casefold()
        self.assertIn("posible excepción legal en infraestructura de transporte público", body)
        self.assertIn("sin autorización nacional", body)
        self.assertIn("señalización", body)

    def test_control_en_via_device_support_is_classified_separately(self):
        answers, result = sast_fixture()
        answers = deepcopy(answers)
        answers["device_type"] = "Control en vía apoyado en dispositivo electrónico"
        report = next(spec for spec in sast_specs(answers, deepcopy(result)) if spec.get("kind") == "sast_report")
        body = visible(report).casefold()
        self.assertIn("control en vía apoyado en dispositivo electrónico", body)
        self.assertIn("ruta distinta del sast automático", body)
        self.assertIn("control directo por agente", body)

    def test_no_search_result_never_becomes_no_authorization(self):
        matrix = next(spec for spec in sast_specs() if spec.get("kind") == "sast_traceability")
        body = visible(matrix).casefold()
        self.assertIn("no localizado en la fuente consultada", body)
        self.assertIn("no autorizado", body)
        self.assertIn("no prueba por sí sola inexistencia", visible(next(spec for spec in sast_specs() if spec.get("kind") == "sast_report")).casefold())

    def test_2026_investigation_is_not_presented_as_final_decision_or_individual_cancellation(self):
        answers, result = sast_fixture()
        answers = deepcopy(answers)
        answers["official_act_number"] = "7091"
        answers["official_act_status"] = "Apertura o formulación de cargos"
        inspection = next(spec for spec in sast_specs(answers, deepcopy(result)) if spec.get("kind") == "sast_inspection")
        body = visible(inspection).casefold()
        self.assertIn("apertura o formulación de cargos no equivale a decisión sancionatoria firme", body)
        self.assertIn("no decisiones firmes", visible(next(spec for spec in sast_specs(answers, deepcopy(result)) if spec.get("kind") == "sast_report")).casefold())
        package = next(spec for spec in sast_specs(answers, deepcopy(result)) if spec.get("kind") == "sast_package")
        self.assertIn("no anula automáticamente cada comparendo", visible(package).casefold())

    def test_current_signage_analysis_uses_2024_manual_with_transition(self):
        report = next(spec for spec in sast_specs() if spec.get("kind") == "sast_report")
        body = visible(report)
        self.assertIn("Resolución 20243040045005 de 2024", body)
        self.assertIn("reglas transitorias", body)

    def test_historical_signage_does_not_apply_2024_manual_retroactively(self):
        answers, result = sast_fixture()
        answers = deepcopy(answers)
        answers["observation_date"] = "2019-06-15"
        report = next(spec for spec in sast_specs(answers, deepcopy(result)) if spec.get("kind") == "sast_report")
        body = visible(report).casefold()
        self.assertIn("sin proyectar automáticamente sobre el pasado el manual 2024", body)

    def test_record_request_uses_differentiated_petition_terms_transfer_and_public_version(self):
        request = next(spec for spec in sast_specs() if spec.get("kind") == "sast_record_request")
        body = visible(request).casefold()
        self.assertIn("diez (10) días", body)
        self.assertIn("quince (15) días", body)
        self.assertIn("cinco (5) días", body)
        self.assertIn("versión pública", body)
        self.assertIn("reserva", body)

    def test_followup_does_not_claim_silence_without_receipt_or_transfer_check(self):
        followup = next(spec for spec in sast_specs() if spec.get("kind") == "sast_followup")
        body = visible(followup).casefold()
        self.assertIn("no debe afirmar silencio", body)
        self.assertIn("acuse", body)
        self.assertIn("traslados por competencia", body)

    def test_red_sast_case_keeps_human_review_gate(self):
        answers, result = sast_fixture()
        result = deepcopy(result)
        result["risk"] = "red"
        specs = sast_specs(deepcopy(answers), result)
        self.assertTrue(all(spec.get("critical_human_review") for spec in specs))
        self.assertTrue(all(spec.get("legal_approval") == "pending" for spec in specs))
        self.assertTrue(all(spec.get("qa_approval") == "pending" for spec in specs))
        self.assertTrue(all(spec.get("released") is False for spec in specs))

    def test_all_sast_outputs_pass_semantic_validation_and_client_docx_has_no_internal_control(self):
        specs = sast_specs()
        with tempfile.TemporaryDirectory() as tmp:
            for spec in specs:
                report = validate_rendered_sections(spec["sections"], product_code="CO-TR-001")
                self.assertTrue(report["valid"], (spec.get("kind"), report["errors"]))
                target = Path(tmp) / f"{spec['kind']}.docx"
                build_docx(
                    target,
                    spec["title"],
                    spec.get("subtitle", ""),
                    [],
                    spec["sections"],
                    product_code="CO-TR-001",
                    enforce_legal_standard=True,
                    append_default_control=not bool(spec.get("internal_controls_externalized")),
                )
                self.assertTrue(target.is_file())
                with ZipFile(target) as zf:
                    xml = zf.read("word/document.xml").decode("utf-8", errors="ignore").casefold()
                self.assertNotIn("control de uso", xml, spec.get("kind"))
                self.assertNotIn("documento candidato interno", xml, spec.get("kind"))
                self.assertNotIn("aprobación jurídica y qa", xml, spec.get("kind"))


if __name__ == "__main__":
    unittest.main()
