from __future__ import annotations

import ast
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

    def test_runtime_factory_reuses_platform_encrypted_object_store(self):
        route = self.read("legalai_platform/routes/m37_1_evidence_routes.py")
        config = self.read("config/m37/evidence_contracts.json")
        self.assertIn("INFRA.objects", route)
        self.assertIn("EvidenceIntakeCenter(followup_center(), MALWARE_SCANNER, INFRA.objects)", route)
        self.assertIn('"encrypted_object_store_required": true', config)
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("self.object_store.put", engine)
        self.assertIn("self.object_store.get", engine)
        self.assertIn("self.object_store.is_reference", engine)
        self.assertNotIn("write_bytes(body)", engine)

    def test_download_decrypts_through_store_and_never_serves_ciphertext_path(self):
        route = self.read("legalai_platform/routes/m37_1_evidence_routes.py")
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("body, name, mime_type, public = center.download", route)
        self.assertIn("handler.send_bytes(body, mime_type, filename=name)", route)
        self.assertNotIn("handler.send_file", route)
        self.assertIn("data = self.object_store.get(con, reference)", engine)
        self.assertIn("return data, core.safe_filename", engine)

    def test_upload_is_multipart_single_file_and_content_type_is_untrusted(self):
        route = self.read("legalai_platform/routes/m37_1_evidence_routes.py")
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("handler.read_multipart()", route)
        self.assertIn("len(files) != 1", route)
        self.assertIn("claimed_content_type_trusted", engine)
        self.assertIn("False", engine[engine.index("claimed_content_type_trusted"):engine.index("claimed_content_type_trusted") + 100])
        self.assertNotIn("mime_type = claimed_content_type", engine)
        self.assertIn("_validate_file", engine)

    def test_malware_scan_and_object_integrity_revalidation_are_mandatory(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("self.malware_scanner.scan", engine)
        self.assertIn("self.object_store.get", engine)
        self.assertIn("EVIDENCE_OBJECT_TAMPERED", engine)
        self.assertIn("EVIDENCE_SCAN_UNAVAILABLE", engine)
        self.assertIn("not_scanned_local", engine)
        self.assertIn("plaintext_sha256", engine)

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

    def test_public_model_excludes_object_refs_hashes_actor_ids_and_scan_details(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        public_section = engine[engine.index("def _public_item") : engine.index("def upload")]
        self.assertNotIn('"object_ref"', public_section)
        self.assertNotIn('"plaintext_sha256"', public_section)
        self.assertNotIn('"uploader_id"', public_section)
        self.assertNotIn('"reviewer_id"', public_section)
        self.assertNotIn('"scan_engine"', public_section)
        self.assertNotIn('"scan_detail"', public_section)

    def test_observability_never_logs_filename_hash_message_or_legal_payload(self):
        route = self.read("legalai_platform/routes/m37_1_evidence_routes.py")
        tree = ast.parse(route)
        observe_keys: set[str] = set()
        observe_calls = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "_observe":
                continue
            observe_calls += 1
            observe_keys.update(keyword.arg for keyword in node.keywords if keyword.arg)
        self.assertGreater(observe_calls, 0)
        forbidden = {
            "filename",
            "sha256",
            "message_to_client",
            "problem_statement",
            "answers",
            "object_ref",
            "scan_detail",
            "payment_intent_id",
        }
        self.assertTrue(forbidden.isdisjoint(observe_keys), sorted(forbidden & observe_keys))
        self.assertIn("ip_hash", observe_keys)

    def test_only_assigned_specialist_or_admin_can_review(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("_require_reviewer", engine)
        self.assertIn('role == "admin"', engine)
        self.assertIn('role == "specialist"', engine)
        self.assertIn('case.get("specialist_id")', engine)
        route = self.read("legalai_platform/routes/m37_1_evidence_routes.py")
        self.assertIn('parts[4] == "review"', route)

    def test_reviews_are_append_only_with_explicit_monotonic_sequence(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("sequence INTEGER NOT NULL", engine)
        self.assertIn("UNIQUE(evidence_id,sequence)", engine)
        self.assertIn("ORDER BY sequence DESC LIMIT 1", engine)
        self.assertIn("MAX(sequence)", engine)
        self.assertNotIn("UPDATE m37_evidence_review", engine)

    def test_evidence_events_reuse_m37_chain_and_do_not_store_review_message(self):
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        self.assertIn("self.followup._append_event", engine)
        self.assertIn('"EVIDENCE_RECEIVED"', engine)
        self.assertIn('"EVIDENCE_REVIEW_RECORDED"', engine)
        review_event = engine[engine.index('"EVIDENCE_REVIEW_RECORDED"'):engine.index("task_after", engine.index('"EVIDENCE_REVIEW_RECORDED"'))]
        self.assertIn('"message_present": bool(message)', review_event)
        self.assertNotIn('"message_to_client": message', review_event)

    def test_storage_quotas_are_explicit_and_checked_before_object_write(self):
        config = self.read("config/m37/evidence_contracts.json")
        engine = self.read("legalai_platform/evidence_intake_m37_1.py")
        for marker in ("max_items_per_case", "max_items_per_task", "max_total_bytes_per_case"):
            self.assertIn(f'"{marker}"', config)
            self.assertIn(marker, engine)
        quota_pos = engine.index("self._check_quota")
        store_pos = engine.index("self.object_store.put", quota_pos)
        self.assertLess(quota_pos, store_pos)

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
