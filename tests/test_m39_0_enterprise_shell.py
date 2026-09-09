from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "app" / "modules" / "enterprise_shell_m39_0.js"
CSS = ROOT / "app" / "modules" / "enterprise_shell_m39_0.css"
INDEX = ROOT / "app" / "index.html"


class M390EnterpriseShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MODULE.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")
        cls.index = INDEX.read_text(encoding="utf-8")

    def test_shell_module_and_css_are_loaded_after_m38(self):
        self.assertIn('enterprise_shell_m39_0.css', self.index)
        self.assertIn('enterprise_shell_m39_0.js', self.index)
        self.assertGreater(self.index.index('enterprise_shell_m39_0.js'), self.index.index('professional_review_m38_6.js'))

    def test_shell_is_client_only(self):
        self.assertIn("const CLIENT_ROLE = 'client';", self.source)
        self.assertIn('state.user?.role === CLIENT_ROLE', self.source)

    def test_meridiano_is_the_private_client_brand(self):
        self.assertIn('Meridiano Empresas', self.source)
        self.assertIn('Tu operación jurídica organizada', self.source)
        self.assertIn('Cliente empresarial', self.source)
        self.assertIn('Tecnología jurídica sobre infraestructura LegalAIZ.', self.source)

    def test_existing_real_routes_are_preserved(self):
        for route in ('/nuevo', '/casos', '/soluciones', '/documentos', '/notificaciones', '/ayuda', '/accesibilidad'):
            self.assertIn(f"'{route}'", self.source)

    def test_unimplemented_enterprise_routes_are_not_exposed(self):
        for route in ('/solicitudes', '/contratos', '/obligaciones', '/proyectos', '/decisiones', '/empresa'):
            self.assertNotIn(route, self.source)

    def test_shell_has_no_backend_or_storage_channel(self):
        for token in ('api(', 'fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'indexedDB'):
            self.assertNotIn(token, self.source)

    def test_shell_does_not_mutate_application_state(self):
        self.assertIsNone(re.search(r"\bstate\.[A-Za-z0-9_]+\s*=", self.source))

    def test_shell_uses_scoped_enterprise_marker(self):
        self.assertIn("document.documentElement.dataset.m390Enterprise = '1';", self.source)
        self.assertIn('html[data-m390-enterprise="1"]', self.css)


if __name__ == '__main__':
    unittest.main()
