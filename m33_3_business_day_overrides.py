from __future__ import annotations

"""Override runtime M33.3 para cómputos jurídicos en días hábiles nacionales.

Los motores históricos de salud, hábeas data y consumo llaman a ``_business_day_add``.
Esta capa sustituye únicamente ese primitivo por el calendario nacional auditado y
adjunta al cálculo la trazabilidad de cada suma ejecutada. No altera los términos
configurados ni convierte el resultado en un cómputo judicial universal.
"""

from contextvars import ContextVar
from functools import wraps
from types import ModuleType
from typing import Any

from legalai_platform.colombian_business_calendar import (
    CALENDAR_BASIS,
    CALENDAR_LIMITATIONS,
    CALENDAR_SCOPE,
    COUNTING_RULE,
    RULESET_VERIFIED_AT,
    calculate_colombian_business_days,
)

CALENDAR_ENGINE = "M33.3-colombia-national-business-days-v1"

_ACTIVE_AUDIT: ContextVar[list[dict] | None] = ContextVar("m33_3_business_day_audit", default=None)

_STALE_ASSUMPTION_TOKENS = (
    "no descuenta festivos",
    "no descuentan festivos",
    "excluye sábados y domingos, pero no festivos",
    "excluyen sábados y domingos, pero no descuentan festivos",
)


def _audited_business_day_add(start, days):
    if not start or days is None:
        return None
    result = calculate_colombian_business_days(start, days)
    audit = _ACTIVE_AUDIT.get()
    if audit is not None:
        payload = result.to_dict()
        payload["sequence"] = len(audit) + 1
        audit.append(payload)
    return result.due_date


def _clean_assumptions(values: Any) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        text = str(value)
        lowered = text.casefold()
        if any(token in lowered for token in _STALE_ASSUMPTION_TOKENS):
            continue
        cleaned.append(text)
    national_note = (
        "Los cómputos automáticos en días hábiles incorporan sábados, domingos y "
        "festivos nacionales del ruleset colombiano verificado; la fecha sigue "
        "sujeta a la recepción efectiva, cierres o suspensiones especiales, régimen "
        "sectorial y, cuando corresponda, calendario judicial."
    )
    if national_note not in cleaned:
        cleaned.insert(0, national_note)
    return cleaned


def _decorate_calculation(calculation: dict, audit: list[dict]) -> dict:
    calculation = calculation if isinstance(calculation, dict) else {}
    calculation["holiday_calendar_applied"] = bool(audit)
    calculation["deadline_is_preliminary"] = True
    calculation["business_day_calendar_engine"] = CALENDAR_ENGINE
    calculation["business_day_calendar_scope"] = CALENDAR_SCOPE
    calculation["business_day_calendar_verified_at"] = RULESET_VERIFIED_AT
    calculation["business_day_counting_rule"] = COUNTING_RULE
    calculation["business_day_calendar_basis"] = list(CALENDAR_BASIS)
    calculation["business_day_calendar_limitations"] = list(CALENDAR_LIMITATIONS)
    calculation["business_day_calculations"] = audit
    calculation["assumptions"] = _clean_assumptions(calculation.get("assumptions"))
    return calculation


def _wrap_calculator(core_module: ModuleType, name: str) -> bool:
    current = getattr(core_module, name, None)
    if current is None:
        return False
    if getattr(current, "_legalaiz_m33_3_business_calendar", False):
        return True

    @wraps(current)
    def wrapped(*args, **kwargs):
        audit: list[dict] = []
        token = _ACTIVE_AUDIT.set(audit)
        try:
            calculation = current(*args, **kwargs)
        finally:
            _ACTIVE_AUDIT.reset(token)
        return _decorate_calculation(calculation, audit)

    wrapped._legalaiz_m33_3_business_calendar = True
    wrapped._legalaiz_original = current
    setattr(core_module, name, wrapped)
    return True


def install_m33_3_business_day_overrides(core_module: ModuleType) -> dict:
    """Instala de forma idempotente el calendario nacional en motores compatibles."""
    current_adder = getattr(core_module, "_business_day_add", None)
    if not getattr(current_adder, "_legalaiz_m33_3_business_calendar", False):
        _audited_business_day_add._legalaiz_m33_3_business_calendar = True
        _audited_business_day_add._legalaiz_original = current_adder
        setattr(core_module, "_business_day_add", _audited_business_day_add)

    wrapped = {
        name: _wrap_calculator(core_module, name)
        for name in ("health_petition_calc", "habeas_data_calc", "consumer_protection_calc")
    }
    return {
        "installed": all(wrapped.values()),
        "calendar_engine": CALENDAR_ENGINE,
        "calendar_scope": CALENDAR_SCOPE,
        "ruleset_verified_at": RULESET_VERIFIED_AT,
        "calculators": wrapped,
    }


__all__ = [
    "CALENDAR_ENGINE",
    "install_m33_3_business_day_overrides",
]
