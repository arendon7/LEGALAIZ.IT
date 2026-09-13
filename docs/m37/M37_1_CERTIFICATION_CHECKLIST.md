# M37.1 — Checklist de certificación técnica

Este checklist certifica un SHA exacto. No equivale a aprobación jurídica humana, QA de contenido ni autorización de producción.

## Integridad de base

- [ ] rama M37.1 parte del SHA certificado M37.0 `999dc0468a67b6191410f14bd0c74d33f749d5c4`;
- [ ] compare contra M37.0: `behind_by=0`;
- [ ] no hay cambios accidentales fuera del alcance M37.1.

## Seguridad de archivo

- [ ] máximo 10 MB por archivo;
- [ ] tipos permitidos cerrados: PDF, PNG, JPG/JPEG, DOCX, TXT;
- [ ] firma/estructura real validada; `Content-Type` declarado no es fuente de confianza;
- [ ] DOCX con macros, embeddings, traversal o expansión insegura es rechazado;
- [ ] antimalware se ejecuta antes de persistir;
- [ ] fuera de local, escáner no disponible bloquea la carga;
- [ ] local `not_scanned_local` se informa sin presentarlo como `clean`.

## Confidencialidad e integridad

- [ ] se reutiliza `INFRA.objects` / `EncryptedObjectStore`;
- [ ] almacenamiento cifrado AES-256-GCM con AAD;
- [ ] tabla M37.1 conserva referencia `lzobj://...`, no ruta física pública;
- [ ] descarga usa `object_store.get()` y sólo entrega plaintext después de validar integridad;
- [ ] manipulación de ciphertext, metadata o hash bloquea lectura/review/download;
- [ ] modelo público no expone object refs, hashes internos, rutas, uploader/reviewer IDs ni detalle del escáner.

## Cuotas

- [ ] 10 soportes máximo por actividad;
- [ ] 30 soportes máximo por expediente;
- [ ] 100 MB máximo acumulado por expediente;
- [ ] cuotas se verifican antes de persistir un objeto nuevo.

## Frontera jurídica

- [ ] upload sólo produce `RECEIVED`;
- [ ] upload no completa tarea;
- [ ] review no completa tarea;
- [ ] upload/review no cambia M24 fuera de `EN_SEGUIMIENTO`;
- [ ] upload/review no cambia `close_readiness`;
- [ ] ninguna salida declara autenticidad verificada;
- [ ] ninguna salida declara suficiencia jurídica verificada;
- [ ] ninguna salida declara efecto jurídico verificado;
- [ ] no se calcula término legal;
- [ ] no existe cierre, escalamiento, reapertura ni envío externo automático.

## RBAC y aislamiento

- [ ] cliente propietario puede cargar/leer/descargar sus soportes;
- [ ] otro cliente recibe 404 sin revelación cross-tenant;
- [ ] cliente no puede revisar su propio soporte;
- [ ] sólo especialista asignado o administración puede registrar review;
- [ ] POST exige same-origin, sesión y CSRF;
- [ ] rate limiting real permanece activo.

## Trazabilidad

- [ ] `EVIDENCE_RECEIVED` usa la cadena hash M37 existente;
- [ ] `EVIDENCE_REVIEW_RECORDED` usa la misma cadena;
- [ ] revisiones son append-only;
- [ ] secuencia de revisión es monotónica por evidencia;
- [ ] retry idéntico de review no duplica revisión;
- [ ] mensaje completo de revisión no se duplica en el ledger M37.

## Regresión

- [ ] `python -m compileall -q .` PASS;
- [ ] suite completa PASS;
- [ ] datos demo 11 productos / >=473 preguntas PASS;
- [ ] HTTP smoke M34.2 → M37.1 PASS;
- [ ] M33.1 public demo smoke PASS;
- [ ] visual-docx SUCCESS;
- [ ] no se relajó autenticación, CSRF, rate limiting, dual approval ni release gate.

## Evidencia final

Registrar al cerrar:

- SHA certificado: pendiente;
- workflow/run: pendiente;
- total de tests: pendiente;
- resultado M37.1 HTTP smoke: pendiente;
- visual-docx: pendiente;
- limitaciones conocidas: pendiente.
