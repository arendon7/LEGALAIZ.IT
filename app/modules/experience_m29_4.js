import { esc, humanize } from '../core.js';

const UI_PREFS_KEY = 'legalaizit:m294:ui-preferences';

const safeStore = {
  get(key, fallback = null) {
    try { const value = localStorage.getItem(key); return value === null ? fallback : JSON.parse(value); }
    catch { return fallback; }
  },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch {} },
};

export const productJourneys = Object.freeze({
  'CO-LA-001': { visual:'journey-co-la-001.svg', label:'Liquidación y reclamación laboral', steps:[['Reconstruye la relación','Confirma fechas, salario, jornada y forma de terminación.'],['Conciliar valores','Compara pagos, deducciones y acreencias con sus soportes.'],['Evaluar riesgos','Identifica diferencias, prescripción y pruebas faltantes.'],['Preparar la salida','Genera cálculo, reclamación, matriz de soportes o acuerdo.']], prepare:['Contrato, certificaciones o comunicaciones','Desprendibles, pagos y comprobantes','Fechas de ingreso, retiro y salario'], outputs:['Informe de liquidación','Reclamación laboral','Matriz probatoria','Propuesta de acuerdo'] },
  'CO-LA-002': { visual:'journey-co-la-002.svg', label:'Contrato de trabajo', steps:[['Define la modalidad','Selecciona duración, cargo y lugar de ejecución.'],['Ajusta las condiciones','Establece jornada, salario, funciones y beneficios.'],['Gestiona riesgos','Revisa subordinación, SST, datos y confidencialidad.'],['Formaliza la relación','Obtén contrato y anexos coherentes entre sí.']], prepare:['Identificación de empleador y trabajador','Cargo, salario, jornada y sede','Funciones, riesgos y condiciones especiales'], outputs:['Contrato laboral','Anexo de funciones','Actas y comunicaciones','Guía de cierre'] },
  'CO-EM-003': { visual:'journey-co-em-003.svg', label:'Prestación de servicios', steps:[['Describe el servicio','Delimita alcance, entregables y responsables.'],['Define aceptación y pago','Fija hitos, honorarios, impuestos y soportes.'],['Distribuye riesgos','Regula independencia, datos, PI y responsabilidad.'],['Prepara el paquete','Genera contrato, anexos y actas de ejecución.']], prepare:['Datos de las partes','Alcance, entregables y cronograma','Honorarios, gastos y criterios de aceptación'], outputs:['Contrato de servicios','Anexo de alcance','Acta de inicio','Acta de terminación'] },
  'CO-EM-004': { visual:'journey-co-em-004.svg', label:'Confidencialidad y propiedad intelectual', steps:[['Clasifica la información','Identifica secretos, datos, accesos y desarrollos.'],['Define los usos permitidos','Establece finalidad, receptores y restricciones.'],['Asigna titularidades','Regula software, contenidos, mejoras e IA.'],['Activa controles','Genera acuerdo, inventarios y protocolo de incidentes.']], prepare:['Inventario de información y activos','Personas con acceso y finalidad','Desarrollos, software, datos e IA involucrados'], outputs:['Acuerdo de confidencialidad','Inventario de información','Anexo de PI e IA','Protocolo de incidentes'] },
  'CO-AR-001': { visual:'journey-co-ar-001.svg', label:'Arrendamiento de vivienda', steps:[['Identifica inmueble y partes','Confirma dirección, destinación y capacidad de las partes.'],['Define condiciones económicas','Regula canon, administración, servicios y ajustes.'],['Documenta la entrega','Registra inventario, estado y obligaciones.'],['Prepara el cierre','Incluye terminación, restitución y actas.']], prepare:['Documentos de las partes','Información e inventario del inmueble','Canon, duración, servicios y administración'], outputs:['Contrato de arrendamiento','Inventario del inmueble','Acta de entrega','Acta de restitución'] },
  'CO-SA-001': { visual:'journey-co-sa-001.svg', label:'Petición en salud', steps:[['Ubica la necesidad','Identifica servicio, medicamento, procedimiento o respuesta pendiente.'],['Ordena antecedentes','Relaciona diagnósticos, órdenes y comunicaciones.'],['Determina la solicitud','Define autorización, continuidad, entrega o programación.'],['Prepara radicación','Genera petición, anexos y ruta de seguimiento.']], prepare:['Órdenes, fórmulas o historia relevante','Respuestas de EPS, IPS o prestador','Datos de contacto y urgencia clínica'], outputs:['Derecho de petición','Relación de anexos','Guía de radicación','Seguimiento de términos'] },
  'CO-CD-001': { visual:'journey-co-cd-001.svg', label:'Hábeas data financiero', steps:[['Identifica el dato','Ubica obligación, fuente y operador de información.'],['Contrasta soportes','Revisa pagos, comunicaciones y permanencia del reporte.'],['Define la corrección','Solicita consulta, actualización, rectificación o retiro procedente.'],['Activa seguimiento','Genera reclamo, anexos y control de respuesta.']], prepare:['Reporte o consulta de central de riesgo','Comprobantes de pago o paz y salvo','Comunicaciones con acreedor u operador'], outputs:['Reclamo de hábeas data','Solicitud de soportes','Matriz de inconsistencias','Ruta de seguimiento'] },
  'CO-CD-003': { visual:'journey-co-cd-003.svg', label:'Protección al consumidor', steps:[['Describe la compra','Identifica producto, servicio, proveedor y fecha.'],['Documenta el incumplimiento','Relaciona falla, publicidad, garantía y comunicaciones.'],['Selecciona la pretensión','Define reparación, cambio, devolución, retracto o reversión.'],['Prepara la reclamación','Genera documento, anexos y seguimiento.']], prepare:['Factura, orden o comprobante','Garantía, publicidad y comunicaciones','Fotos, videos o evidencia del problema'], outputs:['Reclamación directa','Solicitud de garantía','Retracto o reversión','Matriz de evidencias'] },
  'CO-CD-004': { visual:'journey-co-cd-004.svg', label:'Deuda y acuerdo de pago', steps:[['Conciliar la obligación','Verifica capital, abonos, cargos y saldo.'],['Definir condiciones','Establece cuotas, fechas, intereses y garantías.'],['Formalizar compromisos','Regula incumplimiento, aceleración y comunicaciones.'],['Controlar el cierre','Genera acuerdo, pagaré, estado de cuenta y paz y salvo.']], prepare:['Contrato, factura o título de la obligación','Estado de cuenta y comprobantes de abono','Capacidad de pago y propuesta de cuotas'], outputs:['Estado de cuenta','Acuerdo de pago','Pagaré y carta de instrucciones','Paz y salvo'] },
  'CO-TR-001': { visual:'journey-co-tr-001.svg', label:'Verificación de fotodetección', steps:[['Identifica el sistema','Ubica autoridad, dispositivo, lugar y fecha.'],['Consulta fuentes oficiales','Contrasta autorizaciones, registros y evidencia disponible.'],['Evalúa coincidencias','Distingue datos confirmados, vacíos y contradicciones.'],['Documenta el resultado','Genera informe, matriz de fuentes y solicitudes.']], prepare:['Comparendo o evidencia recibida','Lugar, fecha y autoridad relacionada','Consultas o respuestas oficiales existentes'], outputs:['Informe de verificación','Matriz de fuentes','Solicitud de información','Lista de inconsistencias'] },
  'CO-TR-002': { visual:'journey-co-tr-002.svg', label:'Fotomulta no notificada', steps:[['Obtén el expediente','Solicita comparendo, evidencia y constancias de notificación.'],['Reconstruye los términos','Ordena fechas de detección, validación, envío y conocimiento.'],['Evalúa el debido proceso','Identifica omisiones, dirección usada y oportunidad de defensa.'],['Formula la actuación','Genera petición, reclamación y ruta de seguimiento.']], prepare:['Comparendo y consulta en sistemas','Direcciones registradas y comunicaciones','Constancias de envío o conocimiento'], outputs:['Solicitud de expediente','Reclamación por notificación','Matriz cronológica','Guía de seguimiento'] },
});

export function productJourney(code = '') { return productJourneys[code] || null; }

export function productJourneySection(code = '') {
  const item = productJourney(code);
  if (!item) return '';
  return `<section class="m294-product-journey" aria-labelledby="m294-journey-title"><div class="m294-product-journey-head"><div><span class="eyebrow">Recorrido de esta solución</span><h2 id="m294-journey-title">De los hechos a un resultado utilizable</h2><p>Comprende desde el inicio qué información se analiza, qué decisiones se toman y qué documentos puedes obtener.</p></div><img src="/assets/brand-visuals/internal/${esc(item.visual)}" alt="Recorrido visual de ${esc(item.label)}"></div><ol class="m294-journey-steps">${item.steps.map(([title,text],index)=>`<li><span>${index+1}</span><div><b>${esc(title)}</b><p>${esc(text)}</p></div></li>`).join('')}</ol><div class="m294-journey-columns"><article><h3>Ten a la mano</h3><ul>${item.prepare.map(value=>`<li>${esc(value)}</li>`).join('')}</ul></article><article><h3>Resultados posibles</h3><ul>${item.outputs.map(value=>`<li>${esc(value)}</li>`).join('')}</ul></article></div></section>`;
}

export function wizardContextCard(code = '', section = '') {
  const journey = productJourney(code);
  if (!journey) return '';
  const lower = String(section).toLowerCase();
  let reason = 'Esta etapa permite adaptar el documento y detectar información que requiere revisión.';
  let check = 'Confirma que cada respuesta corresponda con un soporte o con un hecho que puedas explicar.';
  if (/parte|identific|persona/.test(lower)) { reason='Necesitamos identificar correctamente quién asume cada derecho y obligación.'; check='Verifica nombres, documentos, razón social y representación.'; }
  else if (/valor|econ|pago|salario|canon|deuda/.test(lower)) { reason='Los valores alimentan cálculos, obligaciones y cláusulas económicas relacionadas.'; check='Contrasta cifras, fechas, abonos, impuestos y periodicidad.'; }
  else if (/hecho|anteced|situaci/.test(lower)) { reason='La secuencia de hechos determina la ruta jurídica y la utilidad de los documentos.'; check='Ordena cronológicamente y diferencia hechos de opiniones.'; }
  else if (/soporte|evidencia|document/.test(lower)) { reason='Los soportes permiten validar lo informado y reducir contradicciones.'; check='Usa archivos completos, legibles y vinculados al hecho correcto.'; }
  else if (/solicitud|objetivo|resultado|pretensi/.test(lower)) { reason='La salida debe ser concreta, jurídicamente posible y coherente con los hechos.'; check='Prioriza el resultado principal y registra alternativas aceptables.'; }
  return `<section class="summary-card m294-context-card"><div class="m294-context-card-head"><img src="/assets/brand-visuals/internal/contextual-help.svg" alt=""><div><span class="eyebrow">Por qué te preguntamos esto</span><h3>${esc(reason)}</h3></div></div><p><b>Antes de continuar:</b> ${esc(check)}</p><button class="btn ghost sm" data-action="context-help-dialog">Ver ayuda de esta pantalla</button></section>`;
}

const routeHelp = [
  [/^\/$/, ['Panel principal','Continúa un expediente o inicia una nueva solución.','Prioriza la tarjeta que muestra el siguiente paso.']],
  [/^\/soluciones/, ['Soluciones jurídicas','Compara alcance, datos necesarios, resultados y nivel de revisión.','Abre una ficha antes de iniciar para entender el recorrido completo.']],
  [/^\/nuevo\//, ['Formulario guiado','Responde por etapas y guarda el avance cuando lo necesites.','Utiliza información verificable y revisa el resumen antes del análisis.']],
  [/^\/nuevo$/, ['Orientador de soluciones','Describe la necesidad con tus propias palabras.','No necesitas conocer el nombre jurídico del documento.']],
  [/^\/caso\//, ['Expediente','Reúne información, soportes, documentos, revisión y seguimiento.','La tarjeta superior indica el siguiente paso recomendado.']],
  [/^\/casos/, ['Mis expedientes','Filtra por estado y abre el caso que requiere atención.','Los estados explican qué falta y quién debe actuar.']],
  [/^\/documentos/, ['Centro documental','Consulta borradores, revisiones y documentos disponibles.','Verifica siempre versión, estado y advertencias antes de descargar.']],
  [/^\/revision/, ['Bandeja de revisión','Prioriza por riesgo, urgencia y etapa.','Abre el expediente completo antes de aprobar o devolver.']],
  [/^\/fuentes/, ['Fuentes jurídicas','Comprueba vigencia, alcance y aplicación.','La fuente debe quedar vinculada con la decisión o cláusula que respalda.']],
  [/^\/notificaciones/, ['Notificaciones','Revisa cambios y acciones pendientes.','Abrir una notificación la marca como leída y conserva la ruta al expediente.']],
  [/^\/ayuda/, ['Centro de ayuda','Encuentra guías por rol y por momento del proceso.','La ayuda explica la plataforma; no reemplaza la revisión del caso.']],
];

export function contextualHelp(path = '/', user = {}, wizard = null) {
  const row = routeHelp.find(([pattern]) => pattern.test(path))?.[1] || ['Ayuda contextual','Esta pantalla forma parte de un proceso jurídico trazable.','Revisa el alcance y utiliza los accesos de ayuda cuando tengas dudas.'];
  const roleTip = user.role === 'specialist' ? 'Registra criterio, evidencia y responsable en cada decisión.' : user.role === 'admin' ? 'Conserva separación de permisos, auditoría y compuertas de liberación.' : 'No uses datos ficticios en casos reales ni omitas información relevante.';
  const product = wizard?.code ? productJourney(wizard.code) : null;
  return { title:row[0], text:row[1], tip:row[2], roleTip, product };
}

export function contextualHelpDialogBody(path = '/', user = {}, wizard = null) {
  const help = contextualHelp(path,user,wizard);
  return `<div class="m294-context-dialog"><img src="/assets/brand-visuals/internal/contextual-help.svg" alt=""><div><h3>${esc(help.title)}</h3><p>${esc(help.text)}</p><ul><li>${esc(help.tip)}</li><li>${esc(help.roleTip)}</li>${help.product?`<li>Esta solución sigue el recorrido de <b>${esc(help.product.label)}</b>.</li>`:''}</ul></div></div><div class="m294-shortcuts"><span><kbd>⌘/Ctrl</kbd> + <kbd>K</kbd><small>Buscar</small></span><span><kbd>?</kbd><small>Ayuda</small></span><span><kbd>Esc</kbd><small>Cerrar</small></span></div>`;
}

function normalize(value='') { return String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9@._ -]+/g,' ').replace(/\s+/g,' ').trim(); }
const synonyms = Object.freeze({
  arriendo:['arrendamiento','canon','inquilino','arrendador','vivienda'], contrato:['laboral','servicios','confidencialidad','arrendamiento'], empleo:['laboral','trabajo','salario','liquidacion'], despido:['liquidacion','indemnizacion','laboral'], eps:['salud','ips','medicamento','autorizacion'], fotomulta:['comparendo','transito','notificacion','fotodeteccion'], deuda:['cobro','pago','pagare','cartera'], reporte:['habeas data','centrales de riesgo','credito'], compra:['consumidor','garantia','retracto','devolucion'], privacidad:['datos','confidencialidad','habeas data'], ia:['inteligencia artificial','software','propiedad intelectual'],
});
function searchTerms(query='') { const normalized=normalize(query); const expanded=new Set(normalized.split(' ').filter(Boolean)); Object.entries(synonyms).forEach(([key,values])=>{ if(normalized.includes(key)||values.some(value=>normalize(value).includes(normalized))) values.forEach(value=>normalize(value).split(' ').forEach(term=>expanded.add(term))); }); return [...expanded]; }
function scoreText(text='', terms=[]) { const haystack=normalize(text); return terms.reduce((score,term)=>score+(haystack.includes(term)?(haystack.startsWith(term)?4:2):0),0); }

export function workspaceSearch(query='', products=[], cases=[], documents=[], serverRows=[]) {
  const terms=searchTerms(query); if (!terms.length) return [];
  const rows=[];
  products.forEach(item=>{ const journey=productJourney(item.code); const score=scoreText(`${item.code} ${item.title} ${item.summary} ${item.vertical} ${(item.outcomes||[]).join(' ')} ${journey?.prepare.join(' ')} ${journey?.outputs.join(' ')}`,terms); if(score)rows.push({id:`product-${item.code}`,type:'Solución',title:item.title,subtitle:`${item.vertical} · ${journey?.label||item.code}`,route:`/solucion/${encodeURIComponent(item.code)}`,score:score+3,icon:'◇'}); });
  cases.forEach(item=>{ const score=scoreText(`${item.title} ${item.product_code} ${item.status} ${item.review_status}`,terms); if(score)rows.push({id:`case-${item.id}`,type:'Expediente',title:item.title,subtitle:`${item.product_code} · ${humanize(item.status||'En curso')}`,route:`/caso/${encodeURIComponent(item.id)}`,score:score+4,icon:'▣'}); });
  documents.forEach(item=>{ const score=scoreText(`${item.name} ${item.case_title||''} ${item.kind||''} ${item.status||''}`,terms); if(score)rows.push({id:`doc-${item.id||item.name}`,type:'Documento',title:item.name,subtitle:item.case_title||item.case_id||humanize(item.status||'Disponible'),route:'/documentos',score:score+2,icon:'▤'}); });
  serverRows.forEach((item,index)=>{ const score=scoreText(`${item.title||item.name||''} ${item.subtitle||item.detail||''}`,terms); if(score)rows.push({id:`server-${index}`,type:item.type||'Resultado',title:item.title||item.name||'Resultado',subtitle:item.subtitle||item.detail||'',route:item.route||item.url||'/',score:score+1,icon:'⌕'}); });
  const unique=new Map(); rows.sort((a,b)=>b.score-a.score).forEach(row=>{const key=`${row.type}:${row.title}:${row.route}`;if(!unique.has(key))unique.set(key,row);}); return [...unique.values()].slice(0,24);
}

export function searchDialogBody(query='') {
  return `<form id="global-search-form" class="global-search-form"><label for="global-search-input">Busca por situación, expediente o documento</label><div class="search-box"><span aria-hidden="true">⌕</span><input id="global-search-input" class="input" autocomplete="off" placeholder="Ej. no me notificaron una fotomulta" value="${esc(query)}" aria-describedby="m294-search-hint"><button class="btn primary" type="submit">Buscar</button></div><small id="m294-search-hint">Puedes escribir el problema con tus propias palabras.</small></form><div class="m294-search-suggestions" aria-label="Búsquedas sugeridas">${['Necesito un contrato','No me pagaron bien','Problema con una compra','Fotomulta no notificada','Corregir un reporte'].map(value=>`<button type="button" data-action="search-suggestion" data-query="${esc(value)}">${esc(value)}</button>`).join('')}</div><div id="global-search-results" class="search-results" role="region" aria-live="polite"><div class="m294-search-welcome"><img src="/assets/brand-visuals/internal/search-premium.svg" alt=""><div><b>Una búsqueda pensada para necesidades reales</b><p>Encuentra soluciones, expedientes y documentos sin conocer términos jurídicos.</p></div></div></div>`;
}

export function searchResultsHtml(rows=[], query='') {
  if(!rows.length)return `<div class="empty-state compact m294-search-empty"><img src="/assets/brand-visuals/internal/empty-search.svg" alt=""><h3>No encontramos coincidencias</h3><p>Prueba describiendo el hecho principal, el documento o la entidad involucrada.</p></div>`;
  const groups=['Solución','Expediente','Documento','Resultado'];
  return `<div class="m294-search-summary"><b>${rows.length} resultados</b><span>para “${esc(query)}”</span></div>${groups.map(group=>{const items=rows.filter(row=>row.type===group||(group==='Resultado'&&!groups.slice(0,3).includes(row.type)));if(!items.length)return'';return `<section class="m294-search-group"><h3>${esc(group)}${items.length===1?'':'s'}</h3>${items.map(item=>`<button class="search-result" type="button" data-action="go-close-dialog" data-route="${esc(item.route)}"><span class="m294-search-icon" aria-hidden="true">${esc(item.icon||'⌕')}</span><span><b>${esc(item.title)}</b><small>${esc(item.subtitle)}</small></span><i aria-hidden="true">›</i></button>`).join('')}</section>`;}).join('')}`;
}

export function getUiPreferences() { return { largeText:false, highContrast:false, reduceMotion:false, ...(safeStore.get(UI_PREFS_KEY,{})||{}) }; }
export function setUiPreference(name='', enabled=false) { const prefs=getUiPreferences(); if(Object.hasOwn(prefs,name))prefs[name]=Boolean(enabled);safeStore.set(UI_PREFS_KEY,prefs);applyUiPreferences();return prefs; }
export function applyUiPreferences() { const prefs=getUiPreferences(); document.documentElement.classList.toggle('m294-large-text',prefs.largeText);document.documentElement.classList.toggle('m294-high-contrast',prefs.highContrast);document.documentElement.classList.toggle('m294-reduce-motion',prefs.reduceMotion);return prefs; }

export function accessibilityDialogBody() {
  const prefs=getUiPreferences();
  const options=[['largeText','Texto más grande','Aumenta el tamaño base y el espaciado de lectura.','Aa'],['highContrast','Contraste reforzado','Diferencia mejor fondos, bordes, enlaces y controles.','◐'],['reduceMotion','Reducir movimiento','Desactiva transiciones y desplazamientos animados.','―']];
  return `<div class="m294-accessibility-dialog"><img src="/assets/brand-visuals/internal/accessibility-controls.svg" alt=""><div><h3>Adapta la interfaz a tu forma de navegar</h3><p>Estas preferencias solo cambian la presentación en este navegador. No guardan información de tus casos.</p></div></div><div class="m294-preference-list">${options.map(([key,title,text,icon])=>`<button class="m294-preference ${prefs[key]?'active':''}" type="button" role="switch" aria-checked="${prefs[key]}" data-action="accessibility-toggle" data-preference="${key}"><span aria-hidden="true">${icon}</span><div><b>${title}</b><small>${text}</small></div><i>${prefs[key]?'Activado':'Desactivado'}</i></button>`).join('')}</div>`;
}

export function accessibilityPage({shell,pageHeader}) {
  const prefs=getUiPreferences();
  return shell(`<div class="page">${pageHeader({eyebrow:'Accesibilidad',title:'Una experiencia que puedes adaptar',description:'LegalAIZ.it incorpora navegación por teclado, foco visible, etiquetas semánticas, reducción de movimiento y preferencias locales de lectura.'})}<section class="m294-accessibility-hero"><img src="/assets/brand-visuals/internal/accessibility-controls.svg" alt="Controles de accesibilidad"><div><h2>Preferencias de presentación</h2><p>Cambia el tamaño del texto, refuerza el contraste o reduce las animaciones. Ninguna preferencia contiene datos jurídicos.</p><button class="btn primary" data-action="accessibility-dialog">Configurar accesibilidad</button></div></section><section class="section-grid"><article class="card span-4"><h3>Navegación por teclado</h3><p>Usa Tab para recorrer controles, Enter para activar y Esc para cerrar diálogos.</p></article><article class="card span-4"><h3>Atajos globales</h3><p>Presiona Ctrl/⌘ + K para buscar y ? para abrir ayuda contextual.</p></article><article class="card span-4"><h3>Lectura y foco</h3><p>Los cambios de pantalla se anuncian y el foco vuelve al control que abrió un diálogo.</p></article></section><div class="legal-notice mt-22"><b>Preferencias activas:</b> texto grande ${prefs.largeText?'sí':'no'}, contraste reforzado ${prefs.highContrast?'sí':'no'} y movimiento reducido ${prefs.reduceMotion?'sí':'no'}.</div></div>`);
}

export function routeAnnouncement(path='/', products=[], cases=[]) {
  if(path==='/')return 'Panel principal de LegalAIZ.it';
  if(path==='/soluciones')return 'Listado de soluciones jurídicas';
  if(path.startsWith('/solucion/')||path.startsWith('/soluciones/')){const code=decodeURIComponent(path.split('/').pop()||'');const product=products.find(item=>item.code===code||item.slug===code);return product?`Solución: ${product.title}`:'Detalle de solución';}
  if(path.startsWith('/nuevo/'))return 'Formulario guiado de solución';
  if(path==='/nuevo')return 'Orientador de soluciones';
  if(path==='/casos')return 'Listado de expedientes';
  if(path.startsWith('/caso/')){const id=decodeURIComponent(path.split('/')[2]||'');const item=cases.find(row=>String(row.id)===id);return item?`Expediente: ${item.title}`:'Detalle de expediente';}
  const labels={'/documentos':'Centro documental','/notificaciones':'Notificaciones','/ayuda':'Centro de ayuda','/accesibilidad':'Accesibilidad','/revision':'Bandeja de revisión','/fuentes':'Fuentes jurídicas','/operacion':'Operación jurídica','/calidad':'Calidad y gobierno','/configuracion':'Configuración'};
  return labels[path]||humanize(path.replace(/^\//,''))||'LegalAIZ.it';
}

export function announceRoute(path='/', products=[], cases=[]) {
  const label=routeAnnouncement(path,products,cases); const announcer=document.getElementById('route-announcer'); if(announcer){announcer.textContent='';setTimeout(()=>{announcer.textContent=`Vista cargada: ${label}`;},20);} if(!document.title.startsWith(label))document.title=`${label} · LegalAIZ.it`; return label;
}
