from __future__ import annotations

"""Privileged M37.3 lifecycle bridge.

M37.0 intentionally blocks generic CERRADO/ESCALADO transitions for enrolled
cases. M37.3 is the only phase allowed to cross that boundary after its own
professional disposition gate has validated role, readiness, integrity and
explicit confirmation.
"""

from typing import Any


_RESERVED_TARGETS = frozenset({"CERRADO", "ESCALADO"})


def controlled_m37_disposition_transition(
    journey,
    con,
    case_id: str,
    target: str,
    client_summary: str,
    evidence: dict[str, Any],
    actor: dict[str, Any],
):
    normalized_target = str(target or "").upper().strip()
    if normalized_target not in _RESERVED_TARGETS:
        raise ValueError("M37.3 sólo puede controlar CERRADO o ESCALADO.")
    if not bool(getattr(journey, "_m37_0_followup_guard_installed", False)):
        raise RuntimeError("La compuerta M37.0 no está instalada; M37.3 falla cerrado.")
    original = getattr(journey, "_m37_0_original_transition", None)
    if not callable(original):
        raise RuntimeError("M37.3 no encontró la transición M24 protegida por M37.0.")
    return original(
        con,
        str(case_id),
        normalized_target,
        str(client_summary),
        dict(evidence or {}),
        "",
        dict(actor),
    )


__all__ = ["controlled_m37_disposition_transition"]
