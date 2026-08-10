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
from m33_2_analytical_reference_format import apply_m33_2_analytical_format
from m33_2_procedural_reference_format import apply_m33_2_procedural_format
from m33_wave3_runtime import document_specs_m33_all
from tests.test_m33_0_consumer_legal_finalize import MECHANISMS, consumer_route_fixture
from tests.test_m33_0_debt_legal_finalize import debt_stage_fixture
from tests.test_m33_0_procedural_wave import PRODUCTS, habeas_fixture, labor_fixture

SELECTIONS = {
    "CO-LA-001": ("calculation", "claim"),
    "CO-CD-001": (
        "habeas_consultation",
        "habeas_claim",
        "habeas_reiteration",
        "identity_theft_protocol",
        "habeas_authority_escalation",
        "habeas_evidence_matrix",
        "habeas_deadline_calendar",
    ),
}

CONSUMER_COMMON = (
    "consumer_mechanism_diagnosis",
    "consumer_evidence_matrix",
    "consumer_deadline_calendar",
)

DEBT_VISUAL_STAGES = (
    (
        "Enviar un cobro inicial",
        False,
        ("debt_diagnostic", "account_statement", "collection_evidence_matrix", "collection_letter"),
    ),
    (
        "Acordar un plan de pago",
        False,
        ("payment_agreement", "payment_schedule", "promissory_note", "instruction_letter"),
    ),
    (
        "Registrar o seguir pagos",
        False,
        ("payment_receipt",),
    ),
    (
        "Cerrar la obligación",
        True,
        ("settlement_certificate",),
    ),
)


def _specs(code: str, answers: dict, result: dict) -> list[dict]:
    return document_specs_m33_all(
        "CASE-M33-VISUAL",
        code,
        answers,
        result,
        PRODUCTS[code],
        "2026-08-08T08:00:00-05:00",
        [],
    )


def _visible_metadata(code: str, spec: dict) -> list[tuple[str, str]]:
    if spec.get("internal_controls_externalized"):
        return []
    return [
        ("Producto", code),
        ("Estándar documental", "M33.0"),
        ("Estado", "Candidato sujeto a revisión jurídica y QA"),
    ]


def _apply_presentation(target: Path, *, code: str, title: str) -> dict:
    procedural = apply_m33_2_procedural_format(target, product_code=code, title=title)
    if procedural.get("applied"):
        return procedural
    analytical = apply_m33_2_analytical_format(target, product_code=code, title=title)
    if analytical.get("applied"):
        return analytical
    return {"applied": False, "profile": "M33.2-base", "reason": "base_family"}


def _write_sample(output: Path, code: str, kind: str, spec: dict, records: list[dict]) -> None:
    target = output / f"{code}_{kind}_M33_0.docx"
    build_docx(
        target,
        spec["title"],
        spec.get("subtitle", ""),
        _visible_metadata(code, spec),
        spec["sections"],
        product_code=code,
        enforce_legal_standard=True,
        append_default_control=not bool(spec.get("internal_controls_externalized")),
    )
    presentation = _apply_presentation(target, code=code, title=spec["title"])
    records.append({
        "product_code": code,
        "kind": kind,
        "sample": target.name,
        "document_standard": spec.get("document_standard"),
        "presentation_standard": "M33.2" if presentation.get("applied") else "M33.2-base",
        "presentation_profile": presentation.get("profile"),
        "released": False,
        "legal_approval": "pending",
        "qa_approval": "pending",
        "internal_controls_externalized": bool(spec.get("internal_controls_externalized")),
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera muestras representativas de la segunda oleada M33.0.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    fixtures = {
        "CO-LA-001": labor_fixture(),
        "CO-CD-001": habeas_fixture(),
    }
    for code, (answers, result) in fixtures.items():
        by_kind = {spec["kind"]: spec for spec in _specs(code, answers, result)}
        for kind in SELECTIONS[code]:
            if kind not in by_kind:
                raise RuntimeError(f"{code}: no se generó la muestra requerida {kind}.")
            _write_sample(output, code, kind, by_kind[kind], records)

    # CO-CD-003 se valida como cinco expedientes alternativos. Los documentos
    # comunes se toman una sola vez del caso de garantía; cada comunicación
    # sustantiva se genera desde un expediente compatible con su propio mecanismo.
    common_written = False
    for mechanism_kind in MECHANISMS:
        answers, result = consumer_route_fixture(mechanism_kind)
        by_kind = {spec["kind"]: spec for spec in _specs("CO-CD-003", answers, result)}
        if mechanism_kind not in by_kind:
            raise RuntimeError(f"CO-CD-003: no se generó la ruta {mechanism_kind}.")
        if not common_written:
            for kind in CONSUMER_COMMON:
                if kind not in by_kind:
                    raise RuntimeError(f"CO-CD-003: falta documento común {kind}.")
                _write_sample(output, "CO-CD-003", kind, by_kind[kind], records)
            common_written = True
        _write_sample(output, "CO-CD-003", mechanism_kind, by_kind[mechanism_kind], records)

    # CO-CD-004 se revisa como un ciclo completo. Cada documento condicional se
    # genera desde la etapa que realmente lo habilita; los tres documentos comunes
    # se escriben una sola vez para no falsear la selección histórica del producto.
    written_debt: set[str] = set()
    for stage, zero_balance, kinds in DEBT_VISUAL_STAGES:
        answers, result = debt_stage_fixture(stage, zero_balance=zero_balance)
        by_kind = {spec["kind"]: spec for spec in _specs("CO-CD-004", answers, result)}
        for kind in kinds:
            if kind in written_debt:
                continue
            if kind not in by_kind:
                raise RuntimeError(f"CO-CD-004/{stage}: no se generó la muestra requerida {kind}.")
            _write_sample(output, "CO-CD-004", kind, by_kind[kind], records)
            written_debt.add(kind)
    if len(written_debt) != 10:
        raise RuntimeError(f"CO-CD-004: se esperaban 10 piezas visuales y se generaron {len(written_debt)}.")

    manifest = output / "m33-procedural-samples.json"
    manifest.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"samples": len(records), "manifest": str(manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
