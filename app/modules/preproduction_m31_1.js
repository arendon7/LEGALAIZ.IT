'use strict';

import { api, app, closeDialog, dateText, esc, humanize, openDialog, state, toast } from '../core.js';

const endpoint = '/api/m31/preproduction';
const groupLabels = {
  environment:'Entorno', security:'Seguridad', secrets:'Secretos', identity:'Identidad', continuity:'Continuidad',
  operations:'Operación', deployment:'Despliegue', data:'Datos', external:'Evidencia externa', governance:'Gobierno',
};
const decisionLabels = {
  ready_for_managed_preproduction:'Lista para preproducción administrada',
  hold_for_remediation:'Mantener bloqueada y corregir',
};
const visual = name => `/assets/brand-visuals/preproduction/${name}.svg`;
const badge = passed => `<span class="badge ${passed ? 'green' : 'red'}">${passed ? 'Superado' : 'Pendiente'}</span>`;

function checksByGroup(rows = []) {
  const grouped = rows.reduce((acc, row) => ((acc[row.group] ||= []).push(row), acc), {});
  return Object.entries(grouped).map(([group, checks]) => `<section class="card m31-check-group"><div class="card-header"><div><span class="eyebrow">${esc(groupLabels[group] || humanize(group))}</span><h2>${checks.filter(row=>row.passed).length}/${checks.length} controles</h2></div>${badge(checks.every(row=>row.passed))}</div><div class="m31-check-list">${checks.map(row=>`<article class="m31-check ${row.passed?'ok':''}"><span aria-hidden="true">${row.passed?'✓':'!'}</span><div><b>${esc(row.label)}</b><small>${esc(typeof row.detail === 'string' ? row.detail : JSON.stringify(row.detail))}</small></div></article>`).join('')}</div></section>`).join('');
}

function historyTable(rows, type) {
  if (!rows?.length) return '<div class="empty-state compact"><p>Aún no existe evidencia registrada.</p></div>';
  return `<div class="m31-history">${rows.slice(0,6).map(row=>`<article><div><b>${esc(type==='snapshot' ? row.status : type==='drill' ? row.status : decisionLabels[row.decision] || humanize(row.decision))}</b><small>${esc(dateText(row.created_at))} · ${esc(row.created_by)}</small></div><code>${esc(type==='snapshot' ? row.snapshot_hash?.slice(0,14) : type==='drill' ? row.evidence_hash?.slice(0,14) : row.id)}</code></article>`).join('')}</div>`;
}

export function createPreproductionExperience({ shell, pageHeader }) {
  let current = null;

  async function load() {
    if (!state.user || state.user.role !== 'admin') {
      app.innerHTML = shell('<div class="page"><div class="result-banner red"><div class="result-icon">!</div><div><h2>Acceso restringido</h2><p>El Centro de Preproducción está reservado para administración.</p></div></div></div>');
      return;
    }
    current = await api(endpoint);
    const report = current.current || {};
    const hard = report.hard_blocking || [];
    const latest = current.snapshots?.[0];
    const productionBlocked = current.production_authorized === false;
    app.innerHTML = shell(`<div class="page m31-page">${pageHeader({eyebrow:'M31.2 · Preproducción',title:'Centro de Preproducción',description:'Configura, verifica y documenta el entorno administrado sin habilitar producción pública.'})}
      <section class="m31-hero card"><div><span class="eyebrow">Compuerta técnica</span><h2>${report.preproduction_ready ? 'Base lista para preproducción administrada' : 'Preproducción aún bloqueada'}</h2><p>${report.preproduction_ready ? 'Los controles duros están satisfechos. Registra un snapshot y la decisión operativa antes de desplegar.' : `Faltan ${hard.length} controles duros. La aplicación puede seguir en demo o piloto local, pero no debe exponerse como preproducción.`}</p><div class="button-group"><button class="btn primary" type="button" data-m31-snapshot>Crear snapshot</button><button class="btn secondary" type="button" data-m31-backup>Ejecutar backup drill</button><a class="btn ghost" href="${endpoint}/export" download>Exportar evidencia</a></div></div><img src="${visual('gate')}" alt="Compuertas técnicas de preproducción"></section>
      <section class="kpi-grid"><div class="kpi"><span class="kpi-label">Controles satisfechos</span><div class="kpi-value"><strong>${esc(report.passed || 0)}/${esc(report.total || 0)}</strong></div></div><div class="kpi"><span class="kpi-label">Compuertas duras pendientes</span><div class="kpi-value"><strong>${esc(hard.length)}</strong></div></div><div class="kpi"><span class="kpi-label">Backups verificados</span><div class="kpi-value"><strong>${esc(current.backup_drills?.length || 0)}</strong></div></div><div class="kpi"><span class="kpi-label">Producción</span><div class="kpi-value"><strong>${productionBlocked ? 'Bloqueada' : 'No definido'}</strong></div></div></section>
      <section class="m31-visual-grid"><article class="card"><img src="${visual('environment')}" alt="Configuración segura de entornos"><h2>Entorno y secretos</h2><p>Perfil, HTTPS, cookies, origen, proxy y llaves externas deben coincidir con preproducción.</p></article><article class="card"><img src="${visual('backup')}" alt="Backup cifrado y restauración controlada"><h2>Continuidad</h2><p>El drill cifra, verifica hash y prueba la integridad de una copia restaurable sin reemplazar la base activa.</p></article><article class="card"><img src="${visual('observability')}" alt="Observabilidad y correlación de eventos"><h2>Observabilidad</h2><p>Eventos JSON, rotación, request ID y redacción de secretos preparan la operación administrada.</p></article></section>
      <div class="m31-check-grid">${checksByGroup(report.checks)}</div>
      <section class="section-grid mt-22"><div class="card span-4"><div class="card-header"><div><span class="eyebrow">Snapshots</span><h2>Evidencia inmutable</h2></div></div>${historyTable(current.snapshots,'snapshot')}</div><div class="card span-4"><div class="card-header"><div><span class="eyebrow">Continuidad</span><h2>Backup drills</h2></div></div>${historyTable(current.backup_drills,'drill')}</div><div class="card span-4"><div class="card-header"><div><span class="eyebrow">Decisiones</span><h2>Avance o corrección</h2></div>${latest?'<button class="btn primary sm" type="button" data-m31-decision>Registrar</button>':''}</div>${historyTable(current.decisions,'decision')}</div></section>
      <div class="legal-notice"><b>Alcance limitado.</b> Una decisión favorable en M31.2 habilita únicamente preproducción administrada. PostgreSQL certificado, pentest, carga, privacidad, alertas, restauración productiva y rollback permanecen como evidencias externas obligatorias.</div>
    </div>`);
    bind();
  }

  async function perform(callback, message) {
    try { await callback(); closeDialog(); toast(message); await load(); }
    catch (error) { toast(error.message, 'danger'); }
  }

  function decisionDialog() {
    const snapshots = current.snapshots || [];
    const latest = snapshots[0];
    if (!latest) return toast('Primero crea un snapshot.', 'danger');
    openDialog({title:'Decisión de preproducción',subtitle:'No autoriza producción pública.',body:`<div class="field"><label for="m31-snapshot">Snapshot</label><select id="m31-snapshot" class="select">${snapshots.map(row=>`<option value="${esc(row.id)}">${esc(row.id)} · ${esc(row.status)}</option>`).join('')}</select></div><div class="field"><label for="m31-decision">Decisión</label><select id="m31-decision" class="select"><option value="hold_for_remediation">Mantener bloqueada y corregir</option>${latest.status==='ready_for_managed_preproduction'?'<option value="ready_for_managed_preproduction">Lista para preproducción administrada</option>':''}</select></div><div class="field"><label for="m31-reason">Justificación</label><textarea id="m31-reason" class="textarea" maxlength="1000" placeholder="Describe la evidencia revisada y las condiciones del avance."></textarea></div><div class="field"><label for="m31-confirmation">Confirmación exacta</label><input id="m31-confirmation" class="input" placeholder="REGISTRAR DECISION PREPRODUCCION M31"></div>`,actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m31-save-decision" type="button">Registrar decisión</button>'});
    document.getElementById('m31-save-decision')?.addEventListener('click',()=>perform(()=>api(`${endpoint}/decisions`,{method:'POST',body:JSON.stringify({snapshot_id:document.getElementById('m31-snapshot').value,decision:document.getElementById('m31-decision').value,reason:document.getElementById('m31-reason').value,confirmation:document.getElementById('m31-confirmation').value})}),'Decisión registrada.'));
  }

  function bind() {
    document.querySelector('[data-m31-snapshot]')?.addEventListener('click',()=>perform(()=>api(`${endpoint}/snapshots`,{method:'POST',body:'{}'}),'Snapshot de preproducción creado.'));
    document.querySelector('[data-m31-backup]')?.addEventListener('click',()=>perform(()=>api(`${endpoint}/backup-drills`,{method:'POST',body:'{}'}),'Backup drill cifrado y verificado.'));
    document.querySelector('[data-m31-decision]')?.addEventListener('click',decisionDialog);
  }

  return { page: load };
}
