from __future__ import annotations

import unittest
from copy import deepcopy

from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_wave3 import PRODUCTS, traffic_fixture


def _specs(answers=None, result=None):
    if answers is None or result is None:
        answers, result = traffic_fixture()
    return document_specs_m33_all(
        "CASE-TRAFFIC-RELEASE", "CO-TR-002", answers, result,
        PRODUCTS["CO-TR-002"], "2026-08-09T12:00:00-05:00", [],
    )


def _has_signature(spec: dict) -> bool:
    return any(
        isinstance(section, dict)
        and str(section.get("_type") or section.get("type") or "").casefold() == "signature"
        for section in spec.get("sections") or []
    )


def _body(spec: dict) -> str:
    return " ".join(str(section) for section in spec.get("sections") or [])


class TrafficReleasePolishM330Tests(unittest.TestCase):
    def test_demo_revocation_not_radicable_has_no_signature(self):
        revocation = next(x for x in _specs() if x.get("kind") == "traffic_revocation_request")
        self.assertIn("NO RADICABLE TODAVÍA", _body(revocation))
        self.assertFalse(_has_signature(revocation))

    def test_demo_registry_without_source_act_is_not_radicable_and_has_no_signature(self):
        registry = next(x for x in _specs() if x.get("kind") == "traffic_registry_correction")
        text = _body(registry)
        self.assertIn("NO RADICABLE TODAVÍA", text)
        self.assertIn("acto fuente", text.casefold())
        self.assertFalse(_has_signature(registry))

    def test_verified_revocation_act_preserves_signature(self):
        answers, result = traffic_fixture()
        answers = deepcopy(answers)
        answers["sanction_resolution"] = "Resolución 12345 de 2025"
        answers["sanction_date"] = "2025-02-14"
        revocation = next(x for x in _specs(answers, result) if x.get("kind") == "traffic_revocation_request")
        self.assertNotIn("NO RADICABLE TODAVÍA — falta individualizar", _body(revocation))
        self.assertTrue(_has_signature(revocation))

    def test_verified_registry_source_preserves_signature(self):
        answers, result = traffic_fixture()
        answers = deepcopy(answers)
        answers["registry_source_act"] = "Resolución 54321 de 2026"
        registry = next(x for x in _specs(answers, result) if x.get("kind") == "traffic_registry_correction")
        self.assertNotIn("NO RADICABLE TODAVÍA", _body(registry))
        self.assertTrue(_has_signature(registry))


if __name__ == "__main__":
    unittest.main()
