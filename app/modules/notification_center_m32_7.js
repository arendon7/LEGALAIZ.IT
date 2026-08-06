'use strict';

import { api, currentPath, dateText, esc, state, toast } from '../core.js';

const BASE='/api/m32/notification-center';
const ROUTE='/mesa-juridica';
const cache={dashboard:null,caseData:new Map(),loading:false};
let timer=null;

const severityLabel={critical:'Crítica',high:'Alta',medium:'Media',info:'Informativa'};
const loadLabel={critical:'Crítica',high:'Alta',balanced:'Equilibrada',available:'Disponible'};

function professional(){return state.user&&['specialist','admin','qa'].includes(state.user.role);}
function encode(value){return encodeURIComponent(String(value||''));}
function caseId(){const path=currentPath();return path.startsWith(`${ROUTE}/`)?decodeURIComponent(path.slice(ROUTE.length+1).split('/')[0]||''):'';}
function post(path,payload){return api(path,{method:'POST',body:JSON.stringify(payload||{})});}
function fmt(value){return value?dateText(value):'Sin fecha';}
function active(item){return !item.acknowledged&&!item.snoozed;}

function inboxItem(item,detail=false){
  const canManage=item.can_manage!==false;
  return `<article class="m327-notification severity-${esc(item.severity||'info')} ${item.read?'is-read':''} ${item.acknowledged?'is-ack':''}">
    <div class="m327-notification-head"><span>${esc(severityLabel[item.severity]||item.severity)}</span><small>${esc(fmt(item.created_at))}</small></div>
    <h4>${esc(item.title||'Notificación')}</h4>
    <p>${esc(item.description||'')}</p>
    <div class="m327-meta"><code>${esc(item.product_code||'')}</code><span>Nivel ${esc(item.escalation_level??0)}</span>${item.due_at?`<span>Objetivo: ${esc(fmt(item.due_at))}</span>`:''}</div>
    <div class="m327-actions">
      ${canManage&&!item.read?`<button class="btn secondary sm" data-m327-action="read" data-id="${esc(item.notification_id)}">Marcar leída</button>`:''}
      ${canManage&&!item.acknowledged?`<button class="btn secondary sm" data-m327-action="ack" data-id="${esc(item.notification_id)}">Reconocer</button>`:''}
      ${canManage&&!item.acknowledged?`<button class="btn ghost sm" data-m327-action="snooze" data-id="${esc(item.notification_id)}">Aplazar</button>`:''}
      ${detail&&item.case_id?`<a class="btn ghost sm" href="#${ROUTE}/${encode(item.case_id)}">Abrir expediente</a>`:''}
    </div>
  </article>`;
}

function workloadTable(data){
  const rows=data?.professionals||[];
  if(!rows.length)return '<p class="m327-muted">No hay responsables dentro del alcance actual.</p>';
  return `<div class="m327-table-wrap"><table class="m327-table"><thead><tr><th>Profesional</th><th>Jurídico</th><th>QA</th><th>Vencidos</th><th>En riesgo</th><th>Alertas</th><th>Carga</th></tr></thead><tbody>${rows.map(row=>`<tr><td><b>${esc(row.professional?.name||row.professional?.id)}</b><small>${esc(row.professional?.role||'')}</small></td><td>${esc(row.legal_assignments)}</td><td>${esc(row.qa_assignments)}</td><td>${esc(row.overdue)}</td><td>${esc(row.at_risk)}</td><td>${esc(row.active_alerts)}</td><td><span class="m327-load ${esc(row.load_band)}">${esc(loadLabel[row.load_band]||row.load_band)} · ${esc(row.load_score)}</span></td></tr>`).join('')}</tbody></table></div>`;
}

function calendarForm(calendar){
  const cfg=calendar?.calendar||{};
  const holidays=(cfg.holidays||[]).join(', ');
  return `<form class="m327-calendar-form" data-m327-form="calendar">
    <div><label>Nombre<input class="input" name="name" value="${esc(cfg.name||'Calendario operativo Colombia')}" required></label><label>Días hábiles<input class="input" name="weekdays" value="${esc((cfg.weekdays||[0,1,2,3,4]).join(','))}" aria-describedby="m327-weekdays"></label><small id="m327-weekdays">0=lunes · 6=domingo</small></div>
    <div><label>Apertura<input class="input" type="time" name="open_time" value="${esc(cfg.open_time||'08:00')}" required></label><label>Cierre<input class="input" type="time" name="close_time" value="${esc(cfg.close_time||'17:00')}" required></label></div>
    <label>Cierres explícitos<textarea class="textarea" rows="2" name="holidays" placeholder="2026-08-07, 2026-12-25">${esc(holidays)}</textarea></label>
    <button class="btn secondary sm" type="submit">Guardar calendario operativo</button>
  </form>`;
}

function policyForm(policy){
  const cfg=policy?.policy||{};
  return `<form class="m327-policy-form" data-m327-form="policy">
    <label class="m327-check"><input type="checkbox" name="external_email_enabled" ${cfg.external_email_enabled?'checked':''}> Encolar correo para alertas graves</label>
    <label>Severidad mínima<select class="select" name="external_min_severity"><option value="high" ${cfg.external_min_severity==='high'?'selected':''}>Alta</option><option value="critical" ${cfg.external_min_severity==='critical'?'selected':''}>Crítica</option></select></label>
    <label>Repetir críticas cada<input class="input" type="number" name="repeat_critical_hours" min="0" max="168" value="${esc(cfg.repeat_critical_hours??24)}"><span>horas</span></label>
    <button class="btn secondary sm" type="submit">Guardar política</button>
  </form>`;
}

function dashboardPanel(data){
  const inbox=data.inbox||{}, metrics=inbox.metrics||{}, outbox=data.outbox?.metrics||{};
  const admin=data.capabilities?.evaluate;
  const notifications=(inbox.notifications||[]).filter(active).slice(0,6);
  return `<section class="m327-center" data-m327>
    <div class="m327-hero"><div><span class="eyebrow">M32.7 · Centro operativo</span><h2>Notificaciones, escalamiento y carga</h2><p>${esc(data.notice||'')}</p></div>${admin?'<button class="btn primary" data-m327-action="evaluate">Evaluar y escalar</button>':''}</div>
    <div class="m327-kpis"><article><small>No leídas</small><b>${esc(metrics.unread||0)}</b><span>Bandeja personal</span></article><article class="danger"><small>Críticas activas</small><b>${esc(metrics.critical||0)}</b><span>Requieren atención</span></article><article><small>Aplazadas</small><b>${esc(metrics.snoozed||0)}</b><span>Sin resolver causa</span></article>${admin?`<article class="warning"><small>Correos en cola</small><b>${esc(outbox.queued||0)}</b><span>Entrega real deshabilitada</span></article>`:''}<article><small>Cadena M32.7</small><b>${data.audit?.valid?'Íntegra':'INVÁLIDA'}</b><span>${esc(data.audit?.events||0)} eventos</span></article></div>
    <div class="m327-grid">
      <article class="card m327-inbox"><div class="card-header"><div><h3>Mi bandeja</h3><p>Reconocer una notificación no resuelve automáticamente la alerta de origen.</p></div></div>${notifications.length?notifications.map(item=>inboxItem(item,true)).join(''):'<p class="m327-empty">No hay notificaciones activas para esta bandeja.</p>'}</article>
      <article class="card m327-workload"><div class="card-header"><div><h3>Carga de trabajo</h3><p>${esc(data.workload?.notice||'')}</p></div></div>${workloadTable(data.workload)}</article>
    </div>
    ${admin?`<details class="m327-admin"><summary>Configuración administrativa</summary><div class="m327-admin-grid"><article><h3>Calendario hábil</h3><p>${esc(data.calendar?.notice||'')}</p>${calendarForm(data.calendar)}</article><article><h3>Política de salida</h3><p>${esc(data.policy?.notice||'')}</p>${policyForm(data.policy)}<div class="m327-outbox"><b>Estado:</b> cola interna, sin proveedor ni constancia de entrega.</div></article></div></details>`:''}
  </section>`;
}

function casePanel(data){
  const business=data.business_sla;
  const notifications=(data.notifications||[]).slice(0,8);
  return `<article class="card m325-card m327-case" data-m327>
    <div class="card-header"><div><span class="eyebrow">M32.7 · Seguimiento</span><h2>Notificaciones del expediente</h2><p>La agenda hábil es operativa y requiere validación si se relaciona con un término legal.</p></div></div>
    ${business?`<div class="m327-business status-${esc(business.status)}"><b>${esc(business.status==='overdue'?'Vencido':business.status==='at_risk'?'En riesgo':'En término')}</b><span>${esc(business.business_hours_remaining)} horas hábiles restantes</span><small>Objetivo ${esc(fmt(business.due_at))}</small></div>`:'<div class="m327-business"><b>Sin agenda hábil M32.7</b><span>El SLA M32.6 puede seguir activo en tiempo continuo.</span></div>'}
    ${state.user?.role==='admin'?`<form class="m327-schedule" data-m327-form="schedule"><label>Horas hábiles<input class="input" type="number" min="1" max="8760" step="0.5" name="business_hours" value="24" required></label><label>Inicio opcional<input class="input" type="datetime-local" name="start_at"></label><button class="btn secondary sm" type="submit">Aplicar calendario</button></form>`:''}
    <div class="m327-case-notifications">${notifications.length?notifications.map(item=>inboxItem(item,false)).join(''):'<p class="m327-empty">No existen notificaciones M32.7 para este expediente.</p>'}</div>
  </article>`;
}

async function renderList(){
  const data=await api(BASE);cache.dashboard=data;
  document.querySelectorAll('.m327-center').forEach(node=>node.remove());
  const anchor=document.querySelector('.m326-portfolio')||document.querySelector('.m325-notice');
  if(anchor)anchor.insertAdjacentHTML('afterend',dashboardPanel(data));
}
async function renderCase(id){
  const data=await api(`${BASE}/cases/${encode(id)}`);cache.caseData.set(id,data);
  document.querySelectorAll('.m327-case').forEach(node=>node.remove());
  const sidebar=document.querySelector('.m325-sidebar');
  if(sidebar)sidebar.insertAdjacentHTML('afterbegin',casePanel(data));
}
async function refresh(force=false){
  if(!professional()||!currentPath().startsWith(ROUTE)||cache.loading)return;
  cache.loading=true;
  try{const id=caseId();if(id)await renderCase(id);else if(force||!cache.dashboard)await renderList();else{document.querySelectorAll('.m327-center').forEach(node=>node.remove());const anchor=document.querySelector('.m326-portfolio')||document.querySelector('.m325-notice');if(anchor)anchor.insertAdjacentHTML('afterend',dashboardPanel(cache.dashboard));}}
  catch(error){toast(error.message||String(error),'danger');}
  finally{cache.loading=false;}
}
function schedule(force=false){clearTimeout(timer);timer=setTimeout(()=>refresh(force),180);}

async function handleForm(form){
  const kind=form.dataset.m327Form,data=Object.fromEntries(new FormData(form).entries());
  const button=form.querySelector('button[type="submit"]');if(button)button.disabled=true;
  try{
    if(kind==='calendar'){
      const weekdays=String(data.weekdays||'').split(',').map(value=>Number(value.trim())).filter(value=>Number.isInteger(value));
      const holidays=String(data.holidays||'').split(',').map(value=>value.trim()).filter(Boolean);
      await post(`${BASE}/calendar`,{name:data.name,weekdays,open_time:data.open_time,close_time:data.close_time,holidays});
    }
    if(kind==='policy')await post(`${BASE}/policy`,{external_email_enabled:form.querySelector('[name="external_email_enabled"]').checked,external_min_severity:data.external_min_severity,repeat_critical_hours:Number(data.repeat_critical_hours)});
    if(kind==='schedule'){
      const id=caseId();if(!id)throw new Error('No hay expediente seleccionado.');
      let start_at=null;if(data.start_at){const parsed=new Date(data.start_at);if(Number.isNaN(parsed.getTime()))throw new Error('La fecha de inicio no es válida.');start_at=parsed.toISOString();}
      await post(`${BASE}/cases/${encode(id)}/schedule`,{business_hours:Number(data.business_hours),start_at});
    }
    cache.dashboard=null;cache.caseData.clear();toast('Configuración M32.7 registrada con trazabilidad.');await refresh(true);
  }finally{if(button)button.disabled=false;}
}

document.addEventListener('submit',event=>{const form=event.target.closest('[data-m327-form]');if(!form)return;event.preventDefault();handleForm(form).catch(error=>toast(error.message||String(error),'danger'));});
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-m327-action]');if(!button)return;event.preventDefault();
  const action=button.dataset.m327Action,id=button.dataset.id;button.disabled=true;
  let task;
  if(action==='evaluate')task=post(`${BASE}/evaluate`,{case_id:caseId()||null});
  if(action==='read')task=post(`${BASE}/notifications/${encode(id)}/read`,{});
  if(action==='ack'){const comment=window.prompt('Comentario de reconocimiento:')||'';task=post(`${BASE}/notifications/${encode(id)}/acknowledge`,{comment});}
  if(action==='snooze'){const hours=Number(window.prompt('¿Cuántas horas desea aplazarla?','24')||0);if(!hours||hours<1||hours>720){button.disabled=false;return toast('El aplazamiento debe estar entre 1 y 720 horas.','danger');}task=post(`${BASE}/notifications/${encode(id)}/snooze`,{until:new Date(Date.now()+hours*3600000).toISOString()});}
  if(!task){button.disabled=false;return;}
  task.then(result=>{cache.dashboard=null;cache.caseData.clear();toast(action==='evaluate'?`Evaluación completada: ${result.created_notifications?.length||0} notificaciones nuevas.`:'Bandeja actualizada.');return refresh(true);}).catch(error=>toast(error.message||String(error),'danger')).finally(()=>button.disabled=false);
});
window.addEventListener('hashchange',()=>{cache.dashboard=null;cache.caseData.clear();schedule(true);});
window.addEventListener('DOMContentLoaded',()=>schedule(true));
new MutationObserver(()=>{if(!currentPath().startsWith(ROUTE)||cache.loading)return;const id=caseId();const missing=id?!document.querySelector('.m327-case'):!document.querySelector('.m327-center');if(missing)schedule(false);}).observe(document.getElementById('app'),{childList:true,subtree:true});
schedule(true);
