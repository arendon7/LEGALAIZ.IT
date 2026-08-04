from __future__ import annotations

from urllib.parse import unquote

from legalai_platform.runtime_registry import DEMO_REALITY_M31_7, SETTINGS


def _allowed(user) -> bool:
    return user.get("role") in {"specialist", "admin"}


def _demo_environment() -> bool:
    return str(getattr(SETTINGS, "profile", "local")) in {"local", "pilot-local"}


def handle_m31_demo_reality_get(handler, path, user):
    prefix = "/api/m31/demo-reality"
    if not path.startswith(prefix):
        return False
    if not _allowed(user):
        handler.send_json({"error": "Esta función está reservada para especialistas y administración."}, 403); return True
    if path in {prefix, f"{prefix}/summary"}:
        handler.send_json(DEMO_REALITY_M31_7.summary()); return True
    if path == f"{prefix}/verify":
        handler.send_json(DEMO_REALITY_M31_7.verify()); return True
    file_prefix = f"{prefix}/files/"
    if path.startswith(file_prefix):
        relative = unquote(path[len(file_prefix):])
        file_path = DEMO_REALITY_M31_7.file_path(relative)
        if not file_path:
            handler.send_json({"error": "Archivo de demostración no encontrado."}, 404); return True
        handler.send_file(file_path, download_name=file_path.name); return True
    handler.send_json({"error": "Ruta M31.7 no encontrada."}, 404); return True


def handle_m31_demo_reality_post(handler, path, user):
    prefix = "/api/m31/demo-reality"
    if not path.startswith(prefix):
        return False
    if not _allowed(user):
        handler.send_json({"error": "Esta función está reservada para especialistas y administración."}, 403); return True
    if not _demo_environment():
        handler.send_json({"error": "La generación masiva de demostración solo está habilitada en entornos locales o de piloto controlado."}, 409); return True
    if path == f"{prefix}/generate":
        try:
            result = DEMO_REALITY_M31_7.generate(user.get("id") or "system")
            verification = DEMO_REALITY_M31_7.verify()
            if not verification.get("ok"):
                handler.send_json({"error": "El portafolio se generó, pero no superó la verificación de integridad.", "verification": verification}, 500); return True
            result["verification"] = verification
            handler.send_json(result, 201); return True
        except (ValueError, OSError, RuntimeError) as exc:
            handler.send_json({"error": str(exc)}, 422); return True
    return False
