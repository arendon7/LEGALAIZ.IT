import { api, dateText, esc, state } from '../core.js';

const DELIVERY_PREFIX = '/api/m36/delivery/cases';
const cache = new Map();
const unavailable = new Set();
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

function replaceExact(element, from, to) {
  if (element && element.textContent.trim() === from) element.textContent = to;
}

function polishActivationCopy() {
  const card = document.querySelector('.m353-activation');
  if (!card) return;
  const pending = card.classList.contains('pending');
  replaceExact(card.querySelector('.m353-status'), pending ? 'Preparación documental pendiente' : 'Expediente activado', pending ? 'Preparación documental en curso' : 'Expediente listo para continuar');
  const title = card.querySelector('.m353-activation-head h2');
  const intro = card.querySelector('.m353-activation-head p');
  if (title) title.textContent = pending ? 'Tu expediente ya está creado y la preparación documental sigue en curso.' : 'Tu solución ya está vinculada a este expediente.';
  if (intro) intro.textContent = pending ? 'No necesitas iniciar otra compra ni crear un expediente nuevo. Cuando la preparación termine, aquí verás el siguiente paso.' : 'Aquí puedes consultar el nivel de servicio, el estado documental y el siguiente paso. La revisión profesional y la entrega final se muestran por separado.';

  card.querySelectorAll('.m353-purchase-grid > div').forEach(cell => {
    const label = cell.querySelector('small');
    if (!label) return;
    const raw = label.textContent.trim();
    if (raw === 'Total sandbox') {
      label.textContent = 'Valor en entorno de prueba';
      replaceExact(cell.querySelector('span'), 'Sin cargo real', 'Sin cobro real');
    } else if (raw === 'Orden') {
      label.textContent = 'Referencia de servicio';
    } else if (raw === 'Comprobante sandbox') {
      label.textContent = 'Comprobante de prueba';
    }
  });

  card.querySelectorAll('.m353-trace-row span').forEach(item => {
    const raw = item.textContent.trim();
    if (raw === 'Pago sandbox verificado') item.textContent = 'Operación de prueba validada';
    else if (raw === 'Trazabilidad de orden y expediente verificada') item.textContent = 'Vinculación con tu expediente confirmada';
    else if (raw.startsWith('Journey:')) item.textContent = `Estado del proceso: ${raw.slice('Journey:'.length).trim().replaceAll('_', ' ').toLowerCase()}`;
  });
}

function polishCaseCopy() {
  const header = document.querySelector('.case-header');
  if (!header) return;
  replaceExact(header.querySelector('.page-actions a.btn.primary'), 'Exportar expediente', 'Descargar copia del expediente');

  const documentsHeading = [...document.querySelectorAll('.card-header h2')].find(node => node.textContent.trim() === 'Documentos del expediente');
  if (documentsHeading) {
    const paragraph = documentsHeading.parentElement?.querySelector('p');
    if (paragraph) paragraph.textContent = 'Aquí encontrarás borradores, versiones revisadas y documentos disponibles de este expediente.';
    const action = documentsHeading.closest('.card-header')?.querySelector('[data-route="/documentos"]');
    replaceExact(action, 'Ver biblioteca', 'Ver todos mis documentos');
  }
}

function safeDownloadUrl(payload, caseId) {
  const value = String(payload?.download_url || '');
  const expected = `${DELIVERY_PREFIX}/${encodeURIComponent(caseId)}/download`;
  return value === expected ? value : '';
}

function deliveryMarkup(payload, caseId) {
  const count = Math.max(0, Math.min(100, Number(payload.document_count) || 0));
  const rawDate = payload.delivered_at || payload.prepared_at || '';
  const date = rawDate ? dateText(rawDate) : '';
  const downloadUrl = safeDownloadUrl(payload, caseId);
  const governance = payload.governance || {};
  const approved = payload.state === 'DELIVERED_IN_APP' && governance.dual_human_approval_preserved === true;
  if (!approved || !downloadUrl || count < 1) return '';
  const priorRequests = Math.max(0, Math.min(999, Number(payload.download_requests) || 0));
  const accessText = priorRequests
    ? `Se han registrado ${priorRequests} ${priorRequests === 1 ? 'solicitud de descarga' : 'solicitudes de descarga'} desde este expediente.`
    : 'Aún no se ha registrado una solicitud de descarga desde este expediente.';
  return `<section class="m383-delivery-card" data-m383-delivery="available" aria-label="Entrega final de documentos">
    <div class="m383-delivery-head">
      <div><span class="m383-status">Documentos finales disponibles</span><h2>Tu solución revisada ya está disponible para descarga.</h2><p>Incluye ${count} ${count === 1 ? 'documento liberado' : 'documentos liberados'} después de revisión jurídica y control de calidad independiente.</p></div>
      <div class="m383-delivery-mark" aria-hidden="true">✓</div>
    </div>
    <div class="m383-delivery-steps" aria-label="Controles completados">
      <div><span>1</span><b>Revisión jurídica</b><small>Completada sobre la versión liberada.</small></div>
      <div><span>2</span><b>Control de calidad</b><small>Completado por un control independiente.</small></div>
      <div><span>3</span><b>Puesta a disposición</b><small>Disponible en tu expediente autenticado${date ? ` desde ${esc(date)}` : ''}.</small></div>
    </div>
    <div class="m383-delivery-actions">
      <div><b>Paquete final del expediente</b><span>Contiene únicamente las copias documentales liberadas para esta entrega. ${esc(accessText)}</span></div>
      <div class="m383-button-row"><button type="button" class="btn secondary" data-action="case-tab" data-tab="documentos" data-case-id="${esc(caseId)}">Ver documentos</button><a class="btn primary" href="${esc(downloadUrl)}">Descargar paquete final</a></div>
    </div>
    <div class="m383-delivery-boundary"><b>Qué significa “disponible”.</b> La puesta a disposición y una solicitud de descarga no acreditan por sí solas lectura, recepción por un canal externo ni un resultado jurídico. Conserva el paquete y las constancias de cualquier radicación o envío que realices.</div>
  </section>`;
}

function deliveryWarning() {
  return `<section class="m383-delivery-warning" data-m383-delivery="warning" role="status" aria-live="polite"><span>Entrega final por verificar</span><h2>No mostramos un botón de descarga hasta confirmar la entrega.</h2><p>Tu expediente sigue disponible. Cuando podamos verificar nuevamente la puesta a disposición de las copias liberadas, la descarga aparecerá aquí.</p></section>`;
}

function mountDelivery(payload, caseId) {
  if (clientCaseId() !== caseId || document.querySelector('[data-m383-delivery]')) return;
  const markup = deliveryMarkup(payload, caseId);
  if (!markup) return mountWarning(caseId);
  const anchor = document.querySelector('.m353-activation') || document.querySelector('.case-header');
  anchor?.insertAdjacentHTML('afterend', markup);
}

function mountWarning(caseId) {
  if (clientCaseId() !== caseId || document.querySelector('[data-m383-delivery]')) return;
  const anchor = document.querySelector('.m353-activation') || document.querySelector('.case-header');
  anchor?.insertAdjacentHTML('afterend', deliveryWarning());
}

async function enhanceDelivery() {
  const caseId = clientCaseId();
  if (!caseId) return;
  polishActivationCopy();
  polishCaseCopy();
  if (document.querySelector('[data-m383-delivery]')) return;
  if (cache.has(caseId)) return mountDelivery(cache.get(caseId), caseId);
  if (unavailable.has(caseId) || inFlight.has(caseId)) return;
  inFlight.add(caseId);
  try {
    const payload = await api(`${DELIVERY_PREFIX}/${encodeURIComponent(caseId)}`);
    cache.set(caseId, payload);
    mountDelivery(payload, caseId);
  } catch (error) {
    const code = String(error?.data?.code || '');
    if (error?.status === 404 && code === 'DELIVERY_NOT_AVAILABLE') unavailable.add(caseId);
    else if (error?.status === 404) unavailable.add(caseId);
    else mountWarning(caseId);
  } finally {
    inFlight.delete(caseId);
  }
}

function schedule() {
  if (scheduled) return;
  scheduled = true;
  window.setTimeout(() => {
    scheduled = false;
    enhanceDelivery();
  }, 60);
}

window.addEventListener('hashchange', schedule);
const app = document.getElementById('app');
if (app) new MutationObserver(schedule).observe(app, { childList: true, subtree: true });
schedule();
