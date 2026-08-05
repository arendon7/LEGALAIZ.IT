'use strict';

import { closeDialog, currentPath, openDialog, state, toast } from '../core.js';
import { buildDemoAnswers, demoAnswerSummary } from './demo_form_values_m32.js';

const STORAGE_PREFIX = 'legalaizit:demo-form:';
let observerQueued = false;

const hasAnswer = value => value !== '' && value != null && (!Array.isArray(value) || value.length > 0);
const markerKey = code => `${STORAGE_PREFIX}${code}`;

function activeWizard() {
  return currentPath().startsWith('/nuevo/') && state.wizard?.code ? state.wizard : null;
}

function readMarker(code) {
  try { return JSON.parse(localStorage.getItem(markerKey(code)) || 'null'); }
  catch { return null; }
}

function writeMarker(code, answerCount) {
  localStorage.setItem(markerKey(code), JSON.stringify({
    product_code: code,
    answer_count: answerCount,
    generated_at: new Date().toISOString(),
    synthetic: true,
  }));
}

function demoButton(label = 'Completar con datos demo') {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'btn gold demo-form-fill-button';
  button.dataset.demoFormFill = 'true';
  button.textContent = label;
  return button;
}

function addFormAssistant(wizard) {
  const body = document.querySelector('.wizard-body');
  if (!body || body.querySelector('[data-demo-form-assistant]')) return;
  const marker = readMarker(wizard.code);
  const section = document.createElement('section');
  section.className = 'demo-form-assistant';
  section.dataset.demoFormAssistant = 'true';
  section.setAttribute('aria-label', 'Asistente de datos para demostración');
  section.innerHTML = `<div class="demo-form-assistant-copy"><span class="demo-form-assistant-icon" aria-hidden="true">▶</span><div><span class="eyebrow">Demostración rápida</span><h3>${marker ? 'Vuelve a cargar el escenario sintético' : 'Prueba el recorrido sin escribir todos los datos'}</h3><p>Completa el formulario con información ficticia coherente, revisa el resumen y continúa al análisis. No utiliza datos personales reales.</p></div></div>`;
  section.appendChild(demoButton(marker ? 'Recargar datos demo' : 'Completar con datos demo'));
  body.prepend(section);
}

function addReviewNotice(wizard) {
  const grid = document.querySelector('.wizard-review-grid');
  if (!grid || document.getElementById('demo-form-review-notice') || !readMarker(wizard.code)) return;
  const notice = document.createElement('section');
  notice.id = 'demo-form-review-notice';
  notice.className = 'demo-form-mode-notice';
  notice.tabIndex = -1;
  notice.innerHTML = '<span class="badge gold">DATOS DEMO</span><div><b>Este resumen contiene información sintética.</b><p>Puedes analizarlo y continuar por el flujo sandbox. No debe utilizarse como información de un cliente ni como base de una actuación real.</p></div>';
  grid.parentElement?.insertBefore(notice, grid);
}

function addResultNotice(wizard) {
  const result = document.querySelector('.result-banner');
  const eyebrow = document.querySelector('.page-header .eyebrow')?.textContent || '';
  if (!result || !/resultado preliminar/i.test(eyebrow) || document.getElementById('demo-form-result-notice') || !readMarker(wizard.code)) return;
  const notice = document.createElement('div');
  notice.id = 'demo-form-result-notice';
  notice.className = 'demo-form-result-notice';
  notice.innerHTML = '<span class="badge gold">ESCENARIO SINTÉTICO</span><span>El diagnóstico corresponde exclusivamente a la demostración y puede continuar por el checkout sandbox.</span>';
  result.parentElement?.insertBefore(notice, result);
}

function augmentWizard() {
  observerQueued = false;
  const wizard = activeWizard();
  if (!wizard) return;
  addFormAssistant(wizard);
  addReviewNotice(wizard);
  addResultNotice(wizard);
}

function scheduleAugment() {
  if (observerQueued) return;
  observerQueued = true;
  queueMicrotask(augmentWizard);
}

function applyDemoData() {
  const wizard = activeWizard();
  if (!wizard) {
    closeDialog();
    toast('Abre primero un formulario de solución.', 'danger');
    return;
  }
  const questions = wizard.detail?.interview?.questions || [];
  const answers = buildDemoAnswers(questions);
  const summary = demoAnswerSummary(questions, answers);
  if (summary.missingRequired.length) {
    closeDialog();
    toast(`No fue posible completar ${summary.missingRequired.length} datos obligatorios.`, 'danger');
    return;
  }
  wizard.answers = answers;
  wizard.demoMode = true;
  wizard.result = null;
  wizard.reviewMode = true;
  wizard.step = Math.max(0, (wizard.sections || []).length - 1);
  wizard.page = 0;
  window.legalaiSaveWizard?.();
  writeMarker(wizard.code, summary.answeredCount);
  closeDialog();
  window.dispatchEvent(new Event('hashchange'));
  setTimeout(() => {
    document.getElementById('demo-form-review-notice')?.focus({ preventScroll: false });
    toast(`${summary.answeredCount} respuestas sintéticas cargadas. Revisa el resumen y continúa al análisis.`, 'success');
  }, 80);
}

function requestDemoData() {
  const wizard = activeWizard();
  if (!wizard) return;
  const existingCount = Object.values(wizard.answers || {}).filter(hasAnswer).length;
  if (!existingCount) return applyDemoData();
  openDialog({
    title: 'Cargar datos de demostración',
    subtitle: 'Escenario sintético para recorrer el formulario',
    body: `<div class="demo-form-dialog"><div class="demo-form-dialog-icon" aria-hidden="true">§</div><div><p>Se reemplazarán las <b>${existingCount} respuestas</b> actualmente guardadas por información ficticia coherente con esta solución.</p><p>La acción no crea un expediente real y los datos quedarán identificados como demostrativos.</p></div></div>`,
    actions: '<button class="btn secondary" data-action="close-dialog">Cancelar</button><button class="btn gold" type="button" data-demo-form-confirm="true">Reemplazar y continuar</button>',
  });
}

document.addEventListener('click', event => {
  const fill = event.target.closest('[data-demo-form-fill]');
  if (fill) {
    event.preventDefault();
    event.stopPropagation();
    requestDemoData();
    return;
  }
  const confirm = event.target.closest('[data-demo-form-confirm]');
  if (confirm) {
    event.preventDefault();
    event.stopPropagation();
    applyDemoData();
  }
}, true);

new MutationObserver(scheduleAugment).observe(document.body, { childList: true, subtree: true });
window.addEventListener('hashchange', scheduleAugment);
scheduleAugment();
