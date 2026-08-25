#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = ROOT / "legalai_runtime_modules"
for candidate in (ROOT, RUNTIME_MODULES):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from co_ar_001_document_factory_v251 import CoAr001DocumentFactoryV251
from co_ar_001_test_fixtures_v249 import complete_answers as lease_answers
from co_em_003_document_factory_v245 import CoEm003DocumentFactoryV245
from co_em_004_document_factory_v248 import CoEm004DocumentFactoryV248
from co_la_002_document_factory_v240 import CoLa002DocumentFactoryV240
from scripts.generate_m32_3_full_portfolio import (
    ControlledEvaluator,
    _confidentiality_answers,
    _labor_contract_answers,
    _services_answers,
)

PRIMARY = {
    "CO-AR-001": "DOC-AR-CONTRACT-001",
    "CO-EM-003": "DOC-EM-CONTRACT-001",
    "CO-EM-004": "DOC-EM4-NDA-001",
    "CO-LA-002": "DOC-LA-CONTRACT-001",
}


class LeaseEvaluator:
    """Fixture mínimo compatible con la interfaz histórica de CO-AR-001."""

    def __init__(self):
        self.documents = [
            {"id": "DOC-AR-CONTRACT-001", "name": "Contrato de arrendamiento"},
        ]
        self.blocks = ["AR-BASE", "AR-PROPERTY", "AR-ECONOMICS"]

    def evaluate(self, answers):
        return {
            "blocked": False,
            "missing_fields": [],
            "documents": ["DOC-AR-CONTRACT-001"],
            "readiness": "ready_for_human_review",
            "status": "ready_for_human_review",
            "professional_review_required": True,
            "professional_reviews": ["Revisión jurídica sustantiva", "QA visual humano"],
            "review_requirements": ["Revisión jurídica sustantiva", "QA visual humano"],
            "findings": [],
            "blockers": [],
            "warnings": [],
            "blocks": self.blocks,
        }


def _copy_primary(factory, answers: dict, product_code: str, output: Path) -> dict:
    manifest = factory.generate(answers, actor={"id": "m33-visual-ci", "role": "qa"})
    document_id = PRIMARY[product_code]
    item = next((item for item in manifest.get("documents", []) if item.get("id") == document_id), None)
    if not item:
        raise RuntimeError(f"{product_code} no generó {document_id}.")
    candidates = sorted((factory.output_dir / manifest["generation_id"]).rglob(item["filename"]))
    if len(candidates) != 1:
        raise RuntimeError(f"{product_code}: salida primaria ambigua o ausente: {candidates}")
    destination = output / f"{product_code}_{Path(item['filename']).stem}_M33_0.docx"
    shutil.copy2(candidates[0], destination)
    return {
        "product_code": product_code,
        "factory": type(factory).__name__,
        "factory_version": str(getattr(factory, "VERSION", "")),
        "document_standard": item.get("document_standard"),
        "sample": destination.name,
        "generation_id": manifest["generation_id"],
        "legal_approval": (manifest.get("legal_approval") or {}).get("status", "pending") if isinstance(manifest.get("legal_approval"), dict) else manifest.get("legal_approval", "pending"),
        "qa_approval": (manifest.get("qa_approval") or {}).get("status", "pending") if isinstance(manifest.get("qa_approval"), dict) else manifest.get("qa_approval", "pending"),
        "released": bool(manifest.get("released", False)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera las cuatro muestras contractuales M33.0.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="legalaiz-m33-contracts-") as temporary:
        root = Path(temporary)
        samples = (
            (CoAr001DocumentFactoryV251(root / "lease", LeaseEvaluator()), lease_answers(), "CO-AR-001"),
            (CoEm003DocumentFactoryV245(root / "services", ControlledEvaluator(["DOC-EM-CONTRACT-001"], ["EM-BASE-001", "EM-SCOPE-001", "EM-FEES-001"])), _services_answers(), "CO-EM-003"),
            (CoEm004DocumentFactoryV248(root / "nda", ControlledEvaluator(["DOC-EM4-NDA-001"], ["NDA_BASE", "SECURITY", "IP"])), _confidentiality_answers(), "CO-EM-004"),
            (CoLa002DocumentFactoryV240(root / "employment", ControlledEvaluator(["DOC-LA-CONTRACT-001", "ANX-LA-FUN-001"], ["LABOR_BASE", "FUNCTIONS_ANNEX"])), _labor_contract_answers(), "CO-LA-002"),
        )
        for factory, answers, product_code in samples:
            records.append(_copy_primary(factory, answers, product_code, output))

    manifest = output / "m33-contractual-samples.json"
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"samples": len(records), "products": [item["product_code"] for item in records], "manifest": str(manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
