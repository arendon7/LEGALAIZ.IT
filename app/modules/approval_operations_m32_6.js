'use strict';

import { api, currentPath, dateText, esc, state, toast } from '../core.js';

const BASE = '/api/m32/approval-operations';
const ROUTE = '/mesa-juridica';
const cache = { portfolio:null, details:new Map(), professionals:null, loading:false };
let timer = null;

const priorityLabel = { critical:'Crítica', high:'Alta', normal:'Normal', low:'Baja' };
const slaLabel = { overdue:'Vencido', at_risk:'En riesgo', in_time:'En término', not_scheduled:'Sin programar', closed:'Cerrado' };
const severityLabel = { critical:'Crítica', high:'Alta', medium:'Media', info:'Informativa' };

function professional(){ return state.user && ['specialist','admin'].includes(state.user.role); }
function encode(value){ return encodeURIComponent(String(value || '')); }
function caseId(){
  const path=currentPath();
  return path.startsWith(`${ROUTE}/`) ? decodeURIComponent(path.slice(ROUTE.length+1).split('/')[0] || '') : '';
}
function fmtDue(value){ return value ? dateText(value) : 'Sin fecha objetivo'; }
function shortHours(value){
  if (value===null || value===undefined) return '—';
  const amount=Math.abs(Number(value));
  const unit=amount>=24 ? `${(amount/24).toFixed(1)} días` : `${amount.toFixed(1)} h`;
  return Number(value)<0 ? `${unit} vencidas` : `${unit} restantes`;
}
function activeAlerts(alerts){ return (alerts||[]).filter(item=>!item.acknowledged); }
function priorityBadge(value){ return `<span class="m326-badge priority-${esc(value||'normal')}">${esc(priorityLabel[value]||value||'Normal')}</span>`; }
function slaBadge(sla){ return `<span class="m326-badge sla-${esc(sla?.status||'not_scheduled')}">${esc(slaLabel[sla?.status]||sla?.status||'Sin SLA')}</span>`; }
function postJson(path,payload){ return api(path,{method:'POST',body:JSON.stringify(payload||{})}); }

function portfolioPanel(data){
  const portfolio=data.portfolio||{}, metrics=data.metrics||{};
  return `<section class="m326-portfolio" data-m326>
    <div class="m326-portfolio-head"><div><span class="eyebrow">M32.6 · Operación del portafolio</span><h2>Cobertura, responsables y SLA</h2><p>${esc(data.notice||'')}</p></div>${state.user?.role==='admin'?'<button class="btn secondary" data-m326-action="sync">Sincronizar portafolio</button>':''}</div>
    <div class="m326-kpis">
      <article><small>Productos cubiertos</small><b>${esc(portfolio.covered_products||0)}/${esc(portfolio.expected_products||11)}</b><span>${esc(portfolio.coverage_percent||0)}% del portafolio</span></article>
      <article><small>Sin asignación completa</small><b>${esc(metrics.unassigned||0)}</b><span>Especialista y QA distintos</span></article>
      <article class="risk"><small>SLA vencidos</small><b>${esc(metrics.overdue||0)}</b><span>Requieren gestión inmediata</span></article>
      <article class="warning"><small>En riesgo</small><b>${esc(metrics.at_risk||0)}</b><span>Próximos al vencimiento</span></article>
      <article><small>Alertas activas</small><b>${esc(metrics.active_alerts||0)}</b><span>No reconocidas</span></article>
    </div>
    ${portfolio.missing?.length?`<div class="m326-missing"><b>Productos aún no registrados:</b><span>${portfolio.missing.map(item=>esc(item.code)).join(' · ')}</span></div>`:'<div class="m326-complete">Los once productos tienen al menos un documento registrado en la Mesa Jurídica.</div>'}
  </section>`;
}

function cardStrip(row){
  const ops=row.operations||{}, sla=row.sla||{}, alerts=activeAlerts(row.alerts);
  const specialist=ops.assigned_specialist?.name||'Sin especialista';
  const qa=ops.assigned_qa?.name||'Sin QA';
  return `<div class="m326-card-strip" data-m326>
    <div>${priorityBadge(ops.priority)}${slaBadge(sla)}</div>
    <span><small>Jurídico</small><b>${esc(specialist)}</b></span>
    <span><small>QA</small><b>${esc(qa)}</b></span>
    <span><small>Objetivo</small><b>${esc(fmtDue(sla.due_at))}</b></span>
    <span class="${alerts.length?'has-alerts':''}"><small>Alertas</small><b>${esc(alerts.length)}</b></span>
  </div>`;
}

function renderPortfolio(data){
  document.querySelectorAll('.m326-portfolio,.m326-card-strip').forEach(node=>node.remove());
  const notice=document.querySelector('.m325-notice');
  if (notice) notice.insertAdjacentHTML('afterend',portfolioPanel(data));
  for (const row of data.cases||[]){
    const links=[...document.querySelectorAll('.m325-case-card a[href]')];
    const link=links.find(item=>item.getAttribute('href')===`#${ROUTE}/${encode(row.desk_case_id)}`);
    const card=link?.closest('.m325-case-card');
    const actions=card?.querySelector('.m325-case-actions');
    if (card && actions) actions.insertAdjacentHTML('beforebegin',cardStrip(row));
  }
}

function optionList(rows,current){
  return (rows||[]).map(row=>`<option value="${esc(row.id)}" ${row.id===current?'selected':''}>${esc(row.name)} · ${esc(row.role)}</option>`).join('');
}
function alertItem(item){
  return `<article class="m326-alert severity-${esc(item.severity)} ${item.acknowledged?'acknowledged':''}">
    <div><span>${esc(severityLabel[item.severity]||item.severity)}</span><b>${esc(item.title)}</b></div><p>${esc(item.description)}</p>
    ${item.acknowledged?`<small>Reconocida por ${esc(item.acknowledgement?.actor?.name||item.acknowledgement?.actor?.id||'usuario')}</small>`:`<button class="btn secondary sm" data-m326-action="ack" data-code="${esc(item.code)}">Reconocer alerta</button>`}
  </article>`;
}
function activityItem(item){
  const actor=item.actor?.name||item.actor?.id||'Sistema';
  return `<li><span class="m326-source ${esc(item.source)}">${item.source==='operations'?'Operación':'Aprobación'}</span><div><b>${esc(item.event_type)}</b><small>${esc(actor)} · ${esc(dateText(item.created_at))}</small></div></li>`;
}

function operationsCard(data,professionals){
  const ops=data.operations||{}, sla=data.sla||{}, caps=data.capabilities||{};
  const alerts=data.alerts||[];
  return `<article class="card m325-card m326-operations-card" data-m326>
    <div class="card-header"><div><span class="eyebrow">M32.6 · Control operativo</span><h2>Responsables y SLA</h2><p>Las metas operativas no sustituyen términos legales aplicables.</p></div>${priorityBadge(ops.priority)}</div>
    <div class="m326-status-row">${slaBadge(sla)}<span>${esc(shortHours(sla.hours_remaining))}</span><span>${esc(fmtDue(sla.due_at))}</span></div>
    <dl class="m326-assignees"><div><dt>Especialista</dt><dd>${esc(ops.assigned_specialist?.name||'Sin asignar')}</dd></div><div><dt>QA</dt><dd>${esc(ops.assigned_qa?.name||'Sin asignar')}</dd></div><div><dt>Cadena operativa</dt><dd>${data.operations_audit?.valid?'Íntegra':'INVÁLIDA'} · ${esc(data.operations_audit?.events||0)} eventos</dd></div></dl>
    ${caps.manage_assignment?`<form class="m326-form" data-m326-form="assignment"><label>Asignación jurídica<select class="select" name="specialist_id" required><option value="">Seleccionar…</option>${optionList(professionals?.specialists,ops.assigned_specialist?.id)}</select></label><label>Responsable QA<select class="select" name="qa_id" required><option value="">Seleccionar…</option>${optionList(professionals?.qa,ops.assigned_qa?.id)}</select></label><button class="btn secondary sm" type="submit">Guardar asignación</button></form>`:''}
    ${caps.manage_priority?`<form class="m326-form compact" data-m326-form="priority"><label>Prioridad<select class="select" name="priority"><option value="critical" ${ops.priority==='critical'?'selected':''}>Crítica · 4 h</option><option value="high" ${ops.priority==='high'?'selected':''}>Alta · 24 h</option><option value="normal" ${ops.priority==='normal'?'selected':''}>Normal · 72 h</option><option value="low" ${ops.priority==='low'?'selected':''}>Baja · 120 h</option></select></label><button class="btn secondary sm" type="submit">Aplicar SLA sugerido</button></form>
    <form class="m326-form compact" data-m326-form="deadline"><label>Fecha objetivo<input class="input" name="due_at" type="datetime-local" required></label><label>Horas de SLA<input class="input" name="sla_hours" type="number" min="1" max="8760" value="${esc(ops.sla_hours||72)}"></label><button class="btn secondary sm" type="submit">Definir vencimiento</button></form>`:''}
    <div class="m326-alerts"><h3>Alertas</h3>${alerts.length?alerts.map(alertItem).join(''):'<p class="m326-muted">No hay alertas operativas activas.</p>'}</div>
    ${caps.add_note?`<form class="m326-note" data-m326-form="note"><label>Nota de seguimiento<textarea class="textarea" name="text" rows="2" maxlength="2000" required></textarea></label><button class="btn secondary sm" type="submit">Registrar nota</button></form>`:''}
    <a class="btn primary btn-block" href="${BASE}/cases/${encode(data.case_id)}/dossier-download">Descargar expediente de aprobación</a>
  </article>`;
}
function activityCard(data){
  const notes=(data.operations?.notes||[]).slice().reverse();
  return `<article class="card m325-card m326-activity-card" data-m326><div class="card-header"><div><span class="eyebrow">Trazabilidad consolidada</span><h2>Actividad operativa</h2><p>Eventos M32.6 y decisiones de la Mesa Jurídica en una sola secuencia.</p></div></div><ol class="m326-timeline">${(data.activity||[]).slice(0,30).map(activityItem).join('')||'<li>Sin actividad registrada.</li>'}</ol>${notes.length?`<div class="m326-notes"><h3>Notas</h3>${notes.map(note=>`<p><b>${esc(note.actor?.name||note.actor?.id)}</b><span>${esc(note.text)}</span><small>${esc(dateText(note.created_at))}</small></p>`).join('')}</div>`:''}</article>`;
}

async function renderDetail(id){
  const data=await api(`${BASE}/cases/${encode(id)}`);
  cache.details.set(id,data);
  let professionals=null;
  if (data.capabilities?.manage_assignment){
    if (!cache.professionals) cache.professionals=await api(`${BASE}/professionals`);
    professionals=cache.professionals;
  }
  document.querySelectorAll('.m326-operations-card,.m326-activity-card').forEach(node=>node.remove());
  const sidebar=document.querySelector('.m325-sidebar');
  if (sidebar) sidebar.insertAdjacentHTML('afterbegin',operationsCard(data,professionals));
  const primary=document.querySelector('.m325-primary');
  if (primary) primary.insertAdjacentHTML('beforeend',activityCard(data));
}
async function renderList(){
  cache.portfolio=await api(BASE);
  renderPortfolio(cache.portfolio);
}
async function refresh(force=false){
  if (!professional() || !currentPath().startsWith(ROUTE) || cache.loading) return;
  cache.loading=true;
  try{
    const id=caseId();
    if (id) await renderDetail(id);
    else if (force || !cache.portfolio) await renderList();
    else renderPortfolio(cache.portfolio);
  }catch(error){ toast(error.message||String(error),'danger'); }
  finally{ cache.loading=false; }
}
function schedule(force=false){
  clearTimeout(timer);
  timer=setTimeout(()=>refresh(force),150);
}
async function handleForm(form){
  const id=caseId();
  if (!id) return;
  const kind=form.dataset.m326Form;
  const data=Object.fromEntries(new FormData(form).entries());
  const button=form.querySelector('button[type="submit"]');
  if (button) button.disabled=true;
  try{
    if (kind==='assignment') await postJson(`${BASE}/cases/${encode(id)}/assignment`,data);
    if (kind==='priority') await postJson(`${BASE}/cases/${encode(id)}/priority`,data);
    if (kind==='deadline'){
      const localDate=new Date(data.due_at);
      if (Number.isNaN(localDate.getTime())) throw new Error('La fecha objetivo no es válida.');
      await postJson(`${BASE}/cases/${encode(id)}/deadline`,{due_at:localDate.toISOString(),sla_hours:Number(data.sla_hours)});
    }
    if (kind==='note') await postJson(`${BASE}/cases/${encode(id)}/notes`,data);
    cache.details.delete(id); cache.portfolio=null; toast('Operación registrada con trazabilidad M32.6.'); await refresh(true);
  }finally{ if (button) button.disabled=false; }
}

document.addEventListener('submit',event=>{
  const form=event.target.closest('[data-m326-form]');
  if (!form) return;
  event.preventDefault();
  handleForm(form).catch(error=>toast(error.message||String(error),'danger'));
});
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-m326-action]');
  if (!button) return;
  event.preventDefault();
  const id=caseId();
  if (button.dataset.m326Action==='sync'){
    if (!window.confirm('Se registrarán en la Mesa Jurídica los DOCX vigentes pendientes. ¿Continuar?')) return;
    button.disabled=true;
    postJson(`${BASE}/portfolio/sync`,{limit:500}).then(()=>{cache.portfolio=null;toast('Portafolio sincronizado.');return refresh(true);}).catch(error=>toast(error.message,'danger')).finally(()=>button.disabled=false);
  }
  if (button.dataset.m326Action==='ack' && id){
    const comment=window.prompt('Comentario de seguimiento para reconocer esta alerta:')||'';
    button.disabled=true;
    postJson(`${BASE}/cases/${encode(id)}/alerts/${encode(button.dataset.code)}/acknowledge`,{comment}).then(()=>{cache.details.delete(id);return refresh(true);}).catch(error=>toast(error.message,'danger')).finally(()=>button.disabled=false);
  }
});
window.addEventListener('hashchange',()=>{cache.portfolio=null;cache.details.clear();schedule(true);});
window.addEventListener('DOMContentLoaded',()=>schedule(true));
new MutationObserver(()=>{
  if (!currentPath().startsWith(ROUTE) || cache.loading) return;
  const id=caseId();
  const missing=id ? !document.querySelector('.m326-operations-card') : !document.querySelector('.m326-portfolio');
  if (missing) schedule(false);
}).observe(document.getElementById('app'),{childList:true,subtree:true});
schedule(true);
