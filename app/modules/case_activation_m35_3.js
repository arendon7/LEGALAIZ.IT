import { api, esc, go, money, state } from '../core.js';

const ACTIVATION_PREFIX = '/api/m35/activation/';
const cache = new Map();
const inFlight = new Set();
let scheduled = false;

function pathNow() {
  return (location.hash.replace(/^#/, '') || '/').split('?')[0];
}

function caseFromPath(path = pathNow()) {
  const match = String(path).match(/^\/caso\/([^/?#]+)$/);
  return match ? decodeURIComponent(match[1]) : '';
}

function actionHtml(next = {}, caseId = '') {
  if (next.route) {
    return `<button type="button" class="btn primary" data-m353-route="${esc(next.route)}">${esc(next.code === 'RETRY_DOCUMENT_PREPARATION' ? 'Reintentar preparación' : 'Continuar')}</button>`;
  }
  if (next.tab) {
    return `<button type="button" class="btn primary" data-m353-tab="${esc(next.tab)}" data-case-id="${esc(caseId)}">${esc(next.tab === 'revision' ? 'Ver revisión' : next.tab === 'seguimiento' ? 'Ver siguientes pasos' : 'Ver documentos')}</button>`;
  }
  return '';
}

function activationMarkup(payload) {
  const activation = payload.activation_status || '';
  const pending = activation === 'DOCUMENTS_PENDING';
  const purchase = payload.purchase_confirmation || {};
  const caseInfo = payload.case || {};
  const documents = payload.documents || {};
  const journey = payload.journey || {};
  const next = payload.next_step || {};
  const badge = pending ? 'Preparación documental pendiente' : 'Expediente activado';
  const headline = pending
    ? 'Tu expediente ya existe y conserva el pago sandbox, pero aún faltan los documentos.'
    : 'Tu checkout sandbox quedó vinculado de forma verificable a este expediente.';
  const intro = pending
    ? 'No se realizará un segundo pago ni se creará otro expediente al reintentar.'
    : 'Puedes comprobar qué nivel de servicio quedó asociado, el comprobante sandbox y el siguiente paso del proceso.';
  const reviewText = purchase.review_included ? 'Incluida o exigida' : 'No incluida en este nivel';
  const documentText = pending ? `${documents.count || 0} materializados` : `${documents.count || 0} vinculados`;

  return `<section class="m353-activation ${pending ? 'pending' : 'active'}" data-m353-case="${esc(caseInfo.id)}" aria-label="Confirmación de activación del expediente">
    <div class="m353-activation-head">
      <div><span class="m353-status">${esc(badge)}</span><h2>${esc(headline)}</h2><p>${esc(intro)}</p></div>
      <div class="m353-shield" aria-hidden="true">✓</div>
    </div>
    <div class="m353-purchase-grid">
      <div><small>Nivel de servicio</small><b>${esc(purchase.service_label || purchase.service_level || 'Servicio')}</b></div>
      <div><small>Total sandbox</small><b>${esc(money(purchase.amount || 0))}</b><span>Sin cargo real</span></div>
      <div><small>Orden</small><b>${esc(purchase.order_id || '—')}</b></div>
      <div><small>Comprobante sandbox</small><b>${esc(purchase.receipt_number || '—')}</b></div>
      <div><small>Documentos</small><b>${esc(documentText)}</b></div>
      <div><small>Revisión profesional</small><b>${esc(reviewText)}</b></div>
    </div>
    <div class="m353-trace-row"><span>Pago sandbox verificado</span><span>Trazabilidad de orden y expediente verificada</span><span>Journey: ${esc(journey.current_state || 'pendiente')}</span></div>
    <div class="m353-next-step">
      <div><span>Siguiente paso</span><h3>${esc(next.title || 'Consulta el estado de tu expediente')}</h3><p>${esc(next.detail || '')}</p></div>
      ${actionHtml(next, caseInfo.id)}
    </div>
    <div class="m353-boundary"><b>Alcance de esta confirmación.</b> ${esc((payload.notices || []).join(' '))}</div>
  </section>`;
}

function warningMarkup(code = '') {
  return `<section class="m353-integrity-warning" role="status" aria-live="polite">
    <div><span>Verificación pendiente</span><h2>No mostramos una confirmación positiva de compra.</h2><p>No fue posible validar toda la cadena entre checkout sandbox, pago, expediente y documentos. El expediente continúa disponible, pero esta tarjeta permanecerá bloqueada hasta recuperar la trazabilidad.</p>${code ? `<small>Código de control: ${esc(code)}</small>` : ''}</div>
  </section>`;
}

function mount(payload, caseId) {
  if (caseFromPath() !== caseId) return;
  const page = document.querySelector('.case-header')?.parentElement;
  const header = page?.querySelector('.case-header');
  if (!page || !header || page.querySelector('[data-m353-case], .m353-integrity-warning')) return;
  header.insertAdjacentHTML('afterend', activationMarkup(payload));
}

function mountWarning(caseId, code) {
  if (caseFromPath() !== caseId) return;
  const page = document.querySelector('.case-header')?.parentElement;
  const header = page?.querySelector('.case-header');
  if (!page || !header || page.querySelector('[data-m353-case], .m353-integrity-warning')) return;
  header.insertAdjacentHTML('afterend', warningMarkup(code));
}

async function enhanceCase() {
  const caseId = caseFromPath();
  if (!caseId || !state.user || state.user.role !== 'client') return;
  if (document.querySelector(`[data-m353-case="${CSS.escape(caseId)}"]`) || document.querySelector('.m353-integrity-warning')) return;
  if (cache.has(caseId)) return mount(cache.get(caseId), caseId);
  if (inFlight.has(caseId)) return;
  inFlight.add(caseId);
  try {
    const payload = await api(`${ACTIVATION_PREFIX}${encodeURIComponent(caseId)}`);
    cache.set(caseId, payload);
    mount(payload, caseId);
  } catch (error) {
    const code = String(error?.data?.code || '');
    if (error?.status === 404 && code === 'NOT_M35_COMMERCE_CASE') return;
    if (error?.status === 404 && code === 'CASE_NOT_FOUND') return;
    mountWarning(caseId, code || 'ACTIVATION_NOT_VERIFIED');
  } finally {
    inFlight.delete(caseId);
  }
}

function schedule() {
  if (scheduled) return;
  scheduled = true;
  window.setTimeout(() => {
    scheduled = false;
    enhanceCase();
  }, 45);
}

document.addEventListener('click', event => {
  const route = event.target.closest('[data-m353-route]');
  if (route) {
    event.preventDefault();
    go(route.dataset.m353Route || '/casos');
    return;
  }
  const tab = event.target.closest('[data-m353-tab]');
  if (tab) {
    event.preventDefault();
    const tabName = tab.dataset.m353Tab || 'resumen';
    const caseId = tab.dataset.caseId || caseFromPath();
    if (typeof window.legalaiCaseTab === 'function') window.legalaiCaseTab(tabName, caseId);
  }
});

window.addEventListener('hashchange', schedule);
const app = document.getElementById('app');
if (app) new MutationObserver(schedule).observe(app, { childList:true, subtree:true });
schedule();
