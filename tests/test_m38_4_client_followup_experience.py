from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'app' / 'index.html').read_text(encoding='utf-8')
JS = (ROOT / 'app' / 'modules' / 'client_followup_m38_4.js').read_text(encoding='utf-8')
CSS = (ROOT / 'app' / 'modules' / 'client_followup_m38_4.css').read_text(encoding='utf-8')
FOLLOWUP = (ROOT / 'legalai_platform' / 'post_delivery_followup_m37_0.py').read_text(encoding='utf-8')
EVIDENCE = (ROOT / 'legalai_platform' / 'evidence_intake_m37_1.py').read_text(encoding='utf-8')
TIMING = (ROOT / 'legalai_platform' / 'timing_reminders_m37_2.py').read_text(encoding='utf-8')
DISPOSITION = (ROOT / 'legalai_platform' / 'professional_disposition_m37_3.py').read_text(encoding='utf-8')
DISPOSITION_CONFIG = (ROOT / 'config' / 'm37' / 'disposition_contracts.json').read_text(encoding='utf-8')


class ClientFollowupExperienceM384Tests(unittest.TestCase):
    def test_assets_load_after_certified_m383_workspace(self):
        self.assertIn('client_followup_m38_4.css', INDEX)
        self.assertIn('client_followup_m38_4.js', INDEX)
        self.assertLess(INDEX.index('client_workspace_m38_3.css'), INDEX.index('client_followup_m38_4.css'))
        self.assertLess(INDEX.index('client_workspace_m38_3.js'), INDEX.index('client_followup_m38_4.js'))

    def test_client_scope_and_case_route_are_explicit(self):
        self.assertIn("state.user.role !== 'client'", JS)
        self.assertIn("/^\\/caso\\/([^/?#]+)$/", JS)
        self.assertIn("caseId !== clientCaseId()", JS)
        self.assertIn('self.journey.can_access(case, dict(actor))', FOLLOWUP)

    def test_ui_reuses_all_four_certified_m37_read_models(self):
        for marker in (
            "const FOLLOWUP_PREFIX = '/api/m37/follow-up/cases'",
            "const EVIDENCE_PREFIX = '/api/m37/evidence/cases'",
            "const TIMING_PREFIX = '/api/m37/timing/cases'",
            "const DISPOSITION_PREFIX = '/api/m37/disposition/cases'",
        ):
            self.assertIn(marker, JS)
        self.assertIn('Promise.all([', JS)
        self.assertNotIn('/api/m38/', JS)

    def test_start_is_explicit_and_uses_exact_existing_confirmation(self):
        self.assertIn("const START_CONFIRMATION = 'INICIAR SEGUIMIENTO'", JS)
        self.assertIn("data-m384-action=\"open-start\"", JS)
        self.assertIn("data-m384-action=\"confirm-start\"", JS)
        self.assertIn('{ confirmation: START_CONFIRMATION }', JS)
        self.assertIn('START_CONFIRMATION = "INICIAR SEGUIMIENTO"', FOLLOWUP)
        self.assertIn('str(confirmation or "").strip() != START_CONFIRMATION', FOLLOWUP)

    def test_task_completion_is_reported_not_verified(self):
        self.assertIn("{ status: 'completed', note }", JS)
        self.assertIn('Reportada por ti', JS)
        self.assertIn('no lo convierte en verificación externa', JS)
        self.assertIn('no acredita por sí solo recepción externa ni efecto jurídico', JS)
        self.assertIn('return "SELF_REPORTED"', FOLLOWUP)
        self.assertIn('"evidence_verified": False', FOLLOWUP)
        self.assertIn('"legal_effect_verified": False', FOLLOWUP)

    def test_upload_uses_existing_encrypted_evidence_intake_without_completing_task(self):
        self.assertIn("const ALLOWED_UPLOAD = '.pdf,.png,.jpg,.jpeg,.docx,.txt'", JS)
        self.assertIn('const MAX_FILE_BYTES = 10 * 1024 * 1024', JS)
        self.assertIn('const form = new FormData()', JS)
        self.assertIn("form.append('file', file, file.name)", JS)
        self.assertIn('/tasks/${encodeURIComponent(taskId)}/upload', JS)
        self.assertIn('Su revisión no completa automáticamente la actividad', JS)
        self.assertIn('self.object_store.put', EVIDENCE)
        self.assertIn('"upload_completes_task": False', EVIDENCE)

    def test_client_cannot_use_professional_evidence_review(self):
        self.assertNotIn('/review`', JS)
        self.assertNotIn('/review\'', JS)
        self.assertIn('def _require_reviewer', EVIDENCE)
        self.assertIn('role == "specialist"', EVIDENCE)
        self.assertIn('role == "admin"', EVIDENCE)
        self.assertNotIn('role == "client" and', EVIDENCE[EVIDENCE.index('def _require_reviewer'):EVIDENCE.index('def review')])

    def test_evidence_download_url_is_exact_server_supplied_case_item_path(self):
        self.assertIn('function safeEvidenceDownloadUrl', JS)
        self.assertIn('/items/${encodeURIComponent(evidenceId)}/download', JS)
        self.assertIn("String(item?.download_url || '') === expected ? expected : ''", JS)
        self.assertIn('Descargar soporte', JS)

    def test_dates_are_user_records_and_never_statutory_calculations(self):
        for event_type in (
            'ACTION_PERFORMED',
            'AUTHORITY_RECEIPT_REPORTED',
            'NOTICE_RECEIVED',
            'RESPONSE_RECEIVED',
            'OTHER_RELEVANT_EVENT',
        ):
            self.assertIn(event_type, JS)
        self.assertIn('no la interpreta aquí como fecha cierta ante terceros ni como inicio o vencimiento de un término legal', JS)
        self.assertNotIn('BusinessCalendar', JS)
        self.assertNotIn('statutory', JS.lower())
        self.assertIn('"is_legal_deadline": False', TIMING)
        self.assertIn('"legal_deadline_verified": False', TIMING)

    def test_reminders_are_in_app_operational_only(self):
        self.assertIn('Crear recordatorio operativo', JS)
        self.assertIn('No se enviará una notificación externa automática', JS)
        self.assertIn('/acknowledge', JS)
        self.assertIn('/cancel', JS)
        self.assertIn('"automatic_external_notification": False', TIMING)
        self.assertIn('"acknowledgement_completes_task": False', TIMING)

    def test_client_disposition_is_read_only_and_cannot_close_or_escalate(self):
        self.assertIn('optionalGet(`${DISPOSITION_PREFIX}/${encodeURIComponent(caseId)}`)', JS)
        self.assertNotIn('${DISPOSITION_PREFIX}/${encodeURIComponent(caseId)}/close', JS)
        self.assertNotIn('${DISPOSITION_PREFIX}/${encodeURIComponent(caseId)}/escalate', JS)
        self.assertIn('El cliente no puede cerrar ni escalar el expediente desde esta interfaz.', JS)
        self.assertIn('"client_may_dispose_case": false', DISPOSITION_CONFIG)
        self.assertIn('"close_roles": ["specialist"]', DISPOSITION_CONFIG)

    def test_close_readiness_is_professional_review_not_legal_success(self):
        self.assertIn('Listo para revisión de cierre', JS)
        self.assertIn('El especialista asignado debe revisar el expediente y decidir expresamente', JS)
        self.assertIn('no la cierra automáticamente', JS)
        self.assertIn('no equivale, por sí solo, a éxito jurídico', JS)
        self.assertIn('"close_is_legal_success": False', DISPOSITION)
        self.assertIn('"automatic_close": False', DISPOSITION)

    def test_public_ui_does_not_render_sensitive_m37_plumbing(self):
        for forbidden in (
            'object_ref',
            'plaintext_sha256',
            'actor_id',
            'internal_reason',
            'event_hash',
            'previous_hash',
            'payment_intent_id',
            'scan_detail',
            'reviewer_id',
        ):
            self.assertNotIn(forbidden, JS)

    def test_404_and_partial_read_fail_closed_without_inventing_progress(self):
        self.assertIn("if (error?.status === 404) return { value: null, error: false }", JS)
        self.assertIn("if (error?.status === 404) {", JS)
        self.assertIn("document.querySelector('[data-m384-followup]')?.remove()", JS)
        self.assertIn('No pudimos consultar esta etapa de forma completa.', JS)
        self.assertNotIn('followup = {}', JS)

    def test_cached_mutation_observer_does_not_remount_existing_card(self):
        guard = "if (!force && models.has(caseId)) {\n    if (!document.querySelector('[data-m384-followup]')) mount(models.get(caseId));\n    return;\n  }"
        self.assertIn(guard, JS)
        self.assertIn('new MutationObserver(schedule)', JS)
        self.assertNotIn('setInterval(', JS)

    def test_no_parallel_browser_storage_or_background_polling(self):
        self.assertNotIn('localStorage', JS)
        self.assertNotIn('sessionStorage', JS)
        self.assertNotIn('indexedDB', JS)
        self.assertNotIn('setInterval(', JS)
        self.assertIn('const models = new Map()', JS)

    def test_accessibility_responsive_and_brand_contracts_are_present(self):
        self.assertIn('aria-label="Seguimiento posterior a la entrega"', JS)
        self.assertIn('role="progressbar"', JS)
        self.assertIn('aria-valuemin="0"', JS)
        self.assertIn('@media(max-width:900px)', CSS)
        self.assertIn('@media(max-width:640px)', CSS)
        self.assertIn('@media(prefers-reduced-motion:reduce)', CSS)
        self.assertIn(':focus-visible', CSS)
        self.assertIn('#0d1324', CSS.lower())
        self.assertIn('#c9a96e', CSS.lower())
        self.assertIn('#2563eb', CSS.lower())


if __name__ == '__main__':
    unittest.main()
