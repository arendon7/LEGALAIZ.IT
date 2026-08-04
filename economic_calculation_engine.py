from __future__ import annotations

"""Motor económico transversal para documentos jurídicos de LegalAIZ.it.

No decide procedencia jurídica. Calcula y reconcilia cifras con Decimal,
conserva trazabilidad de parámetros y bloquea inconsistencias materiales.
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable

CENT = Decimal("0.01")
HUNDRED = Decimal("100")

MODALITY_PARAMETER_KEYS = {
    "Consumo y ordinario": ("ibc_consumption_ordinary_ea", "maximum_consumption_ordinary_ea"),
    "Consumo bajo monto": ("ibc_consumption_low_amount_ea", "maximum_consumption_low_amount_ea"),
    "Productivo mayor monto": ("ibc_productive_major_ea", "maximum_productive_major_ea"),
    "Productivo rural": ("ibc_productive_rural_ea", "maximum_productive_rural_ea"),
    "Productivo urbano": ("ibc_productive_urban_ea", "maximum_productive_urban_ea"),
    "Popular productivo rural": ("ibc_popular_productive_rural_ea", "maximum_popular_productive_rural_ea"),
    "Popular productivo urbano": ("ibc_popular_productive_urban_ea", "maximum_popular_productive_urban_ea"),
}


def decimal_value(value, *, minimum: Decimal | None = None) -> Decimal:
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, bool):
        raise InvalidOperation("boolean is not numeric")
    elif isinstance(value, (int, float)):
        result = Decimal(str(value))
    else:
        raw = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
        for token in ("COP", "cop", "$", "PESOS", "pesos", "M/CTE", "m/cte"):
            raw = raw.replace(token, "")
        if not raw:
            result = Decimal("0")
        elif "," in raw and "." in raw:
            result = Decimal(raw.replace(".", "").replace(",", ".")) if raw.rfind(",") > raw.rfind(".") else Decimal(raw.replace(",", ""))
        elif "," in raw:
            head, tail = raw.rsplit(",", 1)
            result = Decimal(head.replace(".", "") + "." + tail) if len(tail) <= 2 else Decimal(raw.replace(",", ""))
        elif raw.count(".") > 1:
            result = Decimal(raw.replace(".", ""))
        elif raw.count(".") == 1 and len(raw.rsplit(".", 1)[1]) == 3:
            result = Decimal(raw.replace(".", ""))
        else:
            result = Decimal(raw)
    if minimum is not None and result < minimum:
        return minimum
    return result


def money(value) -> Decimal:
    return decimal_value(value, minimum=Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


def effective_annual_rate(rate, period: str | None) -> Decimal:
    """Convierte la tasa informada a E.A.; devuelve porcentaje, no fracción."""
    r = decimal_value(rate, minimum=Decimal("0"))
    if not r:
        return Decimal("0")
    period = str(period or "").strip()
    if period == "Efectiva anual":
        return r.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if period == "Mensual vencida":
        ea = (Decimal("1") + r / HUNDRED) ** 12 - Decimal("1")
        return (ea * HUNDRED).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if period == "Nominal anual mes vencido":
        monthly = r / Decimal("12") / HUNDRED
        ea = (Decimal("1") + monthly) ** 12 - Decimal("1")
        return (ea * HUNDRED).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return Decimal("0")


def modality_rates(parameters: dict, modality: str | None) -> dict:
    keys = MODALITY_PARAMETER_KEYS.get(str(modality or ""))
    if not keys:
        return {"modality": modality or "No definida", "ibc_ea": Decimal("0"), "maximum_ea": Decimal("0"), "configured": False}
    ibc_key, maximum_key = keys
    return {
        "modality": modality,
        "ibc_ea": decimal_value(parameters.get(ibc_key), minimum=Decimal("0")),
        "maximum_ea": decimal_value(parameters.get(maximum_key), minimum=Decimal("0")),
        "configured": bool(parameters.get(maximum_key)),
        "ibc_parameter": ibc_key,
        "maximum_parameter": maximum_key,
    }


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def schedule_date(first: date, index: int, frequency: str | None) -> date | None:
    frequency = str(frequency or "")
    if index == 0:
        return first
    if frequency == "Semanal":
        return first + timedelta(days=7 * index)
    if frequency == "Quincenal":
        return first + timedelta(days=15 * index)
    if frequency == "Mensual":
        return add_months(first, index)
    if frequency == "Bimestral":
        return add_months(first, index * 2)
    if frequency == "Única":
        return first if index == 0 else None
    return None


def build_payment_schedule(total, installments, first_payment_date, frequency) -> dict:
    total_value = money(total)
    try:
        count = max(int(decimal_value(installments)), 1)
    except (ValueError, InvalidOperation):
        count = 1
    first = None
    if first_payment_date:
        try:
            first = date.fromisoformat(str(first_payment_date))
        except ValueError:
            first = None
    base = (total_value / Decimal(count)).quantize(CENT, rounding=ROUND_HALF_UP)
    rows = []
    accumulated = Decimal("0")
    for index in range(count):
        amount = base if index < count - 1 else (total_value - accumulated).quantize(CENT, rounding=ROUND_HALF_UP)
        due = schedule_date(first, index, frequency) if first else None
        accumulated += amount
        rows.append({
            "number": index + 1,
            "due_date": due.isoformat() if due else None,
            "amount": float(amount),
            "status": "Pendiente",
        })
    warnings = []
    if frequency == "Única" and count != 1:
        warnings.append("La periodicidad única exige una sola cuota.")
    if frequency == "Otra" and count > 1:
        warnings.append("Las fechas posteriores deben definirse expresamente porque la periodicidad es 'Otra'.")
    if not first:
        warnings.append("No fue posible construir fechas verificables para el cronograma.")
    return {
        "total": float(total_value),
        "installments": count,
        "frequency": frequency,
        "first_payment_date": first.isoformat() if first else None,
        "regular_installment": float(base),
        "last_installment": rows[-1]["amount"],
        "sum_installments": float(accumulated.quantize(CENT)),
        "rounding_adjustment": float((Decimal(str(rows[-1]["amount"])) - base).quantize(CENT)),
        "rows": rows,
        "warnings": warnings,
        "reconciled": accumulated.quantize(CENT) == total_value,
    }


def accrued_effective_interest(principal, annual_effective_percent, start_date, end_date) -> dict:
    capital = money(principal)
    rate = decimal_value(annual_effective_percent, minimum=Decimal("0"))
    try:
        start = date.fromisoformat(str(start_date))
        end = date.fromisoformat(str(end_date))
    except (TypeError, ValueError):
        return {"calculable": False, "days": 0, "interest": 0.0, "total": float(capital), "reason": "Fechas incompletas o inválidas."}
    if end < start:
        return {"calculable": False, "days": 0, "interest": 0.0, "total": float(capital), "reason": "La fecha final precede la inicial."}
    days = (end - start).days
    factor = (1.0 + float(rate / HUNDRED)) ** (days / 365.0) - 1.0
    interest = (capital * Decimal(str(factor))).quantize(CENT, rounding=ROUND_HALF_UP)
    return {
        "calculable": True,
        "days": days,
        "interest": float(interest),
        "total": float((capital + interest).quantize(CENT)),
        "annual_effective_rate": float(rate),
        "method": "equivalencia efectiva diaria sobre base 365",
    }


def reconcile_amounts(*, principal, payments, charges, reported_balance, agreement_total=None, tolerance=Decimal("1.00")) -> dict:
    capital = money(principal)
    paid = money(payments)
    extras = money(charges)
    reported = money(reported_balance)
    expected_principal = max(capital - paid, Decimal("0"))
    explained = (expected_principal + extras).quantize(CENT)
    difference = (reported - explained).quantize(CENT)
    result = {
        "principal": float(capital),
        "payments": float(paid),
        "charges": float(extras),
        "expected_principal_balance": float(expected_principal),
        "explained_balance": float(explained),
        "reported_balance": float(reported),
        "balance_difference": float(difference),
        "balance_reconciled": abs(difference) <= tolerance,
    }
    if agreement_total is not None:
        agreement = money(agreement_total)
        agreement_difference = (agreement - reported).quantize(CENT)
        result.update({
            "agreement_total": float(agreement),
            "agreement_vs_reported_difference": float(agreement_difference),
            "agreement_reconciled": abs(agreement_difference) <= tolerance,
        })
    return result


def reconcile_line_items(line_items: Iterable[dict], *, gross_total, prior_total, net_total, tolerance=Decimal("0.01")) -> dict:
    gross = sum((money(item.get("gross")) for item in line_items), Decimal("0"))
    prior = sum((money(item.get("prior_paid")) for item in line_items), Decimal("0"))
    net = sum((money(item.get("net")) for item in line_items), Decimal("0"))
    expected = {"gross": money(gross_total), "prior": money(prior_total), "net": money(net_total)}
    calculated = {"gross": gross.quantize(CENT), "prior": prior.quantize(CENT), "net": net.quantize(CENT)}
    deltas = {key: (expected[key] - calculated[key]).quantize(CENT) for key in expected}
    return {
        "valid": all(abs(value) <= tolerance for value in deltas.values()) and abs((gross - prior) - net) <= tolerance,
        "calculated": {key: float(value) for key, value in calculated.items()},
        "declared": {key: float(value) for key, value in expected.items()},
        "deltas": {key: float(value) for key, value in deltas.items()},
        "gross_minus_prior_equals_net": abs((gross - prior) - net) <= tolerance,
    }
