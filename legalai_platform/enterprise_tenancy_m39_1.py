from __future__ import annotations

"""M39.1 · Organizaciones, membresías y contexto empresarial.

Esta capa es deliberadamente aditiva: no cambia todavía la propiedad histórica de
``cases``. Su responsabilidad es establecer un tenant empresarial verificable y
fail-closed antes de que Solicitudes, Contratos u otros dominios nuevos empiecen a
persistir información con ``organization_id``.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import uuid


ACTIVE = "active"
INACTIVE = "inactive"
ORGANIZATION_STATUSES = {ACTIVE, "suspended", INACTIVE}
MEMBERSHIP_STATUSES = {ACTIVE, INACTIVE}
MEMBERSHIP_ROLES = {"owner", "admin", "manager", "member", "viewer"}


class TenancyError(RuntimeError):
    def __init__(self, message: str, *, code: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = int(status)

    def public(self) -> dict[str, str]:
        return {"error": self.message, "code": self.code}


@dataclass(frozen=True)
class EnterpriseContext:
    organization: dict
    membership: dict
    source: str

    def public(self) -> dict:
        return {
            "organization": self.organization,
            "membership": self.membership,
            "context_source": self.source,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _identifier(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16].upper()}"


def _text(value, *, field: str, required: bool = False, limit: int = 240) -> str:
    clean = " ".join(str(value or "").strip().split())
    if required and not clean:
        raise TenancyError(f"{field} es obligatorio.", code="TENANCY_VALIDATION_ERROR")
    if len(clean) > limit:
        raise TenancyError(f"{field} supera el límite permitido.", code="TENANCY_VALIDATION_ERROR")
    return clean


def _tax_id(value) -> str:
    clean = _text(value, field="tax_id", limit=64)
    if clean and not re.fullmatch(r"[A-Za-z0-9.\- ]{3,64}", clean):
        raise TenancyError("tax_id contiene caracteres no permitidos.", code="TENANCY_VALIDATION_ERROR")
    return clean


def ensure_schema(con) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS enterprise_organizations(
          id TEXT PRIMARY KEY,
          legal_name TEXT NOT NULL,
          display_name TEXT NOT NULL,
          tax_id TEXT,
          status TEXT NOT NULL DEFAULT 'active',
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(created_by) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_enterprise_organizations_status
          ON enterprise_organizations(status,display_name);

        CREATE TABLE IF NOT EXISTS enterprise_memberships(
          id TEXT PRIMARY KEY,
          organization_id TEXT NOT NULL,
          user_id TEXT NOT NULL,
          role TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(organization_id) REFERENCES enterprise_organizations(id),
          FOREIGN KEY(user_id) REFERENCES users(id),
          FOREIGN KEY(created_by) REFERENCES users(id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_enterprise_membership_unique
          ON enterprise_memberships(organization_id,user_id);
        CREATE INDEX IF NOT EXISTS idx_enterprise_membership_user_active
          ON enterprise_memberships(user_id,status,organization_id);
        CREATE INDEX IF NOT EXISTS idx_enterprise_membership_org_active
          ON enterprise_memberships(organization_id,status,role);
        """
    )


def _user(con, user_id: str, *, require_active: bool = True):
    row = con.execute("SELECT id,name,email,role,active FROM users WHERE id=?", (str(user_id),)).fetchone()
    if not row or (require_active and not bool(row["active"])):
        raise TenancyError("El usuario indicado no está disponible.", code="TENANCY_USER_NOT_FOUND", status=404)
    return row


def _organization_row(con, organization_id: str, *, active_only: bool = False):
    ensure_schema(con)
    row = con.execute(
        "SELECT id,legal_name,display_name,tax_id,status,created_by,created_at,updated_at FROM enterprise_organizations WHERE id=?",
        (str(organization_id),),
    ).fetchone()
    if not row:
        return None
    if active_only and row["status"] != ACTIVE:
        return None
    return row


def get_organization(con, organization_id: str, *, active_only: bool = False) -> dict | None:
    row = _organization_row(con, organization_id, active_only=active_only)
    return dict(row) if row else None


def create_organization(
    con,
    *,
    legal_name: str,
    owner_user_id: str,
    created_by: str,
    display_name: str = "",
    tax_id: str = "",
) -> dict:
    ensure_schema(con)
    creator = _user(con, created_by)
    owner = _user(con, owner_user_id)
    legal = _text(legal_name, field="legal_name", required=True, limit=240)
    display = _text(display_name, field="display_name", limit=160) or legal
    tax = _tax_id(tax_id)
    organization_id = _identifier("ORG")
    timestamp = _now()
    con.execute(
        "INSERT INTO enterprise_organizations(id,legal_name,display_name,tax_id,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
        (organization_id, legal, display, tax or None, ACTIVE, creator["id"], timestamp, timestamp),
    )
    membership = _insert_membership(
        con,
        organization_id=organization_id,
        user_id=owner["id"],
        role="owner",
        created_by=creator["id"],
    )
    organization = get_organization(con, organization_id)
    return {"organization": organization, "owner_membership": membership}


def _insert_membership(con, *, organization_id: str, user_id: str, role: str, created_by: str) -> dict:
    role = str(role or "").strip().lower()
    if role not in MEMBERSHIP_ROLES:
        raise TenancyError("El rol empresarial no es válido.", code="TENANCY_ROLE_INVALID")
    org = _organization_row(con, organization_id, active_only=True)
    if not org:
        raise TenancyError("La organización no está disponible.", code="ORGANIZATION_NOT_FOUND", status=404)
    user = _user(con, user_id)
    creator = _user(con, created_by)
    existing = con.execute(
        "SELECT id,status FROM enterprise_memberships WHERE organization_id=? AND user_id=?",
        (organization_id, user["id"]),
    ).fetchone()
    if existing:
        code = "MEMBERSHIP_EXISTS" if existing["status"] == ACTIVE else "MEMBERSHIP_INACTIVE"
        message = "El usuario ya tiene una membresía activa." if existing["status"] == ACTIVE else "Existe una membresía inactiva; debe reactivarse de forma explícita."
        raise TenancyError(message, code=code, status=409)
    membership_id = _identifier("MEM")
    timestamp = _now()
    con.execute(
        "INSERT INTO enterprise_memberships(id,organization_id,user_id,role,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
        (membership_id, organization_id, user["id"], role, ACTIVE, creator["id"], timestamp, timestamp),
    )
    return dict(
        con.execute(
            "SELECT id,organization_id,user_id,role,status,created_by,created_at,updated_at FROM enterprise_memberships WHERE id=?",
            (membership_id,),
        ).fetchone()
    )


def add_membership(con, *, organization_id: str, user_id: str, role: str, created_by: str) -> dict:
    ensure_schema(con)
    return _insert_membership(
        con,
        organization_id=str(organization_id),
        user_id=str(user_id),
        role=role,
        created_by=str(created_by),
    )


def membership_for_user(con, organization_id: str, user_id: str, *, active_only: bool = True) -> dict | None:
    ensure_schema(con)
    clauses = ["m.organization_id=?", "m.user_id=?"]
    params = [str(organization_id), str(user_id)]
    if active_only:
        clauses.extend(["m.status='active'", "o.status='active'"])
    row = con.execute(
        f"""SELECT m.id,m.organization_id,m.user_id,m.role,m.status,m.created_by,m.created_at,m.updated_at
            FROM enterprise_memberships m
            JOIN enterprise_organizations o ON o.id=m.organization_id
            WHERE {' AND '.join(clauses)}""",
        params,
    ).fetchone()
    return dict(row) if row else None


def list_user_organizations(con, user_id: str) -> list[dict]:
    ensure_schema(con)
    rows = con.execute(
        """SELECT o.id,o.legal_name,o.display_name,o.tax_id,o.status,o.created_at,o.updated_at,
                  m.id membership_id,m.role membership_role,m.status membership_status
           FROM enterprise_memberships m
           JOIN enterprise_organizations o ON o.id=m.organization_id
           WHERE m.user_id=? AND m.status='active' AND o.status='active'
           ORDER BY lower(o.display_name),o.id""",
        (str(user_id),),
    ).fetchall()
    return [dict(row) for row in rows]


def get_organization_for_user(con, user_id: str, organization_id: str) -> dict | None:
    membership = membership_for_user(con, organization_id, user_id, active_only=True)
    if not membership:
        return None
    organization = get_organization(con, organization_id, active_only=True)
    if not organization:
        return None
    return {"organization": organization, "membership": membership}


def resolve_context(con, user_id: str, organization_id: str = "") -> EnterpriseContext:
    requested = str(organization_id or "").strip()
    if requested:
        pair = get_organization_for_user(con, user_id, requested)
        if not pair:
            # 404 evita confirmar si un tenant ajeno existe.
            raise TenancyError("La organización solicitada no está disponible.", code="ORGANIZATION_NOT_FOUND", status=404)
        return EnterpriseContext(pair["organization"], pair["membership"], "explicit")

    organizations = list_user_organizations(con, user_id)
    if not organizations:
        raise TenancyError(
            "La cuenta no tiene una membresía empresarial activa.",
            code="TENANCY_MEMBERSHIP_REQUIRED",
            status=403,
        )
    if len(organizations) != 1:
        raise TenancyError(
            "Seleccione explícitamente la organización de trabajo.",
            code="ORGANIZATION_CONTEXT_REQUIRED",
            status=409,
        )
    selected = organizations[0]
    pair = get_organization_for_user(con, user_id, selected["id"])
    if not pair:  # defensa ante cambios concurrentes de estado
        raise TenancyError("La organización solicitada no está disponible.", code="ORGANIZATION_NOT_FOUND", status=404)
    return EnterpriseContext(pair["organization"], pair["membership"], "sole_membership")


def list_memberships(con, organization_id: str) -> list[dict]:
    ensure_schema(con)
    if not _organization_row(con, organization_id):
        raise TenancyError("La organización no está disponible.", code="ORGANIZATION_NOT_FOUND", status=404)
    rows = con.execute(
        """SELECT m.id,m.organization_id,m.user_id,m.role,m.status,m.created_by,m.created_at,m.updated_at,
                  u.name user_name,u.email user_email
           FROM enterprise_memberships m
           JOIN users u ON u.id=m.user_id
           WHERE m.organization_id=?
           ORDER BY CASE m.status WHEN 'active' THEN 0 ELSE 1 END,
                    CASE m.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 WHEN 'manager' THEN 2 WHEN 'member' THEN 3 ELSE 4 END,
                    lower(u.name),m.id""",
        (str(organization_id),),
    ).fetchall()
    return [dict(row) for row in rows]


def deactivate_membership(con, *, membership_id: str, changed_by: str) -> dict:
    ensure_schema(con)
    _user(con, changed_by)
    row = con.execute(
        "SELECT id,organization_id,user_id,role,status FROM enterprise_memberships WHERE id=?",
        (str(membership_id),),
    ).fetchone()
    if not row:
        raise TenancyError("La membresía no existe.", code="MEMBERSHIP_NOT_FOUND", status=404)
    if row["status"] != ACTIVE:
        raise TenancyError("La membresía ya está inactiva.", code="MEMBERSHIP_INACTIVE", status=409)
    if row["role"] == "owner":
        owner_count = con.execute(
            "SELECT COUNT(*) FROM enterprise_memberships WHERE organization_id=? AND role='owner' AND status='active'",
            (row["organization_id"],),
        ).fetchone()[0]
        if int(owner_count) <= 1:
            raise TenancyError(
                "No se puede desactivar al último owner activo de la organización.",
                code="TENANCY_LAST_OWNER",
                status=409,
            )
    timestamp = _now()
    con.execute(
        "UPDATE enterprise_memberships SET status='inactive',updated_at=? WHERE id=?",
        (timestamp, row["id"]),
    )
    return dict(
        con.execute(
            "SELECT id,organization_id,user_id,role,status,created_by,created_at,updated_at FROM enterprise_memberships WHERE id=?",
            (row["id"],),
        ).fetchone()
    )


def reactivate_membership(con, *, membership_id: str, role: str, changed_by: str) -> dict:
    ensure_schema(con)
    _user(con, changed_by)
    normalized_role = str(role or "").strip().lower()
    if normalized_role not in MEMBERSHIP_ROLES:
        raise TenancyError("El rol empresarial no es válido.", code="TENANCY_ROLE_INVALID")
    row = con.execute(
        "SELECT id,organization_id,status FROM enterprise_memberships WHERE id=?",
        (str(membership_id),),
    ).fetchone()
    if not row:
        raise TenancyError("La membresía no existe.", code="MEMBERSHIP_NOT_FOUND", status=404)
    if row["status"] == ACTIVE:
        raise TenancyError("La membresía ya está activa.", code="MEMBERSHIP_EXISTS", status=409)
    if not _organization_row(con, row["organization_id"], active_only=True):
        raise TenancyError("La organización no está disponible.", code="ORGANIZATION_NOT_FOUND", status=404)
    timestamp = _now()
    con.execute(
        "UPDATE enterprise_memberships SET status='active',role=?,updated_at=? WHERE id=?",
        (normalized_role, timestamp, row["id"]),
    )
    return dict(
        con.execute(
            "SELECT id,organization_id,user_id,role,status,created_by,created_at,updated_at FROM enterprise_memberships WHERE id=?",
            (row["id"],),
        ).fetchone()
    )


def actor_can_manage_memberships(global_role: str, membership_role: str | None, target_role: str) -> bool:
    """Matriz mínima de delegación; evita escaladas silenciosas de privilegio."""
    target = str(target_role or "").strip().lower()
    if target not in MEMBERSHIP_ROLES:
        return False
    if global_role == "admin":
        return True
    current = str(membership_role or "").strip().lower()
    if current == "owner":
        return target in {"admin", "manager", "member", "viewer"}
    if current == "admin":
        return target in {"manager", "member", "viewer"}
    return False


__all__ = [
    "ACTIVE",
    "INACTIVE",
    "MEMBERSHIP_ROLES",
    "TenancyError",
    "EnterpriseContext",
    "ensure_schema",
    "create_organization",
    "get_organization",
    "add_membership",
    "membership_for_user",
    "list_user_organizations",
    "get_organization_for_user",
    "resolve_context",
    "list_memberships",
    "deactivate_membership",
    "reactivate_membership",
    "actor_can_manage_memberships",
]
