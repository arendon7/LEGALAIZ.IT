from __future__ import annotations

"""Defense-in-depth guards for M37.0 controlled M24 follow-up operations.

Once a case is enrolled in M37.0, M24 remains the canonical task store, but task
mutations must pass through the M37 control layer so an append-only M37 event is
recorded. M37.0 also reserves closure/escalation for a later controlled M37
phase instead of leaving a legacy transition bypass. Historical/non-enrolled
cases preserve the previous M24 behavior.
"""

from contextvars import ContextVar
from typing import Any, Callable


_ALLOWED_CASE: ContextVar[str | None] = ContextVar("m37_0_allowed_case", default=None)
_RESERVED_LIFECYCLE_TARGETS = frozenset({"CERRADO", "ESCALADO"})


def _is_controlled_case(con, case_id: str) -> bool:
    try:
        row = con.execute(
            "SELECT state FROM m37_followup_enrollment WHERE case_id=? LIMIT 1",
            (str(case_id),),
        ).fetchone()
    except Exception:
        return False
    return bool(row and str(row[0] or "") in {"PREPARED", "ACTIVE"})


def install_m37_0_followup_guard(journey) -> None:
    """Install idempotent task and lifecycle guards on the runtime M24 singleton."""
    if bool(getattr(journey, "_m37_0_followup_guard_installed", False)):
        return
    original_update: Callable[..., Any] = journey.update_follow_up
    original_transition: Callable[..., Any] = journey.transition

    def guarded_update(con, case_id, follow_up_id, status, note, actor):
        normalized_case = str(case_id or "")
        if _is_controlled_case(con, normalized_case) and _ALLOWED_CASE.get() != normalized_case:
            raise PermissionError(
                "Este expediente ingresó a M37 y sus actividades sólo pueden actualizarse mediante el seguimiento controlado."
            )
        return original_update(con, case_id, follow_up_id, status, note, actor)

    def guarded_transition(con, case_id, target, reason, evidence, confirmation, actor):
        normalized_case = str(case_id or "")
        normalized_target = str(target or "").upper().strip()
        if _is_controlled_case(con, normalized_case) and normalized_target in _RESERVED_LIFECYCLE_TARGETS:
            raise PermissionError(
                "El cierre o escalamiento de un expediente enrolado en M37 requiere la compuerta de lifecycle M37 correspondiente."
            )
        return original_transition(con, case_id, target, reason, evidence, confirmation, actor)

    journey._m37_0_original_update_follow_up = original_update
    journey._m37_0_original_transition = original_transition
    journey.update_follow_up = guarded_update
    journey.transition = guarded_transition
    journey._m37_0_followup_guard_installed = True


def controlled_follow_up_update(
    journey,
    con,
    case_id: str,
    follow_up_id: str,
    status: str,
    note: str,
    actor: dict[str, Any],
):
    """Call M24 task mutation under an exact-case authorization context owned by M37.0."""
    normalized_case = str(case_id or "")
    token = _ALLOWED_CASE.set(normalized_case)
    try:
        return journey.update_follow_up(con, case_id, follow_up_id, status, note, actor)
    finally:
        _ALLOWED_CASE.reset(token)


__all__ = ["install_m37_0_followup_guard", "controlled_follow_up_update"]
