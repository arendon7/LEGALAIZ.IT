from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import json
import tempfile

from legalai_platform.release_readiness_v1 import ReleaseReadinessV1


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "release" / "v1_readiness_contract.json"


class FakeInfra:
    def __init__(self, passed: bool = True):
        self.passed = passed

    def doctor(self, con):
        keys = [
            "master_key",
            "secure_cookies",
            "public_https",
            "mfa",
            "volume_encryption",
            "malware_scanner",
            "canonical_sources",
        ]
        return {
            "passed": len(keys) if self.passed else 0,
            "total": len(keys),
            "checks": [{"key": key, "passed": self.passed} for key in keys],
        }


class FakeSettings:
    def __init__(
        self,
        *,
        profile: str = "production",
        object_storage_backend: str = "s3-encrypted",
        require_origin_check: bool = True,
    ):
        self.profile = profile
        self.object_storage_backend = object_storage_backend
        self.require_origin_check = require_origin_check


def portfolio():
    products = {f"P-{index:02d}": {} for index in range(11)}
    questions = [{"id": f"q-{index}"} for index in range(473)]
    interviews = {"P-00": {"questions": questions}}
    for code in list(products)[1:]:
        interviews[code] = {"questions": []}
    return products, interviews


def all_attestations(contract: dict) -> dict[str, str]:
    return {str(env_name): "true" for env_name in contract["external_attestations"].values()}


def build_complete_root() -> tuple[tempfile.TemporaryDirectory, Path]:
    temp = tempfile.TemporaryDirectory(prefix="legalaiz-v1-r0-")
    root = Path(temp.name)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    target = root / "config" / "release" / "v1_readiness_contract.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(contract), encoding="utf-8")
    run_source = "\n".join(contract["required_runtime_markers"]) + "\nfrom legalai_platform.http_handler_m37_3 import Handler\n"
    (root / "run.py").write_text(run_source, encoding="utf-8")
    for rel in contract["required_repository_evidence"].values():
        path = root / str(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("certification evidence placeholder for unit test\n", encoding="utf-8")
    return temp, root


class V1R0ReleaseReadinessTests(TestCase):
    def test_current_release_flags_cannot_be_called_real_production(self):
        products, interviews = portfolio()
        center = ReleaseReadinessV1(
            ROOT,
            FakeSettings(profile="local", object_storage_backend="local-encrypted", require_origin_check=False),
            FakeInfra(True),
            products,
            interviews,
            env={},
            release_flags={
                "public_demo_mode": False,
                "real_production_authorized": False,
                "real_payments_authorized": False,
                "synthetic_data_only": True,
            },
        )
        with patch(
            "legalai_platform.release_readiness_v1.runtime_status",
            return_value=SimpleNamespace(backend="sqlite", driver_available=True),
        ):
            result = center.assess(object())
        self.assertFalse(result["readiness"]["platform_ready"])
        self.assertFalse(result["readiness"]["activation_authorized"])
        self.assertEqual(result["readiness"]["activation_state"], "BLOCKED")
        self.assertIn("production_profile", result["blocking"])
        self.assertIn("synthetic_data_boundary_removed", result["blocking"])
        self.assertIn("postgres_backend", result["blocking"])
        self.assertIn("durable_object_storage", result["blocking"])

    def test_external_flags_cannot_override_structural_repository_gaps(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        env = all_attestations(contract)
        products, interviews = portfolio()
        center = ReleaseReadinessV1(
            ROOT,
            FakeSettings(),
            FakeInfra(True),
            products,
            interviews,
            env=env,
            release_flags={
                "public_demo_mode": False,
                "real_production_authorized": True,
                "real_payments_authorized": True,
                "synthetic_data_only": False,
            },
        )
        with patch(
            "legalai_platform.release_readiness_v1.runtime_status",
            return_value=SimpleNamespace(backend="postgresql", driver_available=True),
        ):
            result = center.assess(object())
        self.assertFalse(result["evidence_summary"]["repository_evidence_complete"])
        self.assertIn("postgres_repository_evidence", result["blocking"])
        self.assertFalse(result["readiness"]["activation_authorized"])

    def test_complete_evidence_can_be_ready_without_self_authorizing(self):
        temp, root = build_complete_root()
        self.addCleanup(temp.cleanup)
        contract = json.loads((root / "config" / "release" / "v1_readiness_contract.json").read_text(encoding="utf-8"))
        env = all_attestations(contract)
        env["LEGAL_DATABASE_BACKEND"] = "postgresql"
        products, interviews = portfolio()
        center = ReleaseReadinessV1(
            root,
            FakeSettings(),
            FakeInfra(True),
            products,
            interviews,
            env=env,
            release_flags={
                "public_demo_mode": False,
                "real_production_authorized": False,
                "real_payments_authorized": False,
                "synthetic_data_only": False,
            },
        )
        with patch(
            "legalai_platform.release_readiness_v1.runtime_status",
            return_value=SimpleNamespace(backend="postgresql", driver_available=True),
        ):
            result = center.assess(object())
        self.assertTrue(result["readiness"]["platform_ready"])
        self.assertFalse(result["readiness"]["activation_authorized"])
        self.assertFalse(result["readiness"]["payments_ready"])
        self.assertFalse(result["readiness"]["commercial_ready"])
        self.assertEqual(result["blocking"], [])
        self.assertFalse(result["governance"]["self_authorization"])

    def test_explicit_release_authorization_is_separate_from_readiness(self):
        temp, root = build_complete_root()
        self.addCleanup(temp.cleanup)
        contract = json.loads((root / "config" / "release" / "v1_readiness_contract.json").read_text(encoding="utf-8"))
        env = all_attestations(contract)
        env["LEGAL_DATABASE_BACKEND"] = "postgresql"
        products, interviews = portfolio()
        center = ReleaseReadinessV1(
            root,
            FakeSettings(),
            FakeInfra(True),
            products,
            interviews,
            env=env,
            release_flags={
                "public_demo_mode": False,
                "real_production_authorized": True,
                "real_payments_authorized": True,
                "synthetic_data_only": False,
            },
        )
        with patch(
            "legalai_platform.release_readiness_v1.runtime_status",
            return_value=SimpleNamespace(backend="postgresql", driver_available=True),
        ):
            result = center.assess(object())
        self.assertTrue(result["readiness"]["platform_ready"])
        self.assertTrue(result["readiness"]["payments_ready"])
        self.assertTrue(result["readiness"]["commercial_ready"])
        self.assertTrue(result["readiness"]["activation_authorized"])
        self.assertEqual(result["readiness"]["activation_state"], "AUTHORIZED")

    def test_contract_and_response_are_fail_closed_and_secret_minimized(self):
        products, interviews = portfolio()
        center = ReleaseReadinessV1(
            ROOT,
            FakeSettings(profile="local", object_storage_backend="local-encrypted"),
            FakeInfra(False),
            products,
            interviews,
            env={"DATABASE_URL": "postgresql://secret-user:secret-password@db.example/legalaiz"},
            release_flags={
                "public_demo_mode": False,
                "real_production_authorized": False,
                "real_payments_authorized": False,
                "synthetic_data_only": True,
            },
        )
        with patch(
            "legalai_platform.release_readiness_v1.runtime_status",
            return_value=SimpleNamespace(backend="sqlite", driver_available=True),
        ):
            result = center.assess(object())
        raw = json.dumps(result, ensure_ascii=False).lower()
        self.assertNotIn("secret-user", raw)
        self.assertNotIn("secret-password", raw)
        self.assertNotIn("database_url", raw)
        self.assertNotIn("recovery_codes", raw)
        self.assertFalse(result["readiness"]["platform_ready"])
