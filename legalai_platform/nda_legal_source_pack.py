from __future__ import annotations

"""Paquete normativo M33.4 para CO-EM-004.

No asigna una fuente jurídica autónoma a la IA por el solo hecho de usarse. Los
controles de IA se conectan con las normas efectivamente aplicables a confidencialidad,
secretos empresariales, propiedad intelectual, datos y contratación electrónica.
"""

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


NDA_SOURCE_RECORDS = {
    "CAN-DEC486-SECRETS": {
        "title": "Decisión 486 de 2000 de la Comisión de la Comunidad Andina",
        "locator": "Título XVI, Capítulo II, artículos 260 a 265 sobre secretos empresariales",
        "authority": "Comisión de la Comunidad Andina · Secretaría General de la Comunidad Andina",
        "official_url": "https://www.comunidadandina.org/StaticFiles/DocOf/DEC486.pdf",
        "observed_status": "régimen común de propiedad industrial vigente; la CAN identifica la Decisión 486 y sus modificatorias como marco de secretos industriales y competencia desleal vinculada",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["secreto empresarial", "medidas razonables", "deber de reserva", "uso y divulgación", "competencia desleal"],
    },
    "CO-LEY256-ART16": {
        "title": "Ley 256 de 1996, artículo 16",
        "locator": "Violación de secretos como acto de competencia desleal",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes%2F1656946",
        "observed_status": "vigente; artículo 16 consultado en la fuente oficial",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["competencia desleal", "violación de secretos", "divulgación", "explotación no autorizada"],
    },
}


for source_id, record in NDA_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record

validate_registry()


NDA_BASE_SOURCE_IDS = [
    "CAN-DEC486-SECRETS",
    "CO-LEY256-ART16",
    "CO-LEY23-ART183",
    "CO-LEY1955-ART181",
    "CAN-DEC351-DA",
    "CO-LEY527-ARTS6-7-14",
]


def nda_source_ids(*, personal_data: bool) -> list[str]:
    values = list(NDA_BASE_SOURCE_IDS)
    if personal_data:
        values.extend(["CO-LEY1581-2012", "CO-D1074-DATOS"])
    return values


__all__ = ["NDA_BASE_SOURCE_IDS", "NDA_SOURCE_RECORDS", "nda_source_ids"]
