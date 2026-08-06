# M32.7 — Centro de notificaciones, escalamiento y calendario operativo

## Objetivo

Extender la Mesa Jurídica M32.5 y la operación del portafolio M32.6 con una capa auditable para:

- bandejas personales;
- evaluación idempotente de alertas;
- escalamiento por severidad y estado del SLA;
- carga de trabajo por responsable;
- calendarios operativos configurables;
- programación por horas hábiles;
- cola externa de mensajes sin declarar entregas inexistentes.

M32.7 no sustituye la revisión jurídica, el control QA, el cómputo profesional de términos ni la constancia de entrega de comunicaciones.

## Arquitectura incremental

M32.7 se implementa en una capa nueva:

- `legalai_platform/approval_notification_center.py`
- `legalai_platform/routes/m32_7_notification_center_routes.py`
- `legalai_platform/http_handler_m32_7.py`
- `app/modules/notification_center_m32_7.js`
- `app/modules/notification_center_m32_7.css`

El handler M32.7 hereda de M32.6 y delega todas las rutas anteriores. La interfaz se integra dentro de `#/mesa-juridica`; no crea una aplicación paralela.

## Cadena M32.7

Las configuraciones y actuaciones se registran en una bitácora JSONL append-only con SHA-256 encadenado:

- `calendar.updated`
- `policy.updated`
- `calendar.deadline_applied`
- `notification.created`
- `notification.read`
- `notification.snoozed`
- `notification.acknowledged`
- `outbox.queued`
- `outbox.cancelled`
- `evaluation.completed`

Una alteración de la cadena bloquea nuevas evaluaciones y actuaciones M32.7. Esta cadena complementa las cadenas de aprobación M32.4/M32.5 y de operación M32.6.

## Calendario operativo

El calendario predeterminado utiliza:

- zona horaria `America/Bogota`;
- lunes a viernes;
- jornada de 08:00 a 17:00;
- cierres explícitos configurados por administración.

No se incorporan festivos legales automáticamente. Esto evita representar como oficial una lista desactualizada o incompleta. Cada programación conserva una copia del calendario y su SHA-256, de modo que cambios posteriores no alteran retroactivamente el cálculo registrado.

Los resultados incluyen `legal_deadline: false` y una advertencia expresa de validación profesional.

## Notificaciones y escalamiento

La evaluación toma las alertas activas M32.6 y determina destinatarios según la asignación:

- asuntos jurídicos: especialista asignado;
- asuntos QA o liberación: responsable QA;
- ausencia de responsables, cadenas inválidas o conflictos: administración;
- SLA vencido o alerta crítica: responsables y administración.

La deduplicación usa expediente, alerta, destinatario, revisión y vencimiento. Las alertas críticas pueden repetirse después del intervalo administrativo configurado.

Reconocer, leer o aplazar una notificación no resuelve la alerta subyacente. El expediente debe continuar gestionándose en M32.6 y la Mesa Jurídica.

## Cola externa

M32.7 puede crear mensajes con estado `queued` para destinatarios con correo registrado. La cola:

- no contiene el documento ni cláusulas;
- identifica únicamente producto y expediente;
- no tiene proveedor configurado;
- no registra mensajes como entregados;
- permite cancelación administrativa append-only.

`external_delivery_active`, `external_delivery_performed` y `real_external_delivery` permanecen en `false` mientras no exista integración real con evidencia de despacho.

## Carga de trabajo

El puntaje combina:

- asignaciones jurídicas;
- asignaciones QA;
- expedientes vencidos;
- expedientes en riesgo;
- alertas críticas.

Es un indicador de distribución operativa. No mide productividad individual, calidad jurídica ni desempeño laboral.

## RBAC

- Cliente: no accede al centro profesional.
- Especialista: consulta su bandeja, su carga y expedientes dentro de su alcance; puede leer, aplazar y reconocer notificaciones propias.
- Administración: consulta todas las bandejas, ejecuta evaluación, configura calendario y política, revisa la cola y aplica programación hábil.
- Los roles proceden de la sesión; no se aceptan roles enviados por el navegador.
- Las escrituras reutilizan origen permitido y CSRF.

## Evidencia automatizada

La compuerta M32.7 valida:

- sintaxis Python y JavaScript;
- compatibilidad M32.4 a M32.7;
- cobertura 11/11;
- cálculo de horas hábiles con cierre explícito y fin de semana;
- idempotencia de evaluación;
- aislamiento de bandejas;
- cola externa sin entregas;
- cadena M32.7 íntegra;
- arranque HTTP;
- respuesta 401 sin autenticación;
- conservación de evidencia por 30 días.

Toda evidencia de CI es sintética y no equivale a aprobación profesional ni entrega de correo.

## Pendientes posteriores

- proveedor real de correo o mensajería con idempotencia y evidencia de entrega;
- administración de plantillas de comunicación;
- reintentos, rebotes y supresión de destinatarios;
- calendarios oficiales versionados por autoridad y tipo de actuación;
- automatización programada del evaluador;
- preferencias de notificación por usuario;
- firma electrónica, radicación y constancias de recepción.
