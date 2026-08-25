from __future__ import annotations

from types import ModuleType
import unittest

from m33_3_habeas_communication_interview import (
    ALT_AGREED_ID,
    CHANNEL_ID,
    CONSULTABLE_ID,
    CONTENT_ID,
    DESTINATION_ID,
    FIRST_DATE_ID,
    SENT_ID,
    install_m33_3_habeas_communication_interview,
)


class HabeasCommunicationInterviewM333Tests(unittest.TestCase):
    def fake_core(self) -> ModuleType:
        module = ModuleType("fake_communication_interview_core")
        module.INTERVIEWS = {
            "CO-CD-001": {
                "version": "2.32",
                "questions": [
                    {"id": "prior_communication_received", "label": "¿Recibió?", "type": "select", "options": ["Sí", "No", "No sé"], "required": True, "section": "Comunicación previa"},
                    {"id": "prior_communication_date", "label": "Fecha de la última comunicación previa", "type": "date", "required": False, "section": "Comunicación previa"},
                    {"id": "prior_communication_evidence", "label": "Prueba de envío o recepción", "type": "select", "options": ["Completa", "Parcial", "No", "No solicitada"], "required": True, "section": "Comunicación previa"},
                    {"id": "small_obligation_two_notices", "label": "Dos comunicaciones", "type": "select", "options": ["Sí", "No", "No sé", "No aplica"], "required": True, "section": "Comunicación previa"},
                ],
            }
        }
        module.RULES = {
            "CO-CD-001": [
                {
                    "id": "CD1-R13",
                    "message": "No está acreditada la comunicación previa al reporte.",
                    "action": "Solicitar prueba.",
                    "conditions": {"any": [{"field": "prior_communication_received", "op": "equals", "value": "No"}]},
                },
                {
                    "id": "CD1-R14",
                    "message": "La prueba de comunicación previa es incompleta o no ha sido solicitada.",
                    "action": "No concluir cumplimiento.",
                    "conditions": {"any": [{"field": "prior_communication_evidence", "op": "equals", "value": "Parcial"}]},
                },
            ]
        }
        return module

    def test_overlay_inserts_all_questions_once_and_preserves_version(self):
        module = self.fake_core()
        status = install_m33_3_habeas_communication_interview(module)
        self.assertTrue(status["installed"])
        self.assertEqual(status["source_version"], "2.32")
        ids = [q["id"] for q in module.INTERVIEWS["CO-CD-001"]["questions"]]
        expected = {SENT_ID, CHANNEL_ID, DESTINATION_ID, ALT_AGREED_ID, CONSULTABLE_ID, CONTENT_ID, FIRST_DATE_ID}
        self.assertTrue(expected.issubset(ids))
        self.assertEqual(len(ids), len(set(ids)))
        second = install_m33_3_habeas_communication_interview(module)
        self.assertEqual(second["inserted_question_ids"], [])
        self.assertEqual(len(ids), len(module.INTERVIEWS["CO-CD-001"]["questions"]))

    def test_existing_date_is_redefined_as_send_date_without_changing_id(self):
        module = self.fake_core(); install_m33_3_habeas_communication_interview(module)
        question = next(q for q in module.INTERVIEWS["CO-CD-001"]["questions"] if q["id"] == "prior_communication_date")
        self.assertIn("envío", question["label"].casefold())
        self.assertTrue(question["required"])
        self.assertEqual(question["show_if"], {"field": SENT_ID, "equals": "Sí"})

    def test_single_condition_schema_is_preserved(self):
        module = self.fake_core(); install_m33_3_habeas_communication_interview(module)
        questions = {q["id"]: q for q in module.INTERVIEWS["CO-CD-001"]["questions"]}
        for field in (CHANNEL_ID, DESTINATION_ID, ALT_AGREED_ID, CONSULTABLE_ID, CONTENT_ID):
            self.assertEqual(questions[field]["show_if"], {"field": SENT_ID, "equals": "Sí"})
        self.assertEqual(questions[FIRST_DATE_ID]["show_if"], {"field": "small_obligation_two_notices", "equals": "Sí"})

    def test_rule_no_longer_uses_receipt_as_failure_pivot(self):
        module = self.fake_core(); status = install_m33_3_habeas_communication_interview(module)
        self.assertTrue(status["r13_patched"])
        rule = next(r for r in module.RULES["CO-CD-001"] if r["id"] == "CD1-R13")
        serialized = str(rule["conditions"])
        self.assertIn(SENT_ID, serialized)
        self.assertNotIn("prior_communication_received", serialized)
        self.assertIn("envío", rule["message"].casefold())

    def test_active_runtime_exposes_communication_overlay(self):
        import run

        questions = run.INTERVIEWS["CO-CD-001"]["questions"]
        ids = [q.get("id") for q in questions]
        for field in (SENT_ID, CHANNEL_ID, DESTINATION_ID, ALT_AGREED_ID, CONSULTABLE_ID, CONTENT_ID, FIRST_DATE_ID):
            self.assertEqual(ids.count(field), 1)
        date_question = next(q for q in questions if q.get("id") == "prior_communication_date")
        self.assertIn("envío", date_question.get("label", "").casefold())
        self.assertTrue(getattr(run, "M33_3_HABEAS_COMMUNICATION_INTERVIEW")["installed"])
        self.assertTrue(getattr(run, "M33_3_HABEAS_COMMUNICATION_GUARD")["installed"])


if __name__ == "__main__":
    unittest.main()
