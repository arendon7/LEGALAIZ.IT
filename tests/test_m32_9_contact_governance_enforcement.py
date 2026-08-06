from __future__ import annotations

from hashlib import sha256
from unittest import TestCase

from legalai_platform.approval_desk_workspace import ApprovalDeskError, PermissionDenied
from legalai_platform.contact_governance import ContactGovernanceIntegrityError
from legalai_platform.contact_governance_enforcement import (
    EnforcedContactGovernance,
    EnforcedGovernedTransactionalCommunications,
)
from legalai_platform.transactional_communications import CommunicationsIntegrityError
from tests.test_m32_9_contact_governance import ContactGovernanceM329Tests


class ContactGovernanceEnforcementM329Tests(TestCase):
    def setUp(self):
        self.fixture = ContactGovernanceM329Tests(methodName="test_alerta_profesional_es_permitida_y_supresion_la_bloquea")
        self.fixture.setUp()
        self.governance = EnforcedContactGovernance(
            self.fixture.root / "approval-desk",
            db_factory=self.fixture.db,
            now_factory=lambda: self.fixture.fixed_now,
        )
        self.communications = EnforcedGovernedTransactionalCommunications(
            self.fixture.root / "approval-desk",
            notification_center=self.fixture.center,
            db_factory=self.fixture.db,
            now_factory=lambda: self.fixture.fixed_now,
            governance=self.governance,
        )

    def tearDown(self):
        self.fixture.tearDown()

    def test_contacto_queda_vinculado_a_decision_y_despacho_exactos(self):
        decision = self.governance.evaluate(
            self.fixture.admin,
            subject_id="USR-LEGAL",
            purpose="professional_operational",
            channel="email",
            context_reference="DSP-EXACT-001",
        )["decision"]
        with self.assertRaises(ApprovalDeskError):
            self.governance.record_contact(
                self.fixture.admin,
                decision_id=decision["decision_id"],
                subject_id="USR-OTHER",
                purpose="professional_operational",
                channel="email",
                dispatch_id="DSP-EXACT-001",
            )
        with self.assertRaises(ApprovalDeskError):
            self.governance.record_contact(
                self.fixture.admin,
                decision_id=decision["decision_id"],
                subject_id="USR-LEGAL",
                purpose="professional_operational",
                channel="email",
                dispatch_id="DSP-DIFFERENT-001",
            )
        result = self.governance.record_contact(
            self.fixture.admin,
            decision_id=decision["decision_id"],
            subject_id="USR-LEGAL",
            purpose="professional_operational",
            channel="email",
            dispatch_id="DSP-EXACT-001",
        )
        self.assertEqual(result["contact"]["decision_id"], decision["decision_id"])
        self.assertEqual(
            decision["context_sha256"],
            sha256(b"DSP-EXACT-001").hexdigest(),
        )
        with self.assertRaises(ApprovalDeskError):
            self.governance.record_contact(
                self.fixture.admin,
                decision_id=decision["decision_id"],
                subject_id="USR-LEGAL",
                purpose="professional_operational",
                channel="email",
                dispatch_id="DSP-EXACT-001",
            )

    def test_especialista_no_evalua_ni_enumera_titulares_ajenos(self):
        with self.assertRaises(PermissionDenied):
            self.governance.evaluate(
                self.fixture.legal,
                subject_id="USR-OTHER",
                purpose="professional_operational",
                channel="email",
                context_reference="DSP-FOREIGN-001",
            )
        with self.assertRaises(PermissionDenied):
            self.governance.evaluate(
                self.fixture.legal,
                subject_id="USR-NOT-FOUND",
                purpose="professional_operational",
                channel="email",
                context_reference="DSP-UNKNOWN-001",
            )
        with self.assertRaises(PermissionDenied):
            self.governance.record_relationship(self.fixture.legal, {
                "subject_id": "USR-NOT-FOUND",
                "relationship_type": "client",
                "lawful_basis": "contract",
                "status": "active",
                "evidence_reference": "EVIDENCE-UNKNOWN",
            })

    def test_relacion_y_preferencia_rechazan_titular_inexistente(self):
        with self.assertRaises(ApprovalDeskError):
            self.governance.record_relationship(self.fixture.admin, {
                "subject_id": "USR-NOT-FOUND",
                "relationship_type": "client",
                "lawful_basis": "contract",
                "status": "active",
                "evidence_reference": "EVIDENCE-UNKNOWN",
            })
        with self.assertRaises(ApprovalDeskError):
            self.governance.record_preference(self.fixture.admin, {
                "subject_id": "USR-NOT-FOUND",
                "purpose": "commercial_marketing",
                "channel": "email",
                "state": "granted",
                "basis": "consent",
                "evidence_reference": "CONSENT-UNKNOWN",
            })

    def test_decision_bloquea_titular_inactivo(self):
        con = self.fixture.db()
        con.execute("UPDATE users SET active=0 WHERE id='USR-LEGAL'")
        con.commit(); con.close()
        decision = self.governance.evaluate(
            self.fixture.admin,
            subject_id="USR-LEGAL",
            purpose="professional_operational",
            channel="email",
            context_reference="DSP-INACTIVE-001",
        )["decision"]
        self.assertFalse(decision["allowed"])
        self.assertIn("inactive_or_unknown_subject", decision["reasons"])

    def test_metricas_del_especialista_no_revelan_totales_ajenos(self):
        self.governance.record_relationship(self.fixture.admin, {
            "subject_id": "USR-CLIENT",
            "relationship_type": "client",
            "lawful_basis": "contract",
            "status": "active",
            "evidence_reference": "CLIENT-EVIDENCE",
        })
        admin_dashboard = self.governance.dashboard(self.fixture.admin)
        specialist_dashboard = self.governance.dashboard(self.fixture.legal)
        self.assertEqual(admin_dashboard["metrics"]["relationships"], 1)
        self.assertEqual(specialist_dashboard["metrics"]["relationships"], 0)
        self.assertEqual(specialist_dashboard["metrics"]["synthetic_contacts"], 0)

    def test_procesamiento_falla_cerrado_si_m32_8_esta_alterada(self):
        self.fixture.prepare_outbox()
        self.communications.sync_outbox(self.fixture.admin)
        path = self.fixture.root / "approval-desk" / "transactional-communications" / "events.jsonl"
        path.write_text(
            path.read_text(encoding="utf-8").replace('"dispatch.imported"', '"dispatch.altered"', 1),
            encoding="utf-8",
        )
        with self.assertRaises(CommunicationsIntegrityError):
            self.communications.process(self.fixture.admin)
        self.assertEqual(self.governance.verify_chain()["events"], 0)

    def test_procesamiento_falla_cerrado_si_m32_9_esta_alterada(self):
        self.governance.evaluate(
            self.fixture.admin,
            subject_id="USR-LEGAL",
            purpose="professional_operational",
            channel="email",
            context_reference="DSP-AUDIT-001",
        )
        path = self.fixture.root / "approval-desk" / "contact-governance" / "events.jsonl"
        path.write_text(
            path.read_text(encoding="utf-8").replace('"decision.recorded"', '"decision.altered"', 1),
            encoding="utf-8",
        )
        with self.assertRaises(ContactGovernanceIntegrityError):
            self.communications.process(self.fixture.admin)


class ContactGovernanceEnforcementStaticM329Tests(TestCase):
    def test_rutas_usan_implementacion_reforzada(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        governance_routes = (
            root / "legalai_platform" / "routes" / "m32_9_contact_governance_routes.py"
        ).read_text(encoding="utf-8")
        communication_routes = (
            root / "legalai_platform" / "routes" / "m32_8_transactional_communications_routes.py"
        ).read_text(encoding="utf-8")
        self.assertIn("EnforcedContactGovernance", governance_routes)
        self.assertIn("EnforcedGovernedTransactionalCommunications", communication_routes)
