# QA final — LegalAIZ.it M31.8 — v5.0.7

Estado: **APROBADO PARA DEMOSTRACIÓN CONTROLADA Y PILOTO LOCAL**. Producción pública no autorizada.

## Evidencia consolidada

- 66 módulos: **496 pruebas y 938 subpruebas aprobadas**, sin fallos ni timeouts.
- Compatibilidad M31.1–M31.8: **72/72** pruebas focalizadas.
- Smoke HTTP portable: **5/5**.
- Flujo autenticado por expediente: **10/10**.
- Auditoría de fuente: **11/11**.
- Validación estática: 264 Python, 21 JavaScript, 738 JSON y 113 SVG, sin errores.
- Cohorte: 11 expedientes, 76 documentos activos, 22 aprobaciones distintas, 11 certificados, 11 paquetes finales y un ZIP global.
- Integridad: 88 elementos verificados; 0 variables o marcadores sin resolver.
- La nueva revisión invalida paquete y aprobaciones activas; la liberación exige nuevamente especialista asignado y QA administrador sobre el mismo hash.
- Se conserva el QA visual documental de M31.7: 11 documentos y 36 páginas. No se generaron nuevas capturas del navegador M31.8 porque el ejecutable Chromium no estaba disponible en este entorno; la interfaz nueva sí fue cubierta por sintaxis, rutas, API y smoke autenticado.

## Condiciones de uso

Los expedientes, personas y aprobaciones son sintéticos. Un caso real exige validación de hechos, identidad, anexos, vigencia normativa, riesgos y aprobación separada sobre la revisión definitiva. PostgreSQL externo y producción pública permanecen bloqueados.
