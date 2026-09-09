# M35.1 — Fulfillment Context Bridge + Commercial Offer

## Objetivo

M35.1 convierte el handoff autenticado M35.0 en continuidad visible dentro del formulario canónico sin degradar la calidad jurídica del intake ni crear un sistema comercial paralelo.

Flujo:

`M34.4 recomendación → M35.0 claim → M35.1 mapping seguro → draft fulfillment → diagnóstico completo → selección nivel → checkout existente → pago sandbox → expediente`

## Problema resuelto

M35.0 creaba correctamente `service_drafts`, pero el wizard histórico restauraba primero un borrador de `localStorage`. El usuario podía quedar autenticado y propietario del diagnóstico sin ver reutilizada ninguna información.

M35.1 agrega una capa progresiva que:

1. identifica el handoff del usuario y producto;
2. descifra el intake sólo en servidor;
3. toma únicamente Legal Facts decision-usable;
4. aplica mappings explícitos hacia preguntas runtime;
5. guarda sólo respuestas de fulfillment semánticamente compatibles;
6. fusiona esas respuestas en el navegador sin sobrescribir respuestas locales;
7. presenta los niveles/precios sandbox canónicos sin crear orden.

## Matriz de equivalencia

Fuente: `config/m35/fulfillment_fact_mappings.json`.

Cada combinación `product_code + fact_type` de `TRIAGE_REQUIRED` debe aparecer exactamente una vez con uno de estos estados:

- `EXACT`: mismo dato y misma semántica.
- `TRANSFORM_REQUIRED`: equivalencia válida sólo mediante transformación explícita.
- `NO_SAFE_MAP`: se vuelve a preguntar en fulfillment.

El registro inicial cubre 49 combinaciones producto/hecho.

`NO_SAFE_MAP` es una decisión de seguridad, no un defecto de cobertura.

Ejemplos que NO se reutilizan:

- “sé qué autoridad lleva la actuación” → nombre de la autoridad;
- “tengo un comparendo identificado” → número del comparendo;
- plazo de 3–12 meses → número exacto de meses;
- saldo aproximado de deuda → saldo total a cobrar tras abonos/intereses;
- conceptos laborales pendientes → días, períodos y cuantías de cada acreencia.

## Mappings reutilizables iniciales

Incluyen, entre otros:

- tránsito: fecha de conocimiento efectivo;
- liquidación laboral: fechas de inicio/fin y base salarial editable;
- contrato laboral: fecha de inicio, cargo y remuneración;
- servicios: objeto suficientemente detallado y honorarios;
- NDA: contexto de relación cuando existe equivalencia, categorías de información, presencia de datos personales;
- arrendamiento: canon mensual;
- hábeas data: existencia de reclamo previo sí/no;
- consumo: fecha de compra y mecanismos con equivalencia explícita (garantía, retracto, reversión);
- salud: tipo de entidad y necesidad cuando existe equivalencia explícita.

## Invariantes del motor

`FulfillmentFactBridge.validate()` falla cerrado cuando:

- falta una combinación triage;
- aparece una combinación extra;
- hay duplicados;
- se intenta mapear un `FULFILLMENT_ONLY`;
- el producto no existe;
- un reusable no tiene target/transform;
- el target no existe en las 473 preguntas;
- el target es un identificador directo prohibido;
- una transformación enumerada produce una opción inexistente.

## Provenance

Un mapping no convierte un hecho inseguro en respuesta válida.

Sólo se consideran facts para los que `fact_is_decision_usable(...)` es verdadero.

Por tanto, un `AI_INFERRED` no confirmado no puede prellenar fulfillment.

## Transformaciones

Las transformaciones son cerradas y determinísticas. No hay LLM ni inferencia libre.

Ejemplos:

- `MONEY_COP_TO_NUMBER`;
- `DATE_ISO`;
- `TEXT_MIN_3` / `TEXT_MIN_20`;
- `NDA_RELATIONSHIP_TO_RUNTIME`;
- `NDA_CATEGORIES_TO_TEXT`;
- `PERSONAL_DATA_TO_YES_NO_UNKNOWN`;
- `PRIOR_CLAIM_TO_YES_NO`;
- `CONSUMER_ISSUE_TO_REQUEST_MODE`;
- `HEALTH_ENTITY_TO_RUNTIME`;
- `HEALTH_NEED_TO_RUNTIME`.

Una transformación parcial devuelve `None` si no existe equivalencia curada. El wizard repregunta ese campo.

## Precedencia de respuestas

Regla crítica:

`server prefill < respuesta existente del usuario`

Backend:

`merged_answers = {**prefill_answers, **existing_server_answers}`

Frontend:

`mergedAnswers = { ...serverAnswers, ...localAnswers }`

El prefill nunca revierte una edición posterior del usuario.

## Endpoint

`POST /api/m35/fulfillment/prepare`

Requiere:

- mismo origen;
- sesión autenticada;
- rol `client`;
- CSRF;
- rate limit;
- handoff M35.0 perteneciente al usuario;
- mismo producto y `decision_id` transferidos.

Una visita directa a `/nuevo/<producto>` sin handoff sigue siendo válida: M35.1 falla silenciosamente hacia el wizard histórico sin bloquearlo.

## Privacidad

El servidor descifra el payload M34 únicamente para construir respuestas permitidas.

No se copian al resultado del draft:

- relato original;
- `matched_fact_ids`;
- fingerprint de recomendación;
- ids internos de hechos;
- ranking interno.

Observabilidad registra ids operativos, producto y conteos, no valores de respuestas, relato ni recovery code.

Las respuestas de fulfillment continúan usando el almacenamiento del wizard ya existente; M35.1 no introduce un segundo repositorio de respuestas.

## Oferta comercial

M35.1 reutiliza `M24ClientIntakeCenter.offer(code)`.

Los precios provienen de `data/products.json` / `PublicPortal`:

- `documento_personalizado = price_auto`;
- `solucion_revisada = price_auto + price_review`.

Se conserva expresamente:

`pricing_status = sandbox_reference_not_commercially_approved`

La preparación del contexto NO llama:

- `create_order`;
- `pay_order`;
- `create_case`.

La orden sólo nace después de que el usuario termina fulfillment, recibe diagnóstico completo, selecciona nivel de servicio y ejecuta el CTA de checkout existente.

## UX

El wizard muestra una tarjeta “Diagnóstico vinculado / No empiezas de cero”.

Si hubo reutilización, informa cuántas respuestas se prellenaron y aclara que son editables.

Si no hubo mappings seguros, lo dice de forma transparente y vuelve a preguntar los datos necesarios.

La misma tarjeta muestra los niveles de servicio y valores sandbox canónicos, sin presentarlos como oferta pública definitiva.

## QA M35.1

Gates nuevos:

1. cobertura exacta de mappings;
2. no mappings de fulfillment-only;
3. targets reales;
4. transforms fail-closed;
5. AI no confirmado excluido;
6. pruebas por productos representativos;
7. prices = campos canónicos;
8. auth/origin/CSRF;
9. local answer wins;
10. no checkout/case en prepare;
11. no relato/fingerprint/fact ids en draft result;
12. observability sin valores;
13. assets JS/CSS;
14. HTTP real: recommend → claim → prepare → edit → reprepare → edición preservada;
15. cero órdenes antes de checkout;
16. regresión M34.2/M34.3/M34.4/M35.0;
17. M33.1;
18. visual DOCX.

## Fuera de alcance

M35.1 no:

- procesa dinero real;
- autoriza precios de producción;
- crea expediente antes de checkout;
- evita preguntas cuando no hay equivalencia;
- convierte rangos aproximados en datos exactos;
- sustituye diagnóstico completo ni revisión profesional;
- modifica la Fábrica Documental o aprobación dual.

## Siguiente etapa

M35.2 debe cerrar el **Commerce → Case Traceability Bridge**: enlazar de forma inmutable `handoff_id + decision_id + draft_id + order_id + case_id`, sin cambiar el checkout sandbox existente y sin permitir que una orden pagada se adjunte a un diagnóstico distinto.
