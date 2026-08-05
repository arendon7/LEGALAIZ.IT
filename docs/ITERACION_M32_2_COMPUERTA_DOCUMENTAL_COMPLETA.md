# Iteración M32.2 — Compuerta documental completa

## Objetivo

Extender el control técnico y visual común a los seis productos que no contaban con integración transversal explícita al terminar M32.1:

- `CO-TR-001`;
- `CO-TR-002`;
- `CO-SA-001`;
- `CO-CD-001`;
- `CO-CD-003`;
- `CO-CD-004`.

La solución conserva los once productos, 473 preguntas demo, reglas, módulos condicionales, documentos extensos, RBAC, auditoría, revisiones inmutables, comparación y aprobación dual. No reemplaza las fábricas especializadas ni modifica sus decisiones jurídicas.

## Arquitectura adoptada

La compuerta se instala sobre el constructor documental común antes de importar el núcleo histórico. De esta forma, cada DOCX generado por las rutas activas debe superar:

1. comprobación ZIP y CRC;
2. presencia de partes OOXML obligatorias;
3. resolución de relaciones internas;
4. apertura con `python-docx`;
5. control de variables y valores centinela;
6. conservación del código del producto;
7. cálculo de hash SHA-256;
8. preflight de página, márgenes, encabezados, tablas, filas, firmas y paginación;
9. escritura atómica de un manifiesto lateral auditable.

Los errores bloquean la devolución del documento al flujo de generación. Las advertencias no bloqueantes se registran para el especialista jurídico y QA.

## Manifiesto lateral

Cada documento aprobado por el preflight genera un archivo con sufijo:

`.docx.quality.json`

El manifiesto contiene:

- versión de la compuerta;
- fecha en zona `America/Bogota`;
- producto y nombre del archivo;
- hash SHA-256;
- informe técnico OOXML;
- informe de estructura visual;
- advertencias consolidadas;
- estado de aprobación jurídica `pending`;
- estado de aprobación QA `pending`;
- `requires_human_visual_review: true`;
- declaración expresa de que el preflight no reemplaza revisión jurídica ni inspección humana página por página.

## Cobertura de la ola

| Producto | Muestra sustantiva preferida |
|---|---|
| CO-TR-001 | Informe de coincidencia y diagnóstico SAST |
| CO-TR-002 | Solicitud integral de expediente y preservación de evidencia |
| CO-SA-001 | Derecho de petición integral ante EPS o IPS |
| CO-CD-001 | Reclamo integral de hábeas data financiero |
| CO-CD-003 | Diagnóstico jurídico del mecanismo de consumo |
| CO-CD-004 | Diagnóstico de obligación, título y ruta de cobro |

La CI crea los expedientes demo mediante `core_v11` y `document_specs`, selecciona una muestra real por producto, verifica los seis manifiestos, convierte los DOCX a PDF, rasteriza todas las páginas y conserva el paquete como artefacto.

## Salvaguardas

- No se declara aprobación jurídica automática.
- No se declara aprobación QA automática.
- La rasterización no equivale a revisión visual humana.
- La compuerta no altera el texto sustantivo ni las reglas de selección documental.
- La desactivación mediante `LEGAL_DISABLE_DOCX_RELEASE_GATE` existe únicamente para recuperación técnica controlada; no debe utilizarse para una liberación ordinaria.
- El arranque oficial desde `run.py` instala expresamente la compuerta antes de cargar el núcleo.
- `sitecustomize.py` protege entradas históricas, scripts y pruebas que importen el constructor de forma directa.

## Criterio de cierre

M32.2 solo puede considerarse integrada cuando concurran:

1. regresiones específicas aprobadas;
2. CI general sin regresiones;
3. generación real de los seis productos;
4. seis manifiestos válidos con aprobación dual pendiente;
5. conversión de las seis muestras a PDF;
6. rasterización completa de todas sus páginas;
7. artefacto auditable disponible;
8. PR fusionado a `main`;
9. validación posterior a la fusión;
10. publicación de GitHub Pages sin regresiones.
