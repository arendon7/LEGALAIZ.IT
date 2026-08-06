'use strict';

import { api, currentPath, dateText, esc, state, toast } from '../core.js';

const BASE='/api/m32/communications';
const ROUTE='/mesa-juridica';
const cache={dashboard:null,caseData:new Map(),loading:false};
let timer=null;

const statusLabel={
  queued:'En cola',processing:'Procesando',retry_scheduled:'Reintento programado',
  accepted_sandbox:'Aceptado sandbox',delivered_sandbox:'Entregado sintético',
  bounced_sandbox:'Rebote sintético',rejected_sandbox:'Rechazado sintético',
  complained_sandbox:'Queja sintética',cancelled:'Cancelado',dead_letter:'Cola muerta'
};

function professional(){return state.user&&['specialist','admin','qa'].includes(state.user.role);}
function encode(value){return encodeURIComponent(String(value||''));}
function caseId(){const path=currentPath();return path.startsWith(`${ROUTE}/`)?decodeURIComponent(path.slice(ROUTE.length+1).split('/')[0]||''):'';}
function post(path,payload){return api(path,{method:'POST',body:JSON.stringify(payload||{})});}
function fmt(value){return value?dateText(value):'Sin fecha';}

function dispatchItem(item,detail=false){
  const terminal=['delivered_sandbox','bounced_sandbox','rejected_sandbox','complained_sandbox','cancelled','dead_letter'].includes(item.status);
  const admin=state.user?.role==='admin';
  const canReceipt=['admin','qa'].includes(state.user?.role)&&['accepted_sandbox','retry_scheduled','delivered_sandbox','bounced_sandbox'].includes(item.status);
  return `<article class="m328-dispatch status-${esc(item.status||'queued')}">
    <div class="m328-dispatch-head"><span>${esc(statusLabel[item.status]||item.status)}</span><small>${esc(fmt(item.imported_at))}</small></div>
    <h4>${esc(item.context?.title||'Comunicación transaccional')}</h4>
    <p><code>${esc(item.context?.product_code||'')}</code> · ${esc(item.context?.case_id||'Sin expediente')}</p>
    <div class="m328-meta"><span>Intentos: ${esc(item.attempts||0)}</span><span>${esc(item.recipient_hint||'Destino protegido')}</span><span>Plantilla v${esc(item.template_version||1)}</span></div>
    <div class="m328-actions">
      ${detail&&item.context?.case_id?`<a class="btn ghost sm" href="#${ROUTE}/${encode(item.context.case_id)}">Abrir expediente</a>`:''}
      ${canReceipt?`<button class="btn secondary sm" data-m328-action="receipt" data-id="${esc(item.dispatch_id)}">Registrar recibo sintético</button>`:''}
      ${admin&&!terminal?`<button class="btn ghost sm" data-m328-action="cancel" data-id="${esc(item.dispatch_id)}">Cancelar</button>`:''}
    </div>
  </article>`;
}

function policyForm(policy){
  const cfg=policy?.policy||{};
  return `<form class="m328-policy" data-m328-form="policy">
    <label class="m328-check"><input type="checkbox" name="sandbox_enabled" ${cfg.sandbox_enabled?'checked':''}> Procesamiento sandbox habilitado</label>
    <label>Máximo de intentos<input class="input" type="number" name="max_attempts" min="1" max="10" value="${esc(cfg.max_attempts??3)}"></label>
    <label>Backoff inicial (segundos)<input class="input" type="number" name="initial_backoff_seconds" min="5" max="86400" value="${esc(cfg.initial_backoff_seconds??60)}"></label>
    <label>Backoff máximo (segundos)<input class="input" type="number" name="max_backoff_seconds" min="5" max="604800" value="${esc(cfg.max_backoff_seconds??3600)}"></label>
    <label>Tamaño de lote<input class="input" type="number" name="batch_size" min="1" max="200" value="${esc(cfg.batch_size??25)}"></label>
    <button class="btn secondary sm" type="submit">Guardar política M32.8</button>
  </form>`;
}

function templateForm(){
  return `<form class="m328-template-form" data-m328-form="template">
    <label>Nombre<input class="input" name="name" value="Alerta profesional protegida" required></label>
    <label>Asunto<input class="input" name="subject" value="LegalAIZ.it · {{title}}" required></label>
    <label>Cuerpo<textarea class="textarea" name="body" rows="7" required>Hola {{recipient_name}}.\n\nExiste una actuación pendiente para el producto {{product_code}} en el expediente {{case_id}}. Fecha objetivo: {{due_at}}.\n\nIngrese a la Mesa Jurídica de LegalAIZ.it para consultar el detalle protegido.</textarea></label>
    <button class="btn secondary sm" type="submit">Crear nueva versión</button>
  </form>`;
}

function templateRows(data){
  const rows=data?.templates||[];
  if(!rows.length)return '<p class="m328-muted">No existen plantillas registradas.</p>';
  return `<div class="m328-template-list">${rows.map(item=>`<article><div><b>${esc(item.name)}</b><small>${esc(item.template_id)} · v${esc(item.version)} · ${item.active?'Activa':'Borrador'}</small></div><code>${esc(String(item.template_sha256||'').slice(0,12))}</code>${item.can_activate?`<button class="btn ghost sm" data-m328-action="activate" data-template="${esc(item.template_id)}" data-version="${esc(item.version)}">Activar</button>`:''}</article>`).join('')}</div>`;
}

function dashboardPanel(data){
  const queue=data.queue||{}, metrics=queue.metrics||{}, rows=(queue.dispatches||[]).slice(0,8);
  const admin=data.capabilities?.process;
  return `<section class="m328-center" data-m328>
    <div class="m328-hero"><div><span class="eyebrow">M32.8 · Comunicaciones transaccionales</span><h2>Plantillas, despachos y evidencia</h2><p>${esc(data.notice||'')}</p></div>${admin?'<div class="m328-hero-actions"><button class="btn secondary" data-m328-action="sync">Sincronizar cola M32.7</button><button class="btn primary" data-m328-action="process">Procesar sandbox</button></div>':''}</div>
    <div class="m328-kpis"><article><small>En cola</small><b>${esc(metrics.queued||0)}</b><span>Pendientes</span></article><article><small>Aceptados</small><b>${esc(metrics.accepted_sandbox||0)}</b><span>Solo sandbox</span></article><article><small>Entregados</small><b>${esc(metrics.delivered_sandbox||0)}</b><span>Evidencia sintética</span></article><article class="warning"><small>Rebotes</small><b>${esc(metrics.bounced_sandbox||0)}</b><span>Sintéticos</span></article><article><small>Cadena M32.8</small><b>${data.audit?.valid?'Íntegra':'INVÁLIDA'}</b><span>${esc(data.audit?.events||0)} eventos</span></article></div>
    <div class="m328-grid"><article class="card"><div class="card-header"><div><h3>Cola de despacho</h3><p>No se conserva la dirección completa ni contenido documental.</p></div></div>${rows.length?rows.map(item=>dispatchItem(item,true)).join(''):'<p class="m328-empty">Aún no hay despachos M32.8.</p>'}</article><article class="card"><div class="card-header"><div><h3>Plantillas versionadas</h3><p>${esc(data.templates?.notice||'')}</p></div></div>${templateRows(data.templates)}</article></div>
    ${admin?`<details class="m328-admin"><summary>Configuración administrativa</summary><div class="m328-admin-grid"><article><h3>Política de reintentos</h3>${policyForm(data.policy)}</article><article><h3>Nueva versión de plantilla</h3><p>La activación requiere una persona distinta de quien la creó.</p>${templateForm()}</article></div></details>`:''}
  </section>`;
}

function casePanel(data){
  const rows=(data.communications||[]).slice(0,8);
  return `<article class="card m325-card m328-case" data-m328><div class="card-header"><div><span class="eyebrow">M32.8 · Evidencia de comunicación</span><h2>Despachos del expediente</h2><p>Los estados corresponden al entorno sandbox y no acreditan entrega externa real.</p></div></div>${rows.length?rows.map(item=>dispatchItem(item,false)).join(''):'<p class="m328-empty">No existen comunicaciones M32.8 para este expediente.</p>'}</article>`;
}

async function renderList(){
  const data=await api(BASE);cache.dashboard=data;
  document.querySelectorAll('.m328-center').forEach(node=>node.remove());
  const anchor=document.querySelector('.m327-center')||document.querySelector('.m326-portfolio');
  if(anchor)anchor.insertAdjacentHTML('afterend',dashboardPanel(data));
}
async function renderCase(id){
  const data=await api(`${BASE}/cases/${encode(id)}`);cache.caseData.set(id,data);
  document.querySelectorAll('.m328-case').forEach(node=>node.remove());
  const sidebar=document.querySelector('.m325-sidebar');
  if(sidebar)sidebar.insertAdjacentHTML('afterbegin',casePanel(data));
}
async function refresh(force=false){
  if(!professional()||!currentPath().startsWith(ROUTE)||cache.loading)return;
  cache.loading=true;
  try{const id=caseId();if(id)await renderCase(id);else if(force||!cache.dashboard)await renderList();else{document.querySelectorAll('.m328-center').forEach(node=>node.remove());const anchor=document.querySelector('.m327-center')||document.querySelector('.m326-portfolio');if(anchor)anchor.insertAdjacentHTML('afterend',dashboardPanel(cache.dashboard));}}
  catch(error){toast(error.message||String(error),'danger');}
  finally{cache.loading=false;}
}
function schedule(force=false){clearTimeout(timer);timer=setTimeout(()=>refresh(force),200);}

async function handleForm(form){
  const kind=form.dataset.m328Form,data=Object.fromEntries(new FormData(form).entries());
  const button=form.querySelector('button[type="submit"]');if(button)button.disabled=true;
  try{
    if(kind==='policy')await post(`${BASE}/policy`,{sandbox_enabled:form.querySelector('[name="sandbox_enabled"]').checked,max_attempts:Number(data.max_attempts),initial_backoff_seconds:Number(data.initial_backoff_seconds),max_backoff_seconds:Number(data.max_backoff_seconds),batch_size:Number(data.batch_size)});
    if(kind==='template')await post(`${BASE}/templates`,{template_id:'professional-alert',name:data.name,subject:data.subject,body:data.body});
    cache.dashboard=null;cache.caseData.clear();toast('Actuación M32.8 registrada con trazabilidad.');await refresh(true);
  }finally{if(button)button.disabled=false;}
}

document.addEventListener('submit',event=>{const form=event.target.closest('[data-m328-form]');if(!form)return;event.preventDefault();handleForm(form).catch(error=>toast(error.message||String(error),'danger'));});
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-m328-action]');if(!button)return;event.preventDefault();
  const action=button.dataset.m328Action;button.disabled=true;let task;
  if(action==='sync')task=post(`${BASE}/sync`,{});
  if(action==='process')task=post(`${BASE}/process`,{});
  if(action==='cancel'){const reason=window.prompt('Motivo de cancelación:','Cancelación administrativa')||'';task=post(`${BASE}/dispatches/${encode(button.dataset.id)}/cancel`,{reason});}
  if(action==='receipt'){
    const provider_status=window.prompt('Estado sintético: delivered, bounced, rejected, complained o deferred','delivered')||'';
    const allowed=['delivered','bounced','rejected','complained','deferred'];if(!allowed.includes(provider_status)){button.disabled=false;return toast('Estado sintético no válido.','danger');}
    task=post(`${BASE}/dispatches/${encode(button.dataset.id)}/receipt`,{provider_status,provider_event_id:`UI-${Date.now()}`,synthetic:true});
  }
  if(action==='activate')task=post(`${BASE}/templates/${encode(button.dataset.template)}/${encode(button.dataset.version)}/activate`,{});
  if(!task){button.disabled=false;return;}
  task.then(result=>{cache.dashboard=null;cache.caseData.clear();const amount=result.imported_dispatches?.length??result.accepted_sandbox?.length;toast(amount!==undefined?`Operación completada: ${amount} registros.`:'Comunicaciones actualizadas.');return refresh(true);}).catch(error=>toast(error.message||String(error),'danger')).finally(()=>button.disabled=false);
});
window.addEventListener('hashchange',()=>{cache.dashboard=null;cache.caseData.clear();schedule(true);});
window.addEventListener('DOMContentLoaded',()=>schedule(true));
new MutationObserver(()=>{if(!currentPath().startsWith(ROUTE)||cache.loading)return;const id=caseId();const missing=id?!document.querySelector('.m328-case'):!document.querySelector('.m328-center');if(missing)schedule(false);}).observe(document.getElementById('app'),{childList:true,subtree:true});
schedule(true);
