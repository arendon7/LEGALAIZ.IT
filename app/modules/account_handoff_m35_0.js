import { api, esc, go, state, toast } from '../core.js';

const CLAIM_KEY = 'legalaiz.m35.pendingClaim';
const NEXT_ROUTE_KEY = 'legalaiz.m35.nextRoute';
let scheduled = false;
let claiming = false;

function pathNow() { return location.hash.replace(/^#/, '') || '/'; }
function codeFromDom() { return String(document.querySelector('.m341-recovery code')?.textContent || '').trim(); }
function pendingCode() { return String(sessionStorage.getItem(CLAIM_KEY) || '').trim(); }
function hasPendingClaim() { return Boolean(pendingCode()); }

function clearPendingClaim() {
  sessionStorage.removeItem(CLAIM_KEY);
}

function storePendingClaim(code) {
  const normalized = String(code || '').trim();
  if (!normalized) throw new Error('No encontramos el código de continuidad de este diagnóstico.');
  sessionStorage.setItem(CLAIM_KEY, normalized);
}

function injectRecommendationContinue() {
  if (pathNow() !== '/orientador') return;
  const actions = document.querySelector('.m344-primary .m344-actions');
  if (!actions || actions.querySelector('[data-m350-continue]')) return;
  actions.insertAdjacentHTML(
    'afterbegin',
    '<button class="btn gold m350-continue" type="button" data-m350-continue>Continuar con esta solución</button>',
  );
  const boundary = document.querySelector('.m344-boundary');
  if (boundary && !document.querySelector('.m350-account-note')) {
    boundary.insertAdjacentHTML(
      'afterend',
      '<div class="m350-account-note"><b>Tu diagnóstico ya aportó valor antes de pedirte una cuenta.</b><span>Al continuar, vincularemos esta recomendación a tu espacio privado. Después completarás únicamente el fulfillment necesario antes de checkout y expediente.</span></div>',
    );
  }
}

function loginContinuationBanner() {
  if (pathNow() !== '/login' || !hasPendingClaim()) return;
  const card = document.querySelector('.login-card');
  if (!card || card.querySelector('.m350-login-continuation')) return;
  const form = card.querySelector('#login-form');
  const block = `<section class="m350-login-continuation" aria-label="Continuar recomendación"><span>Recomendación lista</span><b>Ingresa o crea una cuenta para conservar este diagnóstico.</b><p>No volveremos a pedirte el relato inicial. El contexto detallado permanece cifrado y el formulario completo continuará después del acceso.</p><button class="btn secondary btn-block" type="button" data-m350-register>Crear una cuenta nueva</button><button class="m350-cancel-link" type="button" data-m350-cancel>Cancelar esta continuidad</button></section>`;
  if (form) form.insertAdjacentHTML('afterend', block);
  else card.insertAdjacentHTML('beforeend', block);
}

function registrationForm() {
  const card = document.querySelector('.login-card');
  if (!card) return;
  card.innerHTML = `<button class="login-back-link" type="button" data-m350-back-login>← Ya tengo una cuenta</button><span class="eyebrow">Crea tu espacio privado</span><h2>Guarda tu recomendación y continúa.</h2><p class="lead">La cuenta se solicita ahora porque ya completaste el diagnóstico inicial. El siguiente paso es vincularlo de forma segura y completar el formulario de la solución.</p><form id="m350-register-form"><div class="field"><label for="m350-name">Nombre completo</label><input id="m350-name" class="input" autocomplete="name" maxlength="120" required></div><div class="field"><label for="m350-email">Correo electrónico</label><input id="m350-email" class="input" type="email" autocomplete="email" maxlength="180" required></div><div class="field"><label for="m350-password">Contraseña</label><input id="m350-password" class="input" type="password" autocomplete="new-password" required><span class="field-hint">Usa una contraseña robusta y distinta de otros servicios.</span></div><label class="m350-consent"><input id="m350-consent" type="checkbox" required><span>Autorizo el tratamiento de mis datos para crear la cuenta y continuar este proceso jurídico.</span></label><button class="btn primary btn-block" type="submit">Crear cuenta y continuar</button><div id="m350-register-status" class="m350-status" role="status" aria-live="polite"></div></form><div class="legal-notice"><b>Uso responsable.</b> La cuenta protege el acceso al proceso; no convierte la recomendación en concepto definitivo ni sustituye la revisión profesional cuando corresponda.</div>`;
  window.setTimeout(() => document.getElementById('m350-name')?.focus(), 20);
}

async function claimPending({ reloadAfter = false } = {}) {
  const code = pendingCode();
  if (!code || !state.user || !state.csrf || claiming) return null;
  claiming = true;
  try {
    const result = await api('/api/m35/intake/claim', {
      method: 'POST',
      body: JSON.stringify({ recovery_code: code }),
    });
    clearPendingClaim();
    sessionStorage.setItem(NEXT_ROUTE_KEY, result.next_route || `/nuevo/${result.product_code}`);
    toast(result.idempotent ? 'El diagnóstico ya estaba vinculado a tu cuenta.' : 'Diagnóstico vinculado a tu cuenta.');
    if (reloadAfter) {
      location.hash = `#${result.next_route || `/nuevo/${result.product_code}`}`;
      location.reload();
      return result;
    }
    const next = sessionStorage.getItem(NEXT_ROUTE_KEY) || result.next_route;
    sessionStorage.removeItem(NEXT_ROUTE_KEY);
    if (next) go(next);
    return result;
  } catch (error) {
    toast(error.message, 'danger');
    throw error;
  } finally {
    claiming = false;
  }
}

async function registerAndClaim(form) {
  const button = form.querySelector('button[type="submit"]');
  const status = form.querySelector('#m350-register-status');
  button.disabled = true;
  button.textContent = 'Creando cuenta…';
  try {
    const result = await api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: document.getElementById('m350-name').value,
        email: document.getElementById('m350-email').value,
        password: document.getElementById('m350-password').value,
        consent: document.getElementById('m350-consent').checked,
      }),
    });
    state.user = result.user;
    state.csrf = result.csrf_token;
    state.mfaEnrollmentRequired = Boolean(result.mfa_enrollment_required);
    if (state.mfaEnrollmentRequired) throw new Error('La cuenta requiere completar MFA antes de transferir el diagnóstico.');
    button.textContent = 'Vinculando diagnóstico…';
    await claimPending({ reloadAfter: true });
  } catch (error) {
    if (status) {
      status.className = 'm350-status danger';
      status.textContent = error.message;
    }
    button.disabled = false;
    button.textContent = 'Crear cuenta y continuar';
  }
}

async function continueRecommendation(button) {
  const code = codeFromDom();
  try {
    storePendingClaim(code);
  } catch (error) {
    toast(error.message, 'danger');
    return;
  }
  button.disabled = true;
  if (state.user) {
    try { await claimPending(); }
    catch { button.disabled = false; }
    return;
  }
  toast('Ingresa o crea una cuenta para guardar esta recomendación.');
  go('/login');
}

function resumeAfterExistingLogin() {
  if (!state.user || !state.csrf || !hasPendingClaim() || claiming) return;
  claimPending().catch(() => {});
}

function resumeReloadedRoute() {
  if (!state.user) return;
  const next = sessionStorage.getItem(NEXT_ROUTE_KEY);
  if (!next) return;
  sessionStorage.removeItem(NEXT_ROUTE_KEY);
  if (pathNow() !== next) go(next);
}

function mount() {
  scheduled = false;
  injectRecommendationContinue();
  loginContinuationBanner();
  resumeReloadedRoute();
  if (pathNow() !== '/login') resumeAfterExistingLogin();
}

function scheduleMount() {
  if (scheduled) return;
  scheduled = true;
  window.setTimeout(mount, 60);
}

document.addEventListener('click', event => {
  const continueButton = event.target.closest('[data-m350-continue]');
  if (continueButton) { continueRecommendation(continueButton); return; }
  if (event.target.closest('[data-m350-register]')) { registrationForm(); return; }
  if (event.target.closest('[data-m350-cancel]')) {
    clearPendingClaim();
    document.querySelector('.m350-login-continuation')?.remove();
    toast('Continuidad cancelada. Tu diagnóstico anónimo conserva su código original mientras siga vigente.');
    return;
  }
  if (event.target.closest('[data-m350-back-login]')) {
    location.reload();
  }
});

document.addEventListener('submit', event => {
  if (event.target?.id !== 'm350-register-form') return;
  event.preventDefault();
  registerAndClaim(event.target);
});

window.addEventListener('hashchange', scheduleMount);
const app = document.getElementById('app');
if (app) new MutationObserver(scheduleMount).observe(app, { childList: true, subtree: true });
scheduleMount();
