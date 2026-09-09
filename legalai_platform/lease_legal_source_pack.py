from __future__ import annotations

"""Paquete normativo M33.4 para CO-AR-001.

Registra únicamente fuentes oficiales verificadas y deja explícito cuándo una norma
histórica fue compilada en un decreto único vigente. La carga es idempotente.
"""

from legalai_platform.legal_source_registry import (
    LEGAL_SOURCE_REGISTRY,
    OFFICIAL_DOMAINS,
    REVIEW_DUE_ON,
    VERIFIED_ON,
    validate_registry,
)


OFFICIAL_DOMAINS.update({
    "www.corteconstitucional.gov.co",
    "corteconstitucional.gov.co",
})


LEASE_SOURCE_RECORDS = {
    "CO-LEY820-2003": {
        "title": "Ley 820 de 2003",
        "locator": "Régimen de arrendamiento de vivienda urbana; especialmente artículos 2 a 26",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://suin-juriscol.gov.co/clp/contenidos.dll/Leyes/1669010",
        "observed_status": "vigente; régimen especial de arrendamiento de vivienda urbana",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": [
            "arrendamiento vivienda urbana",
            "canon",
            "depósitos",
            "terminación",
            "restitución",
            "preaviso",
            "indemnización",
            "consignación",
            "caución",
            "derecho de retención",
        ],
    },
    "CO-D3130-2003": {
        "title": "Decreto 3130 de 2003",
        "locator": "Reglamentación del artículo 15 de la Ley 820 de 2003 sobre servicios públicos domiciliarios",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Decretos%2F1877380",
        "observed_status": "compilado en el Decreto 1077 de 2015; se conserva como antecedente normativo trazable",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["servicios públicos", "garantías", "solidaridad", "arrendamiento"],
    },
    "CO-D1077-ARRENDAMIENTO": {
        "title": "Decreto 1077 de 2015",
        "locator": "Decreto Único Reglamentario del Sector Vivienda, Ciudad y Territorio; compilación aplicable a vivienda urbana",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Decretos%2F30020036",
        "observed_status": "vigente; decreto único que compila reglamentación del sector vivienda",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["vivienda", "arrendamiento", "servicios públicos", "reglamentación compilada"],
    },
    "CO-LEY675-2001": {
        "title": "Ley 675 de 2001",
        "locator": "Régimen de propiedad horizontal",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://suin-juriscol.gov.co/viewDocument.asp?id=1665811",
        "observed_status": "vigente",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["propiedad horizontal", "bienes privados", "bienes comunes", "convivencia"],
    },
    "CO-CC-ARRENDAMIENTO": {
        "title": "Código Civil colombiano · Ley 84 de 1873",
        "locator": "Título XXVI del contrato de arrendamiento, artículo 1973 y siguientes, en cuanto resulte supletoriamente aplicable",
        "authority": "SUIN-Juriscol · Ministerio de Justicia y del Derecho",
        "official_url": "https://www.suin-juriscol.gov.co/viewdocument.asp?id=1827111",
        "observed_status": "Código Civil consultado; título de arrendamiento identificado en la fuente oficial",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["arrendamiento", "obligaciones del arrendador", "obligaciones del arrendatario", "supletoriedad"],
    },
    "CO-CC-C426-2023": {
        "title": "Corte Constitucional · Sentencia C-426 de 2023",
        "locator": "Exequibilidad del inciso 2 del numeral 8 del artículo 22 de la Ley 820 de 2003 por los cargos examinados",
        "authority": "Corte Constitucional de Colombia",
        "official_url": "https://www.corteconstitucional.gov.co/relatoria/2023/C-426-23.htm",
        "observed_status": "providencia oficial consultada; mantiene la caución examinada como constitucional por los cargos decididos",
        "verified_on": VERIFIED_ON.isoformat(),
        "review_due_on": REVIEW_DUE_ON.isoformat(),
        "topics": ["terminación por arrendador", "caución", "vivienda digna", "buena fe"],
    },
}


for source_id, record in LEASE_SOURCE_RECORDS.items():
    existing = LEGAL_SOURCE_REGISTRY.get(source_id)
    if existing is not None and existing != record:
        raise ValueError(f"M33.4: colisión de fuente jurídica {source_id}")
    LEGAL_SOURCE_REGISTRY[source_id] = record

validate_registry()


LEASE_SOURCE_IDS = [
    "CO-LEY820-2003",
    "CO-D3130-2003",
    "CO-D1077-ARRENDAMIENTO",
    "CO-LEY675-2001",
    "CO-CC-ARRENDAMIENTO",
    "CO-LEY1581-2012",
    "CO-D1074-DATOS",
    "CO-LEY527-ARTS6-7-14",
    "CO-CC-C426-2023",
]


__all__ = ["LEASE_SOURCE_IDS", "LEASE_SOURCE_RECORDS"]
