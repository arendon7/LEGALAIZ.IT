const STAGES = Object.freeze([
  'Cuéntanos tu situación',
  'Confirma los datos',
  'Completa lo necesario',
  'Revisa tu ruta',
  'Guarda y continúa',
  'Completa la solución',
]);

let scheduled = false;

function pathNow() {
  return location.hash.replace(/^#/, '') || '/';
}

function activeStage() {
  const path = pathNow();
  if (path === '/orientador') {
    if (document.querySelector('.m344-panel')) return 4;
    if (document.querySelector('.m343-panel')) return 3;
    if (document.querySelector('.m342-panel')) return 2;
    return 1;
  }
  if (path === '/login' && document.querySelector('.m350-login-continuation,#m350-register-form')) return 5;
  if (/^\/nuevo\/CO-[A-Z]{2}-\d{3}$/.test(path) && document.querySelector('.m351-bridge-card')) return 6;
  return 0;
}

function stageAnchor(stage) {
  if (stage <= 4) return document.querySelector('.m344-panel,.m343-panel,.m342-panel,.m341-saved,#m341-intake-form');
  if (stage === 5) return document.querySelector('.m350-login-continuation,#m350-register-form');
  if (stage === 6) return document.querySelector('.wizard-overview');
  return null;
}

function journeyMarkup(stage) {
  return `<nav class="m381-journey" aria-label="Tu recorrido en LegalAIZ.it" data-m381-stage="${stage}"><ol>${STAGES.map((label,index) => {
    const number = index + 1;
    const state = number < stage ? 'complete' : number === stage ? 'active' : '';
    return `<li class="${state}" ${number === stage ? 'aria-current="step"' : ''}><span>${number < stage ? '✓' : number}</span><b>${label}</b></li>`;
  }).join('')}</ol></nav>`;
}

function contextFor(stage) {
  const reviewed = Boolean(document.querySelector('.m342-reviewed'));
  const values = {
    1: ['Todavía nada: tú decides cuándo guardar.', 'Una descripción breve de lo que ocurrió.', 'Una ruta inicial para saber qué información necesitamos.', 'Guardar tu descripción y revisar los datos detectados.'],
    2: reviewed
      ? ['Tu descripción y los datos que confirmaste.', 'Las preguntas necesarias para afinar la ruta.', 'Una base de hechos trazables para continuar.', 'Continuar con las preguntas que realmente hagan falta.']
      : ['Tu descripción de la situación.', 'Confirmar, corregir o descartar los datos detectados.', 'Una base de hechos revisada por ti.', 'Guardar tu revisión antes de seguir.'],
    3: ['Tu descripción y los datos ya revisados.', 'Sólo los datos mínimos que aún pida el orientador.', 'Una evaluación responsable de las soluciones disponibles.', 'Responder la pregunta actual o indicar que no tienes el dato.'],
    4: ['Tu diagnóstico y la ruta que acabas de revisar.', 'Decidir si quieres continuar con esa solución.', 'El acceso al formulario específico sin repetir tu relato inicial.', 'Continuar con la solución o corregir la información si algo cambió.'],
    5: ['Tu diagnóstico y la ruta elegida siguen disponibles para vincularlos.', 'Ingresar o crear tu espacio privado.', 'Continuidad segura hacia el formulario de la solución.', 'Acceder a tu cuenta; no volverás a empezar desde cero.'],
    6: ['Tu cuenta, el diagnóstico y las respuestas reutilizables.', 'Los datos específicos del documento que todavía no estén completos.', 'Un borrador controlado, revisable y trazable según tu caso.', 'Completar el formulario; tus cambios manuales siempre prevalecen.'],
  }[stage];
  if (!values) return '';
  const labels = ['Ya guardamos', 'Qué falta', 'Qué obtendrás', 'Siguiente paso'];
  return `<aside class="m381-context" aria-label="Estado de tu recorrido">${values.map((value,index) => `<div><small>${labels[index]}</small><span>${value}</span></div>`).join('')}</aside>`;
}

function ensureJourney(stage) {
  const anchor = stageAnchor(stage);
  if (!anchor?.parentElement) return;
  let journey = anchor.parentElement.querySelector(':scope > .m381-journey');
  if (!journey) {
    anchor.insertAdjacentHTML('beforebegin', journeyMarkup(stage) + contextFor(stage));
    return;
  }
  if (Number(journey.dataset.m381Stage || 0) !== stage) journey.outerHTML = journeyMarkup(stage);
  const context = anchor.parentElement.querySelector(':scope > .m381-context');
  const nextContext = contextFor(stage);
  if (!context) journey.insertAdjacentHTML('afterend', nextContext);
  else if (context.outerHTML !== nextContext) context.outerHTML = nextContext;
}

function setText(selector, text) {
  const element = document.querySelector(selector);
  if (element && element.textContent !== text) element.textContent = text;
}

function polishPublicCopy() {
  setText('.m342-panel .m342-step:not(.complete)', 'Etapa 2 de 6 · Confirma los datos');
  setText('.m342-reviewed .m342-legal-boundary b', 'Ya puedes seguir sin repetir lo confirmado.');
  setText('.m342-reviewed .m342-legal-boundary span', 'Compararemos la información revisada con los criterios de las soluciones disponibles y sólo preguntaremos lo que todavía haga falta.');

  setText('.m343-panel .m343-step:not(.complete):not(.caution)', 'Etapa 3 de 6 · Completa lo necesario');
  setText('.m343-ready .m343-step.complete', '✓ Información mínima reunida');
  setText('.m343-ready #m343-title', 'Ya tenemos la información necesaria para evaluar tu ruta.');
  setText('.m343-ready > .m343-head .m343-badge', 'Etapa completada');
  setText('.m343-ready .m343-summary b', 'Qué haremos ahora');
  setText('.m343-ready .m343-summary span', 'Compararemos los hechos que confirmaste con el alcance, las exclusiones y los riesgos de las soluciones disponibles antes de mostrarte una ruta.');

  setText('.m344-panel .m344-step:not(.caution)', 'Etapa 4 de 6 · Revisa tu ruta');
  setText('.m344-primary + .m344-alternatives .m344-kicker', 'Otras rutas compatibles');
  document.querySelectorAll('.m344-trace').forEach(element => element.remove());

  setText('.m350-account-note b', 'Tu avance se conserva al continuar.');
  setText('.m350-account-note span', 'Al continuar, vincularemos esta ruta a tu espacio privado. Después completarás únicamente los datos específicos de la solución antes de crear tu expediente.');

  const bridgeHead = document.querySelector('.m351-bridge-card .m351-bridge-head');
  if (bridgeHead) {
    setText('.m351-bridge-card .m351-bridge-head span', 'Continuidad activada');
    setText('.m351-bridge-card .m351-bridge-head b', 'No empiezas de cero');
  }
}

function mount() {
  scheduled = false;
  const stage = activeStage();
  if (!stage) return;
  polishPublicCopy();
  ensureJourney(stage);
}

function schedule() {
  if (scheduled) return;
  scheduled = true;
  window.setTimeout(mount, 0);
}

window.addEventListener('hashchange', schedule);
const app = document.getElementById('app');
if (app) new MutationObserver(schedule).observe(app, { childList:true, subtree:true });
schedule();
