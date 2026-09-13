from __future__ import annotations

import json
import unittest

from legalai_platform.ai_gateway_m40_0 import (
    AICapability,
    AIGateway,
    AIGatewayError,
    AIRequest,
    M34FactExtractionAdapter,
    StaticDeterministicProvider,
    public_preauth_access,
)
from legalai_platform.m34_intelligent_journey import fact_is_decision_usable


class BadProvider:
    provider_id = "provider id with spaces"
    provider_mode = "unsafe mode"
    model_id = "bad model"
    external = True

    def invoke(self, context):
        return {"schema_version": "40.0.0", "actions": [], "source_ids": []}


class M400AIGatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = AIGateway()

    def request(self, *, capability="FACT_EXTRACTION", payload=None, case_id="", document_id=""):
        return AIRequest(
            request_id="REQ-M40-0001",
            capability=capability,
            access=public_preauth_access("INT-PUBLIC-001"),
            prompt_version="m40.0-test-v1",
            payload=payload or {
                "problem_statement": "Tengo una fotomulta y nunca me notificaron el comparendo. Quiero revisar el caso.",
                "source_reference": "intake:INT-PUBLIC-001:problem_statement",
            },
            case_id=case_id,
            document_id=document_id,
        )

    def test_static_provider_is_deterministic_at_governed_boundary(self):
        provider = StaticDeterministicProvider({
            "schema_version": "40.0.0",
            "actions": [{"type": "NO_ACTION"}],
            "confidence": 0.5,
            "source_ids": [],
        })
        request = self.request()
        first = self.gateway.execute(request, provider)
        second = self.gateway.execute(request, provider)
        self.assertEqual(first["result"], second["result"])
        self.assertEqual(first["audit"]["input_hash"], second["audit"]["input_hash"])
        self.assertEqual(first["audit"]["output_hash"], second["audit"]["output_hash"])
        self.assertEqual(first["audit"]["audit_id"], second["audit"]["audit_id"])
        self.assertFalse(first["audit"]["provider"]["external"])

    def test_m34_adapter_preserves_unconfirmed_fact_boundary(self):
        execution = self.gateway.execute(self.request(), M34FactExtractionAdapter())
        actions = execution["result"]["actions"]
        facts = [item["fact"] for item in actions if item["type"] == "PROPOSE_FACT"]
        topics = [item["product"] for item in actions if item["type"] == "SIGNAL_TOPIC"]
        self.assertTrue(facts)
        self.assertIn("CO-TR-002", {item["product_code"] for item in topics})
        for fact in facts:
            self.assertEqual(fact["provenance"], "AI_INFERRED")
            self.assertEqual(fact["confirmation_status"], "UNCONFIRMED")
            self.assertFalse(fact_is_decision_usable(fact))
        self.assertTrue(execution["result"]["human_confirmation_required"])
        self.assertEqual(execution["audit"]["provider"]["model_id"], "m34.local.conservative.v1")

    def test_public_preauth_cannot_access_private_case_or_document(self):
        provider = StaticDeterministicProvider({
            "schema_version": "40.0.0",
            "actions": [],
            "source_ids": [],
        })
        with self.assertRaisesRegex(AIGatewayError, "expedientes ni documentos privados"):
            self.gateway.execute(self.request(case_id="LZ-PRIVATE-001"), provider)
        with self.assertRaisesRegex(AIGatewayError, "expedientes ni documentos privados"):
            self.gateway.execute(self.request(document_id="DOC-PRIVATE-001"), provider)

    def test_public_preauth_cannot_request_tenant_only_capability(self):
        provider = StaticDeterministicProvider({
            "schema_version": "40.0.0",
            "actions": [],
            "source_ids": [],
        })
        with self.assertRaisesRegex(AIGatewayError, "no está habilitada para este alcance"):
            self.gateway.execute(
                self.request(
                    capability=AICapability.DOCUMENT_ASSIST.value,
                    payload={"document_text": "Texto contractual."},
                ),
                provider,
            )

    def test_context_is_allowlisted_per_capability(self):
        provider = StaticDeterministicProvider({
            "schema_version": "40.0.0",
            "actions": [],
            "source_ids": [],
        })
        with self.assertRaisesRegex(AIGatewayError, "claves de contexto no permitidas"):
            self.gateway.execute(
                self.request(payload={
                    "problem_statement": "Relato",
                    "source_reference": "intake:1:problem_statement",
                    "document_text": "No pertenece a FACT_EXTRACTION",
                }),
                provider,
            )

    def test_sensitive_context_keys_are_blocked_recursively(self):
        provider = StaticDeterministicProvider({
            "schema_version": "40.0.0",
            "actions": [],
            "source_ids": [],
        })
        with self.assertRaisesRegex(AIGatewayError, "clave sensible"):
            self.gateway.execute(
                self.request(payload={
                    "problem_statement": "Relato",
                    "source_reference": "intake:1:problem_statement",
                    "allowed_fact_types": {"nested": {"api_token": "must-never-reach-provider"}},
                }),
                provider,
            )

    def test_provider_metadata_is_validated_before_output_is_trusted(self):
        with self.assertRaisesRegex(AIGatewayError, "identificador del proveedor"):
            self.gateway.execute(self.request(), BadProvider())

    def test_malformed_provider_output_fails_closed(self):
        provider = StaticDeterministicProvider({
            "schema_version": "39.9.0",
            "actions": [],
            "source_ids": [],
        })
        with self.assertRaisesRegex(AIGatewayError, "esquema M40.0"):
            self.gateway.execute(self.request(), provider)

    def test_audit_contains_hashes_and_metadata_not_raw_story_or_values(self):
        marker = "RELATO-SUPER-SENSIBLE-9481"
        output_marker = "BORRADOR-SENSIBLE-7722"
        request = AIRequest(
            request_id="REQ-M40-AUDIT-001",
            capability="FACT_EXTRACTION",
            access=public_preauth_access("INT-AUDIT-001"),
            prompt_version="m40.0-audit-v1",
            payload={
                "problem_statement": marker,
                "source_reference": "intake:INT-AUDIT-001:problem_statement",
            },
        )
        provider = StaticDeterministicProvider({
            "schema_version": "40.0.0",
            "actions": [{
                "type": "PROPOSE_FACT",
                "fact": {
                    "fact_type": "goal.requested_outcome",
                    "value": output_marker,
                    "confidence": 0.61,
                },
            }],
            "source_ids": ["SRC-OFFICIAL-001"],
        })
        execution = self.gateway.execute(request, provider)
        audit = json.dumps(execution["audit"], ensure_ascii=False)
        self.assertNotIn(marker, audit)
        self.assertNotIn(output_marker, audit)
        self.assertNotIn("problem_statement", audit)
        self.assertIn("input_hash", execution["audit"])
        self.assertIn("output_hash", execution["audit"])
        self.assertEqual(execution["audit"]["output"]["action_types"], ["PROPOSE_FACT"])
        self.assertEqual(execution["audit"]["source_ids"], ["SRC-OFFICIAL-001"])


if __name__ == "__main__":
    unittest.main()
