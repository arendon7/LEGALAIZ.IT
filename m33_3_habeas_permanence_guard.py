from __future__ import annotations

"""Compuerta M33.3 para permanencia/caducidad del dato negativo CO-CD-001.

La fórmula histórica ya modela correctamente el artículo 13 de la Ley 1266 de 2008,
modificado por la Ley 2157 de 2021: doble de la mora con máximo de cuatro años tras
pago/extinción y ocho años desde la mora para obligación insoluta. Esta capa no
sustituye esa regla; hace explícitos sus presupuestos probatorios, corrige el control
de frontera en el día exacto de cumplimiento y separa la ruta aplicable según el
estado informado de la obligación.

Ruleset verificado: 2026-08-10.
Fuentes de control: Ley 1266/2008 art. 13, Ley 2157/2021 art. 3 y Resolución SIC
28170/2022 numeral 1.6. La Ley 2573/2026 no modifica el artículo 13 y su vigencia
general se encuentra diferida al 20-11-2026.
"""

from datetime import date
from functools import wraps
from types import ModuleType
from typing import Any

RULESET_VERIFIED_AT = "2026-08-10"
PERMANENCE_STANDARD = "M33.3-habeas-permanence-v1"
LEGAL_BASIS = (
    "Ley Estatutaria 1266 de 2008, artículo 13",
    "Ley Estatutaria 2157 de 2021, artículo 3",
    "Resolución SIC 28170 de 2022, numeral 1.6",
)

_PAID_STATES = {"Pagada", "Extinguida por otro modo"}
_UNPAID_STATE = "Vigente y en mora"
_DISPUTED_STATES = {"No reconocida por el titular", "Discutida"}


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        # 29 de febrero: el aniversario civil aplicable se materializa el 28 de
        # febrero del año no bisiesto, igual que el helper histórico del motor.
        return value.replace(month=2, day=28, year=value.year + years)


def _without_issue(issues: list, *ids: str) -> list:
    blocked = set(ids)
    return [
        issue for issue in (issues or [])
        if not (isinstance(issue, dict) and str(issue.get("id")) in blocked)
    ]


def _append_issue(issues: list, issue: dict) -> list:
    result = list(issues or [])
    if not any(isinstance(item, dict) and item.get("id") == issue.get("id") for item in result):
        result.append(issue)
    return result


def _append_assumption(values: list, text: str) -> list:
    result = list(values or [])
    if text not in result:
        result.append(text)
    return result


def _route(status: str) -> str:
    if status in _PAID_STATES:
        return "paid_or_extinguished"
    if status == _UNPAID_STATE:
        return "unpaid"
    if status in _DISPUTED_STATES:
        return "disputed_or_unrecognized"
    return "undetermined"


def enforce_habeas_permanence(answers: dict, calculation: dict) -> dict:
    calculation = calculation if isinstance(calculation, dict) else {}
    status = str(answers.get("obligation_status") or "").strip()
    route = _route(status)
    mora = _parse_date(answers.get("mora_start_date") or calculation.get("mora_start_date"))
    payment = _parse_date(answers.get("payment_or_extinction_date") or calculation.get("payment_or_extinction_date"))
    reference = date.fromisoformat(RULESET_VERIFIED_AT)

    issues = _without_issue(
        list(calculation.get("issues") or []),
        "CD1-CALC-12",
        "CD1-CALC-13",
        "CD1-M33-PERM-MORA-MISSING",
        "CD1-M33-PERM-EXTINCTION-MISSING",
        "CD1-M33-PERM-STATUS",
    )

    paid_expiry = None
    unpaid_expiry = None
    mora_days = None
    evidence_complete = False
    applicable_expiry = None
    expired = None

    if route == "paid_or_extinguished":
        if not mora:
            issues = _append_issue(issues, {
                "id": "CD1-M33-PERM-MORA-MISSING",
                "risk": "yellow",
                "message": (
                    "La obligación se reporta pagada o extinguida, pero falta una fecha de inicio de mora "
                    "verificable. No puede calcularse el doble de la mora ni afirmarse una fecha de retiro."
                ),
            })
        if not payment:
            issues = _append_issue(issues, {
                "id": "CD1-M33-PERM-EXTINCTION-MISSING",
                "risk": "yellow",
                "message": (
                    "La obligación se reporta pagada o extinguida, pero falta la fecha de pago o extinción. "
                    "No puede fijarse el punto inicial del término de permanencia."
                ),
            })
        if mora and payment and payment >= mora:
            mora_days = (payment - mora).days
            double_mora_expiry = date.fromordinal(payment.toordinal() + (mora_days * 2))
            four_year_cap = _add_years(payment, 4)
            paid_expiry = min(double_mora_expiry, four_year_cap)
            applicable_expiry = paid_expiry
            evidence_complete = True
            expired = applicable_expiry <= reference
            if expired:
                issues = _append_issue(issues, {
                    "id": "CD1-CALC-12",
                    "risk": "yellow",
                    "message": (
                        "Al corte M33.3, el término preliminar de permanencia del dato pagado o extinguido "
                        "aparece cumplido. Deben verificarse mora, pago/extinción, identidad del reporte y "
                        "actualización efectiva antes de exigir retiro."
                    ),
                })

    elif route == "unpaid":
        if not mora:
            issues = _append_issue(issues, {
                "id": "CD1-M33-PERM-MORA-MISSING",
                "risk": "yellow",
                "message": (
                    "La obligación se reporta vigente y en mora, pero falta la fecha verificable de inicio "
                    "de mora. No puede modelarse la caducidad máxima de ocho años."
                ),
            })
        else:
            unpaid_expiry = _add_years(mora, 8)
            applicable_expiry = unpaid_expiry
            evidence_complete = True
            expired = applicable_expiry <= reference
            if expired:
                issues = _append_issue(issues, {
                    "id": "CD1-CALC-13",
                    "risk": "yellow",
                    "message": (
                        "Al corte M33.3, la caducidad preliminar del dato negativo insoluto aparece cumplida. "
                        "Este control exige verificar la fecha real de mora y no extingue ni declara inexistente "
                        "la obligación subyacente."
                    ),
                })

    elif route == "disputed_or_unrecognized":
        issues = _append_issue(issues, {
            "id": "CD1-M33-PERM-STATUS",
            "risk": "yellow",
            "message": (
                "La obligación está discutida o no es reconocida por el titular. La permanencia temporal es "
                "un análisis subsidiario y no puede utilizarse para validar la existencia, autoría o exigibilidad "
                "de la obligación controvertida."
            ),
        })
    else:
        issues = _append_issue(issues, {
            "id": "CD1-M33-PERM-STATUS",
            "risk": "yellow",
            "message": (
                "El estado de la obligación no permite seleccionar con seguridad la regla de permanencia. "
                "Debe precisarse si permanece insoluta, fue pagada/extinguida o está controvertida."
            ),
        })

    # Se conservan las fechas hipotéticas históricas solo cuando son coherentes, pero
    # la salida M33.3 expone por separado cuál ruta es jurídicamente aplicable.
    if mora and not unpaid_expiry:
        unpaid_expiry = _add_years(mora, 8)
    if mora and payment and payment >= mora and not paid_expiry:
        mora_days = (payment - mora).days
        paid_expiry = min(
            date.fromordinal(payment.toordinal() + (mora_days * 2)),
            _add_years(payment, 4),
        )

    calculation["issues"] = issues
    calculation["mora_duration_days"] = mora_days if mora_days is not None else calculation.get("mora_duration_days")
    calculation["paid_negative_expiry_preliminary"] = paid_expiry.isoformat() if paid_expiry else None
    calculation["unpaid_negative_expiry_preliminary"] = unpaid_expiry.isoformat() if unpaid_expiry else None
    calculation["permanence_standard"] = PERMANENCE_STANDARD
    calculation["permanence_ruleset_verified_at"] = RULESET_VERIFIED_AT
    calculation["permanence_legal_basis"] = list(LEGAL_BASIS)
    calculation["permanence_reference_date"] = reference.isoformat()
    calculation["permanence_route"] = route
    calculation["permanence_evidence_complete"] = evidence_complete
    calculation["permanence_applicable_expiry"] = applicable_expiry.isoformat() if applicable_expiry else None
    calculation["permanence_term_completed_at_reference"] = expired
    calculation["permanence_law_2573_changes_article_13"] = False
    calculation["assumptions"] = _append_assumption(
        list(calculation.get("assumptions") or []),
        (
            "La regla vigente de permanencia se controla bajo el artículo 13 de la Ley 1266 de 2008, "
            "modificado por la Ley 2157 de 2021 y desarrollado por la SIC. La Ley 2573 de 2026 no se "
            "usa para modificar este cálculo de permanencia."
        ),
    )
    return calculation


def install_m33_3_habeas_permanence_guard(core_module: ModuleType) -> bool:
    current = getattr(core_module, "habeas_data_calc", None)
    if current is None:
        return False
    if getattr(current, "_legalaiz_m33_3_permanence_guard", False):
        return True

    @wraps(current)
    def wrapped(answers: dict):
        calculation = current(answers)
        return enforce_habeas_permanence(answers, calculation)

    wrapped._legalaiz_m33_3_permanence_guard = True
    wrapped._legalaiz_original = current
    setattr(core_module, "habeas_data_calc", wrapped)
    return True


__all__ = [
    "LEGAL_BASIS",
    "PERMANENCE_STANDARD",
    "RULESET_VERIFIED_AT",
    "enforce_habeas_permanence",
    "install_m33_3_habeas_permanence_guard",
]
