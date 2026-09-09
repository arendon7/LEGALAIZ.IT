from __future__ import annotations

"""Fuentes adicionales para la revisión sustantiva de CO-EM-003.

Se separa la definición laboral de persona natural (art. 22 CST) del régimen del
contratista/subcontratista (art. 34 CST, modificado por Ley 2466 de 2025). La carga
es idempotente y reutiliza el mismo registro M33.4.
"""

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


SERVICES_SUBSTANTIVE_SOURCE_RECORDS = {
    "CO-CST-ART22-2025": {
        "title": "Código Sustantivo del Trabajo, artículo 22",
        "locator": "Artículo 22; definición del contrato de trabajo y prestación personal por una persona natural",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Codigo%2F30019323",
        "observed_status": "texto vigente consultado; el trabajador que presta el servicio personal es persona natural",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["contrato de trabajo", "persona natural", "servicio personal", "subordinación"],
    },
    "CO-CST-ART34-2025": {
        "title": "Código Sustantivo del Trabajo, artículo 34",
        "locator": "Artículo 34, modificado por el artículo 44 de la Ley 2466 de 2025; contratistas, subcontratistas y solidaridad",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Codigo%2F30019323",
        "observed_status": "vigente; modificación de 2025 incorporada en el texto consultado",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": [
            "contratistas",
            "subcontratistas",
            "autonomía técnica y directiva",
            "trabajadores del contratista",
            "solidaridad laboral",
        ],
    },
}


for source_id, record in SERVICES_SUBSTANTIVE_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record

validate_registry()


SERVICES_SUBSTANTIVE_SOURCE_IDS = [
    "CO-CST-ART22-2025",
    "CO-CST-ART34-2025",
]


__all__ = ["SERVICES_SUBSTANTIVE_SOURCE_IDS", "SERVICES_SUBSTANTIVE_SOURCE_RECORDS"]
