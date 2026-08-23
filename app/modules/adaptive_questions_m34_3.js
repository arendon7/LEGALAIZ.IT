import { api, esc, toast } from '../core.js';

let scheduled = false;
let busy = false;
let currentCode = '';
let currentStep = null;

function pathNow() { return location.hash.replace(/^#/, '') || '/'; }
function codeFromDom() { return String(document.querySelector('.m341-recovery code')?.textContent || '').trim(); }

function minimumMissing(step) {
  const perProduct = Object.values(step?.sufficiency?.per_product || {});
  if (!perProduct.length) return null;
  return Math.min(...perProduct.map(item => (item.missing || []).length));
}

function semanticProgress(step) {
  const missing = minimumMissing(step);
  if (missing == null) return '';
  if (missing === 0) return '<span class="m343-progress complete">Información mínima reunida</span>';
  return `<span class="m343-progress">${missing === 1 ? 'Nos falta 1 dato importante' : `Nos faltan ${missing} datos importantes`} para poder pasar al siguiente análisis.</span>`;
}

function inputFor(question) {
  const options = question.options || [];
  if (question.answer_type === 'select' || question.answer_type === 'boolean') {
    return `<fieldset class="m343-options"><legend class="sr-only">${esc(question.prompt)}</legend>${options.map((item,index)=>`<label class="m343-option"><input type="radio" name="m343-answer" value="${esc(item.value)}" ${index===0?'':''} required><span>${esc(item.label)}</span></label>`).join('')}</fieldset>`;
  }
  if (question.answer_type === 'multiselect') {
    return `<fieldset class="m343-options"><legend class="sr-only">${esc(question.prompt)}</legend>${options.map(item=>`<label class="m343-option"><input type="checkbox" name="m343-answer" value="${esc(item.value)}"><span>${esc(item.label)}</span></label>`).join('')}</fieldset>`;
  }
  if (question.answer_type === 'date') {
    return '<label class="m343-field"><span>Fecha</span><input class="input" type="date" data-m343-value required></label>';
  }
  if (question.answer_type === 'money_cop') {
    return '<label class="m343-field"><span>Valor aproximado en pesos colombianos</span><input class="input" type="text" inputmode="numeric" autocomplete="off" placeholder="Ej. 1.800.000" data-m343-value required></label>';
  }
  if (question.answer_type === 'number') {
    return '<label class="m343-field"><span>Valor</span><input class="input" type="number" data-m343-value required></label>';
  }
  if (question.answer_type === 'textarea') {
    return '<label class="m343-field"><span>Respuesta</span><textarea class="input m343-textarea" maxlength="1200" data-m343-value required></textarea></label>';
  }
  return '<label class="m343-field"><span>Respuesta</span><input class="input" type="text" maxlength="1200" autocomplete="off" data-m343-value required></label>';
}

function questionTitle(action) {
  if (action === 'ROUTE_TOPIC') return 'Ubiquemos primero el tema de tu situación.';
  if (action === 'CONFIRM_RISK') return 'Antes de seguir, confirmemos una señal importante.';
  return 'Nos falta un dato para orientar mejor el siguiente paso.';
}

function questionPanel(step) {
  const question = step.question || {};
  const riskCopy = step.action === 'CONFIRM_RISK'
    ? '<div class="m343-boundary"><b>Confirmar esta señal no equivale a una conclusión jurídica.</b><span>La usamos únicamente para decidir si la automatización puede continuar responsablemente.</span></div>'
    : '<div class="m343-boundary"><b>Una respuesta no determina por sí sola la solución.</b><span>Se combina después con los demás hechos, reglas y controles aplicables.</span></div>';
  return `<section class="m343-panel" aria-labelledby="m343-title"><div class="m343-head"><div><span class="m343-step">Paso 3 de 4 · Datos para orientar</span><h3 id="m343-title">${esc(questionTitle(step.action))}</h3>${semanticProgress(step)}</div><span class="m343-badge">Pregunta adaptativa</span></div><form id="m343-question-form" data-question-id="${esc(question.question_id || '')}" data-answer-type="${esc(question.answer_type || '')}"><div class="m343-question-copy"><h4>${esc(question.prompt || '')}</h4>${question.help_text?`<p>${esc(question.help_text)}</p>`:''}</div>${inputFor(question)}${question.why_asked?`<details class="m343-why"><summary>¿Por qué preguntamos esto?</summary><p>${esc(question.why_asked)}</p></details>`:''}${riskCopy}<div class="m343-actions"><button class="btn primary" type="submit">Continuar</button><button class="btn secondary" type="button" data-m341-edit>Corregir mi relato</button></div><div id="m343-status" class="m343-status" role="status" aria-live="polite"></div></form></section>`;
}

function readyPanel(step) {
  return `<section class="m343-panel m343-ready" aria-labelledby="m343-title"><div class="m343-head"><div><span class="m343-step complete">✓ Información mínima reunida</span><h3 id="m343-title">Ya tenemos una base suficiente para pasar al recomendador.</h3><p>Esto significa que podemos evaluar qué solución del catálogo encaja mejor con los hechos disponibles. <strong>Todavía no hemos emitido una recomendación.</strong></p></div><span class="m343-badge">Gate superado</span></div><div class="m343-summary"><b>Qué ocurrirá en la siguiente capa</b><span>Se compararán los hechos utilizables con los Product Contracts, exclusiones, riesgos y reglas trazables antes de mostrar una solución.</span></div><div class="m343-actions"><button class="btn secondary" type="button" data-action="go" data-route="/soluciones">Explorar las soluciones actuales</button><button class="btn ghost" type="button" data-m341-edit>Corregir mi relato</button></div></section>`;
}

function escalationPanel(step) {
  const urgent = (step.reason_codes || []).includes('DEADLINE_RISK');
  return `<section class="m343-panel m343-escalate" aria-labelledby="m343-title"><div class="m343-head"><div><span class="m343-step caution">Revisión adicional</span><h3 id="m343-title">${urgent?'Hay una señal de tiempo que aconseja revisión profesional.':'No es responsable continuar automáticamente con la información disponible.'}</h3><p>Preferimos detener la automatización antes que presentar una solución que podría ignorar un riesgo, una contradicción o información todavía insuficiente.</p></div><span class="m343-badge">Escalamiento seguro</span></div><div class="m343-boundary"><b>No estamos afirmando que exista un incumplimiento ni anticipando un resultado.</b><span>Este estado sólo indica que el flujo automático alcanzó su límite responsable.</span></div><div class="m343-actions"><button class="btn secondary" type="button" data-m341-edit>Revisar mi descripción</button><button class="btn ghost" type="button" data-action="go" data-route="/soluciones">Ver soluciones disponibles</button></div></section>`;
}

function outOfScopePanel() {
  return `<section class="m343-panel m343-out" aria-labelledby="m343-title"><div class="m343-head"><div><span class="m343-step caution">Fuera del catálogo automatizado</span><h3 id="m343-title">Tu situación no encaja con suficiente claridad en las soluciones automatizadas actuales.</h3><p>No vamos a forzar una recomendación sólo para completar el recorrido.</p></div><span class="m343-badge">Límite responsable</span></div><div class="m343-actions"><button class="btn primary" type="button" data-action="go" data-route="/soluciones">Revisar las 11 soluciones</button><button class="btn secondary" type="button" data-m341-edit>Ampliar o corregir mi relato</button></div></section>`;
}

function render(root, step) {
  currentStep = step;
  root.querySelector('.m343-panel')?.remove();
  const handled = ['ROUTE_TOPIC','CONFIRM_RISK','ASK_QUESTION','READY_FOR_RECOMMENDATION','ESCALATE','OUT_OF_SCOPE'].includes(step.action);
  root.classList.toggle('m343-active', handled);
  if (!handled) return;
  const html = ['ROUTE_TOPIC','CONFIRM_RISK','ASK_QUESTION'].includes(step.action)
    ? questionPanel(step)
    : step.action === 'READY_FOR_RECOMMENDATION'
      ? readyPanel(step)
      : step.action === 'OUT_OF_SCOPE'
        ? outOfScopePanel()
        : escalationPanel(step);
  const baseActions = root.querySelector(':scope > .m341-actions');
  if (baseActions) baseActions.insertAdjacentHTML('beforebegin', html);
  else root.insertAdjacentHTML('beforeend', html);
  window.setTimeout(()=>root.querySelector('.m343-panel input,.m343-panel textarea,.m343-panel button')?.focus({preventScroll:true}), 20);
}

async function loadStep(root, code) {
  if (busy) return;
  busy = true;
  try {
    const step = await api('/api/m34/intake/next-step', { method:'POST', body:JSON.stringify({ recovery_code:code }) });
    currentCode = code;
    render(root, step);
  } catch (error) {
    root.querySelector('.m343-panel')?.remove();
    root.classList.remove('m343-active');
    root.insertAdjacentHTML('beforeend', `<div class="m343-status danger">${esc(error.message)}</div>`);
  } finally { busy = false; }
}

function collectValue(form, question) {
  if (question.answer_type === 'select' || question.answer_type === 'boolean') {
    const checked = form.querySelector('input[name="m343-answer"]:checked');
    if (!checked) throw new Error('Selecciona una respuesta para continuar.');
    return checked.value;
  }
  if (question.answer_type === 'multiselect') {
    const values = [...form.querySelectorAll('input[name="m343-answer"]:checked')].map(item=>item.value);
    if (!values.length) throw new Error('Selecciona al menos una opción para continuar.');
    return values;
  }
  const field = form.querySelector('[data-m343-value]');
  const value = String(field?.value || '').trim();
  if (!value) throw new Error('Completa este dato para continuar.');
  return value;
}

async function submitAnswer(form) {
  if (!currentStep || !currentCode || busy) return;
  const status = form.querySelector('#m343-status');
  const button = form.querySelector('button[type="submit"]');
  try {
    const value = collectValue(form, currentStep.question || {});
    busy = true;
    button.disabled = true;
    button.textContent = 'Guardando…';
    const next = await api('/api/m34/intake/answer', {
      method:'POST',
      body:JSON.stringify({
        recovery_code:currentCode,
        question_id:form.dataset.questionId,
        value,
      }),
    });
    const root = form.closest('.m341-saved');
    render(root, next);
    toast(next.action === 'READY_FOR_RECOMMENDATION' ? 'Información mínima reunida.' : 'Respuesta guardada.');
  } catch (error) {
    if (status) { status.className = 'm343-status danger'; status.textContent = error.message; }
    button.disabled = false;
    button.textContent = 'Continuar';
  } finally { busy = false; }
}

function mount() {
  scheduled = false;
  if (pathNow() !== '/orientador') return;
  const root = document.querySelector('.m341-saved');
  const code = codeFromDom();
  if (!root || !code) return;
  if (root.dataset.m343Mounted === code && root.querySelector('.m343-panel')) return;
  root.dataset.m343Mounted = code;
  loadStep(root, code);
}

function scheduleMount() {
  if (scheduled) return;
  scheduled = true;
  window.setTimeout(mount, 60);
}

document.addEventListener('submit', event => {
  if (event.target?.id !== 'm343-question-form') return;
  event.preventDefault();
  submitAnswer(event.target);
});

document.addEventListener('click', event => {
  if (event.target.closest('[data-m341-edit]')) {
    currentStep = null;
    currentCode = '';
    document.querySelector('.m341-saved')?.classList.remove('m343-active');
  }
});

window.addEventListener('hashchange', () => {
  currentStep = null;
  currentCode = '';
  scheduleMount();
});

const app = document.getElementById('app');
if (app) new MutationObserver(scheduleMount).observe(app, { childList:true, subtree:true });
scheduleMount();
