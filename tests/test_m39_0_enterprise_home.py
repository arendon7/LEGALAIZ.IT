from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "app" / "modules" / "enterprise_home_m39_0.js"
INDEX = ROOT / "app" / "index.html"


class M390EnterpriseHomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MODULE.read_text(encoding="utf-8")
        cls.index = INDEX.read_text(encoding="utf-8")

    def test_home_module_is_loaded_after_enterprise_shell(self):
        self.assertIn('enterprise_home_m39_0.js', self.index)
        self.assertGreater(self.index.index('enterprise_home_m39_0.js'), self.index.index('enterprise_shell_m39_0.js'))

    def test_home_reuses_certified_m38_and_internal_helpers(self):
        self.assertIn('clientHomeSummary', self.source)
        self.assertIn('sortClientCasesForAttention', self.source)
        self.assertIn('caseCard', self.source)
        self.assertIn('friendlyCaseState', self.source)
        self.assertIn('nextCaseAction', self.source)

    def test_home_is_client_root_only(self):
        self.assertIn("state.user?.role !== 'client' || currentPath() !== '/'", self.source)

    def test_home_uses_only_existing_case_and_document_state(self):
        self.assertIn('state.cases', self.source)
        self.assertIn('state.documents', self.source)
        for token in ('state.contracts', 'state.obligations', 'state.projects', 'state.decisions', 'state.organization'):
            self.assertNotIn(token, self.source)

    def test_open_cases_use_friendly_state(self):
        self.assertIn("friendlyCaseState(item).key !== 'closed'", self.source)
        self.assertNotIn('/cerrado|finalizado/', self.source)

    def test_home_does_not_claim_unimplemented_enterprise_metrics(self):
        lowered = self.source.lower()
        for token in ('contratos activos', 'obligaciones pendientes', 'proyectos activos', 'decisiones pendientes', 'término legal calculado'):
            self.assertNotIn(token, lowered)
        self.assertIn('La plataforma muestra únicamente información ya registrada en tu espacio.', self.source)

    def test_home_preserves_responsible_timing_language(self):
        self.assertIn('referencias operativas', self.source)
        self.assertIn('no sustituyen la verificación de términos legales aplicables', self.source)

    def test_home_has_no_backend_or_storage_channel(self):
        for token in ('api(', 'fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'indexedDB'):
            self.assertNotIn(token, self.source)

    def test_home_does_not_mutate_application_state(self):
        self.assertIsNone(re.search(r"\bstate\.[A-Za-z0-9_]+\s*=", self.source))

    def test_home_is_idempotent_by_fingerprint(self):
        self.assertIn('page.dataset.m390Fingerprint === currentFingerprint', self.source)
        self.assertIn('page.dataset.m390Fingerprint = currentFingerprint', self.source)
        self.assertIn('let scheduled = false;', self.source)
        self.assertIn('queueMicrotask', self.source)


if __name__ == '__main__':
    unittest.main()
