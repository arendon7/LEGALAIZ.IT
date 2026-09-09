import unittest

from legalai_platform.fulfillment_bridge_m35_1 import FulfillmentFactBridge, transform_value


class M351PersonalDataMappingTests(unittest.TestCase):
    def test_unknown_personal_data_never_forces_runtime_yes_or_no(self):
        self.assertIsNone(transform_value("PERSONAL_DATA_TO_YES_NO_UNKNOWN", "no_se"))

    def test_unknown_personal_data_fact_is_skipped_for_nda_prefill(self):
        bridge = FulfillmentFactBridge()
        fact = {
            "fact_id": "fact_personal_data_unknown",
            "fact_type": "data.personal_data_involved",
            "value": "no_se",
            "normalized_value": "no_se",
            "provenance": "USER_ASSERTED",
            "confirmation_status": "UNCONFIRMED",
            "criticality": "HIGH",
            "source_reference": "question:m34_data_personal_data_involved",
            "evidence_ids": [],
            "extraction_confidence": None,
            "legal_relevance": "HIGH",
            "created_at": None,
            "updated_at": None,
            "notes": "",
        }
        result = bridge.build_prefill("CO-EM-004", [fact])
        self.assertNotIn("personal_data", result["answers"])
        self.assertTrue(
            any(
                row["fact_type"] == "data.personal_data_involved"
                and row["reason"] == "TRANSFORM_NOT_SAFE"
                for row in result["skipped"]
            )
        )


if __name__ == "__main__":
    unittest.main()
