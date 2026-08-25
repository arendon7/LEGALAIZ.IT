#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8765"


def main() -> int:
    with urllib.request.urlopen(f"{BASE}/api/products/CO-CD-001", timeout=5) as response:
        payload = json.load(response)

    interview = payload.get("interview") or {}
    questions = interview.get("questions") or []
    by_id: dict[str, list[dict]] = {}
    for question in questions:
        by_id.setdefault(str(question.get("id") or ""), []).append(question)

    expected_singletons = [
        "prior_claim_identity_theft",
        "prior_communication_sent",
        "prior_communication_channel",
        "prior_communication_destination_verified",
        "prior_communication_alternative_channel_agreed",
        "prior_communication_message_consultable",
        "prior_communication_content_sufficient",
        "prior_communication_first_date",
        "identity_theft_correction_requested",
        "identity_theft_security_noncompliance_verified",
        "identity_theft_security_noncompliance_support",
        "identity_theft_security_instrument_authority",
        "identity_theft_security_instrument_reference",
        "identity_theft_security_requirement_tested",
        "identity_theft_security_instrument_applicable",
    ]
    for field in expected_singletons:
        matches = by_id.get(field) or []
        if len(matches) != 1:
            raise SystemExit(f"RC0/M33.3: se esperaba una {field} y se encontraron {len(matches)}")

    identity = by_id["prior_claim_identity_theft"][0]
    if identity.get("show_if") != {"field": "prior_claim", "equals": "Sí"}:
        raise SystemExit(f"RC0/M33.3: condición de suplantación inesperada: {identity.get('show_if')!r}")
    if identity.get("options") != ["Sí", "No", "No sé"]:
        raise SystemExit(f"RC0/M33.3: opciones de suplantación inesperadas: {identity.get('options')!r}")

    sent = by_id["prior_communication_sent"][0]
    if sent.get("options") != ["Sí", "No", "No sé"]:
        raise SystemExit("RC0/M33.3: catálogo de envío de comunicación previa cambió")
    for field in [
        "prior_communication_channel",
        "prior_communication_destination_verified",
        "prior_communication_alternative_channel_agreed",
        "prior_communication_message_consultable",
        "prior_communication_content_sufficient",
    ]:
        if by_id[field][0].get("show_if") != {"field": "prior_communication_sent", "equals": "Sí"}:
            raise SystemExit(f"RC0/M33.3: condición inesperada en {field}")
    if by_id["prior_communication_first_date"][0].get("show_if") != {
        "field": "small_obligation_two_notices",
        "equals": "Sí",
    }:
        raise SystemExit("RC0/M33.3: primera fecha de pequeña cuantía perdió la regla de dos avisos")

    if by_id["identity_theft_correction_requested"][0].get("show_if") != {
        "field": "identity_theft",
        "equals": "Sí",
    }:
        raise SystemExit("RC0/M33.3: solicitud de corrección Ley 2573 perdió condición de suplantación")
    if by_id["identity_theft_security_noncompliance_verified"][0].get("show_if") != {
        "field": "identity_theft",
        "equals": "Sí",
    }:
        raise SystemExit("RC0/M33.3: verificación de seguridad perdió condición de suplantación")
    for field in [
        "identity_theft_security_noncompliance_support",
        "identity_theft_security_instrument_authority",
        "identity_theft_security_instrument_reference",
        "identity_theft_security_requirement_tested",
        "identity_theft_security_instrument_applicable",
    ]:
        if by_id[field][0].get("show_if") != {
            "field": "identity_theft_security_noncompliance_verified",
            "equals": "Sí",
        }:
            raise SystemExit(f"RC0/M33.3: {field} perdió dependencia del incumplimiento verificado")

    if by_id["identity_theft_security_noncompliance_support"][0].get("options") != [
        "Completo",
        "Parcial",
        "No",
        "No sé",
    ]:
        raise SystemExit("RC0/M33.3: catálogo de soporte de seguridad Ley 2573 cambió")
    authority_options = by_id["identity_theft_security_instrument_authority"][0].get("options") or []
    for authority in ("Superintendencia Financiera de Colombia", "Superintendencia de Industria y Comercio"):
        if authority not in authority_options:
            raise SystemExit(f"RC0/M33.3: falta autoridad oficial en catálogo: {authority}")

    send_date = by_id.get("prior_communication_date") or []
    if len(send_date) != 1 or "envío" not in str(send_date[0].get("label") or "").casefold():
        raise SystemExit("RC0/M33.3: prior_communication_date dejó de presentarse como fecha de envío")
    if interview.get("interview_standard") != "M33.3":
        raise SystemExit(f"RC0/M33.3: estándar runtime no activo: {interview.get('interview_standard')!r}")
    if len(questions) < 67:
        raise SystemExit(f"RC0/M33.3: entrevista CO-CD-001 incompleta; solo {len(questions)} preguntas activas")

    print(
        "V1-RC0 M33.3 runtime PASS · "
        f"CO-CD-001 questions={len(questions)} identity_theft=single prior_communication=guarded "
        "law2573=guarded official_security_authorities=present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
