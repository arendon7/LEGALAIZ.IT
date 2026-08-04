'use strict';

import { api, app, closeDialog, dateText, esc, humanize, openDialog, state, toast } from '../core.js';
import { bindParticipantProfessional, participantProfessionalSection } from './participant_m30_2.js';
import { bindGovernanceProfessional, governanceProfessionalSection } from './pilot_governance_m30_3.js';
import { bindSimulation, simulationSection } from './pilot_simulation_m30_4.js';
import { bindLiveEvaluation, liveEvaluationSection } from './live_evaluation_m30_5.js';

const endpoint = '/api/m30/pilot-center';
const productNames = {
  'CO-LA-002': 'Contrato laboral',
  'CO-EM-003': 'Prestación de servicios',
  'CO-AR-001': 'Arrendamiento de vivienda',
  'CO-CD-003': 'Protección al consumidor',
};
const statusLabels = {
  planned:'Planificado', recruited:'Participante vinculado', in_progress:'En ejecución', completed:'Completado', blocked:'Bloqueado', cancelled:'Cancelado',
  open:'Abierto', assigned:'Asignado', resolved:'Resuelto', closed:'Cerrado',
};
const priorityLabels = { low:'Baja', medium:'Media', high:'Alta', critical:'Crítica' };
const checkLabels = {
  planning_ready:'Base técnica y jurídica preparada', cohort_created:'Cohorte de 20 cupos creada', all_roles_assigned:'Responsables asignados',
  pilot_control_active:'Piloto operativo activado', no_high_or_critical_incidents:'Sin incidentes graves abiertos', no_high_or_critical_support:'Sin soporte grave abierto',
  completed_cases:'20 casos entregados', feedback_volume:'Retroalimentación suficiente', clarity:'Claridad mínima alcanzada', ease:'Facilidad mínima alcanzada',
  confidence:'Confianza mínima alcanzada', goal_met:'Objetivo cumplido', manual_validations:'Validación manual completa',
};
const badge = (value, positive = ['completed','resolved','closed','passed','active'].includes(value)) => `<span class="badge ${positive ? 'green' : ['blocked','critical','high'].includes(value) ? 'red' : 'yellow'}">${esc(statusLabels[value] || priorityLabels[value] || humanize(value))}</span>`;
const option = (value, label, selected = false) => `<option value="${esc(value)}"${selected ? ' selected' : ''}>${esc(label)}</option>`;
const professionalOptions = (rows, selected = '') => `<option value="">Seleccionar…</option>${rows.map(row => option(row.id, `${row.name} · ${row.role === 'admin' ? 'QA/Administración' : row.specialty || 'Especialista'}`, row.id === selected)).join('')}`;
const productVisual = code => `/assets/brand-visuals/pilot/${code.toLowerCase().replaceAll('-','_')}.svg`;

function gateCard(title, gate, tone = 'launch') {
  const checks = Object.entries(gate?.checks || {});
  return `<section class="card m30-gate-card ${gate?.ready ? 'is-ready' : ''}"><div class="card-header"><div><span class="eyebrow">${tone === 'launch' ? 'Comienzo controlado' : 'Evidencia de cierre'}</span><h2>${esc(title)}</h2></div>${badge(gate?.ready ? 'passed' : 'pending', Boolean(gate?.ready))}</div><progress class="m30-progress" max="${esc(gate?.total || 1)}" value="${esc(gate?.passed || 0)}">${esc(gate?.passed || 0)}/${esc(gate?.total || 1)}</progress><div class="m30-check-grid">${checks.map(([key, passed]) => `<div class="m30-check ${passed ? 'ok' : ''}"><span>${passed ? '✓' : '○'}</span><b>${esc(checkLabels[key] || humanize(key))}</b></div>`).join('')}</div></section>`;
}

function phaseRail(policy) {
  return `<section class="card m30-phase-card"><div class="card-header"><div><span class="eyebrow">Recorrido operativo</span><h2>Siete etapas con evidencia</h2><p>Cada etapa deja una señal estructurada y no reemplaza la revisión jurídica del expediente.</p></div></div><div class="m30-phase-rail">${(policy.phases || []).map((phase, index) => `<article><span>${index + 1}</span><div><b>${esc(phase.label)}</b><p>${esc(phase.description)}</p></div></article>`).join('')}</div></section>`;
}

function cohortSection(data) {
  const cohort = data.active_cohort;
  if (!cohort) return `<section class="card m30-cohort-card"><div class="m30-empty-visual"><img src="/assets/brand-visuals/pilot/cohort.svg" alt="Planeación de una cohorte de piloto"><div><span class="eyebrow">Primer paso</span><h2>Crea la cohorte controlada</h2><p>Se generarán 20 cupos sin participantes preinscritos: cinco escenarios por cada producto del piloto.</p>${state.user.role === 'admin' ? '<button class="btn primary" type="button" data-m30-create-cohort>Crear cohorte</button>' : '<span class="badge yellow">Requiere administración</span>'}</div></div></section>`;
  const grouped = (cohort.plans || []).reduce((acc, row) => ((acc[row.product_code] ||= []).push(row), acc), {});
  const products = Object.entries(grouped).map(([code, plans]) => {
    const complete = plans.filter(row => row.status === 'completed').length;
    const teamReady = plans.every(row => row.assigned_specialist_id && row.independent_reviewer_id && row.qa_reviewer_id);
    return `<article class="m30-product-run"><img src="${productVisual(code)}" alt="${esc(productNames[code] || code)}"><div class="m30-product-run-main"><div class="m30-product-run-head"><div><span class="eyebrow">${esc(code)}</span><h3>${esc(productNames[code] || code)}</h3></div>${badge(teamReady ? 'Equipo completo' : 'Equipo pendiente', teamReady)}</div><progress class="m30-progress compact" max="${plans.length}" value="${complete}">${complete}/${plans.length}</progress><div class="m30-slot-list">${plans.map(plan => `<button class="m30-slot" type="button" data-m30-plan="${esc(plan.id)}"><span>${esc(humanize(plan.archetype))}</span>${badge(plan.status, plan.status === 'completed')}</button>`).join('')}</div><div class="button-group"><button class="btn secondary sm" type="button" data-m30-team="${esc(code)}">Asignar equipo del producto</button><button class="btn ghost sm" type="button" data-m30-observation-product="${esc(code)}">Registrar observación</button></div></div></article>`;
  }).join('');
  return `<section class="card m30-cohort-card"><div class="card-header"><div><span class="eyebrow">${esc(statusLabels[cohort.status] || humanize(cohort.status))}</span><h2>${esc(cohort.title)}</h2><p>${esc(cohort.plan_counts.completed || 0)} de ${esc(cohort.plan_counts.total || 0)} cupos completados.</p></div><div class="button-group">${state.user.role === 'admin' && cohort.status === 'planned' ? '<button class="btn primary sm" type="button" data-m30-activate-cohort>Activar cohorte</button>' : ''}<a class="btn secondary sm" href="/api/m30/pilot-center/export" download>Exportar evidencia</a></div></div><div class="m30-role-coverage"><div><span>Especialista</span><b>${esc(data.role_coverage.assigned)}/${esc(data.role_coverage.total)}</b></div><div><span>Revisión independiente</span><b>${esc(data.role_coverage.independent)}/${esc(data.role_coverage.total)}</b></div><div><span>QA</span><b>${esc(data.role_coverage.qa)}/${esc(data.role_coverage.total)}</b></div><div><span>Equipos completos</span><b>${esc(data.role_coverage.complete)}/${esc(data.role_coverage.total)}</b></div></div><div class="m30-product-runs">${products}</div></section>`;
}

function supportSection(data) {
  const rows = data.support_tickets || [];
  return `<section class="card"><div class="card-header"><div><span class="eyebrow">Soporte del piloto</span><h2>Fricciones operativas</h2><p>Registros breves y estructurados. No incluyas hechos, documentos, valores ni datos sensibles del caso.</p></div><button class="btn primary sm" type="button" data-m30-new-ticket>Nueva solicitud</button></div><div class="m30-support-kpis"><div><span>Abiertas</span><b>${esc(data.support_metrics.open)}</b></div><div><span>Vencidas</span><b>${esc(data.support_metrics.overdue)}</b></div><div><span>Altas/críticas</span><b>${esc(data.support_metrics.high_or_critical_open)}</b></div></div>${rows.length ? `<div class="m30-ticket-list">${rows.map(row => `<article class="m30-ticket ${row.overdue ? 'overdue' : ''}"><div><div class="approval-badges">${badge(row.priority)}${badge(row.status, ['resolved','closed'].includes(row.status))}${row.overdue ? '<span class="badge red">SLA vencido</span>' : ''}</div><b>${esc(row.summary)}</b><small>${esc(humanize(row.category))} · vence ${esc(dateText(row.due_at))}${row.owner_name ? ` · ${esc(row.owner_name)}` : ''}</small></div><button class="btn secondary sm" type="button" data-m30-ticket="${esc(row.id)}">Gestionar</button></article>`).join('')}</div>` : '<div class="empty-state compact"><p>No hay solicitudes de soporte registradas.</p></div>'}</section>`;
}

function metricsSection(data) {
  const metrics = data.readiness?.pilot_metrics || {};
  const feedback = data.release_gate?.metrics?.feedback || {};
  return `<section class="card"><div class="card-header"><div><span class="eyebrow">Aprendizaje verificable</span><h2>Métricas del piloto</h2></div><button class="btn secondary sm" type="button" data-m30-new-observation>Registrar observación</button></div><div class="m30-metric-grid"><div><span>Participantes con consentimiento</span><b>${esc(metrics.consented_participants || 0)}</b></div><div><span>Casos entregados</span><b>${esc(metrics.delivered_cases || 0)}/20</b></div><div><span>Claridad</span><b>${esc(feedback.average_clarity || 0)}/5</b></div><div><span>Facilidad</span><b>${esc(feedback.average_ease || 0)}/5</b></div><div><span>Confianza</span><b>${esc(feedback.average_confidence || 0)}/5</b></div><div><span>Fricción observada</span><b>${Math.round((data.observations?.friction_rate || 0) * 100)}%</b></div></div></section>`;
}

function decisionSection(data) {
  const cohort = data.active_cohort;
  const decisions = data.decisions || [];
  return `<section class="card"><div class="card-header"><div><span class="eyebrow">Gobierno</span><h2>Decisiones sustentadas</h2><p>Una decisión no equivale a autorización general de producción.</p></div>${state.user.role === 'admin' && cohort ? '<button class="btn primary sm" type="button" data-m30-decision>Registrar decisión</button>' : ''}</div>${decisions.length ? `<div class="m30-decision-list">${decisions.slice(0,8).map(row => `<article><div>${badge(row.decision, row.decision === 'proceed_limited')}<b>${esc(row.product_code || 'Cohorte completa')}</b><span>${esc(humanize(row.reason_code))}</span></div><small>${esc(dateText(row.created_at))} · ${esc(row.actor_name)}</small></article>`).join('')}</div>` : '<div class="empty-state compact"><p>Aún no existen decisiones de cierre.</p></div>'}<div class="legal-notice mt-16"><b>Producción pública bloqueada.</b> Los pagos reales, la entrega desatendida y la publicación general requieren una fase posterior y controles externos adicionales.</div></section>`;
}

export function createPilotCenterExperience({ shell, pageHeader }) {
  let current = null;
  let participantData = null;
  let governanceData = null;
  let simulationData = null;
  let liveEvaluationData = null;

  async function page() {
    if (!state.user || !['admin','specialist'].includes(state.user.role)) {
      app.innerHTML = shell('<div class="page"><div class="result-banner red"><div class="result-icon">!</div><div><h2>Acceso restringido</h2><p>El Centro Operativo del Piloto exige rol profesional.</p></div></div></div>'); return;
    }
    [current, participantData, governanceData, simulationData, liveEvaluationData] = await Promise.all([api(endpoint), api('/api/m30/participants/summary'), api('/api/m30/governance/summary'), api('/api/m30/simulation/summary'), api('/api/m30/live-evaluation/summary')]);
    const controlState = current.release_gate?.control?.state || 'frozen';
    const controlButton = state.user.role === 'admin' && current.active_cohort?.status === 'active' ? `<button class="btn ${controlState === 'active' ? 'secondary' : 'primary'} sm" type="button" data-m30-control="${controlState === 'active' ? 'freeze' : 'activate'}">${controlState === 'active' ? 'Congelar operación' : 'Activar operación controlada'}</button>` : '';
    app.innerHTML = shell(`<div class="page m30-pilot-page">${pageHeader({ eyebrow:'M30.5 · piloto real limitado', title:'Centro Operativo del Piloto', description:'Opera la cohorte limitada, compara evidencia real y simulada y formaliza una decisión go/no-go sin habilitar producción pública.' })}<section class="m30-pilot-hero"><div><span class="eyebrow">Operación trazable</span><h2>${current.launch_gate.ready ? 'La cohorte cumple las condiciones para iniciar' : 'Completa las compuertas antes de iniciar usuarios reales'}</h2><p>${esc(current.notice)}</p><div class="approval-badges">${badge(controlState, controlState === 'active')}<span class="badge blue">${esc(current.launch_gate.passed)}/${esc(current.launch_gate.total)} controles de inicio</span>${controlButton}</div></div><img src="/assets/brand-visuals/pilot/operations-center.svg" alt="Centro operativo para coordinar el piloto LegalAIZ.it"></section><div class="section-grid mt-22"><div class="span-6">${gateCard('Compuerta de inicio', current.launch_gate, 'launch')}</div><div class="span-6">${gateCard('Compuerta de evidencia', current.evidence_gate, 'evidence')}</div><div class="span-12">${phaseRail(current.policy)}</div><div class="span-12">${simulationSection(simulationData)}</div><div class="span-12">${liveEvaluationSection(liveEvaluationData)}</div><div class="span-12">${cohortSection(current)}</div><div class="span-12">${participantProfessionalSection(participantData)}</div><div class="span-12">${governanceProfessionalSection(governanceData,participantData)}</div><div class="span-7">${supportSection(current)}</div><div class="span-5">${metricsSection(current)}${decisionSection(current)}</div></div></div>`);
    bind();
  }

  function bind() {
    document.querySelector('[data-m30-create-cohort]')?.addEventListener('click', cohortDialog);
    document.querySelector('[data-m30-activate-cohort]')?.addEventListener('click', activateDialog);
    document.querySelector('[data-m30-control]')?.addEventListener('click', event => controlDialog(event.currentTarget.dataset.m30Control));
    document.querySelector('[data-m30-new-ticket]')?.addEventListener('click', () => ticketDialog());
    document.querySelector('[data-m30-new-observation]')?.addEventListener('click', () => observationDialog());
    document.querySelector('[data-m30-decision]')?.addEventListener('click', decisionDialog);
    document.querySelectorAll('[data-m30-team]').forEach(button => button.addEventListener('click', () => teamDialog(button.dataset.m30Team)));
    document.querySelectorAll('[data-m30-plan]').forEach(button => button.addEventListener('click', () => planDialog(button.dataset.m30Plan)));
    document.querySelectorAll('[data-m30-ticket]').forEach(button => button.addEventListener('click', () => ticketDialog(button.dataset.m30Ticket)));
    document.querySelectorAll('[data-m30-observation-product]').forEach(button => button.addEventListener('click', () => observationDialog(button.dataset.m30ObservationProduct)));
    bindParticipantProfessional(participantData, page);
    bindGovernanceProfessional(governanceData, participantData, page);
    bindSimulation(simulationData, page);
    bindLiveEvaluation(liveEvaluationData, page);
  }

  function cohortDialog() {
    openDialog({ title:'Crear cohorte controlada', subtitle:'Genera 20 cupos sin inscribir participantes.', body:`<div class="field"><label for="m30-cohort-title">Nombre de la cohorte</label><input id="m30-cohort-title" class="input" value="Piloto controlado · Cohorte 01" maxlength="120"></div><div class="field"><label for="m30-cohort-confirmation">Confirmación</label><input id="m30-cohort-confirmation" class="input" placeholder="CREAR PILOTO M25 CONTROLADO"><span class="field-hint">Escribe exactamente la frase indicada.</span></div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m30-save-cohort" type="button">Crear 20 cupos</button>' });
    document.getElementById('m30-save-cohort')?.addEventListener('click', async () => perform(async () => api('/api/m25/readiness/cohorts',{method:'POST',body:JSON.stringify({title:document.getElementById('m30-cohort-title').value,confirmation:document.getElementById('m30-cohort-confirmation').value})}), 'Cohorte creada.'));
  }

  function teamDialog(code) {
    const rows = current.professionals || [];
    openDialog({ title:`Equipo · ${productNames[code] || code}`, subtitle:'La asignación se aplica a los cinco escenarios del producto.', body:`<div class="field"><label for="m30-team-specialist">Especialista</label><select id="m30-team-specialist" class="select">${professionalOptions(rows.filter(row=>row.role==='specialist'))}</select></div><div class="field"><label for="m30-team-independent">Revisor independiente</label><select id="m30-team-independent" class="select">${professionalOptions(rows.filter(row=>row.role==='specialist'))}</select></div><div class="field"><label for="m30-team-qa">Responsable QA</label><select id="m30-team-qa" class="select">${professionalOptions(rows)}</select></div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m30-save-team" type="button">Asignar equipo</button>' });
    document.getElementById('m30-save-team')?.addEventListener('click', async () => perform(async () => api(`${endpoint}/cohorts/${encodeURIComponent(current.active_cohort.id)}/teams/${encodeURIComponent(code)}`,{method:'POST',body:JSON.stringify({assigned_specialist_id:document.getElementById('m30-team-specialist').value,independent_reviewer_id:document.getElementById('m30-team-independent').value,qa_reviewer_id:document.getElementById('m30-team-qa').value})}), 'Equipo asignado.'));
  }

  function planDialog(planId) {
    const plan = (current.active_cohort?.plans || []).find(row => row.id === planId); if (!plan) return;
    const rows = current.professionals || [];
    openDialog({ title:humanize(plan.archetype), subtitle:`${productNames[plan.product_code] || plan.product_code} · cupo de piloto`, body:`<div class="field"><label for="m30-plan-status">Estado</label><select id="m30-plan-status" class="select">${(current.policy.plan_statuses || []).map(status => option(status,statusLabels[status] || humanize(status),status===plan.status)).join('')}</select></div><div class="field"><label for="m30-plan-case">ID del expediente vinculado</label><input id="m30-plan-case" class="input" value="${esc(plan.case_id || '')}" placeholder="Se exige para completar"></div><div class="m30-dialog-grid"><div class="field"><label for="m30-plan-specialist">Especialista</label><select id="m30-plan-specialist" class="select">${professionalOptions(rows.filter(row=>row.role==='specialist'),plan.assigned_specialist_id)}</select></div><div class="field"><label for="m30-plan-independent">Revisor independiente</label><select id="m30-plan-independent" class="select">${professionalOptions(rows.filter(row=>row.role==='specialist'),plan.independent_reviewer_id)}</select></div><div class="field"><label for="m30-plan-qa">QA</label><select id="m30-plan-qa" class="select">${professionalOptions(rows,plan.qa_reviewer_id)}</select></div></div><div class="field"><label for="m30-plan-evidence">Evidencia operativa</label><textarea id="m30-plan-evidence" class="textarea" maxlength="800" placeholder="No incluyas hechos sensibles del caso.">${esc(plan.evidence_note || '')}</textarea></div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m30-save-plan" type="button">Guardar cupo</button>' });
    document.getElementById('m30-save-plan')?.addEventListener('click', async () => perform(async () => api(`${endpoint}/plans/${encodeURIComponent(planId)}`,{method:'POST',body:JSON.stringify({status:document.getElementById('m30-plan-status').value,case_id:document.getElementById('m30-plan-case').value,assigned_specialist_id:document.getElementById('m30-plan-specialist').value,independent_reviewer_id:document.getElementById('m30-plan-independent').value,qa_reviewer_id:document.getElementById('m30-plan-qa').value,evidence_note:document.getElementById('m30-plan-evidence').value})}), 'Cupo actualizado.'));
  }

  function activateDialog() {
    openDialog({ title:'Activar cohorte', subtitle:'Requiere equipos completos en los 20 cupos.', body:`<div class="legal-notice"><b>Alcance controlado.</b> Esta acción no habilita pagos reales, producción pública ni entrega desatendida.</div><div class="field mt-16"><label for="m30-activate-confirmation">Confirmación</label><input id="m30-activate-confirmation" class="input" placeholder="ACTIVAR COHORTE CONTROLADA M30"></div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m30-activate" type="button">Activar cohorte</button>' });
    document.getElementById('m30-activate')?.addEventListener('click', async () => perform(async () => api(`${endpoint}/cohorts/${encodeURIComponent(current.active_cohort.id)}/activate`,{method:'POST',body:JSON.stringify({confirmation:document.getElementById('m30-activate-confirmation').value})}), 'Cohorte activada.'));
  }

  function controlDialog(action) {
    const activate = action === 'activate';
    const confirmation = activate ? 'ACTIVAR PILOTO OPERATIVO' : 'CONGELAR PILOTO Y PRESERVAR DATOS';
    openDialog({ title:activate ? 'Activar operación controlada' : 'Congelar operación', subtitle:activate ? 'Habilita únicamente la cohorte interna ya preparada.' : 'Detiene nuevos avances y preserva toda la evidencia.', body:`<div class="legal-notice"><b>Alcance limitado.</b> Esta decisión no habilita producción pública, pagos reales ni entrega desatendida.</div><div class="field mt-16"><label for="m30-control-reason">Justificación verificable</label><textarea id="m30-control-reason" class="textarea" maxlength="1200" placeholder="Mínimo 20 caracteres; no incluyas hechos sensibles del caso."></textarea></div><div class="field"><label for="m30-control-confirmation">Confirmación</label><input id="m30-control-confirmation" class="input" placeholder="${confirmation}"><span class="field-hint">Escribe exactamente la frase indicada.</span></div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m30-save-control" type="button">Confirmar decisión</button>' });
    document.getElementById('m30-save-control')?.addEventListener('click', async () => perform(async () => { await api('/api/m24/pilot-operations/control',{method:'POST',body:JSON.stringify({action,reason:document.getElementById('m30-control-reason').value,confirmation:document.getElementById('m30-control-confirmation').value})}); return api(endpoint); }, activate ? 'Operación controlada activada.' : 'Operación congelada y evidencia preservada.'));
  }

  function ticketDialog(ticketId = '') {
    const ticket = (current.support_tickets || []).find(row => row.id === ticketId);
    if (ticket) {
      openDialog({ title:'Gestionar soporte', subtitle:ticket.summary, body:`<div class="field"><label for="m30-ticket-owner">Responsable</label><select id="m30-ticket-owner" class="select">${professionalOptions(current.professionals || [],ticket.owner_id)}</select></div><div class="field"><label for="m30-ticket-status">Estado</label><select id="m30-ticket-status" class="select">${(current.policy.support_statuses || []).map(status=>option(status,statusLabels[status] || humanize(status),status===ticket.status)).join('')}</select></div><div class="field"><label for="m30-ticket-resolution">Código de resolución</label><input id="m30-ticket-resolution" class="input" value="${esc(ticket.resolution_code || '')}" placeholder="ej. guidance_updated"></div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m30-save-ticket" type="button">Actualizar</button>' });
      document.getElementById('m30-save-ticket')?.addEventListener('click', async () => perform(async () => api(`${endpoint}/support-tickets/${encodeURIComponent(ticket.id)}`,{method:'POST',body:JSON.stringify({owner_id:document.getElementById('m30-ticket-owner').value,status:document.getElementById('m30-ticket-status').value,resolution_code:document.getElementById('m30-ticket-resolution').value})}), 'Soporte actualizado.')); return;
    }
    const cohort = current.active_cohort;
    openDialog({ title:'Nueva solicitud de soporte', subtitle:'Registra la fricción, no el contenido jurídico del caso.', body:`<div class="m30-dialog-grid"><div class="field"><label for="m30-ticket-category">Categoría</label><select id="m30-ticket-category" class="select">${(current.policy.support_categories || []).map(value=>option(value,humanize(value))).join('')}</select></div><div class="field"><label for="m30-ticket-priority">Prioridad</label><select id="m30-ticket-priority" class="select">${Object.keys(current.policy.support_priorities || {}).map(value=>option(value,priorityLabels[value])).join('')}</select></div></div><div class="field"><label for="m30-ticket-summary">Resumen operativo</label><textarea id="m30-ticket-summary" class="textarea" maxlength="220" placeholder="Ejemplo: el botón para continuar no queda visible en pantalla pequeña"></textarea><span class="field-hint">No incluyas nombres, identificaciones, valores, salud, correos ni narraciones del caso.</span></div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m30-create-ticket" type="button">Registrar soporte</button>' });
    document.getElementById('m30-create-ticket')?.addEventListener('click', async () => perform(async () => api(`${endpoint}/support-tickets`,{method:'POST',body:JSON.stringify({cohort_id:cohort?.id || null,category:document.getElementById('m30-ticket-category').value,priority:document.getElementById('m30-ticket-priority').value,summary:document.getElementById('m30-ticket-summary').value})}), 'Solicitud registrada.'));
  }

  function observationDialog(productCode = '') {
    const plans = (current.active_cohort?.plans || []).filter(row => !productCode || row.product_code === productCode);
    openDialog({ title:'Registrar observación', subtitle:'Solo señales estructuradas; no escribas relatos del caso.', body:`<div class="field"><label for="m30-observation-plan">Cupo observado</label><select id="m30-observation-plan" class="select">${plans.map(row=>option(row.id,`${row.product_code} · ${humanize(row.archetype)}`)).join('')}</select></div><div class="m30-dialog-grid"><div class="field"><label for="m30-observation-stage">Etapa</label><select id="m30-observation-stage" class="select">${(current.policy.observation_stages || []).map(value=>option(value,humanize(value))).join('')}</select></div><div class="field"><label for="m30-observation-outcome">Resultado</label><select id="m30-observation-outcome" class="select">${(current.policy.observation_outcomes || []).map(value=>option(value,humanize(value))).join('')}</select></div><div class="field"><label for="m30-observation-issue">Código de fricción</label><select id="m30-observation-issue" class="select">${(current.policy.issue_codes || []).map(value=>option(value,humanize(value))).join('')}</select></div><div class="field"><label for="m30-observation-duration">Duración</label><select id="m30-observation-duration" class="select">${(current.policy.duration_buckets || []).map(value=>option(value,humanize(value))).join('')}</select></div></div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m30-save-observation" type="button">Guardar observación</button>' });
    document.getElementById('m30-save-observation')?.addEventListener('click', async () => perform(async () => api(`${endpoint}/observations`,{method:'POST',body:JSON.stringify({case_plan_id:document.getElementById('m30-observation-plan').value,stage:document.getElementById('m30-observation-stage').value,outcome:document.getElementById('m30-observation-outcome').value,issue_code:document.getElementById('m30-observation-issue').value,duration_bucket:document.getElementById('m30-observation-duration').value})}), 'Observación registrada.'));
  }

  function decisionDialog() {
    openDialog({ title:'Registrar decisión de piloto', subtitle:'La evidencia actual queda preservada dentro del snapshot.', body:`<div class="m30-dialog-grid"><div class="field"><label for="m30-decision-product">Alcance</label><select id="m30-decision-product" class="select"><option value="">Cohorte completa</option>${Object.entries(productNames).map(([code,name])=>option(code,`${code} · ${name}`)).join('')}</select></div><div class="field"><label for="m30-decision-value">Decisión</label><select id="m30-decision-value" class="select">${(current.policy.decisions || []).map(value=>option(value,humanize(value))).join('')}</select></div><div class="field"><label for="m30-decision-reason">Motivo</label><select id="m30-decision-reason" class="select">${(current.policy.decision_reason_codes || []).map(value=>option(value,humanize(value))).join('')}</select></div></div><div class="field"><label for="m30-decision-confirmation">Confirmación</label><input id="m30-decision-confirmation" class="input" placeholder="REGISTRAR DECISION PILOTO M30"></div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m30-save-decision" type="button">Registrar decisión</button>' });
    document.getElementById('m30-save-decision')?.addEventListener('click', async () => perform(async () => api(`${endpoint}/decisions`,{method:'POST',body:JSON.stringify({cohort_id:current.active_cohort.id,product_code:document.getElementById('m30-decision-product').value,decision:document.getElementById('m30-decision-value').value,reason_code:document.getElementById('m30-decision-reason').value,confirmation:document.getElementById('m30-decision-confirmation').value})}), 'Decisión registrada.'));
  }

  async function perform(callback, message) {
    try { current = await callback(); closeDialog(); toast(message); await page(); }
    catch (error) { toast(error.message,'danger'); }
  }

  return { page };
}
