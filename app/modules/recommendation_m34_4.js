import { api, esc, toast } from '../core.js';
import { publicProductRoute } from './public_m29_1.js';

let scheduled = false;
let busy = false;
let currentCode = '';

function pathNow() { return location.hash.replace(/^#/, '') || '/'; }
function codeFromDom() { return String(document.querySelector('.m341-recovery code')?.textContent || '').trim(); }

function reviewCopy(requirement) {
  if (requirement === 'CASE_SPECIFIC_REVIEW_EXPECTED') {
    return {
      title:'Esta solución prevé revisión profesional del caso.',
      text:'La generación automatizada no reemplaza la revisión jurídica que corresponde por la naturaleza de esta solución.'
    };
  }
  return {
    title:'La necesidad de revisión depende de los riesgos del caso.',
    text:'Si durante el formulario completo aparecen riesgos, contradicciones o complejidad adicional, LegalAIZ.it puede exigir revisión profesional antes de liberar el documento.'
  };
}

function safeList(items, empty='Sin información adicional.') {
  if (!Array.isArray(items) || !items.length) return `<li>${esc(empty)}</li>`;
  return items.map(item=>`<li>${esc(item)}</li>`).join('');
}

function warningList(items) {
  if (!Array.isArray(items) || !items.length) return '';
  return `<div class="m344-warnings" role="note"><b>Condiciones que debes tener presentes</b>${items.map(item=>`<p>${esc(item.message || '')}</p>`).join('')}</div>`;
}

function alternativeCards(items) {
  if (!Array.isArray(items) || !items.length) return '';
  return `<section class="m344-alternatives"><div><span class="m344-kicker">Otras rutas compatibles</span><h4>También podrían ser relevantes</h4><p>Las mostramos como alternativas de producto, no como probabilidades ni como resultados jurídicos.</p></div><div class="m344-alt-grid">${items.slice(0,2).map(item=>`<article><span>${esc(item.eligibility === 'CONDITIONAL' ? 'Encaje condicionado' : 'Alternativa')}</span><h5>${esc(item.public_title || '')}</h5><p>${esc(item.fit_statement || '')}</p><button class="btn ghost" type="button" data-action="go" data-route="${esc(publicProductRoute(item.product_code || ''))}">Conocer esta solución</button></article>`).join('')}</div></section>`;
}

function recommendationPanel(result) {
  const primary = result.primary || {};
  const review = reviewCopy(primary.review_requirement);
  const condition = primary.eligibility === 'CONDITIONAL'
    ? '<span class="m344-eligibility conditional">Encaje condicionado</span>'
    : '<span class="m344-eligibility">Mejor encaje encontrado</span>';
  return `<section class="m344-panel" aria-labelledby="m344-title"><div class="m344-head"><div><span class="m344-step">Paso 4 de 4 · Recomendación</span><h3 id="m344-title">Esta es la solución que mejor corresponde a tu situación.</h3><p>La selección compara los hechos utilizables del diagnóstico con los límites del catálogo y los controles de riesgo de LegalAIZ.it.</p></div>${condition}</div><article class="m344-primary"><span class="m344-kicker">Solución recomendada</span><h4>${esc(primary.public_title || '')}</h4><p class="m344-fit">${esc(primary.fit_statement || '')}</p>${warningList(primary.warnings)}<div class="m344-columns"><div><h5>Por qué encaja</h5><ul>${safeList(primary.why_this_solution)}</ul></div><div><h5>Qué incluye</h5><ul>${safeList(primary.includes)}</ul></div><div><h5>Qué no incluye</h5><ul>${safeList(primary.not_included)}</ul></div></div><div class="m344-review"><b>${esc(review.title)}</b><span>${esc(review.text)}</span></div><div class="m344-actions"><button class="btn primary" type="button" data-action="go" data-route="${esc(publicProductRoute(primary.product_code || ''))}">Revisar esta solución</button><button class="btn secondary" type="button" data-m341-edit>Corregir mi relato</button></div></article>${alternativeCards(result.alternatives)}<div class="m344-boundary"><b>Adecuación al producto no significa probabilidad de ganar.</b><span>${esc(result.notice || 'La recomendación no anticipa el resultado jurídico del caso.')}</span></div><div class="m344-trace"><span>Decisión trazable</span><code>${esc(result.decision_id || '')}</code></div></section>`;
}

function escalationPanel(result) {
  const messages = Array.isArray(result.messages) ? result.messages : [];
  return `<section class="m344-panel m344-escalate" aria-labelledby="m344-title"><div class="m344-head"><div><span class="m344-step caution">Revisión profesional</span><h3 id="m344-title">No es responsable recomendarte un producto automáticamente.</h3><p>El diagnóstico alcanzó un límite que requiere revisar mejor la naturaleza de la situación antes de escoger una solución.</p></div><span class="m344-eligibility conditional">Escalamiento seguro</span></div>${messages.length?`<div class="m344-warnings"><b>Qué detectó el control</b>${messages.map(message=>`<p>${esc(message)}</p>`).join('')}</div>`:''}<div class="m344-boundary"><b>No estamos concluyendo que exista un incumplimiento ni anticipando un resultado.</b><span>${esc(result.notice || '')}</span></div><div class="m344-actions"><button class="btn secondary" type="button" data-m341-edit>Revisar mi descripción</button><button class="btn ghost" type="button" data-action="go" data-route="/soluciones">Ver soluciones disponibles</button></div></section>`;
}

function outOfScopePanel(result) {
  const messages = Array.isArray(result.messages) ? result.messages : [];
  return `<section class="m344-panel m344-out" aria-labelledby="m344-title"><div class="m344-head"><div><span class="m344-step caution">Fuera del alcance automatizado</span><h3 id="m344-title">No encontramos una solución del catálogo que debamos recomendar de forma responsable.</h3><p>Preferimos no adaptar un documento que fue diseñado para un supuesto distinto.</p></div><span class="m344-eligibility conditional">Sin recomendación forzada</span></div>${messages.length?`<div class="m344-warnings"><b>Por qué no encaja</b>${messages.map(message=>`<p>${esc(message)}</p>`).join('')}</div>`:''}<div class="m344-boundary"><b>Esto no significa que no exista una alternativa jurídica.</b><span>${esc(result.notice || '')}</span></div><div class="m344-actions"><button class="btn secondary" type="button" data-m341-edit>Ampliar o corregir mi relato</button><button class="btn ghost" type="button" data-action="go" data-route="/soluciones">Explorar las 11 soluciones</button></div></section>`;
}

function askMorePanel(result) {
  return `<section class="m344-panel m344-out" aria-labelledby="m344-title"><div class="m344-head"><div><span class="m344-step caution">Falta información</span><h3 id="m344-title">Necesitamos completar el diagnóstico antes de recomendar.</h3><p>${esc(result.notice || 'Todavía falta información para evaluar una solución responsablemente.')}</p></div></div><div class="m344-actions"><button class="btn primary" type="button" data-m344-return>Continuar diagnóstico</button><button class="btn secondary" type="button" data-m341-edit>Corregir mi relato</button></div></section>`;
}

function renderResult(root, result) {
  root.querySelector('.m344-panel')?.remove();
  root.classList.add('m344-active');
  const html = result.outcome === 'RECOMMEND'
    ? recommendationPanel(result)
    : result.outcome === 'ESCALATE'
      ? escalationPanel(result)
      : result.outcome === 'OUT_OF_SCOPE'
        ? outOfScopePanel(result)
        : askMorePanel(result);
  const m343 = root.querySelector(':scope > .m343-panel');
  if (m343) m343.insertAdjacentHTML('afterend', html);
  else root.insertAdjacentHTML('beforeend', html);
  window.setTimeout(()=>root.querySelector('.m344-panel button')?.focus({preventScroll:true}), 20);
}

function enhanceReady(root) {
  const ready = root.querySelector(':scope > .m343-panel.m343-ready');
  if (!ready || ready.querySelector('[data-m344-request]')) return;
  const actions = ready.querySelector('.m343-actions');
  if (!actions) return;
  actions.insertAdjacentHTML('afterbegin', '<button class="btn primary" type="button" data-m344-request>Ver mi recomendación</button>');
  const explanatory = ready.querySelector('.m343-summary');
  if (explanatory && !ready.querySelector('.m344-ready-note')) {
    explanatory.insertAdjacentHTML('afterend', '<p class="m344-ready-note">La recomendación se calcula sólo cuando tú la solicitas y puede concluir que el caso necesita revisión o está fuera del catálogo.</p>');
  }
}

async function requestRecommendation(button) {
  const root = button.closest('.m341-saved');
  const code = codeFromDom();
  if (!root || !code || busy) return;
  busy = true;
  currentCode = code;
  const original = button.textContent;
  button.disabled = true;
  button.textContent = 'Evaluando…';
  try {
    const result = await api('/api/m34/intake/recommendation', {
      method:'POST',
      body:JSON.stringify({ recovery_code:code }),
    });
    renderResult(root, result);
    toast(result.outcome === 'RECOMMEND' ? 'Recomendación disponible.' : 'El diagnóstico requiere otro siguiente paso.');
  } catch (error) {
    const ready = root.querySelector('.m343-ready');
    ready?.insertAdjacentHTML('beforeend', `<div class="m344-status danger" role="status">${esc(error.message)}</div>`);
    button.disabled = false;
    button.textContent = original;
  } finally { busy = false; }
}

function returnToDiagnosis(button) {
  const root = button.closest('.m341-saved');
  root?.classList.remove('m344-active');
  root?.querySelector('.m344-panel')?.remove();
  currentCode = '';
  window.setTimeout(()=>root?.querySelector('.m343-panel button,.m343-panel input')?.focus({preventScroll:true}), 20);
}

function mount() {
  scheduled = false;
  if (pathNow() !== '/orientador') return;
  const root = document.querySelector('.m341-saved');
  if (!root) return;
  enhanceReady(root);
}

function scheduleMount() {
  if (scheduled) return;
  scheduled = true;
  window.setTimeout(mount, 50);
}

document.addEventListener('click', event => {
  const request = event.target.closest('[data-m344-request]');
  if (request) { requestRecommendation(request); return; }
  const back = event.target.closest('[data-m344-return]');
  if (back) { returnToDiagnosis(back); return; }
  if (event.target.closest('[data-m341-edit]')) {
    currentCode = '';
    document.querySelector('.m341-saved')?.classList.remove('m344-active');
    document.querySelector('.m344-panel')?.remove();
  }
});

window.addEventListener('hashchange', () => { currentCode = ''; scheduleMount(); });
const app = document.getElementById('app');
if (app) new MutationObserver(scheduleMount).observe(app, {childList:true,subtree:true});
scheduleMount();
