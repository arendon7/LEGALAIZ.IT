from __future__ import annotations

"""Activación acotada de la Fábrica Documental M33.0.

La primera oleada sustituye únicamente las fábricas principales de cuatro contratos
mediante nuevas versiones. La segunda oleada conserva el motor genérico histórico
`expanded_documents.document_specs`, pero reemplaza su símbolo activo por un wrapper
M33.0 que reutiliza cálculos, condiciones y bloqueos y solo recompone las salidas.

Los símbolos/API M32.x permanecen disponibles para no romper handlers e integraciones.
Las clases y funciones históricas siguen importables para regresión y comparación.
"""

from types import ModuleType
from typing import Any

from co_ar_001_document_factory_v251 import CoAr001DocumentFactoryV251
from co_ar_001_governance_v251 import CoAr001GovernanceV251
from co_em_003_document_factory_v245 import CoEm003DocumentFactoryV245
from co_em_003_governance_v245 import CoEm003GovernanceV245
from co_em_004_document_factory_v248 import CoEm004DocumentFactoryV248
from co_em_004_governance_v248 import CoEm004GovernanceV248
from co_la_002_document_factory_v240 import CoLa002DocumentFactoryV240
from co_la_002_governance_v240 import CoLa002GovernanceV240
from m33_procedural_composition import document_specs_m33


_ACTIVE = False
_CACHE: dict[str, Any] = {}


def _build(registry: ModuleType) -> dict[str, Any]:
    root = registry.core.ROOT

    services_factory = CoEm003DocumentFactoryV245(root, registry.COEM003_V244)
    services_governance = CoEm003GovernanceV245(root, services_factory)

    nda_factory = CoEm004DocumentFactoryV248(root, registry.COEM004_V247)
    nda_governance = CoEm004GovernanceV248(root, nda_factory)

    lease_factory = CoAr001DocumentFactoryV251(root, registry.COAR001_V250)
    lease_governance = CoAr001GovernanceV251(root, lease_factory)

    employment_factory = CoLa002DocumentFactoryV240(root, registry.COLA002_V236)
    employment_governance = CoLa002GovernanceV240(root, employment_factory)

    return {
        # Símbolos nuevos explícitos.
        "COEM003_FACTORY_V245": services_factory,
        "COEM003_GOVERNANCE_V245": services_governance,
        "COEM004_FACTORY_V248": nda_factory,
        "COEM004_GOVERNANCE_V248": nda_governance,
        "COAR001_FACTORY_V251": lease_factory,
        "COAR001_GOVERNANCE_V251": lease_governance,
        "COLA002_FACTORY_V240": employment_factory,
        "COLA002_GOVERNANCE_M33": employment_governance,
        "DOCUMENT_SPECS_M33": document_specs_m33,

        # Alias de compatibilidad consumidos por endpoints M32.x. No se cambia la API.
        "COEM003_FACTORY_V244": services_factory,
        "COEM003_GOVERNANCE_V244": services_governance,
        "COEM004_FACTORY_V247": nda_factory,
        "COEM004_GOVERNANCE_V247": nda_governance,
        "COAR001_FACTORY_V250": lease_factory,
        "COAR001_GOVERNANCE_V250": lease_governance,
        "COLA002_FACTORY_V239": employment_factory,
        "COLA002_GOVERNANCE_V240": employment_governance,
    }


def activate_m33_contract_factories(
    registry: ModuleType,
    application_services: ModuleType | None = None,
    target_namespace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Activa una única vez las capas M33.0 y propaga alias compatibles.

    Además de las cuatro fábricas contractuales, rebindea `core.document_specs` al
    wrapper M33.0. El wrapper devuelve exactamente la salida histórica para productos
    fuera de la segunda oleada y para expedientes rojos; de este modo el cambio es
    incremental y no altera motores sustantivos ni reglas de riesgo.
    """
    global _ACTIVE, _CACHE
    if not _ACTIVE:
        _CACHE = _build(registry)
        _ACTIVE = True

    # `generate_documents()` y las rutas históricas de core resuelven este global en
    # tiempo de ejecución. No se reescribe core_v11.py ni expanded_documents.py.
    registry.core.document_specs = document_specs_m33
    if application_services is not None:
        setattr(application_services, "document_specs", document_specs_m33)
    if target_namespace is not None:
        target_namespace["document_specs"] = document_specs_m33

    for name, value in _CACHE.items():
        setattr(registry, name, value)
        if application_services is not None:
            setattr(application_services, name, value)
        if target_namespace is not None:
            target_namespace[name] = value

    return dict(_CACHE)
