import { api, esc, toast } from '../core.js';

const FACT_LABELS = {
  'goal.requested_outcome':'Qué quieres lograr',
  'employment.start_date':'Fecha de inicio',
  'employment.end_date':'Fecha de terminación',
  'employment.compensation_basis':'Base de remuneración',
  'employment.pending_concepts':'Conceptos pendientes',
  'traffic.notification_status':'Estado de notificación',
  'consumer.issue_type':'Tipo de problema de consumo',
  'payment.method':'Medio de pago',
  'lease.property_use':'Uso del inmueble',
  'lease.rent':'Canon informado',
  'credit_data.prior_claim_status':'Reclamación previa',
};

const VALUE_LABELS = {
  reclamar_o_solicitar:'Reclamar o solicitar una actuación',
  crear_o_formalizar:'Crear o formalizar un documento',
  revisar_o_verificar:'Revisar o verificar antes de actuar',
  NOT_NOTIFIED:'Indicas que no hubo notificación',
  NOTIFIED:'Indicas que sí hubo notificación',
  GARANTIA:'Garantía',
  RETRACTO:'Retracto',
  REVERSION_PAGO:'Reversión del pago',
  PRODUCTO_DEFECTUOSO:'Producto defectuoso',
  TARJETA_CREDITO:'Tarjeta de crédito',
  TARJETA_DEBITO:'Tarjeta débito',
  PSE:'PSE',
  TRANSFERENCIA:'Transferencia',
  EFECTIVO:'Efectivo',
  VIVIENDA_URBANA:'Vivienda urbana',
  PRIOR_CLAIM_ASSERTED:'Indicas que ya presentaste una reclamación',
};

const RISK_LABELS = {
  DEADLINE_RISK:'Posible término o fecha próxima',
  LITIGATION_ACTIVE:'Posible proceso judicial activo',
  CRIMINAL_MATTER:'Posible asunto penal',
  TAX_COMPLEXITY:'Posible complejidad tributaria',
  REGULATORY_COMPLEXITY:'Posible complejidad regulatoria',
  HIGH_VALUE:'Cuantía potencialmente relevante',
  MINOR_OR_VULNERABLE_PERSON:'Posible participación de menor o persona vulnerable',
  PERSONAL_DATA_SENSITIVE:'Posibles datos personales sensibles',
  MULTIPLE_PARTIES:'Posible pluralidad de partes',
  FACT_CONTRADICTION:'Posible contradicción entre hechos',
  DOCUMENT_CONTRADICTION:'Posible contradicción documental',
  INSUFFICIENT_INFORMATION:'Información todavía insuficiente',
  OUT_OF_JURISDICTION:'Posible asunto fuera de la jurisdicción prevista',
  OUT_OF_CATALOG:'Posible asunto fuera del catálogo actual',
  PROFESSIONAL_REVIEW_REQUIRED:'Posible necesidad de revisión profesional',
};

let currentSession = null;
let currentCode = '';
let mounting = false;
let scheduled = false;

function pathNow() { return location.hash.replace(/^#/, '') || '/'; }

function codeFromDom() {
  return String(document.querySelector('.m341-recovery code')?.textContent || '').trim();
}

function formatMoney(value) {
  try {
    return new Intl.NumberFormat('es-CO', { style:'currency', currency:'COP', maximumFractionDigits:0 }).format(Number(value || 0));
  } catch { return String(value || ''); }
}

function formatValue(value) {
  if (value == null) return 'Sin valor';
  if (typeof value === 'string') return VALUE_LABELS[value] || value;
  if (Array.isArray(value)) return value.map(item => VALUE_LABELS[item] || item).join(', ');
  if (typeof value === 'object') {
    if (value.amount_cop != null) return `${formatMoney(value.amount_cop)}${String(value.frequency || '').startsWith('MONTH') ? ' mensuales' : ''}`;
    return Object.entries(value).map(([key,item]) => `${key}: ${item}`).join(' · ');
  }
  return String(value);
}

function editValue(value) {
  if (value == null) return '';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object') {
    if (value.amount_cop != null) return String(value.amount_cop);
    return Object.values(value).join(' ');
  }
  return String(value);
}

function factLabel(fact) {
  return FACT_LABELS[fact.fact_type] || String(fact.fact_type || '').replaceAll('.', ' · ').replaceAll('_', ' ');
}

function providerLabel(provider={}) {
  if (provider.ai_enabled) return 'Extracción estructurada asistida por IA';
  return 'Detección automática conservadora';
}

function pendingFacts(session) {
  return (session.facts || []).filter(fact => fact.provenance === 'AI_INFERRED' && fact.confirmation_status === 'UNCONFIRMED');
}

function confirmedFacts(session) {
  return (session.confirmed_facts || []).filter(fact => fact.confirmation_status === 'CONFIRMED_BY_USER' || fact.confirmation_status === 'CONFIRMED_BY_LEGAL_REVIEW');
}

function disputedFacts(session) {
  return (session.facts || []).filter(fact => fact.provenance === 'AI_INFERRED' && fact.confirmation_status === 'DISPUTED');
}

function riskBanner(session) {
  const risks = session.risk_signals || [];
  if (!risks.length) return '';
  return `<div class="m342-risk-banner" role="note"><div><b>Hay ${risks.length === 1 ? 'una señal que conviene revisar' : 'señales que conviene revisar'}.</b><p>${risks.map(item => esc(RISK_LABELS[item.code] || item.code)).join(' · ')}</p><small>Son señales automáticas no confirmadas. No equivalen a una conclusión jurídica ni a un diagnóstico definitivo.</small></div></div>`;
}

function analyzePanel(session) {
  return `<section class="m342-panel m342-ready" aria-labelledby="m342-title"><div class="m342-panel-head"><div><span class="m342-step">Paso 2 de 4</span><h3 id="m342-title">Organicemos lo que ya nos contaste.</h3><p>Podemos identificar algunos datos explícitos para que no tengas que repetirlos después. Nada se usará como hecho confirmado sin tu revisión.</p></div><span class="m342-method">Detección conservadora</span></div><div class="m342-boundary"><span>Lo que sí hace</span><b>Estructura datos explícitos.</b><span>Lo que no hace</span><b>No decide tu solución ni emite concepto jurídico.</b></div><div class="m342-actions"><button class="btn primary" type="button" data-m342-analyze>Organizar lo que conté</button><button class="btn secondary" type="button" data-m341-mode="finder">Prefiero seguir con preguntas</button></div><div id="m342-status" class="m342-status" role="status" aria-live="polite"></div></section>`;
}

function noFactsPanel(session) {
  return `<section class="m342-panel" aria-labelledby="m342-title"><div class="m342-panel-head"><div><span class="m342-step">Paso 2 de 4</span><h3 id="m342-title">Necesitamos preguntarte un poco más.</h3><p>El análisis conservador no encontró datos suficientemente explícitos para proponértelos como hechos candidatos.</p></div><span class="m342-method">${esc(providerLabel(session.extraction_provider || {}))}</span></div>${riskBanner(session)}<div class="m342-actions"><button class="btn primary" type="button" data-m341-mode="finder">Continuar con preguntas generales</button><button class="btn secondary" type="button" data-m341-edit>Ampliar mi descripción</button></div></section>`;
}

function factCard(fact) {
  return `<article class="m342-fact-card" data-m342-fact-card data-fact-id="${esc(fact.fact_id)}"><div class="m342-fact-copy"><small>${esc(factLabel(fact))}</small><strong>${esc(formatValue(fact.value))}</strong><span>Detectado automáticamente · requiere tu revisión</span></div><fieldset><legend class="sr-only">Revisar ${esc(factLabel(fact))}</legend><label><input type="radio" name="decision-${esc(fact.fact_id)}" value="CONFIRM" data-m342-action> Sí, es correcto</label><label><input type="radio" name="decision-${esc(fact.fact_id)}" value="EDIT" data-m342-action> Quiero corregirlo</label><label><input type="radio" name="decision-${esc(fact.fact_id)}" value="DISPUTE" data-m342-action> No corresponde</label></fieldset><div class="m342-edit" hidden><label for="edit-${esc(fact.fact_id)}">Escribe el dato correcto</label><input class="input" id="edit-${esc(fact.fact_id)}" data-m342-edit-value value="${esc(editValue(fact.value))}" autocomplete="off"></div></article>`;
}

function reviewPanel(session) {
  const facts = pendingFacts(session);
  if (!facts.length) return noFactsPanel(session);
  return `<section class="m342-panel" aria-labelledby="m342-title"><div class="m342-panel-head"><div><span class="m342-step">Paso 2 de 4</span><h3 id="m342-title">Esto es lo que entendimos de tu relato.</h3><p>Revisa cada dato. Puedes confirmarlo, corregirlo o indicar que no corresponde. Un dato automático nunca se vuelve confirmado por sí solo.</p></div><span class="m342-method">${esc(providerLabel(session.extraction_provider || {}))}</span></div>${riskBanner(session)}<form id="m342-fact-form"><div class="m342-fact-list">${facts.map(factCard).join('')}</div><div class="m342-actions"><button class="btn primary" type="submit">Guardar mi revisión</button><button class="btn secondary" type="button" data-m341-edit>Corregir el relato completo</button></div><div id="m342-status" class="m342-status" role="status" aria-live="polite"></div></form><div class="m342-legal-boundary"><b>Aún no estamos recomendando una solución.</b><span>Primero consolidamos hechos. Después aplicaremos preguntas y reglas jurídicas trazables.</span></div></section>`;
}

function reviewedPanel(session) {
  const confirmed = confirmedFacts(session);
  const disputed = disputedFacts(session);
  return `<section class="m342-panel m342-reviewed" aria-labelledby="m342-title"><div class="m342-panel-head"><div><span class="m342-step complete">✓ Datos revisados</span><h3 id="m342-title">Ya distinguimos lo que confirmaste de lo que rechazaste.</h3><p>Los hechos confirmados conservan una procedencia distinta de los candidatos automáticos que les dieron origen.</p></div><span class="m342-method">Trazabilidad activa</span></div>${riskBanner(session)}${confirmed.length?`<div class="m342-confirmed-list">${confirmed.map(fact => `<div><small>${esc(factLabel(fact))}</small><b>${esc(formatValue(fact.value))}</b><span>Confirmado por ti</span></div>`).join('')}</div>`:'<div class="m342-empty"><b>No confirmaste datos de esta extracción.</b><span>Podemos continuar mediante preguntas para obtener la información que falta.</span></div>'}${disputed.length?`<p class="m342-disputed">Marcaste ${disputed.length} ${disputed.length===1?'dato':'datos'} como no correspondiente${disputed.length===1?'':'s'}.</p>`:''}<div class="m342-actions"><button class="btn primary" type="button" data-m341-mode="finder">Continuar con preguntas</button><button class="btn secondary" type="button" data-m341-edit>Editar mi descripción</button></div><div class="m342-legal-boundary"><b>Siguiente capa.</b><span>La información confirmada podrá compararse con los requisitos mínimos de los 11 Product Contracts. Si falta información, se preguntará antes de recomendar.</span></div></section>`;
}

function panelFor(session) {
  if (session.stage === 'FACTS_PENDING_CONFIRMATION') return reviewPanel(session);
  if (session.stage === 'FACTS_REVIEWED') return reviewedPanel(session);
  if (session.stage === 'FACTS_NOT_FOUND') return noFactsPanel(session);
  return analyzePanel(session);
}

function updateBaseCopy(root, session) {
  const heading = root.querySelector(':scope > div:first-child h2');
  const paragraph = root.querySelector(':scope > div:first-child p');
  const notice = root.querySelector('.legal-notice');
  if (session.stage === 'FACTS_PENDING_CONFIRMATION') {
    if (heading) heading.textContent = 'Tu descripción quedó guardada. Ahora revisa los datos que detectamos.';
    if (paragraph) paragraph.textContent = 'No asumimos que una detección automática sea correcta. Tú decides qué hechos representan tu situación.';
  } else if (session.stage === 'FACTS_REVIEWED') {
    if (heading) heading.textContent = 'Tu relato y tu revisión quedaron guardados.';
    if (paragraph) paragraph.textContent = 'Los datos confirmados y los candidatos descartados conservan trazabilidad separada.';
  } else if (session.stage === 'FACTS_NOT_FOUND') {
    if (heading) heading.textContent = 'Tu descripción quedó guardada.';
    if (paragraph) paragraph.textContent = 'No encontramos datos suficientemente explícitos para estructurarlos sin hacer suposiciones.';
  } else {
    if (heading) heading.textContent = 'Tu situación quedó registrada de forma segura.';
    if (paragraph) paragraph.textContent = 'Podemos organizar datos explícitos antes de hacerte más preguntas. Primero hechos; después orientación.';
  }
  if (notice) notice.innerHTML = '<b>Límite de esta etapa.</b> La estructuración automática no constituye concepto jurídico, recomendación de producto ni promesa de resultado.';
}

function render(root, session) {
  currentSession = session;
  updateBaseCopy(root, session);
  root.querySelector('.m342-panel')?.remove();
  const actions = root.querySelector('.m341-actions');
  if (actions) actions.insertAdjacentHTML('beforebegin', panelFor(session));
  else root.insertAdjacentHTML('beforeend', panelFor(session));
}

async function hydrate(root, code) {
  if (mounting) return;
  mounting = true;
  try {
    const session = await api('/api/m34/intake/recover', { method:'POST', body:JSON.stringify({ recovery_code:code }) });
    currentCode = code;
    render(root, session);
  } catch (error) {
    root.querySelector('.m342-panel')?.remove();
    root.insertAdjacentHTML('beforeend', `<div class="m342-status danger">${esc(error.message)}</div>`);
  } finally {
    mounting = false;
  }
}

async function analyze(button) {
  const root = button.closest('.m341-saved');
  if (!root || !currentCode) return;
  button.disabled = true;
  const original = button.textContent;
  button.textContent = 'Organizando…';
  const status = root.querySelector('#m342-status');
  try {
    const result = await api('/api/m34/intake/analyze', { method:'POST', body:JSON.stringify({ recovery_code:currentCode }) });
    render(root, result);
    toast(result.facts?.length ? 'Datos candidatos listos para revisar.' : 'Necesitamos un poco más de información.');
  } catch (error) {
    if (status) { status.className = 'm342-status danger'; status.textContent = error.message; }
    button.disabled = false;
    button.textContent = original;
  }
}

function toggleEdit(radio) {
  const card = radio.closest('[data-m342-fact-card]');
  const editor = card?.querySelector('.m342-edit');
  if (!editor) return;
  editor.hidden = radio.value !== 'EDIT';
  if (!editor.hidden) window.setTimeout(() => editor.querySelector('input')?.focus(), 20);
}

async function submitReview(form) {
  const root = form.closest('.m341-saved');
  const status = form.querySelector('#m342-status');
  const button = form.querySelector('button[type="submit"]');
  const decisions = [];
  let missing = null;
  for (const card of form.querySelectorAll('[data-m342-fact-card]')) {
    const selected = card.querySelector('input[data-m342-action]:checked');
    if (!selected) { missing = card; break; }
    const decision = { fact_id:card.dataset.factId, action:selected.value };
    if (selected.value === 'EDIT') {
      const value = String(card.querySelector('[data-m342-edit-value]')?.value || '').trim();
      if (!value) { missing = card; break; }
      decision.value = value;
    }
    decisions.push(decision);
  }
  if (missing) {
    status.className = 'm342-status danger';
    status.textContent = 'Revisa cada dato antes de guardar.';
    missing.scrollIntoView({ behavior:'smooth', block:'center' });
    missing.querySelector('input')?.focus();
    return;
  }
  button.disabled = true;
  button.textContent = 'Guardando revisión…';
  try {
    const result = await api('/api/m34/intake/facts/decide', { method:'POST', body:JSON.stringify({ recovery_code:currentCode, decisions }) });
    render(root, result);
    toast('Revisión de datos guardada.');
  } catch (error) {
    status.className = 'm342-status danger';
    status.textContent = error.message;
    button.disabled = false;
    button.textContent = 'Guardar mi revisión';
  }
}

function mount() {
  scheduled = false;
  if (pathNow() !== '/orientador') return;
  const root = document.querySelector('.m341-saved');
  const code = codeFromDom();
  if (!root || !code) return;
  if (root.dataset.m342Mounted === code && root.querySelector('.m342-panel')) return;
  root.dataset.m342Mounted = code;
  hydrate(root, code);
}

function scheduleMount() {
  if (scheduled) return;
  scheduled = true;
  window.setTimeout(mount, 30);
}

document.addEventListener('click', event => {
  const analyzeButton = event.target.closest('[data-m342-analyze]');
  if (analyzeButton) { event.preventDefault(); analyze(analyzeButton); }
});

document.addEventListener('change', event => {
  if (event.target.matches?.('input[data-m342-action]')) toggleEdit(event.target);
});

document.addEventListener('submit', event => {
  if (event.target?.id !== 'm342-fact-form') return;
  event.preventDefault();
  submitReview(event.target);
});

window.addEventListener('hashchange', () => {
  currentSession = null;
  currentCode = '';
  scheduleMount();
});

const app = document.getElementById('app');
if (app) new MutationObserver(scheduleMount).observe(app, { childList:true, subtree:true });
scheduleMount();
