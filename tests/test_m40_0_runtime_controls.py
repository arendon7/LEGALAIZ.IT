from __future__ import annotations

import sqlite3
import unittest

from legalai_platform.ai_gateway_m40_0 import (
    AIGatewayError,
    AIRequest,
    StaticDeterministicProvider,
    public_preauth_access,
)
from legalai_platform.ai_runtime_m40_0 import AIAuditLedger, GovernedAIExecutor


EMPTY_OUTPUT = {
    "schema_version": "40.0.0",
    "actions": [{"type": "NO_ACTION"}],
    "confidence": 0.5,
    "source_ids": [],
}


class MutableClock:
    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class CountingFailureProvider:
    provider_id = "m40.test.failure.v1"
    provider_mode = "TEST_FAILURE"
    model_id = "failure-fixture-v1"
    external = False

    def __init__(self):
        self.calls = 0

    def invoke(self, context):
        self.calls += 1
        raise RuntimeError("provider raw failure must not leak")


class SlowLocalProvider:
    provider_id = "m40.test.slow.v1"
    provider_mode = "TEST_SLOW"
    model_id = "slow-fixture-v1"
    external = False

    def __init__(self, clock):
        self.clock = clock
        self.calls = 0

    def invoke(self, context):
        self.calls += 1
        self.clock.advance(2.0)
        return dict(EMPTY_OUTPUT)


class ExternalProvider:
    provider_id = "m40.test.external.v1"
    provider_mode = "TEST_EXTERNAL"
    model_id = "external-fixture-v1"
    external = True

    def __init__(self, *, units=100, include_usage=True):
        self.units = units
        self.include_usage = include_usage
        self.calls = 0
        self.timeout_values = []

    def invoke(self, context):
        raise AssertionError("external provider must use invoke_with_timeout")

    def invoke_with_timeout(self, context, timeout_ms):
        self.calls += 1
        self.timeout_values.append(timeout_ms)
        output = dict(EMPTY_OUTPUT)
        if self.include_usage:
            output["_runtime_usage"] = {"units": self.units}
        return output


class ExternalWithoutTimeoutContract:
    provider_id = "m40.test.external.no-timeout.v1"
    provider_mode = "TEST_EXTERNAL"
    model_id = "external-no-timeout-v1"
    external = True

    def __init__(self):
        self.calls = 0

    def invoke(self, context):
        self.calls += 1
        output = dict(EMPTY_OUTPUT)
        output["_runtime_usage"] = {"units": 10}
        return output


class M400RuntimeControlsTests(unittest.TestCase):
    def request(self, *, capability="FACT_EXTRACTION", payload=None):
        return AIRequest(
            request_id="REQ-M40-RUNTIME-001",
            capability=capability,
            access=public_preauth_access("INT-M40-RUNTIME-001"),
            prompt_version="m40.0-runtime-v1",
            payload=payload or {
                "problem_statement": "Necesito revisar un asunto jurídico.",
                "source_reference": "intake:INT-M40-RUNTIME-001:problem_statement",
            },
        )

    def test_local_provider_runs_with_zero_reported_units(self):
        executor = GovernedAIExecutor()
        execution = executor.execute(self.request(), StaticDeterministicProvider(EMPTY_OUTPUT))
        self.assertEqual(execution["runtime"]["total_units"], 0)
        self.assertFalse(execution["runtime"]["fallback_used"])
        self.assertEqual(execution["runtime"]["attempts"][0]["status"], "SUCCESS")
        self.assertTrue(executor.ledger.verify_chain())

    def test_external_provider_uses_explicit_timeout_and_reports_usage(self):
        provider = ExternalProvider(units=321)
        executor = GovernedAIExecutor()
        execution = executor.execute(self.request(), provider, timeout_ms=4321)
        self.assertEqual(provider.timeout_values, [4321])
        self.assertEqual(execution["runtime"]["total_units"], 321)
        self.assertEqual(execution["runtime"]["selected_provider_id"], provider.provider_id)

    def test_external_provider_without_timeout_contract_falls_back_without_invocation(self):
        primary = ExternalWithoutTimeoutContract()
        fallback = StaticDeterministicProvider(EMPTY_OUTPUT)
        executor = GovernedAIExecutor()
        execution = executor.execute(self.request(), primary, fallbacks=[fallback])
        self.assertEqual(primary.calls, 0)
        self.assertTrue(execution["runtime"]["fallback_used"])
        self.assertEqual(execution["runtime"]["attempts"][0]["error_code"], "AI_PROVIDER_TIMEOUT_CONTRACT_REQUIRED")

    def test_external_usage_is_required_fail_closed(self):
        provider = ExternalProvider(include_usage=False)
        executor = GovernedAIExecutor()
        with self.assertRaises(AIGatewayError) as captured:
            executor.execute(self.request(), provider, fallbacks=[StaticDeterministicProvider(EMPTY_OUTPUT)])
        self.assertEqual(captured.exception.code, "AI_USAGE_REQUIRED")
        entries = executor.ledger.entries()
        self.assertEqual(entries[-1]["payload"]["outcome"], "FAILURE")
        self.assertEqual(entries[-1]["payload"]["terminal_error_code"], "AI_USAGE_REQUIRED")

    def test_cumulative_budget_is_terminal_and_blocks_fallback(self):
        provider = ExternalProvider(units=12001)
        fallback = CountingFailureProvider()
        executor = GovernedAIExecutor()
        with self.assertRaises(AIGatewayError) as captured:
            executor.execute(self.request(), provider, fallbacks=[fallback])
        self.assertEqual(captured.exception.code, "AI_BUDGET_EXCEEDED")
        self.assertEqual(fallback.calls, 0)

    def test_provider_failure_uses_fallback_and_records_only_error_code(self):
        primary = CountingFailureProvider()
        fallback = StaticDeterministicProvider(EMPTY_OUTPUT)
        executor = GovernedAIExecutor()
        execution = executor.execute(self.request(), primary, fallbacks=[fallback])
        self.assertTrue(execution["runtime"]["fallback_used"])
        self.assertEqual(execution["runtime"]["attempts"][0]["error_code"], "AI_PROVIDER_FAILURE")
        payload = executor.ledger.entries()[-1]["payload"]
        self.assertNotIn("raw failure", str(payload))

    def test_local_logical_timeout_is_rejected_and_fallback_can_continue(self):
        clock = MutableClock()
        primary = SlowLocalProvider(clock)
        fallback = StaticDeterministicProvider(EMPTY_OUTPUT)
        executor = GovernedAIExecutor(monotonic=clock)
        execution = executor.execute(self.request(), primary, fallbacks=[fallback], timeout_ms=1000)
        self.assertTrue(execution["runtime"]["fallback_used"])
        self.assertEqual(execution["runtime"]["attempts"][0]["error_code"], "AI_PROVIDER_TIMEOUT")

    def test_circuit_opens_after_threshold_and_recovers_after_window(self):
        clock = MutableClock()
        primary = CountingFailureProvider()
        fallback = StaticDeterministicProvider(EMPTY_OUTPUT)
        executor = GovernedAIExecutor(monotonic=clock)
        for _ in range(3):
            executor.execute(self.request(), primary, fallbacks=[fallback])
        self.assertEqual(primary.calls, 3)
        fourth = executor.execute(self.request(), primary, fallbacks=[fallback])
        self.assertEqual(primary.calls, 3)
        self.assertEqual(fourth["runtime"]["attempts"][0]["error_code"], "AI_CIRCUIT_OPEN")
        clock.advance(61)
        executor.execute(self.request(), primary, fallbacks=[fallback])
        self.assertEqual(primary.calls, 4)

    def test_policy_denial_happens_before_any_provider_or_fallback(self):
        primary = CountingFailureProvider()
        fallback = CountingFailureProvider()
        executor = GovernedAIExecutor()
        with self.assertRaises(AIGatewayError) as captured:
            executor.execute(
                self.request(capability="DOCUMENT_ASSIST", payload={"document_text": "Documento privado"}),
                primary,
                fallbacks=[fallback],
            )
        self.assertEqual(captured.exception.code, "AI_POLICY_DENIED")
        self.assertEqual(primary.calls, 0)
        self.assertEqual(fallback.calls, 0)
        self.assertEqual(executor.ledger.entries(), [])

    def test_timeout_cannot_exceed_policy_maximum(self):
        provider = StaticDeterministicProvider(EMPTY_OUTPUT)
        executor = GovernedAIExecutor()
        with self.assertRaises(AIGatewayError) as captured:
            executor.execute(self.request(), provider, timeout_ms=60001)
        self.assertEqual(captured.exception.code, "AI_TIMEOUT_POLICY_DENIED")

    def test_fallback_chain_is_bounded(self):
        provider = StaticDeterministicProvider(EMPTY_OUTPUT)
        fallbacks = [CountingFailureProvider() for _ in range(4)]
        for index, item in enumerate(fallbacks):
            item.provider_id = f"m40.test.failure.{index}.v1"
        executor = GovernedAIExecutor()
        with self.assertRaises(AIGatewayError) as captured:
            executor.execute(self.request(), provider, fallbacks=fallbacks)
        self.assertEqual(captured.exception.code, "AI_PROVIDER_CHAIN_INVALID")

    def test_duplicate_provider_identity_is_rejected(self):
        primary = CountingFailureProvider()
        duplicate = CountingFailureProvider()
        executor = GovernedAIExecutor()
        with self.assertRaises(AIGatewayError) as captured:
            executor.execute(self.request(), primary, fallbacks=[duplicate])
        self.assertEqual(captured.exception.code, "AI_PROVIDER_CHAIN_INVALID")
        self.assertEqual(primary.calls, 0)
        self.assertEqual(duplicate.calls, 0)


class M400AuditLedgerTests(unittest.TestCase):
    def test_ledger_stores_hashes_and_runtime_metadata_not_raw_story(self):
        marker = "RELATO-PRIVADO-RUNTIME-9917"
        request = AIRequest(
            request_id="REQ-M40-LEDGER-001",
            capability="FACT_EXTRACTION",
            access=public_preauth_access("INT-M40-LEDGER-001"),
            prompt_version="m40.0-ledger-v1",
            payload={
                "problem_statement": marker,
                "source_reference": "intake:INT-M40-LEDGER-001:problem_statement",
            },
        )
        ledger = AIAuditLedger()
        executor = GovernedAIExecutor(ledger=ledger)
        executor.execute(request, StaticDeterministicProvider(EMPTY_OUTPUT))
        payload = ledger.entries()[0]["payload"]
        self.assertNotIn(marker, str(payload))
        self.assertNotIn("problem_statement", str(payload))
        self.assertEqual(len(payload["context_hash"]), 64)
        self.assertTrue(ledger.verify_chain())

    def test_database_guards_reject_update_and_delete(self):
        ledger = AIAuditLedger()
        ledger.append({"event_type": "ONE", "request_id": "REQ-1"})
        with self.assertRaises(sqlite3.IntegrityError):
            ledger._connection.execute("UPDATE ai_audit_ledger SET payload_json = '{}' WHERE sequence = 1")
        ledger._connection.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            ledger._connection.execute("DELETE FROM ai_audit_ledger WHERE sequence = 1")
        ledger._connection.rollback()
        self.assertEqual(len(ledger.entries()), 1)
        self.assertTrue(ledger.verify_chain())

    def test_hash_chain_detects_privileged_tampering_after_guards_are_removed(self):
        ledger = AIAuditLedger()
        ledger.append({"event_type": "ONE", "request_id": "REQ-1"})
        ledger.append({"event_type": "TWO", "request_id": "REQ-2"})
        self.assertTrue(ledger.verify_chain())
        ledger._connection.execute("DROP TRIGGER ai_audit_ledger_no_update")
        ledger._connection.execute(
            "UPDATE ai_audit_ledger SET payload_json = ? WHERE sequence = 1",
            ('{"event_type":"TAMPERED"}',),
        )
        ledger._connection.commit()
        self.assertFalse(ledger.verify_chain())

    def test_ledger_chain_links_each_entry_to_previous_hash(self):
        ledger = AIAuditLedger()
        first = ledger.append({"event_type": "ONE"})
        second = ledger.append({"event_type": "TWO"})
        entries = ledger.entries()
        self.assertEqual(entries[0]["previous_hash"], "GENESIS")
        self.assertEqual(entries[1]["previous_hash"], first["entry_hash"])
        self.assertEqual(entries[1]["entry_hash"], second["entry_hash"])
        self.assertTrue(ledger.verify_chain())


if __name__ == "__main__":
    unittest.main()
