# M37.1 — Evidence Intake & Review Boundary

## Propósito

M37.1 añade recepción y revisión controlada de soportes después de una entrega M36.3 y un seguimiento M37.0 activo. La regla de diseño es estricta:

**recibir un archivo no equivale a verificar autenticidad, valor probatorio, suficiencia jurídica, cumplimiento de término, recepción por autoridad, efecto jurídico ni cumplimiento de una actividad.**

## Prerrequisitos

M37.1 sólo opera cuando:

- existe una entrega M36.3 `DELIVERED_IN_APP`;
- M37.0 está `ACTIVE`;
- M24 está en `EN_SEGUIMIENTO` para operaciones de escritura;
- la actividad pertenece al snapshot M37.0 y coincide con el contrato del producto;
- la cadena hash M37.0 sigue íntegra.

Otro cliente recibe 404 sin revelación cross-tenant.

## Tipos admitidos

`config/m37/evidence_contracts.json` permite exclusivamente:

- PDF;
- PNG;
- JPG/JPEG;
- DOCX;
- TXT UTF-8.

No se confía en el `Content-Type` declarado por el cliente. Se valida extensión y firma/estructura real.

Para DOCX se rechazan, entre otros:

- macros `vbaProject.bin`;
- objetos embebidos;
- rutas internas con traversal;
- paquetes con más de 1.000 entradas;
- expansión total superior a 50 MB.

## Antimalware

Todo soporte se somete al `MalwareScanner` de plataforma antes de persistirse.

- En pilot/production, ausencia o fallo del escáner bloquea la carga.
- En local puede existir `not_scanned_local`; esta condición se muestra explícitamente y nunca se presenta como `clean`.

## Almacenamiento cifrado

M37.1 reutiliza `INFRA.objects` y su `EncryptedObjectStore` en vez de crear un repositorio paralelo.

El object store:

- cifra el contenido mediante AES-256-GCM;
- vincula metadatos mediante AAD;
- registra hash de plaintext y ciphertext;
- revalida ciphertext, descifrado y hash antes de entregar bytes.

La tabla M37.1 conserva una referencia `lzobj://...`; no conserva ni expone una ruta física descargable.

Las descargas pasan por `object_store.get()` y la API entrega únicamente los bytes descifrados después de validar integridad.

## Cuotas

El contrato actual limita:

- 10 MB por archivo;
- 10 soportes por actividad;
- 30 soportes por expediente;
- 100 MB totales por expediente.

Las cuotas se evalúan antes de escribir un nuevo objeto.

## Recepción

Una carga válida crea `m37_evidence_item` con estado único `RECEIVED` y registra `EVIDENCE_RECEIVED` en la misma cadena append-only M37.

La recepción:

- no cambia `m24_case_follow_up.status`;
- no modifica `close_readiness`;
- no cambia el estado M24;
- no acredita autenticidad;
- no acredita suficiencia jurídica;
- no acredita efecto jurídico.

## Revisión profesional

Sólo puede revisar:

- administración; o
- el especialista actualmente asignado al expediente.

Las disposiciones son cerradas:

- `ACKNOWLEDGED_FOR_FOLLOWUP`;
- `NEEDS_CLARIFICATION`;
- `NOT_RELEVANT_TO_TASK`.

Las revisiones son append-only y tienen `sequence` monotónica por evidencia. Un retry idéntico de la última revisión es idempotente.

`NEEDS_CLARIFICATION` y `NOT_RELEVANT_TO_TASK` exigen explicación para el cliente.

Una revisión es una clasificación operativa de intake. No es dictamen probatorio ni validación jurídica.

## Modelo público

El modelo público omite:

- `object_ref`;
- hashes internos;
- IDs de uploader/reviewer;
- motor y detalle del escaneo;
- rutas físicas;
- datos de pago;
- hechos jurídicos del expediente.

Sí informa de forma segura:

- tipo y tamaño del archivo;
- estado de escaneo resumido;
- estado de revisión;
- disposición y mensaje al cliente;
- límites de carga;
- advertencias de gobernanza.

## Auditoría

M37.1 reutiliza `m37_followup_event` para:

- `EVIDENCE_RECEIVED`;
- `EVIDENCE_REVIEW_RECORDED`.

El texto del mensaje profesional no se duplica en el evento; sólo se registra si existe mensaje. El mensaje completo permanece en la revisión M37.1.

## API

- `GET /api/m37/evidence/cases/{case_id}`
- `GET /api/m37/evidence/cases/{case_id}/items/{evidence_id}/download`
- `POST /api/m37/evidence/cases/{case_id}/tasks/{follow_up_id}/upload`
- `POST /api/m37/evidence/cases/{case_id}/items/{evidence_id}/review`

Los POST exigen same-origin, sesión y CSRF. Todas las operaciones conservan el rate limiting existente.

## Fuera de alcance

M37.1 no:

- calcula términos legales;
- verifica recepción por autoridad;
- valida firma o autenticidad externa;
- decide valor probatorio;
- completa automáticamente actividades;
- cierra expedientes;
- escala expedientes;
- reabre expedientes;
- envía comunicaciones externas.

## Siguiente fase prevista

M37.2 debe abordar fechas verificadas y recordatorios manteniendo una separación explícita entre checkpoint operativo y término jurídico. Sólo una fase posterior podrá usar evidencia valorada dentro de una compuerta humana de cierre/escalamiento.