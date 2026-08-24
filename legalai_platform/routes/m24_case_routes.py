from __future__ import annotations

import core_v11 as core
from legalai_platform.runtime_registry import M24_CASE_JOURNEY


def _requires_m36_controlled_delivery(con, case_id: str) -> bool:
    """Return True only when this exact case already entered the M36 fulfillment path.

    Older cases created before M36 remain compatible. Once a case has an M36.0
    intake, `ENTREGADO` must be produced only by the controlled M36.3 gate.
    """
    try:
        return bool(con.execute(
            "SELECT 1 FROM m36_fulfillment_intake WHERE case_id=? LIMIT 1",
            (case_id,),
        ).fetchone())
    except Exception:
        # The table is absent on historical databases that have never executed
        # M36.0. That is not evidence that a current M36 case may bypass M36.3.
        return False


def _requires_m37_controlled_followup(con, case_id: str) -> bool:
    """Prevent the legacy M24 endpoint from bypassing the M37 append-only ledger."""
    try:
        row = con.execute(
            "SELECT state FROM m37_followup_enrollment WHERE case_id=? LIMIT 1",
            (case_id,),
        ).fetchone()
        return bool(row and str(row[0] or "") in {"PREPARED", "ACTIVE"})
    except Exception:
        # Historical databases without M37 keep their previous M24 behavior.
        return False


def handle_m24_case_get(handler, path, user):
    prefix = "/api/m24/case-journeys"
    if not path.startswith(prefix):
        return False
    con = core.db()
    try:
        if path == prefix:
            handler.send_json(M24_CASE_JOURNEY.list_for_actor(con, user)); return True
        suffix = path[len(prefix):].strip("/")
        if suffix and "/" not in suffix:
            try:
                handler.send_json(M24_CASE_JOURNEY.ensure_case(con, suffix, user)); return True
            except LookupError as exc:
                handler.send_json({"error": str(exc)}, 404); return True
        handler.send_json({"error": "Ruta de recorrido jurídico no encontrada."}, 404); return True
    finally:
        con.close()


def handle_m24_case_post(handler, path, user):
    prefix = "/api/m24/case-journeys/"
    if not path.startswith(prefix):
        return False
    suffix = path[len(prefix):]
    case_id, _, action = suffix.partition("/")
    if action not in {"transition", "follow-up"}:
        return False
    data = handler.read_json()
    con = core.db()
    try:
        if action == "transition":
            target = str(data.get("target_state") or "").upper().strip()
            if target == "ENTREGADO" and _requires_m36_controlled_delivery(con, case_id):
                handler.send_json(
                    {
                        "error": "Este expediente ingresó al flujo M36 y sólo puede entregarse mediante la compuerta controlada M36.3.",
                        "code": "M36_CONTROLLED_DELIVERY_REQUIRED",
                    },
                    409,
                )
                return True
            result = M24_CASE_JOURNEY.transition(
                con,
                case_id,
                target,
                data.get("reason"),
                data.get("evidence") or {},
                data.get("confirmation") or "",
                user,
            )
        else:
            if _requires_m37_controlled_followup(con, case_id):
                handler.send_json(
                    {
                        "error": "Este expediente ingresó al seguimiento M37 y sus actividades sólo pueden modificarse mediante la compuerta controlada M37.0.",
                        "code": "M37_CONTROLLED_FOLLOWUP_REQUIRED",
                    },
                    409,
                )
                return True
            result = M24_CASE_JOURNEY.update_follow_up(
                con,
                case_id,
                data.get("follow_up_id"),
                data.get("status"),
                data.get("note"),
                user,
            )
        handler.send_json(result); return True
    except LookupError as exc:
        handler.send_json({"error": str(exc)}, 404); return True
    except PermissionError as exc:
        handler.send_json({"error": str(exc)}, 403); return True
    except (ValueError, KeyError) as exc:
        handler.send_json({"error": str(exc)}, 422); return True
    finally:
        con.close()
