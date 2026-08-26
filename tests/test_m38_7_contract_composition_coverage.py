from pathlib import Path
import unittest

from legalai_platform.contract_composition_coverage import (
    POLICIES,
    STANDARD,
    assess_contractual_coverage,
    composition_text,
)
from m33_contractual_adapters import compose_employment_m33, compose_lease_m33, compose_nda_m33
from m33_legal_composition import compose_services_m33


ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = ROOT / "m33_document_presentation.py"
RELEASE_GATE = ROOT / "legalai_platform" / "document_release_gate.py"
ADAPTERS = ROOT / "m33_contractual_adapters.py"
SERVICES = ROOT / "m33_legal_composition.py"


class M387ContractCompositionCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.presentation = PRESENTATION.read_text(encoding="utf-8")
        cls.release_gate = RELEASE_GATE.read_text(encoding="utf-8")
        cls.adapters = ADAPTERS.read_text(encoding="utf-8")
        cls.services = SERVICES.read_text(encoding="utf-8")

    def test_policy_targets_exact_four_contract_products(self):
        self.assertEqual(
            set(POLICIES),
            {"CO-EM-003", "CO-EM-004", "CO-AR-001", "CO-LA-002"},
        )
        for policy in POLICIES.values():
            self.assertGreaterEqual(policy["min_clauses"], 14)
            self.assertGreaterEqual(policy["min_text_chars"], 5500)
            self.assertGreaterEqual(len(policy["families"]), 8)

    def test_canonical_mature_composers_pass_structural_coverage(self):
        composers = {
            "CO-EM-003": compose_services_m33,
            "CO-EM-004": compose_nda_m33,
            "CO-AR-001": compose_lease_m33,
            "CO-LA-002": compose_employment_m33,
        }
        for code, composer in composers.items():
            with self.subTest(product=code):
                composition = composer({})
                sections = composition["sections"]
                report = assess_contractual_coverage(
                    product_code=code,
                    sections=sections,
                    rendered_text=composition_text(sections),
                )
                self.assertTrue(report["passed"], report)
                self.assertGreaterEqual(report["public_clause_count"], POLICIES[code]["min_clauses"])
                self.assertFalse(report["legal_sufficiency_claimed"])

    def test_non_contract_products_are_not_blocked(self):
        report = assess_contractual_coverage(
            product_code="CO-HC-001",
            sections=[],
            rendered_text="",
        )
        self.assertFalse(report["applicable"])
        self.assertTrue(report["passed"])
        self.assertFalse(report["legal_sufficiency_claimed"])

    def test_truncated_contract_fails_even_if_it_mentions_some_topics(self):
        sections = [
            {"heading": f"PRIMERA: CLÁUSULA {index}", "_type": "clause", "paragraphs": ["objeto alcance pago terminación"]}
            for index in range(1, 19)
        ]
        sections.append({"heading": "FIRMAS", "_type": "signature", "parties": [{"name": "A"}, {"name": "B"}]})
        report = assess_contractual_coverage(
            product_code="CO-EM-003",
            sections=sections,
            rendered_text=composition_text(sections) + " firmas",
        )
        self.assertFalse(report["passed"])
        self.assertTrue(any(item.startswith("rendered_text_chars:") for item in report["blockers"]))
        self.assertTrue(any(item.startswith("family_missing:") for item in report["blockers"]))

    def test_rendered_output_must_preserve_every_required_family(self):
        composition = compose_services_m33({})
        sections = composition["sections"]
        source_text = composition_text(sections)
        report = assess_contractual_coverage(
            product_code="CO-EM-003",
            sections=sections,
            rendered_text=source_text.replace("controversias", "tema omitido").replace("ley aplicable", "tema omitido").replace("domicilio", "tema omitido"),
        )
        self.assertFalse(report["passed"])
        self.assertIn("family_missing:disputes", report["blockers"])

    def test_signature_must_exist_in_composition_and_render(self):
        composition = compose_nda_m33({})
        sections = [section for section in composition["sections"] if section.get("_type") != "signature"]
        text = composition_text(sections)
        report = assess_contractual_coverage(
            product_code="CO-EM-004",
            sections=sections,
            rendered_text=text,
        )
        self.assertFalse(report["passed"])
        self.assertIn("signature_missing:composition", report["blockers"])
        self.assertIn("signature_missing:rendered", report["blockers"])

    def test_services_composer_is_wired_to_mature_library(self):
        self.assertIn("services_contract_sections", self.services)
        self.assertIn("service_scope_sections", self.services)
        self.assertIn("services_contract_sections(maturity_answers)", self.services)
        self.assertIn("service_scope_sections(maturity_answers)", self.services)

    def test_other_three_contracts_are_wired_to_mature_library(self):
        for token in (
            "employment_contract_sections",
            "lease_contract_sections",
            "nda_sections",
            "employment_contract_sections(maturity)",
            "lease_contract_sections(maturity)",
            "nda_sections(maturity",
        ):
            self.assertIn(token, self.adapters)

    def test_coverage_runs_only_on_final_approval_candidate_presentation(self):
        self.assertIn("assert_contractual_docx_coverage", self.presentation)
        self.assertIn("if mode == APPROVAL_CANDIDATE_MODE:", self.presentation)
        coverage_call = self.presentation.index("contractual_coverage = assert_contractual_docx_coverage")
        technical_call = self.presentation.index("technical = audit_m33_presentation")
        self.assertGreater(coverage_call, technical_call)

    def test_global_release_gate_does_not_block_legacy_intermediate_contract(self):
        self.assertNotIn("contract_composition_coverage", self.release_gate)
        self.assertNotIn("assert_contractual_docx_coverage", self.release_gate)

    def test_contractual_coverage_is_attached_to_review_evidence(self):
        self.assertIn('evidence["contractual_coverage"] = contractual_coverage', self.presentation)
        self.assertIn('contractual_coverage.get("applicable")', self.presentation)

    def test_failure_deletes_candidate_and_fails_closed(self):
        self.assertIn("ContractCompositionCoverageError", self.presentation)
        self.assertIn("DOCX bloqueado por cobertura contractual M38.7", self.presentation)
        self.assertIn("target.unlink()", self.presentation)

    def test_standard_does_not_claim_automatic_legal_sufficiency(self):
        self.assertEqual(STANDARD, "M38.7-CONTRACT-COMPOSITION-COVERAGE")
        module = (ROOT / "legalai_platform" / "contract_composition_coverage.py").read_text(encoding="utf-8").casefold()
        self.assertIn("no acredita suficiencia jurídica", module)
        self.assertIn("revisión jurídica y qa", module)
        self.assertNotIn("legal_sufficiency_claimed\": true", module)


if __name__ == "__main__":
    unittest.main()
