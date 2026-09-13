from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M372IntegrationContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_runtime_is_incremental_on_certified_m371_handler(self):
        run = self.read("run.py")
        handler = self.read("legalai_platform/http_handler_m37_2.py")
        self.assertIn("from legalai_platform.http_handler_m37_2 import Handler", run)
        self.assertIn("from legalai_platform.http_handler_m37_1 import Handler  # compatibility marker", run)
        self.assertIn("class Handler(BaseHandler)", handler)
        self.assertIn("http_handler_m37_1 import Handler as BaseHandler", handler)
        self.assertIn("m37-2-recorded-dates-reminder-boundary", run)

    def test_runtime_uses_retry_before_quota_hardened_center(self):
        route = self.read("legalai_platform/routes/m37_2_timing_reminder_routes.py")
        hardening = self.read("legalai_platform/timing_reminders_m37_2_hardening.py")
        self.assertIn("HardenedTimingReminderCenter", route)
        self.assertIn("return HardenedTimingReminderCenter(followup_center(), evidence_center())", route)
        self.assertIn("class HardenedTimingReminderCenter(base.TimingReminderCenter)", hardening)
        date_exact = hardening.index("if exact:")
        date_quota = hardening.index('max_date_records_per_task')
        self.assertLess(date_exact, date_quota)
        reminder_exact = hardening.index('if events and str(events[-1].get("action") or "") == "SCHEDULED"')
        reminder_quota = hardening.index('max_reminders_per_task')
        self.assertLess(reminder_exact, reminder_quota)

    def test_handler_preserves_real_origin_auth_and_csrf_status_contracts(self):
        handler = self.read("legalai_platform/http_handler_m37_2.py")
        self.assertIn("path = urlparse(self.path).path", handler)
        self.assertIn("self.require_origin()", handler)
        self.assertIn("self.require_user()", handler)
        self.assertIn("self.require_csrf()", handler)
        self.assertNotIn("except Exception", handler)
        self.assertIn("return super().do_GET()", handler)
        self.assertIn("return super().do_POST()", handler)

    def test_public_boundary_never_claims_legal_deadline_or_calendar_calculation(self):
        engine = self.read("legalai_platform/timing_reminders_m37_2.py")
        config = self.read("config/m37/timing_reminder_contracts.json")
        for marker in (
            '"date_record_is_legal_deadline": false',
            '"date_record_legal_deadline_verified": false',
            '"reminder_is_legal_deadline": false',
            '"business_calendar_calculation": false',
            '"statutory_deadline_calculation": false',
            '"automatic_close": false',
            '"automatic_escalation": false',
        ):
            self.assertIn(marker, config)
        self.assertNotIn('"legal_deadline_verified": True', engine)
        self.assertNotIn('"is_legal_deadline": True', engine)
        self.assertIn('"OPERATIONAL_CHECKPOINT"', engine)
        self.assertIn('"M24_EXISTING_DUE_AT"', engine)

    def test_date_values_are_not_duplicated_into_m37_followup_ledger(self):
        engine = self.read("legalai_platform/timing_reminders_m37_2.py")
        date_event = engine[engine.index('"DATE_RECORDED" if not supersedes_id'):engine.index("after = con.execute", engine.index('"DATE_RECORDED" if not supersedes_id'))]
        self.assertNotIn('"date_value"', date_event)
        self.assertNotIn('"date": normalized_date', date_event)
        reminder_event = engine[engine.index('"REMINDER_SCHEDULED"'):engine.index("after = con.execute", engine.index('"REMINDER_SCHEDULED"'))]
        self.assertNotIn('"scheduled_for"', reminder_event)

    def test_observability_uses_metadata_not_date_values_or_legal_payload(self):
        source = self.read("legalai_platform/routes/m37_2_timing_reminder_routes.py")
        tree = ast.parse(source)
        forbidden = {
            "date",
            "date_value",
            "scheduled_for",
            "record_hash",
            "reminder_hash",
            "event_hash",
            "previous_hash",
            "problem_statement",
            "answers",
            "payment_intent_id",
        }
        observed_keywords = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "_observe":
                continue
            observed_keywords.update(keyword.arg for keyword in node.keywords if keyword.arg)
        self.assertTrue(observed_keywords)
        self.assertTrue(forbidden.isdisjoint(observed_keywords), observed_keywords & forbidden)
        self.assertIn("ip_hash", observed_keywords)

    def test_m372_has_no_external_delivery_close_escalation_or_task_completion_actions(self):
        route = self.read("legalai_platform/routes/m37_2_timing_reminder_routes.py")
        engine = self.read("legalai_platform/timing_reminders_m37_2.py")
        for forbidden in ("send_email", "smtp", 'target_state', '"close"', '"escalate"'):
            self.assertNotIn(forbidden, route)
        self.assertNotIn("controlled_follow_up_update", engine)
        self.assertNotIn("UPDATE m24_case_follow_up", engine)
        self.assertNotIn("journey.transition", engine)
        self.assertIn('"automatic_task_completion": False', engine)
        self.assertIn('"automatic_close": False', engine)
        self.assertIn('"automatic_escalation": False', engine)

    def test_ci_contract_includes_m372_smoke_after_m371(self):
        ci = self.read(".github/workflows/ci.yml")
        self.assertIn("python tools/m37_1_http_smoke.py", ci)
        self.assertIn("python tools/m37_2_http_smoke.py", ci)
        self.assertLess(ci.index("python tools/m37_1_http_smoke.py"), ci.index("python tools/m37_2_http_smoke.py"))


if __name__ == "__main__":
    unittest.main()
