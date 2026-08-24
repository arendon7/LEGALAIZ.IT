from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M363IntegrationContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_runtime_is_incremental_on_certified_m362_handler(self):
        run = self.read("run.py")
        handler = self.read("legalai_platform/http_handler_m36_3.py")
        self.assertIn("from legalai_platform.http_handler_m36_3 import Handler", run)
        self.assertIn("from legalai_platform.http_handler_m36_2 import Handler  # compatibility marker", run)
        self.assertIn("class Handler(BaseHandler)", handler)
        self.assertIn("http_handler_m36_2 import Handler as BaseHandler", handler)
        self.assertIn("m36-3-controlled-delivery-gate", run)

    def test_internal_m24_singleton_guard_is_installed(self):
        run = self.read("run.py")
        guard = self.read("legalai_platform/m36_3_journey_guard.py")
        self.assertIn("install_m36_3_delivery_guard(M24_CASE_JOURNEY)", run)
        self.assertIn("m36_controlled_delivery", guard)
        self.assertIn('str(row["state"] or "") != "PREPARED"', guard)
        self.assertIn('payload.get("source") == "m36_3_controlled_delivery"', guard)
        self.assertIn('payload.get("channel") == "IN_APP"', guard)

    def test_generic_m24_http_delivery_is_blocked_for_m36_cases(self):
        route = self.read("legalai_platform/routes/m24_case_routes.py")
        self.assertIn("_requires_m36_controlled_delivery", route)
        self.assertIn('target == "ENTREGADO"', route)
        self.assertIn("M36_CONTROLLED_DELIVERY_REQUIRED", route)
        self.assertIn("m36_fulfillment_intake", route)

    def test_delivery_write_requires_origin_authenticated_session_and_csrf(self):
        handler = self.read("legalai_platform/http_handler_m36_3.py")
        self.assertIn("self.require_origin()", handler)
        self.assertIn("self.require_user()", handler)
        self.assertIn("self.require_csrf(user)", handler)
        route = self.read("legalai_platform/routes/m36_3_controlled_delivery_routes.py")
        self.assertIn('parts[2] != "deliver"', route)
        self.assertIn("delivery_center().deliver", route)
        self.assertNotIn("target_state", route)

    def test_only_admin_executes_delivery_but_owner_may_read_and_download(self):
        engine = self.read("legalai_platform/controlled_delivery_m36_3.py")
        self.assertIn("Solo administración puede ejecutar la entrega controlada", engine)
        self.assertIn('role == "client" and actor_id', engine)
        self.assertIn('actor_id == str(case.get("owner_id") or "")', engine)
        self.assertIn("DOWNLOAD_REQUESTED", engine)
        self.assertNotIn("DOWNLOAD_RECEIVED", engine)
        self.assertNotIn("RECEIPT_CONFIRMED", engine)

    def test_source_is_released_m32_copy_not_documents_file_path(self):
        engine = self.read("legalai_platform/controlled_delivery_m36_3.py")
        self.assertIn("self.workspace.released_path(actor, desk_id)", engine)
        self.assertIn("M32_RELEASED_EXACT_HASH_ONLY", engine)
        self.assertNotIn('SELECT file_path FROM documents', engine)
        self.assertNotIn('documents.file_path', engine.split('"""', 2)[-1])

    def test_delivery_state_does_not_claim_download_read_or_external_receipt(self):
        engine = self.read("legalai_platform/controlled_delivery_m36_3.py")
        self.assertIn("DELIVERED_IN_APP", engine)
        self.assertIn("download_request_is_not_receipt_confirmation", engine)
        self.assertIn("delivery_state_means_in_app_availability", engine)
        self.assertIn('"external_notification_sent": False', engine)
        self.assertIn('"download_confirmed": False', engine)

    def test_public_model_excludes_internal_release_and_assignment_plumbing(self):
        engine = self.read("legalai_platform/controlled_delivery_m36_3.py")
        public_section = engine[engine.index("def _public(cls") :]
        for forbidden in (
            "package_path",
            "release_snapshot_json",
            "release_snapshot_sha256",
            "release_record_hash",
            "fulfillment_intake_id",
            "assignment_id",
            "m24_transition_id",
            "delivered_by",
        ):
            self.assertNotIn(forbidden, public_section)

    def test_observability_does_not_log_hashes_paths_or_legal_payloads(self):
        route = self.read("legalai_platform/routes/m36_3_controlled_delivery_routes.py")
        for forbidden in (
            "package_sha256=",
            "manifest_sha256=",
            "package_path=",
            "release_snapshot",
            "problem_statement",
            "answers=",
            "receipt_number",
            "payment_intent_id",
        ):
            self.assertNotIn(forbidden, route)
        self.assertIn("ip_hash", route)

    def test_m363_never_creates_legal_or_qa_approval_and_never_sends_email(self):
        engine = self.read("legalai_platform/controlled_delivery_m36_3.py")
        self.assertNotIn(".approve(", engine)
        self.assertNotIn("send_email", engine)
        self.assertNotIn("smtp", engine.lower())
        self.assertIn('"automatic_legal_approval": False', engine)
        self.assertIn('"automatic_qa_approval": False', engine)

    def test_ci_runs_m363_after_m362_with_fresh_process_only(self):
        workflow = self.read(".github/workflows/ci.yml")
        m362 = workflow.index("python tools/m36_2_http_smoke.py")
        restart = workflow.index("start_server /tmp/legalaiz-m36-3.log")
        m363 = workflow.index("python tools/m36_3_http_smoke.py")
        self.assertLess(m362, restart)
        self.assertLess(restart, m363)
        between = workflow[m362:m363]
        self.assertIn("stop_server", between)
        self.assertIn("misma clave", between)
        self.assertIn("12/300", between)
        self.assertNotIn("RATE_LIMIT_DISABLE", workflow)
        self.assertNotIn("LOGIN_RATE_LIMIT", workflow)
        self.assertNotIn("LEGAL_DISABLE_RATE", workflow)


if __name__ == "__main__":
    unittest.main()
