import unittest

from m33_depth_polish import finalize_depth_polish


class M33DepthPolishTests(unittest.TestCase):
    def _signature(self):
        return {
            "heading": "FIRMA",
            "_type": "signature",
            "parties": [{"label": "PERSONA", "name": "Demo"}],
        }

    def test_warranty_claim_gains_substantive_sections_before_signature(self):
        specs = [{
            "kind": "warranty_claim",
            "sections": [
                {"heading": "I. HECHOS", "paragraphs": ["Hechos"]},
                self._signature(),
            ],
        }]
        result = finalize_depth_polish("CO-CD-003", specs, {}, {})
        sections = result[0]["sections"]
        headings = [item.get("heading") for item in sections]
        self.assertIn("VIII. MARCO JURÍDICO ESPECÍFICO Y CARGA DE ACREDITACIÓN", headings)
        self.assertIn("IX. TRAZABILIDAD TÉCNICA, PRUEBA Y CONTRADICCIÓN", headings)
        self.assertIn("X. CUMPLIMIENTO MATERIAL, CIERRE Y RESERVA DE DERECHOS", headings)
        self.assertLess(
            headings.index("X. CUMPLIMIENTO MATERIAL, CIERRE Y RESERVA DE DERECHOS"),
            headings.index("FIRMA"),
        )

    def test_health_petition_gains_execution_priority_and_traceability(self):
        specs = [{
            "kind": "health_petition",
            "sections": [{"heading": "I. HECHOS"}, self._signature()],
        }]
        result = finalize_depth_polish("CO-SA-001", specs, {}, {})
        headings = [item.get("heading") for item in result[0]["sections"]]
        self.assertIn("VII. DEBER DE COORDINACIÓN Y EJECUCIÓN MATERIAL", headings)
        self.assertIn("VIII. PRIORIDAD, URGENCIA Y ESCALAMIENTO", headings)
        self.assertIn("IX. TRAZABILIDAD CLÍNICO-ADMINISTRATIVA Y CIERRE", headings)
        self.assertLess(headings.index("IX. TRAZABILIDAD CLÍNICO-ADMINISTRATIVA Y CIERRE"), headings.index("FIRMA"))

    def test_traffic_notification_gains_due_process_and_evidence_sections(self):
        specs = [{
            "kind": "traffic_notification_claim",
            "sections": [{"heading": "I. HECHOS"}, self._signature()],
        }]
        result = finalize_depth_polish("CO-TR-002", specs, {}, {})
        headings = [item.get("heading") for item in result[0]["sections"]]
        self.assertIn("V. MARCO JURÍDICO DE NOTIFICACIÓN Y DEBIDO PROCESO", headings)
        self.assertIn("VI. PRUEBA MÍNIMA PARA RESOLVER LA CONTROVERSIA", headings)
        self.assertIn("VII. RESPONSABILIDAD, EFECTOS Y RESERVAS", headings)
        self.assertEqual(sum(1 for item in result[0]["sections"] if item.get("_type") == "signature"), 1)

    def test_traffic_polish_does_not_reintroduce_signature_when_release_gate_removed_it(self):
        specs = [{
            "kind": "traffic_notification_claim",
            "sections": [{"heading": "I. HECHOS"}],
        }]
        result = finalize_depth_polish("CO-TR-002", specs, {}, {})
        self.assertFalse(any(item.get("_type") == "signature" for item in result[0]["sections"]))

    def test_non_target_document_remains_unchanged(self):
        specs = [{"kind": "other", "sections": [{"heading": "I"}]}]
        self.assertIs(finalize_depth_polish("CO-AR-001", specs, {}, {}), specs)

    def test_polish_is_idempotent(self):
        specs = [{
            "kind": "health_petition",
            "sections": [{"heading": "I. HECHOS"}, self._signature()],
        }]
        once = finalize_depth_polish("CO-SA-001", specs, {}, {})
        twice = finalize_depth_polish("CO-SA-001", once, {}, {})
        headings = [item.get("heading") for item in twice[0]["sections"]]
        self.assertEqual(headings.count("VII. DEBER DE COORDINACIÓN Y EJECUCIÓN MATERIAL"), 1)
        self.assertEqual(headings.count("VIII. PRIORIDAD, URGENCIA Y ESCALAMIENTO"), 1)
        self.assertEqual(headings.count("IX. TRAZABILIDAD CLÍNICO-ADMINISTRATIVA Y CIERRE"), 1)


if __name__ == "__main__":
    unittest.main()
