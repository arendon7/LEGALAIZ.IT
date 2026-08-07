from __future__ import annotations

"""Activación acotada de las fábricas contractuales M33.0.

`runtime_registry.py` conserva los símbolos históricos que consumen la aplicación y
las pruebas de regresión. Esta capa se aplica explícitamente desde `run.py` después
de importar `application_services`, crea nuevas instancias sobre carpetas versionadas
y rebindea únicamente los alias activos de la primera oleada contractual.

No se reutilizan carpetas de gobierno de versiones anteriores: cada fábrica M33.0
obtiene su propio `output_dir`, por lo que las aprobaciones deben producirse de nuevo
sobre los hashes M33.0.
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
        # El gobierno laboral ya se llamaba v2.40 en la línea anterior.
        "COLA002_GOVERNANCE_M33": employment_governance,

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
    """Activa una única vez las cuatro fábricas M33.0 y propaga los alias.

    La función es idempotente dentro del proceso. Los objetos de gobierno se crean
    sobre los nuevos directorios versionados; por diseño empiezan sin aprobaciones.
    """
    global _ACTIVE, _CACHE
    if not _ACTIVE:
        _CACHE = _build(registry)
        _ACTIVE = True

    for name, value in _CACHE.items():
        setattr(registry, name, value)
        if application_services is not None:
            setattr(application_services, name, value)
        if target_namespace is not None:
            target_namespace[name] = value

    return dict(_CACHE)
