from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac, scrypt, sha256
from http.cookies import SimpleCookie
import base64
import hmac
import secrets

PBKDF2_ROUNDS = 240_000
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
SESSION_COOKIE = "lz_session"
SESSION_HOURS = 8
CLIENT_IDLE_MINUTES = 120
PRIVILEGED_IDLE_MINUTES = 30
LOCKOUT_ATTEMPTS = 5
LOCKOUT_MINUTES = 10
COMMON_PASSWORDS = {
    "password", "password123", "123456789", "qwerty123", "admin123", "administrador",
    "contraseña", "contrasena", "legalaiz", "legalai", "welcome123", "abc123456",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).isoformat(timespec="seconds")


def validate_password(password: str, *, context_values=()) -> None:
    if not isinstance(password, str):
        raise ValueError("La contraseña no es válida.")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres.")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"La contraseña no puede superar {PASSWORD_MAX_LENGTH} caracteres.")
    normalized = password.casefold().strip()
    compact = "".join(ch for ch in normalized if ch.isalnum())
    if normalized in COMMON_PASSWORDS or compact in COMMON_PASSWORDS:
        raise ValueError("La contraseña elegida es demasiado común.")
    for value in context_values or ():
        token = "".join(ch for ch in str(value or "").casefold() if ch.isalnum())
        if len(token) >= 4 and token in compact:
            raise ValueError("La contraseña no debe contener el nombre o correo de la cuenta.")


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32, maxmem=64 * 1024 * 1024)
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N, SCRYPT_R, SCRYPT_P,
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
    )


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_password(password: str, encoded: str) -> bool:
    try:
        parts = encoded.split("$")
        if parts[0] == "scrypt" and len(parts) == 6:
            _, n, r, p, salt, expected = parts
            actual = scrypt(password.encode("utf-8"), salt=_b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32, maxmem=64 * 1024 * 1024)
            return hmac.compare_digest(actual, _b64decode(expected))
        if parts[0] == "pbkdf2_sha256" and len(parts) == 4:
            _, rounds, salt, expected = parts
            actual = pbkdf2_hmac("sha256", password.encode("utf-8"), _b64decode(salt), int(rounds))
            return hmac.compare_digest(actual, _b64decode(expected))
    except Exception:
        return False
    return False


def password_needs_rehash(encoded: str | None) -> bool:
    if not encoded:
        return True
    try:
        parts = encoded.split("$")
        return not (parts[0] == "scrypt" and int(parts[1]) >= SCRYPT_N and int(parts[2]) >= SCRYPT_R and int(parts[3]) >= SCRYPT_P)
    except Exception:
        return True


def new_token(size: int = 32) -> str:
    return secrets.token_urlsafe(size)


def token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def parse_cookie(header: str | None, name: str = SESSION_COOKIE) -> str | None:
    if not header:
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(header)
        morsel = cookie.get(name)
        return morsel.value if morsel else None
    except Exception:
        return None


def make_session_cookie(token: str, *, secure: bool = False) -> str:
    attrs = [
        f"{SESSION_COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Strict",
        f"Max-Age={SESSION_HOURS * 3600}",
    ]
    if secure:
        attrs.append("Secure")
    return "; ".join(attrs)


def clear_session_cookie(*, secure: bool = False) -> str:
    attrs = [f"{SESSION_COOKIE}=", "Path=/", "HttpOnly", "SameSite=Strict", "Max-Age=0"]
    if secure:
        attrs.append("Secure")
    return "; ".join(attrs)


def session_expiry() -> str:
    return utc_iso(utc_now() + timedelta(hours=SESSION_HOURS))


def idle_expiry(role: str, *, client_minutes: int = CLIENT_IDLE_MINUTES, privileged_minutes: int = PRIVILEGED_IDLE_MINUTES) -> str:
    minutes = privileged_minutes if role in {"admin", "specialist"} else client_minutes
    return utc_iso(utc_now() + timedelta(minutes=max(5, int(minutes))))


def lockout_expiry() -> str:
    return utc_iso(utc_now() + timedelta(minutes=LOCKOUT_MINUTES))


def is_future(iso_value: str | None) -> bool:
    if not iso_value:
        return False
    try:
        dt = datetime.fromisoformat(iso_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt > utc_now()
    except Exception:
        return False


def compare_csrf(expected: str | None, received: str | None) -> bool:
    return bool(expected and received and hmac.compare_digest(expected, received))
