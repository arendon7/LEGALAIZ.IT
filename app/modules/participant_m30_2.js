'use strict';

import { api, app, closeDialog, dateText, esc, humanize, openDialog, state, toast } from '../core.js';
import { bindClientCommunications, clientCommunicationSection } from './pilot_governance_m30_3.js';

const endpoint = '/api/m30/participants';
const productNames = {
  'CO-LA-002':'Contrato laboral', 'CO-EM-003':'Prestación de servicios',
  'CO-AR-001':'Arrendamiento de vivienda', 'CO-CD-003':'Protección al consumidor',
};
const statusLabels = { invited:'Invitado', accepted:'Consentimiento vigente', declined:'Invitación rechazada', withdrawn:'Participación retirada', expired:'Invitación vencida' };
const issueLabels = {
  cannot_access:'No puedo acceder', unclear_step:'No entiendo el siguiente paso', validation_block:'El formulario no me permite avanzar',
  document_not_generated:'El documento no se generó', review_delay:'La revisión está demorada', format_problem:'El documento presenta un problema visual',
  privacy_question:'Tengo una pregunta de privacidad', other:'Otra fricción operativa',
};
const categoryLabels = { access:'Acceso', navigation:'Navegación', document_generation:'Generación documental', legal_review:'Revisión jurídica', qa:'QA documental', privacy:'Privacidad', other:'Otra' };
const badge = status => `<span class="badge ${status === 'accepted' ? 'green' : ['withdrawn','declined','expired'].includes(status) ? 'red' : 'yellow'}">${esc(statusLabels[status] || humanize(status))}</span>`;
const option = (value,label) => `<option value="${esc(value)}">${esc(label)}</option>`;

export function participantProfessionalSection(data) {
  if (!data) return '';
  const metrics = data.metrics || {}, counts = metrics.counts || {}, participants = data.participants || [];
  return `<section class="card m302-participant-card"><div class="card-header"><div><span class="eyebrow">M30.2 · incorporación</span><h2>Participantes y consentimientos</h2><p>Vincula cuentas cliente existentes con cupos específicos. La identidad no se duplica y los correos se muestran enmascarados.</p></div><div class="button-group">${state.user.role === 'admin' ? '<button class="btn primary sm" type="button" data-m302-invite>Invitar participante</button>' : ''}<a class="btn secondary sm" href="/api/m30/participants/export" download>Exportar incorporación</a></div></div>
  <div class="m302-kpis"><div><span>Invitados</span><b>${esc(counts.invited || 0)}</b></div><div><span>Consentimientos vigentes</span><b>${esc(counts.accepted || 0)}/${esc(metrics.target || 20)}</b></div><div><span>Cobertura</span><b>${Math.round((metrics.accepted_coverage || 0)*100)}%</b></div><div><span>Cupos disponibles</span><b>${esc(metrics.available_slots || 0)}</b></div><div><span>Respuesta</span><b>${Math.round((metrics.response_rate || 0)*100)}%</b></div><div><span>Soporte dentro de SLA</span><b>${Math.round((metrics.support_sla?.within_sla_rate || 0)*100)}%</b></div></div>
  ${participants.length ? `<div class="m302-participant-list">${participants.map(row=>`<article><div class="m302-participant-main"><span class="avatar">${esc((row.user_name || '?').split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase())}</span><div><div class="approval-badges">${badge(row.status)}<span class="badge blue">${esc(row.product_code)}</span></div><b>${esc(row.user_name)}</b><span>${esc(row.masked_email)} · ${esc(productNames[row.product_code] || row.product_code)}</span><small>${esc(humanize(row.archetype))} · invitación ${esc(dateText(row.invited_at))}${row.accepted_at ? ` · aceptada ${esc(dateText(row.accepted_at))}` : ''}</small></div></div><div class="m302-retention"><span>Retención</span><b>${esc(humanize(row.retention_state))}</b>${row.retention_due_at ? `<small>${esc(dateText(row.retention_due_at))}</small>` : ''}</div></article>`).join('')}</div>` : '<div class="empty-state compact"><p>Aún no hay invitaciones. Los cupos siguen disponibles y no existen participantes preinscritos.</p></div>'}
  <div class="legal-notice mt-16"><b>Política provisional de retención.</b> No existe borrado automático. Los registros retirados o vencidos quedan programados para revisión y pueden estar sujetos a preservación por auditoría o legal hold.</div></section>`;
}

export function bindParticipantProfessional(data, refresh) {
  document.querySelector('[data-m302-invite]')?.addEventListener('click', () => inviteDialog(data, refresh));
}

function inviteDialog(data, refresh) {
  const plans = (data.active_cohort?.plans || []).filter(plan => ['planned','recruited'].includes(plan.status) && !(data.participants || []).some(p => p.case_plan_id === plan.id && ['invited','accepted'].includes(p.status)));
  const clients = data.available_clients || [];
  if (!plans.length) return toast('No hay cupos disponibles para nuevas invitaciones.','danger');
  if (!clients.length) return toast('No existen cuentas cliente activas para invitar.','danger');
  openDialog({ title:'Invitar participante', subtitle:'La invitación se vincula a un cupo y una cuenta cliente existente.', body:`<div class="field"><label for="m302-plan">Cupo del piloto</label><select id="m302-plan" class="select">${plans.map(row=>option(row.id,`${row.product_code} · ${humanize(row.archetype)}`)).join('')}</select></div><div class="field"><label for="m302-user">Cuenta participante</label><select id="m302-user" class="select">${clients.map(row=>option(row.id,`${row.name} · ${row.masked_email}`)).join('')}</select></div><div class="legal-notice"><b>Sin duplicar identidad.</b> No se solicitan documentos de identidad, información clínica, valores ni narraciones del caso.</div>`, actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m302-send-invite" type="button">Crear invitación</button>' });
  document.getElementById('m302-send-invite')?.addEventListener('click', async () => {
    try {
      const result = await api(`${endpoint}/invitations`,{method:'POST',body:JSON.stringify({case_plan_id:document.getElementById('m302-plan').value,user_id:document.getElementById('m302-user').value})});
      const invitation = result.invitation || {};
      openDialog({ title:'Invitación creada', subtitle:'El código se muestra una sola vez.', body:`<div class="legal-notice"><b>Entrega manual de demostración.</b> La integración externa de correo todavía no está habilitada.</div><div class="field mt-16"><label>Código de invitación</label><code class="m302-token">${esc(invitation.token || '')}</code></div><p class="muted">Vence ${esc(dateText(invitation.expires_at))}. Compártelo únicamente con la cuenta seleccionada.</p>`, actions:'<button class="btn primary" id="m302-invite-done" type="button">Entendido</button>' });
      document.getElementById('m302-invite-done')?.addEventListener('click', async()=>{ closeDialog(); await refresh(); });
    } catch(error){ toast(error.message,'danger'); }
  });
}

export function createParticipantExperience({ shell, pageHeader }) {
  let current = null;
  let governanceCurrent = null;
  const ack = id => Boolean(document.getElementById(id)?.checked);
  const val = id => document.getElementById(id)?.value || '';
  const ratingOptions = Array.from({length:5},(_,i)=>`<option value="${i+1}">${i+1}</option>`).join('');

  function invitationView(data) {
    const p = data.participant, consent = data.policy?.consent || {};
    return `<div class="page m302-client-page">${pageHeader({eyebrow:'Piloto controlado',title:'Tu invitación a LegalAIZ.it',description:'Revisa el alcance, decide voluntariamente y conserva control sobre tu participación.'})}<section class="m302-client-hero"><div><span class="eyebrow">${esc(p.product_code)}</span><h2>${esc(productNames[p.product_code] || p.product_code)}</h2><p>${esc(data.notice)}</p>${badge(p.status)}</div><img src="/assets/brand-visuals/pilot/cohort.svg" alt="Participación guiada en el piloto LegalAIZ.it"></section><section class="section-grid mt-22"><div class="card span-7"><div class="card-header"><div><h2>Antes de aceptar</h2><p>Tu autorización será previa, expresa e informada y quedará vinculada a esta versión del piloto.</p></div><span class="badge blue">${esc(data.policy.consent_version)}</span></div><h3>Finalidades</h3><ul class="check-list">${(consent.purposes || []).map(x=>`<li>${esc(x)}</li>`).join('')}</ul><h3>Derechos</h3><ul class="check-list">${(consent.rights || []).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div><div class="card span-5"><div class="card-header"><div><h2>Consentimiento</h2><p>Marca cada condición después de leerla.</p></div></div><div class="pilot-consent-list"><label><input id="m302-voluntary" type="checkbox"> Participo voluntariamente y puedo retirarme.</label><label><input id="m302-privacy" type="checkbox"> Conozco el aviso y las finalidades del tratamiento.</label><label><input id="m302-no-representation" type="checkbox"> Comprendo que no existe representación ni garantía de resultado.</label><label><input id="m302-minimized" type="checkbox"> Usaré información ficticia o estrictamente minimizada.</label><label><input id="m302-support-channel" type="checkbox"> Usaré el canal estructurado de soporte sin narrar el caso.</label></div><div class="field"><label for="m302-token">Código de invitación</label><input id="m302-token" class="input" autocomplete="one-time-code"></div><div class="field"><label for="m302-confirmation">Confirmación</label><input id="m302-confirmation" class="input" placeholder="${esc(consent.confirmation)}"><span class="field-hint">Escribe exactamente la frase indicada.</span></div><div class="button-group"><button class="btn primary" type="button" data-m302-accept>Aceptar participación</button><button class="btn secondary" type="button" data-m302-decline>Rechazar invitación</button></div></div></section></div>`;
  }

  function acceptedView(data) {
    const p = data.participant, tickets = data.support_tickets || [];
    return `<div class="page m302-client-page">${pageHeader({eyebrow:'Piloto controlado',title:'Tu participación está activa',description:'Avanza con datos minimizados, solicita ayuda y evalúa la experiencia sin incluir información sensible.'})}<section class="m302-client-hero accepted"><div><span class="eyebrow">${esc(p.product_code)}</span><h2>${esc(productNames[p.product_code] || p.product_code)}</h2><p>Consentimiento ${esc(p.consent_version)} registrado el ${esc(dateText(p.accepted_at))}. Cada documento continúa sujeto a revisión jurídica y QA.</p>${badge(p.status)}<span class="m302-hash">Huella de consentimiento: ${esc((p.consent_hash || '').slice(0,16))}…</span></div><img src="/assets/brand-visuals/pilot/operations-center.svg" alt="Centro de acompañamiento del piloto LegalAIZ.it"></section><section class="section-grid mt-22"><div class="card span-6"><div class="card-header"><div><h2>Soporte del piloto</h2><p>Describe la fricción, no los hechos jurídicos del caso.</p></div></div><div class="m30-dialog-grid"><div class="field"><label for="m302-support-category">Categoría</label><select id="m302-support-category" class="select">${Object.entries(categoryLabels).map(([k,v])=>option(k,v)).join('')}</select></div><div class="field"><label for="m302-support-issue">Problema</label><select id="m302-support-issue" class="select">${Object.entries(issueLabels).map(([k,v])=>option(k,v)).join('')}</select></div></div><div class="field"><label for="m302-support-summary">Resumen breve</label><textarea id="m302-support-summary" class="textarea" maxlength="180" placeholder="Ejemplo: el botón continuar no aparece en pantalla pequeña"></textarea></div><button class="btn primary" type="button" data-m302-support>Solicitar ayuda</button>${tickets.length ? `<div class="m302-client-tickets">${tickets.map(t=>`<article><div>${badge(t.status === 'closed' ? 'accepted' : 'invited')}<b>${esc(t.summary)}</b><span>${esc(categoryLabels[t.category] || humanize(t.category))} · vence ${esc(dateText(t.due_at))}</span></div><small>${esc(humanize(t.status))}${t.resolution_code ? ` · ${esc(t.resolution_code)}` : ''}</small></article>`).join('')}</div>` : '<p class="muted mt-16">No tienes solicitudes abiertas.</p>'}</div><div class="card span-6"><div class="card-header"><div><h2>Evalúa el recorrido</h2><p>Tu opinión se registra separada del contenido jurídico.</p></div></div><div class="pilot-rating-grid"><label>Claridad<select id="m302-feedback-clarity" class="select">${ratingOptions}</select></label><label>Facilidad<select id="m302-feedback-ease" class="select">${ratingOptions}</select></label><label>Confianza<select id="m302-feedback-confidence" class="select">${ratingOptions}</select></label></div><label class="check-line"><input id="m302-feedback-goal" type="checkbox"> Logré el objetivo del recorrido</label><div class="field"><label for="m302-feedback-comment">Comentario opcional</label><textarea id="m302-feedback-comment" class="textarea" maxlength="1000" placeholder="No incluyas nombres, identificaciones ni detalles sensibles"></textarea></div><button class="btn secondary" type="button" data-m302-feedback>Enviar evaluación</button><div class="legal-notice mt-16"><b>Retiro disponible.</b> Puedes retirarte sin que ello elimine automáticamente la evidencia de seguridad y auditoría ya creada. <button class="btn ghost sm" type="button" data-m302-withdraw>Retirar participación</button></div></div></section></div>`;
  }

  function emptyView(data) {
    return `<div class="page">${pageHeader({eyebrow:'Piloto controlado',title:'Aún no tienes una invitación',description:'La participación se asigna a una cohorte y un cupo específico; no existen usuarios preinscritos.'})}<section class="card m30-empty-visual"><img src="/assets/brand-visuals/pilot/cohort.svg" alt="Cohorte controlada"><div><h2>Tu cuenta no está vinculada a la cohorte activa</h2><p>${esc(data.notice || '')}</p><button class="btn secondary" type="button" data-action="go" data-route="/">Volver al inicio</button></div></section></div>`;
  }

  async function page() {
    [current, governanceCurrent] = await Promise.all([api(`${endpoint}/me`),api('/api/m30/governance/me')]);
    const p = current.participant;
    const base=!p ? emptyView(current) : p.status === 'invited' ? invitationView(current) : p.status === 'accepted' ? acceptedView(current) : emptyView(current);
    app.innerHTML = shell(`${base}${clientCommunicationSection(governanceCurrent)}`);
    bind();
  }

  function bind() {
    document.querySelector('[data-m302-accept]')?.addEventListener('click',()=>respond('accept'));
    document.querySelector('[data-m302-decline]')?.addEventListener('click',()=>respond('decline'));
    document.querySelector('[data-m302-support]')?.addEventListener('click',support);
    document.querySelector('[data-m302-feedback]')?.addEventListener('click',feedback);
    document.querySelector('[data-m302-withdraw]')?.addEventListener('click',withdrawDialog);
    bindClientCommunications(governanceCurrent,page);
  }

  async function respond(action) {
    try {
      await api(`${endpoint}/respond`,{method:'POST',body:JSON.stringify({action,token:val('m302-token'),voluntary_ack:ack('m302-voluntary'),privacy_notice_ack:ack('m302-privacy'),no_representation_ack:ack('m302-no-representation'),minimized_data_ack:ack('m302-minimized'),support_channel_ack:ack('m302-support-channel'),confirmation:val('m302-confirmation')})});
      toast(action === 'accept' ? 'Consentimiento registrado.' : 'Invitación rechazada.'); await page();
    } catch(error){ toast(error.message,'danger'); }
  }
  async function support() {
    try { await api(`${endpoint}/support`,{method:'POST',body:JSON.stringify({category:val('m302-support-category'),issue_code:val('m302-support-issue'),summary:val('m302-support-summary')})}); toast('Solicitud de soporte registrada.'); await page(); }
    catch(error){ toast(error.message,'danger'); }
  }
  async function feedback() {
    try { await api('/api/m24/pilot-operations/feedback',{method:'POST',body:JSON.stringify({case_id:null,clarity:Number(val('m302-feedback-clarity')),ease:Number(val('m302-feedback-ease')),confidence:Number(val('m302-feedback-confidence')),goal_met:ack('m302-feedback-goal'),comment:val('m302-feedback-comment')})}); toast('Evaluación registrada.'); }
    catch(error){ toast(error.message,'danger'); }
  }
  function withdrawDialog() {
    const phrase = current.policy.consent.withdrawal_confirmation;
    openDialog({title:'Retirar participación',subtitle:'El retiro bloquea nuevos avances del cupo y programa la revisión de retención.',body:`<div class="legal-notice"><b>No hay borrado automático.</b> La evidencia ya creada se conserva según la política M30.3, auditoría y posibles obligaciones de preservación.</div><div class="field mt-16"><label for="m302-withdraw-confirmation">Confirmación</label><input id="m302-withdraw-confirmation" class="input" placeholder="${esc(phrase)}"></div>`,actions:'<button class="btn secondary" type="button" data-action="close-dialog">Cancelar</button><button class="btn primary" id="m302-confirm-withdraw" type="button">Retirar participación</button>'});
    document.getElementById('m302-confirm-withdraw')?.addEventListener('click',async()=>{ try{ await api(`${endpoint}/withdraw`,{method:'POST',body:JSON.stringify({confirmation:val('m302-withdraw-confirmation')})}); closeDialog(); toast('Participación retirada.'); await page(); }catch(error){ toast(error.message,'danger'); } });
  }
  return { page };
}
