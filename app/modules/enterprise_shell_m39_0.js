import { currentPath, state } from '../core.js';

const CLIENT_ROLE = 'client';

const NAV_LABELS = Object.freeze({
  '/': 'Inicio',
  '/nuevo': 'Iniciar asunto',
  '/casos': 'Expedientes',
  '/soluciones': 'Soluciones',
  '/documentos': 'Documentos',
  '/notificaciones': 'Notificaciones',
  '/ayuda': 'Centro de ayuda',
  '/accesibilidad': 'Accesibilidad',
});

const GROUP_LABELS = Object.freeze({
  'Mi ruta': 'Operación jurídica',
  'Consulta': 'Recursos',
  'Acompañamiento': 'Acompañamiento',
});

const TITLE_LABELS = Object.freeze({
  '/': 'Inicio',
  '/nuevo': 'Iniciar asunto',
  '/casos': 'Expedientes',
  '/soluciones': 'Soluciones',
  '/documentos': 'Documentos',
  '/notificaciones': 'Notificaciones',
  '/ayuda': 'Centro de ayuda',
  '/accesibilidad': 'Accesibilidad',
});

function isClient() {
  return state.user?.role === CLIENT_ROLE;
}

function routeLabel(path = currentPath()) {
  if (path.startsWith('/caso/')) return 'Expediente';
  if (path.startsWith('/nuevo/')) return 'Nuevo asunto';
  if (path.startsWith('/soluciones/')) return 'Solución jurídica';
  return TITLE_LABELS[path] || 'Espacio jurídico';
}

function enhanceTopbar() {
  const brand = document.querySelector('.topbar .brand-button');
  if (brand && brand.dataset.m390EnterpriseBrand !== '1') {
    brand.innerHTML = `<span class="m390-wordmark"><span class="m390-wordmark-mark" aria-hidden="true">M</span><span class="m390-wordmark-copy"><b>Meridiano</b><small>Empresas</small></span></span>`;
    brand.setAttribute('aria-label', 'Ir al inicio de Meridiano Empresas');
    brand.dataset.m390EnterpriseBrand = '1';
  }

  const context = document.querySelector('.workspace-context');
  if (context && currentPath() === '/') {
    const group = context.querySelector('span');
    const page = context.querySelector('b');
    if (group) group.textContent = 'Meridiano Empresas';
    if (page) page.textContent = 'Inicio';
  }

  const accountRole = document.querySelector('.account-copy span');
  if (accountRole && accountRole.dataset.m390EnterpriseRole !== '1') {
    accountRole.textContent = 'Cliente empresarial';
    accountRole.dataset.m390EnterpriseRole = '1';
  }
}

function enhanceSidebar() {
  const brandCopy = document.querySelector('.sidebar-brand-copy');
  if (brandCopy && brandCopy.dataset.m390EnterpriseCopy !== '1') {
    brandCopy.innerHTML = '<b>Meridiano Empresas</b><span>Tu operación jurídica organizada</span>';
    brandCopy.dataset.m390EnterpriseCopy = '1';
  }

  const primary = document.querySelector('.sidebar-primary[data-route="/nuevo"] b');
  if (primary) primary.textContent = 'Iniciar asunto';

  document.querySelectorAll('.nav-group').forEach(group => {
    const label = group.querySelector('.nav-label');
    const mapped = GROUP_LABELS[String(label?.textContent || '').trim()];
    if (label && mapped) label.textContent = mapped;
  });

  document.querySelectorAll('.side-nav .nav-link').forEach(link => {
    const route = String(link.getAttribute('href') || '').replace(/^#/, '');
    const mapped = NAV_LABELS[route];
    const text = link.querySelector('span:last-child');
    if (mapped && text) text.textContent = mapped;
  });

  const sidebarBottom = document.querySelector('.sidebar-bottom');
  if (sidebarBottom && !sidebarBottom.querySelector('[data-m390-engine-note]')) {
    sidebarBottom.insertAdjacentHTML('beforeend', '<p class="m390-engine-note" data-m390-engine-note="1">Tecnología jurídica sobre infraestructura LegalAIZ.</p>');
  }
}

export function applyEnterpriseShell() {
  if (!isClient()) {
    delete document.documentElement.dataset.m390Enterprise;
    return;
  }

  document.documentElement.dataset.m390Enterprise = '1';
  enhanceTopbar();
  enhanceSidebar();
  document.title = `Meridiano Empresas · ${routeLabel()}`;
}

let scheduled = false;
function scheduleApply() {
  if (scheduled) return;
  scheduled = true;
  queueMicrotask(() => {
    scheduled = false;
    applyEnterpriseShell();
  });
}

const observer = new MutationObserver(scheduleApply);
observer.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', scheduleApply);
window.addEventListener('popstate', scheduleApply);
scheduleApply();
