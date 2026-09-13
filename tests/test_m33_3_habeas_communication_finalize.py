from __future__ import annotations

import unittest

from m33_3_habeas_communication_finalize import finalize_habeas_communication_m33_3


class HabeasCommunicationFinalizeM333Tests(unittest.TestCase):
    def result(self, *, status: str = "preliminarily_supported") -> dict:
        return {
            "calculation": {
                "communication_standard": "M33.3-habeas-prior-communication-v1",
                "communication_ruleset_verified_at": "2026-08-10",
                "communication_status": status,
                "prior_communication_date": "2023-10-20",
                "communication_report_date": "2023-11-10",
                "communication_lead_calendar_days": 21,
                "communication_channel": "Dirección física registrada",
                "communication_received_status": "No",
                "small_obligation_preliminary": False,
                "communication_consequence_if_noncompliance": "Consecuencia condicionada a verificación.",
            }
        }

    def test_claim_receives_one_compact_case_summary(self):
        specs = [{
            "kind": "habeas_claim",
            "sections": [{
                "heading": "IV. COMUNICACIÓN PREVIA Y PERMANENCIA",
                "paragraphs": ["Texto base."],
            }],
        }]
        finalized = finalize_habeas_communication_m33_3(specs, {}, self.result())
        paragraphs = finalized[0]["sections"][0]["paragraphs"]
        self.assertEqual(len(paragraphs), 2)
        self.assertIn("21 días calendario", paragraphs[-1])
        self.assertIn("recepción y el envío son hechos distintos", paragraphs[-1])
        self.assertLess(len(paragraphs[-1].split()), 70)

    def test_consultation_keeps_existing_paragraph_count(self):
        specs = [{
            "kind": "habeas_consultation",
            "sections": [{
                "heading": "IV. INFORMACIÓN SOLICITADA A LA FUENTE",
                "paragraphs": [
                    "1. Copia del soporte de la obligación.",
                    "4. Certificación de la comunicación previa: texto íntegro, fecha y prueba de envío, destinatario, canal utilizado y dirección empleada.",
                ],
            }],
        }]
        before = list(specs[0]["sections"][0]["paragraphs"])
        finalized = finalize_habeas_communication_m33_3(specs, {}, self.result())
        self.assertEqual(finalized[0]["sections"][0]["paragraphs"], before)
        self.assertEqual(finalized[0]["communication_standard"], "M33.3-habeas-prior-communication-v1")

    def test_evidence_matrix_updates_only_communication_row(self):
        specs = [{
            "kind": "habeas_evidence_matrix",
            "sections": [{
                "heading": "Matriz",
                "table": [
                    ["ID", "Elemento", "Fuente", "Estado"],
                    ["HD-EV-004", "Pago", "Soporte", "Pendiente"],
                    ["HD-EV-005", "Comunicación previa", "Soporte", "Pendiente"],
                ],
            }],
        }]
        finalized = finalize_habeas_communication_m33_3(specs, {}, self.result())
        rows = finalized[0]["sections"][0]["table"]
        self.assertEqual(rows[1][3], "Pendiente")
        self.assertIn("Envío preliminarmente soportado", rows[2][3])

    def test_noncompliance_adds_conditioned_consequence_only_to_claim(self):
        specs = [
            {"kind": "habeas_claim", "sections": [{"heading": "COMUNICACIÓN PREVIA Y PERMANENCIA", "paragraphs": ["Base."]}]},
            {"kind": "habeas_consultation", "sections": [{"heading": "INFORMACIÓN SOLICITADA A LA FUENTE", "paragraphs": ["Base consulta."]}]},
        ]
        finalized = finalize_habeas_communication_m33_3(specs, {}, self.result(status="noncompliance_preliminary"))
        self.assertEqual(len(finalized[0]["sections"][0]["paragraphs"]), 3)
        self.assertEqual(finalized[0]["sections"][0]["paragraphs"][-1], "Consecuencia condicionada a verificación.")
        self.assertEqual(finalized[1]["sections"][0]["paragraphs"], ["Base consulta."])


if __name__ == "__main__":
    unittest.main()
