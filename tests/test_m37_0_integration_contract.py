from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M370IntegrationContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_runtime_is_incremental_on_certified_m363_handler(self):
        run = self.read("run.py")
        handler = self.read("legalai_platform/http_handler_m37_0.py")
        self.assertIn("from legalai_platform.http_handler_m37_0 import Handler", run)
        self.assertIn("from legalai_platform.http_handler_m36_3 import Handler  # compatibility marker", run)
        self.assertIn("class Handler(BaseHandler)", handler)
        self.assertIn("http_handler_m36_3 import Handler as BaseHandler", handler)
        self.assertIn("m37-0-post-delivery-followup-foundation", run)

    def test_incremental_handler_uses_real_path_origin_auth_and_csrf_contracts(self):
        handler = self.read("legalai_platform/http_handler_m37_0.py")
        self.assertIn("from urllib.parse import urlparse", handler)
        self.assertIn("path = urlparse(self.path).path", handler)
        self.assertNotIn("self._path()", handler)
        self.assertIn("self.require_origin()", handler)
        self.assertIn("self.require_user()", handler)
        self.assertIn("self.require_csrf()", handler)
        self.assertNotIn("self.require_csrf(user)", handler)
        self.assertIn("return super().do_GET()", handler)
        self.assertIn("return super().do_POST()", handler)

    def test_m37_guard_is_installed_without_removing_m36_delivery_guard(self):
        run = self.read("run.py")
        self.assertIn("install_m36_3_delivery_guard(M24_CASE_JOURNEY)", run)
        self.assertIn("install_m37_0_followup_guard(M24_CASE_JOURNEY)", run)
        guard = self.read("legalai_platform/m37_0_journey_guard.py")
        self.assertIn("ContextVar", guard)
        self.assertIn("m37_followup_enrollment", guard)
        self.assertIn("controlled_follow_up_update", guard)

    def test_legacy_m24_followup_endpoint_is_blocked_only_after_m37_enrollment(self):
        route = self.read("legalai_platform/routes/m24_case_routes.py")
        self.assertIn("_requires_m37_controlled_followup", route)
        self.assertIn("M37_CONTROLLED_FOLLOWUP_REQUIRED", route)
        self.assertIn("m37_followup_enrollment", route)
        self.assertIn("PREPARED", route)
        self.assertIn("ACTIVE", route)

    def test_m370_requires_m363_delivery_and_reuses_m24_tasks(self):
        engine = self.read("legalai_platform/post_delivery_followup_m37_0.py")
        self.assertIn("m36_controlled_delivery", engine)
        self.assertIn('"DELIVERED_IN_APP"', engine)
        self.assertIn("m24_case_follow_up", engine)
        self.assertIn("self.journey.update_follow_up", self.read("legalai_platform/m37_0_journey_guard.py"))
        self.assertNotIn("CREATE TABLE IF NOT EXISTS m37_followup_task", engine)

    def test_operational_checkpoint_never_claims_verified_legal_deadline(self):
        config = self.read("config/m37/follow_up_contracts.json")
        engine = self.read("legalai_platform/post_delivery_followup_m37_0.py")
        self.assertIn('"is_legal_deadline": false', config)
        self.assertIn('"legal_deadline_verified": false', config)
        self.assertIn('"is_legal_deadline": False', engine)
        self.assertIn('"legal_deadline_verified": False', engine)
        self.assertIn('"legal_deadline_calculation": False', engine)
        self.assertNotIn("BusinessCalendar", engine)
        self.assertNotIn("legal_deadline=True", engine)

    def test_completion_is_reported_or_recorded_but_never_verified(self):
        engine = self.read("legalai_platform/post_delivery_followup_m37_0.py")
        self.assertIn('return "SELF_REPORTED"', engine)
        self.assertIn('return "PROFESSIONAL_RECORDED"', engine)
        self.assertIn('"evidence_verified": False', engine)
        self.assertIn('"legal_effect_verified": False', engine)
        self.assertNotIn('"evidence_verified": True', engine)
        self.assertNotIn('"legal_effect_verified": True', engine)

    def test_close_readiness_never_auto_closes_or_escalates(self):
        engine = self.read("legalai_platform/post_delivery_followup_m37_0.py")
        self.assertIn('"automatic_close": False', engine)
        self.assertIn('"automatic_escalation": False', engine)
        self.assertNotIn('"CERRADO",', engine)
        self.assertNotIn('"ESCALADO",', engine)
        self.assertNotIn('target="CERRADO"', engine)
        self.assertNotIn('target="ESCALADO"', engine)

    def test_public_api_has_only_start_task_update_and_read_in_m370(self):
        route = self.read("legalai_platform/routes/m37_0_post_delivery_followup_routes.py")
        self.assertIn('parts[2] == "start"', route)
        self.assertIn('parts[2] == "tasks"', route)
        self.assertNotIn('"close"', route)
        self.assertNotIn('"escalate"', route)
        self.assertNotIn('"deadline"', route)
        self.assertNotIn("send_email", route)

    def test_observability_excludes_note_text_legal_payload_and_integrity_hashes(self):
        route = self.read("legalai_platform/routes/m37_0_post_delivery_followup_routes.py")
        for forbidden in (
            "note=",
            "problem_statement",
            "answers=",
            "event_hash=",
            "previous_hash=",
            "package_sha256=",
            "release_record_hash=",
            "payment_intent_id=",
        ):
            self.assertNotIn(forbidden, route)
        self.assertIn("ip_hash", route)

    def test_m37_event_payload_minimizes_notes_and_sensitive_case_content(self):
        engine = self.read("legalai_platform/post_delivery_followup_m37_0.py")
        append_section = engine[engine.index("def _append_event") : engine.index("def _transition_to_followup")]
        self.assertNotIn("problem_statement", append_section)
        self.assertNotIn("payment", append_section)
        self.assertIn("payload_json", append_section)
        task_event_section = engine[engine.index('"TASK_STATUS_RECORDED"') : engine.index("def _public_task")]
        self.assertIn('"note_present": True', task_event_section)
        self.assertNotIn('"note": note', task_event_section)

    def test_ci_runs_m370_after_m363_with_fresh_process_and_real_login_policy(self):
        workflow = self.read(".github/workflows/ci.yml")
        m363 = workflow.index("python tools/m36_3_http_smoke.py")
        m370 = workflow.find("python tools/m37_0_http_smoke.py")
        if m370 < 0:
            self.fail("CI todavía no ejecuta el smoke M37.0")
        restart = workflow.rfind("start_server", m363, m370)
        self.assertGreater(restart, m363)
        self.assertLess(restart, m370)
        between = workflow[m363:m370]
        self.assertIn("stop_server", between)
        self.assertIn("12/300", between)
        self.assertNotIn("RATE_LIMIT_DISABLE", workflow)
        self.assertNotIn("LOGIN_RATE_LIMIT", workflow)
        self.assertNotIn("LEGAL_DISABLE_RATE", workflow)


if __name__ == "__main__":
    unittest.main()
