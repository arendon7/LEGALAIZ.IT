import json
import unittest
from pathlib import Path

from legalai_platform.fact_extraction_m34_2 import FactExtractionService
from legalai_platform.m34_intelligent_journey import fact_is_decision_usable


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "config" / "m34" / "benchmarks" / "fact_extraction_guardrails_v1.json"


class M342GuardrailBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
        cls.service = FactExtractionService()

    def test_benchmark_has_coverage_for_all_11_products_and_adversarial_cases(self):
        scenarios = self.payload["scenarios"]
        signaled = {
            code
            for scenario in scenarios
            for code in scenario.get("expected_product_signals", [])
        }
        self.assertEqual(
            signaled,
            {
                "CO-LA-001", "CO-LA-002", "CO-EM-003", "CO-EM-004", "CO-AR-001",
                "CO-SA-001", "CO-CD-001", "CO-CD-003", "CO-CD-004", "CO-TR-001", "CO-TR-002",
            },
        )
        self.assertTrue(any(item["id"].startswith("ADVERSARIAL") for item in scenarios))
        self.assertTrue(any(item["id"].startswith("INSUFFICIENT") for item in scenarios))

    def test_guardrail_scenarios(self):
        failures = []
        for scenario in self.payload["scenarios"]:
            result = self.service.extract(
                scenario["narrative"],
                f"benchmark:{scenario['id']}:narrative",
            )
            actual_facts = {fact["fact_type"] for fact in result["facts"]}
            actual_products = {item["product_code"] for item in result["candidate_products"]}
            actual_risks = {item["code"] for item in result["risk_signals"]}

            for fact_type in scenario.get("expected_fact_types", []):
                if fact_type not in actual_facts:
                    failures.append(f"{scenario['id']}: falta hecho esperado {fact_type}")
            for product_code in scenario.get("expected_product_signals", []):
                if product_code not in actual_products:
                    failures.append(f"{scenario['id']}: falta señal de producto {product_code}")
            for risk_code in scenario.get("expected_risks", []):
                if risk_code not in actual_risks:
                    failures.append(f"{scenario['id']}: falta señal de riesgo {risk_code}")
            for fact_type in scenario.get("forbidden_fact_types", []):
                if fact_type in actual_facts:
                    failures.append(f"{scenario['id']}: inventó hecho prohibido {fact_type}")

            if "recommendation" in result or "recommended_product" in result:
                failures.append(f"{scenario['id']}: M34.2 emitió una recomendación")
            if any(fact_is_decision_usable(fact) for fact in result["facts"]):
                failures.append(f"{scenario['id']}: un candidato automático quedó utilizable como decisión")
            if any(fact.get("confirmation_status") != "UNCONFIRMED" for fact in result["facts"]):
                failures.append(f"{scenario['id']}: un candidato automático quedó confirmado")

        if failures:
            self.fail("\n".join(failures))


if __name__ == "__main__":
    unittest.main()
