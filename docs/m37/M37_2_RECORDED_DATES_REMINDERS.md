# M37.2 — Recorded Dates & Reminder Boundary

## Objetivo

M37.2 añade una capa controlada para registrar fechas relevantes reportadas durante el seguimiento post-entrega y programar recordatorios operativos in-app. No calcula términos legales, no determina vencimientos normativos y no convierte una fecha reportada, una fecha registrada por un profesional o un soporte M37.1 en una conclusión jurídica.

## Regla semántica central

M37.2 mantiene separadas cuatro cosas que jurídicamente no deben confundirse:

1. **Fecha registrada:** una fecha reportada por el cliente o registrada por un profesional.
2. **Soporte relacionado:** un archivo M37.1 íntegro y vinculado a la misma actividad.
3. **Recordatorio operativo:** una referencia temporal para gestión del expediente.
4. **Término legal:** una conclusión jurídica que exige análisis normativo, hechos suficientes y, cuando corresponda, revisión profesional.

Por tanto:

- registrar una fecha **no verifica** que el hecho haya ocurrido;
- enlazar evidencia M37.1 **no verifica** la fecha contenida en el soporte;
- que un especialista registre una fecha **no verifica** un término legal;
- un recordatorio `DUE` significa sólo que llegó la fecha operativa programada;
- `due_at` de M24 continúa siendo `OPERATIONAL_CHECKPOINT`, no término legal;
- M37.2 no usa calendario de días hábiles ni reglas normativas para calcular vencimientos.

## Procedencia de fechas

### `USER_ASSERTED`

La fecha fue aportada por el cliente. El sistema conserva esta procedencia y no la presenta como verificada.

### `PROFESSIONAL_RECORDED`

La fecha fue registrada por un especialista o administrador autorizado. Esto mejora la trazabilidad de quién la incorporó, pero no la convierte automáticamente en fecha jurídicamente acreditada ni en término legal.

## Tipos de evento

M37.2 admite únicamente:

- `ACTION_PERFORMED`
- `AUTHORITY_RECEIPT_REPORTED`
- `NOTICE_RECEIVED`
- `RESPONSE_RECEIVED`
- `OTHER_RELEVANT_EVENT`

La palabra `REPORTED` es deliberada cuando existe riesgo de confundir el registro con una constatación externa.

## Correcciones append-only

Una fecha existente nunca se sobrescribe. Una corrección crea un nuevo `date_record_id` con `supersedes_date_record_id`.

Controles:

- hash del registro completo;
- una fecha sólo puede ser supersedida una vez;
- no se permiten bifurcaciones silenciosas;
- un retry exacto de la misma corrección reutiliza el registro existente;
- un retry exacto se resuelve antes de cuotas.

## Evidencia M37.1

Un registro puede referenciar un `evidence_id` únicamente cuando:

- pertenece al mismo expediente;
- pertenece a la misma tarea M37;
- el objeto cifrado conserva integridad verificable por M37.1.

Esto acredita integridad técnica del objeto almacenado, no autenticidad del documento, verdad del contenido, recepción efectiva por autoridad, suficiencia probatoria ni efecto jurídico.

## Recordatorios in-app

Un recordatorio contiene:

- expediente;
- tarea;
- fecha operativa `scheduled_for`;
- opcionalmente una fecha M37.2 vigente como referencia;
- creador y rol internos;
- hash inmutable.

Estados públicos:

- `SCHEDULED`
- `DUE`
- `ACKNOWLEDGED`
- `CANCELLED`

`DUE` se deriva en lectura comparando `scheduled_for` con la fecha local `America/Bogota`. No se persiste un evento automático por el simple paso del tiempo.

## Eventos de recordatorio

La creación genera `SCHEDULED`. Las únicas acciones posteriores son:

- `ACKNOWLEDGED`
- `CANCELLED`

La secuencia es append-only y hash-linked. Un recordatorio reconocido o cancelado queda terminal.

## Idempotencia

Los retries exactos se resuelven antes de cuotas:

- misma fecha / tarea / evento / evidencia / corrección / actor → mismo `date_record_id`;
- mismo recordatorio activo / tarea / fecha / fuente / creador → mismo `reminder_id`;
- misma acción terminal repetida → lectura idempotente sin nuevo evento.

## Seguridad y minimización

M37.2 reutiliza:

- control de acceso del expediente M37.0;
- aislamiento cross-tenant con ocultamiento 404;
- same-origin;
- sesión autenticada;
- CSRF para escrituras;
- rate limiting;
- integridad de evidencia M37.1;
- cadena M37 append-only.

El ledger M37 recibe sólo metadatos causales. No duplica el valor concreto de las fechas ni `scheduled_for`.

La respuesta pública no expone:

- `record_hash`;
- `reminder_hash`;
- `event_hash`;
- `previous_hash`;
- identificadores internos de actor;
- datos de pago;
- narrativa jurídica o respuestas del intake.

## Lo que M37.2 no hace

M37.2 no:

- calcula términos legales;
- calcula días hábiles;
- consulta calendarios judiciales o administrativos;
- determina prescripción o caducidad;
- declara vencimiento normativo;
- verifica autenticidad documental;
- verifica que una autoridad haya recibido una actuación;
- completa tareas M24 por fecha o recordatorio;
- cierra el expediente;
- escala automáticamente;
- envía correo, SMS o comunicaciones externas.

## Criterio de salida

M37.2 sólo puede considerarse técnicamente certificado cuando el SHA exacto supera:

- `compileall`;
- suite completa;
- pruebas M37.2 de dominio, integridad e idempotencia;
- smoke HTTP end-to-end hasta M37.2;
- smoke M33.1;
- visual-docx;
- verificación de no regresión de 11 productos y al menos 473 preguntas.

La certificación técnica no reemplaza aprobación jurídica humana, QA humano de contenido ni autorización de producción.
