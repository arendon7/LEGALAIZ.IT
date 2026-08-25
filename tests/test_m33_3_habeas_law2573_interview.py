from __future__ import annotations

from types import ModuleType
import unittest

from m33_3_habeas_law2573_interview import (
    CORRECTION_ID,
    SECURITY_APPLICABLE_ID,
    SECURITY_AUTHORITY_ID,
    SECURITY_BREACH_ID,
    SECURITY_INSTRUMENT_ID,
    SECURITY_REQUIREMENT_ID,
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

    def test_overlay_inserts_seven_questions_once_and_preserves_source_version(self):
        module = self.fake_core()
        status = install_m33_3_habeas_law2573_interview(module)
        self.assertEqual(status["source_version"], "2.32")
        ids = [q["id"] for q in module.INTERVIEWS["CO-CD-001"]["questions"]]
        expected = (
            CORRECTION_ID,
            SECURITY_BREACH_ID,
            SECURITY_SUPPORT_ID,
            SECURITY_AUTHORITY_ID,
            SECURITY_INSTRUMENT_ID,
            SECURITY_REQUIREMENT_ID,
            SECURITY_APPLICABLE_ID,
        )
        for field in expected:
            self.assertEqual(ids.count(field), 1)
        second = install_m33_3_habeas_law2573_interview(module)
        self.assertEqual(second["inserted_question_ids"], [])
        self.assertEqual(len(ids), len(module.INTERVIEWS["CO-CD-001"]["questions"]))

    def test_visibility_uses_existing_single_condition_schema(self):
        module = self.fake_core(); install_m33_3_habeas_law2573_interview(module)
        by_id = {q["id"]: q for q in module.INTERVIEWS["CO-CD-001"]["questions"]}
        self.assertEqual(by_id[CORRECTION_ID]["show_if"], {"field": "identity_theft", "equals": "Sí"})
        self.assertEqual(by_id[SECURITY_BREACH_ID]["show_if"], {"field": "identity_theft", "equals": "Sí"})
        for field in (
            SECURITY_SUPPORT_ID,
            SECURITY_AUTHORITY_ID,
            SECURITY_INSTRUMENT_ID,
            SECURITY_REQUIREMENT_ID,
            SECURITY_APPLICABLE_ID,
        ):
            self.assertEqual(by_id[field]["show_if"], {"field": SECURITY_BREACH_ID, "equals": "Sí"})

    def test_questions_are_fail_closed_and_require_official_instrument_traceability(self):
        module = self.fake_core(); install_m33_3_habeas_law2573_interview(module)
        by_id = {q["id"]: q for q in module.INTERVIEWS["CO-CD-001"]["questions"]}
        self.assertEqual(by_id[CORRECTION_ID]["options"], ["Sí", "No", "No sé"])
        self.assertEqual(by_id[SECURITY_BREACH_ID]["options"], ["Sí", "No", "No sé"])
        self.assertEqual(by_id[SECURITY_SUPPORT_ID]["options"], ["Completo", "Parcial", "No", "No sé"])
        self.assertEqual(by_id[SECURITY_APPLICABLE_ID]["options"], ["Sí", "No", "No sé"])
        self.assertIn("autoridad", by_id[SECURITY_AUTHORITY_ID]["label"].casefold())
        self.assertIn("referencia exacta", by_id[SECURITY_INSTRUMENT_ID]["label"].casefold())
        self.assertIn("requisito concreto", by_id[SECURITY_REQUIREMENT_ID]["label"].casefold())
        self.assertGreaterEqual(by_id[SECURITY_REQUIREMENT_ID]["min_length"], 10)

    def test_authority_options_do_not_assume_only_future_law2573_protocol(self):
        module = self.fake_core(); install_m33_3_habeas_law2573_interview(module)
        by_id = {q["id"]: q for q in module.INTERVIEWS["CO-CD-001"]["questions"]}
        options = by_id[SECURITY_AUTHORITY_ID]["options"]
        self.assertIn("Superintendencia Financiera de Colombia", options)
        self.assertIn("Superintendencia de Industria y Comercio", options)
        self.assertIn("Otra autoridad competente", options)
        self.assertNotIn("Protocolo Ley 2573", options)

    def test_active_runtime_exposes_transition_overlay_once(self):
        import run

        questions = run.INTERVIEWS["CO-CD-001"]["questions"]
        ids = [q.get("id") for q in questions]
        for field in (
            CORRECTION_ID,
            SECURITY_BREACH_ID,
            SECURITY_SUPPORT_ID,
            SECURITY_AUTHORITY_ID,
            SECURITY_INSTRUMENT_ID,
            SECURITY_REQUIREMENT_ID,
            SECURITY_APPLICABLE_ID,
        ):
            self.assertEqual(ids.count(field), 1)
        self.assertGreaterEqual(len(questions), 67)
        self.assertTrue(getattr(run, "M33_3_HABEAS_LAW2573_INTERVIEW")["installed"])
        self.assertTrue(getattr(run, "M33_3_HABEAS_LAW2573_GUARD")["installed"])


if __name__ == "__main__":
    unittest.main()
