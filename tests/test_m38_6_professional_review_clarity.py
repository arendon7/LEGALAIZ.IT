from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "app" / "modules" / "professional_review_m38_6.js"
STYLE = ROOT / "app" / "modules" / "professional_review_m38_6.css"
INDEX = ROOT / "app" / "index.html"
APPROVAL = ROOT / "app" / "modules" / "approval_desk_m32_5.js"
OPERATIONS = ROOT / "app" / "modules" / "approval_operations_m32_6.js"


class M386ProfessionalReviewClarityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MODULE.read_text(encoding="utf-8")
        cls.style = STYLE.read_text(encoding="utf-8")
        cls.index = INDEX.read_text(encoding="utf-8")
        cls.approval = APPROVAL.read_text(encoding="utf-8")
        cls.operations = OPERATIONS.read_text(encoding="utf-8")

    def test_module_and_style_are_loaded_after_existing_approval_layers(self):
        self.assertIn('professional_review_m38_6.css', self.index)
        self.assertIn('professional_review_m38_6.js', self.index)
        self.assertGreater(self.index.index('professional_review_m38_6.js'), self.index.index('approval_operations_m32_6.js'))
        self.assertGreater(self.index.index('professional_review_m38_6.js'), self.index.index('client_home_m38_5.js'))

    def test_overlay_is_professional_only_and_route_scoped(self):
        self.assertIn("['specialist', 'admin'].includes(state.user.role)", self.source)
        self.assertIn("currentPath().startsWith(ROUTE)", self.source)
        self.assertEqual(self.source.count("const ROUTE = '/mesa-juridica';"), 1)

    def test_overlay_has_no_backend_or_storage_channel(self):
        for token in ('api(', 'fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'indexedDB'):
            self.assertNotIn(token, self.source)

    def test_overlay_does_not_mutate_application_state(self):
        self.assertIsNone(re.search(r"\bstate\.[A-Za-z0-9_]+\s*=", self.source))
        self.assertNotIn('state.cases.push', self.source)
        self.assertNotIn('state.documents.push', self.source)

    def test_overlay_does_not_execute_approval_or_release_actions(self):
        for token in ('data-m325-action="approve"', 'data-m325-action="release"', "method:'POST'", 'method: "POST"'):
            self.assertNotIn(token, self.source)
        self.assertNotIn('/released-download', self.source)

    def test_all_professional_workflow_states_have_decision_cues(self):
        for status in ('draft', 'legal_pending', 'qa_pending', 'changes_required', 'findings_pending', 'audit_invalid', 'ready_to_release', 'released', 'rejected'):
            self.assertIn(f'{status}: {{', self.source)
        self.assertIn('Siguiente control profesional', self.source)
        self.assertIn('Bloqueo de aprobación', self.source)
        self.assertIn('Bloqueo de integridad', self.source)

    def test_technical_traceability_remains_visible(self):
        self.assertIn('Huella SHA-256', self.source)
        self.assertIn('revisión', self.source.lower())
        self.assertIn('hallazgos', self.source.lower())
        self.assertIn('cadena de auditoría', self.source.lower())
        self.assertIn('SHA-256', self.approval)

    def test_list_hierarchy_leads_with_decision_not_internal_version(self):
        self.assertIn('Revisión profesional por documento', self.source)
        self.assertIn('Identifica primero la decisión pendiente o el bloqueo.', self.source)
        self.assertNotIn('M38.6 ·', self.source)

    def test_operational_sla_is_relabelled_as_internal_objective(self):
        for token in ('Objetivos internos vencidos', 'Objetivos internos próximos', 'Horas objetivo', 'Fecha objetivo interna', 'Definir objetivo interno'):
            self.assertIn(token, self.source)
        self.assertIn('sla-overdue', self.source)
        self.assertIn('Objetivo interno vencido', self.source)

    def test_operational_copy_disclaims_legal_deadline_calculation(self):
        copy = self.source.lower()
        for token in ('no son términos legales', 'prescripción', 'caducidad', 'términos procesales', 'administrativos aplicables'):
            self.assertIn(token, copy)
        self.assertNotIn('término legal calculado', copy)
        self.assertNotIn('urgencia jurídica', copy)

    def test_label_copy_change_preserves_form_controls(self):
        helper = self.source.split('function replaceLeadingText', 1)[1].split('function enhanceList', 1)[0]
        self.assertIn('childNodes', helper)
        self.assertIn('Node.TEXT_NODE', helper)
        self.assertIn('textNode.textContent = replacement', helper)
        self.assertNotIn('node.innerHTML', helper)
        self.assertNotIn('node.textContent = replacement', helper)

    def test_existing_m32_5_and_m32_6_remain_sources_of_truth(self):
        self.assertIn("const BASE = '/api/m32/approval-desk';", self.approval)
        self.assertIn("const BASE = '/api/m32/approval-operations';", self.operations)
        self.assertIn('expected_sha256', self.approval)
        self.assertIn('capabilities', self.operations)
        self.assertNotIn("const BASE = '/api/m32", self.source)

    def test_overlay_is_idempotent_under_rerenders(self):
        self.assertIn("data-m386-cue=", self.source)
        self.assertIn("dataset.m386Hierarchy !== '1'", self.source)
        self.assertIn("dataset.m386Operational === '1'", self.source)
        self.assertIn('let scheduled = false;', self.source)
        self.assertIn('queueMicrotask', self.source)

    def test_css_does_not_hide_technical_evidence(self):
        compact = self.style.replace(' ', '')
        self.assertNotIn('display:none', compact)
        self.assertNotIn('visibility:hidden', compact)
        self.assertIn('.m386-technical-facts', self.style)
        self.assertIn('.m386-technical-integrity', self.style)

    def test_mobile_decision_cue_has_single_column_fallback(self):
        self.assertIn('@media(max-width:760px)', self.style)
        self.assertIn('grid-template-columns:1fr', self.style)


if __name__ == '__main__':
    unittest.main()
