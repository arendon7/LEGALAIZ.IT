from __future__ import annotations

from copy import deepcopy
from types import ModuleType
import unittest

from m33_3_interview_overrides import (
    INTERVIEW_STANDARD,
    QUESTION_ID,
    install_m33_3_interview_overrides,
)


class InterviewOverridesM333Tests(unittest.TestCase):
    def _fake_core(self) -> ModuleType:
        module = ModuleType("fake_interview_core")
        module.INTERVIEWS = {
            "CO-CD-001": {
                "version": "2.32",
                "questions": [
                    {
                        "id": "prior_claim",
                        "label": "¿Ya presentó consulta o reclamo?",
                        "type": "select",
                        "options": ["No", "Sí"],
                        "required": True,
                        "section": "Gestiones previas",
                    },
                    {
                        "id": "prior_claim_complete",
                        "label": "¿La actuación previa estaba completa?",
                        "type": "select",
                        "options": ["Sí", "Parcial", "No", "No aplica"],
                        "required": True,
                        "section": "Gestiones previas",
                    },
                    {
                        "id": "response_received",
                        "label": "Respuesta recibida",
                        "type": "select",
                        "options": ["No", "Sí"],
                        "required": True,
                        "section": "Gestiones previas",
                    },
                ],
            }
        }
        return module

    def test_overlay_inserts_question_after_prior_claim_completeness(self):
        module = self._fake_core()
        before = len(module.INTERVIEWS["CO-CD-001"]["questions"])
        status = install_m33_3_interview_overrides(module)
        self.assertTrue(status["installed"])
        self.assertTrue(status["inserted"])
        self.assertEqual(status["interview_standard"], INTERVIEW_STANDARD)
        questions = module.INTERVIEWS["CO-CD-001"]["questions"]
        self.assertEqual(len(questions), before + 1)
        ids = [question["id"] for question in questions]
        self.assertEqual(ids.index(QUESTION_ID), ids.index("prior_claim_complete") + 1)

    def test_question_is_required_only_when_prior_claim_is_visible(self):
        module = self._fake_core()
        install_m33_3_interview_overrides(module)
        question = next(
            item for item in module.INTERVIEWS["CO-CD-001"]["questions"]
            if item["id"] == QUESTION_ID
        )
        self.assertTrue(question["required"])
        self.assertEqual(question["options"], ["Sí", "No", "No sé"])
        self.assertEqual(question["show_if"], {"field": "prior_claim", "equals": "Sí"})
        self.assertIn("suplantación", question["label"].casefold())
        self.assertIn("no sustituye", question["help"]["warning"].casefold())

    def test_overlay_is_idempotent_and_preserves_historical_source_version(self):
        module = self._fake_core()
        first = install_m33_3_interview_overrides(module)
        snapshot = deepcopy(module.INTERVIEWS["CO-CD-001"])
        second = install_m33_3_interview_overrides(module)
        self.assertFalse(second["inserted"])
        self.assertEqual(first["question_count"], second["question_count"])
        self.assertEqual(module.INTERVIEWS["CO-CD-001"], snapshot)
        self.assertEqual(second["source_version"], "2.32")
        self.assertEqual(module.INTERVIEWS["CO-CD-001"]["interview_standard"], "M33.3")

    def test_active_runtime_exposes_question_once_through_shared_interview(self):
        import run

        questions = run.INTERVIEWS["CO-CD-001"]["questions"]
        matches = [question for question in questions if question.get("id") == QUESTION_ID]
        self.assertEqual(len(matches), 1)
        self.assertEqual(run.INTERVIEWS["CO-CD-001"].get("interview_standard"), "M33.3")
        self.assertTrue(getattr(run, "M33_3_INTERVIEW_OVERLAY")["installed"])
        total_questions = sum(
            len(spec.get("questions") or [])
            for spec in run.INTERVIEWS.values()
            if isinstance(spec, dict)
        )
        self.assertGreaterEqual(total_questions, 474)

    def test_active_visibility_uses_existing_single_condition_schema(self):
        import run

        question = next(
            item for item in run.INTERVIEWS["CO-CD-001"]["questions"]
            if item.get("id") == QUESTION_ID
        )
        self.assertFalse(run.visible(question, {"prior_claim": "No"}))
        self.assertTrue(run.visible(question, {"prior_claim": "Sí"}))


if __name__ == "__main__":
    unittest.main()
