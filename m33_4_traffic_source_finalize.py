from __future__ import annotations

"""Finalización interna M33.4 para CO-TR-002 — fotodetección y defensa.

Se ejecuta después del pulido de profundidad. Añade únicamente metadata y controles
internos; las ocho piezas públicas quedan inmutadas. Las compuertas fallan cerrado
cuando faltan actos o fechas necesarias para revocación, corrección, caducidad o
prescripción.
"""

from copy import deepcopy

from legalai_platform import traffic_official_domains as _traffic_official_domains  # noqa: F401
from legalai_platform.legal_source_registry import build_legal_source_manifest, source_control_lines
from legalai_platform.traffic_legal_source_pack import TRAFFIC_KINDS, traffic_case_control, traffic_source_ids


_CONTROL_MARKER = "m33_4_traffic_source_control"


def finalize_traffic_sources_m33_4(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    case_control = traffic_case_control(answers)
    risk = str((result or {}).get("risk") or "").casefold()
    finalized: list[dict] = []

    for original in specs:
        kind = str(original.get("kind") or "")
        if kind not in TRAFFIC_KINDS:
            finalized.append(original)
            continue

        spec = deepcopy(original)
        before_sections = deepcopy(spec.get("sections") or [])
        source_ids = traffic_source_ids(kind, answers, result)
        manifest = build_legal_source_manifest(source_ids)

        internal = [
            deepcopy(section)
            for section in (spec.get("internal_review_sections") or [])
            if not (isinstance(section, dict) and section.get("_m334_marker") == _CONTROL_MARKER)
        ]
        bullets = source_control_lines(source_ids)
        bullets.extend([
            "Control M33.4: comparendo, sanción, ejecutoria, registro y cobro son hitos jurídicos distintos; una anotación en SIMIT/RUNT no sustituye el acto fuente.",
            "Control M33.4: C-038/2020 impide responsabilidad solidaria automática por la mera titularidad; C-321/2022 conserva deberes propios del propietario, pero su sanción exige imputación y prueba de incumplimiento culposo dentro del procedimiento.",
            f"Control M33.4 de notificación: {case_control['notification_status']}; conocimiento tardío = {case_control['late_actual_knowledge_effect']}.",
            f"Control M33.4 de caducidad: {case_control['caducity_control']}; prescripción: {case_control['prescription_control']}.",
        ])
        if kind == "traffic_revocation_request":
            bullets.append(
                "Activación revocatoria M33.4: "
                + ("acto sancionatorio y fecha estructurados; revisión humana obligatoria" if case_control["revocation_ready"] else "bloqueada hasta individualizar y verificar acto sancionatorio y fecha")
                + "."
            )
        if kind == "traffic_registry_correction":
            bullets.append(
                "Activación corrección registral M33.4: "
                + ("acto fuente estructurado; revisión humana obligatoria" if case_control["registry_correction_ready"] else "bloqueada hasta acreditar acto fuente idóneo")
                + "."
            )

        internal.append({
            "heading": "CONTROL DE FUENTES JURÍDICAS M33.4 — CO-TR-002",
            "_type": "control",
            "_m334_marker": _CONTROL_MARKER,
            "source_ids": list(source_ids),
            "source_manifest_status": manifest["status"],
            "case_control": deepcopy(case_control),
            "bullets": bullets,
            "text": (
                "Control interno de alta sensibilidad. Una diferencia de dirección, una entrega fallida, un conocimiento tardío, la condición de propietario, "
                "una consulta registral o el transcurso aparente del tiempo no producen por sí solos nulidad, absolución, prescripción, revocación, devolución o "
                "corrección registral. Deben reconstruirse el expediente, la imputación, los actos, las notificaciones, la ejecutoria y el cobro. Aprobación jurídica "
                "y QA permanecen pendientes sobre la misma revisión."
            ),
        })

        spec["internal_review_sections"] = internal
        spec["legal_source_manifest"] = manifest
        spec["legal_source_standard_m334"] = "M33.4"
        spec["legal_source_ids_m334"] = list(source_ids)
        spec["source_manifest_status_m334"] = manifest["status"]
        spec["source_manifest_gate_m334"] = manifest["status"]
        spec["traffic_case_control_m334"] = deepcopy(case_control)

        if manifest["status"] != "current":
            release_gate = "release_block_reverification_required"
        elif kind == "traffic_revocation_request" and not case_control["revocation_ready"]:
            release_gate = "release_block_verified_sanction_act_required"
        elif kind == "traffic_registry_correction" and not case_control["registry_correction_ready"]:
            release_gate = "release_block_registry_source_act_required"
        elif risk == "red":
            release_gate = "release_block_critical_human_review_required"
        else:
            release_gate = "human_legal_and_qa_review_required"
        spec["release_gate_m334"] = release_gate
        spec["legal_source_scope_m334"] = {
            "document_kind": kind,
            "risk": risk or "unclassified",
            "notification_status": case_control["notification_status"],
            "address_status": case_control["address_status"],
            "caducity_control": case_control["caducity_control"],
            "prescription_control": case_control["prescription_control"],
            "revocation_ready": case_control["revocation_ready"],
            "registry_correction_ready": case_control["registry_correction_ready"],
            "public_sections_unchanged": before_sections == (spec.get("sections") or []),
        }
        finalized.append(spec)

    return finalized


__all__ = ["finalize_traffic_sources_m33_4"]
