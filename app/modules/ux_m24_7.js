import { api, app, esc, go, money, state, toast } from '../core.js';

export function shouldShow(question, answers) {
  if (!question.show_if) return true;
  const condition = question.show_if;
  if (Object.prototype.hasOwnProperty.call(condition, 'equals')) return String(answers[condition.field] || '') === String(condition.equals);
  if (Array.isArray(condition.in)) return condition.in.map(String).includes(String(answers[condition.field] || ''));
  return true;
}
export function answeredValue(value) { return value !== '' && value != null && (!Array.isArray(value) || value.length > 0); }
export function questionPageWeight(question) { return ['textarea','multiselect'].includes(question.type) || (question.options || []).length > 4 ? 2 : 1; }
export function paginateWizardQuestions(questions, maxWeight = 4) {
  const pages = []; let page = []; let weight = 0;
  for (const question of questions) {
    const next = questionPageWeight(question);
    if (page.length && weight + next > maxWeight) { pages.push(page); page = []; weight = 0; }
    page.push(question); weight += next;
  }
  if (page.length || !pages.length) pages.push(page);
  return pages;
}
export function createGuidedExperience({ shell, pageHeader, intakeEndpoint, copy }) {
  const clientJourneyStrip = active => `<nav class="client-journey" aria-label="Recorrido de la solución"><ol>${['Describe tu caso','Confirma la ruta','Completa la información','Recibe y sigue tu solución'].map((label,index) => `<li class="${index + 1 === active ? 'active' : index + 1 < active ? 'complete' : ''}" ${index + 1 === active ? 'aria-current="step"' : ''}><b>${index + 1 < active ? '✓' : index + 1}</b><span>${esc(label)}</span></li>`).join('')}</ol></nav>`;
  function recommendationCard(row, index) {
    const paid = (row.service_levels || []).filter(level => level.checkout_enabled);
    const starting = paid.length ? Math.min(...paid.map(level => Number(level.price || 0))) : 0;
    const confidence = row.confidence === 'high' ? ['Coincidencia alta','success'] : row.confidence === 'medium' ? ['Coincidencia media','warning'] : ['Por confirmar','warning'];
    return `<article class="card intake-recommendation"><div class="card-header"><div><span class="eyebrow">${esc(row.product_code)} · Opción ${index + 1}</span><h3>${esc(row.public_name)}</h3></div><span class="badge ${confidence[1]}">${confidence[0]}</span></div><p>${esc(row.recommendation_reason)}</p>${(row.matched_terms || []).length ? `<div class="product-meta">${row.matched_terms.map(term => `<span class="badge blue">${esc(term)}</span>`).join('')}</div>` : ''}<div class="intake-scope-grid"><div><small>Incluye principalmente</small><ul class="check-list">${(row.scope || []).slice(0,4).map(item => `<li>${esc(item)}</li>`).join('')}</ul></div><div><small>No cubre automáticamente</small><ul class="check-list muted-checks">${(row.exclusions || []).slice(0,3).map(item => `<li>${esc(item)}</li>`).join('')}</ul></div></div><div class="solution-footer"><span>${starting ? `Desde ${money(starting)} · sandbox` : 'Orientación inicial disponible'}</span><div class="button-group"><button class="btn secondary sm" data-action="go" data-route="/solucion/${encodeURIComponent(row.product_code)}">Ver alcance</button><button class="btn navy sm" data-action="go" data-route="/nuevo/${encodeURIComponent(row.product_code)}">Iniciar</button></div></div></article>`;
  }
  function resultsPanel(result) {
    if (!result) return '';
    const recommendations = result.recommendations || [], signals = result.risk_signals || [];
    const title = result.routing_status === 'escalate' ? 'Se requiere revisión profesional prioritaria' : result.routing_status === 'needs_clarification' ? 'Necesitamos confirmar algunos datos' : 'Encontramos una ruta probable';
    const cls = result.routing_status === 'escalate' ? 'red' : result.routing_status === 'needs_clarification' ? 'yellow' : 'green';
    return `<section class="intake-results mt-22" aria-labelledby="intake-results-heading"><div class="result-banner ${cls}"><div class="result-icon">${cls === 'red' ? '!' : cls === 'yellow' ? '?' : '✓'}</div><div><h2 id="intake-results-heading" tabindex="-1">${esc(title)}</h2><p>${esc(result.notice || '')}</p></div></div>${signals.length ? `<div class="legal-notice danger mt-16"><b>Alertas detectadas.</b><ul>${signals.map(signal => `<li>${esc(signal.message)}</li>`).join('')}</ul></div>` : ''}${(result.privacy_warnings || []).length ? `<div class="legal-notice mt-16"><b>Privacidad.</b><ul>${result.privacy_warnings.map(item => `<li>${esc(item)}</li>`).join('')}</ul></div>` : ''}${recommendations.length ? `<div class="candidate-library-grid mt-20">${recommendations.map(recommendationCard).join('')}</div>` : `<div class="empty-state mt-20"><div class="empty-icon">⌕</div><h2>No hay una coincidencia suficientemente clara</h2><p>Agrega quién está involucrado, qué ocurrió, cuándo pasó y qué resultado buscas.</p></div>`}${(result.clarifying_questions || []).length ? `<div class="card mt-20"><div class="card-header"><div><h2>Datos que ayudarían a confirmar la ruta</h2><p>No incluyas cédulas, historias clínicas ni números completos de tarjetas.</p></div></div><ul class="check-list">${result.clarifying_questions.map(item => `<li>${esc(item)}</li>`).join('')}</ul></div>` : ''}</section>`;
  }
  function guidedStartPage() {
    const groups = [['Contratos y relaciones','Contrato de trabajo, servicios, arrendamiento, confidencialidad o propiedad intelectual.','contrato','◇'],['Trabajo y liquidaciones','Liquidación de acreencias, reclamación o formalización laboral.','laboral','▤'],['Salud','Peticiones a EPS o IPS y organización de soportes.','salud','+'],['Consumo, datos y cobros','Garantía, retracto, reportes, hábeas data, acuerdos o pagarés.','consumo','▦'],['Tránsito','Fotomultas, notificaciones y chequeo SAST.','tránsito','⚖']];
    const active = state.clientIntakeResult ? 2 : 1;
    app.innerHTML = shell(`<div class="page">${clientJourneyStrip(active)}${pageHeader({ eyebrow:'Nueva solución', title:'Cuéntanos qué ocurrió', description:`${copy.intro}. Describe la situación en lenguaje sencillo; el diagnóstico jurídico se confirma en el formulario y con los soportes.` })}<section id="client-intake-card" class="card intake-card" aria-busy="false"><div class="card-header"><div><h2>Describe el problema</h2><p>Incluye qué ocurrió, quién intervino, cuándo sucedió y qué resultado buscas. No compartas datos sensibles completos.</p></div><span class="badge blue">No se conserva este texto</span></div><div class="field"><label for="intake-narrative">Situación</label><textarea id="intake-narrative" class="textarea intake-textarea" maxlength="4000" aria-describedby="intake-privacy" placeholder="Ejemplo: Me reportaron en una central de riesgo por una deuda que pagué hace tres meses y quiero solicitar la corrección del reporte.">${esc(state.clientIntakeNarrative || '')}</textarea><small id="intake-privacy" class="field-hint">Evita identificaciones completas, datos clínicos detallados o números de tarjetas.</small></div><div class="intake-actions"><button id="analyze-intake-button" class="btn gold" data-action="analyze-intake">Analizar y sugerir ruta</button><button class="btn secondary" data-action="go" data-route="/soluciones">${esc(copy.compare)}</button></div><p id="intake-live-status" class="sr-status" role="status" aria-live="polite"></p><div class="demo-note"><b>Orientación inicial explicable.</b> La clasificación usa reglas trazables y no reemplaza un concepto jurídico, la verificación de términos ni la revisión profesional.</div></section>${resultsPanel(state.clientIntakeResult)}<section class="mt-28">${pageHeader({ eyebrow:'También puedes explorar', title:'Selecciona una categoría', description:'Usa esta opción cuando prefieras revisar el catálogo por tema.' })}<div class="solution-grid">${groups.map(g => `<button class="solution-card text-left" data-action="choose-need" data-value="${esc(g[2])}"><div class="solution-top"><span class="solution-icon">${g[3]}</span><span class="badge blue">Explorar</span></div><h2>${esc(g[0])}</h2><p>${esc(g[1])}</p><div class="solution-footer"><span>Ver soluciones relacionadas</span><span>›</span></div></button>`).join('')}</div></section></div>`);
  }
  async function analyzeIntake() {
    const input = document.getElementById('intake-narrative'), card = document.getElementById('client-intake-card'), button = document.getElementById('analyze-intake-button'), status = document.getElementById('intake-live-status');
    const narrative = input?.value.trim() || ''; state.clientIntakeNarrative = narrative;
    if (narrative.length < 12) { toast('Describe la situación con un poco más de detalle.','danger'); input?.focus(); return; }
    card?.setAttribute('aria-busy','true'); if (button) { button.disabled = true; button.textContent = 'Analizando…'; } if (status) status.textContent = 'Analizando la situación y comparando rutas jurídicas.';
    try { state.clientIntakeResult = await api(intakeEndpoint,{method:'POST',body:JSON.stringify({narrative})}); guidedStartPage(); setTimeout(() => document.getElementById('intake-results-heading')?.focus({preventScroll:false}),30); }
    catch (error) { card?.setAttribute('aria-busy','false'); if (button) { button.disabled=false; button.textContent='Analizar y sugerir ruta'; } if (status) status.textContent='No fue posible completar el análisis.'; toast(error.message,'danger'); }
  }
  function chooseNeed(term) { state.solutionQuery=term; state.solutionFilter='Todos'; go('/soluciones'); }
  return { clientJourneyStrip, guidedStartPage, analyzeIntake, chooseNeed };
}
