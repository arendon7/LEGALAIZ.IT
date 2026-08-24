from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M371IntegrationContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_runtime_is_incremental_on_certified_m370_handler(self):
        run = self.read("run.py")
        handler = self.read("legalai_platform/http_handler_m37_1.py")
        self.assertIn("from legalai_platform.http_handler_m37_1 import Handler", run)
        self.assertIn("from legalai_platform.http_handler_m37_0 import Handler  # compatibility marker", run)
        self.assertIn("class Handler(BaseHandler)", handler)
        self.assertIn("http_handler_m37_0 import Handler as BaseHandler", handler)
        self.assertIn("m37-1-evidence-intake-review-boundary", run)

    def test_handler_uses_real_path_origin_auth_and_csrf_contracts(self):
        handler = self.read("legalai_platform/http_handler_m37_1.py")
        self.assertIn("path = urlparse(self.path).path", handler)
        self.assertNotIn("self._path()", handler)
        self.assertIn("self.require_origin()", handler)
        self.assertIn("self.require_user()", handler)
        self.assertIn("self.require_csrf()", handler)
        self.assertNotIn("self.require_csrf(user)", handler)
        self.assertIn("return super().do_GET()", handler)
        self.assertIn("return super().do_POST()", handler)

    def test_upload_is_multipart_single_file_and_content_type_is_untrusted(self):
        route = self.read("legalai_platform/routes/m37_1_evidence_routes.py")
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("handler.read_multipart()", route)
        self.assertIn("len(files) != 1", route)
        self.assertIn("claimed_content_type_trusted", engine)
        self.assertIn("False", engine[engine.index("claimed_content_type_trusted"):engine.index("claimed_content_type_trusted") + 100])
        self.assertNotIn("mime_type = claimed_content_type", engine)
        self.assertIn("_validate_file", engine)

    def test_malware_scan_and_exact_hash_revalidation_are_mandatory(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("self.malware_scanner.scan", engine)
        self.assertIn("_sha256_file", engine)
        self.assertIn("EVIDENCE_FILE_TAMPERED", engine)
        self.assertIn("EVIDENCE_SCAN_UNAVAILABLE", engine)
        self.assertIn("not_scanned_local", engine)

    def test_file_policy_excludes_active_docx_and_unbounded_zip_expansion(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("vbaproject.bin", engine.casefold())
        self.assertIn("/embeddings/", engine)
        self.assertIn("50 * 1024 * 1024", engine)
        self.assertIn("len(infos) > 1000", engine)
        self.assertIn("EVIDENCE_DOCX_PATH_INVALID", engine)

    def test_upload_and_review_never_complete_followup_task(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        config = self.read("config/m37/evidence_contracts.json")
        self.assertIn('"upload_completes_task": false', config)
        self.assertIn('"review_completes_task": false', config)
        self.assertNotIn("controlled_follow_up_update", engine)
        self.assertNotIn("UPDATE m24_case_follow_up", engine)
        self.assertIn('"task_status_changed": False', engine)

    def test_review_language_never_becomes_authenticity_or_legal_verification(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        config = self.read("config/m37/evidence_contracts.json")
        for marker in (
            '"authenticity_verified": False',
            '"legal_sufficiency_verified": False',
            '"legal_effect_verified": False',
        ):
            self.assertIn(marker, engine)
        self.assertNotIn('"authenticity_verified": True', engine)
        self.assertNotIn('"legal_sufficiency_verified": True', engine)
        self.assertNotIn('"legal_effect_verified": True', engine)
        self.assertIn('"authenticity_verified_by_review": false', config)
        self.assertIn('"legal_sufficiency_verified_by_review": false', config)
        self.assertIn('"legal_effect_verified_by_review": false', config)

    def test_public_model_excludes_paths_hashes_actor_ids_and_scan_details(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        public_section = engine[engine.index("def _public_item") : engine.index("def upload")]
        self.assertNotIn('"file_path"', public_section)
        self.assertNotIn('"sha256"', public_section)
        self.assertNotIn('"uploader_id"', public_section)
        self.assertNotIn('"reviewer_id"', public_section)
        self.assertNotIn('"scan_engine"', public_section)
        self.assertNotIn('"scan_detail"', public_section)

    def test_observability_never_logs_filename_hash_message_or_legal_payload(self):
        route = self.read("legalai_platform/routes/m37_1_evidence_routes.py")
        for forbidden in (
            "filename=",
            "sha256=",
            "message_to_client=",
            "problem_statement",
            "answers=",
            "file_path=",
            "scan_detail=",
            "payment_intent_id=",
        ):
            self.assertNotIn(forbidden, route)
        self.assertIn("ip_hash", route)

    def test_only_assigned_specialist_or_admin_can_review(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("_require_reviewer", engine)
        self.assertIn('role == "admin"', engine)
        self.assertIn('role == "specialist"', engine)
        self.assertIn('case.get("specialist_id")', engine)
        route = self.read("legalai_platform/routes/m37_1_evidence_routes.py")
        self.assertIn('parts[4] == "review"', route)

    def test_evidence_events_reuse_m37_chain_and_do_not_store_review_message(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("self.followup._append_event", engine)
        self.assertIn('"EVIDENCE_RECEIVED"', engine)
        self.assertIn('"EVIDENCE_REVIEW_RECORDED"', engine)
        review_event = engine[engine.index('"EVIDENCE_REVIEW_RECORDED"'):engine.index("task_after", engine.index('"EVIDENCE_REVIEW_RECORDED"'))]
        self.assertIn('"message_present": bool(message)', review_event)
        self.assertNotIn('"message_to_client": message', review_event)

    def test_m371_has_no_close_escalate_or_external_delivery_actions(self):
        route = self.read("legalai_platform/routes/m37_1_evidence_routes.py")
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        for forbidden in ('"close"', '"escalate"', "send_email", "smtp", 'target_state'):
            self.assertNotIn(forbidden, route)
        self.assertNotIn("journey.transition", engine)
        self.assertIn('"automatic_close": False', engine)
        self.assertIn('"automatic_escalation": False', engine)


if __name__ == "__main__":
    unittest.main()
