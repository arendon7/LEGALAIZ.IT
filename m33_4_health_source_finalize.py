from __future__ import annotations

"""Finalización M33.4 de fuentes para CO-SA-001.

Se ejecuta después de M33.3, compatibilidad y pulido de profundidad. Solo añade
metadata y controles internos: las secciones públicas no se reescriben.
"""

from copy import deepcopy

from legalai_platform.health_legal_source_pack import HEALTH_KINDS, health_source_ids
from legalai_platform.legal_source_registry import build_legal_source_manifest, source_control_lines


_CONTROL_MARKER = "m33_4_health_source_control"


def _priority(answers: dict, result: dict) -> str:
    calculation = (result or {}).get("calculation")
    c = calculation if isinstance(calculation, dict) else {}
    text = " ".join(str(value or "") for value in (
        answers.get("priority"),
        c.get("priority"),
        c.get("classification"),
        answers.get("risk_classification"),
        answers.get("vital_risk"),
    )).casefold()
    if "vital" in text and not any(token in text for token in ("no report", "no identificado", "no confirmado", "sin riesgo")):
        return "vital"
    if "prioriz" in text or "priority" in text:
        return "prioritized"
    if "simple" in text:
        return "simple"
    return "unclassified"


def _sector_term(priority: str) -> dict:
    values = {
        "vital": (24, "hours_continuous_maximum"),
        "prioritized": (48, "hours_continuous_maximum"),
        "simple": (72, "hours_continuous_maximum"),
    }
    if priority not in values:
        return {
            "status": "classification_required",
            "hours": None,
            "counting": "not_determined",
            "legal_effect": "do_not_infer_deadline_without_risk_classification",
        }
    hours, counting = values[priority]
    return {
        "status": "current_sector_rule_observed",
        "hours": hours,
        "counting": counting,
        "legal_effect": "maximum_response_term_not_permission_to_delay_clinically_required_attention",
    }


def finalize_health_sources_m33_4(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    """Adjunta trazabilidad incluso en riesgo rojo, manteniendo release fail-closed."""
    priority = _priority(answers, result)
    sector_control = _sector_term(priority)
    risk = str((result or {}).get("risk") or "").casefold()
    finalized: list[dict] = []

    for original in specs:
        kind = str(original.get("kind") or "")
        if kind not in HEALTH_KINDS:
            finalized.append(original)
            continue

        spec = deepcopy(original)
        before_sections = deepcopy(spec.get("sections") or [])
        source_ids = health_source_ids(kind, answers, result)
        manifest = build_legal_source_manifest(source_ids)

        internal = [
            deepcopy(section)
            for section in (spec.get("internal_review_sections") or [])
            if not (isinstance(section, dict) and section.get("_m334_marker") == _CONTROL_MARKER)
        ]
        bullets = source_control_lines(source_ids)
        if kind in {"health_diagnostic", "health_petition", "health_reiteration", "health_supersalud", "health_calendar"}:
            bullets.append(
                "Control sectorial M33.4: "
                f"clasificación {priority}; máximo observado {sector_control.get('hours') or 'por clasificar'} "
                "horas corridas cuando aplica. El máximo administrativo no autoriza a diferir una atención clínica más urgente."
            )
        internal.append({
            "heading": "CONTROL DE FUENTES JURÍDICAS M33.4 — CO-SA-001",
            "_type": "control",
            "_m334_marker": _CONTROL_MARKER,
            "source_ids": list(source_ids),
            "source_manifest_status": manifest["status"],
            "priority_classification": priority,
            "sector_term_control": deepcopy(sector_control),
            "bullets": bullets,
            "text": (
                "Control interno de alta sensibilidad. Las fuentes jurídicas y los términos sectoriales se trazan sin sustituir valoración clínica. "
                "PQRD administrativa, función jurisdiccional de Supersalud y tutela son rutas distintas; ninguna se activa automáticamente ni se "
                "convierte en requisito previo universal de las demás. La historia clínica conserva reserva y minimización. La aprobación jurídica, "
                "la validación clínica/factual cuando corresponda y QA permanecen pendientes sobre la misma revisión."
            ),
        })

        spec["internal_review_sections"] = internal
        spec["legal_source_manifest"] = manifest
        spec["legal_source_standard_m334"] = "M33.4"
        spec["legal_source_ids_m334"] = list(source_ids)
        spec["source_manifest_status_m334"] = manifest["status"]
        spec["source_manifest_gate_m334"] = manifest["status"]
        spec["health_priority_m334"] = priority
        spec["health_sector_term_control_m334"] = deepcopy(sector_control)
        if manifest["status"] != "current":
            release_gate = "release_block_reverification_required"
        elif risk == "red":
            release_gate = "release_block_critical_human_review_required"
        else:
            release_gate = "human_legal_and_qa_review_required"
        spec["release_gate_m334"] = release_gate
        spec["legal_source_scope_m334"] = {
            "document_kind": kind,
            "risk": risk or "unclassified",
            "priority": priority,
            "sector_term_hours": sector_control.get("hours"),
            "sector_term_counting": sector_control.get("counting"),
            "public_sections_unchanged": before_sections == (spec.get("sections") or []),
        }
        finalized.append(spec)

    return finalized


__all__ = ["finalize_health_sources_m33_4"]
