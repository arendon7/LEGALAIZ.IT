from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'app' / 'index.html').read_text(encoding='utf-8')
JS = (ROOT / 'app' / 'modules' / 'guided_form_m38_2.js').read_text(encoding='utf-8')
CSS = (ROOT / 'app' / 'modules' / 'guided_form_m38_2.css').read_text(encoding='utf-8')
M351 = (ROOT / 'app' / 'modules' / 'fulfillment_bridge_m35_1.js').read_text(encoding='utf-8')


class GuidedFormExperienceM382Tests(unittest.TestCase):
    def test_assets_load_after_m381_and_certified_m35_flow(self):
        self.assertIn('guided_form_m38_2.css', INDEX)
        self.assertIn('guided_form_m38_2.js', INDEX)
        self.assertLess(INDEX.index('fulfillment_bridge_m35_1.js'), INDEX.index('guided_form_m38_2.js'))
        self.assertLess(INDEX.index('guided_journey_m38_1.js'), INDEX.index('guided_form_m38_2.js'))

    def test_layer_is_presentation_only_and_never_calls_backend_or_reads_answers(self):
        forbidden = [
            'api(', 'fetch(', 'XMLHttpRequest', 'localStorage', 'state.',
            '.value', 'problem_statement', 'recovery_code', 'payment', 'checkout',
            '/api/', 'draftKey(', 'answers',
        ]
        for token in forbidden:
            self.assertNotIn(token, JS, token)

    def test_prefill_provenance_uses_only_existing_m351_non_sensitive_metadata(self):
        self.assertIn("legalaiz.m351.bridgeNotice", JS)
        self.assertIn('prefilled_question_ids', JS)
        self.assertIn('product_code', JS)
        self.assertIn('prefilled_question_ids', M351)
        self.assertNotIn('eligible_prefill_count || 0)', JS)
        self.assertNotRegex(JS, r'payload\.(answers|facts|problem|story|narrative|draft_id|offer)')

    def test_each_visible_question_gets_required_optional_and_prefill_explanation(self):
        self.assertIn('.question[data-question]', JS)
        self.assertIn("'Obligatorio'", JS)
        self.assertIn("'Opcional'", JS)
        self.assertIn('Reutilizado inicialmente · tus cambios prevalecen', JS)
        self.assertIn('m382-prefilled-question', JS)

    def test_help_is_descriptive_not_question_mark_only(self):
        self.assertIn("help.textContent !== '¿Por qué?'", JS)
        self.assertIn("help.textContent = '¿Por qué?'", JS)
        self.assertIn('m382-help-button', JS)

    def test_review_gate_explains_exact_human_checks_without_automatic_claims(self):
        for text in (
            'Personas y entidades:',
            'Fechas y plazos:',
            'Valores:',
            'Hechos y soportes:',
            'No radica actuaciones ni sustituye la revisión profesional',
            'Confirmar datos y analizar',
        ):
            self.assertIn(text, JS)
        self.assertNotRegex(JS.lower(), r'aprobaci[oó]n autom[aá]tica|resultado garantizado|radicaci[oó]n autom[aá]tica')

    def test_save_and_progress_states_are_accessible(self):
        self.assertIn("draft.setAttribute('aria-live', 'polite')", JS)
        self.assertIn("overview.setAttribute('aria-valuetext'", JS)
        self.assertIn('Guardar ahora', JS)
        self.assertIn('Al continuar, se validan las preguntas obligatorias visibles.', JS)

    def test_responsive_reduced_motion_and_brand_contracts_exist(self):
        self.assertIn('@media (max-width:900px)', CSS)
        self.assertIn('@media (max-width:640px)', CSS)
        self.assertIn('@media (prefers-reduced-motion:reduce)', CSS)
        self.assertIn('#0D1324', CSS)
        self.assertIn('rgba(37,99,235', CSS)
        self.assertIn('rgba(201,169,110', CSS)
        self.assertIn('#F7F5F1', CSS)

    def test_m382_never_changes_question_controls_or_submit_semantics(self):
        self.assertNotIn('addEventListener(\'click\'', JS)
        self.assertNotIn('addEventListener("click"', JS)
        self.assertNotIn('disabled =', JS)
        self.assertNotIn('preventDefault', JS)
        self.assertNotIn('submit(', JS)
        self.assertNotIn('dispatchEvent', JS)


if __name__ == '__main__':
    unittest.main()
