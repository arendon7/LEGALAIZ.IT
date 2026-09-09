import { api, closeDialog, dateText, esc, openDialog, state, toast } from '../core.js';

const FOLLOWUP_PREFIX = '/api/m37/follow-up/cases';
const EVIDENCE_PREFIX = '/api/m37/evidence/cases';
const TIMING_PREFIX = '/api/m37/timing/cases';
const DISPOSITION_PREFIX = '/api/m37/disposition/cases';
const START_CONFIRMATION = 'INICIAR SEGUIMIENTO';
const ALLOWED_UPLOAD = '.pdf,.png,.jpg,.jpeg,.docx,.txt';
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const models = new Map();
const inFlight = new Set();
let scheduled = false;

function pathNow() {
  return (location.hash.replace(/^#/, '') || '/').split('?')[0];
}

function caseFromPath(path = pathNow()) {
  const match = String(path).match(/^\/caso\/([^/?#]+)$/);
  return match ? decodeURIComponent(match[1]) : '';
}

function clientCaseId() {
  if (!state.user || state.user.role !== 'client') return '';
  return caseFromPath();
}

function safeId(value) {
  const text = String(value || '');
  return /^[A-Za-z0-9._-]{1,120}$/.test(text) ? text : '';
}

function dateOnlyText(value) {
  const raw = String(value || '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw ? esc(raw) : 'Sin fecha';
  try {
    const [year, month, day] = raw.split('-').map(Number);
    return new Date(year, month - 1, day, 12).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return esc(raw);
  }
}

function fileSizeText(bytes) {
  const value = Math.max(0, Number(bytes) || 0);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function safeEvidenceDownloadUrl(item, caseId) {
  const evidenceId = safeId(item?.evidence_id);
  if (!evidenceId) return '';
  const expected = `${EVIDENCE_PREFIX}/${encodeURIComponent(caseId)}/items/${encodeURIComponent(evidenceId)}/download`;
  return String(item?.download_url || '') === expected ? expected : '';
}

function taskStatus(task) {
  const status = String(task?.status || 'pending');
  const effective = String(task?.effective_status || status);
  if (status === 'completed') {
    const completion = String(task?.completion?.class || '');
    return completion === 'SELF_REPORTED'
      ? { label: 'Reportada por ti', className: 'done', note: 'La plataforma registra tu reporte; no lo convierte en verificación externa.' }
      : { label: 'Registrada como realizada', className: 'done', note: 'La actividad figura registrada, sin presumir efectos jurídicos externos.' };
  }
  if (status === 'cancelled') return { label: 'Cancelada', className: 'muted', note: 'Esta actividad no figura como completada.' };
  if (effective === 'overdue') return { label: 'Punto operativo pendiente', className: 'attention', note: 'La referencia operativa ya pasó; no representa un término legal.' };
  return { label: 'Pendiente', className: 'pending', note: 'Aún no has reportado esta actividad como realizada.' };
}

function reviewStatus(item) {
  const review = item?.review || {};
  const disposition = String(review.disposition || '');
  if (String(review.status || '') === 'PENDING_REVIEW') {
    return { label: 'Pendiente de revisión de ingreso', className: 'pending', message: 'Adjuntar el soporte no completa la actividad.' };
  }
  if (disposition === 'NEEDS_CLARIFICATION') {
    return { label: 'Requiere aclaración', className: 'attention', message: String(review.message_to_client || 'El equipo necesita información adicional sobre este soporte.') };
  }
  if (disposition === 'NOT_RELEVANT_TO_TASK') {
    return { label: 'No corresponde a esta actividad', className: 'muted', message: String(review.message_to_client || 'El soporte fue revisado para ingreso y no se vinculó como pertinente a esta actividad.') };
  }
  return { label: 'Revisado para seguimiento', className: 'done', message: String(review.message_to_client || 'El soporte fue revisado para su incorporación al seguimiento.') };
}

const EVENT_LABELS = {
  ACTION_PERFORMED: 'Acción realizada',
  AUTHORITY_RECEIPT_REPORTED: 'Recepción informada',
  NOTICE_RECEIVED: 'Notificación recibida',
  RESPONSE_RECEIVED: 'Respuesta recibida',
  OTHER_RELEVANT_EVENT: 'Otro hecho relevante',
};

const REMINDER_LABELS = {
  SCHEDULED: 'Programado',
  DUE: 'Pendiente de atender',
  ACKNOWLEDGED: 'Reconocido',
  CANCELLED: 'Cancelado',
};

function evidenceFor(model, followUpId) {
  return (model.evidence?.items || []).filter(item => String(item.follow_up_id || '') === String(followUpId || ''));
}

function datesFor(model, followUpId) {
  return (model.timing?.date_records || []).filter(item => String(item.follow_up_id || '') === String(followUpId || '') && item.superseded !== true);
}

function remindersFor(model, followUpId) {
  return (model.timing?.reminders || []).filter(item => String(item.follow_up_id || '') === String(followUpId || ''));
}

function evidenceMarkup(items, caseId) {
  if (!items.length) return '<p class="m384-empty">Todavía no has adjuntado soportes a esta actividad.</p>';
  return `<div class="m384-support-list">${items.map(item => {
    const status = reviewStatus(item);
    const url = safeEvidenceDownloadUrl(item, caseId);
    return `<article class="m384-support">
      <div class="m384-support-main"><b>${esc(item.filename || 'Soporte')}</b><span>${esc(item.file_kind || 'Archivo')} · ${esc(fileSizeText(item.size_bytes))} · ${esc(dateText(item.uploaded_at))}</span></div>
      <div class="m384-support-review"><span class="m384-pill ${status.className}">${esc(status.label)}</span><small>${esc(status.message)}</small></div>
      ${url ? `<a class="m384-text-link" href="${esc(url)}">Descargar soporte</a>` : ''}
    </article>`;
  }).join('')}</div>`;
}

function timingMarkup(model, task, active) {
  const dates = datesFor(model, task.follow_up_id);
  const reminders = remindersFor(model, task.follow_up_id);
  const dateRows = dates.length ? `<div class="m384-timing-list">${dates.map(item => `<div><span>${esc(EVENT_LABELS[item.event_type] || 'Fecha registrada')}</span><b>${esc(dateOnlyText(item.date))}</b><small>${item.provenance === 'USER_ASSERTED' ? 'Registrada por ti' : 'Registrada por un profesional'} · No constituye un término legal verificado.</small></div>`).join('')}</div>` : '';
  const reminderRows = reminders.length ? `<div class="m384-reminder-list">${reminders.map(item => {
    const rid = safeId(item.reminder_id);
    const terminal = ['ACKNOWLEDGED', 'CANCELLED'].includes(String(item.status || ''));
    return `<div class="m384-reminder"><div><span>${esc(REMINDER_LABELS[item.status] || 'Recordatorio')}</span><b>${esc(dateOnlyText(item.scheduled_for))}</b><small>Recordatorio dentro de LegalAIZ.it; no es un vencimiento normativo ni confirma notificación externa.</small></div>${active && rid && !terminal ? `<div class="m384-mini-actions"><button type="button" class="m384-link-button" data-m384-action="ack-reminder" data-case-id="${esc(model.caseId)}" data-reminder-id="${esc(rid)}">Marcar atendido</button><button type="button" class="m384-link-button muted" data-m384-action="cancel-reminder" data-case-id="${esc(model.caseId)}" data-reminder-id="${esc(rid)}">Cancelar</button></div>` : ''}</div>`;
  }).join('')}</div>` : '';
  if (!dateRows && !reminderRows) return '';
  return `<div class="m384-task-timing">${dateRows}${reminderRows}</div>`;
}

function taskMarkup(model, task) {
  const id = safeId(task.follow_up_id);
  if (!id) return '';
  const status = taskStatus(task);
  const active = model.followup.lifecycle === 'ACTIVE';
  const supports = evidenceFor(model, id);
  const due = task.due_at ? `<div class="m384-checkpoint"><span>Punto de control operativo</span><b>${esc(dateText(task.due_at))}</b><small>No es un término legal calculado ni verificado.</small></div>` : '';
  return `<article class="m384-task" data-m384-task>
    <div class="m384-task-head">
      <div><span class="m384-task-kind">${esc(String(task.kind || '').replaceAll('_', ' ').toLowerCase())}</span><h3>${esc(task.label || 'Actividad de seguimiento')}</h3></div>
      <span class="m384-pill ${status.className}">${esc(status.label)}</span>
    </div>
    <p class="m384-task-note">${esc(status.note)}</p>
    ${due}
    ${active ? `<div class="m384-task-actions">
      ${task.status !== 'completed' ? `<button type="button" class="btn primary small" data-m384-action="complete-task" data-case-id="${esc(model.caseId)}" data-task-id="${esc(id)}" data-task-label="${esc(task.label || '')}">Reportar como realizada</button>` : ''}
      <button type="button" class="btn secondary small" data-m384-action="upload" data-case-id="${esc(model.caseId)}" data-task-id="${esc(id)}">Adjuntar soporte</button>
      <button type="button" class="btn ghost small" data-m384-action="record-date" data-case-id="${esc(model.caseId)}" data-task-id="${esc(id)}">Registrar fecha</button>
      <button type="button" class="btn ghost small" data-m384-action="schedule-reminder" data-case-id="${esc(model.caseId)}" data-task-id="${esc(id)}">Crear recordatorio</button>
    </div>` : ''}
    <details class="m384-task-details"><summary>Soportes y referencias de esta actividad</summary>${evidenceMarkup(supports, model.caseId)}${timingMarkup(model, task, active)}</details>
  </article>`;
}

function blockerText(code) {
  return ({
    FOLLOW_UP_NOT_ACTIVE: 'El seguimiento aún no está activo.',
    M24_NOT_IN_FOLLOW_UP: 'El expediente no está actualmente en etapa de seguimiento.',
    REQUIRED_TASKS_NOT_COMPLETED: 'Aún hay actividades requeridas sin reportar como realizadas.',
    EVIDENCE_PENDING_REVIEW: 'Hay soportes pendientes de revisión de ingreso.',
    EVIDENCE_NEEDS_CLARIFICATION: 'Un soporte requiere una aclaración antes de continuar.',
    ACTIVE_REMINDER: 'Hay recordatorios operativos activos por atender o cancelar.',
  })[code] || 'Existe una condición pendiente que debe revisar el equipo profesional.';
}

function professionalMarkup(model) {
  const assessment = model.disposition;
  if (!assessment) return '<div class="m384-professional"><b>Revisión profesional</b><p>No fue posible consultar todavía el estado de cierre profesional. Tus actividades permanecen registradas.</p></div>';
  const disposition = assessment.disposition || null;
  if (disposition?.status === 'COMPLETED') {
    const closed = disposition.target === 'CERRADO';
    return `<div class="m384-professional final"><span>${closed ? 'Seguimiento cerrado por profesional' : 'Expediente escalado para atención adicional'}</span><h3>${closed ? 'El alcance de seguimiento de esta etapa fue cerrado.' : 'El equipo determinó que el expediente requiere una etapa adicional.'}</h3><p>${esc(disposition.client_summary || 'Consulta el expediente para conocer el estado profesional registrado.')}</p><small>Este estado no equivale, por sí solo, a éxito jurídico ni acredita efectos ante terceros o autoridades.</small></div>`;
  }
  const gate = assessment.close_gate || {};
  const blockers = Array.isArray(gate.blockers) ? gate.blockers : [];
  if (gate.ready === true) {
    return `<div class="m384-professional ready"><span>Listo para revisión de cierre</span><h3>Tu parte del seguimiento está completa.</h3><p>El especialista asignado debe revisar el expediente y decidir expresamente si corresponde cerrar esta etapa. LegalAIZ.it no la cierra automáticamente.</p></div>`;
  }
  return `<div class="m384-professional"><span>Revisión profesional pendiente</span><h3>Hay condiciones por completar antes del cierre de esta etapa.</h3>${blockers.length ? `<ul>${blockers.map(item => `<li>${esc(blockerText(item))}</li>`).join('')}</ul>` : '<p>El equipo profesional todavía no ha marcado esta etapa como lista para cierre.</p>'}<small>El cliente no puede cerrar ni escalar el expediente desde esta interfaz.</small></div>`;
}

function summaryMarkup(model) {
  const followup = model.followup;
  const metrics = followup.metrics || {};
  const total = Math.max(0, Number(metrics.tasks) || 0);
  const completed = Math.max(0, Number(metrics.completed) || 0);
  const percent = total ? Math.min(100, Math.round((completed / total) * 100)) : 0;
  return `<div class="m384-summary">
    <div><span>Actividades</span><b>${completed} de ${total}</b><small>reportadas como realizadas</small></div>
    <div><span>Soportes</span><b>${Number(model.evidence?.metrics?.evidence_items || 0)}</b><small>adjuntos al seguimiento</small></div>
    <div><span>Recordatorios</span><b>${Number(model.timing?.metrics?.due || 0) + Number(model.timing?.metrics?.scheduled || 0)}</b><small>operativos activos</small></div>
    <div class="m384-progress-cell"><span>Avance reportado</span><div class="m384-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><i style="width:${percent}%"></i></div><small>${percent}% · no representa probabilidad de éxito jurídico</small></div>
  </div>`;
}

function startMarkup(model) {
  const tasks = model.followup.tasks || [];
  return `<section class="m384-followup-card start" data-m384-followup aria-label="Seguimiento posterior a la entrega">
    <div class="m384-head"><div><span class="m384-eyebrow">Siguiente etapa</span><h2>Organiza lo que ocurre después de recibir tus documentos.</h2><p>Activa un seguimiento guiado para registrar actividades, conservar soportes y crear recordatorios operativos dentro de tu expediente.</p></div><div class="m384-count">${tasks.length}<small>actividades previstas</small></div></div>
    <div class="m384-boundary"><b>Antes de empezar.</b> Este seguimiento no calcula términos legales, no verifica automáticamente que una autoridad haya recibido algo y no cierra tu caso por sí solo.</div>
    <div class="m384-start-actions"><button type="button" class="btn primary" data-m384-action="open-start" data-case-id="${esc(model.caseId)}">Activar seguimiento</button><span>Puedes consultar tus documentos sin activar esta etapa.</span></div>
  </section>`;
}

function activeMarkup(model) {
  const lifecycle = model.followup.lifecycle;
  const readOnly = lifecycle !== 'ACTIVE';
  const title = lifecycle === 'CLOSED' ? 'Seguimiento finalizado' : lifecycle === 'ESCALATED' ? 'Seguimiento escalado' : 'Tus próximos pasos';
  return `<section class="m384-followup-card" data-m384-followup aria-label="Seguimiento posterior a la entrega">
    <div class="m384-head"><div><span class="m384-eyebrow">Después de la entrega</span><h2>${esc(title)}</h2><p>${readOnly ? 'Consulta la trazabilidad disponible de esta etapa.' : 'Avanza actividad por actividad y conserva en el mismo expediente los soportes y referencias operativas que necesites.'}</p></div><span class="m384-state ${readOnly ? 'readonly' : 'active'}">${readOnly ? 'Solo consulta' : 'Seguimiento activo'}</span></div>
    ${summaryMarkup(model)}
    <div class="m384-boundary"><b>Alcance de esta vista.</b> “Completada” significa reportada o registrada en la plataforma. Los soportes no se presumen auténticos ni jurídicamente suficientes. Las fechas y recordatorios son referencias operativas, no términos legales.</div>
    <div class="m384-task-list">${(model.followup.tasks || []).map(task => taskMarkup(model, task)).join('')}</div>
    ${professionalMarkup(model)}
  </section>`;
}

function warningMarkup() {
  return `<section class="m384-followup-card warning" data-m384-followup role="status"><span class="m384-eyebrow">Seguimiento</span><h2>No pudimos consultar esta etapa de forma completa.</h2><p>No cambia el estado de tu expediente. Intenta nuevamente para recuperar la vista actual desde el servidor.</p><button type="button" class="btn secondary" data-m384-action="retry">Reintentar</button></section>`;
}

function mount(model) {
  if (clientCaseId() !== model.caseId) return;
  const existing = document.querySelector('[data-m384-followup]');
  const markup = model.error ? warningMarkup() : (model.followup.lifecycle === 'AVAILABLE' || model.followup.lifecycle === 'NOT_ENROLLED') ? startMarkup(model) : activeMarkup(model);
  if (existing) {
    existing.outerHTML = markup;
    return;
  }
  const delivery = document.querySelector('[data-m383-delivery="available"]');
  const anchor = delivery || document.querySelector('.m353-activation') || document.querySelector('.case-header');
  anchor?.insertAdjacentHTML('afterend', markup);
}

async function optionalGet(path) {
  try { return { value: await api(path), error: false }; }
  catch (error) {
    if (error?.status === 404) return { value: null, error: false };
    return { value: null, error: true };
  }
}

async function loadCase(caseId, force = false) {
  if (!caseId || inFlight.has(caseId)) return;
  if (!force && models.has(caseId)) {
    if (!document.querySelector('[data-m384-followup]')) mount(models.get(caseId));
    return;
  }
  inFlight.add(caseId);
  try {
    const followup = await api(`${FOLLOWUP_PREFIX}/${encodeURIComponent(caseId)}`);
    const model = { caseId, followup, evidence: null, timing: null, disposition: null, error: false };
    if (!['AVAILABLE', 'NOT_ENROLLED'].includes(String(followup.lifecycle || ''))) {
      const [evidence, timing, disposition] = await Promise.all([
        optionalGet(`${EVIDENCE_PREFIX}/${encodeURIComponent(caseId)}`),
        optionalGet(`${TIMING_PREFIX}/${encodeURIComponent(caseId)}`),
        optionalGet(`${DISPOSITION_PREFIX}/${encodeURIComponent(caseId)}`),
      ]);
      model.evidence = evidence.value;
      model.timing = timing.value;
      model.disposition = disposition.value;
      model.error = evidence.error || timing.error || disposition.error;
    }
    models.set(caseId, model);
    mount(model);
  } catch (error) {
    if (error?.status === 404) {
      models.delete(caseId);
      document.querySelector('[data-m384-followup]')?.remove();
    } else {
      const prior = models.get(caseId);
      if (prior) mount({ ...prior, error: true });
      else mount({ caseId, error: true, followup: { lifecycle: 'READ_ONLY', tasks: [], metrics: {} } });
    }
  } finally {
    inFlight.delete(caseId);
  }
}

async function postJson(path, payload) {
  return api(path, { method: 'POST', body: JSON.stringify(payload) });
}

function refresh(caseId) {
  models.delete(caseId);
  return loadCase(caseId, true);
}

function openStart(caseId) {
  openDialog({
    title: 'Activar seguimiento',
    subtitle: 'Esta acción abre la etapa post-entrega del expediente.',
    body: '<div class="m384-dialog-copy"><p>LegalAIZ.it organizará las actividades previstas para este expediente. Tú podrás reportar avances, adjuntar soportes y crear recordatorios operativos.</p><p><b>No se calcularán términos legales ni se cerrará el expediente automáticamente.</b></p></div>',
    actions: `<button type="button" class="btn secondary" data-action="close-dialog">Cancelar</button><button type="button" class="btn primary" data-m384-action="confirm-start" data-case-id="${esc(caseId)}">Sí, activar seguimiento</button>`,
  });
}

function openComplete(caseId, taskId, label) {
  openDialog({
    title: 'Reportar actividad como realizada',
    subtitle: label || 'Actividad de seguimiento',
    body: '<label class="field"><span>Describe brevemente qué hiciste o qué ocurrió</span><textarea id="m384-task-note" rows="4" minlength="10" maxlength="2000" placeholder="Ej.: Presenté la solicitud y conservé la constancia de radicación."></textarea><small>Tu reporte queda trazable, pero no acredita por sí solo recepción externa ni efecto jurídico.</small></label>',
    actions: `<button type="button" class="btn secondary" data-action="close-dialog">Cancelar</button><button type="button" class="btn primary" data-m384-action="confirm-complete" data-case-id="${esc(caseId)}" data-task-id="${esc(taskId)}">Guardar reporte</button>`,
  });
}

function openRecordDate(caseId, taskId) {
  openDialog({
    title: 'Registrar una fecha',
    subtitle: 'Guarda un hecho relevante sin convertirlo en término legal.',
    body: `<div class="m384-dialog-grid"><label class="field"><span>Qué ocurrió</span><select id="m384-event-type"><option value="ACTION_PERFORMED">Realicé una acción</option><option value="AUTHORITY_RECEIPT_REPORTED">Informo una recepción por autoridad</option><option value="NOTICE_RECEIVED">Recibí una notificación</option><option value="RESPONSE_RECEIVED">Recibí una respuesta</option><option value="OTHER_RELEVANT_EVENT">Otro hecho relevante</option></select></label><label class="field"><span>Fecha del hecho</span><input id="m384-event-date" type="date" min="1900-01-01"></label></div><p class="m384-dialog-note">Esta fecha será una referencia registrada por ti. LegalAIZ.it no la interpreta aquí como fecha cierta ante terceros ni como inicio o vencimiento de un término legal.</p>`,
    actions: `<button type="button" class="btn secondary" data-action="close-dialog">Cancelar</button><button type="button" class="btn primary" data-m384-action="confirm-date" data-case-id="${esc(caseId)}" data-task-id="${esc(taskId)}">Registrar fecha</button>`,
  });
}

function openReminder(caseId, taskId) {
  openDialog({
    title: 'Crear recordatorio operativo',
    subtitle: 'Visible dentro del seguimiento de LegalAIZ.it.',
    body: '<label class="field"><span>Fecha del recordatorio</span><input id="m384-reminder-date" type="date"></label><p class="m384-dialog-note">No se enviará una notificación externa automática y esta fecha no es un vencimiento normativo.</p>',
    actions: `<button type="button" class="btn secondary" data-action="close-dialog">Cancelar</button><button type="button" class="btn primary" data-m384-action="confirm-reminder" data-case-id="${esc(caseId)}" data-task-id="${esc(taskId)}">Crear recordatorio</button>`,
  });
}

async function uploadEvidence(caseId, taskId) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = ALLOWED_UPLOAD;
  input.hidden = true;
  document.body.appendChild(input);
  input.addEventListener('change', async () => {
    const file = input.files?.[0];
    input.remove();
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) return toast('El soporte supera el máximo de 10 MB.', 'error');
    const form = new FormData();
    form.append('file', file, file.name);
    try {
      await api(`${EVIDENCE_PREFIX}/${encodeURIComponent(caseId)}/tasks/${encodeURIComponent(taskId)}/upload`, { method: 'POST', body: form });
      toast('Soporte recibido. Su revisión no completa automáticamente la actividad.', 'success');
      await refresh(caseId);
    } catch (error) {
      toast(error.message || 'No fue posible adjuntar el soporte.', 'error');
    }
  }, { once: true });
  input.click();
}

async function handleAction(button) {
  const action = button.dataset.m384Action;
  const caseId = safeId(button.dataset.caseId || clientCaseId());
  const taskId = safeId(button.dataset.taskId);
  if (action === 'retry') return loadCase(clientCaseId(), true);
  if (!caseId || caseId !== clientCaseId()) return;
  if (action === 'open-start') return openStart(caseId);
  if (action === 'complete-task' && taskId) return openComplete(caseId, taskId, button.dataset.taskLabel || '');
  if (action === 'upload' && taskId) return uploadEvidence(caseId, taskId);
  if (action === 'record-date' && taskId) return openRecordDate(caseId, taskId);
  if (action === 'schedule-reminder' && taskId) return openReminder(caseId, taskId);

  button.disabled = true;
  try {
    if (action === 'confirm-start') {
      await postJson(`${FOLLOWUP_PREFIX}/${encodeURIComponent(caseId)}/start`, { confirmation: START_CONFIRMATION });
      closeDialog();
      toast('Seguimiento activado.', 'success');
    } else if (action === 'confirm-complete' && taskId) {
      const note = String(document.getElementById('m384-task-note')?.value || '').trim();
      if (note.length < 10) throw new Error('Describe la actuación con al menos 10 caracteres.');
      await postJson(`${FOLLOWUP_PREFIX}/${encodeURIComponent(caseId)}/tasks/${encodeURIComponent(taskId)}`, { status: 'completed', note });
      closeDialog();
      toast('Actividad reportada como realizada.', 'success');
    } else if (action === 'confirm-date' && taskId) {
      const eventType = String(document.getElementById('m384-event-type')?.value || '');
      const date = String(document.getElementById('m384-event-date')?.value || '');
      if (!date) throw new Error('Selecciona la fecha que deseas registrar.');
      await postJson(`${TIMING_PREFIX}/${encodeURIComponent(caseId)}/tasks/${encodeURIComponent(taskId)}/dates`, { event_type: eventType, date });
      closeDialog();
      toast('Fecha operativa registrada.', 'success');
    } else if (action === 'confirm-reminder' && taskId) {
      const scheduledFor = String(document.getElementById('m384-reminder-date')?.value || '');
      if (!scheduledFor) throw new Error('Selecciona la fecha del recordatorio.');
      await postJson(`${TIMING_PREFIX}/${encodeURIComponent(caseId)}/tasks/${encodeURIComponent(taskId)}/reminders`, { scheduled_for: scheduledFor });
      closeDialog();
      toast('Recordatorio operativo creado.', 'success');
    } else if (action === 'ack-reminder') {
      const reminderId = safeId(button.dataset.reminderId);
      if (!reminderId) return;
      await postJson(`${TIMING_PREFIX}/${encodeURIComponent(caseId)}/reminders/${encodeURIComponent(reminderId)}/acknowledge`, {});
      toast('Recordatorio marcado como atendido.', 'success');
    } else if (action === 'cancel-reminder') {
      const reminderId = safeId(button.dataset.reminderId);
      if (!reminderId) return;
      await postJson(`${TIMING_PREFIX}/${encodeURIComponent(caseId)}/reminders/${encodeURIComponent(reminderId)}/cancel`, {});
      toast('Recordatorio cancelado.', 'success');
    } else {
      return;
    }
    await refresh(caseId);
  } catch (error) {
    toast(error.message || 'No fue posible actualizar el seguimiento.', 'error');
  } finally {
    if (button.isConnected) button.disabled = false;
  }
}

document.addEventListener('click', event => {
  const button = event.target.closest('[data-m384-action]');
  if (!button) return;
  event.preventDefault();
  handleAction(button);
});

function schedule() {
  if (scheduled) return;
  scheduled = true;
  window.setTimeout(() => {
    scheduled = false;
    const caseId = clientCaseId();
    if (caseId) loadCase(caseId);
  }, 80);
}

window.addEventListener('hashchange', schedule);
const app = document.getElementById('app');
if (app) new MutationObserver(schedule).observe(app, { childList: true, subtree: true });
schedule();
