'use strict';

export function createDemoRealityExperience({ app, api, esc, shell, pageHeader, toast }) {
  const fileUrl = relative => `/api/m31/demo-reality/files/${encodeURIComponent(relative)}`;
  const metric = (label, value, note='') => `<div class="kpi"><span class="kpi-label">${esc(label)}</span><div class="kpi-value"><strong>${esc(value)}</strong><span class="kpi-icon">✓</span></div>${note ? `<small>${esc(note)}</small>` : ''}</div>`;
  const fileButton = file => {
    const format = (file.format || file.name?.split('.').pop() || '').toUpperCase();
    const label = file.type === 'validated_reference' ? `Referencia ${format}` : `${format} · ${file.title || file.kind || 'Documento'}`;
    return `<a class="btn secondary sm" href="${fileUrl(file.download_path)}" ${format === 'PDF' ? 'target="_blank" rel="noopener"' : 'download'}>${esc(label)}</a>`;
  };
  const productCard = product => {
    const generated = (product.files || []).filter(file => file.type === 'generated_docx');
    const refs = (product.files || []).filter(file => file.type === 'validated_reference');
    return `<article class="card demo-reality-product">
      <div class="card-header"><div><span class="eyebrow">${esc(product.product_code)}</span><h2>${esc(product.title)}</h2></div><span class="badge green">${esc(product.generated_docx)} documentos</span></div>
      <div class="demo-reality-actions"><a class="btn gold sm" href="${fileUrl(product.package.download_path)}" download>Descargar paquete completo</a>${refs.map(fileButton).join('')}</div>
      <details class="library-detail"><summary>Ver ${esc(generated.length)} documentos generados</summary><div class="demo-reality-file-list">${generated.map(file => `<div><span>${esc(file.title || file.name)}</span><a href="${fileUrl(file.download_path)}" download>Descargar DOCX</a></div>`).join('')}</div></details>
    </article>`;
  };
  async function generate() {
    const button = document.getElementById('demo-reality-generate');
    if (button) { button.disabled = true; button.textContent = 'Generando portafolio…'; }
    try {
      await api('/api/m31/demo-reality/generate', { method:'POST', body:'{}' });
      toast('Portafolio documental completo generado y verificado.');
      await page();
    } catch (error) {
      toast(error.message, 'danger');
      if (button) { button.disabled = false; button.textContent = 'Generar los documentos finales'; }
    }
  }
  async function verify() {
    try {
      const result = await api('/api/m31/demo-reality/verify');
      toast(result.ok ? `Integridad verificada: ${result.checked} archivos.` : 'La verificación encontró inconsistencias.', result.ok ? 'success' : 'danger');
    } catch (error) { toast(error.message, 'danger'); }
  }
  async function page() {
    const data = await api('/api/m31/demo-reality');
    const ready = data.status === 'ready';
    const metrics = data.metrics || {};
    const globalPackage = data.global_package || null;
    app.innerHTML = shell(`<div class="page demo-reality-page">${pageHeader({eyebrow:'M31.7 · Demo documental realista',title:'Generación completa de documentos finales',description:'Construye, verifica y descarga el portafolio documental de los 11 productos con datos sintéticos coherentes, DOCX editables, referencias PDF y hashes de integridad.'})}
      <section class="demo-reality-hero"><div><span class="eyebrow">Entorno de demostración controlada</span><h2>${ready ? 'El portafolio está listo para presentar.' : 'Genera toda la biblioteca documental en un solo paso.'}</h2><p>${esc(data.notice || 'La generación masiva utiliza únicamente datos sintéticos.')}</p><div class="button-group"><button class="btn primary" id="demo-reality-generate" type="button">${ready ? 'Regenerar portafolio' : 'Generar los documentos finales'}</button>${globalPackage ? `<a class="btn gold" href="${fileUrl(globalPackage.download_path)}" download>Descargar ZIP completo</a>` : ''}${ready ? '<button class="btn secondary" id="demo-reality-verify" type="button">Verificar integridad</button>' : ''}</div></div><div class="demo-reality-seal"><b>${ready ? 'LISTO' : 'PENDIENTE'}</b><span>${ready ? `${metrics.generated_docx || 0} DOCX generados` : '11 productos · 76 plantillas'}</span></div></section>
      <section class="kpi-grid">${metric('Productos', metrics.products || 11, 'Cobertura integral')}${metric('DOCX generados', metrics.generated_docx || 0, 'Editables y descargables')}${metric('Referencias PDF', metrics.validated_reference_pdf || 0, 'QA visual previo')}${metric('Variables sin resolver', metrics.unresolved_files || 0, 'Debe permanecer en cero')}</section>
      ${ready ? `<div class="result-banner ${metrics.unresolved_files ? 'red' : 'green'}"><div class="result-icon">${metrics.unresolved_files ? '!' : '✓'}</div><div><h2>${metrics.unresolved_files ? 'Existen documentos bloqueados' : 'Generación completa verificada'}</h2><p>${metrics.unresolved_files ? 'No debe utilizarse el portafolio hasta resolver las variables detectadas.' : 'Todos los documentos se generaron sin variables rotas, cuentan con hash SHA-256 y están organizados por producto.'}</p></div></div><div class="demo-reality-grid">${(data.products || []).map(productCard).join('')}</div>` : `<section class="card empty-state"><div class="empty-icon">§</div><h2>Portafolio aún no generado</h2><p>El proceso crea una salida editable por cada plantilla, copia las referencias finales validadas y construye paquetes ZIP por producto y global.</p></section>`}
      <section class="card mt-22"><div class="card-header"><div><h2>Alcance jurídico de la demostración</h2></div></div><div class="legal-notice"><b>Documentos realistas, no documentos de clientes.</b> Los datos son sintéticos y el portafolio sirve para mostrar profundidad, formato y flujo. Una entrega real exige validar identidad, hechos, soportes, vigencia normativa, riesgos y aprobación jurídica y QA sobre la versión exacta.</div></section>
    </div>`);
    document.getElementById('demo-reality-generate')?.addEventListener('click', generate);
    document.getElementById('demo-reality-verify')?.addEventListener('click', verify);
  }
  return { page };
}
