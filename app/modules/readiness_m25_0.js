'use strict';

import { api, app, esc, icons, state, toast } from '../core.js';

const statusLabel = status => ({
  implemented_controlled: 'Implementada · controlada',
  implemented_controlled_with_disclosure: 'Implementada · responsable único',
  sandbox: 'Sandbox',
  blocked_external_provider: 'Bloqueada · proveedor externo',
  blocked_external_validation: 'Bloqueada · validación externa',
  pending_human_resource: 'Pendiente · segundo revisor',
  pending_legal_approval: 'Pendiente · aprobación jurídica',
  pending_real_validation: 'Pendiente · validación real',
  pending_execution: 'Pendiente · ejecución',
  blocked: 'Bloqueada',
}[status] || status);

const statusClass = status => status.startsWith('implemented') ? 'green' : status === 'sandbox' ? 'blue' : status.startsWith('pending') ? 'yellow' : 'red';
const checkRow = (label, passed) => `<div class="readiness-row"><div><b>${esc(label)}</b><span>${passed ? 'Evidencia verificada' : 'Pendiente'}</span></div><span class="badge ${passed ? 'green' : 'yellow'}">${passed ? 'Cumple' : 'Pendiente'}</span></div>`;

function cohortPanel(report) {
  const cohort = (report.cohorts || []).find(row => ['planned','active'].includes(row.status));
  if (!cohort) return `<div class="empty-state compact"><h3>No existe una cohorte de piloto</h3><p>La creación genera 20 cupos de prueba: cinco por cada producto piloto, sin inscribir usuarios ni almacenar datos personales.</p>${state.user.role === 'admin' ? '<button class="btn primary" type="button" data-m25-create-cohort>Crear cohorte controlada</button>' : ''}</div>`;
  const grouped = Object.groupBy ? Object.groupBy(cohort.plans || [], item => item.product_code) : (cohort.plans || []).reduce((acc, item) => ((acc[item.product_code] ||= []).push(item), acc), {});
  const products = Object.entries(grouped).map(([code, plans]) => `<div class="pilot-product-plan"><div><b>${esc(code)}</b><span>${plans.filter(x => x.status === 'completed').length}/${plans.length} completados</span></div><div class="approval-badges">${plans.map(plan => `<span class="badge ${plan.independent_reviewer_id ? 'green' : 'yellow'}" title="${esc(plan.archetype)}">${esc(plan.archetype.replaceAll('_',' '))}</span>`).join('')}</div></div>`).join('');
  return `<div class="card-header compact"><div><span class="eyebrow">${esc(cohort.status)}</span><h3>${esc(cohort.title)}</h3><p>${esc(cohort.plan_counts.total)} expedientes planificados; no hay usuarios preinscritos.</p></div></div><div class="pilot-plan-grid">${products}</div>`;
}

export function createReadinessExperience({ shell, pageHeader }) {
  async function page() {
    if (!state.user || !['admin','specialist'].includes(state.user.role)) {
      app.innerHTML = shell('<div class="page"><div class="result-banner red"><div class="result-icon">!</div><div><h2>Acceso restringido</h2><p>La preparación del piloto exige rol profesional.</p></div></div></div>');
      return;
    }
    const report = await api('/api/m25/readiness');
    const coreChecks = Object.entries(report.core_checks || {}).map(([key, value]) => checkRow(key.replaceAll('_',' '), Boolean(value))).join('');
    const productRows = (report.products || []).map(row => `<div class="readiness-row"><div><b>${esc(row.product_code)} · ${esc(row.public_name)}</b><span>${esc(row.questions)} preguntas · ${esc(row.rules)} reglas activas</span></div><span class="badge ${row.ready_for_planned_pilot ? 'green' : 'red'}">${row.ready_for_planned_pilot ? 'Preparado' : 'Bloqueado'}</span></div>`).join('');
    const capabilityRows = (report.capabilities || []).map(row => `<div class="readiness-row"><div><b>${esc(row.label)}</b><span>${esc(row.evidence)}</span></div><span class="badge ${statusClass(row.status)}">${esc(statusLabel(row.status))}</span></div>`).join('');
    const blockers = (report.blockers || []).map(text => `<li>${esc(text)}</li>`).join('');
    app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow:'Preparación verificable', title:'Auditoría del piloto real controlado', description:'Diferencia capacidades funcionales, sandbox, bloqueos y evidencia pendiente antes de probar expedientes con usuarios no abogados.' })}
      <section class="readiness-hero ${report.planning_ready ? 'ready' : 'pending'}"><div class="readiness-score">${report.planning_ready ? '100' : '—'}<span>${report.planning_ready ? '%' : ''}</span></div><div><span class="eyebrow">Planeación del piloto</span><h2>${report.planning_ready ? 'Base jurídica y técnica preparada' : 'Existen bloqueos de planeación'}</h2><p>${esc(report.notice)}</p></div><span class="badge ${report.pilot_execution_ready ? 'green' : 'yellow'}">${report.pilot_execution_ready ? 'Ejecución preparada' : 'Ejecución aún bloqueada'}</span></section>
      <section class="kpi-grid"><div class="kpi"><span class="kpi-label">Productos piloto</span><div class="kpi-value"><strong>4</strong><span class="kpi-icon">§</span></div></div><div class="kpi"><span class="kpi-label">Casos objetivo</span><div class="kpi-value"><strong>20</strong><span class="kpi-icon">${icons.cases}</span></div></div><div class="kpi"><span class="kpi-label">Preguntas activas</span><div class="kpi-value"><strong>${esc(report.runtime_counts?.questions || 0)}</strong><span class="kpi-icon">?</span></div></div><div class="kpi"><span class="kpi-label">Reglas activas</span><div class="kpi-value"><strong>${esc(report.runtime_counts?.rules || 0)}</strong><span class="kpi-icon">⚖</span></div></div></section>
      <section class="section-grid"><div class="card span-6"><div class="card-header"><div><h2>Controles estructurales</h2><p>Integridad, escenarios, aprobaciones y vinculaciones reales del runtime.</p></div></div><div class="readiness-list">${coreChecks}</div></div><div class="card span-6"><div class="card-header"><div><h2>Cuatro productos del piloto</h2><p>Contrato laboral, servicios, arrendamiento y consumidor.</p></div></div><div class="readiness-list">${productRows}</div></div><div class="card span-12"><div class="card-header"><div><h2>Plan de 20 expedientes</h2><p>Cinco arquetipos por producto, con revisión independiente planificada.</p></div></div>${cohortPanel(report)}</div><div class="card span-7"><div class="card-header"><div><h2>Inventario de capacidades</h2><p>Estado real, sin equiparar sandbox con producción.</p></div></div><div class="readiness-list">${capabilityRows}</div></div><div class="card span-5"><div class="card-header"><div><h2>Bloqueos y próximos controles</h2><p>Condiciones que permanecen pendientes.</p></div></div><div class="legal-notice"><ol>${blockers}</ol></div><div class="result-banner yellow mt-22"><div class="result-icon">!</div><div><h3>Producción pública bloqueada</h3><p>Pagos reales, entrega desatendida y publicación de M23.2 continúan deshabilitados.</p></div></div></div></section>
    </div>`);
    document.querySelector('[data-m25-create-cohort]')?.addEventListener('click', createCohort);
  }

  async function createCohort() {
    const title = window.prompt('Nombre de la cohorte:', 'Cohorte inicial controlada');
    if (!title) return;
    const confirmation = window.prompt('Escriba exactamente CREAR PILOTO M25 CONTROLADO para crear 20 cupos sin usuarios preinscritos:') || '';
    if (!confirmation) return;
    try {
      await api('/api/m25/readiness/cohorts', { method:'POST', body:JSON.stringify({ title, confirmation }) });
      toast('Cohorte creada con 20 expedientes planificados.');
      await page();
    } catch (error) { toast(error.message, 'danger'); }
  }

  return { page };
}
