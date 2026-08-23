# M34.2 — Extracción estructurada y confirmación trazable de hechos

## Objetivo

M34.2 convierte un relato ya guardado por M34.1 en **hechos candidatos estructurados** que el usuario puede revisar antes de que cualquier regla o recomendación los utilice.

La secuencia queda así:

`relato cifrado → estructuración automática → hechos candidatos → revisión humana → hechos confirmados → siguiente pregunta/regla`

M34.2 no decide todavía qué producto debe comprar el usuario y no emite un concepto jurídico.

## Principio de seguridad jurídica

> La máquina propone estructura. La persona confirma hechos. El motor jurídico decide con reglas trazables.

Un candidato automático nunca cambia silenciosamente de origen.

Si la máquina produce:

```text
fact_ai_x
provenance = AI_INFERRED
confirmation_status = UNCONFIRMED
```

y el usuario confirma que es correcto, M34.2 conserva ese candidato y crea otro hecho:

```text
fact_user_y
provenance = USER_CONFIRMED
confirmation_status = CONFIRMED_BY_USER
source_reference = fact_ai_x
```

El candidato original queda `SUPERSEDED`.

Si el usuario rechaza el candidato, éste permanece `AI_INFERRED` y pasa a `DISPUTED`.

De esta manera la auditoría puede distinguir siempre:

1. qué detectó una máquina;
2. qué afirmó o confirmó el usuario;
3. qué dato fue controvertido;
4. cuál fue el origen de cada hecho posterior.

## Arquitectura de proveedor

M34.2 no acopla LegalAIZ.it a un modelo específico.

Se introduce el contrato `FactExtractionProvider`:

- `provider_id`;
- `provider_mode`;
- `ai_enabled`;
- `extract(problem_statement, allowed_fact_types)`.

Todo proveedor, local o externo, pasa después por `FactExtractionService`.

El servicio es la frontera de seguridad y no confía en la salida del proveedor.

### Proveedor actual

La primera implementación es:

`m34.local.conservative.v1`

Modo:

`LOCAL_CONSERVATIVE`

`ai_enabled = false`

Es un extractor lexical/sintáctico conservador para demostración, QA, fallback y desarrollo del journey.

No se presenta al usuario como un modelo de IA.

Sólo propone un hecho cuando el relato contiene una señal suficientemente explícita. No intenta completar hechos faltantes mediante conocimiento general ni inferencias jurídicas amplias.

La conexión posterior a un modelo externo debe implementar exactamente el mismo contrato y superar los mismos gates antes de sustituir o complementar este proveedor.

## Frontera estricta de extracción

`FactExtractionService` sólo admite tipos de hecho definidos en `minimum_recommendation_facts` de los 11 Product Contracts.

Un proveedor no puede introducir arbitrariamente:

- nuevos tipos de hecho;
- conclusiones jurídicas;
- productos inexistentes;
- riesgos desconocidos;
- hechos ya marcados como confirmados;
- niveles de confianza fuera de 0–1.

La salida se normaliza siempre a:

```json
{
  "provenance": "AI_INFERRED",
  "confirmation_status": "UNCONFIRMED"
}
```

incluso si un proveedor mal configurado intenta afirmar lo contrario.

## Productos candidatos

El extractor puede identificar hasta tres **señales temáticas** de producto.

Internamente se representan como:

```json
{
  "product_code": "CO-LA-001",
  "signal_score": 0.65,
  "reason_codes": ["liquidacion", "me_despidieron"],
  "status": "TOPIC_SIGNAL_ONLY"
}
```

Estas señales:

- no son una recomendación;
- no se muestran como ranking jurídico;
- no habilitan compra;
- no reemplazan los requisitos mínimos del Product Contract;
- no se vuelven decisión hasta que M34.3/M34.4 apliquen hechos confirmados, preguntas faltantes, riesgos y reglas.

La UX M34.2 deliberadamente no renderiza `signal_score`.

## Señales de riesgo

El proveedor puede proponer señales de riesgo conocidas por M34.0.

Toda señal se guarda como:

`UNCONFIRMED_SIGNAL`.

Ejemplos iniciales:

- término o fecha aparentemente próxima;
- proceso judicial activo;
- posible asunto penal;
- participación de menor o persona vulnerable;
- datos personales sensibles.

La interfaz las presenta como algo que **conviene revisar**, nunca como conclusión definitiva.

## Estados del journey

### `PROBLEM_SUBMITTED`

El relato está cifrado y todavía no se ha estructurado.

UX:

**Organicemos lo que ya nos contaste.**

### `FACTS_PENDING_CONFIRMATION`

Existen uno o más candidatos automáticos pendientes.

UX:

**Esto es lo que entendimos de tu relato.**

Por cada hecho:

- Sí, es correcto;
- Quiero corregirlo;
- No corresponde.

### `FACTS_NOT_FOUND`

El proveedor conservador no encontró hechos suficientemente explícitos.

No fuerza inferencias.

La siguiente acción es preguntar más o ampliar el relato.

### `FACTS_REVIEWED`

Todos los candidatos fueron confirmados, corregidos o rechazados.

La plataforma muestra por separado los hechos confirmados y el número de candidatos controvertidos.

Este estado todavía no equivale a diagnóstico ni recomendación.

## API

M34.1 mantiene:

- `POST /api/m34/intake/start`
- `POST /api/m34/intake/recover`
- `POST /api/m34/intake/problem`

M34.2 añade:

### `POST /api/m34/intake/analyze`

Entrada:

```json
{
  "recovery_code": "XXXXXX-XXXXXX-XXXXXX-XXXXXX"
}
```

El servidor recupera el relato cifrado, ejecuta el proveedor, valida la salida y vuelve a cifrar el nuevo estado.

### `POST /api/m34/intake/facts/decide`

Entrada conceptual:

```json
{
  "recovery_code": "...",
  "decisions": [
    {"fact_id":"fact_ai_...","action":"CONFIRM"},
    {"fact_id":"fact_ai_...","action":"EDIT","value":"dato corregido"},
    {"fact_id":"fact_ai_...","action":"DISPUTE"}
  ]
}
```

Las decisiones admitidas son exclusivamente:

- `CONFIRM`;
- `EDIT`;
- `DISPUTE`.

## Invalidación por cambio de relato

Editar el relato original invalida:

- hechos candidatos;
- hechos confirmados derivados de esa extracción;
- señales de riesgo;
- contradicciones;
- productos candidatos;
- proveedor y versión de extracción;
- cierre de revisión.

El estado vuelve a `PROBLEM_SUBMITTED`.

Esto evita que datos derivados de una versión anterior del relato sobrevivan a una corrección material del usuario.

Después de que exista al menos un hecho confirmado, M34.2 tampoco permite simplemente reejecutar la extracción sobre el mismo relato. El usuario debe editar/reconfirmar el origen para evitar que una nueva ejecución reemplace decisiones humanas anteriores.

## Privacidad y observabilidad

Los endpoints siguen siendo anónimos y same-origin.

El recovery code:

- funciona como secreto bearer de alcance limitado;
- nunca se envía en URL;
- permanece únicamente en el cuerpo POST;
- continúa almacenado sólo como hash en servidor.

Observabilidad puede registrar:

- `intake_id`;
- etapa;
- proveedor y modo;
- si el proveedor usa IA;
- número de hechos;
- número de señales temáticas;
- número de señales de riesgo;
- IP hasheada.

Observabilidad no registra:

- relato;
- recovery code;
- valores de hechos;
- motivos textuales del usuario;
- contenido documental.

## UX

M34.2 se monta como progressive enhancement sobre la vista M34.1.

No reescribe `conversion_m29_5.js`.

Esto permite:

- conservar el intake certificado;
- aislar regresiones;
- retirar la capa M34.2 sin destruir M34.1;
- iterar la IA independientemente de la captura inicial.

La interfaz mantiene tres límites visibles:

1. **detección automática no significa hecho confirmado**;
2. **hecho confirmado no significa conclusión jurídica**;
3. **señal temática de producto no significa recomendación**.

## Contratos formales

- Legal Fact Model: `config/m34/legal_fact.schema.json`
- Resultado de extracción: `config/m34/fact_extraction_result.schema.json`
- Product Contracts: `config/m34/product_contracts.json`

## QA M34.2

La suite específica comprueba:

- tipos de hecho no permitidos fallan cerrado;
- riesgos desconocidos fallan cerrado;
- un proveedor no puede autopromover su salida a confirmada;
- todo candidato automático es no decisivo;
- producto candidato nunca se presenta como recomendación;
- confirmación crea un nuevo hecho humano;
- corrección preserva el candidato original;
- controversia vuelve el candidato no utilizable;
- revisión parcial continúa pendiente;
- revisión completa cierra `FACTS_REVIEWED`;
- editar el relato invalida derivados;
- reanalizar después de confirmación exige cambiar primero el relato;
- recovery code permanece en POST;
- valores no llegan a observabilidad;
- JS M34.2 supera validación sintáctica;
- el servidor real completa start → analyze → decide → recover.

## Lo que M34.2 todavía NO hace

- no conecta todavía un LLM externo;
- no analiza documentos adjuntos;
- no determina suficiencia jurídica completa;
- no selecciona la siguiente pregunta óptima;
- no recomienda un producto;
- no calcula precio;
- no abre checkout;
- no crea expediente definitivo;
- no genera documentos.

## Próxima etapa

La siguiente iteración debe concentrarse en **M34.3 — Adaptive Question Engine + Sufficiency Gate**.

Su misión será comparar los hechos confirmados contra los requisitos de los Product Contracts y responder, de manera trazable:

1. qué hechos ya conocemos;
2. cuáles faltan;
3. cuál es la pregunta con mayor valor informativo;
4. qué contradicciones o riesgos bloquean avanzar;
5. cuándo existe información suficiente para pasar al recomendador.

Sólo después de ese gate debe habilitarse M34.4 — recomendación explicable de producto.
