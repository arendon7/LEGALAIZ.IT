# M34.3 — Adaptive Question Engine + Sufficiency Gate

## Objetivo

M34.3 responde una sola pregunta de producto:

> ¿Tenemos información suficiente y jurídicamente segura para que la siguiente capa pueda evaluar una recomendación?

No recomienda todavía un producto.

La secuencia M34 queda:

`relato → hechos candidatos → revisión humana → preguntas adaptativas → gate de suficiencia → M34.4 recomendación explicable`

## Principio

**Preguntar sólo lo que falta y sólo cuando cambia una decisión.**

Las 473 preguntas de las entrevistas vigentes permanecen intactas para fulfillment. M34.3 no intenta ejecutarlas antes de demostrar valor al usuario.

## Question Contracts

`config/m34/question_contracts.json` cubre los requisitos mínimos de los 11 Product Contracts mediante un contrato semántico explícito.

Cada requisito se clasifica como:

- `TRIAGE_REQUIRED`: puede bloquear la suficiencia previa a recomendación;
- `FULFILLMENT_ONLY`: se difiere hasta preparar expediente/documento y no bloquea la orientación inicial.

La separación evita pedir prematuramente nombre completo, identificación, correo, teléfono o dirección exacta únicamente para mostrar una recomendación.

## Routing Contracts

`config/m34/routing_contracts.json` contiene routing neutral.

El routing:

- no crea Legal Facts;
- no se registra como recomendación;
- no muestra scores;
- no afirma una conclusión jurídica;
- únicamente reduce el conjunto de productos que merece preguntas posteriores.

Si no hay señal temática, se pregunta por el tema general.

Si una categoría contiene dos rutas canónicas, puede existir una pregunta de desambiguación adicional.

Si el usuario selecciona `otro`, M34.3 devuelve `OUT_OF_SCOPE` en vez de forzar un producto.

## Orden de decisión

El engine aplica, en orden:

1. extracción pendiente → `ANALYZE_FACTS`;
2. hechos automáticos pendientes → `CONFIRM_FACTS`;
3. señal de riesgo no confirmada → `CONFIRM_RISK`;
4. contradicción no resuelta → `ESCALATE`;
5. routing insuficiente → `ROUTE_TOPIC`;
6. riesgo confirmado/indeterminado que bloquea el Product Contract → `ESCALATE`;
7. requisitos de triage completos para al menos un producto → `READY_FOR_RECOMMENDATION`;
8. falta un hecho preguntable → `ASK_QUESTION`;
9. no queda pregunta responsable y sigue faltando información → `ESCALATE`.

No existe una salida `RECOMMEND` en M34.3.

## Priorización de preguntas

Las preguntas candidatas se ordenan determinísticamente utilizando:

- `information_value`;
- criticidad;
- cobertura dentro del conjunto de productos;
- fuerza de la señal temática ya disponible.

No se usa un LLM para escoger la siguiente pregunta.

Una pregunta cuyo `fact_type` ya tiene un hecho utilizable no vuelve a hacerse.

Una respuesta directa crea:

- `provenance = USER_ASSERTED`;
- `source_reference = m34-question:<question_contract_id>`.

No se reetiqueta como IA ni necesita una segunda confirmación artificial para existir como afirmación del usuario.

## Respuestas inciertas

Valores explícitos equivalentes a `NO_SE` / `UNCERTAIN` no cuentan como suficientes para cerrar el gate.

La incertidumbre no se transforma en un dato inventado.

Si tras las preguntas disponibles sigue faltando un hecho crítico, la salida segura es `ESCALATE` por `INSUFFICIENT_INFORMATION`.

## Riesgos

Una señal de M34.2 se mantiene `UNCONFIRMED_SIGNAL` hasta revisión.

M34.3 permite:

- `confirm` → `CONFIRMED_BY_USER`;
- `dismiss` → `DISMISSED_BY_USER`;
- `uncertain` → `USER_UNCERTAIN`.

La señal no se convierte en Legal Fact.

La decisión de bloqueo se cruza después con `blocking_risks` del Product Contract. `CRIMINAL_MATTER` es escalamiento duro fuera de la automatización ordinaria.

## Estado cifrado e invalidación

El estado nuevo vive dentro de `payload["m34_3"]`, que continúa cifrado por la infraestructura existente.

Incluye:

- hash del relato de origen;
- routing;
- historial de ids de preguntas;
- snapshot de suficiencia.

El estado M34.3 se invalida automáticamente si el hash del relato cambia. Así una edición realizada por capas anteriores no deja preguntas o routing obsoletos activos.

## API

Por seguridad, el recovery code nunca viaja en URL.

M34.3 añade:

- `POST /api/m34/intake/next-step`
- `POST /api/m34/intake/answer`

`next-step` puede devolver:

- `ANALYZE_FACTS`
- `CONFIRM_FACTS`
- `CONFIRM_RISK`
- `ROUTE_TOPIC`
- `ASK_QUESTION`
- `READY_FOR_RECOMMENDATION`
- `ESCALATE`
- `OUT_OF_SCOPE`

## UX

La interfaz presenta una pregunta a la vez.

No muestra:

- códigos internos de producto;
- `signal_score`;
- `fit_score`;
- porcentajes de probabilidad de éxito;
- conclusiones de validez jurídica.

En cambio muestra:

- pregunta clara;
- opciones o campo adecuado;
- “¿Por qué preguntamos esto?”;
- progreso semántico en datos faltantes;
- límite de automatización;
- estado de suficiencia o escalamiento.

## Seguridad

- same-origin heredado del handler M34;
- recovery bearer sólo en cuerpo POST;
- rate limits diferenciados;
- pregunta recibida debe coincidir con la pregunta que el servidor considera vigente;
- respuestas se validan por tipo y opciones del Question Contract;
- observabilidad no recibe relato, recovery code ni valor de respuesta;
- longitud y rangos de entradas acotados;
- hechos existentes no pueden reescribirse mediante una pregunta posterior.

## QA

M34.3 debe probar:

- cobertura de contratos para 11/11 productos;
- 55 tipos de hecho mínimos cubiertos;
- 14 hechos fulfillment-only diferidos;
- routing de los 11 productos;
- no repetición de hechos conocidos;
- riesgo antes de pregunta ordinaria;
- escalamiento ante riesgo bloqueante;
- incertidumbre no contada como suficiencia;
- `USER_ASSERTED` y procedencia de pregunta;
- rechazo de `question_id` obsoleto o inyectado;
- invalidación por cambio de relato;
- JS, responsive, foco y reduced motion;
- HTTP real hasta `READY_FOR_RECOMMENDATION`;
- regresión M34.2/M33.1/documentos.

## Fuera de alcance

M34.3 no:

- recomienda producto;
- muestra precio;
- abre checkout;
- crea expediente definitivo;
- genera documento;
- analiza adjuntos;
- sustituye las entrevistas de fulfillment.

## Próxima etapa

M34.4 debe tomar únicamente hechos utilizables, scope, riesgos ya revisados y Product Contracts para producir una salida explicable:

`RECOMMEND | ASK_MORE | ESCALATE | OUT_OF_SCOPE`

con una solución primaria y, cuando tenga sentido, máximo dos alternativas; nunca una predicción de éxito del caso.
