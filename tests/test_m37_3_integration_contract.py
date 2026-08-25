from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M373IntegrationContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_runtime_is_incremental_on_certified_m372_handler(self):
        run = self.read("run.py")
        handler = self.read("legalai_platform/http_handler_m37_3.py")
        self.assertIn("from legalai_platform.http_handler_m37_3 import Handler", run)
        self.assertIn("from legalai_platform.http_handler_m37_2 import Handler  # compatibility marker", run)
        self.assertIn("class Handler(BaseHandler)", handler)
        self.assertIn("http_handler_m37_2 import Handler as BaseHandler", handler)
        self.assertIn("m37-3-professional-disposition-gate", run)

    def test_m370_legacy_guard_remains_reserved_and_m373_bridge_is_narrow(self):
        guard = self.read("legalai_platform/m37_0_journey_guard.py")
        bridge = self.read("legalai_platform/m37_3_journey_guard.py")
        engine = self.read("legalai_platform/professional_disposition_m37_3.py")
        route = self.read("legalai_platform/routes/m37_3_disposition_routes.py")
        self.assertIn('_RESERVED_LIFECYCLE_TARGETS = frozenset({"CERRADO", "ESCALADO"})', guard)
        self.assertIn("El cierre o escalamiento de un expediente enrolado en M37 requiere", guard)
        self.assertIn('_RESERVED_TARGETS = frozenset({"CERRADO", "ESCALADO"})', bridge)
        self.assertIn("_m37_0_original_transition", bridge)
        self.assertIn("controlled_m37_disposition_transition", engine)
        self.assertNotIn("controlled_m37_disposition_transition", route)
        self.assertNotIn("_m37_0_original_transition", route)

    def test_close_is_specialist_only_escalation_allows_admin_and_client_is_excluded(self):
        config = self.read("config/m37/disposition_contracts.json")
        self.assertIn('"close_roles": ["specialist"]', config)
        self.assertIn('"escalate_roles": ["specialist", "admin"]', config)
        self.assertIn('"client_may_dispose_case": false', config)
        self.assertIn('"admin_may_close_without_specialist": false', config)
        engine = self.read("legalai_platform/professional_disposition_m37_3.py")
        self.assertIn("_assigned_specialist", engine)
        self.assertIn('role == "admin"', engine)

    def test_close_consumes_m370_m371_m372_without_redefining_them(self):
        engine = self.read("legalai_platform/professional_disposition_m37_3.py")
        self.assertIn("self.followup._detail_from_open_connection", engine)
        self.assertIn("self.evidence._public_item", engine)
        self.assertIn("self.timing._verify_date_records", engine)
        self.assertIn("self.timing._public_reminder", engine)
        for blocker in (
            "REQUIRED_TASKS_NOT_COMPLETED",
            "EVIDENCE_PENDING_REVIEW",
            "EVIDENCE_NEEDS_CLARIFICATION",
            "ACTIVE_REMINDER",
        ):
            self.assertIn(blocker, engine)

    def test_internal_reason_is_not_public_transition_reason_ledger_or_observability(self):
        engine = self.read("legalai_platform/professional_disposition_m37_3.py")
        route = self.read("legalai_platform/routes/m37_3_disposition_routes.py")
        bridge = self.read("legalai_platform/m37_3_journey_guard.py")
        self.assertIn('"internal_reason_exposed": False', engine)
        self.assertIn('"internal_reason_in_ledger": False', engine)
        self.assertIn('"client_summary_in_ledger": False', engine)
        call = engine[engine.index("controlled_m37_disposition_transition("):engine.index("return self._finalize", engine.index("controlled_m37_disposition_transition("))]
        self.assertIn("client_summary", call)
        self.assertNotIn("internal_reason,", call)
        self.assertIn("str(client_summary)", bridge)
        tree = ast.parse(route)
        observed_keywords = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_observe":
                observed_keywords.update(keyword.arg for keyword in node.keywords if keyword.arg)
        self.assertTrue({"internal_reason", "client_summary"}.isdisjoint(observed_keywords))

    def test_public_model_never_claims_legal_success_or_external_verification(self):
        engine = self.read("legalai_platform/professional_disposition_m37_3.py")
        config = self.read("config/m37/disposition_contracts.json")
        for marker in (
            '"disposition_is_legal_success": false',
            '"disposition_verifies_external_effect": false',
            '"disposition_verifies_evidence_authenticity": false',
            '"disposition_verifies_legal_deadline": false',
            '"automatic_close": false',
            '"automatic_escalation": false',
            '"external_notification": false',
        ):
            self.assertIn(marker, config)
        for forbidden in (
            '"legal_success_verified": True',
            '"external_effect_verified": True',
            '"evidence_authenticity_verified": True',
            '"legal_deadline_verified": True',
        ):
            self.assertNotIn(forbidden, engine)

    def test_handler_preserves_origin_auth_and_csrf_status_contracts(self):
        handler = self.read("legalai_platform/http_handler_m37_3.py")
        self.assertIn("path = urlparse(self.path).path", handler)
        self.assertIn("self.require_origin()", handler)
        self.assertIn("self.require_user()", handler)
        self.assertIn("self.require_csrf()", handler)
        self.assertNotIn("except Exception", handler)
        self.assertIn("return super().do_GET()", handler)
        self.assertIn("return super().do_POST()", handler)

    def test_disposition_intent_and_events_are_integrity_protected(self):
        engine = self.read("legalai_platform/professional_disposition_m37_3.py")
        self.assertIn("intent_hash TEXT NOT NULL", engine)
        self.assertIn("previous_hash TEXT NOT NULL", engine)
        self.assertIn("event_hash TEXT NOT NULL", engine)
        self.assertIn("UNIQUE(intent_id,sequence)", engine)
        self.assertIn("DISPOSITION_INTENT_TAMPERED", engine)
        self.assertIn("DISPOSITION_EVENT_CHAIN_TAMPERED", engine)
        self.assertNotIn("UPDATE m37_disposition_intent", engine)
        self.assertNotIn("UPDATE m37_disposition_event", engine)

    def test_m373_has_no_email_sms_or_automatic_lifecycle_action(self):
        engine = self.read("legalai_platform/professional_disposition_m37_3.py")
        route = self.read("legalai_platform/routes/m37_3_disposition_routes.py")
        for forbidden in ("send_email", "smtp", "send_sms", "twilio"):
            self.assertNotIn(forbidden, engine.casefold())
            self.assertNotIn(forbidden, route.casefold())
        self.assertIn('"automatic": False', engine)

    def test_ci_runs_m373_after_m372(self):
        ci = self.read(".github/workflows/ci.yml")
        self.assertIn("python tools/m37_2_http_smoke.py", ci)
        self.assertIn("python tools/m37_3_http_smoke.py", ci)
        self.assertLess(ci.index("python tools/m37_2_http_smoke.py"), ci.index("python tools/m37_3_http_smoke.py"))


if __name__ == "__main__":
    unittest.main()
