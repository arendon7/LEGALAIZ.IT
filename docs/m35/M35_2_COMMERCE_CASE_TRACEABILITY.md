# M35.2 — Commerce → Case Traceability Bridge

Estado: **candidato técnico listo para certificación CI sobre SHA limpio**. No autoriza pagos reales, precios comerciales definitivos ni producción jurídica real. La evidencia de certificación del SHA final se registra en el PR para evitar modificar el commit después del gate.

## Objetivo

Cerrar el tramo `fulfillment → checkout sandbox → pago verificable → expediente → documentos → recorrido operativo` sin crear un comercio paralelo ni perder la trazabilidad de M34/M35.

M35.2 reutiliza:

- `SelfServiceCenter` para borradores y `checkout_orders`;
- `PaymentSandboxCenter` para intents idempotentes y eventos firmados;
- `M24CaseJourneyCenter` para reconciliar el expediente sólo cuando ya existen documentos;
- la continuidad M35.0/M35.1 como fuente de ownership del diagnóstico y draft.

## Invariantes

1. Una cuenta cliente sólo opera su propio handoff, draft, orden, intento y expediente.
2. El checkout M35 requiere consentimiento explícito.
3. Sólo se admiten `documento_personalizado` y `solucion_revisada` cuando el nivel está habilitado en la oferta canónica.
4. Riesgo rojo, revisión obligatoria o `service_mode=blocked` fuerzan `solucion_revisada`.
5. El precio de la orden debe coincidir con la oferta sandbox canónica en el momento del checkout.
6. El ledger no duplica relato ni respuestas: conserva IDs, estados y hashes SHA-256 del snapshot de draft y orden.
7. No puede existir una segunda orden activa para el mismo handoff. Una orden pendiente puede invalidarse explícitamente sólo antes de crear un payment intent.
8. Una edición posterior al checkout cambia el hash y bloquea la creación del expediente.
9. M35.2 no acepta `Pagado (simulado)` del flujo legacy. Exige intent sandbox `succeeded`, orden `Pagado (sandbox)` y eventos con SHA/HMAC íntegros.
10. El pago y la creación del expediente son acciones distintas. El segundo paso exige consentimiento explícito.
11. El resultado jurídico se recalcula antes del expediente; un cambio de riesgo bloquea la materialización hasta reconciliar.
12. El precio canónico se vuelve a comprobar antes de crear el expediente.
13. Orden, payment intent, expediente y recuperación de materialización son idempotentes: un reintento no crea duplicados.
14. Los endpoints legacy de orden/pago/caso no pueden saltarse una continuidad M35 activa.
15. La creación del registro del expediente y la vinculación de la orden ocurren antes de materializar documentos físicos.
16. Si falla generación o reconciliación, el expediente queda en `CASE_CREATED_DOCUMENTS_PENDING`; no se borra el pago ni se crea un segundo caso.
17. Un reintento pendiente reutiliza el mismo `case_id` y el snapshot durable almacenado en el expediente. Si ya existen documentos no-audit, no vuelve a generarlos ni crea revisiones artificiales.
18. M24 sólo avanza a `GENERADO` después de comprobar que existen documentos vinculados.
19. Antes de cerrar `CASE_CREATED`, M35.2 vuelve a verificar intent, importe, ownership y cadena SHA/HMAC del pago sandbox.
20. Observabilidad registra IDs/estados/conteos, no relato, respuestas, recovery code ni hashes de snapshots.

## Ledger

`m35_commerce_case_links` conserva:

- `user_id`, `handoff_id`, `intake_id`, `decision_id`, `draft_id`;
- producto y nivel de servicio;
- clave de idempotencia;
- hashes de snapshot de draft y orden;
- `order_id`, `payment_intent_id`, `case_id`;
- estado y timestamps de consentimientos.

Estados:

- `ORDER_CREATED`;
- `PAYMENT_CREATED`;
- `INVALIDATED`;
- `CASE_CREATED_DOCUMENTS_PENDING`;
- `CASE_CREATED`.

El handoff conserva los estados canónicos M35.0: `FULFILLMENT_STARTED → ORDER_CREATED → CASE_CREATED`.

## Finalización transaccional en tres fases

### Fase A — vínculo económico y expediente durable

1. Verifica ownership, snapshot de orden, payment intent `succeeded`, importe, moneda y eventos firmados.
2. Verifica snapshot del draft, precio canónico y resultado jurídico vigente.
3. Crea exactamente un expediente y vincula la orden.
4. Registra `CASE_CREATED_DOCUMENTS_PENDING` antes de ejecutar materialización documental externa.

El expediente ya conserva de forma durable `answers` y `result`, por lo que el recovery no depende de recrear un caso ni de reconstruir información desde observabilidad.

### Fase B — materialización documental

1. Consulta si el mismo expediente ya tiene documentos no-audit.
2. Si ya existen, los reutiliza para continuar la reconciliación.
3. Si no existen, ejecuta `generate_case_documents` una sola vez para ese intento.
4. Un fallo devuelve estado pendiente y conserva orden, pago y expediente.

### Fase C — reconciliación M24

1. Vuelve a verificar la evidencia firmada del pago, incluso cuando la orden ya está `Completada` por estar vinculada al caso exacto.
2. Exige al menos un documento materializado.
3. Sólo entonces ejecuta `bootstrap_paid_generation` y M24 puede quedar en `GENERADO`.
4. Finalmente cambia el ledger a `CASE_CREATED`.

Esta secuencia mantiene la regla histórica de M24: un expediente no puede declararse `GENERADO` sin documentos vinculados.

## Recovery e idempotencia

Si un intento ya creó el expediente pero no terminó Fase B o C:

- el nuevo `finalize` detecta `CASE_CREATED_DOCUMENTS_PENDING`;
- recupera exclusivamente el mismo expediente del mismo owner;
- reutiliza `answers`, `result` y título del snapshot durable del caso;
- cuenta documentos existentes antes de decidir si debe generar;
- nunca inserta un segundo expediente ni una segunda orden;
- una vez `CASE_CREATED`, los siguientes `finalize` son lecturas idempotentes del vínculo terminado.

## Compatibilidad con APIs legacy

- Un producto visitado directamente, sin handoff M35, conserva el flujo legacy.
- Cuando existe continuidad M35 activa, `SelfServiceCenter` bloquea creación genérica de orden y pago legacy.
- El guard de creación genérica de `/api/cases` falla cerrado para órdenes M35.2. Por compatibilidad con el handler histórico, ese bypass se traduce como HTTP `400`; los conflictos de estado de las rutas nativas `/api/m35/commerce/*` usan `409 Conflict` cuando corresponde.
- Ninguno de esos endpoints legacy puede materializar un segundo expediente para una orden M35.2.

## QA y evidencia pre-certificación

El gate de pre-certificación **#709** sobre `d5b7a1816d41de16d28608476e9285fe1f2fb758` quedó verde antes de la limpieza final:

- 295/295 pruebas Python PASS;
- sintaxis y assets JS PASS;
- 11 productos y 473 preguntas conservados;
- M34.2, M34.3, M34.4, M35.0 y M35.1 HTTP smoke PASS;
- M35.2 HTTP smoke PASS con pago firmado verificado, bypasses legacy bloqueados, una sola orden, un solo expediente y 2 documentos materializados;
- M33.1 public-demo smoke 8/8 PASS;
- visual-docx PASS.

Esta evidencia es **pre-certificación** porque el SHA limpio posterior incorpora únicamente regresión de recovery y eliminación de archivos temporales. La certificación formal exige un nuevo run verde sobre ese SHA exacto.

## Límites actuales

- Pagos exclusivamente sandbox.
- Precios con `pricing_status = sandbox_reference_not_commercially_approved`.
- No existe representación judicial automática.
- La aprobación jurídica/QA documental sigue regida por las compuertas existentes de la Fábrica Documental.
- Certificación técnica no equivale a aprobación jurídica de contenido, autorización de pagos reales ni autorización de producción jurídica real.
