import { publicProducts, publicProductRoute, setPublicTitle } from './public_m29_1.js';

const CONSENT_KEY = 'legalaizit:m295:measurement-consent';
const finderState = { audience:'', topic:'', goal:'' };
const intakeState = { mode:'story', session:null, recoveryCode:'', editing:false };
let installed = false;
let lastTrackedPath = '';
let performanceInstalled = false;

const safeStorage = {
  get(key, fallback='') { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch {} },
};

export function measurementConsent() { return safeStorage.get(CONSENT_KEY, 'unset'); }
export function setMeasurementConsent(value='unset') {
  const normalized = ['granted','denied'].includes(value) ? value : 'unset';
  safeStorage.set(CONSENT_KEY, normalized);
  return normalized;
}

function deviceClass() {
  const width = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
  if (width <= 640) return 'mobile';
  if (width <= 1024) return 'tablet';
  return 'desktop';
}

export function routeSurface(path='/', authenticated=false) {
  if (path === '/') return authenticated ? 'dashboard' : 'home';
  if (path === '/soluciones') return 'solutions';
  if (path.startsWith('/soluciones/') || path.startsWith('/solucion/')) return 'product';
  if (path === '/para-personas') return 'people';
  if (path === '/para-empresas') return 'business';
  if (path === '/confianza') return 'trust';
  if (path === '/nosotros') return 'about';
  if (path === '/orientador') return 'finder';
  if (path === '/agenda-demo') return 'demo';
  if (path === '/login') return 'login';
  if (path.startsWith('/nuevo')) return 'wizard';
  if (path.startsWith('/caso') || path === '/casos') return 'cases';
  if (path === '/documentos') return 'documents';
  if (path === '/ayuda') return 'help';
  if (path === '/accesibilidad' || path === '/privacidad-medicion') return 'accessibility';
  if (path === '/experiencia') return 'admin_experience';
  return 'other';
}

export async function trackExperience(api, event, { path='/', authenticated=false, metricBucket='none' }={}) {
  if (measurementConsent() !== 'granted') return { recorded:false };
  const allowedEvent = String(event || '').slice(0,48);
  try {
    return await api('/api/public/experience-event', {
      method:'POST',
      body:JSON.stringify({
        consent:true,
        event:allowedEvent,
        surface:routeSurface(path, authenticated),
        device:deviceClass(),
        metric_bucket:metricBucket,
      }),
    });
  } catch { return { recorded:false }; }
}

export function optimizeMedia(root=document) {
  const images = root.querySelectorAll?.('img') || [];
  images.forEach((image, index) => {
    const critical = image.closest('.public-hero,.m29-page-hero,.login-story,.boot-screen') || index === 0;
    image.decoding = 'async';
    image.loading = critical ? 'eager' : 'lazy';
    if (critical) image.fetchPriority = 'high';
  });
}

function performanceBucket(milliseconds) {
  if (!Number.isFinite(milliseconds) || milliseconds <= 0) return 'none';
  if (milliseconds <= 1800) return 'fast';
  if (milliseconds <= 3500) return 'needs_improvement';
  return 'slow';
}

function installPerformanceMeasurement(api, getPath, getUser) {
  if (performanceInstalled) return;
  performanceInstalled = true;
  window.addEventListener('load', () => {
    window.setTimeout(() => {
      const navigation = performance.getEntriesByType?.('navigation')?.[0];
      const elapsed = navigation?.loadEventEnd || navigation?.domContentLoadedEventEnd || 0;
      trackExperience(api, 'performance_sample', {
        path:getPath(), authenticated:Boolean(getUser()), metricBucket:performanceBucket(elapsed),
      });
    }, 50);
  }, { once:true });
}

function publicHeader(active='') {
  const links = [
    ['solutions','Soluciones','/soluciones'], ['finder','Cuéntanos tu problema','/orientador'],
    ['how','Cómo funciona','/como-funciona'], ['business','Empresas','/para-empresas'],
    ['trust','Confianza','/confianza'],
  ];
  return `<header class="public-header m29-public-header m295-public-header" aria-label="Navegación pública">
    <button class="public-brand" type="button" data-action="go" data-route="/" aria-label="Ir al inicio"><img src="/assets/logo-legalaizit-web.png" alt="LegalAIZ.it"></button>
    <nav class="public-nav m29-public-nav" aria-label="Secciones principales">${links.map(([id,label,route])=>`<button class="${active===id?'active':''}" type="button" data-action="go" data-route="${route}">${label}</button>`).join('')}</nav>
    <div class="public-header-actions"><button class="btn ghost public-login" data-action="go" data-route="/login">Ingresar</button><button class="btn gold public-access" data-action="go" data-route="/agenda-demo" data-track-event="cta_click">Solicitar demo</button></div>
  </header>`;
}

function publicFooter() {
  return `<footer class="public-footer m29-public-footer m295-footer"><div class="m29-footer-brand"><img src="/assets/logo-legalaizit-web.png" alt="LegalAIZ.it"><p>Más que respuestas, soluciones.</p><small>Tu solución legal, impulsada por IA y expertos.</small></div><div><b>Empieza</b><button data-action="go" data-route="/orientador">Cuéntanos tu problema</button><button data-action="go" data-route="/soluciones">Explorar soluciones</button><button data-action="go" data-route="/agenda-demo">Solicitar demo</button></div><div><b>Conoce</b><button data-action="go" data-route="/como-funciona">Cómo funciona</button><button data-action="go" data-route="/confianza">Confianza</button><button data-action="go" data-route="/privacidad-medicion">Medición y privacidad</button></div><div><b>Uso responsable</b><span>LegalAIZ.it orienta, estructura y genera borradores. No garantiza resultados ni sustituye representación judicial.</span></div></footer>`;
}

function publicShell({ active='', title='LegalAIZ.it', content='' }) {
  setPublicTitle(title);
  return `<div class="public-site m29-public-site m295-public-site">${publicHeader(active)}<main id="main-content" tabindex="-1">${content}</main>${publicFooter()}</div>`;
}

const topicOptions = [
  ['trabajo','Trabajo y liquidaciones','Contrato laboral, liquidación o reclamación.'],
  ['contratos','Contratos y confidencialidad','Servicios, obligaciones o información sensible.'],
  ['vivienda','Arrendamiento de vivienda','Contrato, inventario, canon o terminación.'],
  ['salud','Atención en salud','Autorizaciones, continuidad, entrega o respuesta.'],
  ['consumo','Compras y servicios','Garantía, retracto, reversión o devolución.'],
  ['datos','Datos y centrales de riesgo','Consulta, corrección, actualización o retiro.'],
  ['transito','Tránsito y fotodetección','Sistema, expediente, notificación o debido proceso.'],
  ['deuda','Deudas y acuerdos de pago','Saldo, cuotas, pagaré, mora o cierre.'],
];

function recommendedCodes() {
  const topicMap = {
    trabajo:['CO-LA-001','CO-LA-002'], contratos:['CO-EM-003','CO-EM-004'], vivienda:['CO-AR-001'],
    salud:['CO-SA-001'], consumo:['CO-CD-003'], datos:['CO-CD-001'], transito:['CO-TR-002','CO-TR-001'], deuda:['CO-CD-004'],
  };
  let codes = topicMap[finderState.topic] || publicProducts.map(item=>item.code);
  if (finderState.audience === 'empresa') {
    const businessFirst = ['CO-LA-002','CO-EM-003','CO-EM-004','CO-CD-004','CO-AR-001'];
    codes = [...codes].sort((a,b)=>businessFirst.indexOf(a)-businessFirst.indexOf(b));
  }
  if (finderState.goal === 'crear') {
    const createFirst = ['CO-LA-002','CO-EM-003','CO-EM-004','CO-AR-001','CO-CD-004'];
    codes = [...codes].sort((a,b)=>Number(!createFirst.includes(a))-Number(!createFirst.includes(b)));
  }
  return codes.slice(0,3);
}

function finderChoice(group, value, title, detail) {
  const selected = finderState[group] === value;
  return `<button class="m295-choice ${selected?'selected':''}" type="button" data-m295-finder-group="${group}" data-m295-finder-value="${value}" aria-pressed="${selected}"><span>${title}</span><small>${detail}</small></button>`;
}

function legacyFinderContent() {
  const complete = finderState.audience && finderState.topic && finderState.goal;
  const recommendations = complete ? recommendedCodes().map(code=>publicProducts.find(item=>item.code===code)).filter(Boolean) : [];
  return `<section class="m341-fallback-wrap" aria-label="Orientador por preguntas">
    <div class="m341-fallback-head"><div><span class="public-kicker dark">Ruta alternativa</span><h2>Prefiero responder preguntas generales</h2><p>No guardaremos información del caso en esta ruta.</p></div><button class="btn ghost" type="button" data-m341-mode="story">← Volver a contar mi situación</button></div>
    <div class="m295-finder-progress"><span class="${finderState.audience?'complete':''}">1</span><span class="${finderState.topic?'complete':''}">2</span><span class="${finderState.goal?'complete':''}">3</span><span class="${complete?'complete':''}">4</span></div>
    <article class="m295-question"><span class="public-kicker dark">Paso 1</span><h2>¿Para quién buscas la solución?</h2><div class="m295-choice-grid two">${finderChoice('audience','persona','Para mí o mi familia','Una situación personal o doméstica.')}${finderChoice('audience','empresa','Para una empresa','Una necesidad contractual u operativa.')}${finderChoice('audience','aliado','Para un cliente o aliado','Exploración profesional o comercial.')}</div></article>
    <article class="m295-question"><span class="public-kicker dark">Paso 2</span><h2>¿Cuál es el tema principal?</h2><div class="m295-choice-grid">${topicOptions.map(([value,title,detail])=>finderChoice('topic',value,title,detail)).join('')}</div></article>
    <article class="m295-question"><span class="public-kicker dark">Paso 3</span><h2>¿Qué necesitas hacer?</h2><div class="m295-choice-grid three">${finderChoice('goal','crear','Crear o formalizar','Preparar un contrato, acuerdo o documento.')}${finderChoice('goal','reclamar','Reclamar o solicitar','Pedir respuesta, corrección o cumplimiento.')}${finderChoice('goal','revisar','Revisar antes de actuar','Verificar hechos, riesgos o soportes.')}</div></article>
    ${complete?`<section class="m295-recommendations" aria-live="polite"><div class="public-section-heading"><span class="public-kicker dark">Resultado orientativo</span><h2>Estas soluciones pueden acercarse a lo que necesitas.</h2><p>Revisa el alcance antes de iniciar. La selección no constituye concepto jurídico.</p></div><div class="public-solutions-grid">${recommendations.map(product=>`<article class="public-solution-card m29-solution-card m295-result-card"><img class="m29-product-visual" src="/assets/brand-visuals/product-${product.code.toLowerCase()}.svg" alt=""><span class="public-category">${product.category}</span><h3>${product.title}</h3><p>${product.description}</p><button class="btn primary" type="button" data-action="go" data-route="${publicProductRoute(product.code)}" data-track-event="solution_finder_completed">Revisar solución</button></article>`).join('')}</div><button class="btn ghost" type="button" data-m295-finder-reset>Reiniciar orientador</button></section>`:`<div class="m295-finder-pending"><img src="/assets/brand-visuals/conversion-path.svg" alt="Ruta pendiente de completar"><div><b>Completa las tres decisiones.</b><span>Las recomendaciones aparecerán aquí sin guardar información de tu caso.</span></div></div>`}
  </section>`;
}

function savedIntakeContent(esc) {
  const session = intakeState.session || {};
  return `<section class="m341-saved" aria-live="polite">
    <div><span class="m341-safe-badge">✓ Descripción guardada</span><h2>Tu situación quedó registrada de forma segura.</h2><p>En esta etapa todavía no presentamos inferencias ni conclusiones automáticas. Primero conservamos exactamente lo que nos contaste.</p></div>
    <div class="m341-saved-summary"><small>Lo que escribiste</small><p>${esc(session.problem_statement || '')}</p></div>
    ${intakeState.recoveryCode?`<div class="m341-recovery"><small>Código para retomar este diagnóstico</small><code>${esc(intakeState.recoveryCode)}</code><p>Guárdalo en un lugar seguro. No lo compartas: permite recuperar este relato mientras la sesión esté activa.</p></div>`:''}
    <div class="m341-actions"><button class="btn primary" type="button" data-m341-mode="finder">Continuar con preguntas generales</button><button class="btn secondary" type="button" data-m341-edit>Editar mi descripción</button><button class="btn ghost" type="button" data-action="go" data-route="/soluciones">Ya sé qué solución necesito</button></div>
    <div class="legal-notice"><b>Qué ocurre después.</b> La siguiente capa del recorrido convertirá el relato en hechos candidatos que podrás revisar y corregir antes de que una regla o recomendación utilice esa información.</div>
  </section>`;
}

function resumeIntakeContent() {
  if (intakeState.editing || intakeState.session) return '';
  return `<details class="m341-resume"><summary>Ya empecé antes y tengo un código</summary><form id="m341-recover-form" class="m341-resume-form"><label class="sr-only" for="m341-recovery-code">Código de continuidad</label><input class="input" id="m341-recovery-code" autocomplete="off" spellcheck="false" maxlength="27" placeholder="XXXXXX-XXXXXX-XXXXXX-XXXXXX" required><button class="btn secondary" type="submit">Retomar</button></form><div id="m341-recover-status" class="m341-status" role="status" aria-live="polite"></div></details>`;
}

function storyIntakeContent(esc) {
  const existing = intakeState.session?.problem_statement || '';
  if (intakeState.session && !intakeState.editing) return savedIntakeContent(esc);
  return `<form id="m341-intake-form" novalidate>
    <span class="public-kicker dark">Empieza con tus propias palabras</span>
    <h2>${intakeState.editing?'Corrige lo que nos contaste':'¿Qué está pasando?'}</h2>
    <p>No necesitas usar términos jurídicos ni saber qué documento pedir. Cuéntanos los hechos principales como se los explicarías a otra persona.</p>
    <label class="m341-problem-label" for="m341-problem"><span>Describe tu situación</span><small>Entre 20 y 8.000 caracteres</small></label>
    <textarea class="m341-problem" id="m341-problem" name="problem_statement" minlength="20" maxlength="8000" required placeholder="Ejemplo: Trabajé durante varios años para una empresa. Ayer me dijeron que no continuaba y todavía no me han pagado la liquidación…">${esc(existing)}</textarea>
    <div class="m341-problem-hint"><strong>Si puedes, incluye quién interviene, qué ocurrió, cuándo pasó y qué quieres lograr.</strong><span id="m341-count">${existing.length}/8.000</span></div>
    <div class="m341-actions"><button class="btn gold" type="submit">${intakeState.editing?'Guardar corrección':'Guardar y continuar'}</button>${intakeState.editing?'<button class="btn ghost" type="button" data-m341-cancel-edit>Cancelar</button>':'<button class="btn secondary" type="button" data-m341-mode="finder">Prefiero responder preguntas</button>'}</div>
    <div id="m341-intake-status" class="m341-status" role="status" aria-live="polite"></div>
  </form>${resumeIntakeContent()}`;
}

function finderContent(esc) {
  const main = intakeState.mode === 'finder' ? legacyFinderContent() : `<section class="public-section"><div class="m341-intake-shell"><article class="m341-intake-card">${storyIntakeContent(esc)}</article><aside class="m341-trust-panel" aria-label="Cómo usamos esta información"><span class="public-kicker">Tu información</span><h2>Primero hechos. Después orientación.</h2><div class="m341-trust-list"><div class="m341-trust-item"><span>1</span><div><b>Guardamos tu relato cifrado</b><small>El código de continuidad no se almacena en texto claro.</small></div></div><div class="m341-trust-item"><span>2</span><div><b>No inventamos datos faltantes</b><small>Una inferencia futura deberá distinguirse de lo que tú afirmaste.</small></div></div><div class="m341-trust-item"><span>3</span><div><b>Tú podrás corregir lo entendido</b><small>Fechas, partes y hechos críticos deben ser confirmables.</small></div></div><div class="m341-trust-item"><span>4</span><div><b>Los casos sensibles se escalan</b><small>Riesgo, urgencia o complejidad pueden exigir revisión profesional.</small></div></div></div><div class="m341-privacy-note">No incluyas contraseñas, claves, secretos de acceso ni información ajena que no sea necesaria para explicar la situación.</div></aside></div></section>`;
  return `<section class="m295-page-hero m341-intake-hero"><div><span class="public-kicker dark">Orientación jurídica guiada</span><h1>Cuéntanos tu problema. No necesitas saber cómo se llama la solución.</h1><p>LegalAIZ.it organiza el recorrido desde tu situación real. Puedes empezar sin crear una cuenta y elegir una solución concreta si ya sabes qué necesitas.</p><div class="m341-actions"><button class="btn ghost" type="button" data-action="go" data-route="/soluciones">Ver las 11 soluciones</button></div></div><img src="/assets/brand-visuals/conversion-compass.svg" alt="Ruta que conecta una situación jurídica con una solución"></section>${main}`;
}

export function createConversionExperience({ app, esc, api, go, toast, shell, pageHeader, state, getPath }) {
  function finderPage() {
    app.innerHTML = publicShell({ active:'finder', title:'Cuéntanos tu problema', content:finderContent(esc) });
    window.setTimeout(() => document.getElementById('m341-problem')?.focus({preventScroll:true}), 20);
  }

  function demoPage() {
    app.innerHTML = publicShell({ active:'business', title:'Solicitar demostración', content:`<section class="m295-page-hero m295-demo-hero"><div><span class="public-kicker dark">Demostración y alianzas</span><h1>Conoce LegalAIZ.it desde el recorrido que importa a tu organización.</h1><p>Registra únicamente datos de contacto y el tipo de conversación. No incluyas hechos jurídicos, nombres de clientes ni información confidencial.</p></div><img src="/assets/brand-visuals/demo-conversation.svg" alt="Conversación de demostración sobre una plataforma jurídica"></section><section class="public-section m295-demo-layout"><article class="m295-demo-benefits"><span class="public-kicker dark">Qué veremos</span><h2>Una demostración enfocada en valor y control.</h2><ul><li>Recorrido público y selección de soluciones.</li><li>Expedientes, documentos, revisión y trazabilidad.</li><li>Fábrica documental, seguridad y roles.</li><li>Escenarios para personas, empresas o aliados.</li></ul><div class="m295-demo-note"><b>Solicitud trazable</b><span>El entorno registra la solicitud para gestión administrativa. El envío de correos o agenda externa depende de la integración comercial del despliegue.</span></div></article><form id="commercial-lead-form" class="m295-lead-form"><div class="card-header"><div><span class="public-kicker dark">Solicitud de contacto</span><h2>¿Qué conversación necesitas?</h2><p>Campos marcados con * son obligatorios.</p></div></div><input class="m295-honeypot" id="lead-website" name="website" tabindex="-1" autocomplete="off" aria-hidden="true"><div class="field"><label for="lead-purpose">Motivo *</label><select class="select" id="lead-purpose" required><option value="demo">Demostración de la plataforma</option><option value="empresa">Solución para una empresa</option><option value="alianza">Alianza profesional o comercial</option></select></div><div class="m295-form-grid"><div class="field"><label for="lead-audience">Tipo de usuario *</label><select class="select" id="lead-audience" required><option value="empresa">Empresa</option><option value="persona">Persona</option><option value="aliado">Aliado o profesional</option></select></div><div class="field"><label for="lead-role">Tu rol *</label><select class="select" id="lead-role" required><option value="decision">Dirección o decisión</option><option value="legal">Jurídico</option><option value="operaciones">Operaciones</option><option value="tecnologia">Tecnología</option><option value="otro">Otro</option></select></div><div class="field"><label for="lead-name">Nombre completo *</label><input class="input" id="lead-name" maxlength="120" autocomplete="name" required></div><div class="field"><label for="lead-email">Correo *</label><input class="input" id="lead-email" type="email" maxlength="180" autocomplete="email" required></div><div class="field"><label for="lead-phone">Teléfono</label><input class="input" id="lead-phone" maxlength="24" inputmode="tel" autocomplete="tel"></div><div class="field"><label for="lead-organization">Organización</label><input class="input" id="lead-organization" maxlength="140" autocomplete="organization"></div></div><label class="m295-consent"><input id="lead-consent" type="checkbox" required><span>Autorizo el contacto y el tratamiento de estos datos para gestionar esta solicitud. No estoy enviando información de un caso jurídico.</span></label><button class="btn gold btn-block" type="submit">Registrar solicitud</button><div id="lead-form-status" class="m295-form-status" role="status" aria-live="polite"></div></form></section>` });
  }

  function measurementPage() {
    const consent = measurementConsent();
    app.innerHTML = publicShell({ title:'Medición y privacidad', content:`<section class="m295-page-hero"><div><span class="public-kicker dark">Medición responsable</span><h1>Mejorar la experiencia sin convertir tu caso en un dato analítico.</h1><p>La medición es voluntaria. Cuando la autorizas, solo se registran eventos agregados como vistas de secciones, uso del orientador y categorías generales de rendimiento.</p></div><img src="/assets/brand-visuals/analytics-privacy.svg" alt="Gráfico protegido por un escudo de privacidad"></section><section class="public-section m295-measurement"><article><h2>Lo que sí se mide</h2><ul><li>Tipo general de pantalla visitada.</li><li>Acciones generales como iniciar el orientador.</li><li>Tipo de dispositivo: móvil, tableta o escritorio.</li><li>Categorías de velocidad, no tiempos asociados a una persona.</li></ul></article><article><h2>Lo que no se registra</h2><ul><li>Nombres, documentos o correos en analítica.</li><li>Texto de búsquedas o respuestas del formulario jurídico.</li><li>Identificadores de expedientes o documentos.</li><li>Hechos, pretensiones, valores o archivos del caso.</li></ul></article><div class="m295-measurement-choice"><div><b>Estado actual</b><span>${consent==='granted'?'Medición agregada autorizada':consent==='denied'?'Medición desactivada':'Aún no has elegido'}</span></div><div><button class="btn primary" type="button" data-m295-consent="granted">Autorizar medición agregada</button><button class="btn secondary" type="button" data-m295-consent="denied">Mantener desactivada</button></div></div></section>` });
  }

  async function adminExperiencePage() {
    if (state.user?.role !== 'admin') {
      app.innerHTML = shell(`<div class="page"><div class="result-banner red"><div class="result-icon">!</div><div><h2>Acceso restringido</h2><p>La analítica agregada y las solicitudes comerciales están reservadas para administración.</p></div></div></div>`);
      return;
    }
    const data = await api('/api/experience-metrics?days=30');
    const eventLabels = { route_view:'Vistas', cta_click:'Clics en CTA', solution_finder_started:'Orientadores iniciados', solution_finder_completed:'Orientadores completados', intake_started:'Relatos iniciados', intake_saved:'Relatos guardados', lead_form_started:'Formularios iniciados', lead_submitted:'Solicitudes recibidas', performance_sample:'Muestras de rendimiento' };
    const eventRows = Object.entries(data.by_event || {}).map(([key,value])=>`<div class="m295-metric-row"><span>${esc(eventLabels[key] || key)}</span><b>${esc(value)}</b></div>`).join('') || '<p class="muted">Aún no hay eventos autorizados.</p>';
    const surfaceRows = Object.entries(data.by_surface || {}).slice(0,8).map(([key,value])=>`<div class="m295-metric-row"><span>${esc(key)}</span><b>${esc(value)}</b></div>`).join('') || '<p class="muted">Sin recorridos medidos.</p>';
    const leadRows = (data.leads || []).map(item=>`<article class="m295-lead-row"><div><span class="badge blue">${esc(item.purpose)}</span><h3>${esc(item.name)}</h3><p>${esc(item.organization || item.audience)} · ${esc(item.role)}</p></div><div><a href="mailto:${encodeURIComponent(item.email)}">${esc(item.email)}</a>${item.phone?`<span>${esc(item.phone)}</span>`:''}<small>${esc(item.created_at)}</small></div></article>`).join('') || '<div class="empty-state"><h2>No hay solicitudes comerciales</h2><p>Las solicitudes válidas aparecerán aquí.</p></div>';
    app.innerHTML = shell(`<div class="page m295-admin-page">${pageHeader({eyebrow:'Experiencia y conversión',title:'Señales agregadas para mejorar el producto',description:'Métricas voluntarias sin hechos jurídicos, identificadores de expedientes ni texto de búsquedas.'})}<section class="kpi-grid"><div class="kpi"><span class="kpi-label">Eventos agregados</span><div class="kpi-value"><strong>${esc(data.events_total || 0)}</strong><span class="kpi-icon">↗</span></div></div><div class="kpi"><span class="kpi-label">Solicitudes comerciales</span><div class="kpi-value"><strong>${esc(data.leads_total || 0)}</strong><span class="kpi-icon">✦</span></div></div><div class="kpi"><span class="kpi-label">Ventana</span><div class="kpi-value"><strong>${esc(data.window_days || 30)} días</strong><span class="kpi-icon">◷</span></div></div></section><div class="m295-privacy-banner"><img src="/assets/brand-visuals/internal/admin-insights.svg" alt="Panel de métricas agregadas"><div><b>Modelo de privacidad</b><span>No se almacenan texto de búsquedas, casos, documentos, respuestas jurídicas ni identificadores analíticos.</span></div></div><section class="section-grid"><article class="card span-6"><div class="card-header"><div><h2>Eventos</h2><p>Acciones generales autorizadas.</p></div></div>${eventRows}</article><article class="card span-6"><div class="card-header"><div><h2>Superficies</h2><p>Secciones generales utilizadas.</p></div></div>${surfaceRows}</article></section><section class="card"><div class="card-header"><div><h2>Solicitudes comerciales</h2><p>Datos de contacto autorizados; nunca contienen hechos jurídicos.</p></div></div><div class="m295-lead-list">${leadRows}</div></section></div>`);
  }

  async function submitIntake(event) {
    event.preventDefault();
    const textarea = document.getElementById('m341-problem');
    const status = document.getElementById('m341-intake-status');
    const button = event.submitter;
    const problem = String(textarea?.value || '').trim();
    if (problem.length < 20) {
      status.className = 'm341-status danger';
      status.textContent = 'Cuéntanos un poco más para poder organizar tu situación.';
      textarea?.focus();
      return;
    }
    button.disabled = true;
    button.textContent = 'Guardando…';
    try {
      let result;
      if (intakeState.editing && intakeState.recoveryCode) {
        result = await api('/api/m34/intake/problem', { method:'POST', body:JSON.stringify({ recovery_code:intakeState.recoveryCode, problem_statement:problem }) });
        intakeState.session = result;
        intakeState.editing = false;
      } else {
        trackExperience(api, 'intake_started', {path:'/orientador'});
        result = await api('/api/m34/intake/start', { method:'POST', body:JSON.stringify({ problem_statement:problem }) });
        intakeState.session = result;
        intakeState.recoveryCode = result.recovery_code || '';
      }
      trackExperience(api, 'intake_saved', {path:'/orientador'});
      finderPage();
    } catch (error) {
      status.className = 'm341-status danger';
      status.textContent = error.message;
      button.disabled = false;
      button.textContent = intakeState.editing ? 'Guardar corrección' : 'Guardar y continuar';
    }
  }

  async function recoverIntake(event) {
    event.preventDefault();
    const code = String(document.getElementById('m341-recovery-code')?.value || '').trim();
    const status = document.getElementById('m341-recover-status');
    const button = event.submitter;
    button.disabled = true;
    button.textContent = 'Recuperando…';
    try {
      const result = await api('/api/m34/intake/recover', { method:'POST', body:JSON.stringify({ recovery_code:code }) });
      intakeState.session = result;
      intakeState.recoveryCode = code;
      intakeState.editing = false;
      intakeState.mode = 'story';
      finderPage();
      toast('Diagnóstico recuperado.');
    } catch (error) {
      status.className = 'm341-status danger';
      status.textContent = error.message;
      button.disabled = false;
      button.textContent = 'Retomar';
    }
  }

  function install() {
    if (installed) return;
    installed = true;
    installPerformanceMeasurement(api, getPath, () => state.user);
    document.addEventListener('input', event => {
      if (event.target?.id !== 'm341-problem') return;
      const count = document.getElementById('m341-count');
      if (count) count.textContent = `${event.target.value.length}/8.000`;
    });
    document.addEventListener('click', event => {
      const mode = event.target.closest('[data-m341-mode]');
      if (mode) {
        intakeState.mode = mode.dataset.m341Mode === 'finder' ? 'finder' : 'story';
        finderPage();
        return;
      }
      if (event.target.closest('[data-m341-edit]')) {
        intakeState.mode = 'story'; intakeState.editing = true; finderPage(); return;
      }
      if (event.target.closest('[data-m341-cancel-edit]')) {
        intakeState.editing = false; finderPage(); return;
      }
      const choice = event.target.closest('[data-m295-finder-group]');
      if (choice) {
        finderState[choice.dataset.m295FinderGroup] = choice.dataset.m295FinderValue;
        trackExperience(api, 'solution_finder_started', {path:'/orientador'});
        finderPage();
        return;
      }
      if (event.target.closest('[data-m295-finder-reset]')) {
        finderState.audience = ''; finderState.topic = ''; finderState.goal = ''; finderPage(); return;
      }
      const consent = event.target.closest('[data-m295-consent]');
      if (consent) {
        setMeasurementConsent(consent.dataset.m295Consent);
        measurementPage();
        toast(consent.dataset.m295Consent === 'granted' ? 'Medición agregada autorizada.' : 'Medición desactivada.');
        return;
      }
      const tracked = event.target.closest('[data-track-event]');
      if (tracked) trackExperience(api, tracked.dataset.trackEvent, {path:getPath(),authenticated:Boolean(state.user)});
    });
    document.addEventListener('focusin', event => {
      if (event.target?.closest?.('#commercial-lead-form')) trackExperience(api, 'lead_form_started', {path:'/agenda-demo'});
    }, { once:true });
    document.addEventListener('submit', async event => {
      if (event.target?.id === 'm341-intake-form') return submitIntake(event);
      if (event.target?.id === 'm341-recover-form') return recoverIntake(event);
      if (event.target?.id !== 'commercial-lead-form') return;
      event.preventDefault();
      const button = event.submitter;
      const status = document.getElementById('lead-form-status');
      button.disabled = true; button.textContent = 'Registrando…';
      try {
        const result = await api('/api/public/commercial-intake', { method:'POST', body:JSON.stringify({
          website:document.getElementById('lead-website')?.value || '',
          purpose:document.getElementById('lead-purpose').value,
          audience:document.getElementById('lead-audience').value,
          role:document.getElementById('lead-role').value,
          name:document.getElementById('lead-name').value,
          email:document.getElementById('lead-email').value,
          phone:document.getElementById('lead-phone').value,
          organization:document.getElementById('lead-organization').value,
          consent:document.getElementById('lead-consent').checked,
        }) });
        status.className = 'm295-form-status success';
        status.innerHTML = `<b>${esc(result.message)}</b><span>Referencia: ${esc(result.request_id)}</span>`;
        event.target.reset();
        trackExperience(api, 'lead_submitted', {path:'/agenda-demo'});
      } catch (error) {
        status.className = 'm295-form-status danger';
        status.textContent = error.message;
      } finally { button.disabled = false; button.textContent = 'Registrar solicitud'; }
    });
  }

  function afterRender(path=getPath()) {
    optimizeMedia(document);
    if (lastTrackedPath !== path) {
      lastTrackedPath = path;
      trackExperience(api, 'route_view', {path, authenticated:Boolean(state.user)});
    }
  }

  return { install, afterRender, finderPage, demoPage, measurementPage, adminExperiencePage };
}
