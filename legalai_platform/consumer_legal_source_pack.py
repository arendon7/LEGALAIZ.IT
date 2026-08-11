from __future__ import annotations

"""Paquete normativo estructurado M33.4 para CO-CD-003.

El paquete separa la base común de protección al consumidor de las fuentes
específicas de cada remedio. No convierte un remedio en otro ni presume la
aplicación de un régimen general cuando exista regulación sectorial especial.
"""

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


CONSUMER_SOURCE_RECORDS = {
    "CO-CONST-ART78": {
        "title": "Constitución Política de Colombia, artículo 78",
        "locator": "Protección de consumidores, calidad de bienes y servicios e información al público",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1687988",
        "observed_status": "texto constitucional vigente consultado",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["protección al consumidor", "calidad", "información", "responsabilidad"],
        "source_kind": "constitution",
        "applicability": "base constitucional común",
    },
    "CO-LEY1480-CONSUMER": {
        "title": "Ley 1480 de 2011 — Estatuto del Consumidor",
        "locator": "Garantía legal, retracto, comercio electrónico, reversión del pago y reclamación directa, con modificaciones vigentes",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=1681955",
        "observed_status": "vigente con modificaciones incorporadas; los artículos 47 y 50 reflejan cambios de la Ley 2439 de 2024 y el artículo 47 registra el condicionamiento de la Sentencia C-192 de 2026",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["garantía", "retracto", "reversión", "comercio electrónico", "reclamación directa"],
        "source_kind": "statute",
        "applicability": "régimen general, salvo regulación sectorial especial prevalente",
    },
    "CO-D735-GARANTIA": {
        "title": "Decreto 735 de 2013",
        "locator": "Efectividad de la garantía legal; reparación, reposición y devolución del dinero",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Decretos%2F1156200",
        "observed_status": "vigente; reglamenta los artículos 7 y siguientes de la Ley 1480 de 2011 y conserva reglas generales de 30 días hábiles para reparación, 10 para reposición y 15 para devolución en sus respectivos supuestos",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["garantía legal", "reparación", "reposición", "devolución", "reclamación directa"],
        "source_kind": "regulation",
        "applicability": "garantía legal; verificar naturaleza del bien, hito inicial y regla especial",
    },
    "CO-D1074-CONSUMER": {
        "title": "Decreto 1074 de 2015 — Decreto Único Reglamentario del Sector Comercio, Industria y Turismo",
        "locator": "Compilación reglamentaria vigente en materia de protección al consumidor; incluye el Capítulo 51 sobre reversión del pago",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30019935",
        "observed_status": "decreto único vigente; debe leerse con sus adiciones y modificaciones, incluida la incorporación del Capítulo 51 por el Decreto 587 de 2016",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["protección al consumidor", "reversión del pago", "débito periódico"],
        "source_kind": "compiled_regulation",
        "applicability": "según mecanismo y ausencia de régimen sectorial especial",
    },
    "CO-D587-REVERSAL": {
        "title": "Decreto 587 de 2016",
        "locator": "Adiciona al Decreto 1074 de 2015 el Capítulo 51: reversión del pago, débitos automáticos y pagos periódicos",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30020299",
        "observed_status": "vigente; reglamenta el artículo 51 de la Ley 1480 para pagos electrónicos y contiene reglas especiales para revocación de débitos y cargos posteriores",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["reversión del pago", "pago electrónico", "débito automático", "cargo posterior", "pagos periódicos"],
        "source_kind": "regulation",
        "applicability": "operaciones comprendidas por el capítulo y sin regulación especial de reversión",
    },
    "CO-LEY2439-ECOMMERCE": {
        "title": "Ley 2439 de 2024",
        "locator": "Modifica la Ley 1480 de 2011 y crea medidas de protección para consumidores de comercio electrónico",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30054269",
        "observed_status": "vigente; modifica, entre otros, los artículos 47 y 50 de la Ley 1480 y regula reembolsos de 15 días calendario en los supuestos previstos",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["comercio electrónico", "retracto", "reembolso", "entrega", "indisponibilidad"],
        "source_kind": "amending_statute",
        "applicability": "según modalidad de contratación y regla concreta modificada",
    },
    "CO-CC-C192-2026": {
        "title": "Corte Constitucional, Sentencia C-192 de 2026",
        "locator": "Condicionamiento del artículo 3 de la Ley 2439 de 2024 sobre plazo de devolución derivada del retracto",
        "authority": "Corte Constitucional · registro oficial SUIN-Juriscol",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?id=30056645",
        "observed_status": "sentencia de constitucionalidad del 24/06/2026; declaró exequible condicionada la expresión demandada para que el máximo de 15 días calendario aplique uniformemente a las modalidades del artículo 47 de la Ley 1480",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["retracto", "reembolso", "igualdad", "control de constitucionalidad"],
        "source_kind": "constitutional_decision",
        "applicability": "condicionamiento vinculante del artículo 3 de la Ley 2439 de 2024",
    },
}


for source_id, record in CONSUMER_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record

validate_registry()


CONSUMER_MECHANISM_KINDS = {
    "warranty_claim",
    "withdrawal_notice",
    "payment_reversal_request",
    "recurring_debit_revocation",
    "ecommerce_non_delivery_termination",
}

CONSUMER_SUPPORT_KINDS = {
    "consumer_mechanism_diagnosis",
    "consumer_evidence_matrix",
    "consumer_deadline_calendar",
}

CONSUMER_KINDS = CONSUMER_MECHANISM_KINDS | CONSUMER_SUPPORT_KINDS

_COMMON = ["CO-CONST-ART78", "CO-LEY1480-CONSUMER"]
_MECHANISM_SOURCES = {
    "warranty_claim": ["CO-D735-GARANTIA"],
    "withdrawal_notice": ["CO-LEY2439-ECOMMERCE", "CO-CC-C192-2026"],
    "payment_reversal_request": ["CO-D1074-CONSUMER", "CO-D587-REVERSAL"],
    "recurring_debit_revocation": ["CO-D1074-CONSUMER", "CO-D587-REVERSAL"],
    "ecommerce_non_delivery_termination": ["CO-LEY2439-ECOMMERCE"],
}


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def consumer_source_ids(kind: str, selected_kind: str | None = None) -> list[str]:
    """Selecciona fuentes por función documental y remedio realmente activado."""
    if kind not in CONSUMER_KINDS:
        return []
    if kind == "consumer_mechanism_diagnosis":
        values = list(_COMMON)
        for mechanism in sorted(CONSUMER_MECHANISM_KINDS):
            values.extend(_MECHANISM_SOURCES[mechanism])
        return _dedupe(values)

    mechanism = kind if kind in CONSUMER_MECHANISM_KINDS else selected_kind
    values = list(_COMMON)
    if mechanism in _MECHANISM_SOURCES:
        values.extend(_MECHANISM_SOURCES[mechanism])
    if kind == "consumer_evidence_matrix":
        values.extend(["CO-LEY1581-DATOS", "CO-LEY527-MENSAJES"])
    return _dedupe(values)


__all__ = [
    "CONSUMER_KINDS",
    "CONSUMER_MECHANISM_KINDS",
    "CONSUMER_SOURCE_RECORDS",
    "consumer_source_ids",
]
