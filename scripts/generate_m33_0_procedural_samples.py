#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docx_builder import build_docx
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_procedural_wave import (
    PRODUCTS,
    consumer_fixture,
    debt_fixture,
    habeas_fixture,
    labor_fixture,
)

SELECTIONS = {
    "CO-LA-001": ("calculation", "claim"),
    "CO-CD-001": ("habeas_reiteration",),
    "CO-CD-003": ("warranty_claim",),
    "CO-CD-004": ("payment_agreement", "promissory_note"),
}


def _specs(code: str, answers: dict, result: dict) -> list[dict]:
    # El QA visual debe recorrer el mismo agregador activado por la aplicación.
    # Esto evita validar una composición histórica mientras el runtime sirve otra.
    return document_specs_m33_all(
        "CASE-M33-VISUAL",
        code,
        answers,
        result,
        PRODUCTS[code],
        "2026-08-08T08:00:00-05:00",
        [],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera muestras representativas de la segunda oleada M33.0.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    fixtures = {
        "CO-LA-001": labor_fixture(),
        "CO-CD-001": habeas_fixture(),
        "CO-CD-003": consumer_fixture("warranty_claim"),
        "CO-CD-004": debt_fixture(),
    }
    records = []
    for code, (answers, result) in fixtures.items():
        specs = _specs(code, answers, result)
        by_kind = {spec["kind"]: spec for spec in specs}
        for kind in SELECTIONS[code]:
            if kind not in by_kind:
                raise RuntimeError(f"{code}: no se generó la muestra requerida {kind}.")
            spec = by_kind[kind]
            target = output / f"{code}_{kind}_M33_0.docx"
            build_docx(
                target,
                spec["title"],
                spec.get("subtitle", ""),
                [("Producto", code), ("Estándar documental", "M33.0"), ("Estado", "Candidato sujeto a revisión jurídica y QA")],
                spec["sections"],
                product_code=code,
                enforce_legal_standard=True,
                append_default_control=not bool(spec.get("internal_controls_externalized")),
            )
            records.append({
                "product_code": code,
                "kind": kind,
                "sample": target.name,
                "document_standard": spec.get("document_standard"),
                "released": False,
                "legal_approval": "pending",
                "qa_approval": "pending",
                "internal_controls_externalized": bool(spec.get("internal_controls_externalized")),
            })

    manifest = output / "m33-procedural-samples.json"
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"samples": len(records), "manifest": str(manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
