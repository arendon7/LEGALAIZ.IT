from __future__ import annotations

import re

import core_v11 as core
from legalai_platform.enterprise_tenancy_m39_1 import (
    TenancyError,
    actor_can_manage_memberships,
    add_membership,
    create_organization,
    deactivate_membership,
    ensure_schema,
    get_organization,
    get_organization_for_user,
    list_memberships,
    list_user_organizations,
    membership_for_user,
    reactivate_membership,
    resolve_context,
)


PREFIX = "/api/enterprise"
_ORG_RE = re.compile(r"^/api/enterprise/organizations/([^/]+)$")
_MEMBERS_RE = re.compile(r"^/api/enterprise/organizations/([^/]+)/memberships$")
_MEMBERSHIP_ACTION_RE = re.compile(r"^/api/enterprise/organizations/([^/]+)/memberships/([^/]+)/(deactivate|reactivate)$")


def _organization_header(handler) -> str:
    return str(handler.headers.get("X-Organization-Id") or "").strip()


def _actor_membership(con, user: dict, organization_id: str) -> dict | None:
    return membership_for_user(con, organization_id, user["id"], active_only=True)


def _visible_organization(con, user: dict, organization_id: str) -> dict | None:
    if user.get("role") == "admin":
        organization = get_organization(con, organization_id, active_only=True)
        return {"organization": organization, "membership": None} if organization else None
    return get_organization_for_user(con, user["id"], organization_id)


def _require_management(con, user: dict, organization_id: str, target_role: str = "member") -> dict | None:
    if user.get("role") == "admin":
        return {"global_admin": True, "membership": None}
    membership = _actor_membership(con, user, organization_id)
    if not membership:
        return None
    if not actor_can_manage_memberships(user.get("role", ""), membership.get("role"), target_role):
        raise TenancyError("No tiene permisos para administrar estas membresías.", code="TENANCY_FORBIDDEN", status=403)
    return {"global_admin": False, "membership": membership}


def _send_error(handler, exc: TenancyError):
    return handler.send_json(exc.public(), exc.status)


def _audit(con, user: dict, organization_id: str, action: str, detail: dict) -> None:
    core.audit(
        con,
        user.get("id"),
        "enterprise_organization",
        organization_id,
        action,
        detail,
    )


def handle_m39_1_enterprise_get(handler, path: str, user: dict):
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    con = core.db()
    try:
        ensure_schema(con)
        if path == PREFIX:
            return handler.send_json({
                "milestone": "M39.1",
                "capabilities": ["organizations", "memberships", "enterprise_context"],
            })
        if path == PREFIX + "/organizations":
            return handler.send_json({"organizations": list_user_organizations(con, user["id"])})
        if path == PREFIX + "/context":
            context = resolve_context(con, user["id"], _organization_header(handler))
            return handler.send_json(context.public())

        match = _MEMBERS_RE.fullmatch(path)
        if match:
            organization_id = match.group(1)
            visible = _visible_organization(con, user, organization_id)
            if not visible:
                raise TenancyError("La organización solicitada no está disponible.", code="ORGANIZATION_NOT_FOUND", status=404)
            if user.get("role") != "admin":
                membership = visible.get("membership") or {}
                if membership.get("role") not in {"owner", "admin"}:
                    raise TenancyError("No tiene permisos para consultar las membresías.", code="TENANCY_FORBIDDEN", status=403)
            return handler.send_json({
                "organization": visible["organization"],
                "memberships": list_memberships(con, organization_id),
            })

        match = _ORG_RE.fullmatch(path)
        if match:
            visible = _visible_organization(con, user, match.group(1))
            if not visible:
                raise TenancyError("La organización solicitada no está disponible.", code="ORGANIZATION_NOT_FOUND", status=404)
            return handler.send_json(visible)

        return handler.send_json({"error": "Ruta empresarial no encontrada.", "code": "NOT_FOUND"}, 404)
    except TenancyError as exc:
        return _send_error(handler, exc)
    finally:
        con.close()


def handle_m39_1_enterprise_post(handler, path: str, user: dict):
    if not (path == PREFIX or path.startswith(PREFIX + "/")):
        return False
    con = core.db()
    try:
        ensure_schema(con)
        try:
            payload = handler.read_json()
        except Exception:
            return handler.send_json({"error": "JSON inválido.", "code": "INVALID_JSON"}, 400)

        if path == PREFIX + "/organizations":
            if user.get("role") != "admin":
                raise TenancyError("Solo administración puede crear organizaciones en M39.1.", code="TENANCY_FORBIDDEN", status=403)
            result = create_organization(
                con,
                legal_name=payload.get("legal_name", ""),
                display_name=payload.get("display_name", ""),
                tax_id=payload.get("tax_id", ""),
                owner_user_id=payload.get("owner_user_id", ""),
                created_by=user["id"],
            )
            organization = result["organization"]
            owner_membership = result["owner_membership"]
            _audit(
                con,
                user,
                organization["id"],
                "enterprise.organization.created",
                {
                    "owner_user_id": owner_membership["user_id"],
                    "owner_membership_id": owner_membership["id"],
                },
            )
            con.commit()
            return handler.send_json(result, 201)

        match = _MEMBERS_RE.fullmatch(path)
        if match:
            organization_id = match.group(1)
            role = str(payload.get("role") or "member").strip().lower()
            management = _require_management(con, user, organization_id, role)
            if not management:
                raise TenancyError("La organización solicitada no está disponible.", code="ORGANIZATION_NOT_FOUND", status=404)
            membership = add_membership(
                con,
                organization_id=organization_id,
                user_id=payload.get("user_id", ""),
                role=role,
                created_by=user["id"],
            )
            _audit(
                con,
                user,
                organization_id,
                "enterprise.membership.created",
                {
                    "membership_id": membership["id"],
                    "user_id": membership["user_id"],
                    "role": membership["role"],
                },
            )
            con.commit()
            return handler.send_json({"membership": membership}, 201)

        match = _MEMBERSHIP_ACTION_RE.fullmatch(path)
        if match:
            organization_id, membership_id, action = match.groups()
            memberships = list_memberships(con, organization_id)
            target = next((item for item in memberships if item["id"] == membership_id), None)
            if not target:
                raise TenancyError("La membresía no existe.", code="MEMBERSHIP_NOT_FOUND", status=404)
            management = _require_management(con, user, organization_id, target.get("role", "member"))
            if not management:
                raise TenancyError("La organización solicitada no está disponible.", code="ORGANIZATION_NOT_FOUND", status=404)
            if action == "deactivate":
                membership = deactivate_membership(con, membership_id=membership_id, changed_by=user["id"])
                audit_action = "enterprise.membership.deactivated"
            else:
                role = str(payload.get("role") or target.get("role") or "member").strip().lower()
                if not actor_can_manage_memberships(user.get("role", ""), (management.get("membership") or {}).get("role"), role) and user.get("role") != "admin":
                    raise TenancyError("No puede asignar ese rol empresarial.", code="TENANCY_FORBIDDEN", status=403)
                membership = reactivate_membership(con, membership_id=membership_id, role=role, changed_by=user["id"])
                audit_action = "enterprise.membership.reactivated"
            _audit(
                con,
                user,
                organization_id,
                audit_action,
                {
                    "membership_id": membership["id"],
                    "user_id": membership["user_id"],
                    "role": membership["role"],
                    "status": membership["status"],
                },
            )
            con.commit()
            return handler.send_json({"membership": membership})

        return handler.send_json({"error": "Ruta empresarial no encontrada.", "code": "NOT_FOUND"}, 404)
    except TenancyError as exc:
        try:
            con.rollback()
        except Exception:
            pass
        return _send_error(handler, exc)
    finally:
        con.close()


__all__ = ["PREFIX", "handle_m39_1_enterprise_get", "handle_m39_1_enterprise_post"]
