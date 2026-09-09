import { dateText, esc, humanize, icons, riskClass, riskLabels, state } from '../core.js';

const closedPattern = /cerrado|finalizado/i;
const followUpPattern = /seguimiento/i;
const deliveredPattern = /entregad/i;
const reviewPattern = /revisi|aprob|qa/i;
const documentPattern = /document|borrador|generad/i;

export function friendlyCaseState(item = {}) {
  const raw = `${item.status || ''} ${item.review_status || ''}`.toLowerCase();
  if (closedPattern.test(raw)) return { key:'closed', label:'Finalizado', detail:'El expediente conserva sus documentos e historial.', progress:100, visual:'case-closed.svg', cls:'success' };
  if (followUpPattern.test(raw)) return { key:'followup', label:'En seguimiento', detail:'La entrega ya ocurrió y el expediente conserva próximos pasos por gestionar.', progress:95, visual:'case-ready.svg', cls:'blue' };
  if (deliveredPattern.test(raw)) return { key:'delivered', label:'Documentos entregados', detail:'Consulta la entrega y organiza las actuaciones posteriores del expediente.', progress:92, visual:'case-ready.svg', cls:'success' };
  if (/aprobad|listo/.test(raw)) return { key:'ready', label:'Documento listo', detail:'Revisa la versión disponible y los pasos de entrega.', progress:90, visual:'case-ready.svg', cls:'success' };
  if (reviewPattern.test(raw) || item.risk === 'red') return { key:'review', label:'En revisión', detail:'Un especialista debe validar información, riesgos o documentos.', progress:70, visual:'case-review.svg', cls:item.risk === 'red' ? 'danger':'warning' };
  if (documentPattern.test(raw)) return { key:'document', label:'Preparando documentos', detail:'La información se está convirtiendo en documentos revisables.', progress:55, visual:'case-active.svg', cls:'blue' };
  return { key:'active', label:'En progreso', detail:'Completa información y soportes para continuar.', progress:30, visual:'case-active.svg', cls:'blue' };
}

export function nextCaseAction(item = {}) {
  const stage = friendlyCaseState(item);
  if (stage.key === 'closed') return { title:'Consulta el historial', text:'Tus documentos y decisiones permanecen disponibles.', tab:'actividad', button:'Ver historial' };
  if (stage.key === 'followup') return { title:'Continúa los próximos pasos', text:'Registra actuaciones, soportes y referencias operativas del seguimiento.', tab:'seguimiento', button:'Ver seguimiento' };
  if (stage.key === 'delivered') return { title:'Organiza lo que sigue después de la entrega', text:'Consulta tus documentos y activa o continúa el seguimiento cuando corresponda.', tab:'seguimiento', button:'Ver siguientes pasos' };
  if (stage.key === 'ready') return { title:'Revisa el documento disponible', text:'Confirma datos, versión y condiciones antes de descargar o usar.', tab:'documentos', button:'Ver documentos' };
  if (stage.key === 'review') return { title:'Consulta el estado de la revisión', text:item.risk === 'red' ? 'El caso no debe liberarse hasta resolver los bloqueos.' : 'Revisa observaciones y decisiones registradas.', tab:'revision', button:'Ver revisión' };
  if (stage.key === 'document') return { title:'Verifica los documentos', text:'Comprueba que los datos coincidan con los soportes.', tab:'documentos', button:'Ver documentos' };
  return { title:'Continúa completando el expediente', text:'Revisa datos, soportes y preguntas pendientes.', tab:'resumen', button:'Continuar' };
}

export const caseFilters = [
  ['Activos','Activos'], ['Revisión','En revisión'], ['Listos','Listos'], ['Finalizados','Finalizados'], ['Todos','Todos']
];
export function filterCases(items = [], filter = 'Activos') {
  if (filter === 'Todos') return items;
  return items.filter(item => {
    const key = friendlyCaseState(item).key;
    if (filter === 'Activos') return ['active','document','followup'].includes(key);
    if (filter === 'Revisión') return key === 'review';
    if (filter === 'Listos') return ['ready','delivered'].includes(key);
    if (filter === 'Finalizados') return key === 'closed';
    return true;
  });
}

export function caseCard(item, product = {}, compact = false) {
  const stage = friendlyCaseState(item), action = nextCaseAction(item);
  const visual = `/assets/brand-visuals/internal/${stage.visual}`;
  return `<article class="m292-case-card ${compact?'compact':''}"><a class="m292-case-main" href="#/caso/${encodeURIComponent(item.id)}"><img src="${visual}" alt=""><div class="m292-case-copy"><div class="m292-case-title-row"><span class="badge ${stage.cls}">${esc(stage.label)}</span><small>${esc(dateText(item.updated_at))}</small></div><h3>${esc(item.title)}</h3><p>${esc(product.title || item.product_code)}</p><div class="m292-progress"><span class="progress-p${Math.min(100,Math.max(0,Math.round(stage.progress/10)*10))}"></span></div><small>${esc(stage.detail)}</small></div></a><div class="m292-case-action"><div><b>${esc(action.title)}</b><span>${esc(action.text)}</span></div><a class="btn secondary sm" href="#/caso/${encodeURIComponent(item.id)}">${esc(action.button)}</a></div></article>`;
}

export function emptyState({ visual='empty-documents-app.svg', title='Aún no hay información', text='', actionLabel='', route='' }={}) {
  return `<div class="empty-state m292-empty-state"><img src="/assets/brand-visuals/internal/${esc(visual)}" alt=""><h2>${esc(title)}</h2><p>${esc(text)}</p>${actionLabel&&route?`<button class="btn primary" data-action="go" data-route="${esc(route)}">${esc(actionLabel)}</button>`:''}</div>`;
}

export function tabsForCase(role='client') {
  if (role === 'client') return [['resumen','Resumen'],['hechos','Mi información'],['evidencias','Soportes'],['documentos','Documentos'],['revision','Revisión'],['seguimiento','Siguientes pasos'],['actividad','Historial']];
  return [['resumen','Resumen'],['hechos','Hechos'],['evidencias','Evidencias'],['ruta','Ruta jurídica'],['documentos','Documentos'],['revision','Revisión'],['seguimiento','Seguimiento'],['actividad','Actividad']];
}

export function wizardGuidance(section='', questions=[]) {
  const text = String(section).toLowerCase();
  let title='Responde con información verificable';
  let detail='Puedes guardar el avance y corregir las respuestas antes del análisis.';
  let items=['Documento de identidad o datos de las partes','Fechas, valores y hechos principales','Soportes relacionados con esta etapa'];
  if (/partes|identific|persona|datos generales/.test(text)) { title='Empecemos por identificar a las personas'; detail='Escribe los nombres y documentos tal como aparecen en los soportes.'; items=['Documentos de identidad','Razón social y NIT, cuando aplique','Datos de contacto actualizados']; }
  else if (/hecho|situaci|antecedente|caso/.test(text)) { title='Cuéntanos qué ocurrió'; detail='Ordena los hechos cronológicamente y evita conclusiones que no puedas sustentar.'; items=['Fecha y lugar de los hechos','Comunicaciones relevantes','Personas o entidades involucradas']; }
  else if (/econ|valor|pago|salario|canon|deuda/.test(text)) { title='Revisemos los valores'; detail='Usa cifras respaldadas por contratos, comprobantes, extractos o recibos.'; items=['Valor principal','Fechas y formas de pago','Abonos, descuentos o cargos']; }
  else if (/document|soporte|evidencia|prueba/.test(text)) { title='Prepara los soportes'; detail='La calidad del resultado depende de que los archivos correspondan con los hechos.'; items=['Contratos o comunicaciones','Comprobantes y certificaciones','Archivos legibles y completos']; }
  else if (/pretensi|solicitud|resultado|objetivo/.test(text)) { title='Define qué resultado buscas'; detail='Selecciona una salida concreta y compatible con los hechos registrados.'; items=['Petición principal','Alternativas aceptables','Plazo o urgencia relevante']; }
  const required = questions.filter(q=>q.required).length;
  return { title, detail, items, required, total:questions.length };
}

export function clientCaseOverview(detail={}, docs=[], product={}, journey=null) {
  const stage=friendlyCaseState(detail), action=nextCaseAction(detail), result=detail.result||{};
  const progressSteps=[['Información','✓'],['Análisis',stage.progress>=45?'✓':'2'],['Revisión',stage.progress>=70?'✓':'3'],['Resultado',stage.progress>=90?'✓':'4']];
  return `<section class="m292-case-overview"><article class="m292-case-status-card"><div><span class="badge ${stage.cls}">${esc(stage.label)}</span><h2>${esc(action.title)}</h2><p>${esc(action.text)}</p><button class="btn primary" data-action="case-tab" data-tab="${esc(action.tab)}" data-case-id="${esc(detail.id)}">${esc(action.button)}</button></div><img src="/assets/brand-visuals/internal/${stage.visual}" alt=""></article><div class="m292-stage-track">${progressSteps.map(([label,value],index)=>`<div class="${stage.progress >= [20,45,70,90][index]?'complete':''}"><span>${value}</span><b>${label}</b></div>`).join('')}</div><section class="section-grid"><div class="card span-8"><div class="card-header"><div><h2>Resumen de tu expediente</h2><p>La información principal que debes tener presente.</p></div></div><div class="fact-grid"><div class="fact"><small>Solución</small><span>${esc(product.title||detail.product_code)}</span></div><div class="fact"><small>Estado</small><span>${esc(stage.label)}</span></div><div class="fact"><small>Nivel de revisión</small><span>${esc(result.risk_label||riskLabels[detail.risk]||'Por definir')}</span></div><div class="fact"><small>Resultado preliminar</small><span>${esc(result.route||'En análisis')}</span></div><div class="fact"><small>Documentos vinculados</small><span>${docs.length}</span></div><div class="fact"><small>Última actualización</small><span>${esc(dateText(detail.updated_at))}</span></div></div></div><div class="card span-4 m292-help-panel"><img src="/assets/brand-visuals/internal/next-step.svg" alt=""><h3>Antes de continuar</h3><ul><li>Confirma nombres, fechas y valores.</li><li>Relaciona soportes legibles.</li><li>Lee las advertencias de revisión.</li></ul></div></section></section>`;
}

export function clientReviewPanel(detail={}, journey=null) {
  const review = detail.review_status || 'Pendiente de revisión específica';
  const legalDone=Boolean(journey?.legal_approver_id), qaDone=Boolean(journey?.qa_approver_id);
  return `<section class="m292-review-layout"><article class="card"><div class="card-header"><div><h2>Estado de la revisión</h2><p>Tu documento solo puede avanzar cuando se completen los controles aplicables.</p></div><span class="badge ${legalDone&&qaDone?'success':'warning'}">${esc(review)}</span></div><div class="m292-review-steps"><div class="${legalDone?'complete':''}"><span>${legalDone?'✓':'1'}</span><div><b>Revisión jurídica</b><p>Valida contenido, hechos, riesgos y condiciones del documento.</p></div></div><div class="${qaDone?'complete':''}"><span>${qaDone?'✓':'2'}</span><div><b>Control de calidad</b><p>Comprueba versión, formato, consistencia y ausencia de variables rotas.</p></div></div><div class="${legalDone&&qaDone?'complete':''}"><span>${legalDone&&qaDone?'✓':'3'}</span><div><b>Listo para entrega</b><p>La misma revisión debe superar ambos controles antes de liberarse.</p></div></div></div></article><aside class="card m292-review-visual"><img src="/assets/brand-visuals/internal/review-workflow.svg" alt=""><div class="legal-notice"><b>Uso responsable.</b> La aprobación del documento no garantiza el resultado de un trámite, negociación o proceso.</div></aside></section>`;
}

export function clientFollowUpPanel(detail={}, journey=null) {
  const followUps=journey?.follow_ups||[];
  return `<section class="section-grid"><div class="card span-7"><div class="card-header"><div><h2>Siguientes pasos</h2><p>Acciones posteriores para que no pierdas el seguimiento del caso.</p></div></div>${followUps.length?`<div class="follow-up-list">${followUps.map(item=>`<div class="follow-up-item"><div><b>${esc(item.action_label)}</b><small>${esc(item.due_at?dateText(item.due_at):'Fecha por definir')} · ${esc(humanize(item.effective_status))}</small>${item.note?`<p>${esc(item.note)}</p>`:''}</div></div>`).join('')}</div>`:emptyState({visual:'next-step.svg',title:'Aún no hay actividades posteriores',text:'Las acciones de seguimiento aparecerán cuando el documento o la solución se entregue.'})}</div><aside class="card span-5 m292-help-panel"><img src="/assets/brand-visuals/internal/support-center.svg" alt=""><h3>¿Qué debes conservar?</h3><ul><li>Constancia de envío o radicación.</li><li>Respuestas y comunicaciones recibidas.</li><li>Fechas relevantes y recordatorios operativos.</li></ul><div class="legal-notice"><b>Importante.</b> Las fechas de esta vista son referencias operativas y no sustituyen la verificación de términos legales aplicables.</div></aside></section>`;
}

export function friendlyDocumentState(doc={}) {
  const raw=`${doc.status||''} ${doc.kind||''}`.toLowerCase();
  if (/aprob|final|entreg/.test(raw)) return ['Listo','success'];
  if (/revisi|qa/.test(raw)) return ['En revisión','warning'];
  if (/borrador|draft|generad/.test(raw)) return ['Borrador','blue'];
  return [humanize(doc.status||'Disponible'),''];
}
