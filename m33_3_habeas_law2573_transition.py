from __future__ import annotations

"""Compuerta M33.3 para la transición de la Ley Estatutaria 2573 de 2026.

Regla temporal verificada al 2026-08-10:
- vigencia general: 20 de noviembre de 2026;
- excepción inmediata: parágrafos 1 y 2 del artículo 5 desde la promulgación;
- los demás artículos no se aplican anticipadamente durante la ventana transitoria.

La compuerta NO decide que existió suplantación, incumplimiento de seguridad ni
responsabilidad. El parágrafo 2 solo se presenta como candidato preliminar cuando
existen hechos estructurados, soporte suficiente y un instrumento oficial de seguridad
individualizado, vigente y materialmente aplicable. Siempre exige revisión jurídica
humana antes de invocar consecuencias patrimoniales o de reporte.
"""

from copy import deepcopy
from datetime import date
from functools import wraps
from types import ModuleType
from typing import Any

LAW_PROMULGATION = date(2026, 5, 20)
LAW_GENERAL_EFFECTIVE = date(2026, 11, 20)
RULESET_VERIFIED_AT = "2026-08-10"
TRANSITION_STANDARD = "M33.3-law2573-transition-v2"
LEGAL_BASIS = (
    "Ley Estatutaria 2573 de 2026, artículo 13",
    "Ley Estatutaria 2573 de 2026, artículo 5 parágrafo 1",
    "Ley Estatutaria 2573 de 2026, artículo 5 parágrafo 2",
)
SPECIFIC_PROTOCOL_REVIEW_STATUS = "not_identified_in_official_sources_reviewed"
SPECIFIC_PROTOCOL_REVIEW_LIMITATION = (
    "La revisión regulatoria M33.3 no identificó en las fuentes oficiales consultadas un acto específico que ya reglamente el protocolo del parágrafo 1. "
    "Este registro no prueba inexistencia y debe revalidarse antes de una decisión jurídica o liberación documental."
)


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _yes(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"sí", "si", "yes", "true", "1"}


def _reference_date(answers: dict, calculation: dict) -> date | None:
    return _parse_date(
        calculation.get("reference_date")
        or calculation.get("filing_date")
        or answers.get("filing_date")
    )


def _transition_phase(ref: date | None) -> str:
    if ref is None:
        return "reference_date_missing"
    if ref < LAW_PROMULGATION:
        return "pre_promulgation"
    if ref < LAW_GENERAL_EFFECTIVE:
        return "partial_immediate_only"
    return "general_regime_effective"


def _instrument_is_individualized(authority: str, reference: str, requirement: str, applicable: str) -> bool:
    return bool(
        authority not in {"", "No sé"}
        and len(reference.strip()) >= 4
        and len(requirement.strip()) >= 10
        and applicable == "Sí"
    )


def enforce_law2573_transition(answers: dict, calculation: dict) -> dict:
    calculation = calculation if isinstance(calculation, dict) else {}
    ref = _reference_date(answers, calculation)
    phase = _transition_phase(ref)

    identity = str(answers.get("identity_theft") or "").strip()
    correction = str(answers.get("identity_theft_correction_requested") or "").strip()
    security_breach = str(answers.get("identity_theft_security_noncompliance_verified") or "").strip()
    support = str(answers.get("identity_theft_security_noncompliance_support") or "").strip()
    authority = str(answers.get("identity_theft_security_instrument_authority") or "").strip()
    instrument_reference = str(answers.get("identity_theft_security_instrument_reference") or "").strip()
    requirement_tested = str(answers.get("identity_theft_security_requirement_tested") or "").strip()
    instrument_applicable = str(answers.get("identity_theft_security_instrument_applicable") or "").strip()
    instrument_individualized = _instrument_is_individualized(
        authority, instrument_reference, requirement_tested, instrument_applicable
    )

    p1_status = "not_yet_effective"
    p2_status = "not_yet_effective"
    deferred_articles_status = "not_yet_effective"
    human_review = False
    reasons: list[str] = []

    if phase == "partial_immediate_only":
        p1_status = "in_force_regulatory_mandate"
        deferred_articles_status = "deferred_until_2026-11-20"

        if not _yes(identity):
            p2_status = "not_applicable_without_identity_theft_track"
            reasons.append("No hay una ruta de posible suplantación activada para el producto controvertido.")
        elif correction == "No":
            p2_status = "not_applicable_without_correction_request"
            reasons.append("No se acredita solicitud de corrección del titular manifestando posible suplantación.")
        elif correction in {"", "No sé"}:
            p2_status = "not_proven_correction_request"
            human_review = True
            reasons.append("Debe verificarse si existió una solicitud de corrección específicamente asociada a la posible suplantación.")
        elif security_breach == "No":
            p2_status = "not_applicable_without_verified_security_noncompliance"
            reasons.append("No existe incumplimiento verificado de lineamientos, recomendaciones o protocolos de seguridad aplicables.")
        elif security_breach in {"", "No sé"}:
            p2_status = "not_proven_security_noncompliance"
            human_review = True
            reasons.append("La sola ocurrencia del fraude no demuestra incumplimiento de un instrumento oficial de seguridad aplicable.")
        elif security_breach == "Sí" and support != "Completo":
            p2_status = "not_proven_security_support"
            human_review = True
            reasons.append("Se afirma incumplimiento de seguridad, pero el soporte no está completo para invocar consecuencias del parágrafo 2.")
        elif security_breach == "Sí" and instrument_applicable == "No":
            p2_status = "not_applicable_security_instrument"
            human_review = True
            reasons.append("El instrumento identificado no estaba vigente o no era materialmente aplicable a la entidad, canal u operación del caso.")
        elif security_breach == "Sí" and not instrument_individualized:
            p2_status = "not_proven_official_security_instrument"
            human_review = True
            reasons.append(
                "Aunque se informa soporte completo, no se individualizó de forma suficiente la autoridad, el instrumento oficial, el requisito de seguridad cotejado y su aplicabilidad temporal/material."
            )
        elif security_breach == "Sí" and support == "Completo" and instrument_individualized:
            p2_status = "preliminary_candidate_human_review_required"
            human_review = True
            reasons.append(
                "Existen los hechos estructurados mínimos y se individualizó un instrumento oficial de seguridad vigente y aplicable; aun así, la aplicación del parágrafo 2 y sus consecuencias exige revisión jurídica humana de la competencia de la autoridad, texto exacto del requisito, evidencia del incumplimiento y nexo con la operación defraudada."
            )
    elif phase == "general_regime_effective":
        p1_status = "in_force"
        p2_status = "in_force_article_by_article_verification_required"
        deferred_articles_status = "general_regime_effective_article_by_article_review"
        human_review = _yes(identity)
        reasons.append(
            "La vigencia general ya inició; deben aplicarse los artículos pertinentes de la Ley 2573 de 2026 de forma coordinada con Leyes 1266 de 2008, 2157 de 2021 y 1581 de 2012, sin automatizar consecuencias por la sola fecha de vigencia."
        )
    elif phase == "pre_promulgation":
        reasons.append("La fecha de referencia es anterior a la promulgación de la Ley 2573 de 2026.")
    else:
        p1_status = "reference_date_missing"
        p2_status = "reference_date_missing"
        deferred_articles_status = "reference_date_missing"
        human_review = _yes(identity)
        reasons.append("Falta fecha de referencia para seleccionar el régimen temporal aplicable.")

    calculation["law2573_transition_standard"] = TRANSITION_STANDARD
    calculation["law2573_ruleset_verified_at"] = RULESET_VERIFIED_AT
    calculation["law2573_reference_date"] = ref.isoformat() if ref else None
    calculation["law2573_transition_phase"] = phase
    calculation["law2573_general_effective_date"] = LAW_GENERAL_EFFECTIVE.isoformat()
    calculation["law2573_article5_paragraph1_status"] = p1_status
    calculation["law2573_article5_paragraph2_status"] = p2_status
    calculation["law2573_articles_6_to_10_status"] = deferred_articles_status
    calculation["law2573_identity_correction_request"] = correction or "No informado"
    calculation["law2573_security_noncompliance_verified"] = security_breach or "No informado"
    calculation["law2573_security_noncompliance_support"] = support or "No informado"
    calculation["law2573_security_instrument_authority"] = authority or "No informado"
    calculation["law2573_security_instrument_reference"] = instrument_reference or None
    calculation["law2573_security_requirement_tested"] = requirement_tested or None
    calculation["law2573_security_instrument_applicable"] = instrument_applicable or "No informado"
    calculation["law2573_security_instrument_individualized"] = instrument_individualized
    calculation["law2573_specific_protocol_review_status"] = SPECIFIC_PROTOCOL_REVIEW_STATUS
    calculation["law2573_specific_protocol_reviewed_at"] = RULESET_VERIFIED_AT
    calculation["law2573_specific_protocol_review_limitation"] = SPECIFIC_PROTOCOL_REVIEW_LIMITATION
    calculation["law2573_existing_security_instruments_may_apply"] = True
    calculation["law2573_human_review_required"] = human_review
    calculation["law2573_transition_reasons"] = reasons
    calculation["law2573_legal_basis"] = list(LEGAL_BASIS)
    return calculation


def _status_text(calculation: dict) -> str:
    phase = calculation.get("law2573_transition_phase")
    p2 = calculation.get("law2573_article5_paragraph2_status")
    if phase == "partial_immediate_only":
        base = (
            "Al corte del expediente, la vigencia general de la Ley 2573 de 2026 continúa diferida hasta el 20 de noviembre de 2026. "
            "Los parágrafos 1 y 2 del artículo 5 están vigentes desde la promulgación. El parágrafo 1 constituye un mandato regulatorio a las autoridades; en el corte regulatorio M33.3 no se ha incorporado al expediente un acto específico de reglamentación de ese protocolo y ello no prueba su inexistencia, por lo que debe revalidarse la fuente oficial antes de una decisión. "
            "El parágrafo 2 puede requerir el cotejo de lineamientos, recomendaciones o protocolos de seguridad oficiales preexistentes que resulten vigentes y aplicables al caso."
        )
        if p2 == "preliminary_candidate_human_review_required":
            authority = str(calculation.get("law2573_security_instrument_authority") or "autoridad por verificar")
            instrument = str(calculation.get("law2573_security_instrument_reference") or "instrumento por verificar")
            return base + (
                f" El parágrafo 2 aparece como candidato preliminar porque se informan solicitud de corrección, incumplimiento de seguridad con soporte completo e instrumento individualizado ({authority}: {instrument}). "
                "Antes de solicitar suspensión de cobranza, modificación del reporte, devolución o eliminación de acreencias debe existir revisión jurídica humana de la competencia, vigencia, texto exacto del requisito, evidencia del incumplimiento y nexo con la operación."
            )
        if p2 in {
            "not_proven_security_noncompliance",
            "not_proven_security_support",
            "not_proven_correction_request",
            "not_proven_official_security_instrument",
        }:
            return base + (
                " Con la evidencia disponible no están demostrados todos los presupuestos del parágrafo 2; por tanto, sus consecuencias no deben invocarse como automáticas."
            )
        if p2 == "not_applicable_security_instrument":
            return base + (
                " El instrumento informado no aparece vigente o materialmente aplicable al caso; no debe utilizarse como presupuesto del parágrafo 2."
            )
        return base + (
            " En el estado actual no se configuran todos los presupuestos estructurados para invocar el parágrafo 2 como medida inmediata."
        )
    if phase == "general_regime_effective":
        return (
            "La vigencia general de la Ley 2573 de 2026 ya inició. Su aplicación debe hacerse artículo por artículo, coordinada con el régimen general de hábeas data y con los hechos probados del expediente; la fecha de vigencia no activa por sí sola una suspensión, exoneración o eliminación de obligaciones."
        )
    if phase == "pre_promulgation":
        return "La fecha de referencia es anterior a la promulgación de la Ley 2573 de 2026; no se aplica esta ley al hecho temporal modelado."
    return "No existe fecha de referencia suficiente para seleccionar con certeza el régimen temporal de la Ley 2573 de 2026."


def finalize_law2573_transition(specs: list[dict], answers: dict, result: dict) -> list[dict]:
    calculation = (result or {}).get("calculation")
    if not isinstance(calculation, dict) or calculation.get("law2573_transition_standard") != TRANSITION_STANDARD:
        return specs

    status_text = _status_text(calculation)
    finalized: list[dict] = []
    for original in specs:
        spec = deepcopy(original)
        if spec.get("kind") == "identity_theft_protocol":
            sections = deepcopy(spec.get("sections") or [])
            for section in sections:
                if not isinstance(section, dict):
                    continue
                heading = str(section.get("heading") or "").casefold()
                if "régimen jurídico y control temporal" in heading:
                    numbered = list(section.get("numbered") or [])
                    numbered = [
                        item for item in numbered
                        if "mientras no haya entrado en vigor el régimen general diferido" not in str(item).casefold()
                        and "al corte del expediente, la vigencia general de la ley 2573" not in str(item).casefold()
                    ]
                    numbered.append(status_text)
                    numbered.append(
                        "Durante la ventana transitoria no se aplican anticipadamente como régimen general los artículos 6 a 10 de la Ley 2573 de 2026. Las obligaciones de denuncia, suspensión prolongada del cobro, espera de decisión penal y demás efectos de esos artículos solo se modelarán cuando su vigencia general resulte aplicable al caso."
                    )
                    section["numbered"] = numbered
                    break
            spec["sections"] = sections
            spec["law2573_transition_standard"] = TRANSITION_STANDARD
            spec["law2573_ruleset_verified_at"] = RULESET_VERIFIED_AT
            spec["law2573_specific_protocol_review_status"] = calculation.get("law2573_specific_protocol_review_status")
            spec["law2573_human_review_required"] = bool(calculation.get("law2573_human_review_required"))
        finalized.append(spec)
    return finalized


def install_m33_3_habeas_law2573_guard(core_module: ModuleType) -> bool:
    current = getattr(core_module, "habeas_data_calc", None)
    if current is None:
        return False
    if getattr(current, "_legalaiz_m33_3_law2573_guard", False):
        return True

    @wraps(current)
    def wrapped(answers: dict):
        calculation = current(answers)
        return enforce_law2573_transition(answers, calculation)

    wrapped._legalaiz_m33_3_law2573_guard = True
    wrapped._legalaiz_original = current
    setattr(core_module, "habeas_data_calc", wrapped)
    return True


__all__ = [
    "LAW_GENERAL_EFFECTIVE",
    "LAW_PROMULGATION",
    "RULESET_VERIFIED_AT",
    "SPECIFIC_PROTOCOL_REVIEW_LIMITATION",
    "SPECIFIC_PROTOCOL_REVIEW_STATUS",
    "TRANSITION_STANDARD",
    "enforce_law2573_transition",
    "finalize_law2573_transition",
    "install_m33_3_habeas_law2573_guard",
]
