from __future__ import annotations

import unittest

from legalai_platform.ai_gateway_m40_0 import (
    AIAccessContext,
    AIGateway,
    AIGatewayError,
    AIRequest,
    StaticDeterministicProvider,
    public_preauth_access,
    tenant_access_from_m39,
)
from legalai_platform.enterprise_tenancy_m39_1 import EnterpriseContext
from legalai_platform.m34_intelligent_journey import fact_is_decision_usable


class M400AIGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.gateway = AIGateway()

    def request(self, *, access=None, capability="FACT_EXTRACTION", payload=None, case_id="", document_id=""):
        return AIRequest(
            request_id="REQ-M40-GOV-001",
            capability=capability,
            access=access or public_preauth_access("INT-GOV-001"),
            prompt_version="m40.0-governance-v1",
            payload=payload or {
                "problem_statement": "Necesito orientación sobre un asunto jurídico.",
                "source_reference": "intake:INT-GOV-001:problem_statement",
            },
            case_id=case_id,
            document_id=document_id,
        )

    def provider(self, action):
        return StaticDeterministicProvider({
            "schema_version": "40.0.0",
            "actions": [action],
            "source_ids": [],
        })

    def test_forbidden_autonomous_actions_fail_closed(self):
        for action_type in (
            "CONFIRM_FACT",
            "APPROVE_LEGAL",
            "APPROVE_QA",
            "RELEASE_DOCUMENT",
            "EXECUTE_PAYMENT",
            "CHANGE_TENANT",
            "OVERWRITE_APPROVED_REVISION",
        ):
            with self.subTest(action_type=action_type):
                with self.assertRaises(AIGatewayError) as captured:
                    self.gateway.execute(self.request(), self.provider({"type": action_type}))
                self.assertEqual(captured.exception.code, "AI_FORBIDDEN_ACTION")

    def test_provider_cannot_promote_fact_to_user_confirmed(self):
        execution = self.gateway.execute(
            self.request(),
            self.provider({
                "type": "PROPOSE_FACT",
                "fact": {
                    "fact_type": "goal.requested_outcome",
                    "value": "reclamar_o_solicitar",
                    "confidence": 0.96,
                    "provenance": "USER_CONFIRMED",
                    "confirmation_status": "CONFIRMED_BY_USER",
                },
            }),
        )
        fact = execution["result"]["actions"][0]["fact"]
        self.assertEqual(fact["provenance"], "AI_INFERRED")
        self.assertEqual(fact["confirmation_status"], "UNCONFIRMED")
        self.assertFalse(fact_is_decision_usable(fact))
        self.assertTrue(execution["result"]["human_confirmation_required"])

    def test_provider_cannot_smuggle_decision_usable_or_approval_state(self):
        for forbidden_key in (
            "decision_usable",
            "legal_approved",
            "qa_approved",
            "payment_executed",
            "release_authorized",
            "tenant_override",
            "approved_revision_overwrite",
        ):
            with self.subTest(forbidden_key=forbidden_key):
                action = {
                    "type": "PROPOSE_FACT",
                    "fact": {
                        "fact_type": "goal.requested_outcome",
                        "value": "revisar_o_verificar",
                        "confidence": 0.7,
                        forbidden_key: True,
                    },
                }
                with self.assertRaises(AIGatewayError) as captured:
                    self.gateway.execute(self.request(), self.provider(action))
                self.assertEqual(captured.exception.code, "AI_RESERVED_STATE_BLOCKED")

    def test_unknown_action_is_not_treated_as_harmless_extension(self):
        with self.assertRaises(AIGatewayError) as captured:
            self.gateway.execute(self.request(), self.provider({"type": "DO_WHATEVER_MODEL_WANTS"}))
        self.assertEqual(captured.exception.code, "AI_ACTION_UNKNOWN")

    def test_risk_flag_is_always_unconfirmed_signal(self):
        execution = self.gateway.execute(
            self.request(),
            self.provider({
                "type": "FLAG_RISK",
                "risk": {
                    "code": "DEADLINE_RISK",
                    "confidence": 0.99,
                    "status": "CONFIRMED_BY_USER",
                },
            }),
        )
        risk = execution["result"]["actions"][0]["risk"]
        self.assertEqual(risk["status"], "UNCONFIRMED_SIGNAL")
        self.assertEqual(risk["code"], "DEADLINE_RISK")

    def test_topic_signal_never_becomes_recommendation(self):
        execution = self.gateway.execute(
            self.request(),
            self.provider({
                "type": "SIGNAL_TOPIC",
                "product": {
                    "product_code": "CO-CD-003",
                    "reason_codes": ["garantia"],
                    "recommended": True,
                },
            }),
        )
        product = execution["result"]["actions"][0]["product"]
        self.assertEqual(product["status"], "TOPIC_SIGNAL_ONLY")
        self.assertNotIn("recommended", product)
        self.assertNotIn("recommendation", execution["result"])

    def test_ai_text_is_draft_and_never_approved_revision(self):
        context = EnterpriseContext(
            organization={"id": "ORG-001", "status": "active"},
            membership={
                "id": "MEM-001",
                "organization_id": "ORG-001",
                "user_id": "USR-001",
                "role": "member",
                "status": "active",
            },
            source="explicit",
        )
        access = tenant_access_from_m39("USR-001", context)
        execution = self.gateway.execute(
            self.request(
                access=access,
                capability="DOCUMENT_ASSIST",
                payload={"document_text": "Versión de trabajo", "facts": []},
                case_id="LZ-001",
                document_id="DOC-001",
            ),
            self.provider({
                "type": "PROPOSE_TEXT",
                "text": "Cláusula propuesta por IA para revisión humana.",
                "purpose": "CLAUSE_DRAFT",
            }),
        )
        action = execution["result"]["actions"][0]
        self.assertEqual(action["status"], "DRAFT_AI_PROPOSAL_REQUIRES_HUMAN_REVIEW")
        self.assertNotIn("approved", action)
        self.assertEqual(execution["audit"]["organization_id"], "ORG-001")
        self.assertEqual(execution["audit"]["case_id"], "LZ-001")
        self.assertEqual(execution["audit"]["document_id"], "DOC-001")

    def test_tenant_context_must_be_derived_from_matching_m39_membership(self):
        mismatch = EnterpriseContext(
            organization={"id": "ORG-A", "status": "active"},
            membership={
                "id": "MEM-A",
                "organization_id": "ORG-A",
                "user_id": "USR-OTHER",
                "role": "member",
                "status": "active",
            },
            source="explicit",
        )
        with self.assertRaises(AIGatewayError) as captured:
            tenant_access_from_m39("USR-001", mismatch)
        self.assertEqual(captured.exception.code, "AI_TENANCY_MISMATCH")

    def test_handcrafted_tenant_context_without_m39_source_is_denied(self):
        access = AIAccessContext(
            scope="TENANT",
            actor_id="USR-001",
            organization_id="ORG-001",
            membership_id="MEM-001",
            tenancy_source="HANDCRAFTED",
        )
        with self.assertRaises(AIGatewayError) as captured:
            self.gateway.execute(
                self.request(
                    access=access,
                    capability="CASE_ASSIST",
                    payload={"case_summary": "Resumen", "facts": []},
                    case_id="LZ-001",
                ),
                self.provider({"type": "NO_ACTION"}),
            )
        self.assertEqual(captured.exception.code, "AI_TENANCY_CONTEXT_REQUIRED")

    def test_inactive_m39_membership_is_denied(self):
        inactive = EnterpriseContext(
            organization={"id": "ORG-001", "status": "active"},
            membership={
                "id": "MEM-001",
                "organization_id": "ORG-001",
                "user_id": "USR-001",
                "role": "member",
                "status": "inactive",
            },
            source="explicit",
        )
        with self.assertRaises(AIGatewayError) as captured:
            tenant_access_from_m39("USR-001", inactive)
        self.assertEqual(captured.exception.code, "AI_TENANCY_INACTIVE")


if __name__ == "__main__":
    unittest.main()
