from __future__ import annotations

from urllib.parse import unquote

from legalai_platform.runtime_registry import M24_CANDIDATES


def _authorized(user):
    return user.get("role") in {"specialist", "admin"}


def handle_m24_candidate_get(handler, path, user):
    prefix = "/api/m24/candidate-library"
    if not path.startswith(prefix):
        return False
    if not _authorized(user):
        handler.send_json({"error": "Solo especialistas y administradores pueden consultar revisiones candidatas."}, 403)
        return True
    if path == prefix:
        handler.send_json(M24_CANDIDATES.summary())
        return True
    suffix = path[len(prefix):].strip("/")
    parts = suffix.split("/") if suffix else []
    if suffix == "integrity":
        handler.send_json(M24_CANDIDATES.verify_integrity())
        return True
    if len(parts) >= 3 and parts[1] == "assets":
        code = parts[0].upper()
        filename = unquote("/".join(parts[2:]))
        asset = M24_CANDIDATES.asset_path(code, filename)
        if not asset:
            handler.send_json({"error": "El activo candidato no existe o no superó la verificación de integridad."}, 404)
            return True
        handler.send_file(asset, download_name=asset.name)
        return True
    if len(parts) == 1:
        detail = M24_CANDIDATES.detail(parts[0].upper())
        handler.send_json(detail or {}, 200 if detail else 404)
        return True
    handler.send_json({"error": "Ruta M24 no encontrada."}, 404)
    return True
