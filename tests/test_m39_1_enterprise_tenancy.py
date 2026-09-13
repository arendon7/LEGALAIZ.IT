from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from legalai_platform.enterprise_tenancy_m39_1 import (
    TenancyError,
    actor_can_manage_memberships,
    add_membership,
    create_organization,
    deactivate_membership,
    ensure_schema,
    get_organization_for_user,
    list_user_organizations,
    membership_for_user,
    reactivate_membership,
    resolve_context,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "run.py"
HANDLER = ROOT / "legalai_platform" / "http_handler_m39_1.py"
ROUTES = ROOT / "legalai_platform" / "routes" / "m39_1_enterprise_routes.py"


class EnterpriseTenancyM391Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.con = sqlite3.connect(":memory:")
        self.con.row_factory = sqlite3.Row
        self.con.execute(
            """CREATE TABLE users(
                   id TEXT PRIMARY KEY,
                   name TEXT NOT NULL,
                   email TEXT,
                   role TEXT NOT NULL,
                   active INTEGER NOT NULL DEFAULT 1
               )"""
        )
        self.con.execute(
            """CREATE TABLE audit_log(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   actor TEXT,
                   entity_type TEXT,
                   entity_id TEXT,
                   action TEXT,
                   detail TEXT,
                   created_at TEXT NOT NULL
               )"""
        )
        self.con.executemany(
            "INSERT INTO users(id,name,email,role,active) VALUES(?,?,?,?,1)",
            [
                ("USR-ADMIN", "Admin", "admin@example.test", "admin"),
                ("USR-U1", "Uno", "uno@example.test", "client"),
                ("USR-U2", "Dos", "dos@example.test", "client"),
                ("USR-U3", "Tres", "tres@example.test", "client"),
            ],
        )
        ensure_schema(self.con)
        self.con.commit()

    def tearDown(self) -> None:
        self.con.close()

    def _org(self, owner: str, legal_name: str) -> dict:
        result = create_organization(
            self.con,
            legal_name=legal_name,
            owner_user_id=owner,
            created_by="USR-ADMIN",
        )
        self.con.commit()
        return result

    def assertTenancyError(self, code: str, status: int, fn, *args, **kwargs) -> TenancyError:
        with self.assertRaises(TenancyError) as captured:
            fn(*args, **kwargs)
        self.assertEqual(captured.exception.code, code)
        self.assertEqual(captured.exception.status, status)
        return captured.exception

    def test_organization_creation_always_creates_explicit_owner_membership(self):
        created = self._org("USR-U1", "Acme S.A.S.")
        organization = created["organization"]
        membership = created["owner_membership"]
        self.assertEqual(membership["organization_id"], organization["id"])
        self.assertEqual(membership["user_id"], "USR-U1")
        self.assertEqual(membership["role"], "owner")
        self.assertEqual(membership["status"], "active")

    def test_user_lists_only_organizations_with_active_membership(self):
        org1 = self._org("USR-U1", "Empresa Uno")["organization"]
        org2 = self._org("USR-U2", "Empresa Dos")["organization"]
        visible = list_user_organizations(self.con, "USR-U1")
        self.assertEqual([item["id"] for item in visible], [org1["id"]])
        self.assertNotIn(org2["id"], {item["id"] for item in visible})

    def test_foreign_organization_is_not_resolvable_by_guessed_id(self):
        foreign = self._org("USR-U2", "Empresa Ajena")["organization"]
        self.assertIsNone(get_organization_for_user(self.con, "USR-U1", foreign["id"]))
        self.assertTenancyError(
            "ORGANIZATION_NOT_FOUND",
            404,
            resolve_context,
            self.con,
            "USR-U1",
            foreign["id"],
        )

    def test_single_active_membership_resolves_automatically(self):
        org = self._org("USR-U1", "Empresa Única")["organization"]
        context = resolve_context(self.con, "USR-U1")
        self.assertEqual(context.organization["id"], org["id"])
        self.assertEqual(context.membership["role"], "owner")
        self.assertEqual(context.source, "sole_membership")

    def test_multiple_memberships_require_explicit_context(self):
        first = self._org("USR-U1", "Primera")["organization"]
        second = self._org("USR-U2", "Segunda")["organization"]
        add_membership(
            self.con,
            organization_id=second["id"],
            user_id="USR-U1",
            role="member",
            created_by="USR-U2",
        )
        self.con.commit()
        self.assertTenancyError(
            "ORGANIZATION_CONTEXT_REQUIRED",
            409,
            resolve_context,
            self.con,
            "USR-U1",
        )
        explicit = resolve_context(self.con, "USR-U1", first["id"])
        self.assertEqual(explicit.organization["id"], first["id"])
        self.assertEqual(explicit.source, "explicit")

    def test_account_without_membership_fails_closed(self):
        self.assertTenancyError(
            "TENANCY_MEMBERSHIP_REQUIRED",
            403,
            resolve_context,
            self.con,
            "USR-U3",
        )

    def test_duplicate_active_membership_is_rejected(self):
        org = self._org("USR-U1", "Duplicados")["organization"]
        self.assertTenancyError(
            "MEMBERSHIP_EXISTS",
            409,
            add_membership,
            self.con,
            organization_id=org["id"],
            user_id="USR-U1",
            role="member",
            created_by="USR-ADMIN",
        )

    def test_inactive_membership_is_excluded_and_requires_explicit_reactivation(self):
        org = self._org("USR-U1", "Control de membresía")["organization"]
        added = add_membership(
            self.con,
            organization_id=org["id"],
            user_id="USR-U2",
            role="member",
            created_by="USR-U1",
        )
        self.con.commit()
        inactive = deactivate_membership(self.con, membership_id=added["id"], changed_by="USR-U1")
        self.con.commit()
        self.assertEqual(inactive["status"], "inactive")
        self.assertIsNone(membership_for_user(self.con, org["id"], "USR-U2", active_only=True))
        self.assertEqual(list_user_organizations(self.con, "USR-U2"), [])
        self.assertTenancyError(
            "MEMBERSHIP_INACTIVE",
            409,
            add_membership,
            self.con,
            organization_id=org["id"],
            user_id="USR-U2",
            role="member",
            created_by="USR-U1",
        )
        active = reactivate_membership(
            self.con,
            membership_id=added["id"],
            role="viewer",
            changed_by="USR-U1",
        )
        self.con.commit()
        self.assertEqual(active["status"], "active")
        self.assertEqual(active["role"], "viewer")
        self.assertEqual(resolve_context(self.con, "USR-U2").organization["id"], org["id"])

    def test_last_active_owner_cannot_be_deactivated(self):
        created = self._org("USR-U1", "Continuidad de gobierno")
        self.assertTenancyError(
            "TENANCY_LAST_OWNER",
            409,
            deactivate_membership,
            self.con,
            membership_id=created["owner_membership"]["id"],
            changed_by="USR-ADMIN",
        )

    def test_suspended_organization_disappears_from_active_context(self):
        org = self._org("USR-U1", "Suspendida")["organization"]
        self.con.execute(
            "UPDATE enterprise_organizations SET status='suspended' WHERE id=?",
            (org["id"],),
        )
        self.con.commit()
        self.assertEqual(list_user_organizations(self.con, "USR-U1"), [])
        self.assertTenancyError(
            "ORGANIZATION_NOT_FOUND",
            404,
            resolve_context,
            self.con,
            "USR-U1",
            org["id"],
        )

    def test_membership_permission_matrix_prevents_silent_privilege_escalation(self):
        self.assertTrue(actor_can_manage_memberships("admin", None, "owner"))
        self.assertTrue(actor_can_manage_memberships("client", "owner", "admin"))
        self.assertFalse(actor_can_manage_memberships("client", "owner", "owner"))
        self.assertTrue(actor_can_manage_memberships("client", "admin", "manager"))
        self.assertFalse(actor_can_manage_memberships("client", "admin", "admin"))
        self.assertFalse(actor_can_manage_memberships("client", "manager", "viewer"))
        self.assertFalse(actor_can_manage_memberships("client", "member", "member"))

    def test_runtime_activates_m39_1_as_incremental_handler(self):
        run_source = RUN.read_text(encoding="utf-8")
        handler_source = HANDLER.read_text(encoding="utf-8")
        routes_source = ROUTES.read_text(encoding="utf-8")
        self.assertIn("from legalai_platform.http_handler_m39_1 import Handler", run_source)
        self.assertIn("from legalai_platform.http_handler_m37_3 import Handler as BaseHandler", handler_source)
        self.assertIn("return super().do_GET()", handler_source)
        self.assertIn("return super().do_POST()", handler_source)
        self.assertIn('PREFIX = "/api/enterprise"', routes_source)
        self.assertIn("X-Organization-Id", routes_source)
        self.assertIn("require_csrf", handler_source)
        self.assertIn("require_origin", handler_source)


if __name__ == "__main__":
    unittest.main()
