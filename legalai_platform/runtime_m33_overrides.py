from __future__ import annotations

"""Activación acotada de la Fábrica Documental M33.0/M33.3.

La primera oleada sustituye únicamente las fábricas principales de cuatro contratos
mediante nuevas versiones. Las oleadas segunda y tercera conservan los motores
históricos y utilizan un único compositor transversal M33.0 para presentar sus
salidas, sin cambiar la API consumida por los handlers M32.x.

M33.3 añade controles sustantivos acotados:
- calendario nacional colombiano auditable para cómputos compatibles en días hábiles;
- compuerta fail-closed para silencio favorable en hábeas data;
- compuerta probatoria para permanencia/caducidad del dato negativo;
- compuerta de comunicación previa que separa envío de recepción;
- compuerta temporal para Ley 2573 de 2026; y
- overlays condicionales de entrevista para suplantación, comunicación y transición normativa.

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
from m33_3_habeas_communication_guard import install_m33_3_habeas_communication_guard
from m33_3_habeas_communication_interview import install_m33_3_habeas_communication_interview
from m33_3_habeas_law2573_interview import install_m33_3_habeas_law2573_interview
from m33_3_habeas_law2573_transition import install_m33_3_habeas_law2573_guard
from m33_3_habeas_permanence_guard import install_m33_3_habeas_permanence_guard
from m33_3_habeas_silence_guard import install_m33_3_habeas_silence_guard
from m33_3_interview_overrides import install_m33_3_interview_overrides
from m33_wave3_runtime import document_specs_m33_all


_ACTIVE = False
_CACHE: dict[str, Any] = {}


def _sections_externalize_default_control(sections: Any) -> bool:
    return any(
        isinstance(section, dict) and bool(section.get("_suppress_default_control"))
        for section in (sections or [])
    )


def _install_m33_docx_presentation_policy(core_module: ModuleType):
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
    global _ACTIVE, _CACHE

    interview_status = install_m33_3_interview_overrides(registry.core)
    communication_interview_status = install_m33_3_habeas_communication_interview(registry.core)
    law2573_interview_status = install_m33_3_habeas_law2573_interview(registry.core)
    calendar_status = install_m33_3_business_day_overrides(registry.core)
    silence_guard_status = install_m33_3_habeas_silence_guard(registry.core)
    permanence_guard_status = install_m33_3_habeas_permanence_guard(registry.core)
    communication_guard_status = install_m33_3_habeas_communication_guard(registry.core)
    law2573_guard_status = install_m33_3_habeas_law2573_guard(registry.core)

    if not _ACTIVE:
        _CACHE = _build(registry)
        _ACTIVE = True
    _CACHE["M33_3_INTERVIEW_OVERLAY"] = interview_status
    _CACHE["M33_3_HABEAS_COMMUNICATION_INTERVIEW"] = communication_interview_status
    _CACHE["M33_3_HABEAS_LAW2573_INTERVIEW"] = law2573_interview_status
    _CACHE["M33_3_BUSINESS_CALENDAR"] = calendar_status
    _CACHE["M33_3_HABEAS_SILENCE_GUARD"] = {
        "installed": silence_guard_status,
        "scope": "identity_theft_claim_only",
        "authority": "Resolución SIC 107492 del 17 de diciembre de 2025",
    }
    _CACHE["M33_3_HABEAS_PERMANENCE_GUARD"] = {
        "installed": permanence_guard_status,
        "ruleset_verified_at": "2026-08-10",
        "basis": [
            "Ley 1266 de 2008, artículo 13",
            "Ley 2157 de 2021, artículo 3",
            "Resolución SIC 28170 de 2022, numeral 1.6",
        ],
    }
    _CACHE["M33_3_HABEAS_COMMUNICATION_GUARD"] = {
        "installed": communication_guard_status,
        "ruleset_verified_at": "2026-08-10",
        "basis": [
            "Ley 1266 de 2008, artículo 12",
            "Ley 1266 de 2008, artículo 13 parágrafo 2",
            "Ley 2157 de 2021",
            "Decreto 2952 de 2010, artículo 2",
        ],
        "principle": "send_not_receipt",
    }
    _CACHE["M33_3_HABEAS_LAW2573_GUARD"] = {
        "installed": law2573_guard_status,
        "ruleset_verified_at": "2026-08-10",
        "general_effective_date": "2026-11-20",
        "immediate_scope": ["artículo 5 parágrafo 1", "artículo 5 parágrafo 2"],
        "principle": "partial_immediate_only_before_general_effective_date",
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
