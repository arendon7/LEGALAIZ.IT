from __future__ import annotations

"""Compuerta M33.3 para el efecto favorable del silencio en CO-CD-001.

La Resolución SIC 107492 de 17 de diciembre de 2025, divulgada en febrero de 2026,
interpretó que el efecto del numeral 8 de la parte II del artículo 16 de la Ley 1266
de 2008 no se traslada mecánicamente a toda respuesta tardía y se restringe al
supuesto de protección de la víctima de suplantación.

Esta capa no elimina el control de vencimiento. Separa:
- término vencido o respuesta tardía; y
- posible efecto favorable por silencio en una controversia de suplantación.

Si el expediente no individualiza que el reclamo previo correspondía precisamente a
la obligación desconocida por posible suplantación, el segundo efecto falla cerrado.
"""

from datetime import date
from functools import wraps
from types import ModuleType
from typing import Any

SIC_SILENCE_AUTHORITY = "Resolución SIC 107492 del 17 de diciembre de 2025"
SILENCE_SCOPE = "identity_theft_claim_only"


def _yes(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"sí", "si", "yes", "true", "1"}


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _explicit_identity_scope(answers: dict) -> bool:
    """Admite la futura pregunta canónica sin inferir suplantación por coexistencia."""
    if _yes(answers.get("prior_claim_identity_theft")):
        return True
    scope = str(answers.get("prior_claim_scope") or "").strip().casefold()
    return scope in {
        "suplantación",
        "suplantacion",
        "posible suplantación",
        "posible suplantacion",
        "obligación desconocida por suplantación",
        "obligacion desconocida por suplantacion",
    }


def _without_issue(issues: list, issue_id: str) -> list:
    return [
        issue for issue in (issues or [])
        if not (isinstance(issue, dict) and str(issue.get("id")) == issue_id)
    ]


def _append_unique_issue(issues: list, issue: dict) -> list:
    result = list(issues or [])
    if not any(isinstance(item, dict) and item.get("id") == issue.get("id") for item in result):
        result.append(issue)
    return result


def _append_unique_assumption(assumptions: list, text: str) -> list:
    result = list(assumptions or [])
    if text not in result:
        result.append(text)
    return result


def enforce_habeas_silence_scope(answers: dict, calculation: dict) -> dict:
    """Sanea el efecto de silencio sin borrar el control de vencimiento."""
    calculation = calculation if isinstance(calculation, dict) else {}
    calculation["silence_legal_scope"] = SILENCE_SCOPE
    calculation["silence_authority_reference"] = SIC_SILENCE_AUTHORITY

    prior_overdue = bool(calculation.get("prior_term_overdue_preliminary"))
    prior_complete = _yes(answers.get("prior_claim_complete"))
    response_complete = (
        _yes(answers.get("response_received"))
        and str(answers.get("response_quality") or "").strip().casefold() == "de fondo y completa"
    )
    identity_alleged = _yes(answers.get("identity_theft"))
    identity_scope = identity_alleged and _explicit_identity_scope(answers)

    prior_date = _parse_date(answers.get("prior_claim_date") or calculation.get("prior_claim_date"))
    discovery_date = _parse_date(answers.get("identity_theft_discovery_date"))
    chronology_consistent = not (
        identity_scope and prior_date and discovery_date and prior_date < discovery_date
    )
    scope_verified = bool(identity_scope and chronology_consistent)
    calculation["silence_identity_theft_scope_verified"] = scope_verified

    favorable = bool(
        scope_verified
        and _yes(answers.get("prior_claim"))
        and prior_overdue
        and prior_complete
        and not response_complete
    )
    calculation["silence_acceptance_preliminary"] = favorable

    issues = _without_issue(list(calculation.get("issues") or []), "CD1-CALC-15")
    issues = _without_issue(issues, "CD1-M33-SILENCE-SCOPE")
    issues = _without_issue(issues, "CD1-M33-SILENCE-CHRONOLOGY")

    if favorable:
        issues = _append_unique_issue(issues, {
            "id": "CD1-CALC-15",
            "risk": "yellow",
            "message": (
                "Puede existir efecto favorable preliminar por silencio únicamente respecto del "
                "reclamo de posible suplantación individualizado; deben verificarse integridad, "
                "recepción, prórroga y ausencia de respuesta de fondo."
            ),
        })
    elif identity_scope and not chronology_consistent:
        issues = _append_unique_issue(issues, {
            "id": "CD1-M33-SILENCE-CHRONOLOGY",
            "risk": "yellow",
            "message": (
                "El reclamo previo fue marcado como relativo a suplantación, pero su fecha precede "
                "al conocimiento informado de esa suplantación. No se activa efecto favorable por "
                "silencio hasta conciliar la cronología."
            ),
        })
    elif prior_overdue and prior_complete and not response_complete:
        issues = _append_unique_issue(issues, {
            "id": "CD1-M33-SILENCE-SCOPE",
            "risk": "yellow",
            "message": (
                "El reclamo previo aparece vencido sin respuesta completa, pero no está acreditado "
                "que correspondiera específicamente a la obligación desconocida por suplantación. "
                "No se activa automáticamente el efecto favorable del silencio."
            ),
        })

    calculation["issues"] = issues
    calculation["assumptions"] = _append_unique_assumption(
        list(calculation.get("assumptions") or []),
        (
            "El vencimiento de un reclamo y el efecto favorable del silencio son controles distintos. "
            "Conforme al criterio administrativo de la Resolución SIC 107492 de 2025, LegalAIZ.it "
            "solo modela el segundo cuando el reclamo previo está individualizado como controversia "
            "de suplantación; la mera respuesta tardía de una reclamación ordinaria no basta."
        ),
    )
    return calculation


def install_m33_3_habeas_silence_guard(core_module: ModuleType) -> bool:
    current = getattr(core_module, "habeas_data_calc", None)
    if current is None:
        return False
    if getattr(current, "_legalaiz_m33_3_silence_guard", False):
        return True

    @wraps(current)
    def wrapped(answers: dict):
        calculation = current(answers)
        return enforce_habeas_silence_scope(answers, calculation)

    wrapped._legalaiz_m33_3_silence_guard = True
    wrapped._legalaiz_original = current
    setattr(core_module, "habeas_data_calc", wrapped)
    return True


__all__ = [
    "SIC_SILENCE_AUTHORITY",
    "SILENCE_SCOPE",
    "enforce_habeas_silence_scope",
    "install_m33_3_habeas_silence_guard",
]
