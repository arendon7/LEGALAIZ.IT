# M35.2 — Commerce → Case Traceability Bridge

Estado: **candidato técnico en desarrollo**. No autoriza pagos reales, precios comerciales definitivos ni producción jurídica real.

## Objetivo

Cerrar el tramo `fulfillment → checkout sandbox → pago verificable → expediente` sin crear un comercio paralelo ni perder la trazabilidad de M34/M35.

M35.2 reutiliza:

- `SelfServiceCenter` para borradores y `checkout_orders`;
- `PaymentSandboxCenter` para intents idempotentes y eventos firmados;
- `M24CaseJourneyCenter` para la transición del expediente pagado;
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
13. Orden, pago y expediente son idempotentes: un reintento no crea duplicados.
14. Los endpoints legacy de orden/pago/caso no pueden saltarse una continuidad M35 activa.
15. La creación del registro del expediente y la vinculación de la orden ocurren antes de materializar documentos físicos.
16. Si falla la generación documental, el expediente queda en `CASE_CREATED_DOCUMENTS_PENDING`; no se borra el pago ni se crea un segundo caso.
17. Observabilidad registra IDs/estados/conteos, no relato, respuestas, recovery code ni hashes de snapshots.

## Ledger

`m35_commerce_case_links` conserva:

- `user_id`, `handoff_id`, `intake_id`, `decision_id`, `draft_id`;
- producto y nivel de servicio;
- clave de idempotencia;
- hashes de snapshot de draft y orden;
- `order_id`, `payment_intent_id`, `case_id`;
- estado y timestamps de consentimientos.

Estados usados inicialmente:

- `ORDER_CREATED`;
- `PAYMENT_CREATED`;
- `INVALIDATED`;
- `CASE_CREATED_DOCUMENTS_PENDING`;
- `CASE_CREATED`.

El handoff conserva los estados canónicos M35.0: `FULFILLMENT_STARTED → ORDER_CREATED → CASE_CREATED`.

## Separación de fallos

La operación `finalize` tiene dos fases:

1. verificar payment intent/eventos, snapshot, precio y resultado jurídico; crear/vincular el expediente en base de datos;
2. generar documentos y actualizar delivery.

La fase 2 nunca puede hacer desaparecer una orden pagada ni el expediente creado. Un fallo deja un estado explícito pendiente para recuperación controlada en M36.

## Límites actuales

- Pagos exclusivamente sandbox.
- Precios con `pricing_status = sandbox_reference_not_commercially_approved`.
- No existe representación judicial automática.
- La aprobación jurídica/QA documental sigue regida por las compuertas existentes de la Fábrica Documental.
- La reconciliación operativa de una materialización documental pendiente se completa en M36.
