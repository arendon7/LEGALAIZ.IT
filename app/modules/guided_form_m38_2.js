'use strict';

const PREFILL_NOTICE_KEY = 'legalaiz.m351.bridgeNotice';
let scheduled = false;

function pathNow() {
  return location.hash.replace(/^#/, '') || '/';
}

function productCode() {
  const match = pathNow().match(/^\/nuevo\/(CO-[A-Z]{2}-\d{3})$/);
  return match ? match[1] : '';
}

function prefilledQuestionIds(code) {
  if (!code) return new Set();
  try {
    const payload = JSON.parse(sessionStorage.getItem(PREFILL_NOTICE_KEY) || 'null');
    if (!payload || payload.product_code !== code || !Array.isArray(payload.prefilled_question_ids)) return new Set();
    return new Set(payload.prefilled_question_ids.filter(id => typeof id === 'string' && id.length <= 120));
  } catch {
    return new Set();
  }
}

function setText(selector, text) {
  const element = document.querySelector(selector);
  if (element && element.textContent !== text) element.textContent = text;
}

function ensureFormContract(prefilledCount) {
  const overview = document.querySelector('.wizard-overview');
  if (!overview?.parentElement || document.querySelector('.m382-form-contract')) return;
  const reuse = prefilledCount
    ? `<div><b>${prefilledCount}</b><span>${prefilledCount === 1 ? 'dato pudo reutilizarse' : 'datos pudieron reutilizarse'} desde tu diagnóstico. Los identificarás para que puedas verificarlos.</span></div>`
    : '<div><b>Sin repeticiones innecesarias</b><span>Si llegaste desde el orientador, sólo reutilizamos datos con equivalencia directa. Lo demás se pregunta aquí.</span></div>';
  overview.insertAdjacentHTML('afterend', `<section class="m382-form-contract" aria-label="Cómo funciona este formulario">
    <div class="m382-form-contract-head"><span class="eyebrow">Formulario inteligente</span><h2>Completa lo específico de tu solución, con control sobre cada dato.</h2><p>Tu avance se conserva como borrador en este navegador. Antes del análisis tendrás un resumen para corregir nombres, fechas, valores y hechos.</p></div>
    <div class="m382-form-contract-grid">
      <div><b>Guardado progresivo</b><span>Puedes salir y retomar este formulario desde el mismo navegador mientras el borrador esté disponible.</span></div>
      ${reuse}
      <div><b>Confirmación antes del análisis</b><span>Nada se presenta como definitivo por completar una pregunta. Primero revisas el resumen y decides continuar.</span></div>
    </div>
  </section>`);
}

function questionMeta(question, prefilled) {
  const required = Boolean(question.querySelector('.required-mark'));
  const existing = question.querySelector('.m382-question-meta');
  const next = `<div class="m382-question-meta"><span class="m382-field-status ${required ? 'required' : 'optional'}">${required ? 'Obligatorio' : 'Opcional'}</span>${prefilled ? '<span class="m382-prefill-status">Reutilizado inicialmente · tus cambios prevalecen</span>' : ''}</div>`;
  if (!existing) {
    question.querySelector('.question-label')?.insertAdjacentHTML('afterend', next);
  } else if (existing.outerHTML !== next) {
    existing.outerHTML = next;
  }
  question.classList.toggle('m382-prefilled-question', prefilled);

  const help = question.querySelector('.help-btn[data-action="toggle-help"]');
  if (help) {
    help.classList.add('m382-help-button');
    if (help.textContent !== '¿Por qué?') help.textContent = '¿Por qué?';
  }
}

function enhanceQuestions(prefilledIds) {
  document.querySelectorAll('.question[data-question]').forEach(question => {
    const id = question.dataset.question || '';
    questionMeta(question, prefilledIds.has(id));
  });
}

function enhanceGuidance() {
  setText('.m292-wizard-guide .eyebrow', 'Para responder mejor');
  setText('.section-guidance b', 'Responde con información que puedas verificar.');
  setText('.section-guidance span', 'Si un dato no está confirmado, no lo adivines: usa una opción de incertidumbre cuando exista o déjalo pendiente si el formulario lo permite.');
  setText('.m292-prep-card h3', 'Lo que puede ayudarte');

  const recent = [...document.querySelectorAll('.summary-card:not(.m292-prep-card) h3')].find(element => /resumen reciente/i.test(element.textContent || ''));
  if (recent && recent.textContent !== 'Lo que acabas de responder') recent.textContent = 'Lo que acabas de responder';

  const draft = document.querySelector('.draft-status');
  if (draft) {
    draft.setAttribute('role', 'status');
    draft.setAttribute('aria-live', 'polite');
    draft.setAttribute('aria-atomic', 'true');
  }

  const overview = document.querySelector('.wizard-overview[role="progressbar"]');
  if (overview) {
    const progress = Number(overview.getAttribute('aria-valuenow') || 0);
    overview.setAttribute('aria-valuetext', `${Math.max(0, Math.min(100, progress))}% del formulario completado`);
  }
}

function enhanceWizardFooter() {
  const footer = document.querySelector('.wizard-main > .wizard-footer');
  if (!footer || footer.querySelector('.m382-footer-note')) return;
  footer.insertAdjacentHTML('afterbegin', '<p class="m382-footer-note">Al continuar, se validan las preguntas obligatorias visibles. Completar el formulario no radica, firma ni aprueba un documento automáticamente.</p>');
  setText('.wizard-main > .wizard-footer [data-action="wizard-save"]', 'Guardar ahora');
}

function enhanceReview() {
  const review = document.querySelector('.wizard-review-card');
  if (!review) return;
  const grid = review.querySelector('.wizard-review-grid');
  if (grid && !review.querySelector('.m382-review-guide')) {
    grid.insertAdjacentHTML('beforebegin', `<section class="m382-review-guide" aria-label="Lista de verificación antes del análisis">
      <div><span class="eyebrow">Última revisión de datos</span><h3>Comprueba cuatro cosas antes de continuar</h3><p>Si algo no coincide, usa “Editar” en la sección correspondiente. El objetivo es que el análisis parta de hechos que tú reconoces como correctos.</p></div>
      <ul>
        <li><b>Personas y entidades:</b> nombres, identificaciones y calidad en la que actúan.</li>
        <li><b>Fechas y plazos:</b> inicio, terminación, comunicaciones y hechos relevantes.</li>
        <li><b>Valores:</b> montos, pagos, saldos, cánones, honorarios o salarios cuando apliquen.</li>
        <li><b>Hechos y soportes:</b> que el resumen coincida con la información que puedes acreditar.</li>
      </ul>
      <p class="m382-review-boundary"><b>Después de confirmar:</b> LegalAIZ.it genera un análisis o borrador controlado según la solución. No radica actuaciones ni sustituye la revisión profesional cuando ésta sea requerida.</p>
    </section>`);
  }
  setText('.wizard-review-card .badge.blue', 'Revisión final de datos');
  setText('.wizard-review-card [data-action="wizard-review-confirm"]', 'Confirmar datos y analizar');
}

function mount() {
  scheduled = false;
  const code = productCode();
  if (!code) return;
  const prefilledIds = prefilledQuestionIds(code);
  ensureFormContract(prefilledIds.size);
  enhanceQuestions(prefilledIds);
  enhanceGuidance();
  enhanceWizardFooter();
  enhanceReview();
}

function schedule() {
  if (scheduled) return;
  scheduled = true;
  window.setTimeout(mount, 0);
}

window.addEventListener('hashchange', schedule);
const app = document.getElementById('app');
if (app) new MutationObserver(schedule).observe(app, { childList: true, subtree: true });
schedule();
