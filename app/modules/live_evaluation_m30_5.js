'use strict';

import { api, closeDialog, dateText, esc, humanize, openDialog, state, toast } from '../core.js';

const endpoint='/api/m30/live-evaluation';
const labels={go_limited:'GO limitado',extend_pilot:'Extender piloto',no_go:'NO-GO',snapshot:'Evidencia congelada',proposed:'Decisión propuesta',formalized:'Decisión formalizada',rejected:'Requiere nueva propuesta'};
const pct=value=>`${Math.round(Number(value||0)*100)}%`;
const score=value=>Number(value||0).toFixed(2);
const badge=(text,ok=false)=>`<span class="badge ${ok?'green':'yellow'}">${esc(text)}</span>`;

function metricCard(label,value,detail=''){
  return `<article class="m305-metric"><span>${esc(label)}</span><strong>${esc(value)}</strong>${detail?`<small>${esc(detail)}</small>`:''}</article>`;
}
function checksGrid(data){
  return `<div class="m305-check-grid">${Object.entries(data.checks||{}).map(([key,value])=>`<div class="m30-check ${value?'ok':''}"><span>${value?'✓':'○'}</span><b>${esc(humanize(key))}</b></div>`).join('')}</div>`;
}
function comparison(data){
  if(!data.comparison?.available) return '<div class="legal-notice"><b>Sin línea base comparativa.</b> Ejecuta primero una simulación M30.4 para calcular diferencias.</div>';
  return `<div class="m305-comparison"><div class="m305-comparison-head"><b>Simulación M30.4</b><span>${esc(data.comparison.simulation_title||'Línea base')}</span></div>${(data.comparison.rows||[]).map(row=>`<div class="m305-comparison-row"><span>${esc(humanize(row.metric))}</span><b>${esc(row.simulation)}</b><b>${esc(row.live)}</b><em class="${Number(row.delta)>=0?'positive':'negative'}">${Number(row.delta)>=0?'+':''}${esc(row.delta)}</em></div>`).join('')}</div>`;
}
function approvals(evaluation){
  const rows=evaluation?.approvals||[];
  return `<div class="approval-badges">${badge('Propuesta administrativa',Boolean(evaluation?.proposed_decision))}${badge('Revisión jurídica',rows.some(x=>x.approval_type==='legal'&&x.decision==='approved'))}${badge('QA',rows.some(x=>x.approval_type==='qa'&&x.decision==='approved'))}</div>`;
}

export function liveEvaluationSection(data){
  const m=data.live_metrics||{}; const evaluation=data.latest_evaluation;
  return `<section class="card m305-evaluation-card"><div class="card-header"><div><span class="eyebrow">M30.5 · evidencia real</span><h2>Tablero comparativo y decisión go/no-go</h2><p>Compara la cohorte real limitada con la simulación y formaliza una decisión con revisión jurídica y QA separadas.</p></div><img class="m305-visual" src="/assets/brand-visuals/pilot/go-no-go.svg" alt="Tablero de decisión del piloto LegalAIZ.it"></div><div class="m305-metrics">${metricCard('Casos completados',`${m.completed_cases||0}/${m.total_plans||0}`,pct(m.completion_rate))}${metricCard('Participantes aceptados',m.accepted_participants||0,`Consentimiento ${pct(m.consent_coverage)}`)}${metricCard('Claridad',score(m.average_clarity),'Escala de 1 a 5')}${metricCard('Facilidad',score(m.average_ease),'Escala de 1 a 5')}${metricCard('Confianza',score(m.average_confidence),'Escala de 1 a 5')}${metricCard('Productos con evidencia',`${m.product_coverage||0}/4`,`Soporte SLA ${pct(m.support_sla_rate)}`)}</div><div class="m305-columns"><div><div class="card-header compact"><div><span class="eyebrow">Compuertas reales</span><h3>${data.passed_checks||0}/${data.total_checks||0} superadas</h3></div>${badge(labels[data.recommendation]||humanize(data.recommendation),data.recommendation==='go_limited')}</div>${checksGrid(data)}</div><div><div class="card-header compact"><div><span class="eyebrow">Simulación vs. piloto</span><h3>Diferencias observadas</h3></div></div>${comparison(data)}</div></div>${evaluation?`<div class="m305-decision"><div><span class="eyebrow">Última evaluación · ${esc(dateText(evaluation.created_at))}</span><h3>${esc(labels[evaluation.status]||humanize(evaluation.status))}</h3><p>${evaluation.proposal_reason?esc(evaluation.proposal_reason):'La evidencia está congelada y disponible para propuesta formal.'}</p>${approvals(evaluation)}</div><div class="button-group"><a class="btn secondary sm" href="${endpoint}/export" download>Exportar evidencia</a>${state.user?.role==='admin'&&['snapshot','rejected'].includes(evaluation.status)?'<button class="btn primary sm" type="button" data-m305-propose>Proponer decisión</button>':''}${state.user?.role==='specialist'&&evaluation.status==='proposed'?'<button class="btn primary sm" type="button" data-m305-approve="legal">Aprobar revisión jurídica</button>':''}${state.user?.role==='admin'&&evaluation.status==='proposed'?'<button class="btn primary sm" type="button" data-m305-approve="qa">Aprobar QA</button>':''}</div></div>`:`<div class="legal-notice mt-16"><b>No existe una evaluación real congelada.</b> Se requieren al menos cuatro participantes aceptados y cuatro respuestas de experiencia.</div>`}<div class="button-group mt-16">${state.user?.role==='admin'?'<button class="btn secondary" type="button" data-m305-snapshot>Crear evaluación inmutable</button>':''}</div><p class="field-hint mt-12">${esc(data.notice)}</p></section>`;
}

export function bindLiveEvaluation(data,refresh){
  document.querySelector('[data-m305-snapshot]')?.addEventListener('click',()=>confirmDialog('Crear evaluación real','Congela un snapshot inmutable de las señales estructuradas actuales.',data.policy.confirmations.snapshot,`${endpoint}/evaluations`,{},refresh,'Evaluación real creada.'));
  document.querySelector('[data-m305-propose]')?.addEventListener('click',()=>{
    const ev=data.latest_evaluation;
    openDialog({title:'Proponer decisión go/no-go',subtitle:`Recomendación automática: ${labels[ev.recommendation]||humanize(ev.recommendation)}.`,body:`<div class="field"><label for="m305-decision">Decisión propuesta</label><select id="m305-decision" class="select">${data.policy.decisions.map(x=>`<option value="${esc(x)}" ${x===ev.recommendation?'selected':''}>${esc(labels[x]||humanize(x))}</option>`).join('')}</select></div><div class="field"><label for="m305-reason">Fundamento verificable</label><textarea id="m305-reason" class="textarea" maxlength="1200"></textarea></div><div class="field"><label for="m305-confirm">Confirmación</label><input id="m305-confirm" class="input" placeholder="${esc(data.policy.confirmations.proposal)}"></div>`,actions:'<button class="btn secondary" data-action="close-dialog" type="button">Cancelar</button><button class="btn primary" id="m305-save-proposal" type="button">Registrar propuesta</button>'});
    document.getElementById('m305-save-proposal')?.addEventListener('click',()=>post(`${endpoint}/evaluations/${encodeURIComponent(ev.id)}/proposal`,{decision:document.getElementById('m305-decision').value,reason:document.getElementById('m305-reason').value,confirmation:document.getElementById('m305-confirm').value},refresh,'Propuesta registrada.'));
  });
  document.querySelectorAll('[data-m305-approve]').forEach(button=>button.addEventListener('click',()=>{
    const type=button.dataset.m305Approve; const ev=data.latest_evaluation; const phrase=data.policy.confirmations[type==='legal'?'legal_approval':'qa_approval'];
    openDialog({title:type==='legal'?'Aprobación jurídica':'Aprobación QA',subtitle:'La aprobación queda vinculada a la evaluación inmutable.',body:`<div class="field"><label for="m305-comment">Justificación</label><textarea id="m305-comment" class="textarea" maxlength="800"></textarea></div><div class="field"><label for="m305-approval-confirm">Confirmación</label><input id="m305-approval-confirm" class="input" placeholder="${esc(phrase)}"></div>`,actions:'<button class="btn secondary" data-action="close-dialog" type="button">Cancelar</button><button class="btn primary" id="m305-save-approval" type="button">Aprobar</button>'});
    document.getElementById('m305-save-approval')?.addEventListener('click',()=>post(`${endpoint}/evaluations/${encodeURIComponent(ev.id)}/approvals`,{approval_type:type,decision:'approved',comment:document.getElementById('m305-comment').value,confirmation:document.getElementById('m305-approval-confirm').value},refresh,'Aprobación registrada.'));
  }));
}
function confirmDialog(title,subtitle,phrase,url,body,refresh,message){
  openDialog({title,subtitle,body:`<div class="legal-notice"><b>Alcance limitado.</b> Ninguna decisión M30.5 habilita producción pública.</div><div class="field mt-16"><label for="m305-action-confirm">Confirmación</label><input id="m305-action-confirm" class="input" placeholder="${esc(phrase)}"></div>`,actions:'<button class="btn secondary" data-action="close-dialog" type="button">Cancelar</button><button class="btn primary" id="m305-action" type="button">Confirmar</button>'});
  document.getElementById('m305-action')?.addEventListener('click',()=>post(url,{...body,confirmation:document.getElementById('m305-action-confirm').value},refresh,message));
}
async function post(url,body,refresh,message){try{await api(url,{method:'POST',body:JSON.stringify(body)});closeDialog();toast(message);await refresh();}catch(error){toast(error.message,'danger');}}
