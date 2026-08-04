'use strict';

export const app = document.getElementById('app');
const toastEl = document.getElementById('toast');
export const dialogRoot = document.getElementById('dialog-root');
let dialogPreviousFocus = null;

export const state = {
  user: null,
  csrf: null,
  products: [],
  experiences: [],
  cases: [],
  documents: [],
  activeCaseTab: 'resumen',
  solutionFilter: 'Todos',
  solutionQuery: '',
  caseFilter: 'Activos',
  wizard: null,
  clientIntakeResult: null,
  clientIntakeNarrative: '',
  checkoutOrder: null,
  mobileNav: false,
  contractualLibrary: null,
  playbookLibrary: null,
  config: null,
  approval: null,
  rcReadiness: null,
  globalSearchQuery: '',
  mfaEnrollmentRequired: false,
  lastVisitedRoute: '/',
};

export const roleLabels = { client: 'Cliente', specialist: 'Especialista jurídico', admin: 'Administración' };
export const riskLabels = { green: 'Riesgo bajo', yellow: 'Revisión recomendada', red: 'Revisión obligatoria' };
export const riskClass = { green: 'success', yellow: 'warning', red: 'danger' };
export const icons = {
  home: '⌂', new: '＋', cases: '▣', docs: '▤', solutions: '◇', review: '✓', sources: '⌕', catalog: '▦', quality: '◈', settings: '⚙', account: '○', folder: '▰', shield: '◆', search: '⌕', library: '▥', operation: '◎', journey: '→', bell: '◉', help: '?'
};

export const accountOptions = [
  ['juan@demo.legalaiz.it', 'Juan Pérez · Cliente'],
  ['maria@demo.legalaiz.it', 'María Fernández · Laboral'],
  ['carlos@demo.legalaiz.it', 'Carlos López · Contratos'],
  ['laura@demo.legalaiz.it', 'Laura Gómez · Tránsito'],
  ['ana@demo.legalaiz.it', 'Ana Torres · Administración'],
];

export const contractualProductCodes = new Set(['CO-EM-003', 'CO-LA-002', 'CO-EM-004', 'CO-AR-001']);
export const playbookProductCodes = new Set(['CO-LA-001', 'CO-SA-001', 'CO-CD-001', 'CO-CD-003', 'CO-CD-004', 'CO-TR-001', 'CO-TR-002']);

export const esc = (value = '') => String(value).replace(/[&<>'"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));
export const money = value => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(value || 0));
export const dateText = value => {
  if (!value) return 'Sin fecha';
  try { return new Date(value).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' }); }
  catch { return String(value); }
};
export const humanize = value => String(value || '').replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
export const initials = name => String(name || 'U').split(/\s+/).slice(0, 2).map(x => x[0] || '').join('').toUpperCase();
export const currentPath = () => location.hash.replace(/^#/, '') || '/';
export const go = path => { location.hash = `#${path}`; };
window.legalaiGo = go;

export function toast(message, mode = 'default') {
  toastEl.textContent = message;
  toastEl.dataset.mode = mode;
  toastEl.classList.add('show');
  clearTimeout(toastEl._timer);
  toastEl._timer = setTimeout(() => toastEl.classList.remove('show'), 3200);
}

export async function api(path, options = {}) {
  const method = String(options.method || 'GET').toUpperCase();
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData) && options.body !== undefined) headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  if (!['GET', 'HEAD'].includes(method) && state.csrf) headers['X-CSRF-Token'] = state.csrf;
  const response = await fetch(path, { credentials: 'same-origin', ...options, method, headers });
  let data = {};
  try { data = await response.json(); } catch { data = {}; }
  if (response.status === 401 && path !== '/api/auth/login') {
    state.user = null; state.csrf = null; go('/login');
  }
  if (!response.ok) {
    const detail = typeof data.error === 'object' ? (data.error.message || data.error.code) : data.error;
    const error = new Error(detail || `No fue posible completar la operación (${response.status}).`);
    error.status = response.status; error.data = data; throw error;
  }
  return data;
}

export function openDialog({ title, subtitle = '', body = '', actions = '' }) {
  dialogPreviousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  dialogRoot.innerHTML = `<div class="dialog-backdrop" role="presentation" data-action="dialog-backdrop">
    <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title" aria-describedby="dialog-subtitle">
      <header class="dialog-head"><div><h2 id="dialog-title">${esc(title)}</h2>${subtitle ? `<p id="dialog-subtitle">${esc(subtitle)}</p>` : '<span id="dialog-subtitle" class="sr-only">Ventana de diálogo</span>'}</div><button class="icon-btn" aria-label="Cerrar" data-action="close-dialog">×</button></header>
      <div class="dialog-body">${body}</div>
      ${actions ? `<footer class="dialog-actions">${actions}</footer>` : ''}
    </section>
  </div>`;
  setTimeout(() => dialogRoot.querySelector('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')?.focus(), 20);
}

export function closeDialog() {
  dialogRoot.innerHTML = '';
  const target = dialogPreviousFocus;
  dialogPreviousFocus = null;
  setTimeout(() => target?.isConnected && target.focus({ preventScroll: true }), 20);
}

document.addEventListener('keydown', event => {
  if (event.key !== 'Tab' || !dialogRoot.innerHTML) return;
  const focusable = [...dialogRoot.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')].filter(element => element.getClientRects().length);
  if (!focusable.length) return;
  const first = focusable[0], last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
});
window.legalaiCloseDialog = closeDialog;
