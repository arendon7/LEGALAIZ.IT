from __future__ import annotations

from types import ModuleType
import unittest

from m33_3_habeas_law2573_interview import (
    CORRECTION_ID,
    SECURITY_BREACH_ID,
    SECURITY_SUPPORT_ID,
    install_m33_3_habeas_law2573_interview,
)


class HabeasLaw2573InterviewM333Tests(unittest.TestCase):
    def fake_core(self) -> ModuleType:
        module = ModuleType("fake_law2573_interview_core")
        module.INTERVIEWS = {
            "CO-CD-001": {
                "version": "2.32",
                "questions": [
                    {
                        "id": "identity_theft",
                        "label": "¿Alega suplantación de identidad?",
                        "type": "select",
                        "options": ["No", "Sí", "No sé"],
                        "required": True,
                        "section": "Riesgo y escalamiento",
                    },
                    {
                        "id": "identity_theft_complex",
                        "label": "¿Es compleja?",
                        "type": "select",
                        "options": ["No", "Sí", "No aplica"],
                        "required": True,
                        "section": "Riesgo y escalamiento",
                    },
                ],
            }
        }
        return module

    def test_overlay_inserts_three_questions_once_and_preserves_source_version(self):
        module = self.fake_core()
        status = install_m33_3_habeas_law2573_interview(module)
        self.assertEqual(status["source_version"], "2.32")
        ids = [q["id"] for q in module.INTERVIEWS["CO-CD-001"]["questions"]]
        self.assertEqual(ids.count(CORRECTION_ID), 1)
        self.assertEqual(ids.count(SECURITY_BREACH_ID), 1)
        self.assertEqual(ids.count(SECURITY_SUPPORT_ID), 1)
        second = install_m33_3_habeas_law2573_interview(module)
        self.assertEqual(second["inserted_question_ids"], [])
        self.assertEqual(len(ids), len(module.INTERVIEWS["CO-CD-001"]["questions"]))

    def test_visibility_uses_existing_single_condition_schema(self):
        module = self.fake_core(); install_m33_3_habeas_law2573_interview(module)
        by_id = {q["id"]: q for q in module.INTERVIEWS["CO-CD-001"]["questions"]}
        self.assertEqual(by_id[CORRECTION_ID]["show_if"], {"field": "identity_theft", "equals": "Sí"})
        self.assertEqual(by_id[SECURITY_BREACH_ID]["show_if"], {"field": "identity_theft", "equals": "Sí"})
        self.assertEqual(by_id[SECURITY_SUPPORT_ID]["show_if"], {"field": SECURITY_BREACH_ID, "equals": "Sí"})

    def test_questions_are_fail_closed_and_do_not_ask_user_to_make_legal_conclusion(self):
        module = self.fake_core(); install_m33_3_habeas_law2573_interview(module)
        by_id = {q["id"]: q for q in module.INTERVIEWS["CO-CD-001"]["questions"]}
        self.assertEqual(by_id[CORRECTION_ID]["options"], ["Sí", "No", "No sé"])
        self.assertEqual(by_id[SECURITY_BREACH_ID]["options"], ["Sí", "No", "No sé"])
        self.assertEqual(by_id[SECURITY_SUPPORT_ID]["options"], ["Completo", "Parcial", "No", "No sé"])
        self.assertIn("verificación documentada", by_id[SECURITY_BREACH_ID]["label"].casefold())

    def test_active_runtime_exposes_transition_overlay_once(self):
        import run

        questions = run.INTERVIEWS["CO-CD-001"]["questions"]
        ids = [q.get("id") for q in questions]
        for field in (CORRECTION_ID, SECURITY_BREACH_ID, SECURITY_SUPPORT_ID):
            self.assertEqual(ids.count(field), 1)
        self.assertGreaterEqual(len(questions), 63)
        self.assertTrue(getattr(run, "M33_3_HABEAS_LAW2573_INTERVIEW")["installed"])
        self.assertTrue(getattr(run, "M33_3_HABEAS_LAW2573_GUARD")["installed"])


if __name__ == "__main__":
    unittest.main()
