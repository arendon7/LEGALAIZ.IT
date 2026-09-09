# M36.3 — Controlled Delivery Gate

## Objetivo

M36.3 convierte una liberación documental ya aprobada por M32 y reconciliada por M36.2 en una **puesta a disposición controlada dentro del expediente autenticado**, sin inventar aprobación jurídica, aprobación QA, correo enviado, descarga, lectura ni recepción externa.

La frontera de M36.3 es deliberada:

- M36.2 termina en `APROBADO_QA` y, cuando todas las copias exactas están liberadas, declara `delivery_gate_ready=true`.
- M36.3 verifica nuevamente esa evidencia, prepara un paquete sólo con las copias liberadas M32.5, registra la entrega in-app y sincroniza M24 a `ENTREGADO`.
- M36.3 no reemplaza M32.4/M32.5, no crea decisiones profesionales y no envía comunicaciones externas.

## Fuente de verdad documental

Los bytes finales se obtienen exclusivamente mediante `ApprovalDeskWorkspace.released_path()`.

No se usa `documents.file_path` como fuente de entrega final. Esto evita que un borrador, una revisión posterior no aprobada o un archivo mutable distinto del hash liberado sea entregado por error.

Por cada mesa documental se valida:

1. existencia de una liberación vigente;
2. integridad de la cadena M32;
3. `release_id` y `revision_id` vigentes;
4. SHA-256 del archivo liberado;
5. `release_record_hash` del registro de liberación;
6. cobertura de todas las mesas del expediente.

## Prerrequisitos

La entrega falla cerrada salvo que concurran todos estos elementos:

- expediente con titular verificable;
- intake M36.0 existente;
- asignación M36.1 `COMPLETE`;
- trazabilidad entre intake y asignación intacta;
- cadena M36.2 íntegra;
- M24 exactamente en `APROBADO_QA`;
- aprobación QA completa en todos los documentos;
- liberación M32 completa en todos los documentos;
- `delivery_gate_ready=true`;
- ausencia de blockers o reconciliaciones pendientes;
- confirmación administrativa exacta `ENTREGAR SOLUCIÓN`.

## Saga recuperable

La operación no presume atomicidad entre filesystem, SQLite y el `commit` interno de M24. Se implementa como saga explícita:

1. verificar todos los prerequisitos;
2. construir ZIP sobre los bytes liberados exactos;
3. persistir `m36_controlled_delivery.state=PREPARED`;
4. registrar M24 `APROBADO_QA → ENTREGADO` con evidencia exacta del delivery;
5. finalizar el mismo registro como `DELIVERED_IN_APP`.

Si el proceso cae después del paso 4, el retry:

- no crea un segundo paquete;
- no crea una segunda transición `ENTREGADO`;
- verifica que la transición M24 corresponde al mismo `delivery_id` y hashes;
- conserva como `delivered_by` al actor que produjo la transición original;
- conserva como `delivered_at` la fecha de esa transición;
- sólo termina la reconciliación del ledger M36.3.

## Paquete de entrega

El ZIP contiene:

- `documentos_finales/` con las copias M32 liberadas;
- `MANIFEST.json`;
- `CONSTANCIA_PUESTA_A_DISPOSICION.json`;
- `LEEME.txt`.

El manifiesto público contiene únicamente nombre, SHA-256 y tamaño de cada archivo, además del identificador de entrega, expediente, producto, canal y controles de gobernanza. No expone `release_id`, `revision_id`, `release_record_hash`, rutas internas, asignaciones o identificadores de aprobadores.

La generación usa orden estable de archivos y metadata ZIP fija para reducir variaciones no sustantivas del paquete construido sobre el mismo payload.

## Significado exacto de `ENTREGADO`

En M36.3, `ENTREGADO` / `DELIVERED_IN_APP` significa exclusivamente:

> el paquete final quedó puesto a disposición del titular dentro de su expediente autenticado.

No significa ni acredita por sí mismo:

- que el titular descargó el paquete;
- que abrió o leyó los documentos;
- que recibió un correo;
- que un mensaje externo fue entregado;
- que existe constancia legal de notificación o recepción;
- que la solución garantiza un resultado jurídico.

Esta distinción es obligatoria para no convertir telemetría técnica en una conclusión probatoria que el sistema no puede sostener.

## Descargas

Una solicitud autenticada al endpoint de descarga registra `DOWNLOAD_REQUESTED`.

Ese evento acredita que el servidor recibió una petición autorizada y comenzó la respuesta del paquete íntegro. No se denomina `DOWNLOADED`, `RECEIVED` ni `READ`, porque el servidor no puede inferir de manera fiable que la transferencia terminó, que el archivo fue abierto o que su contenido fue leído.

## Control de acceso

- sólo `admin` puede ejecutar la entrega;
- administración puede consultar la cola y paquetes entregados;
- el cliente titular puede consultar y solicitar descarga de su entrega;
- otro cliente no recibe confirmación de existencia: la lectura case-level se oculta como `404 DELIVERY_NOT_AVAILABLE`;
- especialistas no obtienen acceso a entregas de cliente por esta superficie;
- POST de entrega exige same-origin, sesión autenticada y CSRF.

## Bloqueo de bypass

M36.3 cierra dos superficies:

1. **HTTP M24:** un expediente con intake M36 no puede usar el endpoint genérico para registrar `ENTREGADO`; responde `M36_CONTROLLED_DELIVERY_REQUIRED`.
2. **Runtime interno:** `M24_CASE_JOURNEY.transition` queda envuelto con una guarda que, para casos M36, exige un delivery `PREPARED` y evidencia exacta del mismo paquete antes de aceptar `ENTREGADO`.

Los expedientes históricos que nunca ingresaron a M36 conservan la semántica heredada de M24.

## Seguridad e integridad

M36.3 valida antes de entregar y en reintentos:

- hash del ZIP;
- hash del manifiesto;
- cobertura del manifiesto;
- hashes y tamaños de archivos del ZIP;
- hash del snapshot de liberaciones;
- `release_record_hash` de cada liberación;
- correspondencia del snapshot con las liberaciones M32 actuales;
- correspondencia de intake/asignación/cantidad de mesas;
- evidencia exacta de la transición M24.

La observabilidad no registra narrativa jurídica, respuestas del usuario, rutas internas, hashes del paquete, datos de pago ni payloads de evidencia jurídica. Usa ids operativos, estados, conteos e IP resumida mediante hash.

## Fuera de alcance

M36.3 no implementa:

- correo transaccional de entrega;
- WhatsApp/SMS;
- firma electrónica;
- acuse legal de recibo;
- notificación judicial o administrativa;
- seguimiento post-entrega;
- cierre del expediente;
- aprobación automática de documentos;
- garantía de resultado.

El seguimiento y cierre pertenecen a una ola posterior.

## Evidencia requerida para certificación técnica

M36.3 sólo podrá considerarse técnicamente certificado cuando un SHA exacto demuestre:

- suite completa sin regresiones;
- pruebas adversariales de saga e integridad;
- bloqueo HTTP e interno del bypass M24;
- smoke HTTP real desde M35 hasta M36.3;
- aislamiento cross-tenant;
- idempotencia;
- descarga registrada únicamente como request;
- preservación de 11 productos / 473 preguntas;
- M33.1 PASS;
- visual-docx PASS.

La certificación técnica no equivale a aprobación jurídica, QA profesional, autorización de producción ni acreditación de entrega por un canal externo.
