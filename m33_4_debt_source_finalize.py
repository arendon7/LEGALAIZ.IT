from __future__ import annotations

"""Trazabilidad normativa y paramétrica interna M33.4 para CO-CD-004."""

from copy import deepcopy

from legalai_platform.debt_legal_source_pack import (
    DEBT_INTEREST_PARAMETER_KINDS,
    DEBT_KINDS,
    debt_source_ids,
    evaluate_interest_parameter_m334,
)
from legalai_platform.legal_source_registry import build_legal_source_manifest, source_control_lines


_CONTROL_MARKER = "m33_4_debt_source_control"


def _parameter_lines(control: dict) -> list[str]:
    if control.get("status") == "not_applicable":
        return ["Parámetro financiero M33.4: no aplica porque el expediente no informa pacto de intereses."]
    lines = [
        (
            "Parámetro financiero M33.4: "
            f"estado {control.get('status')} · compuerta {control.get('gate')} · "
            f"modalidad {control.get('modality') or 'por verificar'} · "
            f"período {control.get('valid_from') or 'por verificar'} a {control.get('valid_to') or 'por verificar'}."
        )
    ]
    for reason in control.get("reasons") or []:
        lines.append(f"Bloqueo paramétrico: {reason}")
    return lines


def finalize_debt_sources_m33_4(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Adjunta fuentes y control de tasa sin modificar ``sections`` públicas."""
    if (result or {}).get("risk") == "red":
        return specs

    parameter_control = evaluate_interest_parameter_m334(answers, result)
    finalized: list[dict] = []

    for original in specs:
        kind = str(original.get("kind") or "")
        if kind not in DEBT_KINDS:
            finalized.append(original)
            continue

        spec = deepcopy(original)
        source_ids = debt_source_ids(kind, answers)
        manifest = build_legal_source_manifest(source_ids)
        kind_parameter = (
            deepcopy(parameter_control)
            if kind in DEBT_INTEREST_PARAMETER_KINDS
            else {
                "standard": "M33.4",
                "status": "not_applicable",
                "gate": "not_applicable",
                "legal_effect": "document_does_not_reuse_interest_parameter",
                "reasons": [],
            }
        )

        internal = [
            deepcopy(section)
            for section in (spec.get("internal_review_sections") or [])
            if not (isinstance(section, dict) and section.get("_m334_marker") == _CONTROL_MARKER)
        ]
        bullets = source_control_lines(source_ids)
        bullets.extend(_parameter_lines(kind_parameter))
        internal.append({
            "heading": "CONTROL DE FUENTES JURÍDICAS Y PARÁMETROS M33.4 — CO-CD-004",
            "_type": "control",
            "_m334_marker": _CONTROL_MARKER,
            "source_ids": list(source_ids),
            "source_manifest_status": manifest["status"],
            "interest_parameter_status": kind_parameter["status"],
            "interest_parameter_gate": kind_parameter["gate"],
            "bullets": bullets,
            "text": (
                "Control interno. Las normas estables y la certificación periódica de intereses se validan por carriles "
                "distintos. La presencia de una tasa, límite o vigencia en el cálculo no prueba su fuente oficial. Cuando "
                "existan intereses, debe coincidir la modalidad, la fecha del documento y el período exacto de la "
                "certificación de la Superintendencia Financiera. La Ley 2300 de 2023 se registra como control de la "
                "carta de cobranza sin presumir que toda relación empresarial esté dentro de su ámbito. El reporte "
                "crediticio solo activa Ley 1266 cuando el expediente lo informa expresamente. Aprobación jurídica y QA "
                "permanecen pendientes sobre la misma revisión."
            ),
        })

        spec["internal_review_sections"] = internal
        spec["legal_source_manifest"] = manifest
        spec["legal_source_standard_m334"] = "M33.4"
        spec["source_manifest_status_m334"] = manifest["status"]
        spec["source_manifest_gate_m334"] = manifest["status"]
        spec["legal_source_ids_m334"] = list(source_ids)
        spec["interest_parameter_control_m334"] = kind_parameter
        spec["interest_parameter_status_m334"] = kind_parameter["status"]
        spec["interest_parameter_gate_m334"] = kind_parameter["gate"]
        if manifest["status"] != "current":
            release_gate = "release_block_reverification_required"
        elif kind_parameter["gate"] == "release_block_interest_parameter_reverification_required":
            release_gate = kind_parameter["gate"]
        else:
            release_gate = "human_legal_and_qa_review_required"
        spec["release_gate_m334"] = release_gate
        spec["legal_source_scope_m334"] = {
            "document_kind": kind,
            "package_stage": str(answers.get("package_stage") or ""),
            "credit_reporting": "explicit_yes" if str(answers.get("credit_reporting") or "").strip().casefold() in {"sí", "si", "yes", "true", "1"} else "not_activated",
            "collection_law_2300": "conditional_scope_human_review_required" if kind == "collection_letter" else "not_material_to_this_piece",
            "interest_parameter": "period_specific_separate_gate" if kind in DEBT_INTEREST_PARAMETER_KINDS else "not_material_to_this_piece",
        }
        finalized.append(spec)

    return finalized


__all__ = ["finalize_debt_sources_m33_4"]
