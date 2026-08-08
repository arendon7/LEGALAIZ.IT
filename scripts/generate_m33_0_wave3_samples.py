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
from tests.test_m33_0_wave3 import PRODUCTS, health_fixture, sast_fixture, traffic_fixture

SELECTIONS = {
    "CO-SA-001": (
        "health_diagnostic",
        "health_petition",
        "health_reiteration",
        "health_supersalud",
        "health_history_request",
        "health_evidence",
        "health_calendar",
    ),
    "CO-TR-001": ("sast_report", "sast_record_request"),
    "CO-TR-002": ("traffic_diagnostic", "traffic_record_request", "traffic_notification_claim"),
}


def _specs(code: str, answers: dict, result: dict) -> list[dict]:
    return document_specs_m33_all(
        "CASE-M33-W3-VISUAL",
        code,
        answers,
        result,
        PRODUCTS[code],
        "2026-08-08T12:25:00-05:00",
        [],
    )


def _find(specs: list[dict], requested: str) -> dict:
    by_kind = {str(spec.get("kind")): spec for spec in specs}
    if requested in by_kind:
        return by_kind[requested]
    tokens = {
        "health_diagnostic": ("diagnóstico", "salud"),
        "health_petition": ("petición", "reclamo"),
        "health_reiteration": ("reiteración",),
        "health_supersalud": ("supersalud",),
        "health_history_request": ("historia clínica",),
        "health_evidence": ("matriz", "radicación"),
        "health_calendar": ("calendario", "seguimiento"),
        "sast_report": ("informe", "sast"),
        "sast_record_request": ("expediente", "certificación"),
        "traffic_diagnostic": ("diagnóstico", "contravencional"),
        "traffic_record_request": ("expediente", "estado procesal"),
        "traffic_notification_claim": ("notificación", "restablecimiento"),
    }[requested]
    for spec in specs:
        title = str(spec.get("title") or "").casefold()
        if all(token.casefold() in title for token in tokens):
            return spec
    raise RuntimeError(f"No se encontró muestra {requested}; disponibles: {sorted(by_kind)}")


def _metadata(code: str, result: dict, spec: dict) -> list[tuple[str, str]]:
    if spec.get("internal_controls_externalized"):
        return []
    return [
        ("Producto", code),
        ("Estándar documental", "M33.0"),
        ("Nivel de riesgo", str(result.get("risk") or "por verificar")),
        ("Estado", "Candidato sujeto a revisión jurídica y QA"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera muestras representativas M33.0 de salud y tránsito.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    fixtures = {
        "CO-SA-001": health_fixture(),
        "CO-TR-001": sast_fixture(),
        "CO-TR-002": traffic_fixture(),
    }
    records = []
    for code, (answers, result) in fixtures.items():
        specs = _specs(code, answers, result)
        for requested in SELECTIONS[code]:
            spec = _find(specs, requested)
            target = output / f"{code}_{requested}_M33_0.docx"
            build_docx(
                target,
                spec["title"],
                spec.get("subtitle", ""),
                _metadata(code, result, spec),
                spec["sections"],
                product_code=code,
                enforce_legal_standard=True,
                append_default_control=not bool(spec.get("internal_controls_externalized")),
            )
            records.append({
                "product_code": code,
                "requested_kind": requested,
                "actual_kind": spec.get("kind"),
                "sample": target.name,
                "document_standard": "M33.0",
                "risk": result.get("risk"),
                "released": False,
                "legal_approval": "pending",
                "qa_approval": "pending",
                "internal_controls_externalized": bool(spec.get("internal_controls_externalized")),
            })

    manifest = output / "m33-wave3-samples.json"
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"samples": len(records), "manifest": str(manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
