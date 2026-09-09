from __future__ import annotations

"""Compuerta M33.3 de comunicación previa para CO-CD-001.

Separa envío de recepción y exige una cronología probatoria suficiente antes de
presentar como cumplido el artículo 12 de la Ley 1266 de 2008. La conclusión es
siempre preliminar y no sustituye el cotejo del soporte original.

Ruleset verificado: 2026-08-10.
"""

from datetime import date
from functools import wraps
from types import ModuleType
from typing import Any

RULESET_VERIFIED_AT = "2026-08-10"
COMMUNICATION_STANDARD = "M33.3-habeas-prior-communication-v1"
LEGAL_BASIS = (
    "Ley Estatutaria 1266 de 2008, artículo 12",
    "Ley Estatutaria 1266 de 2008, artículo 13 parágrafo 2, adicionado por la Ley 2157 de 2021",
    "Decreto 2952 de 2010, artículo 2",
    "Criterios administrativos SIC sobre prueba de envío, destino y canales alternos",
)

_PAID_STATES = {"Pagada", "Extinguida por otro modo"}
_UNPAID_STATE = "Vigente y en mora"
_PHYSICAL_CHANNELS = {"Dirección física registrada", "Extracto periódico físico"}
_ALTERNATIVE_CHANNELS = {
    "Extracto periódico electrónico",
    "Correo electrónico",
    "SMS u otro mensaje de datos",
    "Otro mecanismo pactado",
}
_LEGACY_ISSUES = {"CD1-CALC-06", "CD1-CALC-09", "CD1-CALC-11"}


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _append_issue(issues: list, issue: dict) -> None:
    if not any(isinstance(item, dict) and item.get("id") == issue.get("id") for item in issues):
        issues.append(issue)


def _issue(issue_id: str, message: str, risk: str = "yellow") -> dict:
    return {"id": issue_id, "risk": risk, "message": message}


def _consequence(status: str, communication_status: str) -> str:
    if communication_status != "noncompliance_preliminary":
        return "No se aplica consecuencia automática: primero debe acreditarse o descartarse el incumplimiento."
    if status in _PAID_STATES:
        return (
            "Si se confirma la omisión de la comunicación previa y la obligación ya estaba extinguida, "
            "corresponde controlar la regla de retiro inmediato del reporte negativo."
        )
    if status == _UNPAID_STATE:
        return (
            "Si se confirma la omisión y la obligación permanece insoluta, debe controlarse el retiro del "
            "reporte y el cumplimiento de la comunicación previa antes de un eventual nuevo reporte."
        )
    return (
        "La consecuencia no puede seleccionarse sin precisar el estado de la obligación; no debe inferirse "
        "pago, extinción, vigencia o exigibilidad a partir del defecto de comunicación."
    )


def enforce_habeas_prior_communication(answers: dict, calculation: dict) -> dict:
    calculation = calculation if isinstance(calculation, dict) else {}
    issues = [
        item for item in list(calculation.get("issues") or [])
        if not (isinstance(item, dict) and item.get("id") in _LEGACY_ISSUES)
    ]

    sent = str(answers.get("prior_communication_sent") or "").strip()
    received = str(answers.get("prior_communication_received") or "").strip()
    evidence = str(answers.get("prior_communication_evidence") or "").strip()
    channel = str(answers.get("prior_communication_channel") or "").strip()
    destination = str(answers.get("prior_communication_destination_verified") or "").strip()
    alt_agreed = str(answers.get("prior_communication_alternative_channel_agreed") or "").strip()
    consultable = str(answers.get("prior_communication_message_consultable") or "").strip()
    content_sufficient = str(answers.get("prior_communication_content_sufficient") or "").strip()
    two_notices = str(answers.get("small_obligation_two_notices") or "").strip()

    send_date = _parse_date(answers.get("prior_communication_date"))
    first_date = _parse_date(answers.get("prior_communication_first_date"))
    report_date = _parse_date(answers.get("report_date") or calculation.get("report_date"))
    amount = _number(answers.get("obligation_amount"))
    threshold = _number(calculation.get("small_obligation_reference_value"))
    small_scope_known = amount is not None and threshold is not None and threshold > 0
    small_obligation = bool(small_scope_known and amount <= threshold)

    definite_failure = False
    uncertainty = False
    lead_days = None

    if sent == "No":
        definite_failure = True
        _append_issue(issues, _issue(
            "CD1-M33-COMM-SEND-UNPROVEN",
            "La fuente no acredita el envío de la comunicación previa antes del reporte negativo.",
        ))
    elif sent in {"", "No sé"}:
        uncertainty = True
        _append_issue(issues, _issue(
            "CD1-M33-COMM-SEND-UNPROVEN",
            "No está acreditado si la comunicación previa fue enviada; la recepción declarada no resuelve por sí sola este punto.",
        ))
    elif sent == "Sí":
        if not send_date:
            uncertainty = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-SEND-DATE",
                "Se declara envío de comunicación previa, pero falta una fecha de envío verificable.",
            ))
        if evidence != "Completa":
            uncertainty = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-EVIDENCE",
                "La prueba de envío no es completa; no puede darse por acreditado el cumplimiento con una afirmación genérica.",
            ))
        if destination == "No":
            definite_failure = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-DESTINATION",
                "El destino acreditado no corresponde a la última dirección o canal registrado o pactado; la comunicación no puede tratarse como válida sin revisión.",
            ))
        elif destination != "Sí":
            uncertainty = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-DESTINATION",
                "No está verificado que el envío se dirigiera a la última dirección o canal registrado o pactado.",
            ))
        if channel in _ALTERNATIVE_CHANNELS:
            if alt_agreed == "No":
                definite_failure = True
                _append_issue(issues, _issue(
                    "CD1-M33-COMM-ALT-CHANNEL",
                    "El canal alterno o electrónico no aparece pactado o autorizado por el titular.",
                ))
            elif alt_agreed != "Sí":
                uncertainty = True
                _append_issue(issues, _issue(
                    "CD1-M33-COMM-ALT-CHANNEL",
                    "No está acreditado que el canal alterno o electrónico hubiera sido pactado o autorizado.",
                ))
            if consultable == "No":
                definite_failure = True
                _append_issue(issues, _issue(
                    "CD1-M33-COMM-CONSULTABLE",
                    "La comunicación por mensaje de datos o canal alterno no aparece disponible para consulta posterior.",
                ))
            elif consultable != "Sí":
                uncertainty = True
                _append_issue(issues, _issue(
                    "CD1-M33-COMM-CONSULTABLE",
                    "No está acreditada la posibilidad de consultar posteriormente la comunicación enviada por canal alterno o electrónico.",
                ))
        elif channel in _PHYSICAL_CHANNELS:
            pass
        elif channel in {"", "No sé"}:
            uncertainty = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-CHANNEL",
                "El canal de envío no está individualizado; debe verificarse antes de concluir cumplimiento.",
            ))
        if content_sufficient == "No":
            definite_failure = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-CONTENT",
                "El contenido informado no permite individualizar suficientemente la obligación o el reporte para ejercer contradicción antes del reporte negativo.",
            ))
        elif content_sufficient != "Sí":
            uncertainty = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-CONTENT",
                "No está verificado que el contenido de la comunicación permitiera identificar y controvertir el reporte negativo.",
            ))

    if send_date and report_date:
        lead_days = (report_date - send_date).days
        if send_date > report_date:
            definite_failure = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-CHRONOLOGY",
                "La fecha de envío de la comunicación previa aparece posterior al reporte negativo.",
                "red",
            ))
        elif lead_days < 20:
            definite_failure = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-LEAD",
                "Entre el envío de la última comunicación previa y el reporte no transcurren veinte días calendario.",
            ))
    elif sent == "Sí":
        uncertainty = True
        _append_issue(issues, _issue(
            "CD1-M33-COMM-REPORT-DATE",
            "No hay fechas suficientes para verificar los veinte días calendario entre el envío y el reporte.",
        ))

    if not small_scope_known:
        uncertainty = True
        _append_issue(issues, _issue(
            "CD1-M33-COMM-SMALL-SCOPE",
            "No puede determinarse si aplica la regla especial de obligaciones iguales o inferiores al 15 % de un SMLMV porque falta una cuantía utilizable.",
        ))
    elif small_obligation:
        if two_notices == "No":
            definite_failure = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-SMALL-TWO-NOTICES",
                "Para la pequeña cuantía modelada no se acreditan al menos dos comunicaciones en días diferentes.",
            ))
        elif two_notices != "Sí":
            uncertainty = True
            _append_issue(issues, _issue(
                "CD1-M33-COMM-SMALL-TWO-NOTICES",
                "No está acreditado si la pequeña cuantía recibió al menos dos comunicaciones en días diferentes.",
            ))
        if two_notices == "Sí":
            if not first_date or not send_date:
                uncertainty = True
                _append_issue(issues, _issue(
                    "CD1-M33-COMM-FIRST-DATE",
                    "Se declaran dos comunicaciones, pero faltan fechas suficientes para probar que fueron enviadas en días diferentes.",
                ))
            elif first_date >= send_date:
                definite_failure = True
                _append_issue(issues, _issue(
                    "CD1-M33-COMM-FIRST-DATE",
                    "La primera y la última comunicación no acreditan dos días de envío distintos y cronológicamente ordenados.",
                ))

    if definite_failure:
        communication_status = "noncompliance_preliminary"
    elif uncertainty:
        communication_status = "not_proven"
    else:
        communication_status = "preliminarily_supported"

    obligation_status = str(answers.get("obligation_status") or "").strip()
    calculation["issues"] = issues
    calculation["communication_standard"] = COMMUNICATION_STANDARD
    calculation["communication_ruleset_verified_at"] = RULESET_VERIFIED_AT
    calculation["communication_legal_basis"] = list(LEGAL_BASIS)
    calculation["communication_status"] = communication_status
    calculation["communication_sent_status"] = sent or "No informado"
    calculation["communication_received_status"] = received or "No informado"
    calculation["communication_receipt_is_independent_fact"] = True
    calculation["prior_communication_date"] = send_date.isoformat() if send_date else None
    calculation["communication_report_date"] = report_date.isoformat() if report_date else None
    calculation["communication_lead_calendar_days"] = lead_days
    calculation["communication_channel"] = channel or None
    calculation["communication_destination_verified"] = destination or None
    calculation["communication_evidence"] = evidence or None
    calculation["communication_content_sufficient"] = content_sufficient or None
    calculation["communication_small_obligation_scope_known"] = small_scope_known
    calculation["small_obligation_preliminary"] = small_obligation if small_scope_known else None
    calculation["communication_first_date"] = first_date.isoformat() if first_date else None
    calculation["communication_two_notices_status"] = two_notices or None
    calculation["communication_consequence_if_noncompliance"] = _consequence(obligation_status, communication_status)
    return calculation


def install_m33_3_habeas_communication_guard(core_module: ModuleType) -> bool:
    current = getattr(core_module, "habeas_data_calc", None)
    if current is None:
        return False
    if getattr(current, "_legalaiz_m33_3_communication_guard", False):
        return True

    @wraps(current)
    def wrapped(answers: dict):
        calculation = current(answers)
        return enforce_habeas_prior_communication(answers, calculation)

    wrapped._legalaiz_m33_3_communication_guard = True
    wrapped._legalaiz_original = current
    setattr(core_module, "habeas_data_calc", wrapped)
    return True


__all__ = [
    "COMMUNICATION_STANDARD",
    "LEGAL_BASIS",
    "RULESET_VERIFIED_AT",
    "enforce_habeas_prior_communication",
    "install_m33_3_habeas_communication_guard",
]
