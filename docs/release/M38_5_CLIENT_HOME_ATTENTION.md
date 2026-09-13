# M38.5 — Client Home Attention

## Objetivo

M38.5 corrige la coherencia del inicio autenticado del cliente después de M38.3/M38.4. El dashboard debe ayudar a decidir **qué puede continuar el usuario** sin convertir estados operativos en conclusiones jurídicas ni exponer lenguaje interno de release.

## Problemas corregidos

1. `entregado` se trataba como `Finalizado`, aunque M37/M38.4 permiten seguimiento post-entrega.
2. El expediente destacado era simplemente el primer caso abierto recibido desde `/api/cases`.
3. La lista reciente conservaba el orden de la API, no una jerarquía explicable para continuar.
4. El conteo de abiertos utilizaba una expresión distinta de la usada por `friendlyCaseState()`.
5. El sidebar cliente mostraba lenguaje interno como `11/11 productos revalidados` / compuertas.
6. El diálogo de cuenta podía indicar que se usaran datos ficticios incluso fuera del entorno local de demo.

## Estados visibles

`friendlyCaseState()` diferencia ahora:

- `closed` → Finalizado;
- `followup` → En seguimiento;
- `delivered` → Documentos entregados;
- `ready` → Documento listo;
- `review` → En revisión;
- `document` → Preparando documentos;
- `active` → En progreso.

**Entrega no equivale a cierre.** El cierre sigue requiriendo un estado real `cerrado`/`finalizado`.

## Orden de atención

La prioridad del home es de UX, no jurídica:

1. Documento listo.
2. Documentos entregados.
3. En seguimiento.
4. En progreso.
5. Preparando documentos.
6. En revisión.
7. Finalizado.

Dentro del mismo estado se ordena por `updated_at` descendente y luego por una clave estable (`title + id`).

Este orden no calcula:

- urgencia jurídica;
- términos legales;
- probabilidad de éxito;
- severidad sustantiva;
- riesgo procesal.

El estado `review` queda por debajo de acciones directamente continuables porque normalmente depende de un tercero/revisor; esto no disminuye su importancia jurídica.

## Conteos

El resumen del cliente deriva los conteos desde `friendlyCaseState()`:

- expediente activo = cualquier estado distinto de `closed`;
- en revisión = únicamente `review`;
- documentos = colección ya autorizada que carga `preload()`.

Así se elimina la contradicción entre tarjeta y KPI.

## Seguridad

`client_home_m38_5.js`:

- no usa `api()`;
- no usa `fetch()`;
- no usa `XMLHttpRequest`;
- no usa `localStorage`, `sessionStorage` ni IndexedDB;
- no modifica `state`;
- no cambia backend, RBAC, aprobación, entrega, seguimiento ni cierre;
- sólo se aplica cuando `state.user.role === 'client'`.

## Copy de confianza

En el sidebar cliente se reemplaza la señal interna de release por:

> Contenido jurídico controlado

Y se explica que cada solución indica cuándo requiere revisión profesional.

El aviso de uso de información ficticia se conserva únicamente para el entorno local de demostración. En un entorno no-demo el diálogo de cuenta comunica controles por rol y trazabilidad sin pedir al cliente que use datos falsos.

## Fechas posteriores a la entrega

La vista heredada de seguimiento M29.2 ahora habla de **fechas relevantes y recordatorios operativos** y aclara expresamente que no sustituyen la verificación de términos legales aplicables. M37.2/M38.4 continúan siendo la implementación canónica de fechas y recordatorios.

## Fuente de verdad

M38.5 no crea un modelo de caso paralelo. Reutiliza:

- `state.cases` cargado por `/api/cases`;
- `friendlyCaseState()`;
- `nextCaseAction()`;
- `caseCard()`;
- `state.products` y `state.documents` ya autorizados.

## Criterios de aceptación

1. Entregado no se muestra como finalizado.
2. Seguimiento tiene estado y acción propios.
3. Sólo `cerrado/finalizado` cuentan como cierre.
4. El home destaca un caso mediante orden determinista.
5. Recencia sólo desempata dentro del mismo estado.
6. Los recientes usan el mismo orden.
7. KPI y tarjetas comparten la misma semántica de estado.
8. No hay scoring de urgencia jurídica.
9. No hay API ni almacenamiento nuevo.
10. No hay mutación de `state`.
11. No hay lenguaje `11/11`, `productos revalidados` ni `compuertas pendientes` en la capa cliente M38.5.
12. La advertencia de datos ficticios no aparece en la cuenta real.
13. Las fechas post-entrega siguen tratándose como referencias operativas, no términos legales.
14. La capa es idempotente frente a rerenders.
15. M38.4 y todos los gates M32–M37 continúan intactos.
