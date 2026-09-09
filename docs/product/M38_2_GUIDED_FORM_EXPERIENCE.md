# M38.2 — Guided Form Experience Hardening

## Objetivo

Endurecer la experiencia de `/nuevo/:producto` sin reescribir el motor certificado de formularios ni modificar reglas jurídicas, respuestas, validaciones, handoff, pagos, expedientes o generación documental.

## Problemas observados

La base ya dispone de progreso, bloques, guardado, ayuda contextual, revisión previa y prefill seguro, pero la información aparece dispersa. El usuario puede completar el flujo sin entender con suficiente claridad:

- qué se guarda y dónde;
- qué dato es obligatorio u opcional;
- cuándo un dato fue reutilizado inicialmente desde el diagnóstico;
- por qué existe una pregunta que sí tiene ayuda contextual;
- qué debe verificar antes de confirmar;
- qué ocurre y qué no ocurre al continuar al análisis.

## Implementación

La capa `guided_form_m38_2` se carga después de M35.1 y M38.1 y actúa únicamente sobre el DOM ya renderizado.

### Contrato visible del formulario

Se añade un bloque que explica:

1. guardado progresivo del borrador en el navegador;
2. reutilización únicamente de datos con equivalencia directa cuando existe un handoff M35.1;
3. revisión previa obligatoria antes del análisis.

### Metadatos por pregunta

Cada pregunta visible muestra si es `Obligatorio` u `Opcional`. Cuando M35.1 ya informó que una pregunta fue prellenada inicialmente, M38.2 la identifica como `Reutilizado inicialmente · tus cambios prevalecen`.

La capa no lee el valor de la respuesta. Sólo consume `product_code` y `prefilled_question_ids` del payload no sensible ya persistido por M35.1 en `sessionStorage`.

### Ayuda contextual

Los botones de ayuda existentes dejan de mostrarse como un `?` aislado y pasan a `¿Por qué?`, conservando el mecanismo certificado de expansión y su contenido fuente.

### Revisión previa

Antes de `Confirmar datos y analizar`, se presentan cuatro controles humanos:

- personas y entidades;
- fechas y plazos;
- valores;
- hechos y soportes.

También se explicita que confirmar el formulario no radica actuaciones ni sustituye revisión profesional cuando corresponda.

## Límites de seguridad y arquitectura

M38.2:

- no importa ni llama `api`;
- no usa `fetch` ni `XMLHttpRequest`;
- no lee `localStorage`;
- no lee `.value` de controles;
- no accede al relato, respuestas, recovery codes, pagos o checkout;
- no cambia `disabled`, submit, preventDefault ni dispatch de eventos;
- no altera las validaciones ni el significado de una respuesta;
- no crea expedientes, documentos, pagos, aprobaciones o radicaciones.

## Validación requerida

- suite integral sin regresiones;
- regresiones M38.2;
- inventario 11 productos / 473 preguntas / 273 reglas;
- demo histórica 451 respuestas visibles;
- smoke M33.3 + M34.2→M37.3;
- public demo 8/8;
- QA visual documental sin regresiones.
