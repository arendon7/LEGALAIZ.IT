from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from document_standard_v33 import validate_rendered_sections
from docx_builder import build_docx
from m33_wave3_runtime import document_specs_m33_all


PRODUCTS = {
    "CO-SA-001": {"code": "CO-SA-001", "title": "Salud"},
    "CO-TR-001": {"code": "CO-TR-001", "title": "Verificación SAST"},
    "CO-TR-002": {"code": "CO-TR-002", "title": "Fotodetección no notificada"},
}


def strict_render(code: str, specs: list[dict]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for index, spec in enumerate(specs, 1):
            report = validate_rendered_sections(spec["sections"], product_code=code)
            if not report["valid"]:
                raise AssertionError((spec.get("kind"), report["errors"]))
            target = Path(tmp) / f"{index:02d}_{spec.get('kind','doc')}.docx"
            build_docx(
                target,
                spec["title"],
                spec.get("subtitle", ""),
                [],
                spec["sections"],
                product_code=code,
                enforce_legal_standard=True,
            )
            if not target.is_file():
                raise AssertionError(target)


def health_fixture():
    answers = {
        "patient_name": "Daniela Andrea López Ruiz",
        "patient_id": "43.000.601",
        "petitioner_name": "Daniela Andrea López Ruiz",
        "petitioner_id": "43.000.601",
        "eps_name": "Salud Integral Demostrativa EPS",
        "provider_name": "Medicamentos Demo S.A.S.",
        "request_mode": "Continuidad de medicamento de uso continuo",
        "service_requested": "Entrega del medicamento prescrito por el profesional tratante",
        "medical_order_date": "2026-07-20",
        "medical_order": "Fórmula médica vigente incorporada como anexo",
        "facts_detail": "El tratamiento venía siendo suministrado y la última entrega completa fue en junio; el gestor informó falta de disponibilidad.",
        "prior_filing_date": "2026-07-30",
        "prior_filing_radicado": "EPS-2026-300701",
        "prior_response": "Sin respuesta material de fondo",
        "priority": "Priorizado sujeto a clasificación institucional",
        "vital_risk": "No reportado con la información disponible",
        "active_tutela": "No",
        "active_contempt": "No",
        "filing_date": "2026-08-07",
    }
    result = {
        "risk": "red",
        "status": "critical_human_review",
        "calculation": {
            "priority": "prioritized",
            "petition_due_date": "2026-08-21",
        },
    }
    return answers, result


def sast_fixture():
    answers = {
        "requester_name": "Carolina Andrea Restrepo Maya",
        "requester_id": "43.000.901",
        "municipality": "Medellín",
        "traffic_authority": "Secretaría de Movilidad Demostrativa",
        "sast_id": "SAST-DEMO-041",
        "location_detail": "Avenida Metropolitana, sentido norte-sur",
        "device_type": "SAST fijo de velocidad, sujeto a verificación",
        "observation_date": "2026-07-20",
        "authorization_status": "No verificada",
        "signage_status": "Evidencia parcial",
        "metrology_status": "Sin soporte aportado",
        "inspection_status": "No confirmado",
        "individual_case_status": "No aportado",
        "documented_inconsistency": "La respuesta oficial deberá cotejarse con ubicación, vigencia y serial antes de afirmar cualquier incumplimiento.",
    }
    result = {"risk": "yellow", "status": "inconclusive_pending_official_records"}
    return answers, result


def traffic_fixture():
    answers = {
        "requester_name": "Carolina Andrea Restrepo Maya",
        "requester_id": "43.000.911",
        "owner_name": "Carolina Andrea Restrepo Maya",
        "owner_id": "43.000.911",
        "vehicle_plate": "DMO911",
        "citation_number": "DEMO-2024-31284567",
        "detection_date": "2024-09-12",
        "validation_date": "2024-09-13",
        "registry_query_date": "2024-09-13",
        "mailing_date": "2024-09-18",
        "delivery_or_return_date": "2024-09-23",
        "actual_knowledge_date": "2026-07-24",
        "official_address": "Carrera 35 No. 10-41, apartamento 604, Medellín",
        "used_address": "Calle 35 No. 10-14, Medellín",
        "postal_result": "Devuelto por dirección errada",
        "secondary_notification": "No acreditada con la información disponible",
        "sanction_exists": "Aparentemente sí; copia pendiente",
        "sanction_resolution": "Resolución por obtener del expediente",
        "sanction_date": "Fecha no confirmada",
        "sanction_notification": "No acreditada",
        "enforceability_date": "Fecha no confirmada",
        "collection_exists": "No determinado",
        "paid": "No",
    }
    result = {"risk": "red", "status": "high_risk_record_reconstruction_required"}
    return answers, result


class Wave3M330Tests(unittest.TestCase):
    def specs(self, code, answers, result):
        return document_specs_m33_all(
            "CASE-W3-M33",
            code,
            answers,
            result,
            PRODUCTS[code],
            "2026-08-07T15:30:00-05:00",
            [],
        )

    def test_health_generates_seven_part_expanded_record_even_when_review_is_critical(self):
        answers, result = health_fixture()
        specs = self.specs("CO-SA-001", answers, result)
        titles = " ".join(spec["title"].casefold() for spec in specs)
        combined = " ".join(str(spec["sections"]) for spec in specs)
        self.assertGreaterEqual(len(specs), 7)
        self.assertIn("petición", titles)
        self.assertIn("historia clínica", titles)
        self.assertIn("supersalud", titles)
        self.assertIn("urgente", combined.casefold())
        self.assertTrue(all(spec.get("document_standard") == "M33.0" for spec in specs))
        strict_render("CO-SA-001", specs)

    def test_sast_keeps_authorization_operation_control_and_individual_case_separate(self):
        answers, result = sast_fixture()
        specs = self.specs("CO-TR-001", answers, result)
        combined = " ".join(str(spec["sections"]) for spec in specs).casefold()
        self.assertGreaterEqual(len(specs), 7)
        for concept in ("autorización", "operación", "inspección", "caso individual"):
            self.assertIn(concept, combined)
        self.assertIn("no concluyente", combined)
        strict_render("CO-TR-001", specs)

    def test_traffic_generates_eight_part_defense_record_without_automatic_nullity(self):
        answers, result = traffic_fixture()
        specs = self.specs("CO-TR-002", answers, result)
        combined = " ".join(str(spec["sections"]) for spec in specs).casefold()
        self.assertGreaterEqual(len(specs), 8)
        for concept in ("comparendo", "notificación", "audiencia", "revocación", "ejecutoria", "cobro"):
            self.assertIn(concept, combined)
        self.assertIn("no produce una fórmula universal de nulidad", combined)
        self.assertIn("propiedad del vehículo", combined)
        strict_render("CO-TR-002", specs)


if __name__ == "__main__":
    unittest.main()
