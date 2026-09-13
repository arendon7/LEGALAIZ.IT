# M37.0 — Seguimiento post-entrega trazable

## Propósito

M37.0 inicia el seguimiento después de una entrega M36.3 válida. La regla de diseño es: **actividad reportada no equivale a evidencia verificada, cumplimiento jurídico ni resultado**.

## Entrada

Sólo se habilita cuando el mismo expediente tiene una entrega M36.3 `DELIVERED_IN_APP`, producto coincidente y actividades M24 compatibles con el contrato M37.0. Los casos históricos sin M36.3 no se presentan como seguimiento M37 certificado.

## Fuente de tareas

`m24_case_follow_up` continúa siendo la fuente canónica de actividades. M37.0 no crea un segundo task store. Añade:

- `m37_followup_enrollment`, para enrolamiento y snapshot de IDs;
- `m37_followup_event`, bitácora append-only hash-linked.

Las notas permanecen en M24 y no se duplican en el ledger M37.

## Contratos explícitos

`config/m37/follow_up_contracts.json` cubre los 11 productos y las 44 actividades generadas actualmente por M24. Cada `label_exact` tiene tipo explícito. Una divergencia bloquea el flujo; no existe matching difuso de etiquetas.

## Inicio y recuperación

El inicio exige la confirmación exacta `INICIAR SEGUIMIENTO` y ejecuta:

`PREPARED → M24 EN_SEGUIMIENTO → ACTIVE`.

Si el proceso cae después de que M24 compromete `EN_SEGUIMIENTO`, un retry finaliza el mismo enrolamiento sin crear otra transición.

## Control de bypass

Después del enrolamiento, el endpoint legacy M24 de tareas queda bloqueado y el singleton M24 sólo acepta cambios de actividad desde el contexto controlado M37. El cierre y escalamiento M24 también quedan reservados para una fase M37 posterior.

## Semántica de completitud

Una actividad completada por el cliente se clasifica `SELF_REPORTED`. Si la registra especialista o administración, `PROFESSIONAL_RECORDED`. En ambos casos:

- `evidence_verified=false`;
- `legal_effect_verified=false`.

## Fechas

Las fechas heredadas de M24 se muestran sólo como puntos de control operativos. M37.0 declara siempre:

- `is_legal_deadline=false`;
- `legal_deadline_verified=false`;
- `legal_deadline_calculation=false`.

No se calculan términos jurídicos en M37.0. Un término futuro requerirá fuente vigente, evento disparador, autoridad, reglas de cómputo y validación separada.

## Cierre

Completar todas las actividades puede producir `close_readiness.ready=true`, pero no cambia M24 a `CERRADO`. Se mantiene `automatic_close=false` y `automatic_escalation=false`.

## API

- `GET /api/m37/follow-up`: cola global, administración.
- `GET /api/m37/follow-up/cases/{case_id}`: detalle autorizado.
- `POST /api/m37/follow-up/cases/{case_id}/start`.
- `POST /api/m37/follow-up/cases/{case_id}/tasks/{follow_up_id}`.

Los POST exigen same-origin, sesión y CSRF. El rate limiting existente permanece intacto.

## Minimización

El modelo público omite IDs internos de actores, snapshot interno de tareas, transición M24, hashes de cadena, notas, datos de pago, rutas y hashes documentales. Otro cliente recibe 404 sin revelar la existencia del seguimiento.

## Fuera de alcance

M37.0 no verifica soportes, no calcula términos legales, no envía recordatorios externos, no reabre, no escala y no cierra expedientes automáticamente.

## Siguientes fases

- M37.1: captura y revisión de evidencia.
- M37.2: fechas verificadas y recordatorios con separación estricta entre calendario operativo y término jurídico.
- M37.3: escalamiento, reapertura y cierre controlado.
