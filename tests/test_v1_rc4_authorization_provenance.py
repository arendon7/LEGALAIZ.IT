from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from legalai_platform import release_metadata
from legalai_platform.release_readiness_v1 import _authorization_state, assess_release_readiness


ROOT = Path(__file__).resolve().parents[1]
REAL_SPEC = {
    "metadata_gate": "REAL_PRODUCTION_AUTHORIZED",
    "required_status": "AUTHORIZED_VERSIONED_HUMAN_DECISION",
    "required_source": "VERSIONED_HUMAN_RELEASE_DECISION",
    "blocker": "REAL_PRODUCTION_AUTHORIZATION_DECISION",
}


class V1RC4AuthorizationProvenanceTests(unittest.TestCase):
    def test_current_release_remains_consistently_not_authorized(self) -> None:
        report = assess_release_readiness(ROOT)
        real = report["real_legal_production"]
        commercial = report["commercial_v1"]
        governance = report["governance"]

        self.assertTrue(report["code_release_candidate"]["ready"], report)
        self.assertFalse(real["ready"])
        self.assertFalse(commercial["ready"])
        self.assertIn("REAL_PRODUCTION_AUTHORIZATION_DECISION", real["blockers"])
        self.assertIn("REAL_PAYMENTS_AUTHORIZATION_DECISION", commercial["blockers"])
        self.assertEqual(real["authorization_decision"]["decision_status"], "NOT_AUTHORIZED")
        self.assertEqual(commercial["authorization_decision"]["decision_status"], "NOT_AUTHORIZED")
        self.assertFalse(governance["authorization_state_inconsistent"])
        self.assertFalse(governance["unauthorized_promotion_detected"])

    def test_ci_policy_remains_unable_to_authorize_production_or_payments(self) -> None:
        governance = assess_release_readiness(ROOT)["governance"]
        self.assertFalse(governance["code_ci_can_authorize_real_production"])
        self.assertFalse(governance["code_ci_can_authorize_real_payments"])
        self.assertTrue(governance["authorization_decision_requires_evidence_ref"])
        self.assertTrue(governance["authorization_decision_is_versioned"])

    def test_enabled_metadata_without_versioned_decision_is_detected_as_unauthorized(self) -> None:
        indexed = {
            "real_legal_production": {
                "id": "real_legal_production",
                "status": "NOT_AUTHORIZED",
                "source": "NOT_AUTHORIZED",
                "evidence_ref": None,
            }
        }
        with patch.object(release_metadata, "REAL_PRODUCTION_AUTHORIZED", True):
            state = _authorization_state(indexed, "real_legal_production", REAL_SPEC)

        self.assertTrue(state["metadata_authorized"])
        self.assertFalse(state["provenance_valid"])
        self.assertFalse(state["state_consistent"])
        self.assertTrue(state["unauthorized_promotion"])

    def test_valid_versioned_human_decision_does_not_look_like_ci_promotion(self) -> None:
        indexed = {
            "real_legal_production": {
                "id": "real_legal_production",
                "status": "AUTHORIZED_VERSIONED_HUMAN_DECISION",
                "source": "VERSIONED_HUMAN_RELEASE_DECISION",
                "evidence_ref": "audit://release/decision-001",
            }
        }
        with patch.object(release_metadata, "REAL_PRODUCTION_AUTHORIZED", True):
            state = _authorization_state(indexed, "real_legal_production", REAL_SPEC)

        self.assertTrue(state["metadata_authorized"])
        self.assertTrue(state["provenance_valid"])
        self.assertTrue(state["state_consistent"])
        self.assertFalse(state["unauthorized_promotion"])

    def test_authorized_decision_without_evidence_reference_fails_closed(self) -> None:
        indexed = {
            "real_legal_production": {
                "id": "real_legal_production",
                "status": "AUTHORIZED_VERSIONED_HUMAN_DECISION",
                "source": "VERSIONED_HUMAN_RELEASE_DECISION",
                "evidence_ref": None,
            }
        }
        with patch.object(release_metadata, "REAL_PRODUCTION_AUTHORIZED", True):
            state = _authorization_state(indexed, "real_legal_production", REAL_SPEC)

        self.assertFalse(state["provenance_valid"])
        self.assertTrue(state["unauthorized_promotion"])

    def test_decision_cannot_run_ahead_of_metadata_gate(self) -> None:
        indexed = {
            "real_legal_production": {
                "id": "real_legal_production",
                "status": "AUTHORIZED_VERSIONED_HUMAN_DECISION",
                "source": "VERSIONED_HUMAN_RELEASE_DECISION",
                "evidence_ref": "audit://release/decision-002",
            }
        }
        with patch.object(release_metadata, "REAL_PRODUCTION_AUTHORIZED", False):
            state = _authorization_state(indexed, "real_legal_production", REAL_SPEC)

        self.assertFalse(state["metadata_authorized"])
        self.assertFalse(state["provenance_valid"])
        self.assertFalse(state["state_consistent"])
        self.assertFalse(state["unauthorized_promotion"])


if __name__ == "__main__":
    unittest.main()
