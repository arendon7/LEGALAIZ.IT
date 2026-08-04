import { accountOptions, api, app, contractualProductCodes, currentPath, dateText, dialogRoot, esc, go, humanize, icons, initials, money, openDialog, playbookProductCodes, riskClass, riskLabels, roleLabels, state, toast } from './core.js';
import { m24CandidateLibraryPage, navigationGroups, quickAction, routeContext } from './ux_m21.js';
import { answeredValue as answeredValueM247, createGuidedExperience, paginateWizardQuestions, questionPageWeight, shouldShow } from './modules/ux_m24_7.js';
import { createPilotExperience } from './modules/pilot_m24_8.js';
import { createProfessionalExperience } from './modules/professional_m24_9.js';
import { createReadinessExperience } from './modules/readiness_m25_0.js';
import { createGoldPublicExperience } from './modules/gold_m26_2.js';
import { createPublicBrandExperience, publicProductCodeBySlug, publicProductRoute, setPublicTitle } from './modules/public_m29_1.js';
import { createDemoRealityExperience } from './modules/demo_reality_m31_7.js';
import { createCaseDemoExperience } from './modules/case_demo_m31_8.js';
import { caseCard, caseFilters, clientCaseOverview, clientFollowUpPanel, clientReviewPanel, emptyState as internalEmptyState, filterCases, friendlyCaseState, friendlyDocumentState, tabsForCase, wizardGuidance } from './modules/internal_m29_2.js';
import { buildNotifications, dismissOnboarding, helpCenterPage as m293HelpCenterPage, markAllNotificationsRead, markNotificationRead, markOnboardingStep, notificationsDialogBody, notificationsPage as m293NotificationsPage, onboardingDialogBody, onboardingPanel, resetOnboarding, sidebarJourneySummary, unreadNotificationCount } from './modules/navigation_m29_3.js';
import { accessibilityDialogBody, accessibilityPage as m294AccessibilityPage, announceRoute, applyUiPreferences, contextualHelpDialogBody, productJourneySection, searchDialogBody, searchResultsHtml, setUiPreference, wizardContextCard, workspaceSearch } from './modules/experience_m29_4.js'; import { createConversionExperience } from './modules/conversion_m29_5.js'; import { createPilotCenterExperience } from './modules/pilot_center_m30_1.js'; import { createParticipantExperience } from './modules/participant_m30_2.js'; import { createPreproductionExperience } from './modules/preproduction_m31_1.js';
const m317DemoReality = createDemoRealityExperience({ app, api, esc, shell, pageHeader, toast });
const m318CaseDemo = createCaseDemoExperience({ app, api, esc, shell, pageHeader, toast, state });
const m291Public = createPublicBrandExperience({ app, esc }); const m295Experience = createConversionExperience({ app, esc, api, go, toast, shell, pageHeader, state, getPath:currentPath }); const m301Pilot = createPilotCenterExperience({ shell, pageHeader }); const m302Participant = createParticipantExperience({ shell, pageHeader }); const m311Preproduction = createPreproductionExperience({ shell, pageHeader });
function loginPage() {
  const deployment = state.config?.deployment || {};
  const localDemo = (deployment.profile || 'local') === 'local' && deployment.app_env !== 'pilot-local';
  const accountField = localDemo
    ? `<div class="field"><label for="login-email">Perfil de demostración</label><select id="login-email" class="select">${accountOptions.map(([v,l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('')}</select><span class="field-hint">Cada perfil muestra una experiencia y permisos diferentes.</span></div>`
    : `<div class="field"><label for="login-email">Correo electrónico</label><input id="login-email" class="input" type="email" autocomplete="username" required></div>`;
  setPublicTitle('Ingresar');
  app.innerHTML = `<main class="login-shell m29-login-shell" id="main-content">
    <section class="login-story m29-login-story" aria-label="Presentación de LegalAIZ.it">
      <button class="m29-login-logo" type="button" data-action="go" data-route="/" aria-label="Volver al inicio"><img src="/assets/logo-legalaizit-web.png" alt="LegalAIZ.it"></button>
      <div class="login-copy"><span class="eyebrow">Tu espacio jurídico</span><h1>Continúa tu caso con <span>claridad y control.</span></h1><p>Retoma formularios, consulta expedientes, revisa documentos y conoce el siguiente paso sin perder el contexto.</p><div class="m29-login-benefits"><span>✓ Avance guardado</span><span>✓ Documentos y versiones</span><span>✓ Revisión según riesgo</span></div></div>
      <img class="m29-login-visual" src="/assets/brand-visuals/people-journey.svg" alt="Persona avanzando dentro de su expediente jurídico">
    </section>
    <section class="login-panel"><div class="login-card"><button class="login-back-link" type="button" data-action="go" data-route="/">← Volver al sitio público</button><span class="eyebrow">Acceso seguro</span><h2>Ingresa a LegalAIZ.it</h2><p class="lead">${localDemo ? 'Selecciona un perfil para revisar la plataforma desde la perspectiva de un cliente, especialista o administrador.' : 'Usa la cuenta autorizada para continuar tus procesos y documentos.'}</p><form id="login-form">${accountField}<div class="field"><label for="login-password">Contraseña</label><input id="login-password" class="input" type="password" autocomplete="current-password" required></div><div class="field"><label for="login-mfa">Código de verificación <span class="field-hint">cuando esté habilitado</span></label><input id="login-mfa" class="input" inputmode="numeric" autocomplete="one-time-code" placeholder="000000"></div><button class="btn primary btn-block" type="submit">Ingresar a mi espacio</button></form><div class="demo-note"><b>${localDemo ? 'Entorno local de demostración.' : 'Acceso institucional.'}</b> ${localDemo ? 'Utiliza únicamente información ficticia. ' : ''}Los resultados se gestionan como borradores controlados y pueden requerir revisión profesional antes de su uso externo.</div></div></section>
  </main>`;
  document.getElementById('login-form').addEventListener('submit', login);
}
function mfaEnrollmentPage() {
  app.innerHTML = `<main class="login-shell" id="main-content">
    <section class="login-story" aria-label="Protección de la cuenta">
      <div class="login-brand"><img src="/assets/logo-legalaizit-web.png" alt="LegalAIZ.it"></div>
      <div class="login-copy"><span class="eyebrow">Segundo factor obligatorio</span><h1>Protege el acceso a información jurídica sensible.</h1><p>Los perfiles de administración y especialistas deben completar MFA antes de acceder a expedientes, documentos o funciones de gobierno.</p></div>
    </section>
    <section class="login-panel"><div class="login-card"><span class="eyebrow">Inscripción MFA</span><h2>Configura tu aplicación autenticadora</h2><p class="lead">Genera el secreto, agrégalo a tu aplicación TOTP y confirma un código de seis dígitos.</p><div id="mfa-enroll-content"><button class="btn primary" id="mfa-start" type="button">Generar secreto MFA</button></div><button class="btn ghost" id="mfa-logout" type="button">Cerrar sesión</button></div></section>
  </main>`;
  document.getElementById('mfa-start').addEventListener('click', startMfaEnrollment);
  document.getElementById('mfa-logout').addEventListener('click', logout);
}
async function startMfaEnrollment() {
  const button = document.getElementById('mfa-start'); button.disabled = true;
  try {
    const enrollment = await api('/api/auth/mfa/enroll', { method: 'POST', body: '{}' });
    document.getElementById('mfa-enroll-content').innerHTML = `<div class="demo-note"><b>Secreto TOTP</b><br><code class="mfa-secret">${esc(enrollment.secret)}</code><br><span>Guárdalo únicamente en tu aplicación autenticadora. No lo compartas.</span></div><form id="mfa-confirm-form"><div class="field"><label for="mfa-confirm-code">Código de verificación</label><input id="mfa-confirm-code" class="input" inputmode="numeric" autocomplete="one-time-code" maxlength="8" required></div><button class="btn primary" type="submit">Activar MFA y continuar</button></form>`;
    document.getElementById('mfa-confirm-form').addEventListener('submit', confirmMfaEnrollment);
    document.getElementById('mfa-confirm-code').focus();
  } catch (error) { toast(error.message, 'danger'); button.disabled = false; }
}
async function confirmMfaEnrollment(event) {
  event.preventDefault(); const button = event.submitter; button.disabled = true;
  try {
    const result = await api('/api/auth/mfa/confirm', { method: 'POST', body: JSON.stringify({ code: document.getElementById('mfa-confirm-code').value }) });
    state.mfaEnrollmentRequired = false;
    openDialog({ title: 'MFA activado', subtitle: 'Guarda los códigos de recuperación fuera de este equipo.', body: `<div class="recovery-grid">${(result.recovery_codes || []).map(code => `<code>${esc(code)}</code>`).join('')}</div>`, actions: '<button class="btn primary" id="mfa-finish" type="button">Continuar</button>' });
    setTimeout(() => document.getElementById('mfa-finish')?.addEventListener('click', async () => { window.legalaiCloseDialog(); await preload(); toast('MFA activado.'); go('/'); }), 20);
  } catch (error) { toast(error.message, 'danger'); button.disabled = false; }
}
async function login(event) {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true; button.textContent = 'Ingresando…';
  try {
    const result = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: document.getElementById('login-email').value,
        password: document.getElementById('login-password').value,
        mfa_code: document.getElementById('login-mfa').value,
      })
    });
    state.user = result.user; state.csrf = result.csrf_token; state.mfaEnrollmentRequired = Boolean(result.mfa_enrollment_required);
    if (state.mfaEnrollmentRequired) { toast('Completa la inscripción MFA para continuar.'); return mfaEnrollmentPage(); }
    await preload();
    toast('Sesión iniciada.'); go('/');
  } catch (error) {
    toast(error.message, 'danger');
    button.disabled = false; button.textContent = 'Ingresar';
  }
}
async function logout() {
  try { await api('/api/auth/logout', { method: 'POST', body: '{}' }); } catch {}
  state.user = null; state.csrf = null; state.products = []; state.cases = []; state.documents = [];
  go('/login');
}
window.legalaiLogout = logout;
function isActive(path) {
  const cur = currentPath();
  if (path === '/') return cur === '/';
  return cur === path || cur.startsWith(`${path}/`);
}
function shell(content) {
  const navGroups = navigationGroups();
  const approved = state.approval?.product_count || 11;
  const controlled = Boolean(state.approval?.professional_publication_authorized);
  const [contextGroup, contextPage] = routeContext();
  const action = quickAction();
  const unreadNotifications = unreadNotificationCount(state.user, state.cases, state.documents);
  const journeySummary = sidebarJourneySummary(state.user, state.cases, state.documents);
  return `<div class="app-shell">
    <header class="topbar">
      <div class="topbar-left"><button class="icon-btn mobile-nav-btn" aria-label="Abrir navegación" aria-expanded="${state.mobileNav}" aria-controls="primary-sidebar" data-action="toggle-nav">☰</button><button class="brand-button" aria-label="Ir al inicio" data-action="go" data-route="/"><img src="/assets/logo-legalaizit-web.png" alt="LegalAIZ.it"></button><div class="workspace-context"><span>${esc(contextGroup)}</span><b>${esc(contextPage)}</b></div></div>
      <div class="topbar-actions">
        <button class="search-trigger" aria-label="Buscar casos, documentos o soluciones" data-action="search-dialog"><span>${icons.search}</span><span>Buscar</span><kbd>⌘ K</kbd></button>
        <button class="m293-topbar-icon m293-help-action" aria-label="Abrir ayuda contextual" data-action="context-help-dialog"><span>${icons.help}</span></button><button class="m293-topbar-icon m294-accessibility-action" aria-label="Configurar accesibilidad" data-action="accessibility-dialog"><span>Aa</span></button>
        <button class="m293-topbar-icon" aria-label="Abrir notificaciones" data-action="notifications-dialog"><span>${icons.bell}</span>${unreadNotifications?`<b>${Math.min(unreadNotifications,9)}</b>`:''}</button>
        <button class="account-menu" data-action="account-dialog"><span class="avatar">${esc(initials(state.user.name))}</span><span class="account-copy"><b>${esc(state.user.name)}</b><span>${esc(roleLabels[state.user.role] || state.user.role)}</span></span><span aria-hidden="true">⌄</span></button>
      </div>
    </header>
    <aside id="primary-sidebar" class="sidebar ${state.mobileNav ? 'open' : ''}" aria-label="Navegación principal">
      <div class="sidebar-brand-copy"><b>Tu solución legal</b><span>impulsada por IA y expertos</span></div>
      <button class="sidebar-primary" data-action="go" data-route="${esc(action.route)}"><span>${action.icon}</span><b>${esc(action.label)}</b></button>
      <nav class="side-nav" aria-label="Navegación por áreas">${navGroups.map(group => `<section class="nav-group"><div class="nav-label">${esc(group.label)}</div>${group.items.map(item => `<a class="nav-link ${item.primary ? 'nav-link-primary' : ''} ${isActive(item.path) ? 'active' : ''}" href="#${item.path}" data-action="close-mobile-nav" ${isActive(item.path) ? 'aria-current="page"' : ''}><span class="nav-icon">${item.icon}</span><span>${esc(item.label)}</span></a>`).join('')}</section>`).join('')}</nav>
      <div class="sidebar-bottom">
        ${journeySummary}
        <div class="approval-mini ${controlled ? 'approved' : 'pending'}"><span class="approval-dot"></span><div><b>${approved}/11 productos revalidados</b><p>${controlled ? 'Contenido vigente para uso profesional controlado.' : 'Existen compuertas pendientes.'}</p></div></div>
        <button class="support-link" data-action="go" data-route="/ayuda"><span>?</span><div><b>Centro de ayuda</b><small>Guías y alcance</small></div></button>
      </div>
    </aside>
    <main class="content" id="main-content" tabindex="-1">${content}</main>
  </div>`;
}
window.legalaiToggleNav = () => { state.mobileNav = !state.mobileNav; router(); };
window.legalaiCloseMobileNav = () => { state.mobileNav = false; };
window.legalaiAccountDialog = () => openDialog({
  title: state.user.name,
  subtitle: roleLabels[state.user.role] || state.user.role,
  body: `<div class="fact-grid"><div class="fact"><small>Correo</small><span>${esc(state.user.email)}</span></div><div class="fact"><small>Especialidad</small><span>${esc(state.user.specialty || 'No registrada')}</span></div></div><div class="demo-note mt-18">El entorno mantiene controles de acceso por rol. No utilices datos personales reales durante esta revisión.</div>`,
  actions: `<button class="btn secondary" data-action="close-dialog">Cerrar</button><button class="btn danger" data-action="logout">Cerrar sesión</button>`
});
window.legalaiHelpDialog = () => openDialog({
  title: 'Ayuda de esta pantalla',
  subtitle: 'Orientación breve según el lugar en el que estás.',
  body: contextualHelpDialogBody(currentPath(), state.user, state.wizard),
  actions: `<button class="btn secondary" data-action="go-close-dialog" data-route="/ayuda">Abrir centro de ayuda</button><button class="btn primary" data-action="close-dialog">Entendido</button>`
});
window.legalaiAccessibilityDialog = () => openDialog({
  title: 'Accesibilidad y lectura',
  subtitle: 'Adapta la interfaz en este navegador.',
  body: accessibilityDialogBody(),
  actions: `<button class="btn secondary" data-action="go-close-dialog" data-route="/accesibilidad">Ver todas las opciones</button><button class="btn primary" data-action="close-dialog">Cerrar</button>`
});
window.legalaiNotificationsDialog = () => openDialog({
  title: 'Notificaciones',
  subtitle: 'Cambios relevantes y acciones pendientes.',
  body: notificationsDialogBody(state.user, state.cases, state.documents),
  actions: `<button class="btn secondary" data-action="notifications-read-all">Marcar todas como leídas</button><button class="btn primary" data-action="go-close-dialog" data-route="/notificaciones">Ver todas</button>`
});
window.legalaiOnboardingDialog = () => openDialog({
  title: 'Tu recorrido inicial',
  subtitle: 'Una guía breve adaptada a tu rol.',
  body: onboardingDialogBody(state.user, state.cases, state.documents),
  actions: `<button class="btn secondary" data-action="onboarding-reset">Reiniciar guía</button><button class="btn primary" data-action="close-dialog">Cerrar</button>`
});
window.legalaiSearchDialog = () => openDialog({
  title: 'Buscar en tu espacio jurídico',
  subtitle: 'Describe lo que necesitas con tus propias palabras.',
  body: searchDialogBody(state.globalSearchQuery),
  actions: `<button class="btn secondary" data-action="close-dialog">Cerrar</button>`
});
document.addEventListener('submit', async event => {
  if (event.target?.id !== 'global-search-form') return;
  event.preventDefault();
  const input = document.getElementById('global-search-input');
  const output = document.getElementById('global-search-results');
  const query = String(input?.value || '').trim();
  state.globalSearchQuery = query;
  if (query.length < 2) { output.innerHTML = '<p class="muted">Escribe al menos dos caracteres.</p>'; return; }
  output.innerHTML = '<div class="loading-inline">Buscando…</div>';
  try {
    const remote = await api(`/api/search?q=${encodeURIComponent(query)}`).catch(() => ({}));
    const rows = workspaceSearch(query, state.products, state.cases, state.documents, Array.isArray(remote.results) ? remote.results : []);
    output.innerHTML = searchResultsHtml(rows, query);
  } catch (error) { output.innerHTML = `<div class="legal-notice danger">${esc(error.message)}</div>`; }
});
document.addEventListener('click', event => {
  const trigger = event.target.closest('[data-action]');
  if (!trigger) return;
  const action = trigger.dataset.action;
  if (action === 'dialog-backdrop' && event.target !== trigger) return;
  const actionsThatPreventDefault = new Set([
    'dialog-backdrop', 'close-dialog', 'toggle-nav', 'go', 'search-dialog',
    'account-dialog', 'help-dialog', 'context-help-dialog', 'accessibility-dialog', 'accessibility-toggle', 'search-suggestion', 'notifications-dialog', 'notification-open', 'notifications-read-all', 'onboarding-open', 'onboarding-dismiss', 'onboarding-go', 'onboarding-reset', 'logout', 'go-close-dialog', 'query-go',
    'solution-filter', 'reset-solution-filters', 'case-filter', 'choose-need', 'wizard-previous',
    'wizard-save', 'wizard-next', 'wizard-jump', 'wizard-review-edit', 'wizard-review-confirm', 'toggle-help', 'back-to-wizard',
    'create-case', 'analyze-intake', 'select-service-level', 'start-checkout', 'pay-checkout',
    'case-tab', 'journey-transition', 'follow-up-update', 'pilot-enroll', 'pilot-withdraw', 'pilot-feedback', 'pilot-incident', 'pilot-manual', 'pilot-control', 'pilot-triage',
    'professional-invite', 'professional-invitation-accept', 'professional-verify', 'professional-availability', 'professional-offer', 'professional-assignment-decision', 'professional-conflict-resolve', 'professional-assignment-complete', 'reload'
  ]);
  if (actionsThatPreventDefault.has(action)) event.preventDefault();
  const route = trigger.dataset.route || '/';
  switch (action) {
    case 'dialog-backdrop':
    case 'close-dialog': window.legalaiCloseDialog(); break;
    case 'toggle-nav': window.legalaiToggleNav(); break;
    case 'go': window.legalaiGo(route); break;
    case 'search-dialog': window.legalaiSearchDialog(); break;
    case 'account-dialog': window.legalaiAccountDialog(); break;
    case 'close-mobile-nav': window.legalaiCloseMobileNav(); break;
    case 'help-dialog':
    case 'context-help-dialog': window.legalaiHelpDialog(); break;
    case 'accessibility-dialog': window.legalaiAccessibilityDialog(); break;
    case 'accessibility-toggle': setUiPreference(trigger.dataset.preference || '', trigger.getAttribute('aria-checked') !== 'true'); window.legalaiAccessibilityDialog(); break;
    case 'search-suggestion': { const input=document.getElementById('global-search-input'); if(input){ input.value=trigger.dataset.query||''; input.focus(); document.getElementById('global-search-form')?.requestSubmit(); } break; }
    case 'notifications-dialog': window.legalaiNotificationsDialog(); break;
    case 'notification-open': markNotificationRead(state.user, trigger.dataset.notificationId || ''); window.legalaiCloseDialog(); window.legalaiGo(route); break;
    case 'notifications-read-all': markAllNotificationsRead(state.user, state.cases, state.documents); window.legalaiCloseDialog(); router(); break;
    case 'onboarding-open': window.legalaiCloseDialog(); window.legalaiOnboardingDialog(); break;
    case 'onboarding-dismiss': dismissOnboarding(state.user); router(); break;
    case 'onboarding-go': markOnboardingStep(state.user, trigger.dataset.step || ''); window.legalaiCloseDialog(); window.legalaiGo(route); break;
    case 'onboarding-reset': resetOnboarding(state.user); window.legalaiCloseDialog(); router(); break;
    case 'logout': window.legalaiCloseDialog(); window.legalaiLogout(); break;
    case 'go-close-dialog': window.legalaiCloseDialog(); window.legalaiGo(route); break;
    case 'query-go': window.legalaiSetSolutionQuery(trigger.dataset.query || ''); window.legalaiGo(route); break;
    case 'solution-filter': window.legalaiSetSolutionFilter(trigger.dataset.value || 'Todos'); break;
    case 'reset-solution-filters': window.legalaiResetSolutionFilters(); break;
    case 'case-filter': window.legalaiSetCaseFilter(trigger.dataset.value || 'Activos'); break;
    case 'choose-need': window.legalaiChooseNeed(trigger.dataset.value || ''); break;
    case 'analyze-intake': window.legalaiAnalyzeIntake(); break;
    case 'wizard-previous': window.legalaiWizardPrevious(); break;
    case 'wizard-save': window.legalaiSaveWizard(true); break;
    case 'wizard-next': window.legalaiWizardNext(); break;
    case 'wizard-jump': window.legalaiWizardJump(Number(trigger.dataset.index || 0)); break;
    case 'wizard-review-edit': window.legalaiWizardReviewEdit(); break;
    case 'wizard-review-confirm': window.legalaiWizardReviewConfirm(); break;
    case 'toggle-help': window.legalaiToggleHelp(trigger.dataset.id || ''); break;
    case 'back-to-wizard': window.legalaiBackToWizard(); break;
    case 'create-case': window.legalaiCreateCase(); break;
    case 'select-service-level': window.legalaiSelectServiceLevel(trigger.dataset.level || ''); break;
    case 'start-checkout': window.legalaiStartCheckout(); break;
    case 'pay-checkout': window.legalaiPayCheckout(trigger.dataset.orderId || '', trigger.dataset.method || ''); break;
    case 'case-tab': window.legalaiCaseTab(trigger.dataset.tab || 'resumen', trigger.dataset.caseId || ''); break;
    case 'journey-transition': window.legalaiJourneyTransition(trigger.dataset.caseId || '', trigger.dataset.targetState || ''); break;
    case 'follow-up-update': window.legalaiFollowUpUpdate(trigger.dataset.caseId || '', trigger.dataset.followUpId || '', trigger.dataset.status || 'completed'); break;
    case 'pilot-enroll': m248Pilot.enroll(); break;
    case 'pilot-withdraw': m248Pilot.withdraw(); break;
    case 'pilot-feedback': m248Pilot.feedback(); break;
    case 'pilot-incident': m248Pilot.incident(); break;
    case 'pilot-manual': m248Pilot.manual(trigger.dataset.checkId || '', trigger.dataset.status || 'pending'); break;
    case 'pilot-control': m248Pilot.control(trigger.dataset.pilotAction || 'freeze'); break;
    case 'pilot-triage': m248Pilot.triage(trigger.dataset.incidentId || ''); break;
    case 'professional-invite': m249Professional.invite(trigger.dataset.specialistId || ''); break;
    case 'professional-invitation-accept': m249Professional.acceptInvitation(); break;
    case 'professional-verify': m249Professional.verify(trigger.dataset.specialistId || ''); break;
    case 'professional-availability': m249Professional.availability(trigger.dataset.status || 'available'); break;
    case 'professional-offer': m249Professional.offer(trigger.dataset.caseId || ''); break;
    case 'professional-assignment-decision': m249Professional.decision(trigger.dataset.assignmentId || '', trigger.dataset.decision || 'reject'); break;
    case 'professional-conflict-resolve': m249Professional.resolve(trigger.dataset.assignmentId || ''); break;
    case 'professional-assignment-complete': m249Professional.complete(trigger.dataset.assignmentId || ''); break;
    case 'reload': location.reload(); break;
    default: break;
  }
});
document.addEventListener('keydown', event => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); window.legalaiSearchDialog(); }
  if (event.key === '?' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)) { event.preventDefault(); window.legalaiHelpDialog(); }
  if (event.key === 'Escape' && dialogRoot.innerHTML) window.legalaiCloseDialog();
});
async function preload() {
  const tasks = [
    api('/api/products').then(x => state.products = x),
    api('/api/product-experience').then(x => state.experiences = x.products || []),
    api('/api/cases').then(x => state.cases = Array.isArray(x) ? x : []).catch(() => state.cases = []),
    api('/api/documents').then(x => state.documents = Array.isArray(x) ? x : []).catch(() => state.documents = []),
    api('/api/config').then(x => state.config = x).catch(() => state.config = {}),
    api('/api/approval-status').then(x => state.approval = x).catch(() => state.approval = {}),
  ];
  await Promise.all(tasks);
}
function productMap() { return Object.fromEntries(state.products.map(p => [p.code, p])); }
function experienceMap() { return Object.fromEntries(state.experiences.map(p => [p.product_code, p])); }
function productStatus(product) {
  if (product?.internal_legal_approval?.publication_authorized) return ['Aprobado · uso controlado', 'success'];
  if (product?.human_validation_required) return ['Revisión profesional obligatoria', 'danger'];
  return ['Revisión específica requerida', 'warning'];
}
function deepLibraryRoute(code) {
  if (contractualProductCodes.has(code)) return '/biblioteca-contractual';
  if (playbookProductCodes.has(code)) return '/biblioteca-playbooks';
  return null;
}
function deepLibraryLabel(code) {
  return contractualProductCodes.has(code) ? 'Biblioteca contractual profunda' : 'Playbook jurídico profundo';
}
async function loadDeepLibraries() {
  if (!state.contractualLibrary) {
    const response = await fetch('/assets/contractual-library-m4/manifest.json', { credentials: 'same-origin' });
    if (!response.ok) throw new Error('No fue posible cargar la biblioteca contractual profunda.');
    state.contractualLibrary = await response.json();
  }
  if (!state.playbookLibrary) {
    const response = await fetch('/assets/playbook-library-m5/manifest.json', { credentials: 'same-origin' });
    if (!response.ok) throw new Error('No fue posible cargar la biblioteca de playbooks jurídicos profundos.');
    state.playbookLibrary = await response.json();
  }
}
function riskBadge(risk) { return `<span class="badge ${riskClass[risk] || ''}">${esc(riskLabels[risk] || humanize(risk))}</span>`; }
function pageHeader({ eyebrow, title, description, actions = '' }) {
  return `<header class="page-header"><div class="page-title"><span class="eyebrow">${esc(eyebrow)}</span><h1>${esc(title)}</h1>${description ? `<p>${esc(description)}</p>` : ''}</div>${actions ? `<div class="page-actions">${actions}</div>` : ''}</header>`;
}
const M24_CLIENT_INTAKE_ENDPOINT = '/api/m24/client-intake';
const M21_GUIDED_COPY = Object.freeze({ intro: 'No necesitas conocer el nombre del documento', compare: 'Comparar las 11 soluciones' });
function answeredValue(value) { return answeredValueM247(value); }
const m247Guided = createGuidedExperience({ shell, pageHeader, intakeEndpoint: M24_CLIENT_INTAKE_ENDPOINT, copy: M21_GUIDED_COPY });
const m248Pilot = createPilotExperience({ shell, pageHeader });
const m249Professional = createProfessionalExperience({ shell, pageHeader });
const m250Readiness = createReadinessExperience({ shell, pageHeader });
const m262Gold = createGoldPublicExperience();
const { guidedStartPage } = m247Guided;
window.legalaiAnalyzeIntake = m247Guided.analyzeIntake;
window.legalaiChooseNeed = m247Guided.chooseNeed;
function caseList(cases, limit = 99) {
  const products = productMap();
  if (!cases.length) return internalEmptyState({ visual:'empty-evidence.svg', title:'No hay expedientes en esta vista', text:state.user.role === 'client' ? 'Cambia el filtro o inicia una nueva solución para crear tu primer expediente.' : 'No hay expedientes que coincidan con este estado.', actionLabel:state.user.role === 'client'?'Iniciar una solución':'', route:'/nuevo' });
  return `<div class="m292-case-grid">${cases.slice(0, limit).map(c => caseCard(c, products[c.product_code] || {}, limit <= 4)).join('')}</div>`;
}
function homePage() {
  const assigned = state.user.role === 'client' ? state.cases : state.cases.filter(c => c.specialist_id === state.user.id || state.user.role === 'admin');
  const openCases = assigned.filter(c => !/cerrado|finalizado/i.test(c.status || '')).length;
  const docs = state.documents.length;
  const reviewCount = assigned.filter(c => /revisi/i.test(c.review_status || c.status || '')).length;
  const onboarding = onboardingPanel(state.user, assigned, state.documents);
  if (state.user.role === 'client') {
    const firstName = String(state.user.name || 'Hola').split(/\s+/)[0];
    const active = assigned.find(c => !/cerrado|finalizado/i.test(c.status || ''));
    app.innerHTML = shell(`<div class="page m29-client-home">
      <section class="m29-client-welcome"><div><span class="eyebrow">Tu espacio jurídico</span><h1>Hola, ${esc(firstName)}. ¿Qué necesitas resolver hoy?</h1><p>Empieza una nueva solución o continúa un expediente sin perder tus respuestas, documentos ni próximos pasos.</p><div class="hero-actions"><button class="btn gold" data-action="go" data-route="/nuevo">Encontrar una solución</button><button class="btn secondary" data-action="go" data-route="/casos">Ver mis expedientes</button></div></div><img src="/assets/brand-visuals/people-journey.svg" alt="Recorrido guiado hacia una solución jurídica"></section>
      ${onboarding}
      ${active?(()=>{const stage=friendlyCaseState(active);return `<section class="m29-continue-card m292-continue-card"><img src="/assets/brand-visuals/internal/${stage.visual}" alt=""><div><span class="badge ${stage.cls}">${esc(stage.label)}</span><h2>${esc(active.title)}</h2><p>${esc((productMap()[active.product_code]||{}).title||active.product_code)} · Actualizado ${esc(dateText(active.updated_at))}</p><div class="m292-progress"><span class="progress-p${Math.min(100,Math.max(0,Math.round(stage.progress/10)*10))}"></span></div></div><button class="btn primary" data-action="go" data-route="/caso/${encodeURIComponent(active.id)}">Continuar expediente</button></section>`;})():''}
      <section class="m29-client-summary"><article><span>${icons.cases}</span><div><b>${openCases}</b><small>${openCases===1?'expediente activo':'expedientes activos'}</small></div></article><article><span>${icons.docs}</span><div><b>${docs}</b><small>${docs===1?'documento guardado':'documentos guardados'}</small></div></article><article><span>${icons.review}</span><div><b>${reviewCount}</b><small>en revisión</small></div></article></section>
      <section class="section-grid"><div class="card span-8"><div class="card-header"><div><h2>Mis expedientes recientes</h2><p>Consulta qué falta, qué está en revisión y cuál es el siguiente paso.</p></div><button class="btn secondary sm" data-action="go" data-route="/casos">Ver todos</button></div>${caseList(assigned,4)}</div><div class="card span-4 m29-help-card"><div class="card-header"><div><h2>Empieza por tu necesidad</h2><p>No necesitas conocer el nombre del documento.</p></div></div><button class="m29-need-option" data-action="query-go" data-query="contrato" data-route="/soluciones"><span>◇</span><div><b>Necesito un contrato</b><small>Trabajo, servicios, arriendo o confidencialidad.</small></div></button><button class="m29-need-option" data-action="query-go" data-query="reclamar" data-route="/soluciones"><span>⚖</span><div><b>Necesito presentar una reclamación</b><small>Laboral, salud, consumo, datos o tránsito.</small></div></button><button class="m29-need-option" data-action="go" data-route="/nuevo"><span>?</span><div><b>No sé cuál solución necesito</b><small>Utiliza el orientador guiado.</small></div></button></div></section>
    </div>`); return;
  }
  const primaryCta = state.user.role === 'specialist' ? ['/revision','Abrir bandeja de revisión'] : ['/operacion','Ver operación jurídica'];
  const heroTitle = state.user.role === 'specialist' ? 'Prioriza revisiones con todo el contexto del expediente.' : 'Gestiona la operación jurídica sin perder trazabilidad.';
  app.innerHTML = shell(`<div class="page">${onboarding}<section class="hero-panel"><div class="hero-grid"><div><span class="eyebrow hero-eyebrow">LegalAIZ.it · espacio profesional</span><h1>${heroTitle}</h1><p>Consulta hechos, soportes, documentos y decisiones desde una vista unificada. Cada revisión conserva responsable, versión y evidencia.</p><div class="hero-actions"><button class="btn gold" data-action="go" data-route="${primaryCta[0]}">${primaryCta[1]}</button><button class="btn secondary" data-action="go" data-route="/casos">Ver expedientes</button></div></div><aside class="hero-side"><img class="m29-professional-hero-image" src="/assets/brand-visuals/ai-human-review.svg" alt="Revisión profesional asistida por tecnología"></aside></div></section><section class="kpi-grid"><div class="kpi"><span class="kpi-label">Casos activos</span><div class="kpi-value"><strong>${openCases}</strong><span class="kpi-icon">${icons.cases}</span></div></div><div class="kpi"><span class="kpi-label">En revisión</span><div class="kpi-value"><strong>${reviewCount}</strong><span class="kpi-icon">${icons.review}</span></div></div><div class="kpi"><span class="kpi-label">Documentos</span><div class="kpi-value"><strong>${docs}</strong><span class="kpi-icon">${icons.docs}</span></div></div><div class="kpi"><span class="kpi-label">Soluciones</span><div class="kpi-value"><strong>${state.products.length}</strong><span class="kpi-icon">${icons.solutions}</span></div></div></section><section class="card"><div class="card-header"><div><h2>Casos que requieren atención</h2><p>Abre el expediente antes de tomar una decisión o aprobar un documento.</p></div><button class="btn secondary sm" data-action="go" data-route="/casos">Ver todos</button></div>${caseList(assigned,6)}</section></div>`);
}
function solutionsPage() {
  const verticals = ['Todos', ...new Set(state.products.map(p => p.vertical).filter(Boolean))];
  const q = state.solutionQuery.toLowerCase().trim();
  const filtered = state.products.filter(p => {
    const matchVertical = state.solutionFilter === 'Todos' || p.vertical === state.solutionFilter;
    const haystack = `${p.title} ${p.summary} ${p.vertical} ${(p.outcomes || []).join(' ')}`.toLowerCase();
    return matchVertical && (!q || haystack.includes(q));
  });
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow: 'Encuentra tu solución', title: '¿Qué necesitas resolver?', description: 'Explora cada opción por la situación que atiende, lo que puedes obtener y la información que necesitarás. Antes de usar un resultado, la plataforma te indicará los riesgos y revisiones aplicables.', actions: state.user.role === 'client' ? `<button class="btn primary" data-action="go" data-route="/nuevo">Nueva solución</button>` : '' })}
    <div class="toolbar"><div class="search-box"><input id="solution-search" class="input" value="${esc(state.solutionQuery)}" placeholder="Buscar por problema, documento o tema…" aria-label="Buscar soluciones"></div><div class="segmented" role="tablist">${verticals.map(v => `<button class="${state.solutionFilter === v ? 'active' : ''}" data-action="solution-filter" data-value="${esc(v)}">${esc(v)}</button>`).join('')}</div></div>
    <div class="solution-grid">${filtered.map(solutionCard).join('')}</div>
    ${!filtered.length ? `<div class="empty-state m292-empty-state mt-20"><img src="/assets/brand-visuals/internal/empty-search.svg" alt=""><h2>No encontramos una coincidencia</h2><p>Prueba con otro término o revisa todas las categorías.</p><button class="btn secondary" data-action="reset-solution-filters">Ver todas</button></div>` : ''}
  </div>`);
  const search = document.getElementById('solution-search');
  search.addEventListener('input', e => { state.solutionQuery = e.target.value; clearTimeout(search._timer); search._timer = setTimeout(solutionsPage, 180); });
}
function solutionCard(product) {
  const [status, cls] = productStatus(product);
  const experience = experienceMap()[product.code];
  return `<article class="solution-card"><div class="solution-top"><span class="solution-icon">${esc(product.icon || '§')}</span><span class="badge ${cls}">${esc(status)}</span></div><div class="solution-code">${esc(product.code)}</div><h2>${esc(product.title)}</h2><p>${esc(experience?.promise || product.summary)}</p><div class="product-meta"><span class="badge blue">${esc(product.vertical)}</span>${riskBadge(product.base_risk)}</div><div class="solution-delivery"><small>Entrega principal</small><b>${esc((experience?.deliverables || product.outcomes || ['Ruta jurídica y documentos'])[0])}</b></div><div class="solution-footer"><span>${esc(experience?.estimated_time || 'Proceso guiado')}</span><div class="button-group"><button class="btn secondary sm" data-action="go" data-route="${publicProductRoute(product.code)}">Ver alcance</button>${state.user.role === 'client' ? `<button class="btn navy sm" data-action="go" data-route="/nuevo/${encodeURIComponent(product.code)}">Iniciar</button>` : ''}</div></div></article>`;
}
window.legalaiSetSolutionFilter = value => { state.solutionFilter = value; solutionsPage(); };
window.legalaiSetSolutionQuery = value => { state.solutionQuery = value; };
window.legalaiResetSolutionFilters = () => { state.solutionFilter = 'Todos'; state.solutionQuery = ''; solutionsPage(); };
async function productDetailPage(code) {
  let product = state.products.find(p => p.code === code);
  if (!product) { await preload(); product = state.products.find(p => p.code === code); }
  if (!product) return notFoundPage('La solución solicitada no está disponible.');
  let exp = experienceMap()[code];
  if (!exp) { try { exp = await api(`/api/product-experience/${encodeURIComponent(code)}`); } catch { exp = null; } }
  const [status, statusCls] = productStatus(product);
  const libraryRoute = deepLibraryRoute(code);
  const libraryAction = libraryRoute ? `<button class="btn secondary" data-action="go" data-route="${libraryRoute}">Explorar documentos</button>` : '';
  const requiredCount = (exp?.required_documents || []).length;
  const deliverableCount = (exp?.deliverables || product.outcomes || []).length;
  app.innerHTML = shell(`<div class="page">
    <div class="journey-strip"><span><b>1</b> Conoce el alcance</span><i>›</i><span><b>2</b> Completa tus datos</span><i>›</i><span><b>3</b> Revisa el resultado</span><i>›</i><span><b>4</b> Gestiona tu expediente</span></div>
    <div class="product-hero"><section class="product-summary"><span class="eyebrow">${esc(product.vertical)}</span><h1>${esc(product.title)}</h1><p class="lead">${esc(exp?.promise || product.summary)}</p><div class="product-meta"><span class="badge ${statusCls}">${esc(status)}</span>${riskBadge(product.base_risk)}<span class="badge">Colombia</span>${exp?.gold_standard ? '<span class="badge gold">Contenido especializado</span>' : ''}${libraryRoute ? '<span class="badge blue">Documentos y anexos disponibles</span>' : ''}</div></section><aside class="product-cta"><h2>Empieza con una ruta guiada</h2><p>${esc(exp?.estimated_time || 'Completa la información relevante y revisa el resultado antes de crear el expediente.')}</p><div class="product-readiness"><span><b>${requiredCount}</b><small>datos o soportes clave</small></span><span><b>${deliverableCount}</b><small>resultados posibles</small></span></div><div class="price-block"><small>Servicio automatizado desde</small><strong>${money(product.price_auto)}</strong></div><button class="btn gold" data-action="go" data-route="/nuevo/${encodeURIComponent(code)}">Comenzar ahora</button>${libraryAction}</aside></div>
    ${productJourneySection(code)}
    ${exp?.gold_standard ? `<section class="gold-standard-banner"><div><span class="eyebrow">Una solución construida para tu caso</span><h2>${esc(exp.gold_standard.headline)}</h2><p>${esc(exp.gold_standard.why_gold)}</p></div><div class="gold-pillar-list">${exp.gold_standard.pillars.map((item,index)=>`<span><b>${index+1}</b>${esc(item)}</span>`).join('')}</div></section>` : ''}<section class="section-grid"><div class="card span-7"><div class="card-header"><div><h2>Cómo funciona</h2><p>Avanza paso a paso, desde la información inicial hasta el documento y sus siguientes acciones.</p></div></div><div class="timeline">${(exp?.steps || []).map((s, i) => `<div class="timeline-item"><div class="timeline-number">${esc(s.number || i + 1)}</div><div class="timeline-copy"><b>${esc(s.title)}</b><p>${esc(s.description)}</p></div></div>`).join('') || `<div class="empty-state"><p>El recorrido detallado estará disponible durante el proceso.</p></div>`}</div></div><div class="card span-5"><div class="card-header"><div><h3>Qué recibirás</h3><p>El resultado se adapta a la información y al nivel de complejidad de tu caso.</p></div></div><ul class="check-list">${(exp?.deliverables || product.outcomes || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul></div><div class="card span-6"><div class="card-header"><div><h3>Qué debes preparar</h3><p>Tener estos datos y soportes a la mano hará el proceso más claro y eficiente.</p></div></div><ul class="check-list">${[...(exp?.required_documents || []), ...(exp?.optional_documents || []).slice(0, 2)].map(x => `<li>${esc(x.label || x)}</li>`).join('') || '<li>La lista específica aparecerá durante el proceso.</li>'}</ul></div><div class="card span-6"><div class="card-header"><div><h3>Revisión y límites</h3><p>Te indicaremos con claridad cuándo el asunto puede avanzar de forma automatizada y cuándo requiere revisión profesional.</p></div></div><div class="demo-note mt-0"><b>${exp?.human_review?.required ? 'Este caso puede requerir revisión profesional.' : 'Puedes solicitar revisión profesional.'}</b><br>${esc(exp?.human_review?.reason || 'El resultado depende de los hechos, los soportes y las condiciones concretas del caso.')}</div>${product.exclusions?.length ? `<ul class="check-list mt-16">${product.exclusions.slice(0, 4).map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}</div>${libraryRoute ? `<div class="card span-12 depth-card"><div><span class="eyebrow">Documentos y anexos</span><h2>${esc(deepLibraryLabel(code))}</h2><p>Consulta los documentos disponibles, anexos y fuentes de apoyo vinculadas a esta solución. El contenido se presenta de forma organizada para facilitar su revisión y seguimiento.</p></div><button class="btn gold" data-action="go" data-route="${libraryRoute}">Explorar contenido</button></div>` : ''}</section>
  </div>`);
}
async function wizardPage(code) {
  let detail;
  try { detail = await api(`/api/products/${encodeURIComponent(code)}`); } catch (error) { return notFoundPage(error.message); }
  const product = detail.product;
  const questions = detail.interview?.questions || [];
  const sections = [...new Set(questions.map(q => q.section || 'Información general'))];
  const saved = loadDraft(code);
  if (!state.wizard || state.wizard.code !== code) {
    state.wizard = { code, product, detail, sections, step: Math.min(saved?.step || 0, Math.max(0, sections.length - 1)), page: Math.max(0, saved?.page || 0), reviewMode: false, answers: saved?.answers || {}, result: null, saving: false, savedAt: saved?.saved_at || null };
  }
  renderWizard();
}
function sectionStats(w, section) {
  const questions = (w.detail.interview?.questions || []).filter(q => (q.section || 'Información general') === section && shouldShow(q, w.answers));
  const required = questions.filter(q => q.required), answered = questions.filter(q => answeredValue(w.answers[q.id])), requiredAnswered = required.filter(q => answeredValue(w.answers[q.id]));
  return { questions, required: required.length, answered: answered.length, complete: requiredAnswered.length === required.length };
}
function wizardBlockState(w) {
  const section = w.sections[w.step], stats = sectionStats(w, section), pages = paginateWizardQuestions(stats.questions), page = Math.min(w.page || 0, Math.max(0,pages.length-1));
  w.page = page; return { section, stats, pages, page, questions: pages[page] || [] };
}
function renderWizardReview() {
  const w=state.wizard, all=(w.detail.interview?.questions||[]).filter(q=>shouldShow(q,w.answers)), answered=all.filter(q=>answeredValue(w.answers[q.id]));
  app.innerHTML=shell(`<div class="page">${pageHeader({eyebrow:'Revisión previa',title:'Confirma la información antes del análisis',description:'Todavía puedes regresar y corregir datos. El análisis no sustituye la revisión jurídica profesional.'})}<section class="card wizard-review-card"><div class="card-header"><div><h2>Resumen de respuestas</h2><p>${answered.length} de ${all.length} datos respondidos.</p></div><span class="badge blue">Paso obligatorio</span></div><div class="wizard-review-grid">${w.sections.map((section,index)=>{const qs=all.filter(q=>(q.section||'Información general')===section&&answeredValue(w.answers[q.id]));return `<section class="review-section"><div class="review-section-head"><h3>${esc(section)}</h3><button class="btn ghost sm" data-action="wizard-jump" data-index="${index}">Editar</button></div>${qs.length?qs.map(q=>`<div class="review-answer"><small>${esc(q.label)}</small><span>${esc(Array.isArray(w.answers[q.id])?w.answers[q.id].join(', '):w.answers[q.id])}</span></div>`).join(''):'<p class="muted">Sin respuestas visibles en esta etapa.</p>'}</section>`;}).join('')}</div><div class="legal-notice mt-20"><b>Verificación.</b> Confirma nombres, fechas, valores y hechos. Los datos finales deben corresponder a soportes verificables.</div><footer class="wizard-footer review-footer"><button class="btn secondary" data-action="wizard-review-edit">Volver a editar</button><button class="btn gold" data-action="wizard-review-confirm">Confirmar y analizar</button></footer></section></div>`);
}
function renderWizard() {
  const w=state.wizard; if(w.reviewMode) return renderWizardReview();
  const block=wizardBlockState(w), visible=block.questions, allQuestions=(w.detail.interview?.questions||[]).filter(q=>shouldShow(q,w.answers)), allAnswered=allQuestions.filter(q=>answeredValue(w.answers[q.id])).length, progress=allQuestions.length?Math.round((allAnswered/allQuestions.length)*100):0, completedAnswers=Object.entries(w.answers).filter(([,v])=>answeredValue(v)).slice(-5), guide=wizardGuidance(block.section,visible), savedText=w.savedAt?`Guardado ${new Date(w.savedAt).toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'})}`:'Aún no guardado', blockLabel=`Bloque ${block.page+1} de ${block.pages.length}`;
  app.innerHTML=shell(`<div class="page">${pageHeader({eyebrow:'Proceso guiado',title:w.product.title,description:w.detail.interview?.intro||'Completa la información confirmada. Puedes guardar el avance y regresar después.',actions:`<button class="btn secondary" data-action="go" data-route="/solucion/${encodeURIComponent(w.code)}">Ver alcance</button>`})}<div class="wizard-overview" role="progressbar" aria-label="Avance total del formulario" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress}"><div><b>${allAnswered}/${allQuestions.length}</b><span>respuestas completadas</span></div><div><b>${block.stats.answered}/${block.stats.questions.length}</b><span>en esta etapa</span></div><div><b>${w.sections.filter(x=>sectionStats(w,x).complete).length}/${w.sections.length}</b><span>etapas completas</span></div><div class="wizard-overall-progress"><span class="progress-p${Math.min(100,Math.max(0,Math.round(progress/10)*10))}"></span></div></div><div class="wizard-layout"><section class="wizard-main"><header class="wizard-head"><div class="wizard-title"><span class="eyebrow">Etapa ${w.step+1} de ${w.sections.length} · ${blockLabel}</span><h2>${esc(block.section)}</h2><p>${visible.length} preguntas en este bloque · ${block.stats.required} obligatorias en la etapa</p></div><div class="progress-ring progress-p${Math.min(100,Math.max(0,Math.round(progress/10)*10))}"><span>${progress}%</span></div></header><div class="wizard-body"><section class="m292-wizard-guide"><img src="/assets/brand-visuals/internal/form-guidance.svg" alt=""><div><span class="eyebrow">Antes de responder</span><h3>${esc(guide.title)}</h3><p>${esc(guide.detail)}</p><div class="m292-guide-meta"><span><b>${guide.required}</b> obligatorias</span><span><b>${guide.total}</b> preguntas visibles</span></div></div></section><div class="section-guidance"><b>Completa únicamente información verificable.</b><span>Presentamos bloques breves para facilitar la revisión, especialmente en móvil.</span></div><div class="question-grid">${visible.map(renderQuestion).join('')||'<div class="empty-state"><p>No hay preguntas visibles en este bloque con las respuestas actuales.</p></div>'}</div></div><footer class="wizard-footer"><button class="btn secondary" ${(w.step===0&&block.page===0)?'disabled':''} data-action="wizard-previous">Anterior</button><div class="button-group"><button class="btn ghost" data-action="wizard-save">Guardar borrador</button><button class="btn primary" data-action="wizard-next">${w.step===w.sections.length-1&&block.page===block.pages.length-1?'Revisar antes de analizar':'Guardar y continuar'}</button></div></footer></section><aside class="wizard-side"><section class="progress-card"><h3>Etapas del proceso</h3><div class="step-list">${w.sections.map((section,index)=>{const st=sectionStats(w,section);return `<button class="step-item ${index===w.step?'active':st.complete?'complete':''}" data-action="wizard-jump" data-index="${index}" ${index>w.step&&!sectionStats(w,w.sections[index-1]).complete?'disabled':''} ${index===w.step?'aria-current="step"':''}><span class="step-dot">${st.complete?'✓':index+1}</span><span><b>${esc(section)}</b><small>${st.answered}/${st.questions.length} respondidas</small></span></button>`;}).join('')}</div><div class="draft-status ${w.savedAt?'saved':'pending'}">${esc(savedText)}</div></section><section class="summary-card m292-prep-card"><h3>Ten a la mano</h3><ul>${guide.items.map(item=>`<li>${esc(item)}</li>`).join('')}</ul></section>${wizardContextCard(w.code, block.section)}<section class="summary-card"><h3>Resumen reciente</h3><div class="answer-summary">${completedAnswers.length?completedAnswers.map(([id,value])=>{const q=w.detail.interview.questions.find(x=>x.id===id);return `<div><small>${esc(q?.label||id)}</small><span>${esc(Array.isArray(value)?value.join(', '):value)}</span></div>`;}).join(''):'<div><span>Las respuestas aparecerán aquí mientras avanzas.</span></div>'}</div></section></aside></div></div>`); bindWizardFields();
}
function renderQuestion(q) {
  const value=state.wizard.answers[q.id]??(q.type==='multiselect'?[]:''), full=['textarea','multiselect'].includes(q.type)||(q.options||[]).length>4, help=q.help?.short||q.help?.why_asked||'', labelId=`label-${q.id}`, helpId=`help-${q.id}`, errorId=`error-${q.id}`, described=[help?helpId:'',errorId].filter(Boolean).join(' '); let field='';
  if(q.type==='select'&&(q.options||[]).length<=4) field=`<div class="choice-grid" role="radiogroup" aria-labelledby="${esc(labelId)}" aria-describedby="${esc(described)}">${(q.options||[]).map((opt,index)=>`<div class="choice"><input type="radio" id="${esc(q.id)}-${index}" name="${esc(q.id)}" value="${esc(opt)}" ${String(value)===String(opt)?'checked':''} ${q.required?'aria-required="true"':''}><label for="${esc(q.id)}-${index}">${esc(opt)}</label></div>`).join('')}</div>`;
  else if(q.type==='select') field=`<select class="select" id="${esc(q.id)}" aria-labelledby="${esc(labelId)}" aria-describedby="${esc(described)}" ${q.required?'aria-required="true"':''}><option value="">Selecciona una opción</option>${(q.options||[]).map(opt=>`<option value="${esc(opt)}" ${String(value)===String(opt)?'selected':''}>${esc(opt)}</option>`).join('')}</select>`;
  else if(q.type==='multiselect'){const selected=Array.isArray(value)?value:[];field=`<div class="choice-grid" role="group" aria-labelledby="${esc(labelId)}" aria-describedby="${esc(described)}">${(q.options||[]).map((opt,index)=>`<div class="choice"><input type="checkbox" id="${esc(q.id)}-${index}" name="${esc(q.id)}" value="${esc(opt)}" ${selected.includes(opt)?'checked':''}><label for="${esc(q.id)}-${index}">${esc(opt)}</label></div>`).join('')}</div>`;}
  else if(q.type==='textarea') field=`<textarea class="textarea" id="${esc(q.id)}" aria-labelledby="${esc(labelId)}" aria-describedby="${esc(described)}" ${q.required?'aria-required="true"':''} ${q.max_length?`maxlength="${q.max_length}"`:''} placeholder="${esc(q.help?.example||'')}">${esc(value)}</textarea>`;
  else {const type=['number','date','email'].includes(q.type)?q.type:'text';field=`<input class="input" id="${esc(q.id)}" type="${type}" value="${esc(value)}" aria-labelledby="${esc(labelId)}" aria-describedby="${esc(described)}" ${q.required?'aria-required="true"':''} ${q.min!=null?`min="${q.min}"`:''} ${q.max!=null?`max="${q.max}"`:''} ${q.min_length?`minlength="${q.min_length}"`:''} ${q.max_length?`maxlength="${q.max_length}"`:''} placeholder="${esc(q.help?.example||'')}">`;}
  return `<div class="question ${full?'full':''}" data-question="${esc(q.id)}"><div class="question-label"><label id="${esc(labelId)}" ${!['select','multiselect'].includes(q.type)||((q.options||[]).length>4&&q.type==='select')?`for="${esc(q.id)}"`:''}>${esc(q.label)}${q.required?' <span class="required-mark" aria-hidden="true">*</span>':''}</label>${help?`<button class="help-btn" type="button" aria-label="Ayuda sobre ${esc(q.label)}" aria-expanded="false" aria-controls="${esc(helpId)}" data-action="toggle-help" data-id="${esc(q.id)}">?</button>`:''}</div>${field}${help?`<div id="${esc(helpId)}" class="help-panel hidden"><b>Por qué lo preguntamos.</b> ${esc(help)}${q.help?.where_to_find?`<br><b>Dónde verificar.</b> ${esc(q.help.where_to_find)}`:''}</div>`:''}<div class="field-error hidden" id="${esc(errorId)}" role="alert"></div></div>`;
}
function bindWizardFields() {
  const w = state.wizard;
  const currentQuestions = (w.detail.interview?.questions || []).filter(q => (q.section || 'Información general') === w.sections[w.step]);
  for (const q of currentQuestions) {
    if (q.type === 'select' && (q.options || []).length <= 4) {
      document.querySelectorAll(`input[name="${CSS.escape(q.id)}"]`).forEach(el => el.addEventListener('change', e => { w.answers[q.id] = e.target.value; saveDraft(); renderWizard(); }));
    } else if (q.type === 'multiselect') {
      document.querySelectorAll(`input[name="${CSS.escape(q.id)}"]`).forEach(el => el.addEventListener('change', () => { w.answers[q.id] = [...document.querySelectorAll(`input[name="${CSS.escape(q.id)}"]:checked`)].map(x => x.value); saveDraft(); }));
    } else {
      const el = document.getElementById(q.id);
      if (!el) continue;
      const handler = e => { w.answers[q.id] = e.target.value; saveDraft(); };
      el.addEventListener(q.type === 'select' ? 'change' : 'input', handler);
      if (q.type === 'select') el.addEventListener('change', renderWizard);
    }
  }
}
window.legalaiToggleHelp = id => { const panel=document.getElementById(`help-${id}`), button=document.querySelector(`[data-action="toggle-help"][data-id="${CSS.escape(id)}"]`); if(!panel)return; const expanded=panel.classList.toggle('hidden')===false; button?.setAttribute('aria-expanded',String(expanded)); };
function draftKey(code) { return `legalaizit:draft:${code}`; }
function legacyDraftKey(code) { return `legalaizit:m1:draft:${code}`; }
function saveDraft(showToast = false) {
  const w = state.wizard; if (!w) return;
  w.savedAt = new Date().toISOString();
  localStorage.setItem(draftKey(w.code), JSON.stringify({ step: w.step, page: w.page || 0, answers: w.answers, saved_at: w.savedAt }));
  if (showToast) toast('Borrador guardado en este equipo.');
}
function loadDraft(code) {
  try {
    const current = localStorage.getItem(draftKey(code));
    if (current) return JSON.parse(current);
    const legacy = localStorage.getItem(legacyDraftKey(code));
    if (!legacy) return null;
    localStorage.setItem(draftKey(code), legacy);
    return JSON.parse(legacy);
  } catch { return null; }
}
window.legalaiSaveWizard = saveDraft;
window.legalaiWizardPrevious=()=>{const w=state.wizard;if(w.reviewMode){w.reviewMode=false;renderWizard();return;}const block=wizardBlockState(w);if(block.page>0)w.page--;else if(w.step>0){w.step--;w.page=Math.max(0,paginateWizardQuestions(sectionStats(w,w.sections[w.step]).questions).length-1);}saveDraft();renderWizard();scrollTo({top:0,behavior:'smooth'});};
window.legalaiWizardJump=step=>{const w=state.wizard;if(step<=w.step||(step===w.step+1&&sectionStats(w,w.sections[w.step]).complete)){w.step=step;w.page=0;w.reviewMode=false;saveDraft();renderWizard();scrollTo({top:0,behavior:'smooth'});}};
window.legalaiWizardReviewEdit=()=>{const w=state.wizard;w.reviewMode=false;renderWizard();};
window.legalaiWizardReviewConfirm=async()=>{const w=state.wizard;w.reviewMode=false;await diagnoseWizard();};
function validateSection() {
  const w=state.wizard,questions=wizardBlockState(w).questions,errors=[];
  for(const q of questions){const value=w.answers[q.id];let message='';if(q.required&&(value==null||value===''||(Array.isArray(value)&&!value.length)))message='Este dato es necesario para continuar.';else if(value&&q.min_length&&String(value).trim().length<q.min_length)message=`Escribe al menos ${q.min_length} caracteres.`;else if(value&&q.max_length&&String(value).length>q.max_length)message=`Máximo ${q.max_length} caracteres.`;else if(value&&q.type==='email'&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value)))message='Ingresa un correo válido.';else if(value!==''&&q.type==='number'&&q.min!=null&&Number(value)<Number(q.min))message=`El valor mínimo es ${q.min}.`;else if(value!==''&&q.type==='number'&&q.max!=null&&Number(value)>Number(q.max))message=`El valor máximo es ${q.max}.`;else if(value&&q.after_field&&w.answers[q.after_field]&&String(value)<=String(w.answers[q.after_field]))message='La fecha debe ser posterior a la fecha relacionada.';const err=document.getElementById(`error-${q.id}`),input=document.getElementById(q.id)||document.querySelector(`[name="${CSS.escape(q.id)}"]`);if(message){errors.push(q.id);if(err){err.textContent=message;err.classList.remove('hidden');}input?.setAttribute('aria-invalid','true');}else{if(err)err.classList.add('hidden');input?.removeAttribute('aria-invalid');}}
  if(errors.length)document.querySelector(`[data-question="${CSS.escape(errors[0])}"]`)?.scrollIntoView({behavior:'smooth',block:'center'});return !errors.length;
}
window.legalaiWizardNext=async()=>{const w=state.wizard;if(!validateSection()){toast('Revisa los datos señalados antes de continuar.','danger');return;}const block=wizardBlockState(w);if(block.page<block.pages.length-1){w.page++;saveDraft();renderWizard();scrollTo({top:0,behavior:'smooth'});return;}if(w.step<w.sections.length-1){w.step++;w.page=0;saveDraft();renderWizard();scrollTo({top:0,behavior:'smooth'});return;}w.reviewMode=true;saveDraft();renderWizard();scrollTo({top:0,behavior:'smooth'});};
async function diagnoseWizard() {
  const w=state.wizard;
  try { const [result,offer]=await Promise.all([api('/api/diagnose',{method:'POST',body:JSON.stringify({product_code:w.code,answers:w.answers,strict:true})}),api(`/api/m24/client-offers/${encodeURIComponent(w.code)}`)]); w.result=result;w.offer=offer;const paid=(offer.service_levels||[]).filter(x=>x.checkout_enabled);const review=result.risk==='red'||result.review_required||result.service_mode==='blocked';const preferred=review?'solucion_revisada':'documento_personalizado';w.serviceLevel=paid.some(x=>x.id===preferred)?preferred:paid[0]?.id||'';saveDraft();renderWizardResult(); } catch(error){toast(error.message,'danger');}
}
function serviceLevelCard(level,selected,forcedReview){const disabled=forcedReview&&level.id!=='solucion_revisada';const label=level.price_label||money(level.price||0);return `<button type="button" class="service-level-card ${selected?'selected':''} ${disabled?'disabled':''}" ${disabled?'disabled':''} data-action="select-service-level" data-level="${esc(level.id)}"><span class="service-level-check">${selected?'✓':'○'}</span><span class="service-level-copy"><b>${esc(level.label)}</b><small>${esc(label)}${Number(level.price||0)?' · sandbox':''}</small><span>${(level.includes||[]).map(esc).join(' · ')}</span></span></button>`;}
function renderWizardResult(){
  const w=state.wizard,r=w.result||{},cls=r.risk||'yellow',messages=[...(r.blocking_rules||[]),...(r.review_rules||[]),...(r.triggered_rules||[])].slice(0,8),canContinue=!r.validation_errors?.length,offer=w.offer||{},paid=(offer.service_levels||[]).filter(x=>x.checkout_enabled),forced=cls==='red'||r.review_required||r.service_mode==='blocked';if(forced&&paid.some(x=>x.id==='solucion_revisada'))w.serviceLevel='solucion_revisada';const selected=paid.find(x=>x.id===w.serviceLevel)||paid[0],scope=offer.scope||w.product.outcomes||[],exclusions=offer.exclusions||w.product.exclusions||[];
  app.innerHTML=shell(`<div class="page">${pageHeader({eyebrow:'Resultado preliminar',title:w.product.title,description:'Confirma alcance, exclusiones y nivel de servicio antes del checkout sandbox.',actions:'<button class="btn secondary" data-action="back-to-wizard">Editar respuestas</button>'})}<section class="result-banner ${cls}"><div class="result-icon">${cls==='green'?'✓':cls==='red'?'!':'◈'}</div><div><h2>${esc(r.route||riskLabels[cls]||'Resultado disponible')}</h2><p>${esc(cls==='red'?'El caso exige revisión profesional antes de cualquier entrega o actuación de impacto.':cls==='yellow'?'Hay aspectos que deben confirmarse antes del uso final.':'La información permite continuar con los controles definidos.')}</p></div><span class="badge ${riskClass[cls]}">${esc(r.risk_label||riskLabels[cls])}</span></section><section class="section-grid"><div class="card span-7"><div class="card-header"><div><h2>Decisiones del análisis</h2><p>Reglas activadas por las respuestas confirmadas.</p></div></div>${messages.length?`<div class="list">${messages.map(m=>`<div class="list-row"><div class="list-main"><div class="list-icon">${m.blocking?'!':'✓'}</div><div class="list-copy"><b>${esc(m.message||m.id||'Control aplicado')}</b><small>${esc(m.action||'')}</small></div></div>${m.risk?riskBadge(m.risk):''}</div>`).join('')}</div>`:'<div class="empty-state"><p>No se activaron alertas adicionales con la información suministrada.</p></div>'}</div><div class="card span-5"><div class="card-header"><div><h3>Identifica tu expediente</h3><p>Este nombre será visible en tu panel de casos.</p></div></div><div class="field"><label for="case-title">Nombre del caso</label><input class="input" id="case-title" value="${esc(w.caseTitle||w.product.title)}"></div><div class="demo-note"><b>Checkout de prueba.</b> No se realizan cargos reales. La compra no equivale a aprobación jurídica ni publica M23.2.</div></div><div class="card span-6"><div class="card-header"><div><h3>Alcance principal</h3><p>Resultado incluido según respuestas y soportes.</p></div></div><ul class="check-list">${scope.slice(0,6).map(x=>`<li>${esc(x)}</li>`).join('')||'<li>Documento y ruta jurídica personalizada.</li>'}</ul></div><div class="card span-6"><div class="card-header"><div><h3>Exclusiones y límites</h3><p>Situaciones que exigen validación o servicio distinto.</p></div></div><ul class="check-list muted-checks">${exclusions.slice(0,6).map(x=>`<li>${esc(x)}</li>`).join('')||'<li>No incluye representación judicial ni garantiza resultados.</li>'}</ul></div><div class="card span-12"><div class="card-header"><div><h2>Selecciona el nivel de servicio</h2><p>${esc(offer.pricing_notice||'Valores de referencia del entorno sandbox.')}</p></div></div><div class="service-level-grid">${paid.map(x=>serviceLevelCard(x,selected?.id===x.id,forced)).join('')}</div>${forced?'<div class="legal-notice danger mt-16"><b>Revisión obligatoria.</b> El nivel de riesgo bloquea la opción documental sin revisión.</div>':''}<div class="checkout-summary"><span><small>Nivel seleccionado</small><b>${esc(selected?.label||'Por seleccionar')}</b></span><span><small>Total sandbox</small><b>${money(selected?.price||0)}</b></span><button class="btn gold" ${canContinue&&selected?'':'disabled'} data-action="start-checkout">Continuar al checkout</button></div></div><div class="card span-12"><div class="card-header"><div><h3>Módulos documentales previstos</h3><p>Se incluirán únicamente cuando las condiciones aplicables estén confirmadas.</p></div></div><div class="product-meta">${(r.modules||[]).map(m=>`<span class="badge blue">${esc(m.message||m.id)}</span>`).join('')||'<span class="badge">Documento principal y trazabilidad</span>'}</div></div></section></div>`);
}
window.legalaiBackToWizard=()=>{if(state.wizard)state.wizard.reviewMode=false;renderWizard();};
window.legalaiSelectServiceLevel=level=>{const w=state.wizard;if(!w)return;w.caseTitle=document.getElementById('case-title')?.value.trim()||w.caseTitle||w.product.title;const valid=(w.offer?.service_levels||[]).some(x=>x.id===level&&x.checkout_enabled),forced=w.result?.risk==='red'||w.result?.review_required||w.result?.service_mode==='blocked';if(!valid||(forced&&level!=='solucion_revisada'))return;w.serviceLevel=level;renderWizardResult();};
window.legalaiStartCheckout=async()=>{const w=state.wizard;if(!w||!w.result||!w.serviceLevel)return;w.caseTitle=document.getElementById('case-title')?.value.trim()||w.caseTitle||w.product.title;try{await api('/api/drafts',{method:'POST',body:JSON.stringify({product_code:w.code,answers:w.answers,current_step:w.step,title:w.caseTitle,result:{...w.result,service_level:w.serviceLevel}})});const order=await api('/api/checkout/orders',{method:'POST',body:JSON.stringify({product_code:w.code,result:{...w.result,service_level:w.serviceLevel},service_level:w.serviceLevel,review_selected:w.serviceLevel==='solucion_revisada'})});state.checkoutOrder=order;go(`/checkout/${encodeURIComponent(order.id)}`);}catch(error){toast(error.message,'danger');}};
window.legalaiCreateCase=()=>window.legalaiStartCheckout();
async function checkoutPage(orderId){
  let order;try{order=await api(`/api/checkout/orders/${encodeURIComponent(orderId)}`);}catch(error){return notFoundPage(error.message);}state.checkoutOrder=order;const detail=order.detail||{},completed=order.status==='Completada'&&order.case_id,paid=['Pagado (simulado)','Pagado (sandbox)'].includes(order.status),buttons=`<div class="checkout-payment-grid"><button class="btn primary" data-action="pay-checkout" data-order-id="${esc(order.id)}" data-method="Tarjeta de prueba">Tarjeta de prueba</button><button class="btn secondary" data-action="pay-checkout" data-order-id="${esc(order.id)}" data-method="PSE de prueba">PSE de prueba</button><button class="btn secondary" data-action="pay-checkout" data-order-id="${esc(order.id)}" data-method="Continuar sin cobro">Continuar sin cobro</button></div>`;
  app.innerHTML=shell(`<div class="page">${pageHeader({eyebrow:'Checkout sandbox',title:'Confirma tu solución',description:'Revisa el servicio y simula el pago. Este entorno no procesa dinero real.',actions:`<button class="btn secondary" data-action="go" data-route="/nuevo/${encodeURIComponent(order.product_code)}">Volver al formulario</button>`})}<section class="checkout-layout"><div class="card"><div class="card-header"><div><h2>${esc(detail.product_title||order.product_code)}</h2><p>${esc(detail.service_label||humanize(order.service_mode))}</p></div><span class="badge ${completed?'success':paid?'blue':'warning'}">${esc(order.status)}</span></div><div class="checkout-breakdown"><div><span>Documento personalizado</span><b>${money(order.document_price||0)}</b></div><div><span>Revisión jurídica y QA</span><b>${money(order.review_price||0)}</b></div><div class="checkout-total"><span>Total sandbox</span><b>${money(order.total||0)}</b></div></div><div class="legal-notice mt-16"><b>Entorno de demostración.</b> No existe cargo real, oferta comercial definitiva ni publicación automática. Los documentos quedan sujetos a las compuertas jurídicas y QA aplicables.</div></div><aside class="card checkout-action-card"><div class="card-header"><div><h2>${completed?'Expediente creado':paid?'Pago confirmado':'Medio de prueba'}</h2><p>${completed?'Continúa al expediente y consulta la ruta.':paid?'Continúa para crear el expediente.':'Selecciona una opción simulada.'}</p></div></div>${completed?`<button class="btn gold btn-block" data-action="go" data-route="/caso/${encodeURIComponent(order.case_id)}">Abrir expediente</button>`:paid?`<button class="btn gold btn-block" data-action="pay-checkout" data-order-id="${esc(order.id)}" data-method="${esc(order.payment_method||'Continuar sin cobro')}">Crear expediente</button>`:buttons}${order.receipt_number?`<div class="receipt-box"><small>Comprobante sandbox</small><b>${esc(order.receipt_number)}</b></div>`:''}</aside></section></div>`);
}
window.legalaiPayCheckout=async(orderId,method)=>{try{let order=await api(`/api/checkout/orders/${encodeURIComponent(orderId)}`);if(order.status==='Completada'&&order.case_id)return go(`/caso/${encodeURIComponent(order.case_id)}`);if(!['Pagado (simulado)','Pagado (sandbox)'].includes(order.status))order=await api(`/api/checkout/orders/${encodeURIComponent(orderId)}/pay`,{method:'POST',body:JSON.stringify({payment_method:method})});const draft=await api(`/api/drafts/product/${encodeURIComponent(order.product_code)}`),created=await api('/api/cases',{method:'POST',body:JSON.stringify({product_code:order.product_code,answers:draft.answers||{},title:draft.title||order.detail?.product_title||order.product_code,order_id:order.id})});localStorage.removeItem(draftKey(order.product_code));state.wizard=null;state.checkoutOrder=null;await preload();toast('Pago sandbox confirmado y expediente creado.');go(`/caso/${encodeURIComponent(created.case_id||created.id)}`);}catch(error){toast(error.message,'danger');await checkoutPage(orderId);}};
function casesPage() {
  const title = state.user.role === 'client' ? 'Mis expedientes' : state.user.role === 'specialist' ? 'Expedientes asignados' : 'Operación de expedientes';
  const description = state.user.role === 'client' ? 'Consulta el progreso, la siguiente acción y los documentos de cada caso.' : 'Prioriza expedientes por estado, riesgo y revisión.';
  const visible = state.user.role === 'client' ? filterCases(state.cases, state.caseFilter) : state.cases;
  const active = state.cases.filter(c => ['active','document'].includes(friendlyCaseState(c).key)).length;
  const review = state.cases.filter(c => friendlyCaseState(c).key === 'review').length;
  const ready = state.cases.filter(c => friendlyCaseState(c).key === 'ready').length;
  const filters = state.user.role === 'client' ? `<div class="m292-case-filters" role="tablist" aria-label="Filtrar expedientes">${caseFilters.map(([value,label])=>`<button class="${state.caseFilter===value?'active':''}" data-action="case-filter" data-value="${esc(value)}">${esc(label)}<span>${filterCases(state.cases,value).length}</span></button>`).join('')}</div>` : '';
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow:'Expedientes', title, description, actions:state.user.role==='client'?`<button class="btn primary" data-action="go" data-route="/nuevo">Nueva solución</button>`:'' })}<section class="m292-case-summary"><article><img src="/assets/brand-visuals/internal/case-active.svg" alt=""><div><b>${active}</b><span>En progreso</span></div></article><article><img src="/assets/brand-visuals/internal/case-review.svg" alt=""><div><b>${review}</b><span>En revisión</span></div></article><article><img src="/assets/brand-visuals/internal/case-ready.svg" alt=""><div><b>${ready}</b><span>Listos</span></div></article></section>${filters}${caseList(visible)}</div>`);
}
window.legalaiSetCaseFilter = value => { state.caseFilter = value; casesPage(); };
async function casePage(id) {
  let detail; let journey = null;
  try {
    [detail, journey] = await Promise.all([
      api(`/api/cases/${encodeURIComponent(id)}`),
      api(`/api/m24/case-journeys/${encodeURIComponent(id)}`).catch(() => null)
    ]);
  } catch (error) { return notFoundPage(error.message); }
  const product = state.products.find(p => p.code === detail.product_code) || detail.result?.product || {};
  const docs = state.documents.filter(d => d.case_id === id);
  const tab = state.activeCaseTab;
  const journeyBadge = journey ? `<span class="badge success">${esc(humanize(journey.current_state))}</span>` : '';
  app.innerHTML = shell(`<div class="page"><div class="case-header"><div class="page-title"><span class="eyebrow">${esc(product.vertical || detail.product_code)}</span><h1>${esc(detail.title)}</h1><p class="case-id">Expediente ${esc(detail.id)}</p><div class="product-meta">${riskBadge(detail.risk)}<span class="badge blue">${esc(detail.status)}</span><span class="badge">${esc(detail.review_status || 'Sin revisión asignada')}</span>${journeyBadge}</div></div><div class="page-actions"><button class="btn secondary" data-action="go" data-route="/casos">Volver</button><a class="btn primary" href="/api/cases/${encodeURIComponent(id)}/export">Exportar expediente</a></div></div><nav class="case-tabs" aria-label="Secciones del expediente">${tabsForCase(state.user.role).map(([v,l]) => `<button class="case-tab ${tab === v ? 'active' : ''}" data-action="case-tab" data-tab="${esc(v)}" data-case-id="${esc(id)}">${l}</button>`).join('')}</nav>${caseTabContent(tab, detail, docs, product, journey)}</div>`);
}
window.legalaiCaseTab = (tab, id) => { state.activeCaseTab = tab; casePage(id); };
window.legalaiJourneyTransition = async (caseId, targetState) => {
  const reason = prompt(`Justificación para avanzar a ${humanize(targetState)}:`) || '';
  if (!reason) return;
  let confirmation = '';
  if (targetState === 'ENTREGADO') confirmation = prompt('Escribe exactamente ENTREGAR SOLUCIÓN para confirmar la entrega:') || '';
  try {
    await api(`/api/m24/case-journeys/${encodeURIComponent(caseId)}/transition`, { method:'POST', body:JSON.stringify({ target_state:targetState, reason, confirmation, evidence:{ channel:'web_m24_6' } }) });
    toast('Estado del recorrido actualizado.'); await casePage(caseId);
  } catch (error) { toast(error.message, 'danger'); }
};
window.legalaiFollowUpUpdate = async (caseId, followUpId, status) => {
  const note = prompt('Registra el resultado o evidencia del seguimiento:') || '';
  if (!note) return;
  try {
    await api(`/api/m24/case-journeys/${encodeURIComponent(caseId)}/follow-up`, { method:'POST', body:JSON.stringify({ follow_up_id:followUpId, status, note }) });
    toast('Seguimiento actualizado.'); await casePage(caseId);
  } catch (error) { toast(error.message, 'danger'); }
};
function caseTabContent(tab, detail, docs, product, journey) {
  if (state.user.role === 'client' && tab === 'resumen') return clientCaseOverview(detail, docs, product, journey);
  if (tab === 'resumen') {
    const result = detail.result || {};
    return `<section class="section-grid"><div class="card span-8"><div class="card-header"><div><h2>Estado del expediente</h2><p>Información esencial para decidir el siguiente paso.</p></div></div><div class="fact-grid"><div class="fact"><small>Solución</small><span>${esc(product.title || detail.product_code)}</span></div><div class="fact"><small>Estado</small><span>${esc(detail.status)}</span></div><div class="fact"><small>Riesgo</small><span>${esc(result.risk_label || riskLabels[detail.risk])}</span></div><div class="fact"><small>Ruta</small><span>${esc(result.route || 'En análisis')}</span></div><div class="fact"><small>Especialista</small><span>${esc(detail.specialist_name || 'Pendiente de asignación')}</span></div><div class="fact"><small>Actualización</small><span>${esc(dateText(detail.updated_at))}</span></div>${journey?.commerce ? `<div class="fact"><small>Nivel de servicio</small><span>${esc(journey.commerce.detail?.service_label || humanize(journey.commerce.service_mode))}</span></div><div class="fact"><small>Checkout</small><span>${money(journey.commerce.total || 0)} · ${esc(journey.commerce.status)}</span></div>` : ''}</div></div><div class="card span-4"><div class="card-header"><div><h3>Siguiente acción</h3><p>La acción depende del riesgo y de la información pendiente.</p></div></div><div class="demo-note mt-0"><b>${detail.risk === 'red' ? 'Revisión profesional obligatoria.' : 'Revisa soportes y documentos.'}</b><br>${esc(detail.risk === 'red' ? 'No se debe liberar un documento de impacto hasta resolver los bloqueos.' : 'Confirma que los datos y evidencias correspondan al caso real.')}</div><button class="btn primary btn-block mt-16" data-action="case-tab" data-tab="documentos" data-case-id="${esc(detail.id)}">Ver documentos</button></div><div class="card span-12"><div class="card-header"><div><h3>Controles activados</h3><p>Reglas y módulos derivados de la información registrada.</p></div></div><div class="product-meta">${(result.triggered_rules || []).slice(0, 10).map(x => `<span class="badge ${riskClass[x.risk] || 'blue'}">${esc(x.message || x.id)}</span>`).join('') || '<span class="badge">Sin controles adicionales visibles</span>'}</div></div></section>`;
  }
  if (tab === 'hechos') {
    const questions = detail.result?.product ? [] : [];
    return `<section class="card"><div class="card-header"><div><h2>Hechos y respuestas</h2><p>Información declarada para el diagnóstico. Debe contrastarse con los soportes.</p></div></div><div class="fact-grid">${Object.entries(detail.answers || {}).map(([k,v]) => `<div class="fact"><small>${esc(humanize(k))}</small><span>${esc(Array.isArray(v) ? v.join(', ') : v)}</span></div>`).join('')}</div></section>`;
  }
  if (tab === 'evidencias') return `<section class="card"><div class="card-header"><div><h2>${state.user.role==='client'?'Soportes de tu expediente':'Evidencias y soportes'}</h2><p>Los archivos deben ser legibles, pertinentes y corresponder con la cronología del caso.</p></div><button class="btn primary sm" data-action="go" data-route="/documentos">Abrir centro documental</button></div>${internalEmptyState({visual:'empty-evidence.svg',title:'Aún no hay soportes vinculados',text:'Prepara contratos, comunicaciones, comprobantes o certificaciones relacionados con el caso.',actionLabel:'Ir a mis documentos',route:'/documentos'})}</section>`;
  if (tab === 'ruta') {
    const result = detail.result || {};
    return `<section class="section-grid"><div class="card span-7"><div class="card-header"><div><h2>Ruta jurídica preliminar</h2><p>Resultado sujeto a verificación de hechos, términos y evidencia.</p></div></div><section class="result-banner ${detail.risk} no-margin"><div class="result-icon">⚖</div><div><h2>${esc(result.route || 'Ruta en análisis')}</h2><p>${esc(result.review_required ? 'Se requiere revisión profesional antes de continuar.' : 'La ruta puede continuar con los controles indicados.')}</p></div></section></div><div class="card span-5"><div class="card-header"><div><h3>Reglas de revisión</h3></div></div><ul class="check-list">${(result.review_rules || result.blocking_rules || []).map(x => `<li>${esc(x.message || x.action)}</li>`).join('') || '<li>No hay reglas de revisión adicionales visibles.</li>'}</ul></div></section>`;
  }
  if (tab === 'documentos') return `<section class="card"><div class="card-header"><div><h2>Documentos del expediente</h2><p>Borradores, anexos, auditorías y paquetes generados.</p></div><button class="btn secondary sm" data-action="go" data-route="/documentos">Ver biblioteca</button></div>${documentList(docs)}</section>`;
  if (state.user.role === 'client' && tab === 'revision') return clientReviewPanel(detail, journey);
  if (tab === 'revision') return `<section class="section-grid"><div class="card span-7"><div class="card-header"><div><h2>Revisión profesional</h2><p>Comentarios, decisiones y estado de aprobación del expediente.</p></div></div><div class="fact-grid"><div class="fact"><small>Especialista del caso</small><span>${esc(detail.specialist_name || 'Por asignar según riesgo')}</span></div><div class="fact"><small>Estado del caso</small><span>${esc(detail.review_status || 'Pendiente de revisión específica')}</span></div><div class="fact"><small>Aprobación jurídica M24.6</small><span>${esc(journey?.legal_approver_id || 'Pendiente')}</span></div><div class="fact"><small>QA independiente M24.6</small><span>${esc(journey?.qa_approver_id || 'Pendiente')}</span></div></div></div><div class="card span-5"><div class="card-header"><div><h3>Control de liberación</h3></div></div><div class="demo-note mt-0"><b>Compuerta por expediente.</b><br>La entrega exige documento vinculado, aprobación jurídica, QA por usuario distinto y confirmación expresa. No publica M23.2 automáticamente.</div></div></section>`;
  if (state.user.role === 'client' && tab === 'seguimiento') return clientFollowUpPanel(detail, journey);
  if (tab === 'seguimiento') {
    if (!journey) return `<section class="card"><div class="legal-notice danger">No fue posible cargar el recorrido operativo del expediente.</div></section>`;
    const transitions = (journey.transitions || []).slice().reverse();
    const followUps = journey.follow_ups || [];
    const nextButtons = (journey.available_transitions || []).map(target => `<button class="btn secondary sm" data-action="journey-transition" data-case-id="${esc(detail.id)}" data-target-state="${esc(target)}">${esc(humanize(target))}</button>`).join('');
    return `<section class="section-grid"><div class="card span-7"><div class="card-header"><div><span class="eyebrow">Recorrido M24.6</span><h2>${esc(humanize(journey.current_state))}</h2><p>Máquina de estados auditable, separada del estado histórico de M21.1.</p></div></div><div class="journey-actions">${nextButtons || '<span class="badge">Sin transiciones disponibles para este rol</span>'}</div><div class="journey-timeline">${transitions.map(t => `<div class="journey-event"><span class="journey-dot"></span><div><b>${esc(humanize(t.to_state))}</b><p>${esc(t.reason)}</p><small>${esc(t.actor_name)} · ${esc(dateText(t.created_at))}</small></div></div>`).join('')}</div></div><div class="card span-5"><div class="card-header"><div><h3>Plan posterior</h3><p>${esc(journey.follow_up_plan?.response_window_label || 'Pendiente de definir según el producto.')}</p></div></div><div class="demo-note mt-0"><b>Acción de entrega.</b><br>${esc(journey.follow_up_plan?.delivery_action || 'Validar canal, anexos y constancia.')}</div><div class="follow-up-list">${followUps.length ? followUps.map(item => `<div class="follow-up-item"><div><b>${esc(item.action_label)}</b><small>${esc(item.due_at ? dateText(item.due_at) : 'Sin fecha rígida')} · ${esc(humanize(item.effective_status))}</small>${item.note ? `<p>${esc(item.note)}</p>` : ''}</div>${item.status === 'pending' ? `<button class="btn secondary sm" data-action="follow-up-update" data-case-id="${esc(detail.id)}" data-follow-up-id="${esc(item.id)}" data-status="completed">Completar</button>` : ''}</div>`).join('') : '<div class="empty-state compact"><p>Las actividades se crean al entregar la solución.</p></div>'}</div><div class="legal-notice mt-16"><b>Control jurídico.</b> ${esc(journey.follow_up_notice || '')}</div></div></section>`;
  }
  return `<section class="card"><div class="card-header"><div><h2>Actividad</h2><p>Eventos relevantes del expediente.</p></div></div><div class="activity-line"><b>Expediente actualizado</b><span>${esc(dateText(detail.updated_at))}</span></div><div class="activity-line"><b>${esc(detail.review_status || 'Estado de revisión registrado')}</b><span>Especialista: ${esc(detail.specialist_name || 'Pendiente')}</span></div>${journey ? `<div class="activity-line"><b>Recorrido operativo</b><span>${esc(humanize(journey.current_state))}</span></div>` : ''}<div class="activity-line"><b>Expediente creado</b><span>${esc(dateText(detail.created_at))}</span></div></section>`;
}
function documentList(documents) {
  if (!documents.length) return internalEmptyState({ visual:'empty-documents-app.svg', title:'Aún no tienes documentos', text:'Los borradores, anexos y versiones aparecerán cuando avances en una solución.', actionLabel:state.user.role==='client'?'Explorar soluciones':'', route:'/soluciones' });
  return `<div class="m292-document-list">${documents.map(d => { const [label,cls]=friendlyDocumentState(d); return `<article class="m292-document-row"><div class="m292-doc-icon">${d.mime_type?.includes('word')?'W':d.mime_type?.includes('pdf')?'P':'▤'}</div><div><span class="badge ${cls}">${esc(label)}</span><h3>${esc(d.name)}</h3><p>${esc(d.case_title||humanize(d.kind))} · Actualizado ${esc(dateText(d.updated_at||d.created_at))}</p></div><div class="m292-doc-actions"><span>${esc(d.version||'Versión actual')}</span>${String(d.id).startsWith('DOC-')?`<a class="btn secondary sm" href="/api/documents/${encodeURIComponent(d.id)}/download">Descargar</a>`:''}</div></article>`; }).join('')}</div>`;
}
function documentsPage() {
  const ready=state.documents.filter(d=>friendlyDocumentState(d)[0]==='Listo').length;
  const review=state.documents.filter(d=>friendlyDocumentState(d)[0]==='En revisión').length;
  app.innerHTML = shell(`<div class="page"><section class="m292-document-hero"><div><span class="eyebrow">Centro documental</span><h1>${state.user.role==='client'?'Mis documentos':'Revisión documental'}</h1><p>Consulta borradores, anexos, versiones y estados sin perder la relación con cada expediente.</p><div class="m292-document-stats"><span><b>${state.documents.length}</b> documentos</span><span><b>${review}</b> en revisión</span><span><b>${ready}</b> listos</span></div></div><img src="/assets/brand-visuals/internal/document-workspace.svg" alt="Centro documental organizado"></section><section class="card"><div class="card-header"><div><h2>Documentos disponibles</h2><p>Cada archivo conserva expediente, versión, fecha y estado.</p></div>${state.user.role==='client'?`<button class="btn secondary sm" data-action="go" data-route="/casos">Ver expedientes</button>`:''}</div>${documentList(state.documents)}</section></div>`);
}
function reviewPage() {
  const reviewCases = state.cases.filter(c => /revisi/i.test(c.status || '') || /revisi/i.test(c.review_status || ''));
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow: 'Bandeja', title: 'Revisión profesional', description: 'Prioriza expedientes y consulta hechos, evidencia, documentos y decisiones desde un mismo espacio.' })}<section class="kpi-grid"><div class="kpi"><span class="kpi-label">Pendientes</span><div class="kpi-value"><strong>${reviewCases.length}</strong><span class="kpi-icon">${icons.review}</span></div></div><div class="kpi"><span class="kpi-label">Riesgo rojo</span><div class="kpi-value"><strong>${reviewCases.filter(x => x.risk === 'red').length}</strong><span class="kpi-icon">!</span></div></div><div class="kpi"><span class="kpi-label">Riesgo amarillo</span><div class="kpi-value"><strong>${reviewCases.filter(x => x.risk === 'yellow').length}</strong><span class="kpi-icon">◈</span></div></div><div class="kpi"><span class="kpi-label">Documentos</span><div class="kpi-value"><strong>${state.documents.length}</strong><span class="kpi-icon">${icons.docs}</span></div></div></section><section class="card"><div class="card-header"><div><h2>Casos por revisar</h2><p>Abre cada expediente para consultar su ruta jurídica, documentos, controles y actividad.</p></div></div>${caseList(reviewCases)}</section></div>`);
}
function statusPill(passed, yes='Cumple', no='Pendiente') { return `<span class="badge ${passed ? 'success' : 'warning'}">${esc(passed ? yes : no)}</span>`; }
function metricCard(label, value, icon, detail='') { return `<div class="kpi"><span class="kpi-label">${esc(label)}</span><div class="kpi-value"><strong>${esc(value)}</strong><span class="kpi-icon">${icon}</span></div>${detail ? `<small>${esc(detail)}</small>` : ''}</div>`; }
async function sourcesWorkspacePage() {
  const [normative, governance] = await Promise.all([api('/api/normative-updates'), api('/api/governance')]);
  const sources = normative.sources || [];
  const products = governance.products || [];
  const registered = products.reduce((sum, product) => sum + Number(product.registered_sources || 0), 0);
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow:'Conocimiento jurídico', title:'Fuentes y criterios', description:'Consulta la cobertura, vigencia y trazabilidad de las fuentes que respaldan cada solución jurídica.' })}<section class="kpi-grid">${metricCard('Fuentes registradas', registered || sources.length, icons.sources, 'Cobertura de las bibliotecas profundas')}${metricCard('Productos cubiertos', products.filter(p => Number(p.registered_sources || 0) > 0).length, icons.catalog, 'De 11 productos')}${metricCard('Alertas abiertas', normative.metrics?.open_updates || 0, icons.quality, 'Revisión normativa')}${metricCard('Cadenas íntegras', (normative.metrics?.broken_chains || 0) === 0 ? 'Sí' : 'Revisar', icons.shield, 'Auditoría')}</section><section class="section-grid"><div class="card span-7"><div class="card-header"><div><h2>Fuentes oficiales vigiladas</h2><p>Autoridades y registros configurados para actualización jurídica.</p></div></div><div class="source-grid">${sources.slice(0,18).map(source => `<article class="source-item"><div><b>${esc(source.authority)}</b><span>${esc(source.name)}</span></div><div>${statusPill(Boolean(source.official),'Oficial','Revisar')}<small>${esc(source.frequency || '')}</small></div></article>`).join('') || '<div class="empty-state compact"><p>No hay fuentes visibles en esta consulta.</p></div>'}</div></div><div class="card span-5"><div class="card-header"><div><h2>Cobertura por producto</h2><p>Fuentes registradas en las bibliotecas jurídicas profundas.</p></div></div><div class="readiness-list">${products.map(product => `<div class="readiness-row"><div><b>${esc(product.product_code)}</b><span>${esc(product.title)}</span></div><div>${statusPill(Number(product.registered_sources || 0) > 0, `${product.registered_sources} fuentes`, 'Sin fuentes')}</div></div>`).join('')}</div><div class="legal-notice"><b>Control por expediente.</b> El registro de fuentes del producto no reemplaza la verificación de vigencia, competencia, términos y aplicabilidad en el caso concreto.</div></div></section></div>`);
}
async function operationWorkspacePage() {
  const [dashboard, files, batches] = await Promise.all([api('/api/dashboard'), api('/api/file-center'), api('/api/review-batches')]);
  const stats = dashboard.stats || {};
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow:'Operación jurídica', title:'Operación', description:'Carga de trabajo, expedientes, documentos, evidencia y pendientes en una vista unificada.', actions:`<button class="btn primary" data-action="go" data-route="/casos">Ver expedientes</button>` })}<section class="kpi-grid">${metricCard('Expedientes', stats.cases || 0, icons.cases, `${stats.pending_tasks || 0} tareas pendientes`)}${metricCard('En revisión', stats.pending_reviews || 0, icons.review, 'Atención profesional')}${metricCard('Documentos', stats.documents || files.metrics?.documents || 0, icons.docs, 'Versiones y entregables')}${metricCard('Soportes pendientes', files.metrics?.pending_required || 0, icons.folder, 'Requisitos obligatorios')}</section><section class="section-grid"><div class="card span-8"><div class="card-header"><div><h2>Expedientes activos</h2><p>Prioriza por riesgo, estado y fecha de actualización.</p></div><button class="btn secondary sm" data-action="go" data-route="/casos">Ver todos</button></div>${caseList(dashboard.cases || state.cases, 8)}</div><div class="card span-4"><div class="card-header"><div><h2>Salud operativa</h2><p>Indicadores que requieren atención.</p></div></div><div class="readiness-list"><div class="readiness-row"><div><b>Riesgo rojo</b><span>Revisión obligatoria</span></div>${statusPill((stats.red || 0) === 0, 'Sin casos', `${stats.red || 0} casos`)}</div><div class="readiness-row"><div><b>Cobertura documental</b><span>Casos con soportes completos</span></div>${statusPill((files.metrics?.complete_cases || 0) === (files.metrics?.cases || 0), 'Completa', `${files.metrics?.complete_cases || 0}/${files.metrics?.cases || 0}`)}</div><div class="readiness-row"><div><b>Lotes activos</b><span>Revisión agrupada</span></div><span class="badge blue">${esc(batches.metrics?.active || 0)}</span></div></div></div></section></div>`);
}
async function catalogWorkspacePage() {
  const summary = await api('/api/catalog-summary');
  const approvedProducts = state.approval?.products || [];
  const approvalMap = Object.fromEntries(approvedProducts.map(x => [x.product_code, x]));
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow:'Catálogo jurídico', title:'Soluciones y bibliotecas', description:'Once productos aprobados para uso profesional controlado, con entrevistas, reglas, fuentes y documentos profundos.' })}<section class="catalog-hero"><div><span class="eyebrow">Cobertura integral</span><h2>De la necesidad jurídica al expediente y sus documentos.</h2><p>Los contratos profundos y los playbooks operativos se integran con el diagnóstico, la evidencia, la revisión y el seguimiento.</p></div><div class="catalog-hero-actions"><button class="btn gold" data-action="go" data-route="/biblioteca-contractual">Biblioteca contractual</button><button class="btn secondary light" data-action="go" data-route="/biblioteca-playbooks">Playbooks jurídicos</button></div></section><section class="kpi-grid">${metricCard('Productos', summary.products || 11, icons.catalog)}${metricCard('Preguntas', summary.questions || 0, '¿')}${metricCard('Reglas', summary.rules || 0, '◆')}${metricCard('Fuentes', summary.sources || 0, icons.sources)}</section><div class="catalog-table">${state.products.map(p => { const a=approvalMap[p.code] || {}; return `<a class="catalog-row" href="#/solucion/${encodeURIComponent(p.code)}"><div class="catalog-code">${esc(p.code)}</div><div class="catalog-main"><b>${esc(p.title)}</b><span>${esc(p.vertical)} · ${esc(p.description || 'Solución jurídica guiada')}</span></div><div class="catalog-status">${statusPill(Boolean(a.publication_authorized),'Uso controlado','Revisión')}</div><div class="catalog-arrow">›</div></a>`; }).join('')}</div></div>`);
}
async function qualityWorkspacePage() {
  const [rc, approval, doctor, governance] = await Promise.all([api('/api/rc-readiness'), api('/api/approval-status'), api('/api/infrastructure/doctor'), api('/api/governance')]);
  state.rcReadiness = rc;
  const content = rc.content || {};
  const runtime = rc.runtime || {};
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow:'Gobierno y calidad', title:'Preparación de la Preproducción segura', description:'Separación clara entre aprobación jurídica controlada, integridad del contenido y preparación del entorno de despliegue.' })}<section class="readiness-hero ${rc.release_candidate_ready ? 'ready' : 'pending'}"><div class="readiness-score">${esc(rc.score || 0)}<span>%</span></div><div><span class="eyebrow">Preproducción segura</span><h2>${esc(rc.release_candidate_ready ? 'Contenido listo para piloto controlado' : 'Existen compuertas pendientes')}</h2><p>${esc(rc.notice || '')}</p></div>${statusPill(Boolean(rc.release_candidate_ready),'RC lista','RC condicionada')}</section><section class="kpi-grid">${metricCard('Productos aprobados', approval.product_count || 0, icons.quality, `${approval.document_count || 0} documentos canónicos`)}${metricCard('Bibliotecas profundas', content.deep_products || 0, icons.library, 'M4 + M5')}${metricCard('Checks de contenido', `${content.passed || 0}/${content.total || 0}`, icons.review)}${metricCard('Checks de infraestructura', `${doctor.passed || 0}/${doctor.total || 0}`, icons.shield, doctor.profile || 'local')}</section><section class="section-grid"><div class="card span-7"><div class="card-header"><div><h2>Compuertas de contenido</h2><p>Aprobación, documentos, fuentes, integridad y experiencia final.</p></div></div><div class="readiness-list">${(content.checks || []).map(c => `<div class="readiness-row"><div><b>${esc(c.label)}</b><span>${esc(c.detail_text || '')}</span></div>${statusPill(Boolean(c.passed))}</div>`).join('')}</div></div><div class="card span-5"><div class="card-header"><div><h2>Entorno de despliegue</h2><p>El perfil local sirve para validación; producción exige controles adicionales.</p></div></div><div class="readiness-list">${(runtime.checks || doctor.checks || []).map(c => `<div class="readiness-row"><div><b>${esc(c.label)}</b><span>${esc(typeof c.detail === 'string' ? c.detail : '')}</span></div>${statusPill(Boolean(c.passed))}</div>`).join('')}</div></div><div class="card span-12"><div class="card-header"><div><h2>Gobierno consolidado</h2><p>Estado canónico de producto y publicación.</p></div></div><div class="fact-grid"><div class="fact"><small>Productos</small><span>${esc(governance.summary?.products || 11)}</span></div><div class="fact"><small>Aprobados controlados</small><span>${esc(governance.summary?.controlled_approved || approval.product_count || 0)}</span></div><div class="fact"><small>Publicación profesional</small><span>${approval.professional_publication_authorized ? 'Autorizada con controles' : 'Bloqueada'}</span></div><div class="fact"><small>Revisión externa independiente</small><span>${approval.independent_reviewers ? 'Sí' : 'No; responsable único'}</span></div></div></div></section></div>`);
}
async function settingsWorkspacePage() {
  const [config, doctor, users, security] = await Promise.all([api('/api/config'), api('/api/infrastructure/doctor'), api('/api/users'), api('/api/security')]);
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow:'Administración', title:'Configuración y seguridad', description:'Perfil de despliegue, usuarios, controles, sesiones e infraestructura.' })}<section class="section-grid"><div class="card span-7"><div class="card-header"><div><h2>Perfil de la aplicación</h2><p>Los datos sensibles de conexión no se exponen en esta vista.</p></div></div><div class="fact-grid"><div class="fact"><small>Perfil</small><span>${esc(config.deployment?.profile || 'local')}</span></div><div class="fact"><small>Entorno</small><span>${esc(config.deployment?.app_env || 'local')}</span></div><div class="fact"><small>Base de datos</small><span>${esc(config.deployment?.database_backend || '')}</span></div><div class="fact"><small>Almacenamiento</small><span>${esc(config.deployment?.object_storage_backend || '')}</span></div><div class="fact"><small>MFA disponible</small><span>${config.mfa_available ? 'Sí' : 'No'}</span></div><div class="fact"><small>Cookies seguras</small><span>${config.deployment?.secure_cookies ? 'Sí' : 'No · solo entorno local'}</span></div></div></div><div class="card span-5"><div class="card-header"><div><h2>Seguridad operativa</h2><p>Sesiones y eventos recientes.</p></div></div><div class="kpi-stack"><div><span>Sesiones activas</span><b>${esc(security.active_sessions || 0)}</b></div><div><span>Eventos registrados</span><b>${esc((security.events || []).length)}</b></div><div><span>Archivos cargados</span><b>${esc((security.uploads || []).length)}</b></div></div></div><div class="card span-12"><div class="card-header"><div><h2>Usuarios y roles</h2><p>Separación de acceso para clientes, especialistas y administración.</p></div></div><div class="user-grid">${(users || []).map(u => `<article class="user-card"><span class="avatar">${esc(initials(u.name))}</span><div><b>${esc(u.name)}</b><span>${esc(u.email)}</span><small>${esc(roleLabels[u.role] || u.role)} · ${esc(u.specialty || '')}</small></div>${statusPill(Boolean(u.active),'Activo','Inactivo')}</article>`).join('')}</div></div><div class="card span-12"><div class="card-header"><div><h2>Diagnóstico de infraestructura</h2><p>${esc(doctor.notice || '')}</p></div></div><div class="readiness-list columns">${(doctor.checks || []).map(c => `<div class="readiness-row"><div><b>${esc(c.label)}</b><span>${esc(typeof c.detail === 'string' ? c.detail : '')}</span></div>${statusPill(Boolean(c.passed))}</div>`).join('')}</div></div></section></div>`);
}
async function libraryHubPage() {
  await loadDeepLibraries();
  const quality = await api('/api/product-quality');
  const contractual = state.contractualLibrary || {};
  const playbooks = state.playbookLibrary || {};
  const cm = contractual.metrics || {};
  const pm = playbooks.metrics || {};
  const qc = quality.counts || {};
  const reviewed = (quality.products || []).filter(product => product.status === 'reviewed');
  const reviewRows = (quality.products || []).map(product => `<div class="quality-product-row"><div><b>${esc(product.product_code)} · ${esc(product.title)}</b><span>${esc(product.next_action || '')}</span></div><span class="badge ${product.status === 'reviewed' ? 'green' : 'yellow'}">${product.status === 'reviewed' ? `Revalidado ${quality.version || ''}` : 'Revisión pendiente'}</span></div>`).join('');
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow:'Bibliotecas jurídicas', title:'Documentos profundos y rutas operativas', description:'Accede a la referencia documental vigente de los once productos: contratos maestros con anexos y playbooks con diagnóstico, actuaciones, términos y seguimiento.' })}<section class="library-hub-grid"><article class="library-hub-card contractual"><span class="eyebrow">Contratos</span><h2>Biblioteca contractual profunda</h2><p>Cuatro productos contractuales con documento principal, anexos operativos, paquete consolidado y fuentes oficiales.</p><div class="library-hub-metrics"><span><b>${esc(cm.products || 0)}</b> productos</span><span><b>${esc(cm.documents || 0)}</b> documentos</span><span><b>${esc(cm.pages || 0)}</b> páginas</span><span><b>${esc(cm.clauses || 0)}</b> cláusulas</span></div><button class="btn gold" data-action="go" data-route="/biblioteca-contractual">Abrir contratos</button></article><article class="library-hub-card playbooks"><span class="eyebrow">Actuaciones</span><h2>Playbooks jurídicos profundos</h2><p>Siete rutas no contractuales con diagnóstico, evidencia, documentos, términos, escalamiento y seguimiento.</p><div class="library-hub-metrics"><span><b>${esc(pm.products || 0)}</b> productos</span><span><b>${esc(pm.documents || 0)}</b> documentos</span><span><b>${esc(pm.pages || 0)}</b> páginas</span><span><b>${new Intl.NumberFormat('es-CO').format(pm.words || 0)}</b> palabras</span></div><button class="btn primary" data-action="go" data-route="/biblioteca-playbooks">Abrir playbooks</button></article></section><section class="card mt-22 product-quality-panel"><div class="card-header"><div><span class="eyebrow">Control sustantivo ${esc(quality.version || '')}</span><h2>Estado de revalidación jurídica</h2><p>La aprobación histórica y la última revisión normativa se presentan como estados distintos.</p></div><span class="quality-counter">${esc(qc.reviewed || 0)}/11</span></div><div class="quality-progress"><span class="progress-${Math.max(0, Math.min(11, Number(qc.reviewed || 0)))}"></span></div><div class="quality-summary"><b>${reviewed.length ? `${esc(reviewed[0].product_code)} revalidado el ${esc(reviewed[0].verified_at)}` : 'Ningún producto revalidado en esta ola'}</b><span>${esc(quality.notice || '')}</span></div><details class="library-detail"><summary>Ver estado de los 11 productos</summary><div class="quality-product-list">${reviewRows}</div></details></section><section class="card mt-22"><div class="card-header"><div><h2>Regla de uso</h2><p>La biblioteca muestra contenido canónico aprobado para uso profesional controlado.</p></div></div><div class="legal-notice"><b>Referencia vigente dentro de la aplicación.</b> Los modelos históricos, notas de desarrollo y estados anteriores no deben presentarse como entregables finales. Cada expediente conserva validación específica de hechos, fuentes, términos, anexos y nivel de riesgo.</div></section></div>`);
}
async function contractualLibraryPage() {
  await loadDeepLibraries();
  const [quality, employmentQuality] = await Promise.all([api('/api/product-quality'), api('/api/product-quality/CO-LA-002')]);
  const qualityByCode = Object.fromEntries((quality.products || []).map(product => [product.product_code, product]));
  const data = state.contractualLibrary;
  const metric = data.metrics || {};
  const productCards = (data.products || []).map(product => {
    const qualityRow = qualityByCode[product.code] || { status:'pending' };
    const reviewed = qualityRow.status === 'reviewed';
    const detail = product.code === 'CO-LA-002' ? employmentQuality : null;
    const packageDoc = (product.documents || []).find(doc => doc.kind === 'consolidated_package');
    const mainDoc = (product.documents || []).find(doc => doc.kind === 'main_contract');
    const sourceList = (product.sources || []).map(source => `<li>${esc(source.reference)} <span class="muted">· verificada ${esc(source.verified_at)}</span></li>`).join('');
    const docs = (product.documents || []).filter(doc => doc.kind !== 'consolidated_package').map(doc => `<div class="document-row"><div><b>${esc(doc.title)}</b><span>${esc(doc.subtitle)} · ${esc(doc.pages)} páginas · ${esc(doc.words)} palabras</span></div><div class="document-actions"><a class="btn secondary sm" href="/assets/contractual-library-m4/${esc(doc.docx)}" download>DOCX</a><a class="btn secondary sm" href="/assets/contractual-library-m4/${esc(doc.pdf)}" target="_blank" rel="noopener">PDF</a></div></div>`).join('');
    const controls = (detail?.verified_controls || []).map(control => `<div class="legal-control"><small>${esc(control.label)}</small><b>${esc(control.value)}</b><span>Vigente desde ${esc(control.effective_from)}</span></div>`).join('');
    const findings = (detail?.findings || []).map(finding => `<li><b>${esc(finding.title)}</b><span>${esc(finding.resolution)}</span></li>`).join('');
    return `<section class="card contractual-product-card ${reviewed ? 'quality-reviewed' : 'quality-pending'}">
      <div class="card-header"><div><span class="eyebrow">${esc(product.code)}</span><h2>${esc(product.title)}</h2><p>${esc(product.metrics.package_pages)} páginas consolidadas · ${esc(product.metrics.package_words)} palabras · ${esc(product.metrics.clauses)} cláusulas contabilizadas en la biblioteca.</p></div><div class="quality-badges"><span class="badge green">Uso controlado</span><span class="badge ${reviewed ? 'blue' : 'yellow'}">${reviewed ? `Revalidado ${quality.version || ''}` : 'Revisión sustantiva pendiente'}</span></div></div>
      ${reviewed ? `<div class="quality-review-banner"><div><b>Verificación normativa: ${esc(detail.verified_at)}</b><span>${esc(detail.review_scope)}</span></div><span>${esc((detail.verified_controls || []).length)} controles</span></div><div class="legal-controls-grid">${controls}</div>` : `<div class="quality-pending-note">Este producto conserva su aprobación controlada, pero aún no ha pasado por la revalidación sustantiva producto por producto de la ola sustantiva vigente.</div>`}
      <div class="fact-grid"><div class="fact"><small>Documento principal</small><span>${esc(mainDoc?.pages || 0)} páginas · ${esc(mainDoc?.words || 0)} palabras</span></div><div class="fact"><small>Paquete completo</small><span>${esc(product.metrics.package_pages)} páginas · ${esc(product.metrics.documents)} documentos</span></div><div class="fact"><small>Fuentes oficiales</small><span>${esc((product.sources || []).length)}</span></div></div>
      <div class="library-primary-actions">${mainDoc ? `<a class="btn gold" href="/assets/contractual-library-m4/${esc(mainDoc.docx)}" download>Descargar contrato maestro</a>` : ''}${packageDoc ? `<a class="btn primary" href="/assets/contractual-library-m4/${esc(packageDoc.docx)}" download>Descargar paquete completo</a><a class="btn secondary" href="/assets/contractual-library-m4/${esc(packageDoc.pdf)}" target="_blank" rel="noopener">Vista previa PDF</a>` : ''}</div>
      <details class="library-detail"><summary>Ver documentos y anexos</summary><div class="document-list">${docs}</div></details>
      ${reviewed ? `<details class="library-detail"><summary>Hallazgos y alcance de la revisión vigente</summary><ul class="quality-finding-list">${findings}</ul><p class="demo-note">${esc(detail.legal_notice || '')}</p></details>` : ''}
      <details class="library-detail"><summary>Fuentes y control jurídico</summary><ul>${sourceList}</ul><p class="demo-note">La aprobación es multietapa por responsable único y no constituye revisión externa independiente. Antes de firma deben verificarse hechos, capacidad, cuantías, anexos, riesgo, normas vigentes y coherencia con la ejecución real.</p></details>
    </section>`;
  }).join('');
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow: 'Catálogo jurídico', title: 'Biblioteca contractual profunda', description: 'Cuatro contratos maestros desarrollados con anexos operativos, paquetes consolidados, fuentes oficiales y formato profesional. La extensión del contrato principal se diferencia claramente de la del paquete completo.' })}<section class="kpi-grid"><div class="kpi"><span class="kpi-label">Productos P0</span><div class="kpi-value"><strong>${esc(metric.products || 0)}</strong><span class="kpi-icon">§</span></div></div><div class="kpi"><span class="kpi-label">Documentos</span><div class="kpi-value"><strong>${esc(metric.documents || 0)}</strong><span class="kpi-icon">${icons.docs}</span></div></div><div class="kpi"><span class="kpi-label">Páginas</span><div class="kpi-value"><strong>${esc(metric.pages || 0)}</strong><span class="kpi-icon">▤</span></div></div><div class="kpi"><span class="kpi-label">Productos revalidados</span><div class="kpi-value"><strong>${esc(quality.counts?.reviewed || 0)}</strong><span class="kpi-icon">✓</span></div></div></section><div class="result-banner yellow"><div class="result-icon">!</div><div><h2>Uso profesional controlado</h2><p>${esc(data.notice || '')}</p></div></div><div class="contractual-library-grid">${productCards}</div></div>`);
}
async function playbookLibraryPage() {
  await loadDeepLibraries();
  const data = state.playbookLibrary;
  const metric = data.metrics || {};
  const productCards = (data.products || []).map(product => {
    const packageDoc = (product.documents || []).find(doc => doc.kind === 'consolidated_package');
    const sourceList = (product.sources || []).map(source => `<li>${esc(source.title || source.reference || 'Fuente oficial')} <span class="muted">· ${esc(source.status || '')} · verificada ${esc(source.last_verified || source.verified_at || '')}</span></li>`).join('');
    const docs = (product.documents || []).filter(doc => doc.kind !== 'consolidated_package').map(doc => `<div class="document-row"><div><b>${esc(doc.title)}</b><span>${esc(doc.subtitle)} · ${esc(doc.pages)} páginas · ${esc(doc.words)} palabras</span></div><div class="document-actions"><a class="btn secondary sm" href="/assets/playbook-library-m5/${esc(doc.docx)}" download>DOCX</a><a class="btn secondary sm" href="/assets/playbook-library-m5/${esc(doc.pdf)}" target="_blank" rel="noopener">PDF</a></div></div>`).join('');
    return `<section class="card contractual-product-card">
      <div class="card-header"><div><span class="eyebrow">${esc(product.code)}</span><h2>${esc(product.title)}</h2><p>${esc(product.metrics.package_pages)} páginas consolidadas · ${esc(product.metrics.package_words)} palabras · diagnóstico, evidencia, actuaciones y escalamiento.</p></div><span class="badge green">Uso controlado</span></div>
      <div class="fact-grid"><div class="fact"><small>Documentos</small><span>${esc(product.metrics.documents)}</span></div><div class="fact"><small>Páginas totales</small><span>${esc(product.metrics.pages)}</span></div><div class="fact"><small>Fuentes oficiales</small><span>${esc((product.sources || []).length)}</span></div></div>
      <div class="library-primary-actions">${packageDoc ? `<a class="btn primary" href="/assets/playbook-library-m5/${esc(packageDoc.docx)}" download>Descargar paquete DOCX</a><a class="btn secondary" href="/assets/playbook-library-m5/${esc(packageDoc.pdf)}" target="_blank" rel="noopener">Abrir paquete PDF</a>` : ''}</div>
      <details class="library-detail"><summary>Ver documentos y actuaciones</summary><div class="document-list">${docs}</div></details>
      <details class="library-detail"><summary>Fuentes, límites y control jurídico</summary><ul>${sourceList}</ul><p class="demo-note">La aprobación es multietapa por responsable único y no constituye revisión externa independiente. No se prometen decisiones, pagos, nulidades, retiros, sanciones o resultados automáticos. Cada actuación exige verificar competencia, términos, prueba, canal y riesgo del expediente.</p></details>
    </section>`;
  }).join('');
  app.innerHTML = shell(`<div class="page">${pageHeader({ eyebrow: 'Catálogo jurídico', title: 'Playbooks jurídicos profundos', description: 'Siete productos no contractuales organizados como expedientes operativos: diagnóstico, evidencia, actuaciones, documentos, términos, seguimiento y escalamiento.' })}<section class="kpi-grid"><div class="kpi"><span class="kpi-label">Productos</span><div class="kpi-value"><strong>${esc(metric.products || 0)}</strong><span class="kpi-icon">§</span></div></div><div class="kpi"><span class="kpi-label">Documentos</span><div class="kpi-value"><strong>${esc(metric.documents || 0)}</strong><span class="kpi-icon">${icons.docs}</span></div></div><div class="kpi"><span class="kpi-label">Páginas</span><div class="kpi-value"><strong>${esc(metric.pages || 0)}</strong><span class="kpi-icon">▤</span></div></div><div class="kpi"><span class="kpi-label">Palabras</span><div class="kpi-value"><strong>${new Intl.NumberFormat('es-CO').format(metric.words || 0)}</strong><span class="kpi-icon">Aa</span></div></div></section><div class="result-banner yellow"><div class="result-icon">!</div><div><h2>Uso profesional controlado</h2><p>${esc(data.notice || '')}</p></div></div><div class="contractual-library-grid">${productCards}</div></div>`);
}
function executiveDemoPage() {
  const approved = state.approval?.product_count || state.products.length || 11;
  const featured = [
    ['CO-LA-002','Contrato de trabajo','Contratación formal, jornada, remuneración, funciones, protección reforzada y anexos.'],
    ['CO-EM-003','Prestación de servicios','Objeto, entregables, aceptación, pagos, datos, IA, propiedad intelectual y cierre.'],
    ['CO-AR-001','Arrendamiento de vivienda','Canon, inventario, servicios, garantías, entrega, restitución y terminación.'],
    ['CO-CD-003','Protección al consumidor','Garantía, retracto, reversión, evidencia, términos y seguimiento.'],
  ];
  const productCards = featured.map(([code,title,description]) => `<article class="demo-product-card"><span class="eyebrow">${esc(code)}</span><h3>${esc(title)}</h3><p>${esc(description)}</p><button class="btn secondary sm" data-action="go" data-route="${publicProductRoute(code)}">Ver solución</button></article>`).join('');
  app.innerHTML = shell(`<div class="page executive-demo-page">
    <section class="executive-hero"><div><span class="eyebrow">LegalAIZ.it · versión final para piloto y demostración</span><h1>Del problema jurídico a una solución documentada, revisable y trazable.</h1><p>LegalAIZ.it combina entrevistas inteligentes, reglas jurídicas, documentos profesionales, revisión experta y seguimiento del expediente en una experiencia única.</p><div class="button-group"><button class="btn gold" data-action="go" data-route="/nuevo">Probar recorrido del cliente</button><button class="btn secondary" data-action="go" data-route="/operacion">Ver operación jurídica</button></div></div><div class="executive-promise"><b>Más que respuestas, soluciones.</b><span>IA guiada + contenido jurídico aprobado + expertos</span></div></section>
    <section class="kpi-grid"><div class="kpi"><span class="kpi-label">Productos jurídicos</span><div class="kpi-value"><strong>${esc(approved)}</strong><span class="kpi-icon">§</span></div></div><div class="kpi"><span class="kpi-label">Preguntas vinculadas</span><div class="kpi-value"><strong>473</strong><span class="kpi-icon">?</span></div></div><div class="kpi"><span class="kpi-label">Reglas jurídicas</span><div class="kpi-value"><strong>273</strong><span class="kpi-icon">⚖</span></div></div><div class="kpi"><span class="kpi-label">Escenarios validados</span><div class="kpi-value"><strong>110</strong><span class="kpi-icon">✓</span></div></div></section>
    <section class="card mt-22"><div class="card-header"><div><span class="eyebrow">Recorrido integral</span><h2>Una plataforma, no una colección de formatos</h2></div></div><div class="executive-flow"><div><span>1</span><b>Entiende</b><p>El usuario describe su necesidad y recibe una ruta explicable.</p></div><div><span>2</span><b>Estructura</b><p>Preguntas progresivas recopilan hechos, datos y soportes.</p></div><div><span>3</span><b>Genera</b><p>La fábrica activa cláusulas, módulos, anexos y fuentes aplicables.</p></div><div><span>4</span><b>Revisa</b><p>Especialista y QA controlan consistencia, riesgo y presentación.</p></div><div><span>5</span><b>Acompaña</b><p>El expediente conserva versiones, tareas, términos y seguimiento.</p></div></div></section>
    <section class="mt-28">${pageHeader({eyebrow:'Demostraciones recomendadas',title:'Cuatro recorridos para presentar la plataforma',description:'Casos suficientemente distintos para mostrar contratos, reclamaciones, reglas, documentos y seguimiento.'})}<div class="demo-product-grid">${productCards}</div></section>
    <section class="section-grid mt-22"><div class="card span-7"><div class="card-header"><div><h2>Controles verificables</h2></div></div><ul class="check-list"><li>RBAC y aislamiento por usuario, expediente y rol.</li><li>Revisiones documentales inmutables y comparación de versiones.</li><li>Aprobación jurídica, QA, auditoría y confirmación de entrega.</li><li>Datos y archivos cifrados, MFA y trazabilidad de seguridad.</li><li>Biblioteca jurídica con fuentes, reglas y módulos condicionales.</li></ul></div><div class="card span-5"><div class="card-header"><div><h2>Alcance de esta edición</h2></div></div><div class="legal-notice"><b>Lista para demostración y piloto controlado.</b> Los pagos son simulados y la producción pública exige infraestructura, revisión independiente y controles externos adicionales.</div><div class="button-group mt-18"><button class="btn primary" data-action="go" data-route="/centro-piloto">Ver preparación</button><button class="btn secondary" data-action="go" data-route="/calidad">Ver calidad</button></div></div></section>
  </div>`);
}
function notificationsPage() { app.innerHTML = m293NotificationsPage({ shell, pageHeader, user:state.user, cases:state.cases, documents:state.documents }); } function helpCenterPage() { app.innerHTML = m293HelpCenterPage({ shell, pageHeader, user:state.user }); } function accessibilityPage() { app.innerHTML = m294AccessibilityPage({ shell, pageHeader }); }
function notFoundPage(message = 'No encontramos la página solicitada.') {
  app.innerHTML = shell(`<div class="page"><div class="empty-state"><div class="empty-icon">?</div><h1>Página no disponible</h1><p>${esc(message)}</p><button class="btn primary" data-action="go" data-route="/">Volver al inicio</button></div></div>`);
}
async function router() {
  const path = currentPath();
  if (!state.user) {
    if (path === '/login') return loginPage();
    if (path === '/soluciones') return m291Public.publicSolutionsHubPage();
    if (path === '/como-funciona') return m291Public.publicHowWorksPage();
    if (path === '/para-personas') return m291Public.publicAudiencePage('personas');
    if (path === '/para-empresas') return m291Public.publicAudiencePage('empresas');
    if (path === '/confianza') return m291Public.publicTrustPage();
    if (path === '/preguntas-frecuentes') return m291Public.publicFaqPage();
    if (path === '/nosotros') return m291Public.publicAboutPage();
    if (path === '/orientador') return m295Experience.finderPage(); if (path === '/agenda-demo') return m295Experience.demoPage(); if (path === '/privacidad-medicion') return m295Experience.measurementPage();
    if (path.startsWith('/soluciones/')) { const slug = decodeURIComponent(path.split('/')[2] || ''); return m262Gold.publicProductPage(publicProductCodeBySlug[slug] || slug); }
    if (path.startsWith('/solucion/')) return m262Gold.publicProductPage(decodeURIComponent(path.split('/')[2] || ''));
    if (path !== '/') return go('/');
    return m291Public.publicLandingPage();
  }
  if (state.mfaEnrollmentRequired) return mfaEnrollmentPage();
  try {
    if (path === '/login') return go('/');
    if (path === '/') return homePage();
    if (path === '/demo-ejecutiva') return executiveDemoPage();
    if (path === '/demo-documental') return m317DemoReality.page();
    if (path === '/demo-expedientes') return m318CaseDemo.page();
    if (path === '/soluciones') return solutionsPage();
    if (path.startsWith('/soluciones/')) { const slug = decodeURIComponent(path.split('/')[2] || ''); return productDetailPage(publicProductCodeBySlug[slug] || slug); }
    if (path === '/nuevo') return guidedStartPage();
    if (path.startsWith('/solucion/')) return productDetailPage(decodeURIComponent(path.split('/')[2] || ''));
    if (path.startsWith('/nuevo/')) return wizardPage(decodeURIComponent(path.split('/')[2] || ''));
    if (path.startsWith('/checkout/')) return checkoutPage(decodeURIComponent(path.split('/')[2] || ''));
    if (path === '/casos') return casesPage();
    if (path.startsWith('/caso/')) return casePage(decodeURIComponent(path.split('/')[2] || ''));
    if (path === '/documentos') return documentsPage();
    if (path === '/notificaciones') return notificationsPage();
    if (path === '/ayuda') return helpCenterPage();
    if (path === '/accesibilidad') return accessibilityPage();
    if (path === '/experiencia') return m295Experience.adminExperiencePage();
    if (path === '/revision') return reviewPage();
    if (path === '/fuentes') return sourcesWorkspacePage();
    if (path === '/operacion') return operationWorkspacePage();
    if (path === '/catalogo') return catalogWorkspacePage();
    if (path === '/bibliotecas') return libraryHubPage();
    if (path === '/biblioteca-contractual') return contractualLibraryPage();
    if (path === '/biblioteca-playbooks') return playbookLibraryPage();
    if (path === '/maduracion-juridica') return m24CandidateLibraryPage({ shell, pageHeader });
    if (path === '/calidad') return qualityWorkspacePage();
    if (path === '/piloto') return state.user.role === 'client' ? m302Participant.page() : go('/centro-piloto');
    if (path === '/red-profesional') return m249Professional.page();
    if (path === '/centro-piloto') return m301Pilot.page(); if (path === '/preparacion-piloto') return go('/centro-piloto'); if (path === '/preproduccion') return m311Preproduction.page();
    if (path === '/configuracion') return settingsWorkspacePage();
    return notFoundPage();
  } catch (error) {
    console.error(error);
    app.innerHTML = shell(`<div class="page"><div class="result-banner red"><div class="result-icon">!</div><div><h2>No fue posible cargar esta vista</h2><p>${esc(error.message)}</p></div><button class="btn secondary" data-action="reload">Reintentar</button></div></div>`);
  }
}
async function renderRoute() { await router(); applyUiPreferences(); announceRoute(currentPath(), state.products, state.cases); m295Experience.afterRender(currentPath()); setTimeout(() => document.getElementById('main-content')?.focus({preventScroll:true}), 20); }
async function bootstrap() {
  m295Experience.install(); try { state.config = await api('/api/config'); } catch { state.config = {}; }
  try {
    const auth = await api('/api/auth/me');
    if (auth.authenticated) { state.user = auth.user; state.csrf = auth.csrf_token; state.mfaEnrollmentRequired = Boolean(auth.mfa_enrollment_required); if (!state.mfaEnrollmentRequired) await preload(); }
  } catch {}
  await renderRoute();
}
window.addEventListener('hashchange', async () => { state.mobileNav = false; state.lastVisitedRoute = currentPath(); await renderRoute(); }); window.addEventListener('storage', event => { if ((event.key?.startsWith('legalaizit:draft:') || event.key?.startsWith('legalaizit:m1:draft:')) && state.wizard) loadDraft(state.wizard.code); });
bootstrap();
