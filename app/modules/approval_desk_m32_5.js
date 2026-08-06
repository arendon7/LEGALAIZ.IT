'use strict';

import { api, app, currentPath, dateText, esc, state, toast } from '../core.js';

const BASE = '/api/m32/approval-desk';
const ROUTE = '/mesa-juridica';
const local = { summary:null, detail:null, preview:null, comparison:null, filter:'all', rendering:false, token:0 };

const statusLabels = {
  draft:'Sin revisión', legal_pending:'Pendiente jurídica', qa_pending:'Pendiente QA',
  changes_required:'Requiere ajustes', rejected:'Rechazado', findings_pending:'Hallazgos pendientes',
  ready_to_release:'Listo para liberar', released:'Liberado',
};
const statusClass = {
  draft:'neutral', legal_pending:'warning', qa_pending:'blue', changes_required:'danger', rejected:'danger',
  findings_pending:'warning', ready_to_release:'success', released:'success',
};
const severityLabels = { blocking:'Bloqueante', major:'Mayor', minor:'Menor', observation:'Observación' };
const severityClass = { blocking:'danger', major:'danger', minor:'warning', observation:'blue' };

function professional() { return state.user && ['specialist','admin'].includes(state.user.role); }
function encode(value) { return encodeURIComponent(String(value || '')); }
function compactHash(value) { const text=String(value||''); return text ? `${text.slice(0,12)}…${text.slice(-8)}` : 'Sin hash'; }
function currentCaseId() {
  const path=currentPath();
  if (!path.startsWith(`${ROUTE}/`)) return '';
  return decodeURIComponent(path.slice(ROUTE.length+1).split('/')[0] || '');
}
function mainNode() { return document.getElementById('main-content'); }
function setContext(page='Mesa Jurídica') {
  const context=document.querySelector('.workspace-context');
  if (context) context.innerHTML=`<span>Trabajo jurídico</span><b>${esc(page)}</b>`;
  document.querySelectorAll('.side-nav .nav-link').forEach(link => link.classList.toggle('active', link.getAttribute('href') === `#${ROUTE}`));
}
function ensureNavigation() {
  if (!professional()) return;
  const nav=document.querySelector('.side-nav');
  if (!nav || nav.querySelector(`[href="#${ROUTE}"]`)) return;
  const groups=[...nav.querySelectorAll('.nav-group')];
  const target=groups[0];
  if (!target) return;
  const link=document.createElement('a');
  link.className='nav-link m325-nav-link';
  link.href=`#${ROUTE}`;
  link.innerHTML='<span class="nav-icon">⚖</span><span>Mesa Jurídica</span>';
  const reference=target.querySelector('[href="#/revision"], [href="#/operacion"]');
  if (reference) reference.insertAdjacentElement('afterend',link); else target.appendChild(link);
}
function pageFrame(content, title='Mesa Jurídica') {
  const main=mainNode();
  if (!main) return false;
  setContext(title);
  main.innerHTML=`<div class="page m325-page">${content}</div>`;
  main.focus({preventScroll:true});
  return true;
}
function loading(label='Cargando Mesa Jurídica…') {
  return pageFrame(`<section class="m325-loading"><div class="boot-spinner" aria-hidden="true"></div><h1>${esc(label)}</h1><p>Validando expediente, revisión y cadena de auditoría.</p></section>`);
}
function errorPanel(error) {
  return pageFrame(`<section class="result-banner red"><div class="result-icon">!</div><div><h2>No fue posible cargar la Mesa Jurídica</h2><p>${esc(error.message || error)}</p></div><button class="btn secondary" data-m325-action="reload">Reintentar</button></section>`);
}
function accessDenied() {
  return pageFrame(`<section class="m325-access"><span class="m325-lock">⚖</span><h1>Acceso profesional restringido</h1><p>La Mesa Jurídica contiene documentos, hallazgos y decisiones de aprobación. Solo especialistas jurídicos y administración pueden consultarla.</p><a class="btn secondary" href="#/">Volver al inicio</a></section>`);
}
function kpi(label,value,detail,kind='') {
  return `<article class="m325-kpi ${kind}"><small>${esc(label)}</small><strong>${esc(value)}</strong><span>${esc(detail)}</span></article>`;
}
function statusBadge(status) { return `<span class="m325-status ${statusClass[status]||'neutral'}">${esc(statusLabels[status]||status)}</span>`; }
function approvalBadge(label, approval) {
  const decision=approval?.decision;
  const cls=decision==='approve'?'success':decision==='reject'?'danger':'warning';
  const text=decision==='approve'?'Aprobada':decision==='reject'?'Rechazada':'Pendiente';
  return `<span class="m325-approval ${cls}"><b>${esc(label)}</b><span>${text}</span></span>`;
}
function emptyList() {
  const action=state.user?.role==='admin' ? '<button class="btn primary" data-m325-action="bootstrap">Preparar bandeja desde documentos vigentes</button>' : '';
  return `<section class="m325-empty"><div>⚖</div><h2>La bandeja aún no tiene documentos registrados</h2><p>La mesa trabaja sobre revisiones inmutables de documentos concretos. Administración debe registrar primero los DOCX vigentes.</p>${action}</section>`;
}
function listCard(row) {
  return `<article class="m325-case-card" data-status="${esc(row.status)}">
    <div class="m325-case-top"><div><span class="eyebrow">${esc(row.product_code)} · ${esc(row.source_case_id)}</span><h2>${esc(row.title)}</h2></div>${statusBadge(row.status)}</div>
    <div class="m325-case-facts"><span><small>Revisión</small><b>${esc(row.current_revision_id||'Sin revisión')}</b></span><span><small>Hash vigente</small><code title="${esc(row.current_sha256||'')}">${esc(compactHash(row.current_sha256))}</code></span><span><small>Hallazgos abiertos</small><b>${esc(row.open_findings)}</b></span><span><small>Auditoría</small><b>${row.audit_valid?'Íntegra':'Revisar'}</b></span></div>
    <div class="m325-case-approvals">${approvalBadge('Jurídica', row.legal_decision?{decision:row.legal_decision}:null)}${approvalBadge('QA', row.qa_decision?{decision:row.qa_decision}:null)}</div>
    <div class="m325-case-actions"><a class="btn primary sm" href="#${ROUTE}/${encode(row.desk_case_id)}">Abrir revisión</a>${row.release_id?`<a class="btn secondary sm" href="${BASE}/cases/${encode(row.desk_case_id)}/released-download">Descargar liberado</a>`:''}</div>
  </article>`;
}
function listPageHtml(data) {
  const metrics=data.metrics||{};
  const filters=[['all','Todos'],['legal_pending','Pendiente jurídica'],['qa_pending','Pendiente QA'],['changes_required','Ajustes'],['ready_to_release','Listos'],['released','Liberados']];
  const rows=(data.cases||[]).filter(row=>local.filter==='all'||row.status===local.filter);
  return `<header class="m325-hero"><div><span class="eyebrow">M32.5 · Gobierno por documento</span><h1>Mesa Jurídica</h1><p>Revisa cada archivo concreto, registra hallazgos localizados y aprueba únicamente el SHA-256 visible. La aprobación de una plantilla no aprueba sus documentos derivados.</p></div><div class="m325-hero-actions">${state.user?.role==='admin'?'<button class="btn secondary" data-m325-action="bootstrap">Sincronizar documentos nuevos</button>':''}<button class="btn ghost" data-m325-action="reload">Actualizar</button></div></header>
  <section class="m325-kpis">${kpi('Documentos',metrics.total||0,'Revisiones controladas')}${kpi('Pendiente jurídica',metrics.legal_pending||0,'Decisión de especialista','warning')}${kpi('Pendiente QA',metrics.qa_pending||0,'Control independiente','blue')}${kpi('Hallazgos abiertos',metrics.open_findings||0,'Deben cerrarse para liberar','danger')}${kpi('Liberados',metrics.released||0,'Hash exacto aprobado','success')}</section>
  <section class="m325-notice"><b>Control de alcance.</b><span>${esc(data.notice||'')}</span>${metrics.invalid_audit_chains?'<strong>Existe una cadena de auditoría inválida.</strong>':''}</section>
  <section class="m325-toolbar" aria-label="Filtros de bandeja">${filters.map(([value,label])=>`<button class="m325-filter ${local.filter===value?'active':''}" data-m325-filter="${value}">${esc(label)}</button>`).join('')}</section>
  ${!(data.cases||[]).length?emptyList():`<section class="m325-case-grid">${rows.map(listCard).join('')||'<div class="m325-empty compact"><h2>No hay documentos con este estado</h2><p>Cambia el filtro para consultar el resto de la bandeja.</p></div>'}</section>`}`;
}
async function renderList(force=false) {
  if (!professional()) return accessDenied();
  if (force || !local.summary) local.summary=await api(BASE);
  pageFrame(listPageHtml(local.summary),'Bandeja documental');
}
function revisionOption(row,current) { return `<option value="${esc(row.revision_id)}" ${row.revision_id===current?'selected':''}>${esc(row.revision_id)} · ${esc(compactHash(row.sha256))}</option>`; }
function findingRow(row, capabilities) {
  const locator=[row.locator?.page?`p. ${row.locator.page}`:'',row.locator?.clause||'',row.locator?.block_id||''].filter(Boolean).join(' · ')||'Sin localizador';
  return `<article class="m325-finding ${row.state}"><div class="m325-finding-head"><span class="m325-severity ${severityClass[row.severity]||'neutral'}">${esc(severityLabels[row.severity]||row.severity)}</span><b>${esc(locator)}</b><span>${row.state==='open'?'Abierto':'Cerrado'}</span></div><p>${esc(row.description)}</p><small>${esc(row.finding_id)} · ${esc(row.created_by)}</small>${row.state==='open'&&capabilities.resolve_finding?`<button class="btn secondary sm" data-m325-action="resolve-finding" data-finding-id="${esc(row.finding_id)}">Cerrar hallazgo</button>`:''}</article>`;
}
function approvalPanel(type,label,approval,current,capability) {
  const allowed=capability && !approval;
  return `<article class="m325-decision-card"><div><span class="eyebrow">${esc(label)}</span><h3>${approval?approval.decision==='approve'?'Aprobada':'Rechazada':'Pendiente'}</h3></div>${approval?`<p>${esc(approval.comment||'Sin comentario')}</p><dl><div><dt>Actor</dt><dd>${esc(approval.actor?.name||approval.actor?.id)}</dd></div><div><dt>Hash</dt><dd><code>${esc(compactHash(approval.sha256))}</code></dd></div><div><dt>Fecha</dt><dd>${esc(dateText(approval.created_at))}</dd></div></dl>`:`<p>La decisión quedará vinculada de forma inmutable a <code>${esc(compactHash(current?.sha256))}</code>.</p>`}${allowed?`<div class="m325-decision-actions"><button class="btn primary sm" data-m325-action="approve" data-approval-type="${type}" data-decision="approve">Aprobar</button><button class="btn danger sm" data-m325-action="approve" data-approval-type="${type}" data-decision="reject">Rechazar</button></div>`:''}</article>`;
}
function previewHtml(preview) {
  if (!preview) return '<section class="m325-preview-empty"><p>La vista documental aún no se cargó.</p></section>';
  if (preview.rendered) return `<div class="m325-preview-head"><div><b>${esc(preview.page_count)} páginas renderizadas</b><span>${esc(preview.rendering_engine)}</span></div><a class="btn secondary sm" href="${esc(preview.pdf_url)}" target="_blank" rel="noopener">Abrir PDF de revisión</a></div><div class="m325-pages">${(preview.pages||[]).map(page=>`<article class="m325-page-sheet"><header><span>Página ${esc(page.page)}</span><small>Vista extraída del PDF renderizado</small></header><pre>${esc(page.text||'Página sin texto extraíble; requiere inspección visual del PDF.')}</pre></article>`).join('')}</div><p class="m325-preview-warning">${esc(preview.warning||'')}</p>`;
  return `<div class="m325-preview-warning strong"><b>Paginación no disponible.</b><span>${esc(preview.warning||'')}</span></div><div class="m325-structural-preview">${(preview.structural_preview||[]).map((line,index)=>`<p><span>${index+1}</span>${esc(line)}</p>`).join('')}</div>`;
}
function comparisonHtml(comparison) {
  if (!comparison) return '<p class="m325-muted">Selecciona dos revisiones para construir la comparación inmutable.</p>';
  return `<div class="m325-compare-summary"><span><b>${esc(comparison.summary?.added_lines||0)}</b> líneas agregadas</span><span><b>${esc(comparison.summary?.removed_lines||0)}</b> líneas retiradas</span><span>${comparison.changed?'Contenido diferente':'Sin cambios'}</span></div><pre class="m325-diff">${esc((comparison.diff_lines||[]).join('\n')||'No se identificaron diferencias textuales.')}</pre>`;
}
function detailPageHtml(detail,preview) {
  const record=detail.case||{};
  const revisions=detail.revisions||[];
  const current=revisions.find(row=>row.revision_id===record.current_revision_id)||revisions[revisions.length-1];
  const findings=current?.findings||[];
  const approvals=current?.approvals||{};
  const caps=detail.capabilities||{};
  const canRelease=caps.release && detail.workflow_status==='ready_to_release';
  return `<header class="m325-detail-hero"><div><a class="m325-back" href="#${ROUTE}">← Volver a la bandeja</a><span class="eyebrow">${esc(record.product_code)} · ${esc(detail.source_case_id)}</span><h1>${esc(record.title)}</h1><div class="m325-title-meta">${statusBadge(detail.workflow_status)}<span>${esc(record.current_revision_id||'Sin revisión')}</span><code title="${esc(current?.sha256||'')}">${esc(compactHash(current?.sha256))}</code></div></div><div class="m325-hero-actions"><a class="btn secondary" href="#/caso/${encode(detail.source_case_id)}">Abrir expediente</a>${detail.release?`<a class="btn primary" href="${BASE}/cases/${encode(record.case_id)}/released-download">Descargar versión liberada</a>`:''}</div></header>
  <section class="m325-integrity"><div><small>Cadena de auditoría</small><b>${detail.audit?.valid?'Íntegra':'INVÁLIDA'}</b><span>${esc(detail.audit?.events||0)} eventos</span></div><div><small>Revisiones inmutables</small><b>${esc(record.revision_count||0)}</b><span>Vigente: ${esc(record.current_revision_id||'—')}</span></div><div><small>Hallazgos abiertos</small><b>${esc(findings.filter(row=>row.state==='open').length)}</b><span>Todos deben cerrarse para liberar</span></div><div><small>Liberación</small><b>${detail.release?'Exacta':'Pendiente'}</b><span>${detail.release?esc(compactHash(detail.release.sha256)):'Sin archivo exportable'}</span></div></section>
  <section class="m325-layout"><div class="m325-primary">
    <article class="card m325-card"><div class="card-header"><div><span class="eyebrow">Visor por revisión</span><h2>Documento vigente</h2><p>La paginación se obtiene del PDF renderizado cuando el motor está disponible.</p></div>${caps.add_revision?'<button class="btn secondary sm" data-m325-action="register-current">Registrar documento vigente como nueva revisión</button>':''}</div>${previewHtml(preview)}</article>
    <article class="card m325-card"><div class="card-header"><div><span class="eyebrow">Control localizado</span><h2>Hallazgos</h2><p>Página, cláusula y bloque quedan vinculados al hash de la revisión.</p></div></div>${findings.length?`<div class="m325-findings">${findings.map(row=>findingRow(row,caps)).join('')}</div>`:'<div class="m325-empty compact"><h3>Sin hallazgos registrados</h3><p>La ausencia de hallazgos automáticos no equivale a aprobación profesional.</p></div>'}${caps.add_finding?`<form id="m325-finding-form" class="m325-form"><input type="hidden" name="revision_id" value="${esc(current?.revision_id||'')}"><div class="field"><label>Severidad</label><select name="severity" class="select" required><option value="blocking">Bloqueante</option><option value="major">Mayor</option><option value="minor">Menor</option><option value="observation">Observación</option></select></div><div class="field"><label>Página</label><input name="page" class="input" type="number" min="1" max="999"></div><div class="field"><label>Cláusula o sección</label><input name="clause" class="input" maxlength="180"></div><div class="field span-2"><label>Descripción verificable</label><textarea name="description" class="textarea" rows="3" required maxlength="3000"></textarea></div><div class="span-2"><button class="btn primary" type="submit">Registrar hallazgo inmutable</button></div></form>`:''}</article>
    <article class="card m325-card"><div class="card-header"><div><span class="eyebrow">Comparación</span><h2>Cambios entre revisiones</h2><p>La comparación textual no sustituye la inspección visual de todas las páginas.</p></div></div><form id="m325-compare-form" class="m325-compare-form"><select name="from" class="select">${revisions.map(row=>revisionOption(row,revisions[0]?.revision_id)).join('')}</select><span>→</span><select name="to" class="select">${revisions.map(row=>revisionOption(row,current?.revision_id)).join('')}</select><button class="btn secondary" type="submit" ${revisions.length<2?'disabled':''}>Comparar</button></form>${comparisonHtml(local.comparison)}</article>
  </div><aside class="m325-sidebar">
    <article class="card m325-card"><div class="card-header"><div><span class="eyebrow">Aprobación dual</span><h2>Decisiones</h2></div></div><div class="m325-decisions">${approvalPanel('legal','Jurídica',approvals.legal,current,caps.legal_approve)}${approvalPanel('qa','QA',approvals.qa,current,caps.qa_approve)}</div><p class="m325-legal-note">QA solo puede aprobar después de la aprobación jurídica del mismo hash y debe corresponder a una persona diferente.</p></article>
    <article class="card m325-card"><div class="card-header"><div><span class="eyebrow">Versiones</span><h2>Historial</h2></div></div><div class="m325-revisions">${revisions.slice().reverse().map(row=>`<div class="m325-revision ${row.revision_id===record.current_revision_id?'current':''}"><div><b>${esc(row.revision_id)}</b><span>${esc(dateText(row.created_at))}</span></div><code title="${esc(row.sha256)}">${esc(compactHash(row.sha256))}</code><small>${esc(row.note||'Sin nota')}</small></div>`).join('')}</div>${caps.add_revision?`<form id="m325-upload-form" class="m325-upload"><label for="m325-upload-file">Cargar revisión DOCX controlada</label><input id="m325-upload-file" name="file" type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required><textarea name="note" class="textarea" rows="2" placeholder="Explique el cambio" required></textarea><button class="btn secondary sm" type="submit">Registrar nueva revisión</button></form>`:''}</article>
    <article class="card m325-release-card ${canRelease?'ready':''}"><span class="eyebrow">Compuerta final</span><h2>${detail.release?'Documento liberado':canRelease?'Listo para liberar':'Liberación bloqueada'}</h2><p>${detail.release?'La descarga corresponde exactamente al hash aprobado por jurídica y QA.':canRelease?'No existen hallazgos abiertos y ambas aprobaciones coinciden con el hash vigente.':'Deben completarse las decisiones y cerrar todos los hallazgos.'}</p>${canRelease?'<button class="btn primary btn-block" data-m325-action="release">Liberar hash exacto</button>':''}${detail.release?`<dl><div><dt>Release</dt><dd>${esc(detail.release.release_id)}</dd></div><div><dt>SHA-256</dt><dd><code>${esc(compactHash(detail.release.sha256))}</code></dd></div><div><dt>Fecha</dt><dd>${esc(dateText(detail.release.released_at))}</dd></div></dl>`:''}</article>
    <article class="card m325-card"><div class="card-header"><div><span class="eyebrow">Auditoría</span><h2>Cadena enlazada</h2></div></div><dl class="m325-audit"><div><dt>Estado</dt><dd>${detail.audit?.valid?'Válida':'Inválida'}</dd></div><div><dt>Eventos</dt><dd>${esc(detail.audit?.events||0)}</dd></div><div><dt>Último hash</dt><dd><code>${esc(compactHash(detail.audit?.last_hash))}</code></dd></div></dl></article>
  </aside></section>`;
}
async function renderDetail(caseId,force=false) {
  if (!professional()) return accessDenied();
  const token=++local.token;
  if (force || local.detail?.case?.case_id!==caseId) { local.detail=null; local.preview=null; local.comparison=null; }
  if (!local.detail) local.detail=await api(`${BASE}/cases/${encode(caseId)}`);
  const current=local.detail.case?.current_revision_id;
  if (current && !local.preview) {
    try { local.preview=await api(`${BASE}/cases/${encode(caseId)}/revisions/${encode(current)}/preview`); }
    catch (error) { local.preview={rendered:false,warning:error.message,structural_preview:[]}; }
  }
  if (token!==local.token) return;
  pageFrame(detailPageHtml(local.detail,local.preview),'Revisión documental');
}
async function route(force=false) {
  if (!currentPath().startsWith(ROUTE)) return;
  ensureNavigation();
  if (!mainNode()) return setTimeout(()=>route(force),80);
  if (!professional()) return accessDenied();
  try {
    loading();
    const caseId=currentCaseId();
    if (caseId) await renderDetail(caseId,force); else await renderList(force);
  } catch (error) { errorPanel(error); }
}
async function refreshCurrent() {
  local.summary=null; local.detail=null; local.preview=null; local.comparison=null;
  await route(true);
}
async function postJson(path,payload) {
  return api(path,{method:'POST',body:JSON.stringify(payload||{})});
}
async function handleAction(button) {
  const action=button.dataset.m325Action;
  const caseId=local.detail?.case?.case_id;
  if (action==='reload') return refreshCurrent();
  if (action==='bootstrap') {
    if (!window.confirm('Se registrarán en la Mesa Jurídica los DOCX vigentes que aún no tengan expediente de revisión. ¿Continuar?')) return;
    button.disabled=true;
    const result=await postJson(`${BASE}/bootstrap`,{limit:200});
    toast(`${result.created_count} documentos añadidos a la bandeja.`); return refreshCurrent();
  }
  if (!caseId) return;
  const current=local.detail.revisions?.find(row=>row.revision_id===local.detail.case.current_revision_id);
  if (action==='register-current') {
    const note=window.prompt('Explique por qué debe registrarse una nueva revisión del documento vigente:');
    if (!note) return;
    button.disabled=true; await postJson(`${BASE}/cases/${encode(caseId)}/register-current`,{note}); toast('Nueva revisión registrada.'); return refreshCurrent();
  }
  if (action==='resolve-finding') {
    const resolution=window.prompt('Describa cómo se resolvió o por qué se descarta este hallazgo:');
    if (!resolution) return;
    button.disabled=true; await postJson(`${BASE}/cases/${encode(caseId)}/findings/${encode(button.dataset.findingId)}/resolve`,{resolution,state:'resolved'}); toast('Hallazgo cerrado con registro inmutable.'); return refreshCurrent();
  }
  if (action==='approve') {
    const type=button.dataset.approvalType, decision=button.dataset.decision;
    const label=type==='legal'?'jurídica':'QA';
    const comment=window.prompt(`${decision==='approve'?'Fundamento de aprobación':'Motivo de rechazo'} ${label}:`);
    if (!comment) return;
    button.disabled=true;
    await postJson(`${BASE}/cases/${encode(caseId)}/approvals`,{revision_id:current.revision_id,approval_type:type,decision,comment,expected_sha256:current.sha256});
    toast(`Decisión ${label} registrada sobre el hash vigente.`); return refreshCurrent();
  }
  if (action==='release') {
    if (!window.confirm(`Se liberará únicamente el archivo con SHA-256 ${current.sha256}. Esta operación es inmutable. ¿Continuar?`)) return;
    button.disabled=true; await postJson(`${BASE}/cases/${encode(caseId)}/release`,{revision_id:current.revision_id,expected_sha256:current.sha256}); toast('Documento liberado con el hash exacto aprobado.'); return refreshCurrent();
  }
}
async function submitFinding(form) {
  const caseId=local.detail?.case?.case_id;
  const data=new FormData(form);
  const payload=Object.fromEntries(data.entries());
  payload.page=payload.page?Number(payload.page):null;
  const button=form.querySelector('button[type="submit"]'); button.disabled=true;
  await postJson(`${BASE}/cases/${encode(caseId)}/findings`,payload); toast('Hallazgo registrado.'); return refreshCurrent();
}
async function submitComparison(form) {
  const caseId=local.detail?.case?.case_id;
  const data=new FormData(form);
  local.comparison=await api(`${BASE}/cases/${encode(caseId)}/compare?from=${encode(data.get('from'))}&to=${encode(data.get('to'))}`);
  pageFrame(detailPageHtml(local.detail,local.preview),'Revisión documental');
}
async function submitUpload(form) {
  const caseId=local.detail?.case?.case_id;
  const data=new FormData(form);
  const button=form.querySelector('button[type="submit"]'); button.disabled=true;
  await api(`${BASE}/cases/${encode(caseId)}/upload-revision`,{method:'POST',body:data}); toast('Revisión DOCX registrada y enlazada a la versión anterior.'); return refreshCurrent();
}

document.addEventListener('click',event=>{
  const filter=event.target.closest('[data-m325-filter]');
  if (filter) { local.filter=filter.dataset.m325Filter; if(local.summary) pageFrame(listPageHtml(local.summary),'Bandeja documental'); return; }
  const button=event.target.closest('[data-m325-action]');
  if (!button) return;
  event.preventDefault();
  handleAction(button).catch(error=>{ toast(error.message,'danger'); button.disabled=false; });
});
document.addEventListener('submit',event=>{
  if (event.target.id==='m325-finding-form') { event.preventDefault(); submitFinding(event.target).catch(error=>{toast(error.message,'danger'); event.target.querySelector('button').disabled=false;}); }
  if (event.target.id==='m325-compare-form') { event.preventDefault(); submitComparison(event.target).catch(error=>toast(error.message,'danger')); }
  if (event.target.id==='m325-upload-form') { event.preventDefault(); submitUpload(event.target).catch(error=>{toast(error.message,'danger'); event.target.querySelector('button').disabled=false;}); }
});

let timer=null;
function schedule(force=false) {
  clearTimeout(timer);
  timer=setTimeout(()=>{ ensureNavigation(); if(currentPath().startsWith(ROUTE)) route(force); },90);
}
window.addEventListener('hashchange',()=>schedule(false));
window.addEventListener('DOMContentLoaded',()=>schedule(false));
const observer=new MutationObserver(()=>schedule(false));
observer.observe(app,{childList:true,subtree:true});
schedule(false);
