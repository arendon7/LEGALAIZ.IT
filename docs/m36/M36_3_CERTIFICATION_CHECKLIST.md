# M36.3 — Checklist de certificación técnica

Estado inicial: **pendiente**. Este archivo dispara el gate del PR sobre `main`; sólo se actualizará con evidencia verificable de un SHA exacto.

## Integridad funcional

- [ ] Sintaxis Python completa PASS.
- [ ] Suite `unittest` completa PASS, sin reducir pruebas existentes.
- [ ] Se preservan 11 productos y el floor de 473 preguntas.
- [ ] M33.1 public demo PASS.
- [ ] visual-docx PASS y artifact disponible.

## Compuerta de entrega

- [ ] M36.3 exige M36.0 + M36.1 + M36.2 íntegros.
- [ ] M24 debe estar exactamente en `APROBADO_QA`.
- [ ] `delivery_gate_ready=true` y liberación completa son obligatorios.
- [ ] El paquete se construye únicamente desde copias `released_path()` M32.5.
- [ ] Todos los SHA-256 y `release_record_hash` se validan.
- [ ] Cobertura documental case-level completa; no se permite éxito parcial.
- [ ] Confirmación exacta `ENTREGAR SOLUCIÓN` requerida.

## Saga e idempotencia

- [ ] `PREPARED → ENTREGADO → DELIVERED_IN_APP` probado.
- [ ] Caída después del commit M24 es recuperable.
- [ ] Retry no crea segundo paquete.
- [ ] Retry no crea segunda transición `ENTREGADO`.
- [ ] Retry conserva actor y timestamp de la transición M24 original.
- [ ] Un `PREPARED` revalida M36.2 antes de continuar.

## Anti-bypass y RBAC

- [ ] Endpoint M24 genérico bloquea `ENTREGADO` para casos M36.
- [ ] Guarda interna del singleton M24 bloquea llamadas directas sin `PREPARED` exacto.
- [ ] Sólo administración ejecuta entrega.
- [ ] Titular puede leer/solicitar descarga de su entrega.
- [ ] Otro cliente no descubre existencia de la entrega.
- [ ] Especialista no obtiene acceso por la superficie de entrega.
- [ ] POST exige same-origin, sesión y CSRF.

## Semántica probatoria

- [ ] `DELIVERED_IN_APP` significa únicamente puesta a disposición en expediente autenticado.
- [ ] No se afirma correo enviado, descarga, lectura o recepción externa.
- [ ] Acceso al archivo se registra como `DOWNLOAD_REQUESTED`.
- [ ] `DOWNLOAD_REQUESTED` no se presenta como constancia de recibo.

## Seguridad e integridad adversarial

- [ ] Manipulación del ZIP bloquea lectura, descarga y retry.
- [ ] Drift de una liberación o `release_record_hash` bloquea entrega.
- [ ] Manifiesto exige cobertura exacta y nombres no duplicados.
- [ ] Modelo público no expone rutas, release/revision ids, asignaciones o aprobadores.
- [ ] Observabilidad no registra hashes privados, narrativa, respuestas ni datos de pago.
- [ ] Rate limit real de login `12/300` no se desactiva ni amplía en CI.

## Smoke HTTP real

- [ ] M35 crea expediente y documentos reales.
- [ ] M36.0 registra todas las mesas.
- [ ] M36.1 asigna especialista y QA separados.
- [ ] Especialista aprueba legalmente hashes vigentes.
- [ ] QA aprueba después de legal.
- [ ] M36.2 reconcilia hasta `APROBADO_QA`.
- [ ] M32 libera todas las copias exactas.
- [ ] Bypass M24 directo queda bloqueado.
- [ ] M36.3 entrega y M24 termina en `ENTREGADO`.
- [ ] Retry M36.3 es idempotente.
- [ ] Cliente titular descarga ZIP válido.
- [ ] Segundo cliente queda oculto.

## Evidencia final a registrar

- SHA certificado: pendiente.
- Workflow/run: pendiente.
- Total de pruebas: pendiente.
- Artifact visual: pendiente.
- Digest artifact: pendiente.

La certificación de este checklist es **técnica**. No constituye aprobación jurídica, QA profesional, autorización de producción, constancia de notificación o prueba de recepción externa.
