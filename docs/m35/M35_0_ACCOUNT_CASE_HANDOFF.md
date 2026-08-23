# M35.0 — Account & Case Handoff

## Objetivo

M35.0 conecta el valor generado antes del login con el flujo autenticado existente de LegalAIZ.it.

Flujo:

`intake anónimo cifrado → recomendación M34.4 → decisión explícita de continuar → login/registro → claim one-time → draft de fulfillment`

M35.0 **no crea todavía un expediente (`case`) ni una orden de pago**. Esa separación es intencional: el triage M34 es suficiente para recomendar un producto, pero no sustituye las 473 preguntas, soportes, reglas y validaciones que pueden ser necesarias para preparar la solución definitiva.

## Arquitectura reutilizada

M35.0 no crea sistemas paralelos.

Reutiliza:

- `/api/auth/register` y `/api/auth/login`;
- sesiones, cookies, CSRF, MFA y RBAC existentes;
- `service_drafts` / `SelfServiceCenter` para fulfillment;
- `checkout_orders` y `PaymentSandboxCenter` para etapas posteriores;
- `cases` y `M24CaseJourneyCenter` para expediente posterior al fulfillment/pago;
- payload cifrado de `intelligent_intake_sessions` como fuente de contexto M34.

## Principio de valor antes de cuenta

La cuenta sólo se solicita después de que el usuario:

1. describió su situación;
2. revisó hechos;
3. contestó preguntas adaptativas;
4. superó suficiencia;
5. pidió y recibió una recomendación.

El CTA M35 es **“Continuar con esta solución”**.

## Secreto de continuidad en navegador

Para atravesar temporalmente la pantalla de login/registro sin poner el recovery code en la URL:

- se usa `sessionStorage` de la pestaña;
- nunca `localStorage`;
- nunca query string/hash params;
- nunca analytics;
- se elimina inmediatamente después de un claim exitoso;
- se puede cancelar manualmente antes del login.

Esto no cambia el modelo bearer del código: el servidor sigue almacenando únicamente su hash.

## Endpoint autenticado

`POST /api/m35/intake/claim`

Requisitos simultáneos:

- mismo origen;
- sesión autenticada;
- rol `client`;
- CSRF válido;
- rate limiting.

El endpoint no acepta selección arbitraria de producto. El producto se toma de la **recomendación primaria vigente** guardada en el payload M34.4.

## One-time ownership

La tabla `m35_intake_handoffs` tiene `intake_id UNIQUE`.

La transferencia también actualiza atómicamente `intelligent_intake_sessions`:

- `status = Transferido`;
- `stage = TRANSFERRED_TO_ACCOUNT`;
- `transferred_user_id`;
- `transferred_at`.

Después del claim, el recovery code ya no puede recuperar el intake mediante la API pública M34.

Un segundo claim de la misma cuenta es idempotente y devuelve el mismo `handoff_id` y `draft_id`.

Otra cuenta no puede apropiarse del intake ya transferido.

## Protección contra pérdida de información

El esquema histórico `service_drafts` mantiene un draft activo por `user_id + product_code`.

Por eso M35.0 adopta una política fail-closed:

- si el usuario ya tiene un draft de ese producto, **no se sobrescribe**;
- el intake continúa activo y transferible;
- se devuelve `HANDOFF_CONFLICT`.

Una futura evolución puede convertir los drafts a identidad por asunto/matter; M35.0 no elimina silenciosamente contenido previo.

## No degradación de cifrado

`service_drafts` no recibe el relato ni los valores de Legal Facts M34.

El draft recibe solamente metadata mínima de enlace:

- `intake_id`;
- `decision_id`;
- producto recomendado;
- elegibilidad cualitativa;
- requisito de revisión;
- `fulfillment_status = NOT_STARTED`;
- `triage_reuse_status = PENDING_SAFE_MAPPING`.

No se copian:

- `problem_statement`;
- fact values;
- `matched_fact_ids`;
- `matched_fact_types`;
- recommendation fingerprint;
- ranking interno.

El detalle jurídico permanece en el payload M34 cifrado, ahora vinculado al `user_id` propietario.

## Fulfillment

El claim crea un draft vacío de respuestas y dirige a:

`/nuevo/<product_code>`

Esto evita fabricar respuestas de fulfillment a partir de hechos de triage que pueden tener semántica distinta.

`triage_reuse_status = PENDING_SAFE_MAPPING` deja explícito que el futuro prefill debe contar con un mapping revisado fact-type → interview-question y reglas de confirmación, no inferencia automática.

## Relación con commerce y case

Infraestructura existente confirmada:

- `checkout_orders`;
- `PaymentSandboxCenter` con intents y eventos HMAC;
- M24 journey con estados `LISTO_PARA_PAGO` y `PAGADO`;
- UI actual: draft completo → checkout sandbox → pago → `/api/cases`.

M35.0 preserva ese orden.

No crea un `case` con respuestas M34 incompletas porque `core.create_case` aplica validación estricta del producto.

## QA requerido

M35.0 debe probar:

1. claim anónimo → 401;
2. claim sin CSRF → 403;
3. sólo rol client;
4. intake sin recomendación → fail closed;
5. primera transferencia → 201;
6. misma cuenta → idempotencia;
7. otra cuenta → 409;
8. draft existente → 409 sin overwrite ni transferencia;
9. draft nuevo con `answers = {}`;
10. `decision_id` preservado;
11. relato/fact values ausentes del draft plaintext;
12. recovery code deja de funcionar en `/recover` tras transferencia;
13. secreto browser sólo en `sessionStorage`;
14. registro público existente reutilizado;
15. JS syntax y assets;
16. smoke HTTP M34.2/M34.3/M34.4 sin regresión;
17. M33.1 sin regresión;
18. visual DOCX sin regresión.

## Fuera de alcance

M35.0 no:

- mapea hechos M34 a las 473 preguntas de fulfillment;
- crea cotización nueva;
- modifica precios;
- procesa dinero real;
- crea expediente antes de completar el formulario;
- genera documento;
- modifica aprobación dual;
- convierte pagos sandbox en pagos productivos.

## Próxima etapa

**M35.1 — Fulfillment Context Bridge + Commercial Offer**:

1. mapping seguro de hechos M34 confirmados a preguntas compatibles;
2. evitar repreguntas sólo cuando la equivalencia semántica esté validada;
3. preservar confirmación del usuario;
4. construir oferta comercial desde precios canónicos existentes;
5. enlazar handoff → draft → order sin duplicar commerce;
6. mantener PaymentSandboxCenter hasta que exista una pasarela real explícitamente aprobada.
