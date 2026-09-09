# M34.4 — Recomendación explicable y trazable

## Objetivo

M34.4 es la primera capa del journey M34 autorizada a seleccionar una solución del catálogo. Parte únicamente de un intake que haya superado M34.3 y aplica una segunda verificación de seguridad antes de emitir una recomendación.

Flujo:

`relato → hechos revisados → preguntas adaptativas → suficiencia → recomendación explicable`

M34.4 no crea expediente definitivo, no cobra, no genera documentos y no predice resultados jurídicos.

## Invariante principal

**Suficiencia de información no equivale a adecuación jurídica del producto.**

M34.3 responde: “¿tenemos información mínima para evaluar?”.

M34.4 responde: “¿alguna solución del catálogo encaja responsablemente con esos hechos y límites?”.

Un caso puede estar suficientemente descrito y aun terminar en `ESCALATE` u `OUT_OF_SCOPE`.

## Resultados permitidos

- `RECOMMEND`
- `ASK_MORE`
- `ESCALATE`
- `OUT_OF_SCOPE`

No existe un resultado de “probabilidad de éxito”.

## Recommendation Contracts

`config/m34/recommendation_contracts.json` contiene exactamente un contrato por cada uno de los 11 Product Contracts.

Cada contrato define:

- título público;
- frase de encaje;
- hechos que explican la selección;
- textos explicativos controlados;
- qué incluye;
- qué no incluye;
- política de revisión;
- checks de frontera del catálogo;
- alternativas permitidas cuando una frontera remite a otra solución.

Los contratos no sustituyen reglas jurídicas, fuentes ni entrevistas de fulfillment.

## Fronteras de catálogo

M34.4 vuelve a comprobar límites del producto aunque M34.3 haya superado suficiencia. Ejemplos cubiertos por pruebas:

- empleo público no se fuerza dentro de la liquidación laboral privada;
- prestación de servicios con subordinación expresa escala a revisión en vez de vender automáticamente un contrato de servicios;
- arrendamiento comercial no se fuerza dentro del producto de vivienda urbana;
- una fotomulta reportada como notificada no se presenta falsamente como “no notificada”; el encaje pasa a condicionado.

## Ranking interno

Cuando más de un producto es elegible, el orden interno considera:

1. elegibilidad (`PASS` > `CONDITIONAL` > `FAIL`);
2. coincidencia con routing confirmado;
3. señal temática previa;
4. cobertura de hechos explicativos.

Este ranking es exclusivamente operacional. El usuario nunca recibe `fit_score`, `signal_score`, porcentajes ni probabilidades.

## Resultado público

Una recomendación pública puede mostrar:

- `decision_id`;
- timestamp de decisión;
- producto primario;
- elegibilidad cualitativa;
- explicación de encaje;
- alcance incluido;
- alcance no incluido;
- requisito de revisión;
- advertencias;
- máximo dos alternativas;
- aviso de límites.

No se exponen:

- ids internos de hechos;
- nombres técnicos de `fact_type`;
- fingerprint de entrada;
- ranking interno;
- valores de señales;
- texto del relato dentro de telemetría de recomendación.

## Trazabilidad cifrada

Cada decisión se conserva dentro del payload cifrado del intake con:

- `decision_id` opaco;
- schema M34.4;
- fecha;
- fingerprint determinista de inputs y versiones;
- snapshot mínimo de hechos utilizables y riesgos;
- scope y productos ready;
- resultado público;
- ranking y enlaces de hechos sólo para auditoría interna.

La misma entrada y la misma versión contractual reutilizan la misma decisión mediante idempotencia.

## API

`POST /api/m34/intake/recommendation`

El recovery code se envía exclusivamente en el body. La ruta exige mismo origen y conserva rate limiting.

## UX

La recomendación no se ejecuta al entrar en `READY_FOR_RECOMMENDATION`.

El usuario debe activar expresamente **“Ver mi recomendación”**.

La pantalla diferencia:

- recomendación;
- recomendación condicionada;
- revisión profesional;
- fuera del catálogo;
- necesidad de completar diagnóstico.

Copy de frontera obligatorio:

> Adecuación al producto no significa probabilidad de ganar.

## QA M34.4

El gate técnico exige:

1. 11 Recommendation Contracts válidos;
2. 11/11 productos recomendables en fixtures limpios;
3. fronteras adversariales cubiertas;
4. riesgo no resuelto bloquea recomendación;
5. gate no-ready retorna `ASK_MORE`;
6. decisión cifrada e idempotente;
7. metadata interna ausente del payload público;
8. JS syntax PASS;
9. assets cargados después de M34.3;
10. responsive, focus-visible y reduced-motion;
11. HTTP real hasta `RECOMMEND`;
12. segunda llamada reutiliza `decision_id`;
13. smoke M34.2/M34.3 y M33.1 sin regresión;
14. visual DOCX sin regresión.

## Fuera de alcance

M34.4 todavía no:

- presenta precio;
- inicia checkout;
- exige autenticación para comprar;
- crea expediente definitivo;
- transfiere intake anónimo a una cuenta;
- abre fulfillment;
- genera documento;
- conecta pago;
- hace seguimiento posterior.

La siguiente capa natural es **M35 — Commerce & Case**, comenzando por conversión segura del intake recomendado a cuenta/expediente y preservando `decision_id` y trazabilidad.

## Criterio de cierre

CI verde acredita integración técnica del SHA exacto. No constituye aprobación jurídica sustantiva de cada Recommendation Contract ni autorización de producción real. La UX `/orientador` debe conservar revisión visual humana desktop/mobile antes del cierre comercial del journey.
