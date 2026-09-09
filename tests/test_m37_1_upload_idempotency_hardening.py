from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M371UploadIdempotencyHardeningTests(unittest.TestCase):
    def test_exact_retry_precedes_quota_scan_and_object_write(self):
        source = (ROOT / "legalai_platform/evidence_intake_m37_1.py").read_text(encoding="utf-8")
        upload = source[source.index("    def upload(") : source.index("    @staticmethod\n    def _require_reviewer")]
        retry = upload.index("existing = self._exact_retry")
        quota = upload.index("self._check_quota")
        scan = upload.index("self.malware_scanner.scan")
        write = upload.index("self.object_store.put")
        self.assertLess(retry, quota)
        self.assertLess(retry, scan)
        self.assertLess(retry, write)
        self.assertIn('result["idempotent"] = True', upload)
        self.assertIn('result["idempotent"] = False', upload)

    def test_exact_retry_identity_is_case_task_name_hash_and_size(self):
        source = (ROOT / "legalai_platform/evidence_intake_m37_1.py").read_text(encoding="utf-8")
        section = source[source.index("    def _exact_retry") : source.index("    def _verify_content")]
        for field in ("case_id=?", "follow_up_id=?", "original_name=?", "plaintext_sha256=?", "size_bytes=?"):
            self.assertIn(field, section)

    def test_followup_ledger_does_not_duplicate_evidence_hash(self):
        source = (ROOT / "legalai_platform/evidence_intake_m37_1.py").read_text(encoding="utf-8")
        event = source[source.index('"EVIDENCE_RECEIVED"') : source.index("after = con.execute", source.index('"EVIDENCE_RECEIVED"'))]
        self.assertNotIn("evidence_sha256", event)
        self.assertNotIn("plaintext_sha256", event)
        self.assertIn('"evidence_id": evidence_id', event)
        self.assertIn('"encrypted_at_rest": True', event)


if __name__ == "__main__":
    unittest.main()
