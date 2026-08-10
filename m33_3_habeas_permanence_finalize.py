from __future__ import annotations

"""Presentación M33.3 del control de permanencia en documentos CO-CD-001.

La capa no calcula términos. Consume la salida de `m33_3_habeas_permanence_guard`
y evita presentar simultáneamente las rutas pagada e insoluta como si ambas fueran
aplicables al mismo expediente.
"""

from copy import deepcopy
from datetime import date
from typing import Any


_ROUTE_LABELS = {
    "paid_or_extinguished": "Obligación pagada o extinguida",
    "unpaid": "Obligación insoluta / vigente en mora",
    "disputed_or_unrecognized": "Obligación discutida o no reconocida",
    "undetermined": "Estado de obligación por precisar",
}


def _calc(result: dict) -> dict:
    value = (result or {}).get("calculation")
    return value if isinstance(value, dict) else {}


def _date_es(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "No calculable con la evidencia disponible"
    try:
        parsed = date.fromisoformat(text[:10])
    except ValueError:
        return text
    months = (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    )
    return f"{parsed.day} de {months[parsed.month - 1]} de {parsed.year}"


def _status_text(calculation: dict) -> str:
    complete = calculation.get("permanence_evidence_complete")
    completed = calculation.get("permanence_term_completed_at_reference")
    if not complete:
        return "No concluyente: faltan presupuestos temporales o el estado está controvertido"
    if completed is True:
        return "Término preliminar cumplido al corte; exige cotejo del reporte y soportes"
    if completed is False:
        return "Término preliminar en curso al corte de verificación"
    return "Estado temporal por verificar"


def _rewrite_permanence_table(table: list[list[Any]], calculation: dict) -> list[list[Any]]:
    route = str(calculation.get("permanence_route") or "undetermined")
    paid = calculation.get("paid_negative_expiry_preliminary")
    unpaid = calculation.get("unpaid_negative_expiry_preliminary")
    applicable = calculation.get("permanence_applicable_expiry")

    rewritten: list[list[Any]] = []
    for row in deepcopy(table):
        if not row:
            rewritten.append(row)
            continue
        label = str(row[0])
        if label == "Retiro preliminar del dato pagado":
            if route == "paid_or_extinguished":
                row[1] = _date_es(paid)
                row[2] = "Ruta aplicable; requiere acreditar mora y pago/extinción antes de exigir retiro"
            else:
                row[1] = "No aplica como ruta principal"
                row[2] = "Hipótesis de dato pagado no seleccionada para el estado actual"
        elif label == "Caducidad preliminar del dato insoluto":
            if route == "unpaid":
                row[1] = _date_es(unpaid)
                row[2] = "Ruta aplicable; ocho años desde la mora no extinguen la obligación subyacente"
            else:
                row[1] = "No aplica como ruta principal"
                row[2] = "Hipótesis de obligación insoluta no seleccionada para el estado actual"
        rewritten.append(row)

    rewritten.append([
        "Ruta temporal aplicable",
        _ROUTE_LABELS.get(route, route),
        _status_text(calculation),
    ])
    rewritten.append([
        "Fecha aplicable / corte M33.3",
        _date_es(applicable),
        f"Corte jurídico: {_date_es(calculation.get('permanence_reference_date'))}; ruleset {_date_es(calculation.get('permanence_ruleset_verified_at'))}",
    ])
    return rewritten


def finalize_habeas_permanence_m33_3(specs: list[dict], result: dict) -> list[dict]:
    calculation = _calc(result)
    if calculation.get("permanence_standard") != "M33.3-habeas-permanence-v1":
        return specs

    finalized: list[dict] = []
    for original in specs:
        spec = deepcopy(original)
        sections = deepcopy(spec.get("sections") or [])
        for section in sections:
            if not isinstance(section, dict):
                continue
            table = section.get("table")
            if not isinstance(table, list):
                continue
            labels = {str(row[0]) for row in table if isinstance(row, list) and row}
            if "Retiro preliminar del dato pagado" not in labels and "Caducidad preliminar del dato insoluto" not in labels:
                continue
            section["table"] = _rewrite_permanence_table(table, calculation)
            paragraphs = list(section.get("paragraphs") or [])
            note = (
                "M33.3 separa la permanencia del dato de la existencia de la obligación. Una fecha temporal "
                "cumplida puede sustentar una solicitud de actualización o retiro del dato negativo, pero no "
                "declara pago, inexistencia, prescripción ni extinción de la obligación. Si la obligación es "
                "discutida o no reconocida, la controversia sobre veracidad, autoría y soporte conserva prioridad."
            )
            if note not in paragraphs:
                paragraphs.append(note)
            section["paragraphs"] = paragraphs
        spec["sections"] = sections
        spec["permanence_standard"] = calculation.get("permanence_standard")
        spec["permanence_ruleset_verified_at"] = calculation.get("permanence_ruleset_verified_at")
        finalized.append(spec)
    return finalized


__all__ = ["finalize_habeas_permanence_m33_3"]
