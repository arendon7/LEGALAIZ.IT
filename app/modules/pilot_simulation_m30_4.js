'use strict';

import { api, closeDialog, dateText, esc, humanize, openDialog, state, toast } from '../core.js';

const endpoint='/api/m30/simulation';
const labels={proceed_limited:'Avance limitado',extend:'Extender validación',hold:'Congelar',draft:'Preparada',completed:'Ejecutada',decision_recorded:'Decisión registrada'};
const badge=(value,ok=false)=>`<span class="badge ${ok?'green':value==='hold'?'red':'yellow'}">${esc(labels[value]||humanize(value))}</span>`;
const pct=value=>`${Math.round(Number(value||0)*100)}%`;

function metrics(run){
  const m=run?.metrics||{};
  return `<div class="m304-metrics"><div><span>Completitud</span><b>${pct(m.completion_rate)}</b></div><div><span>Éxito</span><b>${pct(m.success_rate)}</b></div><div><span>Claridad</span><b>${esc(m.average_clarity||0)}/5</b></div><div><span>Facilidad</span><b>${esc(m.average_ease||0)}/5</b></div><div><span>Confianza</span><b>${esc(m.average_confidence||0)}/5</b></div><div><span>Soporte</span><b>${pct(m.support_rate)}</b></div></div>`;
}

export function simulationSection(data){
  const run=data?.latest_run;
  if(!run) return `<section class="card m304-card"><div class="m304-empty"><img src="/assets/brand-visuals/pilot/simulation.svg" alt="Simulación controlada de una cohorte jurídica"><div><span class="eyebrow">M30.4 · validación sintética</span><h2>Ensaya una cohorte completa sin usar datos reales</h2><p>Genera 20 recorridos sintéticos para probar métricas, compuertas y decisiones antes de incorporar participantes.</p>${state.user?.role==='admin'?'<button class="btn primary" type="button" data-m304-create>Crear simulación</button>':'<span class="badge yellow">Requiere administración</span>'}</div></div></section>`;
  const checks=Object.entries(run.checks||{});
  return `<section class="card m304-card"><div class="card-header"><div><span class="eyebrow">M30.4 · cohorte sintética</span><h2>${esc(run.title)}</h2><p>Perfil ${esc(humanize(run.profile))} · ${esc(run.case_count)} casos sin usuarios ni expedientes reales.</p></div><div class="approval-badges">${badge(run.status,run.status!=='draft')}${run.recommendation?badge(run.recommendation,run.recommendation==='proceed_limited'):''}<a class="btn secondary sm" href="/api/m30/simulation/export" download>Exportar evidencia</a></div></div>${run.status==='draft'?'<div class="legal-notice"><b>Lista para ejecutar.</b> La ejecución solo crea métricas sintéticas y no modifica la cohorte real.</div>':`${metrics(run)}<div class="m304-checks">${checks.map(([key,value])=>`<div class="m30-check ${value?'ok':''}"><span>${value?'✓':'○'}</span><b>${esc(humanize(key))}</b></div>`).join('')}</div>`}<div class="button-group mt-16">${state.user?.role==='admin'&&run.status==='draft'?'<button class="btn primary" type="button" data-m304-execute>Ejecutar 20 casos</button>':''}${state.user?.role==='admin'&&run.status==='completed'?'<button class="btn primary" type="button" data-m304-decision>Documentar decisión</button>':''}</div>${run.decision?`<div class="legal-notice mt-16"><b>Decisión documentada: ${esc(labels[run.decision]||run.decision)}.</b> ${esc(run.decision_reason)}<br><small>${esc(dateText(run.decided_at))}. No autoriza producción pública.</small></div>`:''}</section>`;
}

export function bindSimulation(data,refresh){
  const run=data?.latest_run;
  document.querySelector('[data-m304-create]')?.addEventListener('click',()=>{
    const profiles=data.policy.profiles||{};
    openDialog({title:'Crear simulación sintética',subtitle:'No crea usuarios, expedientes ni documentos reales.',body:`<div class="field"><label for="m304-title">Nombre</label><input id="m304-title" class="input" value="Cohorte sintética M30.4"></div><div class="field"><label for="m304-profile">Perfil</label><select id="m304-profile" class="select">${Object.entries(profiles).map(([key,row])=>`<option value="${esc(key)}">${esc(row.label)}</option>`).join('')}</select></div><div class="field"><label for="m304-confirm">Confirmación</label><input id="m304-confirm" class="input" placeholder="${esc(data.policy.confirmations.create)}"></div>`,actions:'<button class="btn secondary" data-action="close-dialog" type="button">Cancelar</button><button class="btn primary" id="m304-save" type="button">Crear</button>'});
    document.getElementById('m304-save')?.addEventListener('click',()=>post(`${endpoint}/runs`,{title:document.getElementById('m304-title').value,profile:document.getElementById('m304-profile').value,confirmation:document.getElementById('m304-confirm').value},refresh,'Simulación preparada.'));
  });
  document.querySelector('[data-m304-execute]')?.addEventListener('click',()=>confirmAction('Ejecutar cohorte sintética','Se crearán exactamente 20 señales estructuradas.',data.policy.confirmations.execute,`${endpoint}/runs/${encodeURIComponent(run.id)}/execute`,{},refresh,'Simulación ejecutada.'));
  document.querySelector('[data-m304-decision]')?.addEventListener('click',()=>{
    openDialog({title:'Documentar decisión simulada',subtitle:`Recomendación automática: ${labels[run.recommendation]||run.recommendation}.`,body:`<div class="field"><label for="m304-decision-value">Decisión</label><select id="m304-decision-value" class="select">${data.policy.decisions.map(x=>`<option value="${esc(x)}" ${x===run.recommendation?'selected':''}>${esc(labels[x]||humanize(x))}</option>`).join('')}</select></div><div class="field"><label for="m304-reason">Fundamento verificable</label><textarea id="m304-reason" class="textarea" maxlength="1000"></textarea></div><div class="field"><label for="m304-decision-confirm">Confirmación</label><input id="m304-decision-confirm" class="input" placeholder="${esc(data.policy.confirmations.decision)}"></div>`,actions:'<button class="btn secondary" data-action="close-dialog" type="button">Cancelar</button><button class="btn primary" id="m304-save-decision" type="button">Registrar</button>'});
    document.getElementById('m304-save-decision')?.addEventListener('click',()=>post(`${endpoint}/runs/${encodeURIComponent(run.id)}/decision`,{decision:document.getElementById('m304-decision-value').value,reason:document.getElementById('m304-reason').value,confirmation:document.getElementById('m304-decision-confirm').value},refresh,'Decisión simulada registrada.'));
  });
}

function confirmAction(title,subtitle,phrase,url,body,refresh,message){
  openDialog({title,subtitle,body:`<div class="legal-notice"><b>Datos sintéticos únicamente.</b> Esta acción no altera participantes ni expedientes.</div><div class="field mt-16"><label for="m304-action-confirm">Confirmación</label><input id="m304-action-confirm" class="input" placeholder="${esc(phrase)}"></div>`,actions:'<button class="btn secondary" data-action="close-dialog" type="button">Cancelar</button><button class="btn primary" id="m304-action" type="button">Confirmar</button>'});
  document.getElementById('m304-action')?.addEventListener('click',()=>post(url,{...body,confirmation:document.getElementById('m304-action-confirm').value},refresh,message));
}
async function post(url,body,refresh,message){try{await api(url,{method:'POST',body:JSON.stringify(body)});closeDialog();toast(message);await refresh();}catch(error){toast(error.message,'danger');}}
