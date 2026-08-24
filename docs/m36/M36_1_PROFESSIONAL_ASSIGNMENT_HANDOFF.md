# M36.1 — Professional Assignment & Handoff

## Propósito

M36.1 toma un expediente que ya superó M36.0 y organiza su entrada efectiva al trabajo profesional sin crear un segundo motor de operaciones. Reutiliza la asignación por documento de M32.6 y la evaluación de notificaciones M32.7, pero las coordina a nivel de expediente completo.

El problema concreto es de consistencia: un expediente puede contener varios documentos y M32.6 asigna responsables por cada mesa documental. Ejecutar esas asignaciones manualmente una por una puede dejar un caso parcialmente distribuido. M36.1 introduce una saga recuperable que asegura que todos los desks del mismo intake converjan a la misma pareja especialista/QA o que el estado parcial quede explícitamente registrado para recuperación.

## Precondiciones

Para asignar un expediente se exige:

1. sesión autenticada con rol `admin`;
2. same-origin y CSRF en la mutación;
3. intake M36.0 existente e íntegro;
4. M24 en una fase compatible con revisión profesional;
5. cobertura completa y única de desks respecto de los documentos del intake;
6. cadenas M32.5 y M32.6 íntegras en cada desk;
7. especialista activo con rol `specialist`;
8. QA activo con rol `qa` o `admin` según la política ya existente M32.6;
9. especialista y QA distintos;
10. ausencia de responsables incompatibles ya registrados en cualquiera de los desks.

## Selección humana

M36.1 **no contiene matching automático**. Administración elige de forma explícita `specialist_id` y `qa_id` desde el directorio activo M32.6.

La especialidad se expone como dato orientador para la decisión humana. No se usa como conclusión automática de competencia profesional ni como garantía de idoneidad para un asunto concreto.

## Saga recuperable

La coordinación utiliza `m36_professional_assignment` con un único registro por intake/caso.

Estados:

- `PENDING`: solicitud registrada antes de aplicar desks;
- `PARTIAL`: al menos una mesa fue asignada, pero falta cobertura total;
- `ASSIGNED`: todos los desks tienen la pareja profesional correcta, pero falta completar la evaluación de handoff M32.7;
- `COMPLETE`: todos los desks están asignados y M32.7 fue evaluado para cada uno.

Se guardan dos checkpoints explícitos:

- `completed_desk_ids_json`;
- `notified_desk_ids_json`.

Esta estructura reconoce que la operación no puede ser una única transacción SQL: M32.6 y M32.7 conservan bitácoras append-only en archivos además de persistencia relacional. Ante una falla intermedia, M36.1 no revierte artificialmente una bitácora inmutable; conserva el progreso y un retry continúa únicamente los pasos faltantes.

## Idempotencia

Un retry sobre `COMPLETE`:

- verifica nuevamente intake, desks, cadenas y pareja profesional;
- exige cobertura completa del ledger;
- retorna el mismo `assignment_id`;
- no vuelve a llamar `update_assignment`;
- no vuelve a evaluar M32.7;
- no cambia `updated_at`;
- no registra otro evento `assignment_completed`.

Una solicitud posterior con otra pareja profesional no se interpreta como retry: queda bloqueada. La reasignación futura deberá ser una operación separada, explícita y auditable.

## Handoff M32.7

Después de completar la asignación en M32.6, M36.1 ejecuta la evaluación M32.7 para cada desk. Con el estado `legal_pending`, las alertas aplicables pueden dirigirse al especialista ya seleccionado.

La evaluación M32.7:

- genera notificaciones in-app según sus reglas existentes;
- puede suprimir duplicados de forma idempotente;
- no acredita que el destinatario leyó el mensaje;
- no acredita envío externo;
- no equivale a entrega del documento;
- no equivale a revisión o aprobación jurídica.

## API

### `GET /api/m36/assignments/professionals`

Directorio administrativo de especialistas y perfiles QA activos. Expone especialidad únicamente como ayuda de selección. Declara `automatic_matching=false`.

### `GET /api/m36/assignments`

Cola administrativa de sagas de asignación y sus estados de cobertura.

### `GET /api/m36/assignments/cases/<case_id>`

Detalle administrativo de la asignación de un expediente.

### `POST /api/m36/assignments/cases/<case_id>/assign`

Payload:

```json
{
  "specialist_id": "USR-LEGAL",
  "qa_id": "USR-QA"
}
```

Es la única mutación M36.1. Requiere admin, same-origin y CSRF.

## Gobernanza preservada

M36.1 declara expresamente:

- `manual_selection_required=true`;
- `automatic_matching=false`;
- `specialty_is_advisory=true`;
- `automatic_legal_approval=false`;
- `automatic_qa_approval=false`;
- `automatic_release=false`;
- `dual_approval_preserved=true`;
- `assignment_completion_is_not_review_completion=true`;
- `notification_evaluation_is_not_delivery=true`.

M24 permanece en la fase de revisión correspondiente; la mera asignación no lo avanza a `APROBADO_JURIDICAMENTE`, `EN_QA`, `APROBADO_QA` ni `ENTREGADO`.

## Seguridad y privacidad

- lectura y escritura M36.1 son administrativas;
- POST exige origin + CSRF;
- rate limits separados para lectura/escritura;
- no se registran relato, respuestas, receipt, payment intent ni fingerprints M35 en observabilidad M36.1;
- los IDs de profesionales son datos operativos necesarios para RBAC y trazabilidad;
- no se sobrescribe una asignación incompatible;
- una cadena M32 alterada bloquea el preflight;
- una saga incompleta nunca se presenta como `COMPLETE`.

## Validación mínima de certificación

- suite completa sin regresiones;
- fallo en segundo desk → `PARTIAL` y retry recuperable;
- fallo M32.7 → `ASSIGNED` y retry sólo de notificación faltante;
- retry `COMPLETE` estrictamente read-only;
- cambio de pareja → conflicto, no reasignación silenciosa;
- separación especialista/QA obligatoria;
- cliente bloqueado del directorio y asignación;
- admin sin CSRF bloqueado;
- HTTP real M34 → M35 → M36.0 → M36.1;
- M32.6 muestra la misma pareja en todos los desks;
- workflow documental continúa `legal_pending` después de asignar;
- M32.7 contiene handoff dirigido al especialista;
- M33.1 y visual-docx permanecen verdes.

## Fuera de M36.1

No se implementan todavía:

- reasignación profesional;
- balanceo automático de carga;
- algoritmo de matching;
- aceptación/acknowledgement explícito del profesional asignado;
- sincronización de decisiones M32 con hitos M24 posteriores;
- liberación y entrega final al cliente;
- seguimiento M37.
