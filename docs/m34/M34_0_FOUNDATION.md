# M34.0 — Intelligent Journey Foundation

## Estado

**Iteración:** M34.0  
**Objetivo:** construir la base declarativa y trazable para el recorrido `problema humano → hechos → preguntas → reglas → recomendación`, sin sustituir la Fábrica Documental, Studio Jurídico, RBAC, revisiones inmutables ni aprobación dual.

## Decisión de arquitectura

M34 no introduce un «chatbot jurídico» que decida libremente. Introduce una capa de orquestación encima de las capacidades existentes:

```text
relato / documento
      ↓
extracción de hechos candidatos
      ↓
Legal Fact Model + procedencia
      ↓
contratos de producto
      ↓
entrevistas + reglas + fuentes existentes
      ↓
decisión controlada
      ↓
RECOMMEND | ASK_MORE | ESCALATE | OUT_OF_SCOPE
```

La IA futura podrá proponer hechos, clasificaciones y explicaciones. La decisión de producto deberá seguir siendo reconstruible con hechos, reglas, fuentes y versiones identificables.

## Baseline preservado

La iteración parte de `main` en el commit `ea0d8171db040e090e7fc9a1efdb04dc652670d8`.

Se preservan como mínimo:

- 11 productos jurídicos;
- 473 preguntas runtime o más;
- 273 reglas runtime o más;
- biblioteca jurídica avanzada de los mismos 11 productos;
- generación y preflight DOCX;
- expedientes y trazabilidad;
- revisiones inmutables y comparación;
- aprobación jurídica y QA;
- RBAC y controles de seguridad;
- Studio Jurídico.

Los números `176 preguntas / 96 reglas` permanecen como referencia histórica de una etapa anterior, pero **no son un objetivo de reducción**. El runtime actual y la biblioteca avanzada han crecido y M34 falla cerrado si esa cobertura retrocede.

## Fuentes existentes reutilizadas

M34.0 no duplica cientos de preguntas y reglas dentro de los contratos de producto. Cada contrato referencia:

- `data/interviews.json` — entrevista runtime;
- `data/rules.json` — reglas runtime;
- `app/assets/advanced-legal-library/<producto>/ENTREVISTA.json`;
- `app/assets/advanced-legal-library/<producto>/REGLAS.json`;
- `app/assets/advanced-legal-library/<producto>/FUENTES.json`;
- `app/assets/advanced-legal-library/<producto>/PAQUETE_PRODUCTO.json`.

Esto evita que M34 cree una segunda fuente jurídica divergente.

## Legal Fact Model

Un hecho M34 separa explícitamente:

1. **tipo del hecho** — namespace semántico, por ejemplo `employment.start_date`;
2. **valor** — dato declarado, extraído o derivado;
3. **procedencia**;
4. **estado de confirmación**;
5. **criticidad**;
6. **referencia a la fuente/evidencia**;
7. **confianza de extracción**, cuando exista;
8. **relevancia jurídica**, distinta de la confianza semántica.

### Procedencias permitidas

- `USER_ASSERTED`
- `DOCUMENT_EXTRACTED`
- `AI_INFERRED`
- `RULE_DERIVED`
- `USER_CONFIRMED`
- `LEGAL_REVIEWED`
- `DISPUTED`

### Regla crítica

`AI_INFERRED` no puede convertirse dentro del mismo evento en `CONFIRMED_BY_USER` o `CONFIRMED_BY_LEGAL_REVIEW`.

La confirmación debe quedar como un evento/facto trazable distinto. Esto evita transformar una inferencia generativa en «verdad del expediente» sin intervención verificable.

Los hechos extraídos de documentos tampoco se usan como decisivos hasta que sean confirmados por el usuario o por revisión jurídica cuando corresponda.

## Contratos de producto

`config/m34/product_contracts.json` crea un puente declarativo para cada producto. No redefine sus normas ni plantillas. Para cada uno registra:

- código canónico;
- nombre público;
- vertical;
- problema expresado en lenguaje humano;
- binding de entrevista runtime;
- binding de reglas runtime;
- bindings de biblioteca avanzada;
- conjunto mínimo de hechos para llegar a una recomendación;
- dominios de hechos críticos;
- riesgos que pueden bloquear o escalar;
- política inicial de revisión.

## Resultado de decisión

M34 congela únicamente cuatro salidas de orquestación:

- `RECOMMEND` — existe producto suficientemente adecuado y no hay bloqueo sin resolver;
- `ASK_MORE` — un dato puede cambiar materialmente la ruta;
- `ESCALATE` — el caso requiere revisión profesional antes de automatizar;
- `OUT_OF_SCOPE` — no existe correspondencia responsable en el catálogo actual.

No existe una salida «adivinar producto».

## No regresión

`legalai_platform/m34_intelligent_journey.py` calcula el inventario directamente desde el repositorio. La validación falla si:

- no existen exactamente 11 contratos;
- los códigos de contrato, entrevistas, reglas y biblioteca avanzada divergen;
- el runtime baja de 473 preguntas;
- el runtime baja de 273 reglas;
- falta una fuente enlazada por un contrato;
- existe un riesgo no soportado;
- existe un `fact_type` mal formado;
- las cuatro salidas de decisión divergen entre configuración y código.

## Qué NO hace M34.0

Todavía no:

- llama a un proveedor de modelos;
- extrae hechos de texto libre;
- clasifica automáticamente el problema;
- selecciona la siguiente pregunta;
- emite una recomendación real;
- cambia la landing;
- cambia el checkout;
- cambia la Fábrica Documental.

Es una decisión deliberada: primero se fija el contrato y se protege el dominio jurídico; después se conecta IA.

## Próximas subiteraciones

### M34.1 — Intake UX

- `/empezar`;
- relato libre;
- sesión invitada;
- pantalla «Esto es lo que entendimos»;
- confirmación/edición de hechos;
- resumen persistente «Tu caso»;
- adaptación móvil y accesibilidad.

### M34.2 — Fact Extraction AI

- salida JSON estructurada;
- prohibición de inventar hechos/citas/productos;
- procedencia automática;
- contradicciones;
- fallback sin IA;
- observabilidad y coste.

### M34.3 — Adaptive Question Orchestrator

- mapeo pregunta → fact target;
- `ask_when` / `skip_when`;
- information gain jurídico;
- eliminación de preguntas redundantes;
- explicación «¿Por qué preguntamos esto?».

### M34.4 — Risk & Recommendation

- candidatos;
- motor de suficiencia;
- compuertas de riesgo;
- recomendación trazable;
- explicación para usuario;
- alternativas limitadas;
- escalamiento y fuera de alcance.

## Criterio de cierre de M34.0

M34.0 se considera técnicamente integrado sólo cuando la suite completa del repositorio, incluida `tests/test_m34_0_intelligent_journey_foundation.py`, esté verde en el SHA exacto de la rama/PR. La aprobación técnica no sustituye aprobación jurídica ni QA humano de las decisiones de producto que se incorporen en M34.1–M34.4.
