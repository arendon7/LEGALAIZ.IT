'use strict';

import { api, app, currentPath, esc, icons, state, toast } from './core.js';

export function navigationGroups() {
  if (state.user.role === 'client') return [
    { label: 'Mi ruta', items: [
      { path: '/', label: 'Inicio', icon: icons.home },
      { path: '/nuevo', label: 'Nueva solución', icon: icons.new, primary: true },
      { path: '/casos', label: 'Mis expedientes', icon: icons.cases },
    ]},
    { label: 'Consulta', items: [
      { path: '/soluciones', label: 'Explorar soluciones', icon: icons.solutions },
      { path: '/documentos', label: 'Mis documentos', icon: icons.docs },
    ]},
    { label: 'Acompañamiento', items: [
      { path: '/notificaciones', label: 'Notificaciones', icon: icons.bell },
      { path: '/ayuda', label: 'Centro de ayuda', icon: icons.help },
      { path: '/accesibilidad', label: 'Accesibilidad', icon: 'Aa' },
    ]},
  ];
  if (state.user.role === 'specialist') return [
    { label: 'Trabajo jurídico', items: [
      { path: '/', label: 'Inicio', icon: icons.home },
      { path: '/revision', label: 'Bandeja priorizada', icon: icons.review, primary: true },
      { path: '/casos', label: 'Expedientes asignados', icon: icons.cases },
      { path: '/documentos', label: 'Documentos por revisar', icon: icons.docs },
    ]},
    { label: 'Conocimiento', items: [
      { path: '/soluciones', label: 'Soluciones jurídicas', icon: icons.solutions },
      { path: '/bibliotecas', label: 'Bibliotecas vigentes', icon: icons.library },
      { path: '/maduracion-juridica', label: 'Biblioteca jurídica aprobada', icon: icons.quality },
      { path: '/demo-documental', label: 'Demo documental', icon: icons.docs },
      { path: '/demo-expedientes', label: 'Demo de expedientes', icon: icons.cases },
      { path: '/fuentes', label: 'Fuentes y criterios', icon: icons.sources },
      { path: '/red-profesional', label: 'Red profesional', icon: icons.review },
      { path: '/centro-piloto', label: 'Centro del piloto', icon: icons.shield },
    ]},
    { label: 'Acompañamiento', items: [
      { path: '/notificaciones', label: 'Notificaciones', icon: icons.bell },
      { path: '/ayuda', label: 'Centro de ayuda', icon: icons.help },
      { path: '/accesibilidad', label: 'Accesibilidad', icon: 'Aa' },
    ]},
  ];
  return [
    { label: 'Dirección', items: [
      { path: '/', label: 'Inicio', icon: icons.home },
      { path: '/demo-ejecutiva', label: 'Demo ejecutiva', icon: icons.solutions },
      { path: '/demo-documental', label: 'Demo documental', icon: icons.docs },
      { path: '/demo-expedientes', label: 'Demo de expedientes', icon: icons.cases },
      { path: '/experiencia', label: 'Experiencia y conversión', icon: icons.quality },
      { path: '/operacion', label: 'Operación jurídica', icon: icons.operation, primary: true },
      { path: '/calidad', label: 'Gobierno y calidad', icon: icons.quality },
      { path: '/red-profesional', label: 'Red profesional', icon: icons.review },
      { path: '/centro-piloto', label: 'Centro del piloto', icon: icons.shield },
      { path: '/preproduccion', label: 'Preproducción', icon: icons.settings },
    ]},
    { label: 'Contenido', items: [
      { path: '/catalogo', label: 'Catálogo jurídico', icon: icons.catalog },
      { path: '/bibliotecas', label: 'Bibliotecas vigentes', icon: icons.library },
      { path: '/maduracion-juridica', label: 'Biblioteca jurídica aprobada', icon: icons.quality },
    ]},
    { label: 'Sistema', items: [
      { path: '/notificaciones', label: 'Notificaciones', icon: icons.bell },
      { path: '/ayuda', label: 'Centro de ayuda', icon: icons.help },
      { path: '/accesibilidad', label: 'Accesibilidad', icon: 'Aa' },
      { path: '/configuracion', label: 'Configuración', icon: icons.settings },
    ]},
  ];
}

export function routeContext() {
  const path = currentPath();
  if (path.startsWith('/caso/')) return ['Mis expedientes', 'Estado y siguientes pasos'];
  if (path.startsWith('/nuevo/')) return ['Nueva solución', 'Formulario guiado'];
  if (path.startsWith('/checkout/')) return ['Nueva solución', 'Checkout sandbox'];
  if (path.startsWith('/solucion/')) return ['Soluciones', 'Alcance y entregables'];
  const map = {
    '/': ['Espacio jurídico', 'Inicio'], '/soluciones': ['Catálogo', 'Soluciones'], '/nuevo': ['Ruta guiada', 'Nueva solución'],
    '/casos': ['Expedientes', state.user.role === 'client' ? 'Mis expedientes' : 'Casos asignados'], '/documentos': ['Mis documentos', 'Borradores y versiones'],
    '/revision': ['Trabajo jurídico', 'Bandeja priorizada'], '/fuentes': ['Conocimiento', 'Fuentes y criterios'], '/operacion': ['Dirección', 'Operación jurídica'],
    '/catalogo': ['Contenido', 'Catálogo jurídico'], '/bibliotecas': ['Contenido', 'Bibliotecas vigentes'], '/biblioteca-contractual': ['Bibliotecas', 'Contratos profundos'],
    '/biblioteca-playbooks': ['Bibliotecas', 'Playbooks profundos'], '/maduracion-juridica': ['Gobierno', 'Biblioteca jurídica aprobada'], '/calidad': ['Gobierno', 'Calidad y preproducción'], '/red-profesional': ['Operación', 'Red profesional'], '/piloto': ['Preproducción', 'Participación en piloto'], '/centro-piloto': ['Preproducción', 'Centro operativo del piloto'], '/preparacion-piloto': ['Preproducción', 'Centro operativo del piloto'], '/preproduccion': ['Sistema', 'Centro de Preproducción'], '/demo-ejecutiva': ['Presentación', 'Demo ejecutiva'], '/demo-documental': ['Presentación', 'Portafolio documental final'], '/demo-expedientes': ['Presentación', 'Demo integral por expediente'], '/experiencia': ['Dirección', 'Experiencia y conversión'], '/notificaciones': ['Acompañamiento', 'Notificaciones'], '/ayuda': ['Acompañamiento', 'Centro de ayuda'], '/accesibilidad': ['Acompañamiento', 'Accesibilidad'], '/configuracion': ['Sistema', 'Configuración y seguridad'],
  };
  return map[path] || ['LegalAIZ.it', 'Espacio jurídico'];
}

export function quickAction() {
  if (state.user.role === 'client') return { route:'/nuevo', label:'Iniciar solución', icon:icons.new };
  if (state.user.role === 'specialist') return { route:'/revision', label:'Revisar pendientes', icon:icons.review };
  return { route:'/operacion', label:'Abrir operación', icon:icons.operation };
}


const candidateAssetButton = asset => {
  const label = asset.format === 'pdf' ? 'Abrir PDF' : asset.format === 'docx' ? 'Descargar DOCX' : 'Descargar JSON';
  const target = asset.format === 'pdf' ? ' target="_blank" rel="noopener"' : ' download';
  return `<a class="btn secondary sm" href="${esc(asset.download_url)}"${target}>${esc(label)}</a>`;
};

const approvalBadge = (label, approval) => {
  const status = approval?.status || 'pending';
  const cls = status === 'approved' ? 'green' : status === 'rejected' ? 'red' : 'yellow';
  const text = status === 'approved' ? 'Aprobada' : status === 'rejected' ? 'Rechazada' : 'Pendiente';
  return `<span class="badge ${cls}">${esc(label)} · ${esc(text)}</span>`;
};

async function candidateProductCard(row, validationRow) {
  const detail = await api(`/api/m24/candidate-library/${encodeURIComponent(row.product_code)}`);
  const assetGroup = (title, role) => {
    const assets = (detail.assets || []).filter(asset => asset.role === role);
    return assets.length ? `<div class="candidate-asset-group"><b>${esc(title)}</b><div class="candidate-actions">${assets.map(candidateAssetButton).join('')}</div></div>` : '';
  };
  const validation = validationRow || null;
  const approvals = validation?.approvals || { legal:{status:'pending'}, qa:{status:'pending'} };
  const activation = validation?.activation || { state:'inactive', internal_pilot_active:false };
  const evidence = (validation?.generated_documents || []).map(candidateAssetButton).join('');
  const legalAction = state.user.role === 'specialist' && validation?.passed && approvals.legal?.status !== 'approved'
    ? `<button class="btn primary sm" type="button" data-full-approval="legal" data-product-code="${esc(row.product_code)}">Registrar aprobación jurídica</button>` : '';
  const qaAction = state.user.role === 'admin' && validation?.passed && approvals.legal?.status === 'approved' && approvals.qa?.status !== 'approved'
    ? `<button class="btn primary sm" type="button" data-full-approval="qa" data-product-code="${esc(row.product_code)}">Registrar aprobación QA</button>` : '';
  const activationAction = state.user.role === 'admin' && approvals.complete
    ? activation.internal_pilot_active
      ? `<button class="btn secondary sm" type="button" data-internal-activation="deactivate" data-product-code="${esc(row.product_code)}">Desactivar piloto interno</button>`
      : `<button class="btn primary sm" type="button" data-internal-activation="activate" data-product-code="${esc(row.product_code)}">Activar piloto interno</button>`
    : '';
  const activationBadge = activation.internal_pilot_active
    ? '<span class="badge green">Piloto interno activo</span>'
    : '<span class="badge yellow">Piloto interno inactivo</span>';
  const validationPanel = validation ? `<div class="pilot-validation-panel">
      <div class="pilot-validation-head"><b>Validación integral del producto</b><span class="badge ${validation.passed ? 'green' : 'red'}">${esc(validation.passed_count)}/${esc(validation.scenario_count)} escenarios</span></div>
      <div class="approval-badges">${approvalBadge('Jurídica', approvals.legal)}${approvalBadge('QA', approvals.qa)}${activationBadge}</div>
      ${evidence ? `<div class="candidate-asset-group"><b>Evidencia de generación final</b><div class="candidate-actions">${evidence}</div></div>` : ''}
      <div class="candidate-actions">${legalAction}${qaAction}${activationAction}</div>
      <p class="demo-note">El diseño original de aprobación dual por usuarios distintos exige un especialista y un administrador distintos. M24.10 registra, por autorización expresa, la ratificación jurídica y el QA jurídico-editorial en etapas separadas por el mismo abogado responsable, divulgando que no existe independencia personal. La publicación continúa siendo una decisión separada. La activación habilita únicamente el piloto profesional interno y cada expediente mantiene sus controles específicos.</p>
    </div>` : `<div class="pilot-validation-panel muted-panel"><b>Validación no disponible</b><p>El producto no tiene evidencia completa de validación integral.</p></div>`;
  return `<article class="card candidate-product-card">
    <div class="card-header"><div><span class="eyebrow">${esc(row.product_code)} · ${esc(row.category)}</span><h2>${esc(row.public_name)}</h2></div><span class="badge green">Aprobada para piloto controlado</span></div>
    <div class="candidate-revision-grid"><span><small>Activa</small><b>${esc(row.active_revision)}</b></span><span><small>Candidata</small><b>${esc(row.candidate_revision)}</b></span><span><small>Activos</small><b>${esc(row.asset_count)}</b></span></div>
    <p class="demo-note">La revisión jurídica vigente se conserva como versión inmutable y requiere control específico en cada expediente.</p>
    ${validationPanel}
    ${assetGroup('Plantilla jurídica', 'master_template')}${assetGroup('Ejemplo diligenciado', 'worked_example')}${assetGroup('Reglas y fuentes', 'rules_and_sources')}
  </article>`;
}

async function registerFullApproval(button) {
  const type = button.dataset.fullApproval;
  const code = button.dataset.productCode;
  const label = type === 'legal' ? 'jurídica' : 'QA';
  const comment = window.prompt(`Comentario de aprobación ${label} para ${code}:`);
  if (!comment) return;
  button.disabled = true;
  try {
    await api(`/api/m24/full-validation/${encodeURIComponent(code)}/approvals`, {
      method: 'POST',
      body: JSON.stringify({ approval_type:type, decision:'approved', comment }),
    });
    toast(`Aprobación ${label} registrada para ${code}.`);
    await m24CandidateLibraryPage(window.legalaiM24PageDeps);
  } catch (error) {
    toast(error.message, 'danger');
    button.disabled = false;
  }
}

async function registerInternalActivation(button) {
  const action = button.dataset.internalActivation;
  const code = button.dataset.productCode;
  const activating = action === 'activate';
  const comment = window.prompt(`${activating ? 'Justificación de activación' : 'Motivo de desactivación'} para ${code}:`);
  if (!comment) return;
  let confirmation = '';
  if (activating) {
    confirmation = window.prompt('Escriba exactamente ACTIVAR PILOTO INTERNO para confirmar:') || '';
    if (!confirmation) return;
  }
  button.disabled = true;
  try {
    await api(`/api/m24/full-validation/${encodeURIComponent(code)}/activation`, {
      method: 'POST',
      body: JSON.stringify({ action, comment, confirmation }),
    });
    toast(`${activating ? 'Piloto interno activado' : 'Piloto interno desactivado'} para ${code}.`);
    await m24CandidateLibraryPage(window.legalaiM24PageDeps);
  } catch (error) {
    toast(error.message, 'danger');
    button.disabled = false;
  }
}

export async function m24CandidateLibraryPage({ shell, pageHeader }) {
  window.legalaiM24PageDeps = { shell, pageHeader };
  if (!state.user || !['specialist', 'admin'].includes(state.user.role)) {
    app.innerHTML = shell(`<div class="page"><div class="result-banner red"><div class="result-icon">!</div><div><h2>Acceso restringido</h2><p>Esta vista está reservada para especialistas jurídicos y administración.</p></div></div></div>`);
    return;
  }
  const data = await api('/api/m24/candidate-library');
  const integrity = await api('/api/m24/candidate-library/integrity');
  const validation = await api('/api/m24/full-validation');
  const validationMap = Object.fromEntries((validation.products || []).map(row => [row.product_code, row]));
  const cards = [];
  for (const row of data.products || []) cards.push(await candidateProductCard(row, validationMap[row.product_code]));
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow: 'Gobierno documental', title: 'Biblioteca jurídica aprobada', description: 'Once productos jurídicos, versiones inmutables, 110 escenarios aprobados y ratificación humana para uso profesional controlado.' })}
    <section class="kpi-grid"><div class="kpi"><span class="kpi-label">Productos integrados</span><div class="kpi-value"><strong>${esc(data.product_count || 0)}</strong><span class="kpi-icon">${icons.catalog}</span></div></div><div class="kpi"><span class="kpi-label">Activos verificados</span><div class="kpi-value"><strong>${esc(integrity.checked_files || 0)}</strong><span class="kpi-icon">${icons.docs}</span></div></div><div class="kpi"><span class="kpi-label">Escenarios integrales</span><div class="kpi-value"><strong>${esc(validation.passed || 0)}/${esc(validation.scenario_count || 0)}</strong><span class="kpi-icon">${icons.quality}</span></div></div><div class="kpi"><span class="kpi-label">Pilotos internos activos</span><div class="kpi-value"><strong>${esc(validation.internal_pilot_active_count || 0)}/11</strong><span class="kpi-icon">${icons.shield}</span></div></div></section>
    <div class="result-banner ${integrity.ok && validation.failed === 0 ? 'green' : 'red'}"><div class="result-icon">${integrity.ok && validation.failed === 0 ? '✓' : '!'}</div><div><h2>${validation.failed === 0 ? 'Validación integral aprobada' : 'Existen escenarios pendientes'}</h2><p>${validation.failed === 0 ? 'Los 110 escenarios y once generaciones documentales finales superaron sus controles. La biblioteca está habilitada para piloto profesional controlado; cada expediente conserva revisión y aprobación específicas antes de la entrega.' : 'No debe avanzarse a aprobación mientras existan fallos.'}</p></div></div>
    <div class="candidate-library-grid">${cards.join('')}</div></div>`);
  document.querySelectorAll('[data-full-approval]').forEach(button => button.addEventListener('click', () => registerFullApproval(button)));
  document.querySelectorAll('[data-internal-activation]').forEach(button => button.addEventListener('click', () => registerInternalActivation(button)));
}
