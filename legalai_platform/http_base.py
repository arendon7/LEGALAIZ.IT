from __future__ import annotations

import json
from urllib.parse import urlparse

from legalai_platform.application_services import get_session
from legalai_platform.operational_security import same_origin_allowed
from legalai_platform.runtime_registry import OBSERVABILITY, SETTINGS
from security import compare_csrf, parse_cookie


class RequestContextMixin:
    """Shared HTTP request, session and security primitives.

    The mixin is intentionally transport-focused. Functional endpoints live in
    route modules so authentication, catalogue, product and governance domains
    can evolve independently without expanding the central handler again.
    """

    _session_cache = False
    _request_id = None

    @property
    def request_id(self):
        if not self._request_id:
            self._request_id = OBSERVABILITY.request_id(self.headers.get("X-Request-ID"))
        return self._request_id

    def log_message(self, fmt, *args):
        OBSERVABILITY.write(
            "http_access",
            request_id=self.request_id,
            method=getattr(self, "command", ""),
            path=self.path.split("?", 1)[0],
            client_ip=self.ip,
            message=fmt % args,
        )

    def end_headers(self):
        self.send_header("X-Request-ID", self.request_id)
        if self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Permitted-Cross-Domain-Policies", "none")
        if SETTINGS.secure_cookies:
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        super().end_headers()

    @property
    def ip(self):
        peer = self.client_address[0] if self.client_address else ""
        if SETTINGS.trust_proxy and peer in SETTINGS.trusted_proxy_ips:
            forwarded = (self.headers.get("X-Forwarded-For") or "").split(",", 1)[0].strip()
            if forwarded:
                return forwarded
        return peer

    @property
    def agent(self):
        return self.headers.get("User-Agent", "")

    def session(self):
        if self._session_cache is False:
            self._session_cache = get_session(parse_cookie(self.headers.get("Cookie")))
        return self._session_cache

    def user(self):
        session = self.session()
        return session["user"] if session else None

    def require_user(self, roles=None):
        user = self.user()
        if not user:
            self.send_json({"error": "Autenticación requerida.", "code": "AUTH_REQUIRED"}, 401)
            return None
        session = self.session()
        allowed_restricted = {
            "/api/auth/me",
            "/api/auth/mfa",
            "/api/auth/mfa/enroll",
            "/api/auth/mfa/confirm",
            "/api/auth/logout",
        }
        if session and session.get("mfa_enrollment_required") and urlparse(self.path).path not in allowed_restricted:
            self.send_json(
                {"error": "Debe completar la inscripción MFA antes de continuar.", "code": "MFA_ENROLLMENT_REQUIRED"},
                403,
            )
            return None
        if roles and user["role"] not in roles:
            self.send_json({"error": "No tiene permisos para esta operación.", "code": "FORBIDDEN"}, 403)
            return None
        return user

    def require_csrf(self):
        session = self.session()
        received = self.headers.get("X-CSRF-Token")
        if not session or not compare_csrf(session["csrf"], received):
            self.send_json({"error": "Token CSRF inválido o ausente.", "code": "CSRF_FAILED"}, 403)
            return False
        return True

    def require_origin(self):
        if same_origin_allowed(
            self.headers.get("Origin"),
            self.headers.get("Referer"),
            SETTINGS.public_base_url,
            required=SETTINGS.require_origin_check,
        ):
            return True
        self.send_json({"error": "Origen de solicitud no permitido.", "code": "ORIGIN_REJECTED"}, 403)
        return False

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 1024 * 1024:
            raise ValueError("La solicitud JSON supera el límite de 1 MB.")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw or b"{}")

    def send_json_cookie(self, obj, cookie, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)
