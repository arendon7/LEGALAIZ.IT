import { api, esc, go, state, toast } from '../core.js';

const CONTEXT_PREFIX = '/api/m35/commerce/context/';
const ORDER_LOOKUP_PREFIX = '/api/m35/commerce/order/';
const ORDER_PATH = '/api/m35/commerce/order';
const PAYMENT_PATH = '/api/m35/commerce/payment-intent';
const INVALIDATE_PATH = '/api/m35/commerce/invalidate';
const FINALIZE_PATH = '/api/m35/commerce/finalize';
const contexts = new Map();
let originalStartCheckout = null;
let originalPayCheckout = null;
let installed = false;
let scheduling = false;

function pathNow() { return location.hash.replace(/^#/, '') || '/'; }
function productFromPath(path = pathNow()) {
  const match = String(path).match(/^\/nuevo\/(CO-[A-Z]{2}-\d{3})$/);
  return match ? match[1] : '';
}
function checkoutFromPath(path = pathNow()) {
  const match = String(path).match(/^\/checkout\/(ORD-[A-Z0-9]+)$/i);
  return match ? match[1] : '';
}
function draftKey(code) { return `legalaizit:draft:${code}`; }
function orderKeyName(code, level) { return `legalaiz.m352.orderKey:${code}:${level}`; }
function paymentKeyName(linkId, provider) { return `legalaiz.m352.paymentKey:${linkId}:${provider}`; }
function newKey(prefix) {
  const token = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${token}`.slice(0, 120);
}
function getOrCreateKey(name, prefix) {
  let value = sessionStorage.getItem(name);
  if (!value) {
    value = newKey(prefix);
    sessionStorage.setItem(name, value);
  }
  return value;
}
function clearOrderKeys(code) {
  for (let i = sessionStorage.length - 1; i >= 0; i -= 1) {
    const key = sessionStorage.key(i) || '';
    if (key.startsWith(`legalaiz.m352.orderKey:${code}:`)) sessionStorage.removeItem(key);
  }
}

async function contextFor(code, force = false) {
  if (!code || !state.user || state.user.role !== 'client') return { linked:false, product_code:code };
  if (!force && contexts.has(code)) return contexts.get(code);
  const result = await api(`${CONTEXT_PREFIX}${encodeURIComponent(code)}`);
  contexts.set(code, result);
  return result;
}

async function linkedOrder(orderId) {
  try {
    return await api(`${ORDER_LOOKUP_PREFIX}${encodeURIComponent(orderId)}`);
  } catch (error) {
    const message = String(error?.message || '');
    if (/no pertenece a una continuidad m35\.2|COMMERCE_LINK_NOT_FOUND/i.test(message)) return null;
    throw error;
  }
}

function wizardConsent(context) {
  const code = productFromPath();
  if (!code || !context?.linked || state.wizard?.code !== code) return;
  const summary = document.querySelector('.checkout-summary');
  if (!summary) return;
  const container = summary.closest('.card') || summary.parentElement;
  if (!container) return;

  if (!container.querySelector('.m352-consent')) {
    summary.insertAdjacentHTML(
      'beforebegin',
      `<label class="m352-consent"><input type="checkbox" data-m352-checkout-consent><span><b>Confirmo que deseo continuar al checkout sandbox.</b><small>El nivel y el precio mostrados se vincularán a esta versión del formulario. No existe un cargo real.</small></span></label>`,
    );
  }

  const commerce = context.commerce;
  if (commerce && !container.querySelector('.m352-active-checkout')) {
    const canInvalidate = commerce.state === 'ORDER_CREATED' && !commerce.payment_intent_id && commerce.order_status === 'Pendiente';
    const control = canInvalidate
      ? `<button type="button" class="btn secondary" data-m352-invalidate data-link-id="${esc(commerce.link_id)}" data-product-code="${esc(code)}">Invalidar checkout y usar mis cambios</button>`
      : '<small>Este checkout ya avanzó al pago o expediente y no puede sustituirse silenciosamente.</small>';
    summary.insertAdjacentHTML(
      'beforebegin',
      `<div class="m352-active-checkout"><span>Checkout trazable activo</span><b>${esc(commerce.order_id)}</b><p>Si cambiaste respuestas o nivel de servicio, debes invalidar la orden pendiente antes de crear otra.</p>${control}</div>`,
    );
  }
}

async function enhanceWizard() {
  const code = productFromPath();
  if (!code || !state.user || state.user.role !== 'client') return;
  try {
    const context = await contextFor(code);
    if (context.linked) wizardConsent(context);
  } catch {
    // Fail closed in the override; visual enhancement can remain absent.
  }
}

async function enhanceCheckout() {
  const orderId = checkoutFromPath();
  if (!orderId || !state.user || state.user.role !== 'client') return;
  try {
    const link = await linkedOrder(orderId);
    if (!link) return;
    const card = document.querySelector('.checkout-action-card');
    if (!card || card.querySelector('.m352-checkout-trace')) return;
    const order = await api(`/api/checkout/orders/${encodeURIComponent(orderId)}`);
    const paid = ['Pagado (sandbox)'].includes(order.status);
    const completed = order.status === 'Completada' && order.case_id;
    const consent = paid && !completed
      ? `<label class="m352-consent m352-case-consent"><input type="checkbox" data-m352-case-consent><span><b>Confirmo la creación del expediente.</b><small>Usaremos exactamente la versión del formulario vinculada a este checkout.</small></span></label>`
      : '';
    card.insertAdjacentHTML(
      'afterbegin',
      `<div class="m352-checkout-trace"><span>Continuidad protegida M35.2</span><p>${completed ? 'La orden ya está vinculada al expediente.' : paid ? 'El pago sandbox está confirmado. Crear el expediente requiere una acción separada.' : 'El pago se registrará mediante un intento sandbox firmado antes de habilitar el expediente.'}</p>${consent}</div>`,
    );
  } catch {
    // Never fall back to legacy behavior because enhancement failed; override handles it.
  }
}

async function tracedStartCheckout() {
  const w = state.wizard;
  if (!w || !w.result || !w.serviceLevel) return originalStartCheckout?.();
  let context;
  try {
    context = await contextFor(w.code, true);
  } catch (error) {
    toast('No pudimos verificar la continuidad segura del diagnóstico.', 'danger');
    return;
  }
  if (!context.linked) return originalStartCheckout?.();
  const consent = document.querySelector('[data-m352-checkout-consent]');
  if (!consent?.checked) {
    toast('Confirma el checkout sandbox antes de continuar.', 'danger');
    consent?.focus();
    return;
  }
  w.caseTitle = document.getElementById('case-title')?.value.trim() || w.caseTitle || w.product.title;
  try {
    await api('/api/drafts', {
      method:'POST',
      body:JSON.stringify({
        product_code:w.code,
        answers:w.answers,
        current_step:w.step,
        title:w.caseTitle,
        result:{...w.result, service_level:w.serviceLevel},
      }),
    });
    const keyName = orderKeyName(w.code, w.serviceLevel);
    const order = await api(ORDER_PATH, {
      method:'POST',
      body:JSON.stringify({
        product_code:w.code,
        service_level:w.serviceLevel,
        idempotency_key:getOrCreateKey(keyName, 'm352-order'),
        checkout_consent:true,
      }),
    });
    contexts.delete(w.code);
    go(`/checkout/${encodeURIComponent(order.order_id)}`);
  } catch (error) {
    toast(error.message || 'No fue posible iniciar el checkout trazable.', 'danger');
    contextFor(w.code, true).then(wizardConsent).catch(() => {});
  }
}

function providerFor(method) {
  const value = String(method || '').toLowerCase();
  if (value.includes('pse')) return 'sandbox_pse';
  if (value.includes('sin cobro')) return 'sandbox_free';
  return 'sandbox_card';
}

async function tracedPayOrFinalize(orderId, method) {
  let link;
  try {
    link = await linkedOrder(orderId);
  } catch (error) {
    toast('No pudimos verificar la trazabilidad de esta orden.', 'danger');
    return;
  }
  if (!link) return originalPayCheckout?.(orderId, method);
  if (link.state === 'INVALIDATED') {
    toast('Este checkout fue invalidado. Regresa al formulario.', 'danger');
    return go(`/nuevo/${encodeURIComponent(link.product_code)}`);
  }
  try {
    const order = await api(`/api/checkout/orders/${encodeURIComponent(orderId)}`);
    if (order.status === 'Completada' && order.case_id) return go(`/caso/${encodeURIComponent(order.case_id)}`);
    const paid = order.status === 'Pagado (sandbox)';
    if (!paid) {
      const provider = providerFor(method);
      const keyName = paymentKeyName(link.link_id, provider);
      const payment = await api(PAYMENT_PATH, {
        method:'POST',
        body:JSON.stringify({
          link_id:link.link_id,
          provider,
          idempotency_key:getOrCreateKey(keyName, 'm352-payment'),
        }),
      });
      const intentId = payment.payment_intent?.id;
      if (!intentId) throw new Error('El intento de pago no quedó vinculado.');
      await api(`/api/payment-intents/${encodeURIComponent(intentId)}/simulate`, {
        method:'POST',
        body:JSON.stringify({ outcome:'approved' }),
      });
      toast('Pago sandbox confirmado. Ahora confirma la creación del expediente.');
      window.dispatchEvent(new HashChangeEvent('hashchange'));
      return;
    }

    const consent = document.querySelector('[data-m352-case-consent]');
    if (!consent?.checked) {
      toast('Confirma expresamente la creación del expediente.', 'danger');
      consent?.focus();
      return;
    }
    const finalized = await api(FINALIZE_PATH, {
      method:'POST',
      body:JSON.stringify({ link_id:link.link_id, case_consent:true }),
    });
    localStorage.removeItem(draftKey(link.product_code));
    clearOrderKeys(link.product_code);
    state.wizard = null;
    state.checkoutOrder = null;
    const suffix = finalized.documents_ready === false ? '?m352_documents=pending' : '';
    location.hash = `#/caso/${encodeURIComponent(finalized.case_id)}${suffix}`;
    location.reload();
  } catch (error) {
    toast(error.message || 'No fue posible completar la transición trazable.', 'danger');
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  }
}

async function invalidateCheckout(button) {
  const linkId = button.dataset.linkId || '';
  const code = button.dataset.productCode || productFromPath();
  if (!linkId || !code) return;
  button.disabled = true;
  try {
    await api(INVALIDATE_PATH, { method:'POST', body:JSON.stringify({ link_id:linkId }) });
    clearOrderKeys(code);
    contexts.delete(code);
    toast('Checkout pendiente invalidado. Tus respuestas siguen en el formulario.');
    document.querySelector('.m352-active-checkout')?.remove();
    const context = await contextFor(code, true);
    wizardConsent(context);
  } catch (error) {
    toast(error.message || 'No fue posible invalidar este checkout.', 'danger');
    button.disabled = false;
  }
}

function installOverrides() {
  if (installed) return;
  if (typeof window.legalaiStartCheckout !== 'function' || typeof window.legalaiPayCheckout !== 'function') {
    window.setTimeout(installOverrides, 50);
    return;
  }
  originalStartCheckout = window.legalaiStartCheckout;
  originalPayCheckout = window.legalaiPayCheckout;
  window.legalaiStartCheckout = tracedStartCheckout;
  window.legalaiPayCheckout = tracedPayOrFinalize;
  installed = true;
}

function enhance() {
  scheduling = false;
  enhanceWizard();
  enhanceCheckout();
}
function schedule() {
  if (scheduling) return;
  scheduling = true;
  window.setTimeout(enhance, 40);
}

document.addEventListener('click', event => {
  const button = event.target.closest('[data-m352-invalidate]');
  if (button) {
    event.preventDefault();
    invalidateCheckout(button);
  }
});
window.addEventListener('hashchange', schedule);
const app = document.getElementById('app');
if (app) new MutationObserver(schedule).observe(app, { childList:true, subtree:true });
installOverrides();
schedule();
