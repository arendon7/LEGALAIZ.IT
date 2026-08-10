from __future__ import annotations

"""Activación acotada de la Fábrica Documental M33.0/M33.3.

La primera oleada sustituye únicamente las fábricas principales de cuatro contratos
mediante nuevas versiones. Las oleadas segunda y tercera conservan los motores
históricos y utilizan un único compositor transversal M33.0 para presentar sus
salidas, sin cambiar la API consumida por los handlers M32.x.

M33.3 añade dos controles sustantivos acotados:
- un calendario nacional colombiano auditable para cómputos compatibles en días
  hábiles; y
- una compuerta fail-closed para no confundir respuesta tardía con efecto favorable
  del silencio en hábeas data cuando la controversia de suplantación no está
  individualizada.

Los símbolos/API históricos permanecen disponibles para comparación y regresión.
"""

from functools import wraps
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
from m33_3_business_day_overrides import install_m33_3_business_day_overrides
from m33_3_habeas_silence_guard import install_m33_3_habeas_silence_guard
from m33_wave3_runtime import document_specs_m33_all


_ACTIVE = False
_CACHE: dict[str, Any] = {}


def _sections_externalize_default_control(sections: Any) -> bool:
    return any(
        isinstance(section, dict) and bool(section.get("_suppress_default_control"))
        for section in (sections or [])
    )


def _install_m33_docx_presentation_policy(core_module: ModuleType):
    """Respeta la separación cliente/gobierno sin tocar la release gate instalada.

    `core_v11.generate_case_documents` conserva su API histórica y solo entrega las
    secciones al builder. Las composiciones M33.0 que externalizan controles dejan un
    marcador privado no renderizable; esta envoltura lo traduce al argumento ya
    soportado `append_default_control=False`. Los demás documentos mantienen el
    comportamiento previo.
    """
    current = getattr(core_module, "build_docx")
    if getattr(current, "_m33_presentation_policy", False):
        return current

    @wraps(current)
    def wrapped(*args, **kwargs):
        sections = kwargs.get("sections")
        if sections is None and len(args) >= 5:
            sections = args[4]
        if "append_default_control" not in kwargs and _sections_externalize_default_control(sections):
            kwargs["append_default_control"] = False
        return current(*args, **kwargs)

    wrapped._m33_presentation_policy = True
    wrapped._m33_wrapped_builder = current
    setattr(core_module, "build_docx", wrapped)
    return wrapped


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
        "COEM003_FACTORY_V245": services_factory,
        "COEM003_GOVERNANCE_V245": services_governance,
        "COEM004_FACTORY_V248": nda_factory,
        "COEM004_GOVERNANCE_V248": nda_governance,
        "COAR001_FACTORY_V251": lease_factory,
        "COAR001_GOVERNANCE_V251": lease_governance,
        "COLA002_FACTORY_V240": employment_factory,
        "COLA002_GOVERNANCE_M33": employment_governance,
        "DOCUMENT_SPECS_M33": document_specs_m33_all,

        # Alias de compatibilidad consumidos por endpoints M32.x.
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
    """Activa una única vez las oleadas M33 y propaga aliases compatibles."""
    global _ACTIVE, _CACHE

    # Se instala antes de exponer los servicios activos. `diagnose` conserva su API,
    # pero sus referencias globales quedan enlazadas a las compuertas auditadas M33.3.
    calendar_status = install_m33_3_business_day_overrides(registry.core)
    silence_guard_status = install_m33_3_habeas_silence_guard(registry.core)

    if not _ACTIVE:
        _CACHE = _build(registry)
        _ACTIVE = True
    _CACHE["M33_3_BUSINESS_CALENDAR"] = calendar_status
    _CACHE["M33_3_HABEAS_SILENCE_GUARD"] = {
        "installed": silence_guard_status,
        "scope": "identity_theft_claim_only",
        "authority": "Resolución SIC 107492 del 17 de diciembre de 2025",
    }

    wrapped_builder = _install_m33_docx_presentation_policy(registry.core)
    registry.core.document_specs = document_specs_m33_all
    if application_services is not None:
        setattr(application_services, "document_specs", document_specs_m33_all)
        if hasattr(application_services, "build_docx"):
            setattr(application_services, "build_docx", wrapped_builder)
    if target_namespace is not None:
        target_namespace["document_specs"] = document_specs_m33_all
        if "build_docx" in target_namespace:
            target_namespace["build_docx"] = wrapped_builder

    for name, value in _CACHE.items():
        setattr(registry, name, value)
        if application_services is not None:
            setattr(application_services, name, value)
        if target_namespace is not None:
            target_namespace[name] = value

    return dict(_CACHE)
