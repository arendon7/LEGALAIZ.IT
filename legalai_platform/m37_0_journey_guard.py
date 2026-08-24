from __future__ import annotations

"""Defense-in-depth guard for M37.0 controlled M24 follow-up updates.

Once a case is enrolled in M37.0, M24 remains the canonical task store, but all
mutations must pass through the M37 control layer so an append-only M37 event is
recorded. Historical/non-enrolled cases preserve the legacy M24 behavior.
"""

from contextvars import ContextVar
from typing import Any, Callable


_ALLOWED_CASE: ContextVar[str | None] = ContextVar("m37_0_allowed_case", default=None)


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
    """Install an idempotent guard on the runtime M24 singleton."""
    if bool(getattr(journey, "_m37_0_followup_guard_installed", False)):
        return
    original: Callable[..., Any] = journey.update_follow_up

    def guarded(con, case_id, follow_up_id, status, note, actor):
        normalized_case = str(case_id or "")
        if _is_controlled_case(con, normalized_case) and _ALLOWED_CASE.get() != normalized_case:
            raise PermissionError(
                "Este expediente ingresó a M37 y sus actividades sólo pueden actualizarse mediante el seguimiento controlado."
            )
        return original(con, case_id, follow_up_id, status, note, actor)

    journey._m37_0_original_update_follow_up = original
    journey.update_follow_up = guarded
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
    """Call M24 under an exact-case authorization context owned by M37.0."""
    normalized_case = str(case_id or "")
    token = _ALLOWED_CASE.set(normalized_case)
    try:
        return journey.update_follow_up(con, case_id, follow_up_id, status, note, actor)
    finally:
        _ALLOWED_CASE.reset(token)


__all__ = ["install_m37_0_followup_guard", "controlled_follow_up_update"]
