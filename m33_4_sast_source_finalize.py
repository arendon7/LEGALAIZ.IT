from __future__ import annotations

"""Finalización interna M33.4 para CO-TR-001 — SAST."""

from copy import deepcopy

from legalai_platform.sast_legal_source_pack import SAST_KINDS, sast_source_ids, sast_temporal_control
from legalai_platform.legal_source_registry import build_legal_source_manifest, source_control_lines


_CONTROL_MARKER = "m33_4_sast_source_control"


def finalize_sast_sources_m33_4(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    risk = str((result or {}).get("risk") or "").casefold()
    temporal = sast_temporal_control(answers)
    finalized: list[dict] = []

    for original in specs:
        kind = str(original.get("kind") or "")
        if kind not in SAST_KINDS:
            finalized.append(original)
            continue
        spec = deepcopy(original)
        before = deepcopy(spec.get("sections") or [])
        source_ids = sast_source_ids(kind, answers, result)
        manifest = build_legal_source_manifest(source_ids)
        internal = [
            deepcopy(section) for section in (spec.get("internal_review_sections") or [])
            if not (isinstance(section, dict) and section.get("_m334_marker") == _CONTROL_MARKER)
        ]
        bullets = source_control_lines(source_ids)
        bullets.extend([
            f"Temporalidad SAST M33.4: fecha de referencia {temporal.get('reference_date') or 'por verificar'}.",
            f"Concepto de Desempeño: {temporal.get('performance_concept')}; no se trata como requisito actual fuera de su ventana histórica.",
            f"Señalización: {temporal.get('signage_regime')}; no se proyecta retrospectivamente el Manual 2024 sin revisar transición.",
        ])
        internal.append({
            "heading": "CONTROL DE FUENTES JURÍDICAS M33.4 — CO-TR-001",
            "_type": "control",
            "_m334_marker": _CONTROL_MARKER,
            "source_ids": list(source_ids),
            "source_manifest_status": manifest["status"],
            "temporal_control": deepcopy(temporal),
            "bullets": bullets,
            "text": (
                "Control interno. Autorización, puesta en operación, señalización, metrología, inspección institucional y caso individual son capas distintas. "
                "Una consulta pública sin resultado no prueba inexistencia de autorización; una investigación o requerimiento no equivale a decisión firme; "
                "una excepción legal exige individualización fáctica; y la validez de un comparendo no se decide automáticamente por este chequeo del sistema. "
                "Aprobación jurídica y QA permanecen pendientes sobre la misma revisión."
            ),
        })
        spec["internal_review_sections"] = internal
        spec["legal_source_manifest"] = manifest
        spec["legal_source_standard_m334"] = "M33.4"
        spec["legal_source_ids_m334"] = list(source_ids)
        spec["source_manifest_status_m334"] = manifest["status"]
        spec["source_manifest_gate_m334"] = manifest["status"]
        spec["sast_temporal_control_m334"] = deepcopy(temporal)
        spec["release_gate_m334"] = (
            "release_block_reverification_required" if manifest["status"] != "current"
            else "release_block_critical_human_review_required" if risk == "red"
            else "human_legal_and_qa_review_required"
        )
        spec["legal_source_scope_m334"] = {
            "document_kind": kind,
            "risk": risk or "unclassified",
            "reference_date": temporal.get("reference_date"),
            "performance_concept": temporal.get("performance_concept"),
            "signage_regime": temporal.get("signage_regime"),
            "public_sections_unchanged": before == (spec.get("sections") or []),
        }
        finalized.append(spec)
    return finalized


__all__ = ["finalize_sast_sources_m33_4"]
