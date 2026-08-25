from __future__ import annotations

from pathlib import Path
from unittest import TestCase
import json


ROOT = Path(__file__).resolve().parents[1]


class V1R0IntegrationContractTests(TestCase):
    def test_runtime_is_incremental_on_certified_m373_handler(self):
        source = (ROOT / "run.py").read_text(encoding="utf-8")
        handler = (ROOT / "legalai_platform" / "http_handler_release_v1.py").read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.http_handler_release_v1 import Handler", source)
        self.assertIn("from legalai_platform.http_handler_m37_3 import Handler as BaseHandler", handler)
        self.assertIn("# from legalai_platform.http_handler_m37_3 import Handler  # compatibility marker", source)
        self.assertIn("# v1-r0-release-readiness-gate", source)

    def test_endpoint_is_admin_only_and_read_only(self):
        handler = (ROOT / "legalai_platform" / "http_handler_release_v1.py").read_text(encoding="utf-8")
        self.assertIn('roles={"admin"}', handler)
        self.assertIn("def do_GET", handler)
        self.assertNotIn("def do_POST", handler)
        self.assertNotIn("require_csrf", handler)

    def test_readiness_never_mutates_release_flags(self):
        source = (ROOT / "legalai_platform" / "release_readiness_v1.py").read_text(encoding="utf-8")
        forbidden_writes = [
            "os.environ[",
            "REAL_PRODUCTION_AUTHORIZED =",
            "REAL_PAYMENTS_AUTHORIZED =",
            "SYNTHETIC_DATA_ONLY =",
            "UPDATE release",
            "INSERT INTO release",
        ]
        for marker in forbidden_writes:
            self.assertNotIn(marker, source)
        metadata = (ROOT / "legalai_platform" / "release_metadata.py").read_text(encoding="utf-8")
        self.assertIn("REAL_PRODUCTION_AUTHORIZED = False", metadata)
        self.assertIn("REAL_PAYMENTS_AUTHORIZED = False", metadata)
        self.assertIn("SYNTHETIC_DATA_ONLY = True", metadata)

    def test_contract_preserves_current_portfolio_floor_and_full_m34_m37_stack(self):
        contract = json.loads((ROOT / "config" / "release" / "v1_readiness_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["portfolio_floor"], {"products": 11, "questions": 473})
        markers = contract["required_runtime_markers"]
        self.assertEqual(len(markers), 16)
        self.assertEqual(len(markers), len(set(markers)))
        self.assertIn("m34-1-intelligent-intake-ux", markers)
        self.assertIn("m37-3-professional-disposition-gate", markers)

    def test_postgres_evidence_claim_is_backed_by_real_files_or_reported_missing(self):
        contract = json.loads((ROOT / "config" / "release" / "v1_readiness_contract.json").read_text(encoding="utf-8"))
        expected = contract["required_repository_evidence"]
        self.assertEqual(expected["postgres_certification_tool"], "tools/postgres_certify.py")
        self.assertEqual(expected["postgres_migration_tool"], "tools/migrate_sqlite_to_postgres.py")
        evaluator = (ROOT / "legalai_platform" / "release_readiness_v1.py").read_text(encoding="utf-8")
        self.assertIn("path.is_file()", evaluator)
        self.assertIn("repository_evidence_missing", evaluator)

    def test_public_model_excludes_secrets_and_user_level_mfa_inventory(self):
        source = (ROOT / "legalai_platform" / "release_readiness_v1.py").read_text(encoding="utf-8")
        route = (ROOT / "legalai_platform" / "routes" / "release_readiness_v1_routes.py").read_text(encoding="utf-8")
        self.assertNotIn('doctor["checks"]', route)
        self.assertNotIn("database_url", route)
        self.assertNotIn("master_key_seed", route.lower())
        self.assertNotIn("actor_id=", route)
        self.assertNotIn('mfa["users"]', source)

    def test_governance_keeps_technical_and_human_approvals_separate(self):
        source = (ROOT / "legalai_platform" / "release_readiness_v1.py").read_text(encoding="utf-8")
        for marker in (
            '"self_authorization": False',
            '"technical_readiness_is_legal_approval": False',
            '"technical_readiness_is_qa_approval": False',
            '"technical_readiness_is_security_approval": False',
            '"technical_readiness_is_privacy_approval": False',
            '"real_payments_are_separate": True',
        ):
            self.assertIn(marker, source)
