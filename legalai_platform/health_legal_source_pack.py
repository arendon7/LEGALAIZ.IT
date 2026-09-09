from __future__ import annotations

"""Paquete de fuentes jurídicas M33.4 para CO-SA-001.

La selección se realiza por función documental. Los términos sectoriales de PQR
se tratan como instrucciones operativas de Supersalud y no como sustitutos de la
atención clínica urgente. La historia clínica conserva fuentes propias de reserva,
custodia e interoperabilidad. Tutela y función jurisdiccional de Supersalud se
mantienen como rutas distintas y condicionales.
"""

from typing import Any

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


HEALTH_SOURCE_RECORDS = {
    "CO-LEY1751-SALUD": {
        "title": "Ley Estatutaria 1751 de 2015",
        "locator": "Artículos 2, 6, 8 y 10, entre otros — derecho fundamental a la salud, continuidad, oportunidad, integralidad y urgencias",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30019746",
        "observed_status": "vigente; reconoce la salud como derecho fundamental autónomo, continuidad, oportunidad, integralidad, atención de urgencias y acceso a historia clínica",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["salud", "continuidad", "oportunidad", "integralidad", "urgencias"],
        "source_kind": "statutory_health_regime",
        "applicability": "base transversal de las siete piezas CO-SA-001",
    },
    "CO-LEY1755-PETICION-SALUD": {
        "title": "Ley 1755 de 2015",
        "locator": "Artículos 14 y 20 — términos de petición y atención prioritaria",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30043679",
        "observed_status": "vigente; término general sujeto a norma especial y atención prioritaria/inmediata cuando existe riesgo de perjuicio irremediable o peligro inminente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["derecho de petición", "términos", "atención prioritaria", "peligro inminente"],
        "source_kind": "petition_statute",
        "applicability": "peticiones, reiteraciones y calendario general subsidiario",
    },
    "CO-SNS-CIRC10-2023-PQR": {
        "title": "Circular Externa 2023151000000010-5 de 2023",
        "locator": "Términos máximos para reclamos en salud por clasificación de riesgo: simple 72 h, priorizado 48 h, vital 24 h",
        "authority": "Superintendencia Nacional de Salud",
        "official_url": "https://www.supersalud.gov.co/es-co/atencion-ciudadano/preguntas-frecuentes",
        "observed_status": "Supersalud continúa publicando como aplicables los máximos de 72, 48 y 24 horas; su doctrina institucional precisa que son horas corridas",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["PQR salud", "riesgo simple", "riesgo priorizado", "riesgo vital", "horas corridas"],
        "source_kind": "sector_operational_instruction",
        "applicability": "reclamos ante EAPB según clasificación real de riesgo; máximo que no autoriza demorar una atención más urgente",
    },
    "CO-RES1995-HISTORIA": {
        "title": "Resolución 1995 de 1999",
        "locator": "Normas para el manejo de la historia clínica",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Resolucion%2F30035652",
        "observed_status": "vigente con modificaciones; historia clínica privada, obligatoria y sometida a reserva",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["historia clínica", "reserva", "custodia", "integridad"],
        "source_kind": "health_record_regulation",
        "applicability": "solicitud, custodia, reserva y trazabilidad de historia clínica",
    },
    "CO-RES839-2017-HISTORIA": {
        "title": "Resolución 839 de 2017",
        "locator": "Modifica la Resolución 1995 de 1999; custodia, retención, conservación y disposición final",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Resolucion%2F30040120",
        "observed_status": "vigente; modifica el régimen de manejo y conservación de historias clínicas y remite a protección de datos personales",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["historia clínica", "retención", "conservación", "datos personales"],
        "source_kind": "health_record_regulation",
        "applicability": "historia clínica y matriz probatoria con información clínica",
    },
    "CO-LEY2015-HCE": {
        "title": "Ley 2015 de 2020",
        "locator": "Historia Clínica Electrónica Interoperable; artículos 1 a 10",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F30038770",
        "observed_status": "vigente; regula interoperabilidad, titularidad, acceso, gratuidad, seguridad e integridad de la historia clínica electrónica",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["historia clínica electrónica", "interoperabilidad", "titularidad", "gratuidad", "seguridad"],
        "source_kind": "electronic_health_record_statute",
        "applicability": "cuando se solicita o preserva historia clínica en soporte electrónico/interoperable",
    },
    "CO-LEY1949-ART6-SNS": {
        "title": "Ley 1949 de 2019, artículo 6",
        "locator": "Modifica el artículo 41 de la Ley 1122 de 2007 — función jurisdiccional de la Superintendencia Nacional de Salud",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30036084",
        "observed_status": "vigente; delimita asuntos sometidos a función jurisdiccional de Supersalud y exige actuación a petición de parte",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["Supersalud", "función jurisdiccional", "competencia", "medidas cautelares"],
        "source_kind": "health_jurisdiction_statute",
        "applicability": "solo para distinguir PQRD administrativa de eventual función jurisdiccional",
    },
    "CO-CP86-TUTELA": {
        "title": "Constitución Política, artículo 86",
        "locator": "Acción de tutela para protección inmediata de derechos fundamentales",
        "authority": "SUIN-Juriscol · Constitución Política",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Constitucion%2F1687988+",
        "observed_status": "vigente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["tutela", "derechos fundamentales", "protección inmediata"],
        "source_kind": "constitution",
        "applicability": "diagnóstico y escalamiento cuando debe evaluarse tutela; no implica procedencia automática",
    },
    "CO-D2591-TUTELA": {
        "title": "Decreto 2591 de 1991",
        "locator": "Reglamentación de la acción de tutela del artículo 86 de la Constitución",
        "authority": "SUIN-Juriscol · Presidencia de la República",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Decretos%2F1470723",
        "observed_status": "vigente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["tutela", "subsidiariedad", "protección inmediata", "procedimiento"],
        "source_kind": "constitutional_decree",
        "applicability": "diagnóstico/escalamiento; requiere análisis individual de procedencia",
    },
    "CO-CC-T008-2025-SALUD": {
        "title": "Corte Constitucional, Sentencia T-008 de 2025",
        "locator": "Derecho a la salud; barreras administrativas, acompañamiento, seguimiento, continuidad e integralidad",
        "authority": "Corte Constitucional de Colombia",
        "official_url": "https://www.corteconstitucional.gov.co/relatoria/2025/t-008-25.htm",
        "observed_status": "precedente de revisión consultado; la EPS debe evitar barreras administrativas y asegurar acompañamiento y seguimiento en el acceso a prestaciones requeridas",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["salud", "barreras administrativas", "seguimiento", "continuidad", "integralidad"],
        "source_kind": "constitutional_case_law",
        "applicability": "referencia jurisprudencial para continuidad y eliminación de barreras; no sustituye análisis del caso concreto",
    },
    "CO-CC-T125-2026-SALUD": {
        "title": "Corte Constitucional, Sentencia T-125 de 2026",
        "locator": "Suministro oportuno de medicamentos y responsabilidad de la EPS frente al usuario",
        "authority": "Corte Constitucional de Colombia",
        "official_url": "https://www.corteconstitucional.gov.co/relatoria/2026/T-125-26.htm",
        "observed_status": "precedente de revisión 2026 consultado; reprocha dilaciones administrativas y reitera el deber de garantizar oportunamente prestaciones requeridas",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["medicamentos", "EPS", "oportunidad", "gestor farmacéutico", "barreras administrativas"],
        "source_kind": "constitutional_case_law",
        "applicability": "referencia jurisprudencial cuando la barrera involucra entrega o continuidad de medicamentos",
    },
}


for source_id, record in HEALTH_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record

validate_registry()


HEALTH_KINDS = {
    "health_diagnostic", "health_petition", "health_reiteration",
    "health_supersalud", "health_history_request", "health_evidence",
    "health_calendar",
}


def _yes(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"sí", "si", "yes", "true", "1"}


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def health_source_ids(kind: str, answers: dict, result: dict) -> list[str]:
    if kind not in HEALTH_KINDS:
        return []

    values = ["CO-LEY1751-SALUD"]

    if kind in {"health_diagnostic", "health_petition", "health_reiteration", "health_supersalud", "health_calendar"}:
        values.extend(["CO-LEY1755-PETICION-SALUD", "CO-SNS-CIRC10-2023-PQR"])

    if kind in {"health_diagnostic", "health_supersalud"}:
        values.append("CO-LEY1949-ART6-SNS")

    if kind == "health_diagnostic":
        values.extend(["CO-CP86-TUTELA", "CO-D2591-TUTELA", "CO-CC-T008-2025-SALUD"])

    request_text = " ".join(str(answers.get(key) or "") for key in ("request_mode", "service_requested", "facts_detail")).casefold()
    medication_case = any(token in request_text for token in ("medicamento", "fármaco", "farmaco", "farmacéut", "farmaceut"))
    if medication_case and kind in {"health_diagnostic", "health_petition", "health_reiteration"}:
        values.append("CO-CC-T125-2026-SALUD")

    if kind in {"health_history_request", "health_evidence"}:
        values.extend(["CO-RES1995-HISTORIA", "CO-RES839-2017-HISTORIA", "CO-LEY1581-2012"])
    if kind == "health_history_request":
        values.append("CO-LEY2015-HCE")

    if _yes(answers.get("active_tutela")) or _yes(answers.get("active_contempt")):
        if kind in {"health_diagnostic", "health_petition", "health_reiteration", "health_calendar"}:
            values.extend(["CO-CP86-TUTELA", "CO-D2591-TUTELA"])

    return _dedupe(values)


__all__ = ["HEALTH_KINDS", "HEALTH_SOURCE_RECORDS", "health_source_ids"]
