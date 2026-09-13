import { dateText, esc, state } from '../core.js';
import { caseCard, friendlyCaseState, nextCaseAction } from './internal_m29_2.js';

const STAGE_PRIORITY = Object.freeze({
  ready: 600,
  delivered: 550,
  followup: 520,
  active: 500,
  document: 400,
  review: 300,
  closed: 0,
});

function timestamp(value) {
  const parsed = Date.parse(String(value || ''));
  return Number.isFinite(parsed) ? parsed : 0;
}

export function clientAttentionRank(item = {}) {
  const stage = friendlyCaseState(item);
  return {
    stage,
    priority: STAGE_PRIORITY[stage.key] ?? 100,
    updatedAt: timestamp(item.updated_at),
    stableKey: `${String(item.title || '')}\u0000${String(item.id || '')}`,
  };
}

export function sortClientCasesForAttention(items = []) {
  return [...items].sort((left, right) => {
    const a = clientAttentionRank(left);
    const b = clientAttentionRank(right);
    if (a.priority !== b.priority) return b.priority - a.priority;
    if (a.updatedAt !== b.updatedAt) return b.updatedAt - a.updatedAt;
    return a.stableKey.localeCompare(b.stableKey, 'es');
  });
}

export function clientHomeSummary(items = [], documents = []) {
  const stages = items.map(friendlyCaseState);
  return {
    openCases: stages.filter(stage => stage.key !== 'closed').length,
    reviewCases: stages.filter(stage => stage.key === 'review').length,
    deliveredOrFollowUp: stages.filter(stage => ['delivered', 'followup'].includes(stage.key)).length,
    documents: Array.isArray(documents) ? documents.length : 0,
  };
}

function productMap() {
  return Object.fromEntries((state.products || []).map(product => [product.code, product]));
}

function continueCard(item) {
  if (!item) return '';
  const stage = friendlyCaseState(item);
  const action = nextCaseAction(item);
  const product = productMap()[item.product_code] || {};
  return `<section class="m29-continue-card m292-continue-card m385-priority-card" data-m385-priority-case="${esc(item.id)}">
    <img src="/assets/brand-visuals/internal/${esc(stage.visual)}" alt="">
    <div>
      <span class="eyebrow">Lo más útil para continuar</span>
      <span class="badge ${esc(stage.cls)}">${esc(stage.label)}</span>
      <h2>${esc(item.title)}</h2>
      <p>${esc(product.title || item.product_code)} · Actualizado ${esc(dateText(item.updated_at))}</p>
      <div class="m292-progress"><span class="progress-p${Math.min(100, Math.max(0, Math.round(stage.progress / 10) * 10))}"></span></div>
      <small>${esc(action.text)}</small>
    </div>
    <button class="btn primary" data-action="go" data-route="/caso/${encodeURIComponent(item.id)}">${esc(action.button)}</button>
  </section>`;
}

function summaryMarkup(summary) {
  return [
    ['expediente activo', 'expedientes activos', summary.openCases],
    ['documento guardado', 'documentos guardados', summary.documents],
    ['expediente en revisión', 'expedientes en revisión', summary.reviewCases],
  ].map(([one, many, count], index) => `<article data-m385-summary="${index}"><span aria-hidden="true">${['◫','▤','✓'][index]}</span><div><b>${count}</b><small>${count === 1 ? one : many}</small></div></article>`).join('');
}

function clientHomeFingerprint(items, docs) {
  return JSON.stringify({
    cases: items.map(item => [item.id, item.status, item.review_status, item.risk, item.updated_at]),
    docs: (docs || []).map(doc => [doc.id, doc.status, doc.updated_at]),
  });
}

function enhanceClientHome() {
  if (state.user?.role !== 'client') return;
  const page = document.querySelector('.m29-client-home');
  if (!page) return;

  const cases = Array.isArray(state.cases) ? state.cases : [];
  const docs = Array.isArray(state.documents) ? state.documents : [];
  const fingerprint = clientHomeFingerprint(cases, docs);
  if (page.dataset.m385Fingerprint === fingerprint) return;

  const ordered = sortClientCasesForAttention(cases);
  const open = ordered.filter(item => friendlyCaseState(item).key !== 'closed');
  const priority = open[0] || null;
  const currentContinue = page.querySelector('.m29-continue-card');
  if (priority) {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = continueCard(priority).trim();
    const replacement = wrapper.firstElementChild;
    if (currentContinue && replacement) currentContinue.replaceWith(replacement);
    else if (replacement) page.querySelector('.m29-client-welcome')?.insertAdjacentElement('afterend', replacement);
  } else if (currentContinue) {
    currentContinue.remove();
  }

  const summary = page.querySelector('.m29-client-summary');
  if (summary) summary.innerHTML = summaryMarkup(clientHomeSummary(cases, docs));

  const recentGrid = page.querySelector('.card.span-8 .m292-case-grid');
  if (recentGrid) {
    const products = productMap();
    recentGrid.innerHTML = ordered.slice(0, 4).map(item => caseCard(item, products[item.product_code] || {}, true)).join('');
  }

  const recentHeading = page.querySelector('.card.span-8 .card-header h2');
  const recentCopy = page.querySelector('.card.span-8 .card-header p');
  if (recentHeading) recentHeading.textContent = 'Expedientes para tener presentes';
  if (recentCopy) recentCopy.textContent = 'Ordenados por la etapa que puedes continuar y, después, por la actualización más reciente.';

  page.dataset.m385Fingerprint = fingerprint;
}

function enhanceClientShell() {
  if (state.user?.role !== 'client') return;
  const approval = document.querySelector('.approval-mini');
  if (approval && approval.dataset.m385ClientCopy !== '1') {
    approval.innerHTML = '<span class="approval-dot"></span><div><b>Contenido jurídico controlado</b><p>Cada solución indica cuándo requiere revisión profesional antes de utilizar un resultado.</p></div>';
    approval.dataset.m385ClientCopy = '1';
  }
}

function enhanceAccountDialog() {
  if (state.user?.role !== 'client') return;
  const deployment = state.config?.deployment || {};
  const localDemo = deployment.profile === 'local' && deployment.app_env !== 'pilot-local';
  if (localDemo) return;
  const root = document.getElementById('dialog-root');
  const note = root?.querySelector('.demo-note');
  if (!note || note.dataset.m385AccountCopy === '1') return;
  if (!/datos personales reales|durante esta revisión/i.test(note.textContent || '')) return;
  note.innerHTML = '<b>Acceso controlado.</b> Tu acceso y las acciones realizadas dentro del expediente están sujetos a permisos por rol y trazabilidad.';
  note.dataset.m385AccountCopy = '1';
}

export function applyClientHomeExperience() {
  enhanceClientHome();
  enhanceClientShell();
  enhanceAccountDialog();
}

let scheduled = false;
function scheduleApply() {
  if (scheduled) return;
  scheduled = true;
  queueMicrotask(() => {
    scheduled = false;
    applyClientHomeExperience();
  });
}

const observer = new MutationObserver(scheduleApply);
observer.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', scheduleApply);
window.addEventListener('popstate', scheduleApply);
scheduleApply();
