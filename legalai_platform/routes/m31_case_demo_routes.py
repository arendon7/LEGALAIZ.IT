from __future__ import annotations

from urllib.parse import unquote

import core_v11 as core
from legalai_platform.runtime_registry import M31_CASE_DEMO, SETTINGS


def _demo_environment() -> bool:
    return str(getattr(SETTINGS, "profile", "local")) in {"local", "pilot-local"}


def _professional(user) -> bool:
    return user.get("role") in {"specialist", "admin"}


def handle_m31_case_demo_get(handler, path, user):
    prefix = "/api/m31/case-demo"
    if not path.startswith(prefix):
        return False
    if not _professional(user):
        handler.send_json({"error": "La demo integral de expedientes está reservada para especialistas y administración."}, 403)
        return True
    con = core.db()
    try:
        if path in {prefix, f"{prefix}/summary"}:
            handler.send_json(M31_CASE_DEMO.summary(con)); return True
        if path == f"{prefix}/verify":
            handler.send_json(M31_CASE_DEMO.verify(con)); return True
        file_prefix = f"{prefix}/files/"
        if path.startswith(file_prefix):
            relative = unquote(path[len(file_prefix):])
            file_path = M31_CASE_DEMO.file_path(relative)
            if not file_path:
                handler.send_json({"error": "Archivo del expediente demo no encontrado."}, 404); return True
            handler.send_file(file_path, download_name=file_path.name); return True
        case_prefix = f"{prefix}/cases/"
        if path.startswith(case_prefix):
            case_id = unquote(path[len(case_prefix):].strip("/"))
            detail = M31_CASE_DEMO.detail(con, case_id)
            handler.send_json(detail or {"error": "Expediente demo no encontrado."}, 200 if detail else 404); return True
        handler.send_json({"error": "Ruta M31.8 no encontrada."}, 404); return True
    finally:
        con.close()


def handle_m31_case_demo_post(handler, path, user):
    prefix = "/api/m31/case-demo"
    if not path.startswith(prefix):
        return False
    if not _professional(user):
        handler.send_json({"error": "La demo integral de expedientes está reservada para especialistas y administración."}, 403)
        return True
    if not _demo_environment():
        handler.send_json({"error": "La preparación de expedientes demo solo está habilitada en entornos locales o de piloto controlado."}, 409)
        return True
    data = handler.read_json()
    con = core.db()
    try:
        if path == f"{prefix}/prepare":
            result = M31_CASE_DEMO.bootstrap(con, user["id"], reset=bool(data.get("reset")), auto_release=bool(data.get("auto_release", True)))
            handler.send_json(result, 201); return True
        if path == f"{prefix}/reset":
            if user.get("role") != "admin":
                raise PermissionError("Solo administración puede reiniciar la cohorte demo.")
            result = M31_CASE_DEMO.reset(con, user["id"])
            handler.send_json(result); return True
        case_prefix = f"{prefix}/cases/"
        if path.startswith(case_prefix):
            suffix = path[len(case_prefix):].strip("/")
            if "/" not in suffix:
                return False
            case_id, action = suffix.rsplit("/", 1)
            case_id = unquote(case_id)
            if action == "revise":
                result = M31_CASE_DEMO.revise(con, case_id, user["id"], data.get("answers_patch") or {}, str(data.get("note") or ""))
                handler.send_json(result, 201); return True
            if action == "legal-approve":
                result = M31_CASE_DEMO.approve(con, case_id, "legal", user["id"], str(data.get("decision") or "approve"), str(data.get("comment") or ""))
                con.commit(); handler.send_json(result); return True
            if action == "qa-approve":
                result = M31_CASE_DEMO.approve(con, case_id, "qa", user["id"], str(data.get("decision") or "approve"), str(data.get("comment") or ""))
                con.commit(); handler.send_json(result); return True
            if action == "release":
                result = M31_CASE_DEMO.release(con, case_id, user["id"])
                con.commit(); handler.send_json(result, 201); return True
        return False
    except PermissionError as exc:
        con.rollback(); handler.send_json({"error": str(exc)}, 403); return True
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        con.rollback(); handler.send_json({"error": str(exc)}, 422); return True
    finally:
        con.close()
