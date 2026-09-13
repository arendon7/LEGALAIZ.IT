from __future__ import annotations

"""Calendario nacional colombiano para cómputos jurídicos en días hábiles.

La utilidad es determinística y no depende de servicios externos en tiempo de
 ejecución. Su alcance deliberadamente limitado es el calendario nacional de
 descanso obligatorio: fines de semana y festivos nacionales modelados por el
 ruleset jurídico verificado. No modela vacaciones judiciales, cierres de despacho,
 suspensiones procesales, días cívicos, festivos territoriales ni calendarios
 especiales de una autoridad.

Ruleset verificado: 2026-08-10.
Base principal: Ley 51 de 1983 y Ley 2578 de 2026, art. 6.
"""

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from functools import lru_cache

RULESET_VERIFIED_AT = "2026-08-10"
CALENDAR_SCOPE = "colombia_national_holidays"
COUNTING_RULE = "start_exclusive"
CALENDAR_BASIS = (
    "Ley 51 de 1983",
    "Ley 2578 de 2026, artículo 6",
)
CALENDAR_LIMITATIONS = (
    "La fecha efectiva de recepción, radicación o conocimiento debe verificarse con su soporte.",
    "No se incluyen vacaciones judiciales ni cierres extraordinarios de despachos o autoridades.",
    "No se incluyen suspensiones procesales, interrupciones de términos ni reglas sectoriales especiales.",
    "No se incluyen festivos territoriales, días cívicos u otros cierres locales no incorporados al calendario nacional.",
    "Una reforma posterior a la fecha de verificación del ruleset exige revalidar el calendario antes de usarlo como fecha definitiva.",
)


@dataclass(frozen=True)
class Holiday:
    date: date
    name: str
    basis: str
    nominal_date: date
    shifted_to_monday: bool = False

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["date"] = self.date.isoformat()
        payload["nominal_date"] = self.nominal_date.isoformat()
        return payload


@dataclass(frozen=True)
class BusinessDayResult:
    start_date: date
    business_days: int
    due_date: date
    skipped_weekend_days: int
    skipped_holidays: tuple[Holiday, ...]
    calendar_scope: str = CALENDAR_SCOPE
    calendar_ruleset_verified_at: str = RULESET_VERIFIED_AT
    counting_rule: str = COUNTING_RULE
    holiday_calendar_applied: bool = True
    calendar_basis: tuple[str, ...] = CALENDAR_BASIS
    limitations: tuple[str, ...] = CALENDAR_LIMITATIONS

    def to_dict(self) -> dict:
        return {
            "start_date": self.start_date.isoformat(),
            "business_days": self.business_days,
            "due_date": self.due_date.isoformat(),
            "skipped_weekend_days": self.skipped_weekend_days,
            "skipped_holidays": [holiday.to_dict() for holiday in self.skipped_holidays],
            "calendar_scope": self.calendar_scope,
            "calendar_ruleset_verified_at": self.calendar_ruleset_verified_at,
            "counting_rule": self.counting_rule,
            "holiday_calendar_applied": self.holiday_calendar_applied,
            "calendar_basis": list(self.calendar_basis),
            "limitations": list(self.limitations),
        }


_FIXED_HOLIDAYS = (
    (1, 1, "Año Nuevo", "Ley 51 de 1983"),
    (5, 1, "Día del Trabajo", "Ley 51 de 1983"),
    (7, 20, "Día de la Independencia", "Ley 51 de 1983"),
    (8, 7, "Batalla de Boyacá", "Ley 51 de 1983"),
    (12, 8, "Inmaculada Concepción", "Ley 51 de 1983"),
    (12, 25, "Navidad", "Ley 51 de 1983"),
)

_SHIFT_TO_MONDAY_HOLIDAYS = (
    (1, 6, "Epifanía del Señor", "Ley 51 de 1983"),
    (3, 19, "San José", "Ley 51 de 1983"),
    (6, 29, "San Pedro y San Pablo", "Ley 51 de 1983"),
    (8, 15, "Asunción de la Virgen", "Ley 51 de 1983"),
    (10, 12, "Día de la Raza", "Ley 51 de 1983"),
    (11, 1, "Todos los Santos", "Ley 51 de 1983"),
    (11, 11, "Independencia de Cartagena", "Ley 51 de 1983"),
)

_ADDITIONAL_NATIONAL_HOLIDAYS = (
    {
        "name": "Nuestra Señora del Rosario de Chiquinquirá",
        "month": 7,
        "day": 9,
        "effective_from": date(2026, 6, 2),
        "shift_to_monday": True,
        "basis": "Ley 2578 de 2026, artículo 6",
    },
)


def _next_monday(value: date) -> date:
    """Traslada una festividad al lunes siguiente cuando no cae en lunes."""
    if value.weekday() == 0:
        return value
    days = (7 - value.weekday()) % 7
    return value + timedelta(days=days or 7)


def _gregorian_easter(year: int) -> date:
    """Meeus/Jones/Butcher para Pascua gregoriana."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _holiday(nominal: date, name: str, basis: str, *, shift_to_monday: bool = False) -> Holiday:
    observed = _next_monday(nominal) if shift_to_monday else nominal
    return Holiday(
        date=observed,
        name=name,
        basis=basis,
        nominal_date=nominal,
        shifted_to_monday=observed != nominal,
    )


@lru_cache(maxsize=64)
def colombian_national_holidays(year: int) -> dict[date, Holiday]:
    """Retorna festivos nacionales observados bajo el ruleset vigente verificado.

    La función puede calcular años futuros, pero el consumidor debe conservar y
    revisar ``RULESET_VERIFIED_AT`` porque una reforma posterior puede modificar el
    resultado. Para períodos históricos anteriores al régimen actual también debe
    verificarse la norma temporalmente aplicable.
    """
    if not isinstance(year, int) or year < 1900 or year > 2199:
        raise ValueError("El año del calendario debe estar entre 1900 y 2199.")

    holidays: list[Holiday] = []
    for month, day, name, basis in _FIXED_HOLIDAYS:
        holidays.append(_holiday(date(year, month, day), name, basis))
    for month, day, name, basis in _SHIFT_TO_MONDAY_HOLIDAYS:
        holidays.append(_holiday(date(year, month, day), name, basis, shift_to_monday=True))

    easter = _gregorian_easter(year)
    holidays.extend(
        (
            _holiday(easter - timedelta(days=3), "Jueves Santo", "Ley 51 de 1983"),
            _holiday(easter - timedelta(days=2), "Viernes Santo", "Ley 51 de 1983"),
            _holiday(easter + timedelta(days=39), "Ascensión del Señor", "Ley 51 de 1983", shift_to_monday=True),
            _holiday(easter + timedelta(days=60), "Corpus Christi", "Ley 51 de 1983", shift_to_monday=True),
            _holiday(easter + timedelta(days=68), "Sagrado Corazón de Jesús", "Ley 51 de 1983", shift_to_monday=True),
        )
    )

    for rule in _ADDITIONAL_NATIONAL_HOLIDAYS:
        nominal = date(year, int(rule["month"]), int(rule["day"]))
        if nominal < rule["effective_from"]:
            continue
        holidays.append(
            _holiday(
                nominal,
                str(rule["name"]),
                str(rule["basis"]),
                shift_to_monday=bool(rule.get("shift_to_monday")),
            )
        )

    # Si dos reglas coincidieran en una misma fecha observada, conservar ambos
    # fundamentos en un único registro legible y determinístico.
    merged: dict[date, Holiday] = {}
    for holiday in sorted(holidays, key=lambda item: (item.date, item.name)):
        existing = merged.get(holiday.date)
        if existing is None:
            merged[holiday.date] = holiday
            continue
        merged[holiday.date] = Holiday(
            date=holiday.date,
            name=f"{existing.name} / {holiday.name}",
            basis=f"{existing.basis}; {holiday.basis}",
            nominal_date=min(existing.nominal_date, holiday.nominal_date),
            shifted_to_monday=existing.shifted_to_monday or holiday.shifted_to_monday,
        )
    return merged


def calculate_colombian_business_days(start: date, days: int) -> BusinessDayResult:
    """Suma días hábiles nacionales desde ``start`` con inicio excluido."""
    if not isinstance(start, date):
        raise TypeError("start debe ser datetime.date.")
    if isinstance(days, bool):
        raise TypeError("days debe ser un entero no negativo.")
    try:
        business_days = int(days)
    except (TypeError, ValueError) as exc:
        raise TypeError("days debe ser un entero no negativo.") from exc
    if business_days < 0:
        raise ValueError("days no puede ser negativo.")
    if business_days != days:
        raise ValueError("days debe ser un entero exacto.")
    if business_days == 0:
        return BusinessDayResult(
            start_date=start,
            business_days=0,
            due_date=start,
            skipped_weekend_days=0,
            skipped_holidays=(),
        )

    cursor = start
    added = 0
    skipped_weekends = 0
    skipped_holidays: list[Holiday] = []
    while added < business_days:
        cursor += timedelta(days=1)
        if cursor.weekday() >= 5:
            skipped_weekends += 1
            continue
        holiday = colombian_national_holidays(cursor.year).get(cursor)
        if holiday is not None:
            skipped_holidays.append(holiday)
            continue
        added += 1

    return BusinessDayResult(
        start_date=start,
        business_days=business_days,
        due_date=cursor,
        skipped_weekend_days=skipped_weekends,
        skipped_holidays=tuple(skipped_holidays),
    )


def add_colombian_business_days(start: date, days: int) -> date:
    return calculate_colombian_business_days(start, days).due_date


__all__ = [
    "BusinessDayResult",
    "Holiday",
    "CALENDAR_BASIS",
    "CALENDAR_LIMITATIONS",
    "CALENDAR_SCOPE",
    "COUNTING_RULE",
    "RULESET_VERIFIED_AT",
    "add_colombian_business_days",
    "calculate_colombian_business_days",
    "colombian_national_holidays",
]
