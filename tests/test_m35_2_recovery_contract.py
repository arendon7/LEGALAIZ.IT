from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M352RecoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = (ROOT / "legalai_platform" / "routes" / "m35_2_commerce_routes.py").read_text(encoding="utf-8")
        cls.store = (ROOT / "legalai_platform" / "commerce_case_m35_2.py").read_text(encoding="utf-8")
        cls.frontend = (ROOT / "app" / "modules" / "commerce_case_m35_2.js").read_text(encoding="utf-8")

    def test_pending_case_is_resumed_from_same_durable_case_snapshot(self):
        self.assertIn('public.get("state") != "CASE_CREATED_DOCUMENTS_PENDING"', self.routes)
        self.assertIn("_pending_case_snapshot(", self.routes)
        self.assertIn('public["case_id"]', self.routes)
        self.assertIn('public["resumed"] = True', self.routes)
        self.assertIn("WHERE id=? AND owner_id=?", self.routes)

    def test_retry_reuses_committed_documents_instead_of_creating_versions_again(self):
        generation = self.routes.index("documents = core.generate_case_documents(")
        guard = self.routes.rfind("if existing_documents < 1:", 0, generation)
        reuse = self.routes.index("documents_count = existing_documents", generation)
        self.assertGreaterEqual(guard, 0)
        self.assertLess(guard, generation)
        self.assertGreater(reuse, generation)
        self.assertIn("SELECT COUNT(*) FROM documents WHERE case_id=? AND kind!='audit'", self.routes)

    def test_m24_generated_state_is_reconciled_only_after_document_guard(self):
        finalize_start = self.store.index("def finalize_case_record")
        materialized_start = self.store.index("def mark_materialized")
        finalize_segment = self.store[finalize_start:materialized_start]
        materialized_segment = self.store[materialized_start:]
        self.assertIn("CASE_CREATED_DOCUMENTS_PENDING", finalize_segment)
        self.assertNotIn("bootstrap_paid_generation", finalize_segment)
        self.assertIn('if int(documents_count or 0) < 1:', materialized_segment)
        self.assertIn("bootstrap_paid_generation", materialized_segment)
        self.assertLess(
            materialized_segment.index('if int(documents_count or 0) < 1:'),
            materialized_segment.index("bootstrap_paid_generation"),
        )

    def test_reconciliation_reverifies_signed_payment_and_never_opens_second_case(self):
        materialized = self.store[self.store.index("def mark_materialized"):]
        self.assertIn("_verify_payment_evidence", materialized)
        self.assertIn('PAID_ORDER_STATUSES | {"Completada"}', materialized)
        self.assertIn("CASE_TRACE_BROKEN", materialized)
        self.assertNotIn("INSERT INTO cases", materialized)
        retry_branch = self.routes[
            self.routes.index('if public.get("idempotent"):'):
            self.routes.index("case_id = public[\"case_id\"]")
        ]
        self.assertNotIn("/api/cases", retry_branch)
        self.assertNotIn("create_case", retry_branch)

    def test_frontend_never_embeds_pending_marker_inside_case_id(self):
        self.assertNotIn("?m352_documents=pending", self.frontend)
        self.assertIn("location.hash = `#/caso/${encodeURIComponent(finalized.case_id)}`", self.frontend)
        self.assertIn("PENDING_DOCUMENTS_STATE = 'CASE_CREATED_DOCUMENTS_PENDING'", self.frontend)

    def test_frontend_pending_state_offers_retry_before_completed_case_redirect(self):
        self.assertIn("data-m352-retry-finalize", self.frontend)
        self.assertIn("Reintentar preparación de documentos", self.frontend)
        pending_branch = "if (link.state === PENDING_DOCUMENTS_STATE) return retryPendingDocuments(link);"
        completed_branch = "if (order.status === 'Completada' && order.case_id) return go(`/caso/${encodeURIComponent(order.case_id)}`);"
        self.assertIn(pending_branch, self.frontend)
        self.assertIn(completed_branch, self.frontend)
        self.assertLess(self.frontend.index(pending_branch), self.frontend.index(completed_branch))
        retry_start = self.frontend.index("async function retryPendingDocuments")
        retry_end = self.frontend.index("async function tracedPayOrFinalize", retry_start)
        retry = self.frontend[retry_start:retry_end]
        self.assertIn("FINALIZE_PATH", retry)
        self.assertIn("finalized.documents_ready === false", retry)
        self.assertIn("finishIntoCase(link, finalized)", retry)


if __name__ == "__main__":
    unittest.main()
