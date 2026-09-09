import json
from pathlib import Path
import unittest

from legalai_platform.fulfillment_bridge_m35_1 import FulfillmentFactBridge, transform_value
from legalai_platform.m24_client_intake import M24ClientIntakeCenter


ROOT = Path(__file__).resolve().parents[1]


def fact(fact_type, value, *, provenance="USER_ASSERTED", confirmation="UNCONFIRMED", fact_id="fact_test"):
    return {
        "fact_id": fact_id,
        "fact_type": fact_type,
        "value": value,
        "normalized_value": value,
        "provenance": provenance,
        "confirmation_status": confirmation,
        "criticality": "HIGH",
        "source_reference": "question:m35-test",
        "evidence_ids": [],
        "extraction_confidence": None,
        "legal_relevance": "HIGH",
        "created_at": None,
        "updated_at": None,
        "notes": "",
    }


class M351MappingRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = FulfillmentFactBridge()
        cls.validation = cls.bridge.validate()

    def test_registry_covers_every_triage_product_fact_combination(self):
        self.assertTrue(self.validation.ok, "\n".join(self.validation.errors))
        self.assertEqual(self.validation.combinations, 49)
        self.assertEqual(len(self.bridge.mappings), 49)
        self.assertGreater(self.validation.no_safe_map, self.validation.reusable)

    def test_fulfillment_only_facts_are_never_mapped(self):
        self.assertFalse(set(self.bridge.mappings) & self.bridge.deferred_combinations())

    def test_every_reusable_target_exists_in_the_real_interview(self):
        for (code, fact_type), mapping in self.bridge.mappings.items():
            if mapping["status"] == "NO_SAFE_MAP":
                continue
            target = mapping["target_question_id"]
            question = self.bridge._question(code, target)
            self.assertIsNotNone(question, f"{code}/{fact_type} -> {target}")

    def test_money_date_and_text_transformations_fail_closed(self):
        self.assertEqual(transform_value("MONEY_COP_TO_NUMBER", {"amount_cop": 1800000, "currency": "COP"}), 1800000)
        self.assertIsNone(transform_value("MONEY_COP_TO_NUMBER", {"amount_cop": -1, "currency": "COP"}))
        self.assertEqual(transform_value("DATE_ISO", "2026-08-01"), "2026-08-01")
        self.assertIsNone(transform_value("DATE_ISO", "2026-02-31"))
        self.assertIsNone(transform_value("TEXT_MIN_20", "muy corto"))
        self.assertEqual(transform_value("TEXT_MIN_3", "  Analista   jurídico "), "Analista jurídico")

    def test_partial_enum_transformations_never_guess_unmapped_values(self):
        self.assertEqual(transform_value("CONSUMER_ISSUE_TO_REQUEST_MODE", "GARANTIA"), "Garantía legal")
        self.assertIsNone(transform_value("CONSUMER_ISSUE_TO_REQUEST_MODE", "INCUMPLIMIENTO"))
        self.assertEqual(transform_value("NDA_RELATIONSHIP_TO_RUNTIME", "empleo"), "Laboral/colaborador")
        self.assertIsNone(transform_value("NDA_RELATIONSHIP_TO_RUNTIME", "negociacion"))
        self.assertEqual(transform_value("PRIOR_CLAIM_TO_YES_NO", "PRIOR_CLAIM_ASSERTED"), "Sí")
        self.assertIsNone(transform_value("PRIOR_CLAIM_TO_YES_NO", "UNCERTAIN"))

    def test_unconfirmed_ai_fact_never_prefills(self):
        result = self.bridge.build_prefill(
            "CO-AR-001",
            [fact("lease.rent", {"amount_cop": 1800000, "currency": "COP"}, provenance="AI_INFERRED")],
        )
        self.assertEqual(result["answers"], {})
        self.assertEqual(result["reused"], [])

    def test_labor_prefill_reuses_only_semantically_safe_fields(self):
        result = self.bridge.build_prefill(
            "CO-LA-001",
            [
                fact("employment.start_date", "2024-01-15", fact_id="fact_start"),
                fact("employment.end_date", "2026-08-01", fact_id="fact_end"),
                fact("employment.compensation_basis", {"amount_cop": 3200000, "currency": "COP"}, fact_id="fact_salary"),
                fact("employment.pending_concepts", ["salario", "cesantias"], fact_id="fact_pending"),
            ],
        )
        self.assertEqual(result["answers"]["start_date"], "2024-01-15")
        self.assertEqual(result["answers"]["end_date"], "2026-08-01")
        self.assertEqual(result["answers"]["monthly_salary"], 3200000)
        self.assertNotIn("salary_due_days", result["answers"])
        self.assertTrue(any(row["fact_type"] == "employment.pending_concepts" for row in result["skipped"]))

    def test_services_object_requires_runtime_minimum_detail(self):
        short = self.bridge.build_prefill("CO-EM-003", [fact("services.object", "Asesoría", fact_id="fact_short")])
        self.assertNotIn("object", short["answers"])
        detailed = self.bridge.build_prefill(
            "CO-EM-003",
            [fact("services.object", "Diseñar e implementar un prototipo jurídico para gestión documental", fact_id="fact_long")],
        )
        self.assertIn("object", detailed["answers"])

    def test_nda_categories_are_expanded_without_inventing_categories(self):
        result = self.bridge.build_prefill(
            "CO-EM-004",
            [fact("confidentiality.information_categories", ["comercial", "software_codigo"], fact_id="fact_nda")],
        )
        self.assertEqual(
            result["answers"]["info_categories"],
            "Información comercial o estratégica; Software o código fuente",
        )

    def test_consumer_prefill_uses_date_and_only_verified_mechanisms(self):
        result = self.bridge.build_prefill(
            "CO-CD-003",
            [
                fact("consumer.issue_type", "GARANTIA", fact_id="fact_issue"),
                fact("consumer.transaction_date", "2026-07-15", fact_id="fact_date"),
                fact("consumer.requested_remedy", "devolucion", fact_id="fact_remedy"),
            ],
        )
        self.assertEqual(result["answers"]["request_mode"], "Garantía legal")
        self.assertEqual(result["answers"]["purchase_date"], "2026-07-15")
        self.assertEqual(set(result["answers"]), {"request_mode", "purchase_date"})


class M351CanonicalOfferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        products = json.loads((ROOT / "data" / "products.json").read_text(encoding="utf-8"))
        cls.products = {row["code"]: row for row in products}
        cls.center = M24ClientIntakeCenter(ROOT, products)

    def test_m351_offer_source_uses_existing_canonical_product_prices(self):
        for code, product in self.products.items():
            offer = self.center.offer(code)
            levels = {row["id"]: row for row in offer.get("service_levels", [])}
            if "documento_personalizado" in levels:
                self.assertEqual(levels["documento_personalizado"]["price"], int(product.get("price_auto") or 0), code)
            if "solucion_revisada" in levels:
                self.assertEqual(
                    levels["solucion_revisada"]["price"],
                    int(product.get("price_auto") or 0) + int(product.get("price_review") or 0),
                    code,
                )
            self.assertEqual(offer["pricing_status"], "sandbox_reference_not_commercially_approved")
            self.assertIn("No constituyen una oferta comercial pública definitiva", offer["pricing_notice"])


if __name__ == "__main__":
    unittest.main()
