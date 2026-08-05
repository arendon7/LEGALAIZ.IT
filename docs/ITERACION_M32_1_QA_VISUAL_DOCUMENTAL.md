# Iteración M32.1 — Preflight y evidencia visual documental

## Objetivo

Extender la compuerta común de calidad documental a `CO-LA-001`, `CO-LA-002` y `CO-EM-004`, y crear evidencia reproducible del renderizado de documentos reales generados por las fábricas activas.

La iteración conserva los once productos, formularios, reglas, anexos condicionales, revisiones inmutables, comparación, RBAC, auditoría y aprobación dual. No sustituye las fábricas extensas por documentos resumidos.

## Componentes incorporados

### 1. Preflight visual estructural

El módulo `legalai_platform/document_visual_quality.py` inspecciona el DOCX antes del renderizado y reporta:

- tamaño de página y márgenes;
- ancho y altura imprimibles;
- encabezados y cláusulas detectables;
- ordinal y título inicial en negrita;
- párrafos excesivamente extensos;
- tablas anchas;
- encabezados repetibles;
- filas protegidas contra división;
- numeración de página;
- zona de firmas;
- acumulación de párrafos vacíos.

Los errores estructurales bloquean la entrega. Las advertencias quedan disponibles para revisión jurídica y QA.

El preflight declara expresamente `requires_human_visual_review: true`; por tanto, no se interpreta como aprobación visual humana.

### 2. Integración en fábricas activas

#### CO-LA-001

La fábrica v2.53 conserva el cálculo, conciliación económica, informe, reclamación, matriz probatoria y acuerdo. Cada DOCX incorpora ahora:

- informe de integridad OOXML;
- apertura comprobada con `python-docx`;
- hash SHA-256;
- métricas estructurales;
- preflight visual y advertencias.

#### CO-LA-002

La fábrica v2.39 conserva su evaluación y paquete, y añade:

- ordinales jurídicos en letras: `CLÁUSULA PRIMERA`, `SEGUNDA`, etc.;
- pie con identificación `LegalAIZ.it`, código de producto y campo de página;
- encabezados protegidos para evitar que queden aislados al final de página;
- tabla de firmas con encabezado repetible y filas protegidas contra división;
- reglas de ejecución y límites en el anexo de funciones;
- compuerta común de integridad y preflight visual para contrato y anexos;
- señal explícita de revisión visual humana pendiente.

Las aprobaciones jurídica y QA permanecen en estado `pending` después de generar.

#### CO-EM-004

La fábrica v2.47 conserva el acuerdo extenso de confidencialidad, propiedad intelectual, seguridad, datos, IA y anexos. Todos sus DOCX incorporan la compuerta común, hash, métricas y preflight visual.

## Evidencia renderizada en CI

GitHub Actions genera muestras mediante las fábricas activas, no mediante documentos estáticos. Luego:

1. convierte cada DOCX a PDF con LibreOffice Writer;
2. obtiene el número real de páginas con `pdfinfo`;
3. rasteriza todas las páginas a PNG con Poppler;
4. comprueba que el número de PNG coincide con el número de páginas del PDF;
5. conserva DOCX, PDF, PNG y metadatos como artefacto por 30 días.

Resultado de la ejecución de rama `31050025748`:

| Documento | Páginas renderizadas |
|---|---:|
| `CO-EM-004_Acuerdo_Confidencialidad_PI.docx` | 7 |
| `CO-LA-002_Contrato_Indefinido.docx` | 3 |
| **Total** | **10** |

Artefacto:

- nombre: `m32-1-evidencia-visual-docx`;
- ID: `8948018411`;
- tamaño: `2.719.016` bytes;
- digest: `sha256:0280f8903a03b3c10a225cfb3a3ef0d53980917d2a4e1498405c51f0bb91ec04`;
- expiración prevista: `2026-09-04`.

## Validaciones aprobadas en la rama

- compilación Python;
- once regresiones documentales;
- integridad OOXML;
- apertura con `python-docx`;
- generación real de `CO-LA-002`;
- integración de `CO-LA-001` y `CO-EM-004`;
- 11 formularios y 473 preguntas demo;
- arranque HTTP y `/api/live`;
- conversión de dos DOCX reales a PDF;
- rasterización completa de diez páginas;
- carga del artefacto de evidencia.

## Límite de la evidencia

La conversión y rasterización demuestran que los documentos pueden abrirse, paginarse y representarse de extremo a extremo. No prueban por sí solas que cada página sea visualmente óptima.

La aprobación visual final continúa requiriendo inspección humana de las imágenes renderizadas para verificar, entre otros aspectos:

- viudas y huérfanas;
- cortes de cláusulas;
- equilibrio del espacio en blanco;
- tablas partidas o desbordadas;
- firmas separadas del contenido correspondiente;
- legibilidad de encabezados y pies;
- consistencia tipográfica entre páginas;
- calidad en Word para Mac y Microsoft Word para Windows.

## Estado acumulado de la compuerta común

Productos con integración activa al terminar M32.1:

- `CO-EM-003`;
- `CO-EM-004`;
- `CO-AR-001`;
- `CO-LA-001`;
- `CO-LA-002`.

Productos pendientes de integración transversal:

- `CO-TR-001`;
- `CO-TR-002`;
- `CO-SA-001`;
- `CO-CD-001`;
- `CO-CD-003`;
- `CO-CD-004`.
