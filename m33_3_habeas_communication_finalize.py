from __future__ import annotations

"""Presentación compacta M33.3 del control de comunicación previa CO-CD-001."""

from copy import deepcopy
from datetime import date
from typing import Any

COMMUNICATION_STANDARD = "M33.3-habeas-prior-communication-v1"

_STATUS_LABELS = {
    "preliminarily_supported": "envío preliminarmente soportado",
    "not_proven": "cumplimiento no acreditado con la evidencia disponible",
    "noncompliance_preliminary": "posible incumplimiento sujeto a validación jurídica",
}


def _calc(result: dict) -> dict:
    value = (result or {}).get("calculation")
    return value if isinstance(value, dict) else {}


def _date_es(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "por verificar"
    try:
        parsed = date.fromisoformat(text[:10])
    except ValueError:
        return text
    months = (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    )
    return f"{parsed.day} de {months[parsed.month - 1]} de {parsed.year}"


def _summary(calculation: dict) -> str:
    status = str(calculation.get("communication_status") or "not_proven")
    label = _STATUS_LABELS.get(status, status)
    send_date = _date_es(calculation.get("prior_communication_date"))
    report_date = _date_es(calculation.get("communication_report_date"))
    lead = calculation.get("communication_lead_calendar_days")
    lead_text = f"{lead} días calendario" if isinstance(lead, int) else "antelación por verificar"
    channel = str(calculation.get("communication_channel") or "canal por verificar")
    received = str(calculation.get("communication_received_status") or "No informado")
    return (
        f"Control M33.3 de comunicación previa: {label}. Envío: {send_date}; reporte: {report_date}; "
        f"intervalo: {lead_text}; canal: {channel}; recepción declarada: {received}. La recepción y el envío "
        "son hechos distintos; el expediente debe conservar prueba individualizable de envío, destino y contenido."
    )


def _small_note(calculation: dict) -> str | None:
    if calculation.get("small_obligation_preliminary") is not True:
        return None
    first_date = _date_es(calculation.get("communication_first_date"))
    last_date = _date_es(calculation.get("prior_communication_date"))
    return (
        "Pequeña cuantía: verificar al menos dos comunicaciones en días diferentes. "
        f"Primera: {first_date}; última: {last_date}; los veinte días se controlan desde la última hasta el reporte."
    )


def _append_unique(paragraphs: list, text: str | None) -> list:
    result = list(paragraphs or [])
    if text and text not in result:
        result.append(text)
    return result


def _evidence_status(calculation: dict) -> str:
    status = str(calculation.get("communication_status") or "not_proven")
    if status == "preliminarily_supported":
        return "Envío preliminarmente soportado; conservar original y trazabilidad"
    if status == "noncompliance_preliminary":
        return "Posible incumplimiento; requiere cotejo del soporte y consecuencia aplicable"
    return "Envío no acreditado suficientemente; solicitar soporte completo"


def finalize_habeas_communication_m33_3(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    calculation = _calc(result)
    if calculation.get("communication_standard") != COMMUNICATION_STANDARD:
        return specs

    summary = _summary(calculation)
    small_note = _small_note(calculation)
    consequence = str(calculation.get("communication_consequence_if_noncompliance") or "").strip()
    finalized: list[dict] = []

    for original in specs:
        spec = deepcopy(original)
        kind = str(spec.get("kind") or "")
        sections = deepcopy(spec.get("sections") or [])

        for section in sections:
            if not isinstance(section, dict):
                continue
            heading = str(section.get("heading") or "").casefold()

            # La reclamación sí debe explicar el control jurídico aplicado al caso.
            if kind == "habeas_claim" and "comunicación previa y permanencia" in heading:
                section["paragraphs"] = _append_unique(section.get("paragraphs") or [], summary)
                section["paragraphs"] = _append_unique(section.get("paragraphs") or [], small_note)
                if calculation.get("communication_status") == "noncompliance_preliminary":
                    section["paragraphs"] = _append_unique(section.get("paragraphs") or [], consequence)

            # La consulta ya solicita texto íntegro, fecha, prueba de envío, destinatario,
            # canal y dirección. Repetir aquí la síntesis jurídica crea una página de firma
            # residual sin agregar una petición nueva; por eso solo conserva metadatos M33.3.

            table = section.get("table")
            if kind == "habeas_evidence_matrix" and isinstance(table, list):
                for row in table:
                    if isinstance(row, list) and row and str(row[0]) == "HD-EV-005":
                        while len(row) < 4:
                            row.append("")
                        row[3] = _evidence_status(calculation)

        spec["sections"] = sections
        spec["communication_standard"] = COMMUNICATION_STANDARD
        spec["communication_ruleset_verified_at"] = calculation.get("communication_ruleset_verified_at")
        finalized.append(spec)
    return finalized


__all__ = ["finalize_habeas_communication_m33_3"]
