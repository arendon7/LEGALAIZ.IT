from __future__ import annotations

"""Contrato transversal de portafolio para M33.4.

Esta prueba no sustituye los tests sectoriales. Su función es detectar regresiones
de cableado: exige que los once productos jurídicos del portafolio activo alcancen
una ruta viva con manifiesto M33.4 actual, fuentes resolubles, control interno,
metadata fuera del instrumento público y una compuerta humana o de bloqueo.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
for candidate in (ROOT, RUNTIME_MODULES):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from co_ar_001_test_fixtures_v249 import complete_answers as lease_answers
from legalai_platform.consumer_legal_source_pack import CONSUMER_KINDS
from legalai_platform.debt_legal_source_pack import DEBT_KINDS
from legalai_platform.habeas_data_legal_source_pack import HABEAS_KINDS
from legalai_platform.health_legal_source_pack import HEALTH_KINDS
from legalai_platform.labor_liquidation_legal_source_pack import LABOR_KINDS
from legalai_platform.legal_source_registry import get_legal_source, validate_registry
from legalai_platform.sast_legal_source_pack import SAST_KINDS
from legalai_platform.traffic_legal_source_pack import TRAFFIC_KINDS
from m33_4_nda_instrument_finalize import compose_nda_m33_instrument
from m33_document_presentation import split_internal_review_sections
from m33_employment_instrument_finalize import compose_employment_m33_instrument
from m33_lease_instrument_finalize import compose_lease_m33_instrument
from m33_services_release_polish import compose_services_m33_release
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_consumer_legal_finalize import consumer_route_fixture
from tests.test_m33_0_contractual_wave import employment_answers
from tests.test_m33_0_debt_legal_finalize import debt_stage_fixture
from tests.test_m33_0_procedural_wave import PRODUCTS as PROCEDURAL_PRODUCTS, habeas_fixture, labor_fixture
from tests.test_m33_0_services_reference import services_answers
from tests.test_m33_0_wave3 import PRODUCTS as WAVE3_PRODUCTS, health_fixture, sast_fixture, traffic_fixture
from test_m33_0_nda_legal_review import nda_answers


EXPECTED_PRODUCTS = {
    "CO-AR-001",
    "CO-EM-003",
    "CO-EM-004",
    "CO-LA-002",
    "CO-LA-001",
    "CO-CD-001",
    "CO-CD-003",
    "CO-CD-004",
    "CO-SA-001",
    "CO-TR-001",
    "CO-TR-002",
}


def _contract_compositions() -> dict[str, dict]:
    return {
        "CO-AR-001": compose_lease_m33_instrument(lease_answers()),
        "CO-EM-003": compose_services_m33_release(services_answers()),
        "CO-EM-004": compose_nda_m33_instrument(nda_answers()),
        "CO-LA-002": compose_employment_m33_instrument(employment_answers()),
    }


def _runtime_specs() -> dict[str, tuple[list[dict], set[str]]]:
    labor_answers, labor_result = labor_fixture()
    labor_result["risk"] = "yellow"

    habeas_answers, habeas_result = habeas_fixture()
    habeas_result["risk"] = "yellow"

    consumer_answers, consumer_result = consumer_route_fixture("warranty_claim")
    consumer_result["risk"] = "yellow"

    debt_answers, debt_result = debt_stage_fixture("Acordar un plan de pago")
    debt_result["risk"] = "yellow"

    health_answers, health_result = health_fixture()
    sast_answers, sast_result = sast_fixture()
    traffic_answers, traffic_result = traffic_fixture()

    cases = {
        "CO-LA-001": (labor_answers, labor_result, PROCEDURAL_PRODUCTS["CO-LA-001"], set(LABOR_KINDS)),
        "CO-CD-001": (habeas_answers, habeas_result, PROCEDURAL_PRODUCTS["CO-CD-001"], set(HABEAS_KINDS)),
        "CO-CD-003": (consumer_answers, consumer_result, PROCEDURAL_PRODUCTS["CO-CD-003"], set(CONSUMER_KINDS)),
        "CO-CD-004": (debt_answers, debt_result, PROCEDURAL_PRODUCTS["CO-CD-004"], set(DEBT_KINDS)),
        "CO-SA-001": (health_answers, health_result, WAVE3_PRODUCTS["CO-SA-001"], set(HEALTH_KINDS)),
        "CO-TR-001": (sast_answers, sast_result, WAVE3_PRODUCTS["CO-TR-001"], set(SAST_KINDS)),
        "CO-TR-002": (traffic_answers, traffic_result, WAVE3_PRODUCTS["CO-TR-002"], set(TRAFFIC_KINDS)),
    }

    generated: dict[str, tuple[list[dict], set[str]]] = {}
    for code, (answers, result, product, kinds) in cases.items():
        specs = document_specs_m33_all(
            f"CASE-M334-PORTFOLIO-{code}",
            code,
            answers,
            result,
            product,
            "2026-08-11T00:15:00-05:00",
            [],
        )
        generated[code] = (specs, kinds)
    return generated


class PortfolioSourceCoverageM334Tests(unittest.TestCase):
    def assert_manifest_sources_are_internal(self, *, code: str, public: list | dict, internal: list | dict, manifest: dict) -> None:
        self.assertEqual("M33.4", manifest.get("standard"), code)
        self.assertEqual("current", manifest.get("status"), code)
        self.assertEqual([], manifest.get("stale_source_ids"), code)
        source_ids = list(manifest.get("source_ids") or [])
        self.assertTrue(source_ids, code)

        public_text = json.dumps(public, ensure_ascii=False)
        internal_text = json.dumps(internal, ensure_ascii=False)
        for source_id in source_ids:
            source = get_legal_source(source_id)
            self.assertEqual(source_id, source["id"], code)
            self.assertNotIn(source_id, public_text, f"{code}: fuga de ID {source_id}")
            self.assertNotIn(source["official_url"], public_text, f"{code}: fuga de URL {source_id}")
            self.assertIn(source_id, internal_text, f"{code}: fuente no trazada internamente {source_id}")

    def test_exactly_eleven_active_products_have_live_m334_source_coverage(self):
        validate_registry()
        contracts = _contract_compositions()
        runtime = _runtime_specs()
        self.assertEqual(EXPECTED_PRODUCTS, set(contracts) | set(runtime))
        self.assertEqual(11, len(contracts) + len(runtime))

        covered: set[str] = set()

        for code, composition in contracts.items():
            with self.subTest(product=code, family="contractual"):
                manifest = composition.get("legal_source_manifest") or {}
                public, internal = split_internal_review_sections(composition.get("sections") or [])
                self.assertTrue(public, code)
                self.assertTrue(internal, code)
                self.assert_manifest_sources_are_internal(
                    code=code,
                    public=public,
                    internal=internal,
                    manifest=manifest,
                )
                maturity = composition.get("maturity_answers") or {}
                self.assertEqual("M33.4", maturity.get("legal_source_standard"), code)
                self.assertEqual("current", maturity.get("legal_source_gate_m334"), code)
                self.assertIn("human_legal_review_required", manifest.get("legal_effect") or "", code)
                covered.add(code)

        for code, (specs, kinds) in runtime.items():
            with self.subTest(product=code, family="procedural"):
                selected = [spec for spec in specs if str(spec.get("kind") or "") in kinds]
                self.assertTrue(selected, code)
                self.assertEqual(
                    len(selected),
                    len({str(spec.get("kind") or "") for spec in selected}),
                    f"{code}: la ruta viva no debe repetir kind canónico",
                )
                for spec in selected:
                    kind = str(spec.get("kind") or "")
                    manifest = spec.get("legal_source_manifest") or {}
                    internal = spec.get("internal_review_sections") or []
                    public = spec.get("sections") or []
                    self.assertEqual("M33.4", spec.get("legal_source_standard_m334"), f"{code}/{kind}")
                    self.assertEqual("current", spec.get("source_manifest_status_m334"), f"{code}/{kind}")
                    self.assertTrue(internal, f"{code}/{kind}")
                    self.assert_manifest_sources_are_internal(
                        code=f"{code}/{kind}",
                        public=public,
                        internal=internal,
                        manifest=manifest,
                    )
                    gate = str(spec.get("release_gate_m334") or "")
                    self.assertTrue(
                        gate.startswith("human_") or gate.startswith("release_block_"),
                        f"{code}/{kind}: compuerta M33.4 inválida {gate!r}",
                    )
                    self.assertNotEqual("released", gate.casefold(), f"{code}/{kind}")
                covered.add(code)

        self.assertEqual(EXPECTED_PRODUCTS, covered)

    def test_portfolio_never_marks_m334_traceability_as_legal_approval(self):
        for code, composition in _contract_compositions().items():
            with self.subTest(product=code):
                manifest = composition.get("legal_source_manifest") or {}
                self.assertEqual("traceability_only; human_legal_review_required", manifest.get("legal_effect"))

        for code, (specs, kinds) in _runtime_specs().items():
            with self.subTest(product=code):
                for spec in specs:
                    if str(spec.get("kind") or "") not in kinds:
                        continue
                    manifest = spec.get("legal_source_manifest") or {}
                    self.assertIn("human_legal_review_required", manifest.get("legal_effect") or "", f"{code}/{spec.get('kind')}")


if __name__ == "__main__":
    unittest.main()
