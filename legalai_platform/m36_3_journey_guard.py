from __future__ import annotations

"""Defense-in-depth guard for M24 delivery after a case enters M36.

The public M24 route already rejects direct ``ENTREGADO`` transitions for M36
cases. This module protects the runtime singleton as well, so another internal
caller cannot bypass M36.3 by invoking ``M24_CASE_JOURNEY.transition`` directly.

Historical cases that never entered M36 remain compatible.
"""

from functools import wraps
from typing import Any, Mapping


_GUARD_MARKER = "_m36_3_controlled_delivery_guard_installed"


def _table_exists(con, table: str) -> bool:
    module = str(con.__class__.__module__ or "").lower()
    try:
        if "sqlite" in module:
            return bool(
                con.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                    (table,),
                ).fetchone()
            )
        return bool(
            con.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name=? LIMIT 1",
                (table,),
            ).fetchone()
        )
    except Exception:
        # This function is invoked only as a compatibility probe. A current M36
        # case will have the intake table and will therefore be checked below.
        return False


def _m36_case(con, case_id: str) -> bool:
    if not _table_exists(con, "m36_fulfillment_intake"):
        return False
    return bool(
        con.execute(
            "SELECT 1 FROM m36_fulfillment_intake WHERE case_id=? LIMIT 1",
            (case_id,),
        ).fetchone()
    )


def _require_prepared_delivery(con, case_id: str, evidence: Mapping[str, Any] | None) -> None:
    if not _m36_case(con, case_id):
        return
    if not _table_exists(con, "m36_controlled_delivery"):
        raise ValueError("Este expediente M36 exige una entrega preparada por la compuerta M36.3.")
    row = con.execute(
        """SELECT id,state,package_sha256,manifest_sha256,release_snapshot_sha256,release_count
           FROM m36_controlled_delivery WHERE case_id=?""",
        (case_id,),
    ).fetchone()
    if not row or str(row["state"] or "") != "PREPARED":
        raise ValueError("Este expediente M36 exige una entrega PREPARED válida antes de marcar ENTREGADO.")
    payload = evidence if isinstance(evidence, Mapping) else {}
    exact = (
        payload.get("source") == "m36_3_controlled_delivery"
        and payload.get("delivery_id") == row["id"]
        and payload.get("package_sha256") == row["package_sha256"]
        and payload.get("manifest_sha256") == row["manifest_sha256"]
        and payload.get("release_snapshot_sha256") == row["release_snapshot_sha256"]
        and int(payload.get("release_count") or 0) == int(row["release_count"] or 0)
        and payload.get("channel") == "IN_APP"
        and payload.get("download_confirmed") is False
        and payload.get("external_notification_sent") is False
    )
    if not exact:
        raise ValueError("La evidencia M36.3 no coincide con el paquete PREPARED del expediente.")


def install_m36_3_delivery_guard(journey):
    """Wrap the runtime journey once without changing historical M24 semantics."""
    if getattr(journey, _GUARD_MARKER, False):
        return journey
    original = journey.transition

    @wraps(original)
    def guarded_transition(con, case_id, target, reason, evidence, confirmation, actor):
        if str(target or "").upper().strip() == "ENTREGADO":
            _require_prepared_delivery(con, str(case_id or ""), evidence)
        return original(con, case_id, target, reason, evidence, confirmation, actor)

    journey.transition = guarded_transition
    setattr(journey, _GUARD_MARKER, True)
    setattr(journey, "_m36_3_original_transition", original)
    return journey


__all__ = ["install_m36_3_delivery_guard", "_require_prepared_delivery"]
