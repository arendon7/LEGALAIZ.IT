# M36.2 — Review Lifecycle Reconciliation

## Objetivo

M36.2 reconcilia el estado operativo M24 del expediente con evidencia ya existente en la Mesa Jurídica M32. No crea decisiones jurídicas, no crea decisiones QA, no libera documentos y no registra entrega.

El problema que resuelve es la posible divergencia entre dos capas legítimas:

- **M32.5/M32.6** conserva la verdad documental: revisión vigente, SHA-256, hallazgos, aprobación jurídica, aprobación QA y liberación;
- **M24.6** conserva el recorrido operativo del expediente.

Sin M36.2, los documentos pueden avanzar en M32 mientras M24 continúa en `EN_REVISION_JURIDICA`. M36.2 transforma únicamente evidencia humana ya registrada en hitos derivados del journey.

## Precondiciones

La reconciliación falla cerrada si no se cumplen simultáneamente:

1. existe un intake M36.0 del mismo expediente con estado canónico `EN_REVISION_JURIDICA`;
2. existe una asignación M36.1 `COMPLETE` para ese mismo intake;
3. todos los desks M36.0 aparecen como asignados y con handoff M32.7 evaluado;
4. especialista y QA son personas distintas;
5. cada desk apunta al mismo expediente fuente;
6. la cadena M32.5 es íntegra;
7. la cadena M32.6 es íntegra;
8. los responsables visibles en M32.6 coinciden con M36.1;
9. toda aprobación utilizada corresponde a la revisión y SHA-256 vigentes y al profesional asignado.

## Agregación case-level

M36.2 no permite que un solo documento determine el estado de un expediente con varios documentos.

Estados agregados:

- `LEGAL_REVIEW`: falta aprobación jurídica completa en al menos un documento.
- `OBSERVED`: al menos un documento tiene cambios requeridos, rechazo o hallazgos pendientes.
- `LEGAL_APPROVED`: todos los documentos tienen aprobación jurídica válida del especialista asignado y QA aún no está completo.
- `QA_APPROVED`: todos los documentos tienen aprobación jurídica y QA independientes válidas sobre las revisiones vigentes.

La liberación se calcula aparte con `release_complete`; no convierte el expediente en entregado.

## Reconciliación M24

El cliente HTTP no puede indicar un estado objetivo. El servidor calcula el único camino permitido por la evidencia.

Ejemplos:

- `EN_REVISION_JURIDICA` + `LEGAL_APPROVED` → `APROBADO_JURIDICAMENTE` → `EN_QA`.
- `EN_QA` + `QA_APPROVED` → `APROBADO_QA`.
- `EN_REVISION_JURIDICA` + `QA_APPROVED` → los tres hitos anteriores en una sola transacción.
- un estado documental observado puede llevar a `OBSERVADO`.
- una regresión después de una aprobación ya reflejada en M24 no rebobina el journey: se propone `ESCALADO` cuando M24 lo permite.

Las transiciones derivadas se registran con actor técnico `system-m36-2`. Los IDs del especialista y QA que realizaron las decisiones fuente quedan registrados separadamente en la evidencia y en la cadena M36.2. El sistema no suplanta su identidad.

## Correcciones después de observaciones

`OBSERVADO → CORREGIDO` requiere evidencia documental sustantiva diferente a la que originó la observación.

Cambios que sí pueden modificar esa evidencia:

- nueva revisión;
- cambio de SHA de la revisión vigente mediante el mecanismo inmutable de nueva revisión;
- cierre de hallazgos;
- nueva decisión jurídica o QA válida;
- liberación de la revisión aprobada.

Cambios puramente operativos de M32.6 —prioridad, SLA, notas o reconocimientos— no cuentan como corrección jurídica.

## Cadena de reconciliación

Cada transición M36.2 se persiste en `m36_review_reconciliation_event` con:

- secuencia por expediente;
- estado origen y destino;
- estado agregado M32;
- fingerprint de evidencia;
- snapshot interno de evidencia;
- usuario administrador que inició la reconciliación;
- aprobadores humanos fuente;
- `previous_hash`;
- `event_hash`.

La cadena se verifica antes de añadir eventos y antes de devolver history. Una alteración bloquea nuevas reconciliaciones.

## API

Prefijo: `/api/m36/review-lifecycle`.

- `GET /cases/{case_id}`: assessment administrativo, sin hashes ni payload jurídico.
- `GET /cases/{case_id}/history`: historial resumido de reconciliaciones y validez de cadena.
- `POST /cases/{case_id}/reconcile`: única mutación; exige sesión admin, same-origin y CSRF.

No existe parámetro `target` ni una ruta genérica para imponer estados.

## Delivery boundary

M36.2 nunca registra `ENTREGADO`.

Cuando todos los documentos están liberados sobre el hash aprobado y M24 está en `APROBADO_QA`, el assessment puede indicar:

`delivery_gate_ready = true`

Esto significa únicamente que una futura compuerta de entrega tiene evidencia suficiente para iniciar su propia decisión. La entrega requiere un milestone posterior, confirmación y trazabilidad independientes.

## Datos y observabilidad

La respuesta pública no expone:

- SHA-256 de revisiones;
- hashes de decisiones;
- fingerprint interno de evidencia;
- `evidence_json`;
- relato M34;
- respuestas del formulario;
- información de pago o recibos.

Observabilidad registra IDs, estados y conteos, no contenido jurídico.

## QA requerido

La certificación M36.2 exige como mínimo:

- suite completa del repositorio;
- contrato canónico M36.0 → M36.2;
- cobertura multi-documento;
- aprobación jurídica parcial no suficiente;
- QA parcial no suficiente;
- separación de funciones;
- idempotencia;
- observación/corrección;
- cambio operativo no considerado corrección;
- regresión → escalamiento;
- detección de cadena alterada;
- HTTP real M34 → M35 → M36.0 → M36.1 → decisiones M32 → M36.2;
- M33.1 public demo smoke;
- visual DOCX.

La certificación técnica no constituye aprobación jurídica, QA, entrega ni autorización de producción real.
