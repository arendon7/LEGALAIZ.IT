from __future__ import annotations

from legalai_platform.runtime_registry import M24_CLIENT_INTAKE


def handle_m24_client_get(handler, path, user):
    prefix = "/api/m24/client-offers/"
    if not path.startswith(prefix):
        return False
    code = path[len(prefix):].strip("/").upper()
    try:
        handler.send_json(M24_CLIENT_INTAKE.offer(code)); return True
    except LookupError as exc:
        handler.send_json({"error": str(exc)}, 404); return True


def handle_m24_client_post(handler, path, user):
    if path != "/api/m24/client-intake":
        return False
    data = handler.read_json()
    try:
        handler.send_json(M24_CLIENT_INTAKE.analyze(data.get("narrative") or "")); return True
    except ValueError as exc:
        handler.send_json({"error": str(exc)}, 400); return True
