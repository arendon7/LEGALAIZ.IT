import { api, esc, state } from '../core.js';

const NOTICE_KEY = 'legalaiz.m351.bridgeNotice';
let activeRoute = '';
let attempted = false;
let inFlight = false;

function pathNow() { return location.hash.replace(/^#/, '') || '/'; }
function productFromPath(path = pathNow()) {
  const match = String(path).match(/^\/nuevo\/(CO-[A-Z]{2}-\d{3})$/);
  return match ? match[1] : '';
}
function draftKey(code) { return `legalaizit:draft:${code}`; }
function parseStored(code) {
  try { return JSON.parse(localStorage.getItem(draftKey(code)) || 'null') || {}; }
  catch { return {}; }
}
function stable(value) { return JSON.stringify(value, Object.keys(value || {}).sort()); }
function money(value) { return new Intl.NumberFormat('es-CO', { style:'currency', currency:'COP', maximumFractionDigits:0 }).format(Number(value || 0)); }

function mergeIntoLocal(code, result) {
  const local = parseStored(code);
  const serverAnswers = result?.answers && typeof result.answers === 'object' ? result.answers : {};
  const localAnswers = local?.answers && typeof local.answers === 'object' ? local.answers : {};
  const mergedAnswers = { ...serverAnswers, ...localAnswers };
  const next = {
    ...local,
    step: Number.isInteger(local.step) ? local.step : 0,
    page: Number.isInteger(local.page) ? local.page : 0,
    answers: mergedAnswers,
    saved_at: local.saved_at || new Date().toISOString(),
  };
  const changed = stable(mergedAnswers) !== stable(localAnswers);
  localStorage.setItem(draftKey(code), JSON.stringify(next));
  return changed;
}

function noticePayload(result) {
  return {
    product_code: result.product_code,
    draft_id: result.draft_id,
    eligible_prefill_count: Number(result.eligible_prefill_count || 0),
    prefilled_question_ids: Array.isArray(result.prefilled_question_ids) ? result.prefilled_question_ids : [],
    notice: result.notice || '',
    offer: result.offer || {},
  };
}

function renderNotice(payload) {
  const code = productFromPath();
  if (!code || !payload || payload.product_code !== code) return;
  const anchor = document.querySelector('.wizard-overview');
  if (!anchor || document.querySelector('.m351-bridge-card')) return;
  const count = Number(payload.eligible_prefill_count || 0);
  const levels = (payload.offer?.service_levels || []).filter(level => level.checkout_enabled);
  const pricing = levels.length
    ? `<div class="m351-offer-levels">${levels.map(level => `<span><small>${esc(level.label)}</small><b>${esc(level.price_label || money(level.price))}</b></span>`).join('')}</div>`
    : '';
  const reuseCopy = count
    ? `Reutilizamos ${count} ${count === 1 ? 'respuesta' : 'respuestas'} de tu diagnóstico porque tienen equivalencia directa con este formulario. Puedes corregirlas.`
    : 'Vinculamos tu diagnóstico, pero no prellenamos datos cuya equivalencia jurídica no era exacta. Te los preguntaremos aquí.';
  anchor.insertAdjacentHTML('afterend', `<section class="m351-bridge-card" aria-label="Continuidad del diagnóstico"><div class="m351-bridge-head"><span>Diagnóstico vinculado</span><b>No empiezas de cero</b></div><p>${esc(reuseCopy)}</p>${pricing}<small class="m351-pricing-note">${esc(payload.offer?.pricing_notice || 'Valores de referencia del entorno sandbox; no constituyen una oferta comercial pública definitiva.')}</small></section>`);
}

function restoreNotice() {
  try {
    const payload = JSON.parse(sessionStorage.getItem(NOTICE_KEY) || 'null');
    if (payload) renderNotice(payload);
  } catch {}
}

async function prepareRoute() {
  const path = pathNow();
  if (path !== activeRoute) {
    activeRoute = path;
    attempted = false;
  }
  const code = productFromPath(path);
  if (!code) { attempted = false; return; }
  restoreNotice();
  if (attempted || inFlight || !state.user || state.user.role !== 'client' || state.wizard?.code !== code) return;
  attempted = true;
  inFlight = true;
  try {
    const result = await api('/api/m35/fulfillment/prepare', {
      method: 'POST',
      body: JSON.stringify({ product_code: code }),
    });
    const payload = noticePayload(result);
    sessionStorage.setItem(NOTICE_KEY, JSON.stringify(payload));
    const changed = mergeIntoLocal(code, result);
    if (changed) {
      sessionStorage.setItem('legalaiz.m351.reloadReason', result.draft_id || code);
      location.reload();
      return;
    }
    renderNotice(payload);
  } catch (error) {
    // A direct product visit without an M35 handoff is a normal path. Do not show a false error.
    if (!/diagnóstico transferido|NO_TRANSFERRED_INTAKE/i.test(String(error?.message || ''))) {
      console.warn('M35.1 fulfillment bridge unavailable without altering the wizard.');
    }
  } finally {
    inFlight = false;
  }
}

function schedule() { window.setTimeout(prepareRoute, 50); }
window.addEventListener('hashchange', schedule);
const app = document.getElementById('app');
if (app) new MutationObserver(schedule).observe(app, { childList:true, subtree:true });
schedule();
