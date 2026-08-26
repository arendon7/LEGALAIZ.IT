from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'app' / 'index.html').read_text(encoding='utf-8')
JS = (ROOT / 'app' / 'modules' / 'client_workspace_m38_3.js').read_text(encoding='utf-8')
CSS = (ROOT / 'app' / 'modules' / 'client_workspace_m38_3.css').read_text(encoding='utf-8')
M353 = (ROOT / 'app' / 'modules' / 'case_activation_m35_3.js').read_text(encoding='utf-8')
ROUTE = (ROOT / 'legalai_platform' / 'routes' / 'm36_3_controlled_delivery_routes.py').read_text(encoding='utf-8')
ENGINE = (ROOT / 'legalai_platform' / 'controlled_delivery_m36_3.py').read_text(encoding='utf-8')


class ClientWorkspaceDeliveryM383Tests(unittest.TestCase):
    def test_assets_load_last_after_m353_and_m382(self):
        self.assertIn('client_workspace_m38_3.css', INDEX)
        self.assertIn('client_workspace_m38_3.js', INDEX)
        self.assertLess(INDEX.index('case_activation_m35_3.js'), INDEX.index('client_workspace_m38_3.js'))
        self.assertLess(INDEX.index('guided_form_m38_2.js'), INDEX.index('client_workspace_m38_3.js'))

    def test_client_overlay_uses_existing_read_only_delivery_detail(self):
        self.assertIn("state.user.role !== 'client'", JS)
        self.assertIn("const DELIVERY_PREFIX = '/api/m36/delivery/cases'", JS)
        self.assertIn('await api(`${DELIVERY_PREFIX}/${encodeURIComponent(caseId)}`)', JS)
        self.assertNotIn("method:'POST'", JS)
        self.assertNotIn('method: \'POST\'', JS)
        self.assertNotIn('/deliver', JS)
        self.assertNotIn('require_csrf', JS)
        self.assertIn('payload = center.detail(user, parts[1])', ROUTE)

    def test_server_keeps_owner_isolation_and_download_auditing(self):
        self.assertIn('role == "client" and actor_id', ENGINE)
        self.assertIn('actor_id == str(case.get("owner_id") or "")', ENGINE)
        self.assertIn('DOWNLOAD_REQUESTED', ENGINE)
        self.assertIn('download_request_is_not_receipt_confirmation', ENGINE)
        self.assertIn('delivery_state_means_in_app_availability', ENGINE)

    def test_positive_delivery_requires_exact_delivered_state_dual_approval_and_safe_url(self):
        self.assertIn("payload.state === 'DELIVERED_IN_APP'", JS)
        self.assertIn('governance.dual_human_approval_preserved === true', JS)
        self.assertIn('if (!approved || !downloadUrl || count < 1)', JS)
        self.assertIn('value === expected ? value :', JS)
        self.assertIn('Descargar paquete final', JS)
        self.assertIn('href="${esc(downloadUrl)}"', JS)

    def test_client_ui_never_renders_integrity_hashes_or_internal_delivery_identifiers(self):
        for forbidden in (
            'package_sha256',
            'manifest_sha256',
            'release_snapshot_sha256',
            'delivery_id',
            'm24_transition_id',
            'delivered_by',
            'assignment_id',
            'fulfillment_intake_id',
        ):
            self.assertNotIn(forbidden, JS)

    def test_activation_jargon_is_rewritten_at_presentation_boundary(self):
        for text in (
            'Expediente listo para continuar',
            'Valor en entorno de prueba',
            'Referencia de servicio',
            'Comprobante de prueba',
            'Operación de prueba validada',
            'Vinculación con tu expediente confirmada',
            'Estado del proceso:',
        ):
            self.assertIn(text, JS)
        self.assertIn('checkout sandbox', M353.lower())
        self.assertIn('Journey:', M353)

    def test_delivery_copy_preserves_legal_and_receipt_boundaries(self):
        for text in (
            'revisión jurídica y control de calidad independiente',
            'no acreditan por sí solas lectura, recepción por un canal externo ni un resultado jurídico',
            'No mostramos un botón de descarga hasta confirmar la entrega.',
        ):
            self.assertIn(text, JS)
        self.assertNotIn('resultado garantizado', JS.lower())
        self.assertNotIn('recepción confirmada', JS.lower())
        self.assertNotIn('radicación confirmada', JS.lower())

    def test_404_not_available_never_becomes_false_delivery_or_warning(self):
        self.assertIn("error?.status === 404 && code === 'DELIVERY_NOT_AVAILABLE'", JS)
        self.assertIn('unavailable.add(caseId)', JS)
        self.assertNotIn('mountDelivery({}, caseId)', JS)

    def test_workspace_reuses_existing_case_tab_action_without_new_mutating_handler(self):
        self.assertIn('data-action="case-tab" data-tab="documentos"', JS)
        self.assertNotIn("addEventListener('click'", JS)
        self.assertNotIn('preventDefault', JS)
        self.assertNotIn('dispatchEvent', JS)
        self.assertNotIn('localStorage', JS)
        self.assertNotIn('sessionStorage', JS)

    def test_responsive_accessible_and_brand_contracts_exist(self):
        self.assertIn('aria-label="Entrega final de documentos"', JS)
        self.assertIn('role="status" aria-live="polite"', JS)
        self.assertIn('@media(max-width:900px)', CSS)
        self.assertIn('@media(max-width:640px)', CSS)
        self.assertIn('@media(prefers-reduced-motion:reduce)', CSS)
        self.assertIn('#0D1324', CSS)
        self.assertIn('#C9A96E', CSS)
        self.assertIn('rgba(37,99,235', CSS)


if __name__ == '__main__':
    unittest.main()
