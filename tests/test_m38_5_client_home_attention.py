from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "app" / "modules" / "client_home_m38_5.js"
INTERNAL = ROOT / "app" / "modules" / "internal_m29_2.js"
INDEX = ROOT / "app" / "index.html"


class M385ClientHomeAttentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MODULE.read_text(encoding="utf-8")
        cls.internal = INTERNAL.read_text(encoding="utf-8")
        cls.index = INDEX.read_text(encoding="utf-8")

    def test_module_is_loaded_after_m38_4(self):
        self.assertIn('client_home_m38_5.js', self.index)
        self.assertGreater(
            self.index.index('client_home_m38_5.js'),
            self.index.index('client_followup_m38_4.js'),
        )

    def test_delivery_is_not_classified_as_closed(self):
        self.assertIn('const closedPattern = /cerrado|finalizado/i;', self.internal)
        self.assertNotIn('cerrado|finalizado|entregado', self.internal)
        self.assertIn("key:'delivered', label:'Documentos entregados'", self.internal)

    def test_followup_has_its_own_state(self):
        self.assertIn("key:'followup', label:'En seguimiento'", self.internal)
        self.assertIn("tab:'seguimiento', button:'Ver seguimiento'", self.internal)

    def test_priority_is_operational_not_risk_scoring(self):
        expected = [
            'ready: 600',
            'delivered: 550',
            'followup: 520',
            'active: 500',
            'document: 400',
            'review: 300',
            'closed: 0',
        ]
        positions = [self.source.index(token) for token in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('risk:', self.source.split('STAGE_PRIORITY', 1)[1].split('});', 1)[0])

    def test_priority_tiebreaks_by_recency_then_stable_key(self):
        self.assertIn('if (a.priority !== b.priority) return b.priority - a.priority;', self.source)
        self.assertIn('if (a.updatedAt !== b.updatedAt) return b.updatedAt - a.updatedAt;', self.source)
        self.assertIn("return a.stableKey.localeCompare(b.stableKey, 'es');", self.source)

    def test_open_count_uses_friendly_state_not_raw_regex(self):
        summary = self.source.split('export function clientHomeSummary', 1)[1].split('function productMap', 1)[0]
        self.assertIn("stage.key !== 'closed'", summary)
        self.assertIn("stage.key === 'review'", summary)
        self.assertNotIn('/cerrado', summary)

    def test_priority_card_uses_first_non_closed_case(self):
        self.assertIn("const open = ordered.filter(item => friendlyCaseState(item).key !== 'closed');", self.source)
        self.assertIn('const priority = open[0] || null;', self.source)
        self.assertIn('data-m385-priority-case', self.source)

    def test_recent_cases_use_same_deterministic_order(self):
        self.assertIn("ordered.slice(0, 4).map(item => caseCard", self.source)
        self.assertIn('Ordenados por la etapa que puedes continuar', self.source)

    def test_module_is_client_only(self):
        self.assertGreaterEqual(self.source.count("state.user?.role !== 'client'"), 3)

    def test_module_has_no_backend_or_browser_storage_channel(self):
        forbidden = ['api(', 'fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'indexedDB']
        for token in forbidden:
            self.assertNotIn(token, self.source)

    def test_module_does_not_mutate_application_state(self):
        self.assertIsNone(re.search(r"\bstate\.[A-Za-z0-9_]+\s*=", self.source))
        self.assertNotIn('state.cases.push', self.source)
        self.assertNotIn('state.cases.splice', self.source)

    def test_client_sidebar_copy_removes_release_language(self):
        self.assertIn('Contenido jurídico controlado', self.source)
        self.assertIn('requiere revisión profesional', self.source)
        for token in ('11/11', 'productos revalidados', 'compuertas pendientes'):
            self.assertNotIn(token, self.source)

    def test_real_account_copy_does_not_tell_client_to_use_fake_data(self):
        self.assertIn('const localDemo =', self.source)
        self.assertIn('if (localDemo) return;', self.source)
        self.assertIn('Acceso controlado.', self.source)
        self.assertIn('permisos por rol y trazabilidad', self.source)

    def test_home_copy_does_not_claim_legal_urgency(self):
        lowered = self.source.lower()
        for token in ('urgencia jurídica', 'prioridad legal', 'vence hoy', 'término legal calculado'):
            self.assertNotIn(token, lowered)
        self.assertIn('Lo más útil para continuar', self.source)

    def test_old_followup_copy_marks_dates_as_operational(self):
        self.assertIn('Fechas relevantes y recordatorios operativos.', self.internal)
        self.assertIn('no sustituyen la verificación de términos legales aplicables', self.internal)

    def test_filters_keep_followup_active_and_delivered_ready(self):
        self.assertIn("['active','document','followup'].includes(key)", self.internal)
        self.assertIn("['ready','delivered'].includes(key)", self.internal)
        self.assertIn("if (filter === 'Finalizados') return key === 'closed';", self.internal)

    def test_observer_is_idempotent_by_fingerprint(self):
        self.assertIn('page.dataset.m385Fingerprint === fingerprint', self.source)
        self.assertIn('page.dataset.m385Fingerprint = fingerprint', self.source)
        self.assertIn('let scheduled = false;', self.source)
        self.assertIn('queueMicrotask', self.source)


if __name__ == '__main__':
    unittest.main()
