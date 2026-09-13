from __future__ import annotations

from urllib.parse import urlparse

import core_v11 as core
from legalai_platform.http_handler_m35_1 import Handler as BaseHandler
from legalai_platform.routes.m35_2_commerce_routes import (
    PREFIX,
    handle_m35_2_commerce_get,
    handle_m35_2_commerce_post,
)


def _missing_handoff_table(exc: Exception) -> bool:
    text = str(exc).lower()
    return "no such table" in text or ("does not exist" in text and "m35_intake_handoffs" in text)


def _install_legacy_case_guard() -> None:
    """Prevent generic case creation from bypassing an active M35 commerce chain."""
    current = core.create_case
    if getattr(current, "_m35_2_guarded", False):
        return

    def guarded_create_case(code, answers, title=None, owner="USR-CLIENT", seed=False):
        if not seed:
            con = core.db()
            try:
                try:
                    row = con.execute(
                        """SELECT id,status FROM m35_intake_handoffs
                           WHERE user_id=? AND product_code=? AND status!='CANCELLED'
                           ORDER BY created_at DESC LIMIT 1""",
                        (owner, code),
                    ).fetchone()
                except Exception as exc:
                    if _missing_handoff_table(exc):
                        row = None
                    else:
                        raise
            finally:
                con.close()
            if row:
                raise ValueError(
                    "Este diagnóstico tiene continuidad M35 activa y sólo puede crear expediente mediante el checkout trazable."
                )
        return current(code, answers, title=title, owner=owner, seed=seed)

    guarded_create_case._m35_2_guarded = True
    guarded_create_case._m35_2_original = current
    core.create_case = guarded_create_case


_install_legacy_case_guard()


class Handler(BaseHandler):
    """M35.2 commerce/case traceability on top of certified M35.1 fulfillment."""

    def do_GET(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_GET()
        user = self.require_user(roles={"client"})
        if not user:
            return
        if not handle_m35_2_commerce_get(self, path, user):
            return self.send_json({"error": "Ruta M35.2 no encontrada.", "code": "M35_2_NOT_FOUND"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if not (path == PREFIX or path.startswith(PREFIX + "/")):
            return super().do_POST()
        try:
            if not self.require_origin():
                return
            user = self.require_user(roles={"client"})
            if not user:
                return
            if not self.require_csrf():
                return
            if not handle_m35_2_commerce_post(self, path, user):
                return self.send_json({"error": "Ruta M35.2 no encontrada.", "code": "M35_2_NOT_FOUND"}, 404)
        except Exception:
            return self.send_json(
                {"error": "No fue posible operar el checkout trazable.", "code": "M35_2_INTERNAL_ERROR"},
                500,
            )


__all__ = ["Handler"]
