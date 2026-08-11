from __future__ import annotations

"""Trazabilidad jurídica y de parámetros anuales M33.4 para CO-LA-001."""

from copy import deepcopy

from legalai_platform.labor_liquidation_legal_source_pack import (
    LABOR_KINDS,
    evaluate_labor_parameters_m334,
    labor_source_ids,
)
from legalai_platform.legal_source_registry import build_legal_source_manifest, source_control_lines


_CONTROL_MARKER = "m33_4_labor_source_control"
_PARAMETER_SENSITIVE_KINDS = {"calculation", "claim", "labor_diagnostic"}


def _parameter_lines(control: dict) -> list[str]:
    lines = [
        (
            "Parámetros laborales M33.4: "
            f"estado {control.get('status')} · compuerta {control.get('gate')} · "
            f"año {control.get('parameter_year')} · SMLMV ${int(control.get('smlmv') or 0):,} · "
            f"auxilio ${int(control.get('transport_aid') or 0):,}."
        ).replace(",", ".")
    ]
    lines.append(
        "Estado procesal del salario mínimo: Decreto 1469 de 2025 operativo tras la revocatoria de la suspensión provisional comunicada por el Consejo de Estado el 17/07/2026; proceso de nulidad pendiente."
    )
    for warning in control.get("warnings") or []:
        lines.append(f"Advertencia paramétrica: {warning}")
    for reason in control.get("reasons") or []:
        lines.append(f"Bloqueo paramétrico: {reason}")
    return lines


def finalize_labor_sources_m33_4(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Añade control interno después de la presentación, sin tocar ``sections``."""
    if str((result or {}).get("risk") or "").casefold() == "red":
        return specs

    parameter_control = evaluate_labor_parameters_m334(answers, result)
    finalized: list[dict] = []

    for original in specs:
        kind = str(original.get("kind") or "")
        if kind not in LABOR_KINDS:
            finalized.append(original)
            continue

        spec = deepcopy(original)
        source_ids = labor_source_ids(kind, answers, result)
        manifest = build_legal_source_manifest(source_ids)
        kind_parameter = (
            deepcopy(parameter_control)
            if kind in _PARAMETER_SENSITIVE_KINDS
            else {
                "standard": "M33.4",
                "status": "not_material_to_this_piece",
                "gate": "not_applicable",
                "legal_effect": "document_does_not_reuse_annual_labor_parameter",
                "parameter_year": parameter_control.get("parameter_year"),
                "reasons": [],
                "warnings": [],
            }
        )

        internal = [
            deepcopy(section)
            for section in (spec.get("internal_review_sections") or [])
            if not (isinstance(section, dict) and section.get("_m334_marker") == _CONTROL_MARKER)
        ]
        bullets = source_control_lines(source_ids)
        if kind in _PARAMETER_SENSITIVE_KINDS:
            bullets.extend(_parameter_lines(kind_parameter))
        internal.append({
            "heading": "CONTROL DE FUENTES JURÍDICAS Y PARÁMETROS M33.4 — CO-LA-001",
            "_type": "control",
            "_m334_marker": _CONTROL_MARKER,
            "source_ids": list(source_ids),
            "source_manifest_status": manifest["status"],
            "labor_parameter_status": kind_parameter["status"],
            "labor_parameter_gate": kind_parameter["gate"],
            "bullets": bullets,
            "text": (
                "Control interno. La vigencia de las reglas de liquidación y la exactitud de los parámetros anuales se "
                "validan por separado. El SMLMV y el auxilio de transporte 2026 no prueban por sí solos que cada concepto "
                "sea debido: deben cotejarse salario real, modalidad de trabajo, desplazamiento o conectividad, períodos, "
                "pagos previos, causa de terminación, estabilidad reforzada, fueros y demás hechos materiales. La situación "
                "procesal del Decreto 1469 de 2025 requiere seguimiento independiente mientras se decide su legalidad. "
                "Aprobación jurídica y QA permanecen pendientes sobre la misma revisión."
            ),
        })

        spec["internal_review_sections"] = internal
        spec["legal_source_manifest"] = manifest
        spec["legal_source_standard_m334"] = "M33.4"
        spec["source_manifest_status_m334"] = manifest["status"]
        spec["source_manifest_gate_m334"] = manifest["status"]
        spec["legal_source_ids_m334"] = list(source_ids)
        spec["labor_parameter_control_m334"] = kind_parameter
        spec["labor_parameter_status_m334"] = kind_parameter["status"]
        spec["labor_parameter_gate_m334"] = kind_parameter["gate"]
        if manifest["status"] != "current":
            release_gate = "release_block_reverification_required"
        elif (
            kind in _PARAMETER_SENSITIVE_KINDS
            and kind_parameter["gate"] == "release_block_labor_parameter_reverification_required"
        ):
            release_gate = kind_parameter["gate"]
        else:
            release_gate = "human_legal_and_qa_review_required"
        spec["release_gate_m334"] = release_gate
        spec["legal_source_scope_m334"] = {
            "document_kind": kind,
            "parameter_sensitive": kind in _PARAMETER_SENSITIVE_KINDS,
            "period_start": str(answers.get("start_date") or ""),
            "period_end": str(answers.get("end_date") or ""),
            "transport_aid_used": bool(float(answers.get("transport_aid") or 0)),
            "wage_status": (
                parameter_control.get("wage_current_status")
                if kind in _PARAMETER_SENSITIVE_KINDS
                else "not_material_to_this_piece"
            ),
        }
        finalized.append(spec)

    return finalized


__all__ = ["finalize_labor_sources_m33_4"]
