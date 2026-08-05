# Iteración M32.0 — Calidad documental verificable

## Objetivo

Elevar la confiabilidad del demo sin reducir las capacidades canónicas. La intervención añade una compuerta común de calidad a los DOCX y conserva el flujo de revisión jurídica, QA, revisiones inmutables, comparación y liberación controlada.

## Hallazgos confirmados

1. La aplicación carga las fábricas especializadas desde `legalai_runtime_modules` mediante `core_v11.py` y `legalai_platform/runtime_registry.py`.
2. `CO-EM-003` y `CO-AR-001` utilizan fábricas versionadas activas con documentos extensos y anexos condicionales.
3. `CO-LA-002` genera un contrato laboral y anexos editables, y mantiene las aprobaciones jurídica y QA en estado pendiente después de generar.
4. Las comprobaciones existentes abrían los archivos con `python-docx`, buscaban algunos valores centinela y calculaban hash, pero no verificaban de forma transversal las relaciones internas del paquete OOXML.
5. La CI validaba sintaxis, datos demo y arranque HTTP, pero no ejecutaba regresiones unitarias de integridad documental.

## Cambios implementados

### 1. Compuerta común `legalai_platform/document_quality.py`

Valida antes de liberar un DOCX:

- existencia y tamaño razonable;
- integridad ZIP y CRC;
- presencia de partes OOXML obligatorias;
- sintaxis de cada XML y archivo de relaciones;
- existencia de los destinos de relaciones internas;
- apertura efectiva con `python-docx`;
- contenido jurídico mínimo;
- variables y valores centinela sin resolver;
- conservación del código del producto;
- párrafos extensos duplicados;
- hash SHA-256, métricas y advertencias.

Los errores bloquean la generación. Los campos editables compatibles con un borrador, como líneas de firma o `N/A`, se registran como advertencias para revisión humana y no se confunden con una corrupción estructural.

### 2. `CO-EM-003`

- Normalización semántica no destructiva de partes, identificación, representante, objeto, resultado esperado, alcance, exclusiones, entregables y criterios de aceptación.
- Los alias heredados solo completan una ruta canónica vacía.
- Ninguna respuesta canónica es reemplazada.
- Todos los documentos y anexos deben superar la compuerta común antes de quedar registrados en el manifiesto.

### 3. `CO-AR-001`

- Se conserva la fábrica completa v2.49 heredada por v2.50.
- No se sustituye el contrato por un resumen ni se elimina ningún anexo.
- Todos los DOCX generados se validan estructuralmente y guardan métricas y advertencias en el manifiesto.

### 4. `CO-LA-002`

- Se mantiene la fábrica activa v2.39 para no romper su evaluación, paquete ni gobernanza.
- La CI genera un contrato laboral real mediante esa fábrica, lo vuelve a abrir, verifica su código, extensión, integridad OOXML, hash y estados pendientes de aprobación jurídica y QA.
- La mejora de redacción y parametrización de anexos se abordará sobre evidencia visual del documento generado, sin reescribir a ciegas una fábrica ya funcional.

### 5. CI

Se incorpora `unittest` antes de la validación de interfaz y del smoke HTTP. La entrega falla ante:

- DOCX corrupto;
- relación OOXML rota;
- marcador sin resolver;
- regresión de apertura con `python-docx`;
- pérdida del identificador de producto;
- fallo de generación del contrato activo `CO-LA-002`;
- alteración de los estados pendientes de aprobación dual.

## Criterios de aceptación

- [ ] Compilación Python completa.
- [ ] Regresiones documentales aprobadas.
- [ ] Validación de los 11 formularios y datos demo aprobada.
- [ ] Arranque HTTP y `/api/live` aprobados.
- [ ] PR revisable y trazable.
- [ ] Sin fusión a `main` hasta que GitHub Actions esté en verde.

## Alcance deliberadamente no modificado

- RBAC, MFA, auditoría y separación de usuarios.
- Registro de revisiones y comparación.
- Aprobación jurídica y QA.
- Catálogo de 11 productos.
- Preguntas, reglas, fuentes y módulos condicionales.
- Publicación Pages y ejecución completa en Codespaces/local.
