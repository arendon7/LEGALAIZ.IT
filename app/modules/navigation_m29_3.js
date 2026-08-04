import { dateText, esc } from '../core.js';

const safeStore = {
  get(key, fallback = null) {
    try { const value = localStorage.getItem(key); return value === null ? fallback : JSON.parse(value); }
    catch { return fallback; }
  },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch {} },
};

function identity(user = {}) {
  return String(user.id || user.email || user.name || 'usuario').replace(/[^a-z0-9@._-]+/gi, '-').toLowerCase();
}
function onboardingKey(user) { return `legalaizit:m293:onboarding:${identity(user)}`; }
function readKey(user) { return `legalaizit:m293:notifications:${identity(user)}`; }

export function onboardingSteps(user = {}, cases = [], documents = []) {
  const role = user.role || 'client';
  if (role === 'specialist') return [
    { id:'queue', title:'Revisa tu bandeja priorizada', text:'Identifica casos por riesgo, urgencia y etapa.', route:'/revision', visual:'onboarding-review.svg', done:cases.length > 0 },
    { id:'case', title:'Abre un expediente completo', text:'Consulta hechos, soportes, documentos y trazabilidad.', route:'/casos', visual:'onboarding-case.svg', done:cases.some(item => item.specialist_id === user.id) },
    { id:'sources', title:'Verifica fuentes y criterios', text:'Confirma vigencia y aplicación antes de aprobar.', route:'/fuentes', visual:'onboarding-sources.svg', done:false },
    { id:'decision', title:'Registra una decisión trazable', text:'Documenta observaciones, aprobación o devolución.', route:'/revision', visual:'onboarding-decision.svg', done:false },
  ];
  if (role === 'admin') return [
    { id:'operation', title:'Consulta la operación jurídica', text:'Revisa carga, riesgos, tiempos y estados.', route:'/operacion', visual:'onboarding-operation.svg', done:cases.length > 0 },
    { id:'quality', title:'Verifica gobierno y calidad', text:'Controla compuertas, revisiones y evidencia.', route:'/calidad', visual:'onboarding-quality.svg', done:false },
    { id:'network', title:'Revisa la red profesional', text:'Valida capacidad, conflictos y asignaciones.', route:'/red-profesional', visual:'onboarding-network.svg', done:false },
    { id:'pilot', title:'Prepara el piloto controlado', text:'Confirma alcance, controles y métricas.', route:'/preparacion-piloto', visual:'onboarding-pilot.svg', done:false },
  ];
  return [
    { id:'solution', title:'Encuentra la solución adecuada', text:'Describe tu necesidad sin conocer el nombre del documento.', route:'/nuevo', visual:'onboarding-solution.svg', done:cases.length > 0 },
    { id:'case', title:'Completa tu primer expediente', text:'Registra hechos, fechas, valores y personas involucradas.', route:cases[0] ? `/caso/${encodeURIComponent(cases[0].id)}` : '/casos', visual:'onboarding-case.svg', done:cases.length > 0 },
    { id:'evidence', title:'Organiza información y soportes', text:'Relaciona documentos legibles con los hechos del caso.', route:cases[0] ? `/caso/${encodeURIComponent(cases[0].id)}` : '/nuevo', visual:'onboarding-evidence.svg', done:documents.length > 0 },
    { id:'document', title:'Revisa el resultado antes de usarlo', text:'Confirma datos, versión, riesgos y necesidad de revisión.', route:'/documentos', visual:'onboarding-document.svg', done:documents.length > 0 },
  ];
}

export function onboardingStatus(user = {}, cases = [], documents = []) {
  const stored = safeStore.get(onboardingKey(user), {});
  const steps = onboardingSteps(user, cases, documents).map(step => ({ ...step, done:Boolean(step.done || stored.completed?.includes(step.id)) }));
  const complete = steps.filter(step => step.done).length;
  return { steps, complete, total:steps.length, dismissed:Boolean(stored.dismissed), finished:complete === steps.length };
}

export function onboardingPanel(user = {}, cases = [], documents = []) {
  const status = onboardingStatus(user, cases, documents);
  if (status.dismissed && !status.finished) return '';
  const next = status.steps.find(step => !step.done) || status.steps[status.steps.length - 1];
  return `<section class="m293-onboarding ${status.finished ? 'complete' : ''}" aria-label="Guía inicial de LegalAIZ.it">
    <div class="m293-onboarding-copy"><span class="eyebrow">${status.finished ? 'Ruta inicial completada' : 'Empieza con claridad'}</span><h2>${status.finished ? 'Ya conoces los pasos esenciales' : 'Tu recorrido inicial en LegalAIZ.it'}</h2><p>${status.finished ? 'Puedes volver a esta guía desde el Centro de ayuda.' : 'Completa estos pasos para entender la plataforma y avanzar sin perder contexto.'}</p><div class="m293-onboarding-progress"><span class="m293-progress-${status.complete}"></span></div><small>${status.complete} de ${status.total} pasos completados</small></div>
    <div class="m293-onboarding-next"><img src="/assets/brand-visuals/internal/${esc(next.visual)}" alt=""><div><b>${esc(next.title)}</b><span>${esc(next.text)}</span></div><button class="btn primary sm" data-action="onboarding-go" data-step="${esc(next.id)}" data-route="${esc(next.route)}">${status.finished ? 'Revisar guía' : 'Continuar'}</button></div>
    ${!status.finished ? '<button class="m293-onboarding-dismiss" aria-label="Ocultar guía inicial" data-action="onboarding-dismiss">×</button>' : ''}
  </section>`;
}

export function onboardingDialogBody(user = {}, cases = [], documents = []) {
  const status = onboardingStatus(user, cases, documents);
  return `<div class="m293-onboarding-dialog"><div class="m293-onboarding-dialog-intro"><img src="/assets/brand-visuals/internal/onboarding-welcome.svg" alt=""><div><h3>Un recorrido pensado para tu rol</h3><p>LegalAIZ.it conserva la profundidad jurídica detrás de una experiencia guiada. Avanza por estos pasos y vuelve cuando lo necesites.</p></div></div><div class="m293-onboarding-steps">${status.steps.map((step,index)=>`<button class="m293-onboarding-step ${step.done?'complete':''}" data-action="onboarding-go" data-step="${esc(step.id)}" data-route="${esc(step.route)}"><span>${step.done?'✓':index+1}</span><img src="/assets/brand-visuals/internal/${esc(step.visual)}" alt=""><div><b>${esc(step.title)}</b><small>${esc(step.text)}</small></div><i>›</i></button>`).join('')}</div></div>`;
}

export function markOnboardingStep(user = {}, stepId = '') {
  const key = onboardingKey(user), stored = safeStore.get(key, {});
  const completed = new Set(stored.completed || []); if (stepId) completed.add(stepId);
  safeStore.set(key, { ...stored, completed:[...completed], dismissed:false });
}
export function dismissOnboarding(user = {}) {
  const key = onboardingKey(user), stored = safeStore.get(key, {});
  safeStore.set(key, { ...stored, dismissed:true });
}
export function resetOnboarding(user = {}) { safeStore.set(onboardingKey(user), { completed:[], dismissed:false }); }

function notificationVisual(type='info') {
  return ({ review:'notification-review.svg', ready:'notification-ready.svg', action:'notification-action.svg', security:'notification-security.svg', info:'notification-info.svg' })[type] || 'notification-info.svg';
}

export function buildNotifications(user = {}, cases = [], documents = []) {
  const rows = [];
  const role = user.role || 'client';
  cases.forEach(item => {
    const raw = `${item.status || ''} ${item.review_status || ''}`.toLowerCase();
    if (/aprobad|listo|entregado/.test(raw)) rows.push({ id:`case-ready-${item.id}`, type:'ready', title:'Tu expediente tiene un resultado disponible', text:`${item.title}: revisa la versión y las condiciones antes de usarla.`, route:`/caso/${encodeURIComponent(item.id)}`, date:item.updated_at, priority:1 });
    else if (/revisi/.test(raw) || item.risk === 'red') rows.push({ id:`case-review-${item.id}`, type:'review', title:role === 'client' ? 'Tu expediente está en revisión' : 'Expediente que requiere revisión', text:`${item.title}: consulta observaciones, riesgos y próximos pasos.`, route:`/caso/${encodeURIComponent(item.id)}`, date:item.updated_at, priority:2 });
    else if (role === 'client' && !/cerrado|finalizado/.test(raw)) rows.push({ id:`case-action-${item.id}`, type:'action', title:'Tienes un expediente por continuar', text:`${item.title}: completa información o soportes pendientes.`, route:`/caso/${encodeURIComponent(item.id)}`, date:item.updated_at, priority:3 });
  });
  if (role === 'client' && !cases.length) rows.push({ id:'welcome-first-solution', type:'info', title:'Empieza tu primera solución', text:'Describe tu necesidad y deja que la plataforma te guíe.', route:'/nuevo', date:new Date().toISOString(), priority:4 });
  if (role === 'client' && documents.length) rows.push({ id:'documents-center', type:'ready', title:'Tus documentos están organizados', text:`Tienes ${documents.length} ${documents.length === 1 ? 'documento' : 'documentos'} en el Centro documental.`, route:'/documentos', date:documents[0]?.updated_at || documents[0]?.created_at, priority:5 });
  if (role === 'specialist') rows.push({ id:'specialist-sources', type:'security', title:'Verifica fuentes antes de aprobar', text:'La decisión jurídica debe conservar evidencia de vigencia, aplicación y revisión.', route:'/fuentes', date:new Date().toISOString(), priority:6 });
  if (role === 'admin') rows.push({ id:'admin-release-gates', type:'security', title:'Revisa las compuertas de liberación', text:'La aprobación del software no sustituye la aprobación jurídica y QA de cada revisión documental.', route:'/calidad', date:new Date().toISOString(), priority:6 });
  return rows.sort((a,b)=>a.priority-b.priority).slice(0,18);
}

export function readNotificationIds(user = {}) { return new Set(safeStore.get(readKey(user), [])); }
export function unreadNotificationCount(user = {}, cases = [], documents = []) {
  const read = readNotificationIds(user); return buildNotifications(user,cases,documents).filter(item=>!read.has(item.id)).length;
}
export function markNotificationRead(user = {}, id = '') {
  const read = readNotificationIds(user); if (id) read.add(id); safeStore.set(readKey(user), [...read]);
}
export function markAllNotificationsRead(user = {}, cases = [], documents = []) {
  safeStore.set(readKey(user), buildNotifications(user,cases,documents).map(item=>item.id));
}

export function notificationsDialogBody(user = {}, cases = [], documents = []) {
  const items=buildNotifications(user,cases,documents), read=readNotificationIds(user);
  if (!items.length) return '<div class="m293-notification-empty"><img src="/assets/brand-visuals/internal/notification-empty.svg" alt=""><h3>No tienes novedades pendientes</h3><p>Las actualizaciones de expedientes, documentos y revisiones aparecerán aquí.</p></div>';
  return `<div class="m293-notification-list">${items.slice(0,6).map(item=>`<button class="m293-notification ${read.has(item.id)?'read':''}" data-action="notification-open" data-notification-id="${esc(item.id)}" data-route="${esc(item.route)}"><img src="/assets/brand-visuals/internal/${notificationVisual(item.type)}" alt=""><span><b>${esc(item.title)}</b><small>${esc(item.text)}</small><em>${esc(dateText(item.date))}</em></span><i>›</i></button>`).join('')}</div>`;
}

export function notificationsPage({ shell, pageHeader, user, cases, documents }) {
  const items=buildNotifications(user,cases,documents), read=readNotificationIds(user), unread=items.filter(item=>!read.has(item.id)).length;
  return shell(`<div class="page m293-notifications-page">${pageHeader({eyebrow:'Centro de notificaciones',title:'Novedades y acciones pendientes',description:'Consulta cambios relevantes de tus expedientes, documentos, revisiones y controles.',actions:unread?'<button class="btn secondary" data-action="notifications-read-all">Marcar todas como leídas</button>':''})}<section class="m293-notification-summary"><article><b>${items.length}</b><span>Novedades disponibles</span></article><article><b>${unread}</b><span>Sin leer</span></article><article><b>${items.filter(item=>item.type==='review').length}</b><span>Requieren revisión</span></article></section>${items.length?`<div class="m293-notification-page-list">${items.map(item=>`<article class="m293-notification-page-row ${read.has(item.id)?'read':''}"><img src="/assets/brand-visuals/internal/${notificationVisual(item.type)}" alt=""><div><span class="badge ${item.type==='review'?'warning':item.type==='ready'?'success':'blue'}">${item.type==='review'?'Revisión':item.type==='ready'?'Resultado disponible':'Siguiente acción'}</span><h2>${esc(item.title)}</h2><p>${esc(item.text)}</p><small>${esc(dateText(item.date))}</small></div><button class="btn secondary" data-action="notification-open" data-notification-id="${esc(item.id)}" data-route="${esc(item.route)}">Abrir</button></article>`).join('')}</div>`:'<div class="m293-notification-empty"><img src="/assets/brand-visuals/internal/notification-empty.svg" alt=""><h2>No tienes novedades pendientes</h2><p>Las actualizaciones importantes aparecerán aquí.</p></div>'}</div>`);
}

const helpByRole = {
  client: [
    ['Encontrar una solución','Describe tu problema y compara opciones sin conocer el nombre del documento.','/nuevo','help-solution.svg'],
    ['Completar un expediente','Aprende qué información, fechas, valores y soportes debes reunir.','/casos','help-case.svg'],
    ['Entender la revisión','Diferencia borrador, revisión recomendada, revisión obligatoria y documento listo.','/documentos','help-review.svg'],
    ['Usar tus documentos','Confirma datos, versión y alcance antes de descargar, firmar o radicar.','/documentos','help-document.svg'],
  ],
  specialist: [
    ['Priorizar una revisión','Organiza casos por riesgo, etapa y urgencia sin perder el contexto.','/revision','help-review.svg'],
    ['Verificar fuentes','Consulta criterios y vigencia antes de registrar decisiones.','/fuentes','help-sources.svg'],
    ['Documentar decisiones','Conserva observaciones, responsable, versión y evidencia.','/revision','help-decision.svg'],
    ['Gestionar asignaciones','Revisa capacidad, conflicto y seguimiento profesional.','/red-profesional','help-network.svg'],
  ],
  admin: [
    ['Supervisar la operación','Revisa carga, tiempos, riesgos y cuellos de botella.','/operacion','help-operation.svg'],
    ['Gobernar la calidad','Controla aprobación, QA, trazabilidad y liberación.','/calidad','help-quality.svg'],
    ['Preparar el piloto','Confirma alcance, datos, métricas y controles.','/preparacion-piloto','help-pilot.svg'],
    ['Configurar con seguridad','Aplica mínimo privilegio, MFA y separación de funciones.','/configuracion','help-security.svg'],
  ],
};

export function helpCenterPage({ shell, pageHeader, user }) {
  const role=user.role || 'client', topics=helpByRole[role] || helpByRole.client;
  const faqs = role === 'client' ? [
    ['¿La plataforma reemplaza a un abogado?','No. Orienta, estructura información y genera documentos. Los casos de alto impacto o riesgo pueden exigir revisión profesional específica.'],
    ['¿Puedo usar inmediatamente un documento generado?','Debes confirmar datos, versión, anexos y estado de revisión. Los borradores controlados no deben firmarse ni radicarse sin cumplir las compuertas aplicables.'],
    ['¿Se guarda mi avance?','Los formularios permiten guardar y retomar. En demostración y piloto deben utilizarse únicamente datos autorizados para ese entorno.'],
  ] : [
    ['¿Qué debe quedar trazado en una revisión?','Responsable, fecha, revisión documental, fuentes, observaciones, decisión y evidencia de QA cuando aplique.'],
    ['¿Una aprobación general libera todos los documentos?','No. La liberación externa depende de la aprobación jurídica y QA sobre la misma revisión documental y del control específico del expediente.'],
    ['¿Qué ocurre con un riesgo rojo?','Debe permanecer bloqueado hasta resolver los hallazgos y registrar una validación profesional suficiente.'],
  ];
  return shell(`<div class="page m293-help-page">${pageHeader({eyebrow:'Centro de ayuda',title:'Encuentra orientación sin perder tu contexto',description:'Guías breves, conceptos esenciales y accesos directos según tu rol.'})}<section class="m293-help-hero"><div><span class="eyebrow">Ayuda contextual</span><h2>¿En qué etapa necesitas apoyo?</h2><p>Selecciona una guía y vuelve directamente al punto de trabajo relacionado.</p></div><img src="/assets/brand-visuals/internal/help-center-m293.svg" alt="Centro de ayuda de LegalAIZ.it"></section><section class="m293-help-grid">${topics.map(([title,text,route,visual])=>`<article><img src="/assets/brand-visuals/internal/${visual}" alt=""><h3>${esc(title)}</h3><p>${esc(text)}</p><button class="btn secondary sm" data-action="go" data-route="${esc(route)}">Abrir guía</button></article>`).join('')}</section><section class="section-grid mt-22"><div class="card span-7"><div class="card-header"><div><h2>Preguntas frecuentes</h2><p>Respuestas directas sobre uso, revisión y alcance.</p></div></div><div class="m293-faq-list">${faqs.map(([question,answer])=>`<details><summary>${esc(question)}</summary><p>${esc(answer)}</p></details>`).join('')}</div></div><aside class="card span-5 m293-help-side"><img src="/assets/brand-visuals/internal/help-human.svg" alt="Revisión y acompañamiento humano"><h2>¿Tu caso requiere criterio profesional?</h2><p>Los asuntos litigiosos, sancionatorios, laborales, tributarios, societarios, regulatorios o de alto impacto económico deben revisarse con especial cuidado.</p><button class="btn primary" data-action="go" data-route="${role==='client'?'/casos':'/revision'}">Revisar mis pendientes</button><button class="btn secondary" data-action="onboarding-open">Ver recorrido inicial</button></aside></section><div class="legal-notice mt-22"><b>Alcance.</b> El Centro de ayuda explica el funcionamiento de la plataforma. No constituye representación judicial ni una conclusión jurídica definitiva sobre un caso particular.</div></div>`);
}

export function sidebarJourneySummary(user = {}, cases = [], documents = []) {
  const status=onboardingStatus(user,cases,documents);
  return `<button class="m293-sidebar-journey" data-action="onboarding-open"><span>${status.complete}/${status.total}</span><div><b>Mi recorrido inicial</b><small>${status.finished?'Completado':'Continúa la guía'}</small></div></button>`;
}
