# M33.0 — Registro de migración del portafolio jurídico

## 1. Propósito

Este documento registra la migración técnica de la Fábrica Documental de LegalAIZ.it al estándar M33.0. La migración no constituye aprobación jurídica de los documentos generados ni reemplaza las compuertas de publicación ya existentes.

La regla de gobierno permanece inalterada: una salida solo puede liberarse cuando la revisión jurídica y el QA recaen sobre la misma revisión y el mismo hash, además de cumplirse las condiciones de riesgo y publicación del producto.

## 2. Estándar documental aplicado

M33.0 establece, entre otros controles:

- Times New Roman 12 para el cuerpo documental.
- Texto justificado.
- Interlineado 1,15.
- Espacio posterior de 6 pt.
- Márgenes de 2,5 cm.
- Títulos principales centrados y diferenciados.
- Ordinales jurídicos con formato `PRIMERA:` y título en negrita.
- Tablas con encabezados repetibles y filas protegidas frente a divisiones innecesarias.
- Firmas mediante tablas invisibles, sin líneas manuales o guiones bajos.
- Encabezado, pie y paginación estructurados.
- Anexos y módulos condicionales separados del cuerpo cuando su naturaleza lo exige.
- Preflight semántico y auditoría OOXML antes de considerar la salida válida.
- Bloqueo de marcadores sin resolver, `NULL`, `undefined`, `N/A`, variables pendientes y separadores decorativos.
- Control final de uso, fuentes y revisión profesional.

## 3. Oleada 1 — contratos

La primera oleada usa fábricas versionadas nuevas y conserva las clases históricas para regresión y comparación.

| Producto | Versión histórica | Versión M33.0 | Estrategia |
| --- | --- | --- | --- |
| CO-EM-003 · Servicios profesionales | 2.44 | 2.45 | Nueva fábrica sobre la versión histórica; contrato principal recompuesto |
| CO-LA-002 · Contrato laboral | 2.39 | 2.40 | Nueva fábrica; contrato principal recompuesto |
| CO-AR-001 · Arrendamiento | 2.50 | 2.51 | Nueva fábrica; contrato principal recompuesto |
| CO-EM-004 · Confidencialidad | 2.47 | 2.48 | Nueva fábrica; NDA principal recompuesto |

Las aprobaciones de las versiones históricas no se transfieren a las nuevas instancias. Los directorios de gobierno y generación son versionados.

## 4. Oleada 2 — expedientes calculados y reclamaciones

La segunda oleada conserva los motores determinísticos, reglas de selección y bloqueos históricos. M33.0 actúa únicamente como capa de composición y saneamiento documental.

| Producto | Composición M33.0 |
| --- | --- |
| CO-LA-001 · Liquidación laboral | Diagnóstico, informe de cálculo, reclamación, solicitud de soportes, índice probatorio, matriz de diferencias y calendario de seguimiento |
| CO-CD-001 · Hábeas data financiero | Consulta, reclamación, reiteración, protocolo condicional de suplantación, escalamiento, matriz probatoria y calendario |
| CO-CD-003 · Protección al consumidor | Diagnóstico clasificador y un único mecanismo sustantivo compatible: garantía, retracto, reversión, débito periódico o no entrega; más evidencia y calendario |
| CO-CD-004 · Cartera y pagaré | Diagnóstico de deuda, estado de cuenta, requerimiento, acuerdo, cronograma, pagaré, instrucciones condicionales, recibos y cierre según etapa |

Los expedientes rojos de esta oleada conservan la ruta histórica y no son recompuestos para salida ordinaria automática.

## 5. Oleada 3 — salud y tránsito

La tercera oleada permite componer borradores críticos con estándar M33.0, pero mantiene revisión profesional obligatoria y no altera el estado de liberación.

| Producto | Composición M33.0 |
| --- | --- |
| CO-SA-001 · Salud | Diagnóstico, petición, reiteración, Supersalud, historia clínica, evidencia/radicación y calendario |
| CO-TR-001 · Verificación SAST | Informe, trazabilidad, inscripción, expediente oficial, inspección condicionada, seguimiento y paquete consolidado |
| CO-TR-002 · Fotodetección no notificada | Diagnóstico, expediente, reclamación de notificación, audiencia, revocación condicionada, corrección registral, matrices y guía de gestión |

Los documentos distinguen hechos, actos, etapas y consecuencias. Se prohíben conclusiones automáticas como `fotomulta ilegal`, `comparendo anulado`, `prescribió`, `no tiene que pagar` o equivalentes cuando el expediente no las soporte.

## 6. Arquitectura de compatibilidad

La aplicación conserva los símbolos y rutas históricas consumidos por handlers e integraciones. La activación M33.0 se realiza en runtime:

- fábricas contractuales nuevas para la primera oleada;
- wrapper de `document_specs` para la segunda y tercera oleada;
- motores de cálculo, selección de mecanismo, riesgo y reglas jurídicas preservados;
- productos fuera de M33.0 o rutas expresamente bloqueadas conservan el comportamiento histórico;
- las clases históricas siguen disponibles para pruebas y comparación.

## 7. Validación automatizada

La rama M33.0 incorpora pruebas específicas de:

- estándar documental y OOXML;
- contrato patrón de servicios;
- primera oleada contractual completa;
- activación runtime y conservación histórica;
- segunda oleada por producto;
- tercera oleada de salud y tránsito;
- activación transversal del portafolio;
- compuertas rojas y rutas críticas;
- selección exclusiva del mecanismo de consumidor;
- consistencia económica entre acuerdo, cronograma, pagaré e instrucciones.

Además, la regresión completa del repositorio debe permanecer verde antes de promover la rama.

## 8. QA visual

La CI genera documentos representativos de las tres oleadas, los convierte con LibreOffice y rasteriza todas las páginas del PDF resultante. El objetivo es detectar corrupción de OOXML, páginas perdidas, saltos anómalos y problemas de compatibilidad fuera de `python-docx`.

La evidencia visual se conserva como artefacto de GitHub Actions. Esta evidencia técnica no sustituye la revisión humana página a página que forma parte del QA de liberación.

## 9. Gobierno y publicación

La migración M33.0 no modifica los principios de gobierno:

1. Generar borrador.
2. Ejecutar QA estructural y técnico.
3. Validar contenido jurídico contra hechos, reglas y fuentes.
4. Revisar visualmente la salida renderizada.
5. Registrar aprobación jurídica.
6. Registrar aprobación de QA sobre la misma revisión/hash.
7. Liberar solo cuando todas las compuertas aplicables estén satisfechas.

No debe confundirse `document_standard = M33.0` con `legal_approval = approved`, `qa_approval = approved` o `released = true`.

## 10. Estado de esta rama

La rama `m33-0-estandar-documental-juridico` constituye una candidata técnica de migración del portafolio. El PR debe permanecer en borrador hasta completar la validación jurídica y QA humano de las salidas que se pretendan promover.

`main` no debe recibir la migración por el solo hecho de superar CI. La promoción requiere decisión expresa y evidencia del mismo commit que se pretenda fusionar.
