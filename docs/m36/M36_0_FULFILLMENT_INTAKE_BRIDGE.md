# M36.0 — Fulfillment Intake Bridge

## Objetivo

M36.0 conecta de forma exacta un expediente post-compra M35.3 ya verificado con la maquinaria profesional existente M32.5/M32.6 y el recorrido M24.6. No crea una segunda mesa jurídica ni reemplaza las revisiones, aprobaciones o controles existentes.

El problema que resuelve es operativo: antes de M36.0, la Mesa Jurídica podía incorporar documentos mediante sincronización global del portafolio. Ese mecanismo no expresaba qué compra M35 originó el trabajo profesional ni garantizaba un único intake trazable por expediente.

## Precondiciones obligatorias

La activación M36.0 exige, para un `case_id` exacto:

1. actor autenticado con rol `admin`;
2. request mutante same-origin y CSRF válido;
3. expediente fuente existente y con propietario verificable;
4. M35.3 `ACTIVE`, lo que vuelve a comprobar la cadena post-compra;
5. vínculo M35.2 `CASE_CREATED` para el mismo propietario, expediente, producto y orden;
6. conjunto documental idéntico al acreditado por M35.3;
7. todos los documentos no-audit materializados como DOCX revisables;
8. una mesa M32.5 única y determinista `DSK-<document_id>` por documento;
9. cadena de aprobación M32.5 íntegra;
10. cadena operativa M32.6 íntegra;
11. M24 en `GENERADO` o en una fase de revisión ya reconciliable.

Si cualquiera de estas condiciones falla, M36.0 falla cerrado y no presenta el expediente como ingresado a fulfillment.

## Flujo

`M35.3 ACTIVE → M36.0 intake exacto → M32.5 desk por documento → M32.6 operación inicial → M24 EN_REVISION_JURIDICA`

El primer evento M32.6 utiliza prioridad operativa `normal` y su SLA configurado por M32.6. Ese SLA es una meta interna de operación y **no constituye ni sustituye términos legales, judiciales, administrativos o contractuales**.

## Idempotencia y trazabilidad

La tabla `m36_fulfillment_intake` conserva un único registro por `case_id` y una restricción única por `order_id`. Guarda únicamente enlaces y huellas internas necesarias para detectar drift:

- expediente;
- propietario;
- producto;
- vínculo comercial;
- orden;
- fingerprint de activación;
- fingerprint del conjunto documental;
- identificadores de las mesas M32;
- actor administrativo y timestamps.

Las huellas internas, propietario, receipt, payment intent y payload jurídico no se exponen en el modelo público M36.0.

Un reintento con la misma activación y los mismos documentos devuelve el mismo intake y las mismas mesas sin crear revisiones, eventos operativos o transiciones M24 adicionales. Si cambia la activación o el snapshot documental, se bloquea con `FULFILLMENT_INTAKE_DRIFT`.

## Reutilización de capacidades existentes

M36.0 reutiliza deliberadamente:

- **M35.3** para verificación post-compra fail-closed;
- **M32.5** para revisión documental inmutable y decisiones ligadas a SHA-256;
- **M32.6** para prioridad, SLA operativo, alertas, asignación y auditoría;
- **M24.6** para el estado end-to-end del expediente.

No llama a `sync_portfolio()` ni a `bootstrap()` global. Sólo incorpora los documentos del expediente exacto solicitado.

## Límites de autoridad

M36.0 no puede:

- asignar automáticamente especialista jurídico;
- asignar automáticamente QA;
- aprobar jurídicamente un documento;
- aprobar QA;
- liberar o entregar documentos;
- declarar que un resultado jurídico es correcto;
- convertir un SLA operativo en término legal;
- omitir la aprobación dual existente.

La respuesta declara explícitamente:

- `automatic_assignment=false`;
- `automatic_legal_approval=false`;
- `automatic_qa_approval=false`;
- `automatic_release=false`;
- `dual_approval_preserved=true`.

## API M36.0

### `GET /api/m36/fulfillment`

Cola administrativa de expedientes ya ingresados a fulfillment. Resume producto, orden, estado M24, cobertura documental, estados M32 y alertas activas. No expone datos del relato, respuestas, información de pago sensible ni hashes internos.

### `GET /api/m36/fulfillment/cases/<case_id>`

Detalle administrativo del intake registrado.

### `POST /api/m36/fulfillment/cases/<case_id>/activate`

Única mutación M36.0. Requiere sesión admin, same-origin y CSRF. La primera activación responde `201`; un retry íntegro responde `200` e `idempotent=true`.

## Seguridad

- RBAC administrativo para lectura y escritura M36.0.
- Same-origin + CSRF en mutación.
- Rate limiting separado para lectura y escritura.
- IDs validados con allowlist de caracteres.
- No hay barrido multi-tenant para crear mesas.
- La observabilidad registra únicamente IDs operativos, rol, conteos, estado, idempotencia e IP hasheada.
- Las cadenas M32 inválidas bloquean o quedan visibles como alerta operativa, según el punto de lectura.
- El smoke CI usa una contraseña demo generada efímeramente en memoria del job; no existe credencial fija en el repositorio.

## Validación exigida antes de certificar

- suite completa sin regresiones;
- contratos M36.0 y pruebas adversariales;
- flujo HTTP M34 → M35 → M36 real;
- cliente bloqueado de la activación administrativa;
- admin sin CSRF bloqueado;
- admin autenticado con credencial CI efímera;
- cobertura de todas las mesas del expediente;
- idempotencia de retry;
- ausencia de asignación/aprobación/release automático;
- M24 en `EN_REVISION_JURIDICA` después del intake;
- M33.1 public demo smoke;
- visual DOCX.

## Fuera de M36.0

M36.0 no pretende cerrar toda M36. Quedan para olas posteriores la UX operativa avanzada, políticas de asignación humana, vistas especializadas por rol, gestión explícita de carga/capacidad, sincronización consistente de decisiones M32 con M24, liberación/entrega controlada al cliente y transición hacia M37 Follow-up.
