from __future__ import annotations

from pathlib import Path

from co_ar_001_document_factory_v249 import CoAr001DocumentFactoryV249
from legalai_platform.document_quality import assert_docx_quality


class CoAr001DocumentFactoryV250(CoAr001DocumentFactoryV249):
    VERSION = "2.50"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-ar-001-v250"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_documents(self, answers, target_folder):
        evaluation, generated, hashes = super().render_documents(answers, target_folder)
        target_folder = Path(target_folder)
        for item in generated:
            report = assert_docx_quality(target_folder / item["filename"], expected_product="CO-AR-001")
            item["quality"] = {
                "valid": report["valid"],
                "warnings": report["warnings"],
                "metrics": report["metrics"],
            }
            hashes[item["filename"]] = report["sha256"]
        return evaluation, generated, hashes
