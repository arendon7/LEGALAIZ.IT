from __future__ import annotations

"""Paquete normativo estructurado M33.4 para CO-CD-001.

Las fuentes se registran con su estado observado al 10 de agosto de 2026. La
Ley 2573 de 2026 se modela expresamente como norma en transición: antes del 20 de
noviembre de 2026 no se anticipa su régimen general y solo se reconocen como de
vigencia inmediata los parágrafos 1 y 2 del artículo 5, conforme a su artículo 13.
"""

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    OFFICIAL_DOMAINS,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


# La SIC es fuente oficial primaria para sus propios actos y decisiones.
OFFICIAL_DOMAINS.update({"sedeelectronica.sic.gov.co", "www.sic.gov.co", "sic.gov.co"})


HABEAS_SOURCE_RECORDS = {
    "CO-CONST-ART15": {
        "title": "Constitución Política de Colombia, artículo 15",
        "locator": "Derechos a la intimidad, buen nombre y hábeas data; conocer, actualizar y rectificar información",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1687988",
        "observed_status": "texto constitucional vigente consultado; la modificación transitoria de 2003 fue declarada inexequible y el texto vigente preserva el derecho de hábeas data",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["hábeas data", "intimidad", "buen nombre", "actualización", "rectificación"],
        "source_kind": "constitution",
        "applicability": "base constitucional",
    },
    "CO-LEY1266-ARTS12-13-16": {
        "title": "Ley Estatutaria 1266 de 2008",
        "locator": "Artículos 12, 13 y 16: comunicación previa, permanencia y trámite de consultas/reclamos",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1676616",
        "observed_status": "vigente con modificaciones incorporadas; el artículo 16 refleja adiciones de la Ley 2157 de 2021 y la modificación futura de la Ley 2573 de 2026 se controla temporalmente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["comunicación previa", "permanencia", "consulta", "reclamo", "silencio", "suplantación"],
        "source_kind": "statute",
        "applicability": "régimen especial financiero, crediticio, comercial y de servicios",
    },
    "CO-LEY2157-HABEAS": {
        "title": "Ley Estatutaria 2157 de 2021",
        "locator": "Reforma de la Ley 1266 de 2008; entre otros, artículos 3, 6 y 7 sobre permanencia, comunicación previa y suplantación/silencio",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F30042420",
        "observed_status": "vigente; el artículo 7 continúa aplicable hasta el 19/11/2026 y aparece programado para modificación por el artículo 7 de la Ley 2573 de 2026 desde el 20/11/2026",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["permanencia", "comunicación previa", "calidad de información", "suplantación", "silencio"],
        "source_kind": "amending_statute",
        "applicability": "vigente al corte con transición futura identificada",
    },
    "CO-LEY2573-TRANSITION-2026": {
        "title": "Ley Estatutaria 2573 de 2026",
        "locator": "Artículo 13 y parágrafos 1 y 2 del artículo 5; vigencia general diferida al 20 de noviembre de 2026",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30056451",
        "observed_status": "promulgada el 20/05/2026; vigencia general diferida al 20/11/2026; únicamente los parágrafos 1 y 2 del artículo 5 rigen desde la promulgación durante la ventana transitoria",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["suplantación de identidad", "transición normativa", "reporte negativo", "seguridad", "vigencia temporal"],
        "source_kind": "transitional_statute",
        "applicability": "partial_immediate_only_before_2026-11-20",
    },
    "CO-SIC-RES28170-2022": {
        "title": "Resolución SIC 28170 de 2022",
        "locator": "Modifica el Capítulo Primero del Título V de la Circular Única; instrucciones sobre calidad, suplantación, actualización y atención de reclamos",
        "authority": "Superintendencia de Industria y Comercio",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30051550",
        "observed_status": "acto administrativo publicado el 11/05/2022; fuente oficial consultada identifica su entrada en vigencia y actualización de instrucciones posteriores a la Ley 2157 de 2021",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["Circular Única SIC", "calidad", "suplantación", "actualización", "reclamos"],
        "source_kind": "administrative_instruction",
        "applicability": "sujeta a competencia SIC y al supuesto material del expediente",
    },
    "CO-SIC-RES107492-2025": {
        "title": "Resolución SIC 107492 del 17 de diciembre de 2025",
        "locator": "Decisión administrativa sobre el alcance del silencio del numeral 8 del numeral II del artículo 16 de la Ley 1266 de 2008",
        "authority": "Superintendencia de Industria y Comercio · Delegatura para la Protección de Datos Personales",
        "official_url": "https://sedeelectronica.sic.gov.co/transparencia/normativa/resolucion-107492-del-17-de-diciembre-de-2025",
        "observed_status": "decisión administrativa oficial divulgada por la SIC el 26/02/2026; restringe el efecto analizado del silencio al supuesto de protección frente a suplantación en el caso decidido",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["silencio", "suplantación", "reclamo", "alcance administrativo"],
        "source_kind": "administrative_decision",
        "applicability": "criterio administrativo no equivalente a regla general autónoma ni precedente judicial vinculante",
    },
}


for source_id, record in HABEAS_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record

validate_registry()


HABEAS_BASE_SOURCE_IDS = [
    "CO-CONST-ART15",
    "CO-LEY1266-ARTS12-13-16",
    "CO-LEY2157-HABEAS",
    "CO-LEY1581-2012",
    "CO-D1074-DATOS",
]

HABEAS_KINDS = {
    "habeas_consultation",
    "habeas_claim",
    "habeas_reiteration",
    "identity_theft_protocol",
    "habeas_authority_escalation",
    "habeas_evidence_matrix",
    "habeas_deadline_calendar",
}

_LAW2573_KINDS = HABEAS_KINDS - {"habeas_evidence_matrix"}
_RES28170_KINDS = HABEAS_KINDS - {"habeas_deadline_calendar"}
_RES107492_KINDS = {"habeas_reiteration", "identity_theft_protocol"}


def habeas_source_ids(kind: str) -> list[str]:
    """Selecciona solo fuentes materialmente relacionadas con cada pieza."""
    if kind not in HABEAS_KINDS:
        return []
    values = list(HABEAS_BASE_SOURCE_IDS)
    if kind in _LAW2573_KINDS:
        values.append("CO-LEY2573-TRANSITION-2026")
    if kind in _RES28170_KINDS:
        values.append("CO-SIC-RES28170-2022")
    if kind in _RES107492_KINDS:
        values.append("CO-SIC-RES107492-2025")
    return values


__all__ = [
    "HABEAS_BASE_SOURCE_IDS",
    "HABEAS_KINDS",
    "HABEAS_SOURCE_RECORDS",
    "habeas_source_ids",
]
