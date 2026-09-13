from __future__ import annotations

"""Fuentes y parámetros laborales M33.4 para CO-LA-001.

La norma laboral estable y los parámetros anuales se gobiernan por carriles
separados. El salario mínimo y el auxilio de transporte no se congelan dentro del
registro jurídico: su monto, período y estado procesal deben seguir siendo
revalidables sin reescribir las fuentes sustantivas de la liquidación.
"""

from datetime import date
from typing import Any
from urllib.parse import urlparse

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


LABOR_SOURCE_RECORDS = {
    "CO-CST-LIQUIDATION-2026": {
        "title": "Código Sustantivo del Trabajo vigente — liquidación y reclamación",
        "locator": "Artículos 64, 65, 186, 249, 306, 488 y 489, según el concepto y los hechos acreditados",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Codigo%2F30019323",
        "observed_status": "texto oficial consultado con modificaciones vigentes incorporadas, incluida la modificación del artículo 488 por la Ley 2466 de 2025",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["indemnización", "vacaciones", "cesantías", "prima", "prescripción", "reclamación escrita"],
        "source_kind": "labor_code",
        "applicability": "según modalidad contractual, causa de terminación, período y concepto efectivamente acreditados",
    },
    "CO-LEY50-ART99-CESANTIAS": {
        "title": "Ley 50 de 1990, artículo 99",
        "locator": "Nuevo régimen especial de auxilio de cesantía; liquidación anual, intereses y consignación",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F1604809",
        "observed_status": "vigente; contempla liquidación definitiva anual o por fracción y reconoce intereses legales del 12 % anual o proporcionales en el régimen aplicable",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["cesantías", "intereses a las cesantías", "12 por ciento", "consignación"],
        "source_kind": "statute",
        "applicability": "régimen de cesantías aplicable al vínculo y período objeto de la liquidación",
    },
    "CO-LEY52-ART1-CESANTIAS": {
        "title": "Ley 52 de 1975, artículo 1",
        "locator": "Intereses anuales a las cesantías de trabajadores particulares",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F1606193",
        "observed_status": "vigente; reconoce intereses del 12 % anual o proporcionales sobre cesantías en los supuestos regulados",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["intereses a las cesantías", "12 por ciento", "retiro", "liquidación parcial"],
        "source_kind": "statute",
        "applicability": "control complementario de intereses a las cesantías cuando corresponda al trabajador y período",
    },
    "CO-LEY1788-ART306-PRIMA": {
        "title": "Ley 1788 de 2016, artículo 2",
        "locator": "Modifica el artículo 306 del Código Sustantivo del Trabajo — prima de servicios",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30021671",
        "observed_status": "vigente; prima de servicios equivalente a 30 días de salario por año, pagadera por semestres y proporcional al tiempo trabajado",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["prima de servicios", "30 días", "proporcionalidad", "semestre"],
        "source_kind": "statute",
        "applicability": "cuando la liquidación incluye prima causada y no pagada o saldo proporcional",
    },
    "CO-LEY2466-ART62-PRESCRIPTION": {
        "title": "Ley 2466 de 2025, artículo 62",
        "locator": "Modifica el artículo 488 del Código Sustantivo del Trabajo — prescripción",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/clp/contenidos.dll/Leyes/30055086",
        "observed_status": "vigente desde el 25/06/2025; mantiene regla general de tres años y precisa el cómputo desde la exigibilidad de la obligación, salvo prescripciones especiales",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["prescripción laboral", "tres años", "exigibilidad", "artículo 488"],
        "source_kind": "amending_statute",
        "applicability": "reclamaciones y calendarios de exigibilidad; debe leerse con el artículo 489 y reglas especiales",
    },
    "CO-LEY15-TRANSPORT": {
        "title": "Ley 15 de 1959 — auxilio de transporte",
        "locator": "Artículo 2 y disposiciones concordantes sobre auxilio patronal de transporte",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F1571382",
        "observed_status": "vigente; marco legal del auxilio de transporte, cuyo monto y umbral se actualizan mediante decreto anual",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["auxilio de transporte", "desplazamiento", "monto anual"],
        "source_kind": "statute",
        "applicability": "solo cuando el expediente utiliza auxilio de transporte o conectividad y se verifican sus presupuestos",
    },
}


for source_id, record in LABOR_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record

validate_registry()


LABOR_KINDS = {
    "calculation",
    "claim",
    "evidence_matrix",
    "labor_diagnostic",
    "labor_support_request",
    "labor_deadline_calendar",
    "labor_evidence_index",
}

_BASE = ["CO-CST-LIQUIDATION-2026"]
_BENEFIT_SOURCES = [
    "CO-LEY50-ART99-CESANTIAS",
    "CO-LEY52-ART1-CESANTIAS",
    "CO-LEY1788-ART306-PRIMA",
]
_PRESCRIPTION = ["CO-LEY2466-ART62-PRESCRIPTION"]


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def labor_source_ids(kind: str, answers: dict, result: dict) -> list[str]:
    """Selecciona fuentes según función documental y conceptos efectivamente usados."""
    if kind not in LABOR_KINDS:
        return []

    values = list(_BASE)
    c = (result or {}).get("calculation")
    calculation = c if isinstance(c, dict) else {}
    line_keys = {
        str(item.get("key") or "").strip().casefold()
        for item in (calculation.get("line_items") or [])
        if isinstance(item, dict)
    }

    if kind in {"calculation", "claim", "labor_diagnostic"}:
        if line_keys.intersection({"cesantias", "intereses_cesantias", "prima"}):
            values.extend(_BENEFIT_SOURCES)
    if kind in {"claim", "labor_deadline_calendar", "labor_diagnostic"}:
        values.extend(_PRESCRIPTION)
    if _number(answers.get("transport_aid")) not in (None, 0.0) and kind in {
        "calculation",
        "claim",
        "labor_diagnostic",
    }:
        values.append("CO-LEY15-TRANSPORT")
    if kind in {"evidence_matrix", "labor_support_request", "labor_evidence_index"}:
        values.append("CO-LEY527-ARTS6-7-14")

    return _dedupe(values)


LABOR_PARAMETERS_2026 = {
    "year": 2026,
    "smlmv": 1_750_905,
    "transport_aid": 249_095,
    "transport_salary_threshold_smlmv": 2,
    "indemnity_lower_salary_band_smlmv": 10,
    "wage_decree": "Decreto 1469 de 2025",
    "wage_decree_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30055940",
    "wage_current_status": "operative_pending_merits_decision_after_revocation_of_provisional_suspension",
    "wage_status_decision_date": "2026-07-17",
    "wage_status_authority": "Consejo de Estado · Sección Segunda",
    "wage_status_url": "https://consejodeestado.gov.co/noticias/",
    "wage_status_review_due_on": "2026-09-09",
    "transport_decree": "Decreto 1470 de 2025",
    "transport_decree_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30055941",
    "valid_from": "2026-01-01",
    "valid_to": "2026-12-31",
}


def _official_parameter_url(value: Any) -> bool:
    parsed = urlparse(str(value or ""))
    host = parsed.netloc.casefold()
    return parsed.scheme == "https" and host in {
        "suin-juriscol.gov.co",
        "www.suin-juriscol.gov.co",
        "consejodeestado.gov.co",
        "www.consejodeestado.gov.co",
    }


def evaluate_labor_parameters_m334(
    answers: dict,
    result: dict,
    *,
    as_of: date | None = None,
) -> dict:
    """Valida parámetros anuales sin convertirlos en una fuente jurídica estable."""
    effective_date = as_of or date.today()
    p = LABOR_PARAMETERS_2026
    start_date = _parse_date(answers.get("start_date"))
    end_date = _parse_date(answers.get("end_date"))
    salary = _number(answers.get("monthly_salary"))
    transport = _number(answers.get("transport_aid")) or 0.0
    c = (result or {}).get("calculation")
    calculation = c if isinstance(c, dict) else {}

    reasons: list[str] = []
    warnings: list[str] = []

    if start_date is None or end_date is None:
        reasons.append("Faltan fechas completas del vínculo para determinar el año de los parámetros aplicables.")
    elif start_date > end_date:
        reasons.append("La fecha de inicio es posterior a la fecha de terminación o corte.")
    elif start_date.year != end_date.year:
        reasons.append("El vínculo cruza años calendario y requiere periodizar salario, auxilios y demás parámetros anuales antes de reutilizar una única base.")
    elif end_date.year != p["year"]:
        reasons.append(f"El paquete de parámetros verificado corresponde a 2026 y no puede reutilizarse para {end_date.year}.")

    if effective_date > date.fromisoformat(p["wage_status_review_due_on"]):
        reasons.append("El estado procesal del Decreto 1469 de 2025 requiere revalidación posterior al corte especial del 09/09/2026.")

    for key in ("wage_decree_url", "wage_status_url", "transport_decree_url"):
        if not _official_parameter_url(p[key]):
            reasons.append(f"La procedencia oficial del parámetro anual no supera el control de dominio: {key}.")

    if salary is None or salary <= 0:
        reasons.append("Falta un salario mensual positivo para validar umbrales y bases.")

    expected_transport = float(p["transport_aid"])
    threshold = float(p["smlmv"] * p["transport_salary_threshold_smlmv"])
    if transport > 0:
        if transport != expected_transport:
            reasons.append(
                f"El auxilio informado ({int(round(transport))}) no coincide con el valor anual 2026 verificado ({p['transport_aid']})."
            )
        if salary is not None and salary > threshold:
            reasons.append("El salario informado supera dos SMLMV y es incompatible con el umbral general del auxilio de transporte 2026 usado por la revisión.")
        warnings.append("La coincidencia de monto y umbral salarial no prueba desplazamiento, modalidad de trabajo ni demás presupuestos fácticos del auxilio; requieren revisión humana.")

    indemnity_band = "not_evaluated"
    if salary is not None and salary > 0:
        indemnity_band = (
            "below_10_smlmv"
            if salary < p["smlmv"] * p["indemnity_lower_salary_band_smlmv"]
            else "at_or_above_10_smlmv"
        )
        indemnity_days = _number(calculation.get("indemnity_days"))
        link_days = _number(calculation.get("link_days"))
        contract_type = str(answers.get("contract_type") or "").casefold()
        termination = str(answers.get("termination") or "").casefold()
        if (
            "indefin" in contract_type
            and "sin justa causa" in termination
            and link_days is not None
            and link_days <= 365
            and indemnity_band == "below_10_smlmv"
            and indemnity_days not in (None, 30.0)
        ):
            reasons.append("La banda salarial y antigüedad informadas no son coherentes con los 30 días modelados para la indemnización del artículo 64 en el escenario vigente.")

    cesantias_base = _number(calculation.get("cesantias_base"))
    prima_base = _number(calculation.get("prima_base"))
    if salary is not None and transport > 0:
        expected_benefit_base = salary + transport
        for label, value in (("cesantías", cesantias_base), ("prima", prima_base)):
            if value is not None and abs(value - expected_benefit_base) > 0.5:
                reasons.append(
                    f"La base de {label} no reconcilia con salario más auxilio utilizado por esta revisión; debe verificarse la incidencia jurídica y la base real."
                )

    status = "verified_annual_values" if not reasons else "needs_parameter_reverification"
    gate = (
        "current_annual_values_human_entitlement_review_required"
        if status == "verified_annual_values"
        else "release_block_labor_parameter_reverification_required"
    )
    return {
        "standard": "M33.4",
        "status": status,
        "gate": gate,
        "legal_effect": (
            "parameter_traceability_only; factual_entitlement_and_human_legal_review_required"
            if status == "verified_annual_values"
            else "do_not_rely_on_annual_labor_values_or_thresholds_until_reverified"
        ),
        "verified_on": VERIFIED_ON.isoformat(),
        "as_of": effective_date.isoformat(),
        "parameter_year": p["year"],
        "valid_from": p["valid_from"],
        "valid_to": p["valid_to"],
        "smlmv": p["smlmv"],
        "transport_aid": p["transport_aid"],
        "transport_threshold": int(threshold),
        "indemnity_10_smlmv_threshold": p["smlmv"] * p["indemnity_lower_salary_band_smlmv"],
        "indemnity_salary_band": indemnity_band,
        "wage_decree": p["wage_decree"],
        "wage_decree_url": p["wage_decree_url"],
        "wage_current_status": p["wage_current_status"],
        "wage_status_decision_date": p["wage_status_decision_date"],
        "wage_status_authority": p["wage_status_authority"],
        "wage_status_url": p["wage_status_url"],
        "wage_status_review_due_on": p["wage_status_review_due_on"],
        "transport_decree": p["transport_decree"],
        "transport_decree_url": p["transport_decree_url"],
        "reported_monthly_salary": salary,
        "reported_transport_aid": transport,
        "reasons": reasons,
        "warnings": warnings,
    }


__all__ = [
    "LABOR_KINDS",
    "LABOR_PARAMETERS_2026",
    "LABOR_SOURCE_RECORDS",
    "evaluate_labor_parameters_m334",
    "labor_source_ids",
]
