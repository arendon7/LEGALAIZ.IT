from __future__ import annotations

"""Fuentes jurídicas estructuradas M33.4 para CO-TR-002.

El paquete separa procedimiento contravencional, fotodetección, responsabilidad
personal, deberes propios del propietario, notificación, caducidad, prescripción,
revocatoria directa y registros. Ninguna fuente convierte por sí sola una falla de
notificación, la titularidad del vehículo o una consulta registral en nulidad,
responsabilidad o inexigibilidad automática.
"""

from datetime import date
from typing import Any

from legalai_platform import traffic_official_domains as _traffic_official_domains  # noqa: F401
from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


TRAFFIC_SOURCE_RECORDS = {
    "CO-CP29-TRANSITO": {
        "title": "Constitución Política, artículo 29",
        "locator": "Debido proceso aplicable a toda actuación judicial y administrativa",
        "authority": "SUIN-Juriscol · Constitución Política",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Constitucion%2F1687988+",
        "observed_status": "vigente; debido proceso, defensa, contradicción y presunción de inocencia",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["debido proceso", "defensa", "contradicción", "presunción de inocencia"],
        "source_kind": "constitution",
        "applicability": "base transversal de toda actuación sancionatoria de tránsito",
    },
    "CO-LEY769-PROC-TRANSITO": {
        "title": "Ley 769 de 2002 — Código Nacional de Tránsito Terrestre",
        "locator": "Artículos 129, 135 y 136 — comparendo, audiencia, prueba, vinculación y reducción de sanción",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1826223",
        "observed_status": "Código vigente con modificaciones incorporadas; el comparendo no equivale por sí mismo a sanción y la actuación debe respetar defensa y contradicción",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["comparendo", "audiencia", "pruebas", "vinculación", "reducción"],
        "source_kind": "traffic_code",
        "applicability": "diagnóstico, audiencia, reclamación y reconstrucción del expediente",
    },
    "CO-LEY769-159-161": {
        "title": "Ley 769 de 2002 — artículos 159 y 161",
        "locator": "Prescripción de sanciones y caducidad de la acción contravencional; artículo 161 modificado por Ley 1843 de 2017",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1826223",
        "observed_status": "vigente con modificaciones: caducidad de un año para decidir imposición; prescripción de tres años e interrupción con notificación del mandamiento de pago",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["caducidad", "prescripción", "mandamiento de pago", "cobro coactivo"],
        "source_kind": "traffic_limitation_rules",
        "applicability": "solo con fechas y actos verificables; caducidad y prescripción son controles distintos",
    },
    "CO-LEY769-RUNT-SIMIT": {
        "title": "Ley 769 de 2002 — RUNT y SIMIT",
        "locator": "Artículos 8 y 10 — registros nacionales e información sobre multas y sanciones",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1826223",
        "observed_status": "régimen vigente con modificaciones; RUNT y SIMIT son sistemas de información y no sustituyen el acto administrativo fuente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["RUNT", "SIMIT", "registros", "acto fuente"],
        "source_kind": "traffic_registry_regime",
        "applicability": "corrección y cotejo registral; la anotación no prueba por sí sola validez, ejecutoria o exigibilidad",
    },
    "CO-LEY1843-FOTODETECCION": {
        "title": "Ley 1843 de 2017",
        "locator": "Artículos 7, 8, 9 y 11 — notificación de fotodetección, remisión al procedimiento y caducidad",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30032605",
        "observed_status": "vigente con afectación jurisprudencial: el parágrafo 1 del artículo 8 sobre solidaridad automática del propietario fue declarado inexequible por C-038/2020",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["fotodetección", "notificación", "envío", "comparecencia", "caducidad"],
        "source_kind": "photodetection_statute",
        "applicability": "fotodetección individual; una notificación irregular no produce automáticamente nulidad universal",
    },
    "CO-MT-VALIDACION-10D": {
        "title": "Orientación oficial del Ministerio de Transporte sobre fotomultas",
        "locator": "FAQ oficial: validación del comparendo dentro de diez días y envío dentro de tres días hábiles posteriores; comparecencia dentro de once días",
        "authority": "Ministerio de Transporte",
        "official_url": "https://mintransporte.gov.co/publicaciones/5774/faq-sobre-fotomultas/",
        "observed_status": "orientación oficial publicada por MinTransporte que sintetiza el régimen de validación y notificación; no sustituye el texto normativo aplicable al caso",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["validación", "fotodetección", "envío", "comparecencia"],
        "source_kind": "official_operational_guidance",
        "applicability": "control operativo de cronología; debe cotejarse con la regulación vigente y la fecha concreta del hecho",
    },
    "CO-LEY2161-ART10-PROPIETARIO": {
        "title": "Ley 2161 de 2021, artículo 10",
        "locator": "Medidas antievasión — deberes propios del propietario del vehículo",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30043511",
        "observed_status": "vigente; impone deberes propios del propietario y exige procedimiento administrativo contravencional para sancionar su incumplimiento",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["propietario", "deber de cuidado", "velocidad", "semáforo", "SOAT", "RTM"],
        "source_kind": "owner_duties_statute",
        "applicability": "no transforma la titularidad en responsabilidad objetiva por la conducta de un tercero",
    },
    "CO-D998-2022-PROPIETARIO": {
        "title": "Decreto 998 de 2022",
        "locator": "Artículo 1 — corrección del yerro de redacción del artículo 10 de la Ley 2161 de 2021",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Decretos%2F30054162",
        "observed_status": "vigente e incorporado a la Ley 2161 de 2021; aclara el texto de los deberes del propietario",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["propietario", "corrección normativa", "procedimiento contravencional"],
        "source_kind": "corrective_decree",
        "applicability": "debe leerse conjuntamente con Ley 2161 art. 10 y C-321/2022",
    },
    "CO-CC-C038-2020": {
        "title": "Corte Constitucional, Sentencia C-038 de 2020",
        "locator": "Inexequibilidad del parágrafo 1 del artículo 8 de la Ley 1843 de 2017",
        "authority": "Corte Constitucional de Colombia",
        "official_url": "https://www.corteconstitucional.gov.co/relatoria/2020/C-038-20.htm",
        "observed_status": "vigente como precedente de constitucionalidad: proscribe responsabilidad solidaria automática del propietario por infracciones detectadas tecnológicamente sin imputación personal y culpabilidad",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["responsabilidad personal", "fotodetección", "propietario", "culpabilidad"],
        "source_kind": "constitutional_precedent",
        "applicability": "impide inferir responsabilidad por la mera titularidad del vehículo",
    },
    "CO-CC-C321-2022": {
        "title": "Corte Constitucional, Sentencia C-321 de 2022",
        "locator": "Exequibilidad condicionada/parcial del artículo 10 de la Ley 2161 de 2021",
        "authority": "Corte Constitucional de Colombia",
        "official_url": "https://www.corteconstitucional.gov.co/Relatoria/2022/C-321-22.htm",
        "observed_status": "vigente como precedente de constitucionalidad: los deberes propios del propietario no generan sanción automática y, para los supuestos condicionados, requieren prueba de incumplimiento culposo dentro del proceso contravencional",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["propietario", "responsabilidad subjetiva", "culpabilidad", "debido proceso"],
        "source_kind": "constitutional_precedent",
        "applicability": "complementa C-038/2020; no autoriza imputar al propietario la conducta ajena del conductor",
    },
    "CO-CPACA-NOTIF-67-69": {
        "title": "Ley 1437 de 2011 — CPACA",
        "locator": "Artículos 67 a 69 — notificación personal, electrónica y por aviso",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F1680117",
        "observed_status": "vigente con modificaciones; reglas generales de notificación administrativa aplicables por remisión cuando corresponda",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["notificación", "aviso", "acto administrativo", "debido proceso"],
        "source_kind": "administrative_procedure",
        "applicability": "aplicación supletoria/remitida; debe distinguir notificación del comparendo de notificación de actos posteriores",
    },
    "CO-CPACA-REVOC-93-96": {
        "title": "Ley 1437 de 2011 — CPACA",
        "locator": "Artículos 93 a 96 — causales, improcedencia, oportunidad, efectos y trámite de revocación directa",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F1680117",
        "observed_status": "vigente con modificaciones; la revocación directa no sustituye recursos ni revive automáticamente términos judiciales",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["revocación directa", "acto administrativo", "recursos", "medio de control"],
        "source_kind": "administrative_revocation",
        "applicability": "supletiva y condicionada en tránsito conforme al artículo 161; requiere individualizar el acto fuente",
    },
    "CO-LEY1755-PETICION-TRANSITO": {
        "title": "Ley 1755 de 2015",
        "locator": "Artículos 14 y 21 — términos para información/documentos, demás peticiones y traslado por falta de competencia",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30043679",
        "observed_status": "vigente; documentos/información tienen término especial de diez días y la falta de competencia exige traslado oportuno",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["derecho de petición", "expediente", "documentos", "traslado"],
        "source_kind": "petition_statute",
        "applicability": "petición de expediente y actuaciones de corrección/seguimiento cuando no exista regla especial",
    },
}

for source_id, record in TRAFFIC_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record
validate_registry()

TRAFFIC_KINDS = {
    "traffic_diagnostic",
    "traffic_record_request",
    "traffic_notification_claim",
    "traffic_hearing_request",
    "traffic_revocation_request",
    "traffic_registry_correction",
    "traffic_evidence_matrix",
    "traffic_filing_guide",
}

_OWNER_KINDS = {"traffic_diagnostic", "traffic_hearing_request", "traffic_evidence_matrix", "traffic_filing_guide"}
_NOTIFICATION_KINDS = {"traffic_diagnostic", "traffic_record_request", "traffic_notification_claim", "traffic_evidence_matrix", "traffic_filing_guide"}
_LIMITATION_KINDS = {"traffic_diagnostic", "traffic_revocation_request", "traffic_evidence_matrix", "traffic_filing_guide"}


def _parsed_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _verified_act(value: Any) -> bool:
    text = str(value or "").strip().casefold()
    if not text:
        return False
    return not any(token in text for token in ("por obtener", "por verificar", "pendiente", "no confirmado", "aparentemente"))


def traffic_source_ids(kind: str, answers: dict, result: dict) -> list[str]:
    if kind not in TRAFFIC_KINDS:
        return []
    ids = ["CO-CP29-TRANSITO", "CO-LEY769-PROC-TRANSITO"]
    if kind in _NOTIFICATION_KINDS:
        ids.extend(["CO-LEY1843-FOTODETECCION", "CO-MT-VALIDACION-10D", "CO-CPACA-NOTIF-67-69"])
    if kind in _OWNER_KINDS:
        ids.extend(["CO-LEY2161-ART10-PROPIETARIO", "CO-D998-2022-PROPIETARIO", "CO-CC-C038-2020", "CO-CC-C321-2022"])
    if kind in _LIMITATION_KINDS:
        ids.append("CO-LEY769-159-161")
    if kind == "traffic_revocation_request":
        ids.extend(["CO-LEY1843-FOTODETECCION", "CO-CPACA-REVOC-93-96"])
    if kind == "traffic_registry_correction":
        ids.extend(["CO-LEY769-RUNT-SIMIT", "CO-LEY1755-PETICION-TRANSITO"])
    if kind == "traffic_record_request":
        ids.extend(["CO-LEY1755-PETICION-TRANSITO", "CO-LEY769-RUNT-SIMIT"])
    return list(dict.fromkeys(ids))


def traffic_case_control(answers: dict) -> dict:
    detection = _parsed_date(answers.get("detection_date"))
    validation = _parsed_date(answers.get("validation_date"))
    mailing = _parsed_date(answers.get("mailing_date"))
    delivered = _parsed_date(answers.get("delivery_or_return_date"))
    actual_knowledge = _parsed_date(answers.get("actual_knowledge_date"))
    sanction = _parsed_date(answers.get("sanction_date"))
    enforceability = _parsed_date(answers.get("enforceability_date"))
    payment_order = _parsed_date(answers.get("payment_order_date"))
    official_address = str(answers.get("official_address") or "").strip().casefold()
    used_address = str(answers.get("used_address") or "").strip().casefold()
    address_status = (
        "apparent_difference_requires_historical_runt_and_postal_proof"
        if official_address and used_address and official_address != used_address
        else "no_structured_difference_proven"
    )
    revocation_ready = _verified_act(answers.get("sanction_resolution")) and sanction is not None
    registry_ready = _verified_act(answers.get("registry_source_act"))
    return {
        "timeline": {
            "detection_date": detection.isoformat() if detection else None,
            "validation_date": validation.isoformat() if validation else None,
            "mailing_date": mailing.isoformat() if mailing else None,
            "delivery_or_return_date": delivered.isoformat() if delivered else None,
            "actual_knowledge_date": actual_knowledge.isoformat() if actual_knowledge else None,
            "sanction_date": sanction.isoformat() if sanction else None,
            "enforceability_date": enforceability.isoformat() if enforceability else None,
            "payment_order_date": payment_order.isoformat() if payment_order else None,
        },
        "notification_status": "evidence_reconstruction_required",
        "address_status": address_status,
        "late_actual_knowledge_effect": "does_not_automatically_equal_valid_notification",
        "owner_liability": {
            "automatic_from_title": False,
            "third_party_conduct_imputed_from_title": False,
            "own_statutory_duty_requires_culpability_proof": True,
            "administrative_contraventional_process_required": True,
        },
        "caducity_control": "verified_detection_and_sanction_act_dates_required" if not (detection and sanction) else "dates_available_human_legal_evaluation_required",
        "prescription_control": "verified_payment_order_notice_required" if not payment_order else "payment_order_date_available_notice_and_interruptive_effect_must_be_verified",
        "revocation_ready": revocation_ready,
        "registry_correction_ready": registry_ready,
        "legal_effect": "no_automatic_nullity_liability_prescription_revocation_or_registry_correction",
    }


__all__ = [
    "TRAFFIC_KINDS",
    "TRAFFIC_SOURCE_RECORDS",
    "traffic_case_control",
    "traffic_source_ids",
]
