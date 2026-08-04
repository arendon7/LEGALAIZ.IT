'use strict';

export function createCaseDemoExperience({ app, api, esc, shell, pageHeader, toast, state }) {
  const base = '/api/m31/case-demo';
  const fileUrl = relative => `${base}/files/${encodeURIComponent(relative)}`;
  const statusClass = status => {
    const value = String(status || '').toLowerCase();
    if (value.includes('liberado') || value.includes('aprobado para liberación')) return 'green';
    if (value.includes('devuelto') || value.includes('bloque')) return 'red';
    return 'yellow';
  };
  const approvalLine = (type, approvals=[]) => {
    const row = approvals.find(item => item.approval_type === type);
    const label = type === 'legal' ? 'Jurídica' : 'QA';
    return row
      ? `<span class="badge green">${label} · ${esc(row.actor_name || row.actor_id)}</span>`
      : `<span class="badge yellow">${label} pendiente</span>`;
  };
  const fieldInput = field => {
    const value = field.value ?? '';
    if (field.type === 'select') {
      return `<select class="select" name="${esc(field.id)}">${(field.options || []).map(option => `<option value="${esc(option)}" ${String(option)===String(value)?'selected':''}>${esc(option)}</option>`).join('')}</select>`;
    }
    if (field.type === 'textarea') return `<textarea class="textarea" name="${esc(field.id)}" rows="3">${esc(value)}</textarea>`;
    const type = ['number','date','email'].includes(field.type) ? field.type : 'text';
    return `<input class="input" type="${type}" name="${esc(field.id)}" value="${esc(value)}">`;
  };
  const workflowActions = row => {
    const role = state.user?.role;
    const buttons = [];
    if (role === 'specialist' && row.workflow_status === 'Pendiente de revisión jurídica' && state.user.id === row.legal_reviewer_id) {
      buttons.push(`<button class="btn primary sm" data-m318-action="legal" data-case="${esc(row.case_id)}">Aprobar jurídicamente</button>`);
    }
    if (role === 'admin' && row.workflow_status === 'Pendiente de QA independiente') {
      buttons.push(`<button class="btn primary sm" data-m318-action="qa" data-case="${esc(row.case_id)}">Aprobar QA</button>`);
    }
    if (role === 'admin' && row.workflow_status === 'Aprobado para liberación') {
      buttons.push(`<button class="btn gold sm" data-m318-action="release" data-case="${esc(row.case_id)}">Liberar paquete final</button>`);
    }
    return buttons.join('');
  };
  const caseCard = row => `<article class="card m318-case-card">
    <div class="card-header"><div><span class="eyebrow">${esc(row.product_code)} · ${esc(row.case_id)}</span><h2>${esc(row.title)}</h2></div><span class="badge ${statusClass(row.workflow_status)}">${esc(row.workflow_status)}</span></div>
    <div class="m318-case-meta"><span><b>Revisión</b> ${esc(row.revision?.number || 0)}</span><span><b>Documentos</b> ${esc(row.document_count)}</span><span><b>Riesgo</b> ${esc(row.risk || '—')}</span></div>
    <div class="button-group">${approvalLine('legal',row.approvals)}${approvalLine('qa',row.approvals)}</div>
    <div class="button-group mt-18"><button class="btn secondary sm" data-action="go" data-route="/caso/${encodeURIComponent(row.case_id)}">Abrir expediente</button>${row.package?`<a class="btn gold sm" href="${fileUrl(row.package.download_path)}" download>Descargar paquete final</a>`:''}${workflowActions(row)}</div>
    <details class="library-detail"><summary>Editar datos y crear una nueva revisión</summary><form class="m318-revise-form" data-case="${esc(row.case_id)}"><div class="m318-field-grid">${(row.editable_fields || []).map(field=>`<label class="field"><span>${esc(field.label)}</span>${fieldInput(field)}</label>`).join('')}</div><label class="field"><span>Motivo del cambio</span><input class="input" name="change_note" value="Ajuste controlado durante la demostración"></label><button class="btn secondary sm" type="submit">Crear nueva revisión</button></form></details>
    <details class="library-detail"><summary>Ver documentos de la revisión</summary><div class="demo-reality-file-list">${(row.documents || []).map(doc=>`<div><span>${esc(doc.title)}</span><small>${esc(doc.template_id)} · ${esc(doc.sha256.slice(0,12))}…</small></div>`).join('')}</div></details>
  </article>`;

  async function prepare(reset=false) {
    const button = document.getElementById('m318-prepare');
    if (button) { button.disabled=true; button.textContent='Preparando expedientes…'; }
    try {
      await api(`${base}/prepare`, {method:'POST',body:JSON.stringify({reset,auto_release:true})});
      toast('Los 11 expedientes y sus paquetes finales quedaron preparados.');
      await page();
    } catch (error) { toast(error.message,'danger'); if(button){button.disabled=false;button.textContent='Preparar demo integral';} }
  }
  async function verify() {
    try { const result=await api(`${base}/verify`); toast(result.ok?`Verificación aprobada: ${result.checked} archivos.`:'La verificación encontró inconsistencias.',result.ok?'success':'danger'); }
    catch(error){ toast(error.message,'danger'); }
  }
  async function action(caseId, action) {
    const paths={legal:'legal-approve',qa:'qa-approve',release:'release'};
    try {
      await api(`${base}/cases/${encodeURIComponent(caseId)}/${paths[action]}`,{method:'POST',body:JSON.stringify({decision:'approve',comment:action==='legal'?'Revisión jurídica aprobada durante la demostración.':'QA aprobado sobre la revisión exacta.'})});
      toast(action==='release'?'Paquete final liberado.':'Aprobación registrada.');
      await page();
    } catch(error){ toast(error.message,'danger'); }
  }
  async function revise(form) {
    const formData=new FormData(form); const patch={};
    for(const [key,value] of formData.entries()) if(key!=='change_note') patch[key]=value;
    try {
      await api(`${base}/cases/${encodeURIComponent(form.dataset.case)}/revise`,{method:'POST',body:JSON.stringify({answers_patch:patch,note:formData.get('change_note')||''})});
      toast('Nueva revisión creada. Las aprobaciones anteriores quedaron fuera de la revisión activa.');
      await page();
    } catch(error){ toast(error.message,'danger'); }
  }
  async function page() {
    const data=await api(base); const metrics=data.metrics||{}; const ready=data.status==='ready';
    const credentials=data.credentials||{}; const cohortPackage=data.cohort_package||null;
    app.innerHTML=shell(`<div class="page m318-page">${pageHeader({eyebrow:'M31.8 · Demo integral por expediente',title:'Del formulario al paquete final aprobado',description:'Once expedientes sintéticos con documentos editables, revisiones inmutables, aprobación jurídica, QA independiente, trazabilidad y paquetes finales descargables.'})}
      <section class="demo-reality-hero"><div><span class="eyebrow">Flujo realista y controlado</span><h2>${ready?'La cohorte completa está lista para demostrar.':'Prepara los once expedientes en un solo paso.'}</h2><p>${esc(data.notice||'')}</p><div class="button-group"><button class="btn primary" id="m318-prepare">${ready?'Verificar o reconstruir cohorte':'Preparar demo integral'}</button>${ready?'<button class="btn secondary" id="m318-verify">Verificar integridad</button>':''}${cohortPackage?`<a class="btn gold" href="${fileUrl(cohortPackage.download_path)}" download>Descargar cohorte completa</a>`:''}${state.user?.role==='admin'&&ready?'<button class="btn secondary" id="m318-reset">Reiniciar demo</button>':''}</div></div><div class="demo-reality-seal"><b>${ready?'11/11':'0/11'}</b><span>expedientes completos</span></div></section>
      <section class="kpi-grid"><div class="kpi"><span class="kpi-label">Expedientes</span><div class="kpi-value"><strong>${esc(metrics.cases||0)}</strong><span class="kpi-icon">§</span></div></div><div class="kpi"><span class="kpi-label">Documentos activos</span><div class="kpi-value"><strong>${esc(metrics.documents||0)}</strong><span class="kpi-icon">✓</span></div></div><div class="kpi"><span class="kpi-label">Aprobación dual</span><div class="kpi-value"><strong>${esc(metrics.dual_approved_cases||0)}</strong><span class="kpi-icon">2</span></div></div><div class="kpi"><span class="kpi-label">Paquetes liberados</span><div class="kpi-value"><strong>${esc(metrics.released_cases||0)}</strong><span class="kpi-icon">⬇</span></div></div></section>
      ${ready?`<section class="card m318-credentials"><div class="card-header"><div><h2>Perfiles para mostrar el flujo</h2><p>La misma clave funciona únicamente en el entorno local de demostración.</p></div></div><div class="m318-credential-grid"><span><b>Cliente</b>${esc(credentials.client||'')}</span><span><b>Laboral</b>${esc(credentials.labor_specialist||'')}</span><span><b>Contratos</b>${esc(credentials.contracts_specialist||'')}</span><span><b>Tránsito</b>${esc(credentials.transit_specialist||'')}</span><span><b>QA/Admin</b>${esc(credentials.qa_admin||'')}</span><span><b>Clave</b>${esc(credentials.password||'')}</span></div></section><div class="m318-grid">${(data.cases||[]).map(caseCard).join('')}</div>`:`<section class="card empty-state"><div class="empty-icon">§</div><h2>La cohorte aún no está preparada</h2><p>El proceso generará 76 documentos, dos aprobaciones distintas por expediente, 11 certificados y 11 paquetes finales verificables.</p></section>`}
      <section class="card mt-22"><div class="legal-notice"><b>Uso exclusivamente demostrativo.</b> Los datos, personas y aprobaciones son sintéticos. Al crear una nueva revisión, las aprobaciones previas dejan de habilitar la liberación y deben repetirse sobre el nuevo hash.</div></section>
    </div>`);
    document.getElementById('m318-prepare')?.addEventListener('click',()=>prepare(false));
    document.getElementById('m318-verify')?.addEventListener('click',verify);
    document.getElementById('m318-reset')?.addEventListener('click',()=>prepare(true));
    document.querySelectorAll('[data-m318-action]').forEach(button=>button.addEventListener('click',()=>action(button.dataset.case,button.dataset.m318Action)));
    document.querySelectorAll('.m318-revise-form').forEach(form=>form.addEventListener('submit',event=>{event.preventDefault();revise(form);}));
  }
  return { page };
}
