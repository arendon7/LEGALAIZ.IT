# M35.3 — Case Activation & Purchase Confirmation

Estado: **implementación técnica candidata a certificación**. Este milestone no autoriza pagos reales, precios comerciales definitivos, producción jurídica real ni liberación documental automática.

## Objetivo

Cerrar la experiencia inmediatamente posterior a M35.2 para que el cliente pueda entender, desde su expediente y sin reconstruir mentalmente el checkout:

1. qué nivel de servicio quedó asociado;
2. qué orden sandbox originó el expediente;
3. qué comprobante sandbox se generó;
4. si la cadena de pago está íntegramente verificada;
5. si los documentos ya fueron materializados;
6. en qué estado operativo M24 está el expediente; y
7. cuál es el siguiente paso útil.

M35.3 no crea un comercio nuevo. Construye una vista de activación a partir de evidencia ya existente y certificada en M35.2.

## Frontera de arquitectura

### Backend

`CaseActivationCenter` es un **read model fail-closed**. No crea ni modifica:

- órdenes;
- payment intents;
- eventos de pago;
- expedientes;
- documentos;
- revisiones;
- aprobaciones;
- entregas; ni
- seguimientos.

El endpoint es únicamente:

`GET /api/m35/activation/<case_id>`

Requiere sesión `client`. El `case_id` se resuelve siempre con `owner_id` exacto antes de consultar la cadena comercial.

### Frontend

`case_activation_m35_3.js` mejora progresivamente `/caso/<case_id>` para clientes:

- un expediente M35.3 íntegro muestra tarjeta de activación;
- un expediente legacy devuelve `NOT_M35_COMMERCE_CASE` y no cambia visualmente;
- una inconsistencia M35 no muestra una confirmación positiva: renderiza una advertencia de verificación;
- un expediente `CASE_CREATED_DOCUMENTS_PENDING` indica recovery y conduce al mismo checkout, nunca a una segunda compra.

La UI no decide si un expediente está activado. Sólo representa la respuesta verificada del backend.

## Cadena mínima exigida para `ACTIVE`

M35.3 sólo devuelve `activation_status=ACTIVE` cuando todas estas condiciones coinciden:

1. el expediente existe y pertenece al cliente autenticado;
2. existe un único vínculo M35.2 para el mismo `user_id` y `case_id`;
3. producto del vínculo = producto del expediente;
4. existen timestamps de consentimiento de checkout y creación del expediente;
5. la orden pertenece al usuario y apunta exactamente al mismo expediente;
6. la orden está `Completada`;
7. la orden conserva `commerce_trace_required=true`;
8. el nivel de servicio del ledger coincide con `checkout_orders.service_mode`;
9. `review_selected` coincide con el nivel (`solucion_revisada` / `documento_personalizado`);
10. existe payment intent y pertenece al mismo usuario y orden;
11. el intent está `succeeded`;
12. importe y moneda coinciden con la orden;
13. la cadena de eventos sandbox conserva SHA/HMAC válidos y al menos dos eventos;
14. existe `receipt_number` con prefijo sandbox `RCPT-SBX-`;
15. existe al menos un documento no-audit vinculado;
16. existe journey M24 para el mismo producto;
17. el estado M24 está en una fase compatible con materialización; y
18. el historial M24 conserva una transición explícita a `GENERADO`.

Si una sola condición falla, no existe confirmación positiva.

## Estados públicos

### `ACTIVE`

La cadena está verificada y la materialización documental ocurrió. No significa que el documento esté jurídicamente aprobado o entregado.

### `DOCUMENTS_PENDING`

M35.2 ya creó el caso y vinculó la orden, pero la materialización/reconciliación no terminó. La acción indicada es volver al mismo checkout y reintentar la preparación. No debe existir un segundo pago, orden o caso.

No se exponen otros estados internos del ledger como equivalentes a una activación.

## Comprobante sandbox

La tarjeta presenta:

- `order_id`;
- `receipt_number` sandbox;
- método sandbox;
- importe y moneda de la orden histórica;
- nivel de servicio;
- indicación explícita `real_charge=false`.

No se presenta como factura, recibo fiscal ni prueba de un cargo real.

## Privacidad y minimización

La respuesta pública no contiene:

- relato original;
- respuestas jurídicas;
- IDs de hechos;
- `handoff_id`;
- `draft_id`;
- `intake_id`;
- `decision_id`;
- claves de idempotencia;
- hashes de snapshots;
- `provider_reference`;
- payloads de eventos;
- firmas HMAC; ni
- `user_id`.

Observabilidad se limita a IDs operativos, producto, estado, conteo de documentos y estado M24. No registra receipt, respuestas, relato, payload de pago ni firma.

## Relación entre nivel comercial y controles jurídicos

`review_included` describe el **nivel comercial adquirido**, no elimina controles internos.

La Fábrica Documental conserva de forma independiente:

- revisiones inmutables;
- trazabilidad;
- aprobación jurídica;
- QA;
- regla de aprobadores distintos cuando corresponda; y
- compuertas de liberación.

Por eso M35.3 muestra expresamente que la activación del expediente no equivale a aprobación, entrega o garantía de resultado.

## Siguiente paso

El backend determina una acción explicable, sin probabilidades de éxito jurídico:

- `RETRY_DOCUMENT_PREPARATION` — materialización pendiente;
- `WAIT_FOR_REVIEW` — documentos generados y revisión incluida/exigida;
- `REVIEW_IN_PROGRESS` — recorrido ya está en revisión;
- `ESCALATED_REVIEW` — expediente escalado;
- `REVIEW_DELIVERY_OR_FOLLOWUP` — QA/entrega/seguimiento avanzado;
- `REVIEW_DRAFTS` — documento generado sin servicio comercial de revisión.

El frontend sólo navega al tab o ruta indicada por el read model.

## Compatibilidad

- M35.3 extiende `http_handler_m35_2.Handler`.
- No sobrescribe rutas M34/M35 anteriores.
- Un expediente legacy continúa usando el workspace M29 sin tarjeta M35.3.
- Una base legacy donde todavía no existe `m35_commerce_case_links` devuelve `NOT_M35_COMMERCE_CASE`, no error interno.
- M35.2 recovery conserva autoridad para finalizar documentos; M35.3 no llama payment ni finalize directamente.

## QA requerido antes de certificar

1. `compileall` completo.
2. Suite integral sin regresiones.
3. Pruebas unitarias M35.3 de cadena e integridad.
4. Contratos estáticos de runtime, privacidad, UX y accesibilidad.
5. Sintaxis JS del módulo M35.3.
6. Smoke HTTP real M34.2 → M35.3.
7. Cross-tenant de endpoint M35.3 bloqueado con 404 neutral.
8. 11 productos y piso de 473 preguntas preservados.
9. M33.1 public-demo smoke preservado.
10. visual-docx preservado.

## Límites del milestone

M35.3 **no incluye**:

- pagos reales;
- facturación electrónica;
- conciliación bancaria;
- precios aprobados comercialmente;
- asignación automática de abogado;
- SLA operativo;
- colas de especialistas;
- mensajería transaccional nueva;
- notificaciones de producción;
- entrega automática; ni
- seguimiento jurídico M37.

Asignación, operación de la revisión y fulfillment interno a escala corresponden a M36.
