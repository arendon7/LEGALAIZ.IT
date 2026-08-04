from __future__ import annotations

import uuid

import core_v11 as core
from legalai_platform.application_services import authenticate, security_event
from legalai_platform.runtime_registry import (
    ANON_DRAFTS,
    APPROVALS,
    BUILD_ID,
    INFRA,
    PORTAL,
    SELF_SERVICE,
    SETTINGS,
    VERSION,
    WORKFLOW,
    M24_CLIENT_INTAKE,
    GOLD_STANDARD,
    ALLOWED_UPLOADS,
    COMMERCIAL_EXPERIENCE,
    RATE_LIMITER,
    M31_PREPRODUCTION,
)
from legalai_platform.system_api import config_payload, health_payload
from legalai_platform.release_metadata import MILESTONE
from security import hash_password, make_session_cookie, utc_iso, validate_password


def handle_public_get(handler, u, path):
    if path == "/api/live":
        handler.send_json({"ok": True, "build_id": BUILD_ID}); return True
    if path == "/api/ready":
        con = core.db()
        try: report = M31_PREPRODUCTION.checks(con)
        finally: con.close()
        ready = bool(report.get("preproduction_ready"))
        handler.send_json({"ok": ready, "build_id": BUILD_ID, "profile": SETTINGS.profile, "phase": MILESTONE, "blocking": report.get("hard_blocking") or [], "production_authorized": False}, 200 if ready or SETTINGS.profile == "local" else 503); return True
    if path == "/api/health":
        con = core.db(); doctor = INFRA.doctor(con); con.close()
        handler.send_json(health_payload(version=VERSION, build_id=BUILD_ID, settings=SETTINGS, infrastructure_ready=doctor["ready"], approval_summary=APPROVALS.public_summary())); return True
    if path == "/api/config":
        handler.send_json(config_payload(version=VERSION, build_id=BUILD_ID, settings=SETTINGS, allowed_uploads=ALLOWED_UPLOADS, approval_summary=APPROVALS.public_summary())); return True
    if path == "/api/approval-status":
        handler.send_json(APPROVALS.public_summary()); return True
    if path.startswith("/api/approval-status/"):
        code = path.split("/")[-1]; obj = APPROVALS.product_public(code)
        handler.send_json(obj or {}, 200 if obj else 404); return True
    if path == "/api/auth/me":
        session = handler.session()
        handler.send_json({"authenticated": bool(session), "user": session["user"] if session else None, "csrf_token": session["csrf"] if session else None, "auth_level": session.get("auth_level") if session else None, "mfa_enrollment_required": bool(session and session.get("mfa_enrollment_required"))}); return True
    if path == "/api/public/catalog":
        handler.send_json(PORTAL.catalog()); return True
    if path == "/api/public/gold-standard":
        handler.send_json(GOLD_STANDARD.summary()); return True
    if path.startswith("/api/public/gold-standard/"):
        code = path.split("/")[-1]; obj = GOLD_STANDARD.detail(code)
        handler.send_json(obj or {}, 200 if obj else 404); return True
    if path.startswith("/api/public/products/"):
        code = path.split("/")[-1]; obj = PORTAL.detail(code)
        handler.send_json(obj or {}, 200 if obj else 404); return True
    if path == "/api/catalog-summary":
        handler.send_json({
            "products": len(core.PRODUCTS),
            "pilot_products": sum(p.get("pilot_level") == "Piloto integral" for p in core.PRODUCTS),
            "documental_products": sum(p.get("pilot_level") == "Piloto documental" for p in core.PRODUCTS),
            "questions": sum(len(x.get("questions", [])) for x in core.INTERVIEWS.values()),
            "rules": sum(len(x) for x in core.RULES.values()),
            "sources": sum(len(x) for x in core.SOURCES.values()),
            "tests": sum(len(x) for x in core.SCENARIOS.values()),
            "sast_rows": len(core.SAST),
        }); return True
    if path == "/api/products":
        handler.send_json(core.PRODUCTS); return True
    if path == "/api/product-experience":
        handler.send_json(WORKFLOW.experience_summary()); return True
    if path.startswith("/api/product-experience/"):
        code = path.split("/")[-1]; obj = WORKFLOW.product_experience(code)
        handler.send_json(obj or {}, 200 if obj else 404); return True
    if path.startswith("/api/products/"):
        code = path.split("/")[-1]; product = core.product(code)
        handler.send_json({"product": product, "interview": core.INTERVIEWS.get(code, {}), "rules": core.RULES.get(code, []), "sources": core.SOURCES.get(code, []), "scenarios": core.SCENARIOS.get(code, []), "experience": WORKFLOW.product_experience(code)}, 200 if product else 404); return True
    return False


def handle_public_post(handler, path):
    if path == "/api/public/commercial-intake":
        allowed, retry = RATE_LIMITER.allow(f"commercial-intake:{handler.ip}", 5, 3600)
        if not allowed:
            handler.send_json({"error": "Demasiadas solicitudes. Intenta nuevamente más adelante.", "retry_after": retry}, 429); return True
        data = handler.read_json(); con = core.db()
        try:
            result = COMMERCIAL_EXPERIENCE.capture_lead(con, data)
            handler.send_json(result, 200 if result.get("duplicate") else 201)
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, 400)
        finally:
            con.close()
        return True

    if path == "/api/public/experience-event":
        allowed, retry = RATE_LIMITER.allow(f"experience-event:{handler.ip}", 120, 3600)
        if not allowed:
            handler.send_json({"ok": False, "recorded": False, "retry_after": retry}, 429); return True
        data = handler.read_json(); con = core.db()
        try:
            handler.send_json(COMMERCIAL_EXPERIENCE.capture_metric(con, data))
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, 400)
        finally:
            con.close()
        return True

    if path == "/api/public/gold-precheck":
        data = handler.read_json()
        try:
            handler.send_json(GOLD_STANDARD.precheck(data.get("product_code") or "", data.get("answers") or {})); return True
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, 400); return True

    if path == "/api/public/intake":
        data = handler.read_json()
        try:
            handler.send_json(M24_CLIENT_INTAKE.analyze(data.get("narrative") or "")); return True
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, 400); return True

    if path == "/api/public/diagnose":
        data = handler.read_json()
        try:
            result = core.diagnose(data.get("product_code"), data.get("answers") or {}, strict=bool(data.get("strict", True)))
            handler.send_json(PORTAL.result(result))
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, 400)
        return True

    if path == "/api/public/drafts/save":
        data = handler.read_json(); con = core.db()
        try:
            result = ANON_DRAFTS.save(con, data.get("product_code"), data.get("answers") or {}, data.get("current_step") or 0, data.get("recovery_code") or None, data.get("result")); con.commit()
        except ValueError as exc:
            con.close(); handler.send_json({"error": str(exc)}, 400); return True
        finally:
            try: con.close()
            except Exception: pass
        handler.send_json(result, 201); return True

    if path == "/api/public/drafts/recover":
        data = handler.read_json(); con = core.db()
        try:
            result = ANON_DRAFTS.recover(con, data.get("recovery_code") or ""); con.commit()
        except ValueError as exc:
            con.close(); handler.send_json({"error": str(exc)}, 404); return True
        finally:
            try: con.close()
            except Exception: pass
        handler.send_json(result); return True

    if path == "/api/auth/register":
        data = handler.read_json(); name = (data.get("name") or "").strip(); email = (data.get("email") or "").strip().lower(); password = data.get("password") or ""; consent = bool(data.get("consent"))
        if len(name) < 3: handler.send_json({"error": "Escribe tu nombre completo."}, 400); return True
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]: handler.send_json({"error": "Escribe un correo electrónico válido."}, 400); return True
        if not consent: handler.send_json({"error": "Debes aceptar el tratamiento de datos para crear la cuenta."}, 400); return True
        try:
            validate_password(password, context_values=(name, email.split("@", 1)[0])); password_hash = hash_password(password)
        except ValueError as exc:
            handler.send_json({"error": str(exc)}, 400); return True
        con = core.db()
        if con.execute("SELECT 1 FROM users WHERE lower(email)=?", (email,)).fetchone():
            con.close(); handler.send_json({"error": "Ya existe una cuenta con este correo."}, 409); return True
        uid = "USR-" + uuid.uuid4().hex[:12].upper(); timestamp = utc_iso()
        con.execute("INSERT INTO users(id,name,email,role,specialty,verified,password_hash,failed_attempts,locked_until,active,created_at,last_login_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (uid, name, email, "client", "Usuario", 0, password_hash, 0, None, 1, timestamp, None))
        security_event(con, uid, "registration", "success", handler.ip, handler.agent, {"source": "public_portal"}); con.commit(); con.close()
        result, error = authenticate(email, password, handler.ip, handler.agent, "")
        if error: handler.send_json({"error": "La cuenta fue creada, pero no fue posible iniciar sesión."}, 500); return True
        handler.send_json_cookie({"ok": True, "user": result["user"], "csrf_token": result["csrf"], "auth_level": result.get("auth_level"), "mfa_enrollment_required": result.get("mfa_enrollment_required", False)}, make_session_cookie(result["token"], secure=SETTINGS.secure_cookies), 201); return True

    if path == "/api/auth/login":
        data = handler.read_json(); result, error = authenticate(data.get("email"), data.get("password"), handler.ip, handler.agent, data.get("mfa_code", ""))
        if error:
            if isinstance(error, dict):
                status = 429 if error.get("code") == "RATE_LIMITED" else 401
                handler.send_json({"error": error.get("message"), "code": error.get("code"), "retry_after": error.get("retry_after")}, status)
            else:
                handler.send_json({"error": error}, 401)
            return True
        handler.send_json_cookie({"ok": True, "user": result["user"], "csrf_token": result["csrf"], "auth_level": result.get("auth_level"), "mfa_enrollment_required": result.get("mfa_enrollment_required", False)}, make_session_cookie(result["token"], secure=SETTINGS.secure_cookies), 200); return True
    return False
