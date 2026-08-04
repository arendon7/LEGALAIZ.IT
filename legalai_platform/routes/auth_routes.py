from __future__ import annotations

import core_v11 as core
from legalai_platform.application_services import security_event
from legalai_platform.runtime_registry import INFRA, SETTINGS
from security import clear_session_cookie, hash_password, utc_iso, validate_password, verify_password


def handle_auth_get(handler, path, user):
    if path != "/api/auth/mfa":
        return False
    con = core.db(); payload = INFRA.mfa.status(con, user["id"]); con.close()
    handler.send_json(payload); return True


def handle_auth_post(handler, path, user):
    if path == "/api/auth/logout":
        session = handler.session(); con = core.db(); con.execute("UPDATE sessions SET revoked=1 WHERE id=?", (session["id"],)); security_event(con, user["id"], "logout", "success", handler.ip, handler.agent, {"session_id": session["id"]}); con.commit(); con.close()
        handler.send_json_cookie({"ok": True}, clear_session_cookie(secure=SETTINGS.secure_cookies), 200); return True
    if path == "/api/auth/change-password":
        data = handler.read_json(); con = core.db(); row = con.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
        if not row or not verify_password(data.get("current_password", ""), row["password_hash"] or ""):
            security_event(con, user["id"], "password_change", "denied", handler.ip, handler.agent, "Contraseña actual incorrecta"); con.commit(); con.close(); handler.send_json({"error": "La contraseña actual es incorrecta."}, 400); return True
        validate_password(data.get("new_password", ""), context_values=(user.get("name"), user.get("email", "").split("@", 1)[0])); new_hash = hash_password(data.get("new_password", ""))
        con.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user["id"])); con.execute("UPDATE sessions SET revoked=1 WHERE user_id=? AND id<>?", (user["id"], handler.session()["id"])); security_event(con, user["id"], "password_change", "success", handler.ip, handler.agent); con.commit(); con.close(); handler.send_json({"ok": True}); return True
    if path == "/api/auth/mfa/enroll":
        con = core.db(); result = INFRA.mfa.enroll(con, user["id"], user["email"]); INFRA.event(con, "mfa_enrollment_started", user["id"], {"role": user["role"]}); security_event(con, user["id"], "mfa_enroll", "pending", handler.ip, handler.agent); con.commit(); con.close(); handler.send_json(result, 201); return True
    if path == "/api/auth/mfa/confirm":
        data = handler.read_json(); con = core.db(); result = INFRA.mfa.confirm(con, user["id"], data.get("code", "")); INFRA.event(con, "mfa_enabled", user["id"], {"role": user["role"]}); con.execute("UPDATE sessions SET auth_level='full',mfa_verified_at=?,reauthenticated_at=? WHERE id=?", (utc_iso(), utc_iso(), handler.session()["id"])); security_event(con, user["id"], "mfa_confirm", "success", handler.ip, handler.agent); con.commit(); con.close(); handler._session_cache = False; handler.send_json({**result, "auth_level": "full"}); return True
    if path == "/api/auth/mfa/disable":
        if user["role"] in SETTINGS.require_mfa_roles and SETTINGS.profile in {"pilot", "production"}:
            handler.send_json({"error": "MFA es obligatorio para este rol en el perfil actual."}, 403); return True
        data = handler.read_json(); con = core.db(); row = con.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
        if not row or not verify_password(data.get("current_password", ""), row["password_hash"] or ""):
            con.close(); handler.send_json({"error": "La contraseña actual es incorrecta."}, 400); return True
        INFRA.mfa.disable(con, user["id"]); INFRA.event(con, "mfa_disabled", user["id"], {"role": user["role"]}); security_event(con, user["id"], "mfa_disable", "success", handler.ip, handler.agent); con.commit(); con.close(); handler.send_json({"ok": True}); return True
    return False
