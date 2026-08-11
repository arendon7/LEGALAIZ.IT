from __future__ import annotations

"""Trazabilidad normativa interna M33.4 para CO-CD-003."""

from copy import deepcopy

from legalai_platform.consumer_legal_source_pack import (
    CONSUMER_KINDS,
    CONSUMER_MECHANISM_KINDS,
    consumer_source_ids,
)
from legalai_platform.legal_source_registry import build_legal_source_manifest, source_control_lines


_CONTROL_MARKER = "m33_4_consumer_source_control"


def _selected_kind(specs: list[dict]) -> str | None:
    selected = [str(spec.get("kind")) for spec in specs if spec.get("kind") in CONSUMER_MECHANISM_KINDS]
    return selected[0] if len(selected) == 1 else None


def finalize_consumer_sources_m33_4(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Adjunta fuentes estructuradas sin alterar las secciones públicas."""
    if (result or {}).get("risk") == "red":
        return specs

    selected_kind = _selected_kind(specs)
    if selected_kind is None:
        return specs

    finalized: list[dict] = []
    for original in specs:
        kind = str(original.get("kind") or "")
        if kind not in CONSUMER_KINDS:
            finalized.append(original)
            continue

        spec = deepcopy(original)
        source_ids = consumer_source_ids(kind, selected_kind)
        manifest = build_legal_source_manifest(source_ids)
        internal = [
            deepcopy(section)
            for section in (spec.get("internal_review_sections") or [])
            if not (isinstance(section, dict) and section.get("_m334_marker") == _CONTROL_MARKER)
        ]
        internal.append({
            "heading": "CONTROL DE FUENTES JURÍDICAS M33.4 — CO-CD-003",
            "_type": "control",
            "_m334_marker": _CONTROL_MARKER,
            "source_ids": list(source_ids),
            "source_manifest_status": manifest["status"],
            "bullets": source_control_lines(source_ids),
            "text": (
                "Control interno de trazabilidad por remedio. Debe confirmarse la relación de consumo, el mecanismo "
                "realmente activado, sus fechas ancla, el canal de contratación/pago y la inexistencia de un régimen "
                "sectorial especial prevalente. La Sentencia C-192 de 2026 se utiliza exclusivamente para el "
                "condicionamiento del plazo de reembolso por retracto. Decreto 587 de 2016 se aplica solo a las rutas "
                "de reversión/débito comprendidas por su ámbito. Aprobación jurídica y QA permanecen pendientes sobre "
                "la misma revisión."
            ),
        })

        spec["internal_review_sections"] = internal
        spec["legal_source_manifest"] = manifest
        spec["legal_source_standard_m334"] = "M33.4"
        spec["source_manifest_status_m334"] = manifest["status"]
        spec["source_manifest_gate_m334"] = manifest["status"]
        spec["legal_source_ids_m334"] = list(source_ids)
        spec["release_gate_m334"] = (
            "release_block_reverification_required"
            if manifest["status"] != "current"
            else "human_legal_and_qa_review_required"
        )
        spec["legal_source_scope_m334"] = {
            "selected_mechanism": selected_kind,
            "document_kind": kind,
            "sectoral_special_regime_check": "human_review_required",
        }
        finalized.append(spec)

    return finalized


__all__ = ["finalize_consumer_sources_m33_4"]
