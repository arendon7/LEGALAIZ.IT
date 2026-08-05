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

## Correcciones de fábrica detectadas por la compuerta

La integración no se limitó a envolver archivos existentes. La ejecución fail-closed identificó y permitió corregir dos defectos OOXML en el constructor común:

1. **Relación de imagen huérfana.** Cuando el PNG del logotipo no existía, el paquete omitía `word/media/logo-legalaizit-docx.png`, pero conservaba la relación hacia ese recurso. El constructor ahora evalúa una única condición `has_logo` y solo declara y empaqueta la relación de imagen cuando el archivo existe. Esto elimina la causa técnica del aviso de recuperación observado en Microsoft Word.
2. **Tablas sin grilla OOXML.** Las tablas y zonas de firma declaraban filas y celdas, pero no `<w:tblGrid>`. Word podía tolerar algunos archivos, aunque `python-docx` no podía inspeccionar sus columnas de forma determinista. Todas las tablas incorporan ahora grillas, anchos fijos y filas protegidas contra división.

Estas correcciones se aplican al constructor raíz sin reducir contenido ni sustituir las fábricas especializadas.

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

| Producto | Muestra generada con fábrica activa | Páginas PDF/PNG |
|---|---|---:|
| CO-TR-001 | Informe de coincidencia y diagnóstico SAST | 2 |
| CO-TR-002 | Solicitud integral de expediente y preservación de evidencia | 2 |
| CO-SA-001 | Derecho de petición integral ante EPS o IPS | 3 |
| CO-CD-001 | Reclamo integral de hábeas data financiero | 3 |
| CO-CD-003 | Diagnóstico jurídico del mecanismo de consumo | 3 |
| CO-CD-004 | Diagnóstico de obligación, título y ruta de cobro | 3 |
| **Total** | **Seis documentos** | **16** |

La evidencia no depende del conjunto parcial de `seed_demo()`. El script crea expedientes sintéticos controlados, completa las variables del cuestionario y llama directamente a las fábricas activas:

- `expanded_documents.document_specs`;
- `docx_builder.build_docx` protegido por la compuerta M32.2.

No se utiliza una plantilla paralela ni contenido estático sustitutivo. Cada muestra mantiene sujetos diferenciados, hash propio, manifiesto válido, aprobación dual pendiente y revisión visual humana requerida.

## Evidencia CI de rama

La ejecución `31052985186` aprobó:

- tres regresiones específicas M32.2;
- generación de una muestra real por cada producto de la ola;
- seis paquetes OOXML válidos;
- seis aperturas con `python-docx`;
- seis manifiestos `.docx.quality.json`;
- verificación de aprobación jurídica y QA en estado `pending`;
- conversión de los seis DOCX a PDF;
- rasterización completa de las 16 páginas a PNG;
- correspondencia exacta entre páginas PDF y archivos PNG;
- carga del artefacto auditable.

Artefacto de rama:

- nombre: `m32-2-evidencia-seis-productos`;
- ID: `8949158313`;
- tamaño: `2.693.980` bytes;
- digest: `sha256:074b98b4d16abda3f78e87878d7a9acf1421729bc1cc934676b24b362a43c655`;
- archivos cargados: `252`;
- retención: `30` días.

La ejecución general `31052990442` aprobó el trabajo `smoke`; la misma revisión incluye sintaxis, regresiones existentes, 11 productos, 473 preguntas demo y arranque HTTP. El trabajo visual M32.1 también debe mantenerse en verde antes de abrir el PR.

## Salvaguardas

- No se declara aprobación jurídica automática.
- No se declara aprobación QA automática.
- La rasterización no equivale a revisión visual humana.
- La compuerta no altera el texto sustantivo ni las reglas de selección documental.
- La desactivación mediante `LEGAL_DISABLE_DOCX_RELEASE_GATE` existe únicamente para recuperación técnica controlada; no debe utilizarse para una liberación ordinaria.
- El arranque oficial desde `run.py` instala expresamente la compuerta antes de cargar el núcleo.
- `sitecustomize.py` protege entradas históricas, scripts y pruebas que importen el constructor de forma directa.
- Los datos de las muestras son sintéticos y no corresponden a personas, expedientes o controversias reales.

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
