# M37.3 — Professional Disposition Gate

## Objetivo

M37.3 habilita las dos transiciones que M37.0 reservó expresamente para una fase posterior controlada: `CERRADO` y `ESCALADO`.

No es una automatización de lifecycle. Cada decisión exige actor autorizado, causal cerrada, explicación, confirmación exacta y una intención inmutable trazable.

## Semántica

### CERRADO

`CERRADO` significa únicamente que el **alcance de seguimiento contratado** fue concluido mediante una decisión expresa del especialista asignado.

No significa ni acredita:

- éxito de la pretensión jurídica;
- cumplimiento material por una autoridad o contraparte;
- autenticidad de soportes;
- suficiencia probatoria;
- vencimiento o cumplimiento de un término legal;
- producción de un efecto jurídico externo.

### ESCALADO

`ESCALADO` significa que apareció una contingencia que exige nueva intervención o revisión controlada. No requiere que el expediente esté listo para cierre: tareas pendientes, dudas sobre evidencia o una nueva circunstancia pueden ser precisamente la razón para escalar.

## Roles

### Cierre

Sólo puede ejecutarlo el **especialista asignado al expediente**.

- cliente: no;
- especialista distinto: ocultamiento por el control de acceso del expediente;
- administración: puede consultar la evaluación, pero no cerrar sin el especialista asignado.

### Escalamiento

Puede ejecutarlo:

- especialista asignado;
- administración.

El cliente no puede cambiar el lifecycle final de M37.

## Condiciones de cierre

El cierre exige simultáneamente:

1. seguimiento M37.0 `ACTIVE`;
2. M24 en `EN_SEGUIMIENTO`;
3. `close_readiness.ready=true` en M37.0;
4. todas las tareas requeridas completadas;
5. ningún soporte M37.1 `PENDING_REVIEW`;
6. ningún último review M37.1 `NEEDS_CLARIFICATION`;
7. ningún recordatorio M37.2 en `SCHEDULED` o `DUE`;
8. cadena M37 válida;
9. integridad de evidencia y estructuras M37.2 válida;
10. causal `FOLLOW_UP_SCOPE_COMPLETED`;
11. `internal_reason` profesional;
12. `client_summary` visible y neutral;
13. confirmación exacta `CERRAR SEGUIMIENTO`.

## Condiciones de escalamiento

El escalamiento exige:

- M37.0 activo y M24 en `EN_SEGUIMIENTO`;
- actor autorizado;
- causal cerrada;
- razón interna;
- resumen visible;
- confirmación exacta `ESCALAR SEGUIMIENTO`.

No exige `close_readiness` ni resolver previamente evidencia o recordatorios.

## Privacidad de la razón profesional

M37.3 separa dos textos:

- `internal_reason`: fundamento interno profesional, no público;
- `client_summary`: explicación neutral visible para el titular del expediente.

M24 recibe únicamente `client_summary` como `reason`. El ledger M37 no duplica ninguno de los dos textos; conserva sólo causal, target e identificadores causales.

## Integridad y crash recovery

La decisión usa:

- intención inmutable `m37_disposition_intent` con hash;
- eventos append-only `PREPARED` y `COMPLETED` con cadena hash;
- referencia exacta a la transición M24 atribuible al `disposition_id`;
- evento final M37 `FOLLOW_UP_CLOSED` o `FOLLOW_UP_ESCALATED`.

M24 realiza commit dentro de su transición. Por ello M37.3 implementa una saga recuperable:

1. prepara intención y evento;
2. ejecuta la transición M24 mediante el bridge privilegiado M37.3;
3. si el proceso cae después del commit M24, el retry exacto encuentra la transición atribuible;
4. finaliza `COMPLETED` sin ejecutar una segunda transición.

## Bypass legacy

M37.0 continúa bloqueando las transiciones genéricas `CERRADO` y `ESCALADO` de cualquier expediente enrolado. M37.3 no desinstala ni debilita ese guard.

El bridge privilegiado sólo acepta estos dos targets y sólo es llamado por el motor M37.3 después de validar la compuerta.

## Fuera de alcance

M37.3 no:

- decide automáticamente cerrar o escalar;
- calcula términos legales;
- verifica autenticidad;
- verifica efectos externos;
- envía correo o SMS;
- reabre un expediente escalado o cerrado;
- reemplaza una nueva revisión jurídica cuando la contingencia lo requiera.

## Certificación

La certificación técnica exige SHA exacto con:

- `compileall` PASS;
- suite completa PASS;
- no regresión de 11 productos / >=473 preguntas;
- HTTP smoke completo M34.2 → M37.3 PASS;
- M33.1 public demo PASS;
- visual-docx PASS.

La certificación técnica no sustituye aprobación jurídica humana, QA humano ni autorización de producción.
