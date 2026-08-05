from __future__ import annotations

from pathlib import Path

from co_em_004_document_factory_v246 import CoEm004DocumentFactoryV246
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure


class CoEm004DocumentFactoryV247(CoEm004DocumentFactoryV246):
    VERSION = "2.47"

    def __init__(self, root: Path, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = Path(root) / "data" / "generated" / "co-em-004-v247"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_documents(self, answers, target_folder):
        evaluation, generated, hashes = super().render_documents(answers, target_folder)
        target_folder = Path(target_folder)
        for item in generated:
            path = target_folder / item["filename"]
            quality = assert_docx_quality(path, expected_product="CO-EM-004")
            visual = assert_visual_structure(path, expected_product="CO-EM-004")
            item["quality"] = {
                "valid": quality["valid"],
                "warnings": quality["warnings"],
                "metrics": quality["metrics"],
            }
            item["visual_preflight"] = {
                "valid": visual["valid"],
                "warnings": visual["warnings"],
                "metrics": visual["metrics"],
                "requires_human_visual_review": True,
            }
            hashes[item["filename"]] = quality["sha256"]
        return evaluation, generated, hashes
