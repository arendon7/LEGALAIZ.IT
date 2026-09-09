import { currentPath, dateText, esc, state } from '../core.js';
import { caseCard, friendlyCaseState, nextCaseAction } from './internal_m29_2.js';
import { clientHomeSummary, sortClientCasesForAttention } from './client_home_m38_5.js';

function productMap() {
  return Object.fromEntries((state.products || []).map(product => [product.code, product]));
}

function fingerprint(cases = [], documents = []) {
  return JSON.stringify({
    cases: cases.map(item => [item.id, item.status, item.review_status, item.risk, item.updated_at]),
    documents: documents.map(item => [item.id, item.status, item.updated_at]),
  });
}

function summaryMarkup(summary) {
  return [
    ['Expedientes activos', summary.openCases, 'Asuntos abiertos en tu espacio.'],
    ['Documentos', summary.documents, 'Borradores, versiones y entregables disponibles.'],
    ['En revisión', summary.reviewCases, 'Expedientes con control profesional en curso.'],
  ].map(([label, value, detail]) => `<article class="m390-summary-card"><small>${esc(label)}</small><strong>${value}</strong><span>${esc(detail)}</span></article>`).join('');
}

function priorityMarkup(item, products) {
  if (!item) {
    return `<section class="m390-priority-card m390-priority-empty"><div><span class="eyebrow">Para continuar</span><h2>No hay expedientes abiertos en este momento.</h2><p>Puedes iniciar un nuevo asunto o consultar el historial de tus expedientes anteriores.</p></div><div class="button-group"><button class="btn primary" data-action="go" data-route="/nuevo">Iniciar un asunto</button><button class="btn secondary" data-action="go" data-route="/casos">Ver expedientes</button></div></section>`;
  }

  const stage = friendlyCaseState(item);
  const action = nextCaseAction(item);
  const product = products[item.product_code] || {};
  return `<section class="m390-priority-card" data-m390-priority-case="${esc(item.id)}"><div class="m390-priority-copy"><div class="m390-priority-meta"><span class="eyebrow">Lo más útil para continuar</span><span class="badge ${esc(stage.cls)}">${esc(stage.label)}</span></div><h2>${esc(item.title)}</h2><p>${esc(product.title || item.product_code)} · Actualizado ${esc(dateText(item.updated_at))}</p><div class="m292-progress"><span class="progress-p${Math.min(100, Math.max(0, Math.round(stage.progress / 10) * 10))}"></span></div><small>${esc(action.text)}</small></div><button class="btn primary" data-action="go" data-route="/caso/${encodeURIComponent(item.id)}">${esc(action.button)}</button></section>`;
}

function capabilityMarkup() {
  const rows = [
    ['/nuevo', 'Iniciar un asunto', 'Comienza una solución guiada con el contexto necesario.'],
    ['/casos', 'Consultar expedientes', 'Revisa estado, soportes, documentos y próximos pasos.'],
    ['/documentos', 'Revisar documentos', 'Accede a borradores, versiones y entregables disponibles.'],
    ['/notificaciones', 'Ver notificaciones', 'Consulta novedades relacionadas con tu actividad jurídica.'],
  ];
  return rows.map(([route, title, detail]) => `<button class="m390-capability" data-action="go" data-route="${route}"><span aria-hidden="true">→</span><div><b>${esc(title)}</b><small>${esc(detail)}</small></div></button>`).join('');
}

function recentCasesMarkup(openCases, products) {
  if (!openCases.length) {
    return `<div class="m390-empty-list"><h3>Sin asuntos abiertos</h3><p>Cuando inicies o continúes un expediente, aparecerá aquí con su estado y siguiente paso.</p></div>`;
  }
  return `<div class="m292-case-grid">${openCases.slice(0, 4).map(item => caseCard(item, products[item.product_code] || {}, true)).join('')}</div>`;
}

export function applyEnterpriseHome() {
  if (state.user?.role !== 'client' || currentPath() !== '/') return;
  const page = document.querySelector('.m29-client-home, .m390-enterprise-home');
  if (!page) return;

  const cases = Array.isArray(state.cases) ? state.cases : [];
  const documents = Array.isArray(state.documents) ? state.documents : [];
  const currentFingerprint = fingerprint(cases, documents);
  if (page.classList.contains('m390-enterprise-home') && page.dataset.m390Fingerprint === currentFingerprint) return;

  const ordered = sortClientCasesForAttention(cases);
  const open = ordered.filter(item => friendlyCaseState(item).key !== 'closed');
  const priority = open[0] || null;
  const summary = clientHomeSummary(cases, documents);
  const products = productMap();
  const firstName = String(state.user?.name || '').trim().split(/\s+/)[0] || 'Hola';

  page.classList.remove('m29-client-home');
  page.classList.add('m390-enterprise-home');
  page.dataset.m390Fingerprint = currentFingerprint;
  page.innerHTML = `<section class="m390-enterprise-hero"><div class="m390-enterprise-hero-copy"><span class="eyebrow">Meridiano Empresas</span><h1>Hola, ${esc(firstName)}. Tu operación jurídica, en un solo lugar.</h1><p>Consulta expedientes, documentos, revisiones y próximos pasos sin perder el contexto de cada asunto.</p><div class="hero-actions"><button class="btn gold" data-action="go" data-route="/nuevo">Iniciar un asunto</button><button class="btn secondary" data-action="go" data-route="/casos">Ver expedientes</button></div></div><aside class="m390-enterprise-hero-side"><span>Vista actual</span><b>${summary.openCases}</b><small>${summary.openCases === 1 ? 'expediente activo' : 'expedientes activos'}</small><p>La plataforma muestra únicamente información ya registrada en tu espacio.</p></aside></section>
    <section class="m390-summary-grid">${summaryMarkup(summary)}</section>
    ${priorityMarkup(priority, products)}
    <section class="section-grid m390-home-grid"><div class="card span-8"><div class="card-header"><div><span class="eyebrow">Trabajo en curso</span><h2>Asuntos abiertos</h2><p>Ordenados por la etapa que puedes continuar y después por la actualización más reciente.</p></div><button class="btn secondary sm" data-action="go" data-route="/casos">Ver todos</button></div>${recentCasesMarkup(open, products)}</div><aside class="card span-4"><div class="card-header"><div><span class="eyebrow">Accesos directos</span><h2>Qué puedes hacer hoy</h2><p>Funciones disponibles actualmente en tu espacio jurídico.</p></div></div><div class="m390-capability-list">${capabilityMarkup()}</div></aside></section>
    <section class="m390-control-grid"><article><b>Contenido jurídico controlado</b><p>Cada solución conserva criterios de uso y señala cuándo corresponde una revisión profesional.</p></article><article><b>Versiones e historial</b><p>Los documentos y expedientes mantienen contexto para que puedas retomar el trabajo sin empezar de cero.</p></article><article><b>Seguimiento operativo</b><p>Las fechas mostradas para seguimiento son referencias operativas y no sustituyen la verificación de términos legales aplicables.</p></article></section>`;
}

let scheduled = false;
function scheduleApply() {
  if (scheduled) return;
  scheduled = true;
  queueMicrotask(() => {
    scheduled = false;
    applyEnterpriseHome();
  });
}

const observer = new MutationObserver(scheduleApply);
observer.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', scheduleApply);
window.addEventListener('popstate', scheduleApply);
scheduleApply();
