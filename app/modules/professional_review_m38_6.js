import { currentPath, state } from '../core.js';

const ROUTE = '/mesa-juridica';

const STATUS_BY_LABEL = Object.freeze({
  'Sin revisión': 'draft',
  'Pendiente jurídica': 'legal_pending',
  'Pendiente QA': 'qa_pending',
  'Requiere ajustes': 'changes_required',
  'Rechazado': 'rejected',
  'Hallazgos pendientes': 'findings_pending',
  'Cadena de auditoría inválida': 'audit_invalid',
  'Listo para liberar': 'ready_to_release',
  'Liberado': 'released',
});

const DECISION_CUES = Object.freeze({
  draft: {
    tone: 'neutral', eyebrow: 'Siguiente control profesional', title: 'Preparar la revisión del documento',
    detail: 'Confirma que la revisión vigente sea la que debe someterse a control jurídico y QA.',
  },
  legal_pending: {
    tone: 'warning', eyebrow: 'Decisión pendiente', title: 'Revisión jurídica',
    detail: 'Revisa el contenido y los hallazgos abiertos antes de aprobar o rechazar la revisión vigente.',
  },
  qa_pending: {
    tone: 'blue', eyebrow: 'Decisión pendiente', title: 'Control QA independiente',
    detail: 'La revisión jurídica ya avanzó. Corresponde verificar integridad, consistencia y calidad antes de liberar.',
  },
  changes_required: {
    tone: 'danger', eyebrow: 'Bloqueo de aprobación', title: 'Hay ajustes requeridos',
    detail: 'No debe aprobarse ni liberarse hasta registrar una revisión que atienda los ajustes pendientes.',
  },
  findings_pending: {
    tone: 'danger', eyebrow: 'Bloqueo de aprobación', title: 'Hay hallazgos abiertos',
    detail: 'Los hallazgos deben resolverse de forma trazable antes de continuar con la aprobación.',
  },
  audit_invalid: {
    tone: 'danger', eyebrow: 'Bloqueo de integridad', title: 'Validar la cadena de auditoría',
    detail: 'La integridad de la trazabilidad debe restablecerse antes de cualquier liberación.',
  },
  ready_to_release: {
    tone: 'success', eyebrow: 'Siguiente control profesional', title: 'Liberar la revisión aprobada',
    detail: 'Jurídica y QA están conformes. Verifica la huella SHA-256 visible antes de liberar el archivo exacto.',
  },
  released: {
    tone: 'success', eyebrow: 'Estado de entrega', title: 'Documento liberado',
    detail: 'La versión liberada permanece vinculada a la revisión y huella SHA-256 aprobadas.',
  },
  rejected: {
    tone: 'danger', eyebrow: 'Decisión registrada', title: 'Revisión rechazada',
    detail: 'Consulta el motivo registrado y genera o selecciona una nueva revisión antes de reiniciar la aprobación.',
  },
});

export function professionalDecisionCue(status = 'draft') {
  return DECISION_CUES[status] || DECISION_CUES.draft;
}

function professional() {
  return state.user && ['specialist', 'admin'].includes(state.user.role);
}

function cueMarkup(status, scope = 'list') {
  const cue = professionalDecisionCue(status);
  return `<section class="m386-decision-cue tone-${cue.tone}" data-m386-cue="${scope}">
    <div><span class="eyebrow">${cue.eyebrow}</span><h3>${cue.title}</h3></div><p>${cue.detail}</p>
  </section>`;
}

function statusFromDetail() {
  const label = document.querySelector('.m325-detail-hero .m325-status')?.textContent?.trim() || '';
  return STATUS_BY_LABEL[label] || 'draft';
}

function replaceText(selector, expected, replacement) {
  document.querySelectorAll(selector).forEach(node => {
    if (node.dataset.m386Copy === '1' || (node.textContent || '').trim() !== expected) return;
    node.textContent = replacement;
    node.dataset.m386Copy = '1';
  });
}

function replaceLeadingText(selector, expected, replacement) {
  document.querySelectorAll(selector).forEach(node => {
    if (node.dataset.m386Copy === '1') return;
    const textNode = [...node.childNodes].find(child => child.nodeType === Node.TEXT_NODE && (child.textContent || '').trim() === expected);
    if (!textNode) return;
    textNode.textContent = replacement;
    node.dataset.m386Copy = '1';
  });
}

function enhanceList() {
  const hero = document.querySelector('.m325-hero');
  if (hero && hero.dataset.m386Hierarchy !== '1') {
    const eyebrow = hero.querySelector('.eyebrow');
    const copy = hero.querySelector('p');
    if (eyebrow) eyebrow.textContent = 'Revisión profesional por documento';
    if (copy) copy.textContent = 'Identifica primero la decisión pendiente o el bloqueo. Después verifica la revisión, los hallazgos, las aprobaciones y la huella SHA-256 del archivo exacto.';
    hero.dataset.m386Hierarchy = '1';
  }
  document.querySelectorAll('.m325-case-card').forEach(card => {
    if (!card.querySelector('[data-m386-cue="list"]')) card.querySelector('.m325-case-top')?.insertAdjacentHTML('afterend', cueMarkup(card.dataset.status || 'draft', 'list'));
    card.querySelector('.m325-case-facts')?.classList.add('m386-technical-facts');
  });
  replaceText('.m325-case-facts small', 'Hash vigente', 'Huella SHA-256');
}

function enhanceDetail() {
  const hero = document.querySelector('.m325-detail-hero');
  if (!hero) return;
  if (!document.querySelector('[data-m386-cue="detail"]')) hero.insertAdjacentHTML('afterend', cueMarkup(statusFromDetail(), 'detail'));
  document.querySelector('.m325-integrity')?.classList.add('m386-technical-integrity');
  replaceText('.m325-card .eyebrow', 'Visor por revisión', 'Documento y revisión vigente');
}

function relabelSlaBadges() {
  const labels = {
    'sla-overdue': 'Objetivo interno vencido',
    'sla-at_risk': 'Objetivo interno próximo',
    'sla-in_time': 'Dentro del objetivo interno',
    'sla-not_scheduled': 'Sin tiempo objetivo',
    'sla-closed': 'Gestión cerrada',
  };
  document.querySelectorAll('.m326-badge').forEach(badge => {
    if (badge.dataset.m386Operational === '1') return;
    const cls = Object.keys(labels).find(name => badge.classList.contains(name));
    if (!cls) return;
    badge.textContent = labels[cls];
    badge.dataset.m386Operational = '1';
  });
}

function enhanceOperations() {
  const portfolio = document.querySelector('.m326-portfolio-head');
  if (portfolio && portfolio.dataset.m386Hierarchy !== '1') {
    const eyebrow = portfolio.querySelector('.eyebrow');
    const title = portfolio.querySelector('h2');
    if (eyebrow) eyebrow.textContent = 'Gestión profesional';
    if (title) title.textContent = 'Cobertura, responsables y tiempos internos';
    portfolio.dataset.m386Hierarchy = '1';
  }
  replaceText('.m326-kpis small', 'SLA vencidos', 'Objetivos internos vencidos');
  replaceText('.m326-kpis small', 'En riesgo', 'Objetivos internos próximos');

  const operations = document.querySelector('.m326-operations-card');
  if (operations && operations.dataset.m386Hierarchy !== '1') {
    const eyebrow = operations.querySelector('.card-header .eyebrow');
    const title = operations.querySelector('.card-header h2');
    const copy = operations.querySelector('.card-header p');
    if (eyebrow) eyebrow.textContent = 'Gestión interna de la revisión';
    if (title) title.textContent = 'Responsables y tiempo objetivo';
    if (copy) copy.textContent = 'Estos tiempos son metas internas de gestión. No son términos legales y no calculan prescripción, caducidad ni términos procesales o administrativos aplicables.';
    operations.dataset.m386Hierarchy = '1';
  }

  replaceLeadingText('.m326-form label', 'Horas de SLA', 'Horas objetivo');
  replaceLeadingText('.m326-form label', 'Fecha objetivo', 'Fecha objetivo interna');
  replaceText('.m326-form button', 'Definir vencimiento', 'Definir objetivo interno');
  relabelSlaBadges();

  document.querySelectorAll('.m326-status-row span:not(.m326-badge)').forEach(node => {
    if (node.dataset.m386Operational === '1') return;
    const text = (node.textContent || '').trim();
    if (/vencidas$/i.test(text)) node.textContent = text.replace(/vencidas$/i, 'fuera del objetivo interno');
    node.dataset.m386Operational = '1';
  });
}

export function applyProfessionalReviewClarity() {
  if (!professional() || !currentPath().startsWith(ROUTE)) return;
  enhanceList();
  enhanceDetail();
  enhanceOperations();
}

let scheduled = false;
function scheduleApply() {
  if (scheduled) return;
  scheduled = true;
  queueMicrotask(() => { scheduled = false; applyProfessionalReviewClarity(); });
}

const observer = new MutationObserver(scheduleApply);
observer.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', scheduleApply);
window.addEventListener('popstate', scheduleApply);
scheduleApply();
