from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "legalai_platform" / "ai_gateway_m40_0.py"
POLICY = ROOT / "config" / "m40" / "ai_gateway_policy.json"


class M400IntegrationContractTests(unittest.TestCase):
    def test_policy_declares_exact_no_bypass_human_boundaries(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["schema_version"], "40.0.0")
        self.assertEqual(policy["policy_version"], "M40.0-GOVERNED-GATEWAY-V1")
        boundaries = policy["human_boundaries"]
        self.assertTrue(boundaries["ai_fact_requires_confirmation"])
        self.assertTrue(boundaries["legal_approval_must_be_human"])
        self.assertTrue(boundaries["qa_approval_must_be_human"])
        self.assertTrue(boundaries["approved_revision_overwrite_forbidden"])
        self.assertTrue(boundaries["production_payment_execution_forbidden"])

    def test_public_scope_is_strictly_smaller_than_tenant_scope(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        public = set(policy["access_scopes"]["PUBLIC_PREAUTH"]["capabilities"])
        tenant = set(policy["access_scopes"]["TENANT"]["capabilities"])
        self.assertEqual(public, {"FACT_EXTRACTION", "INTAKE_ASSIST"})
        self.assertTrue(public < tenant)
        self.assertFalse(policy["access_scopes"]["PUBLIC_PREAUTH"]["case_or_document_context_allowed"])
        self.assertTrue(policy["access_scopes"]["TENANT"]["tenant_required"])

    def test_forbidden_actions_cover_approval_release_payment_and_tenant_mutation(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        forbidden = set(policy["forbidden_action_types"])
        self.assertTrue({
            "CONFIRM_FACT",
            "APPROVE_LEGAL",
            "APPROVE_QA",
            "RELEASE_DOCUMENT",
            "EXECUTE_PAYMENT",
            "CHANGE_TENANT",
            "OVERWRITE_APPROVED_REVISION",
        }.issubset(forbidden))

    def test_audit_policy_never_persists_raw_input_or_output(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        audit = policy["audit"]
        self.assertFalse(audit["store_raw_input"])
        self.assertFalse(audit["store_raw_output"])
        self.assertTrue(audit["store_input_hash"])
        self.assertTrue(audit["store_output_hash"])
        self.assertTrue(audit["store_action_types_only"])

    def test_gateway_reuses_m34_fact_model_and_m39_tenancy_contract(self):
        source = GATEWAY.read_text(encoding="utf-8")
        self.assertIn("FactExtractionService", source)
        self.assertIn("validate_legal_fact", source)
        self.assertIn("fact_is_decision_usable", source)
        self.assertIn("EnterpriseContext", source)
        self.assertIn("M39_1:", source)
        self.assertIn("M34FactExtractionAdapter", source)

    def test_gateway_foundation_has_no_network_or_http_runtime_side_effect(self):
        source = GATEWAY.read_text(encoding="utf-8")
        for forbidden in (
            "import requests",
            "import httpx",
            "import urllib.request",
            "import socket",
            "BaseHTTPRequestHandler",
            "do_POST",
            "do_GET",
        ):
            self.assertNotIn(forbidden, source)

    def test_gateway_does_not_define_autonomous_mutation_methods(self):
        source = GATEWAY.read_text(encoding="utf-8")
        for forbidden in (
            "def approve_legal",
            "def approve_qa",
            "def release_document",
            "def execute_payment",
            "def overwrite_approved_revision",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
