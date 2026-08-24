# M37.2 — Certification Checklist

Estado inicial: **NO CERTIFICADO** hasta que un workflow completo sea exitoso sobre el SHA exacto candidato.

## Contrato jurídico y semántico

- [x] `M24 due_at` permanece sólo como `OPERATIONAL_CHECKPOINT`.
- [x] Una fecha registrada no es término legal.
- [x] Una fecha registrada por profesional no verifica término legal.
- [x] Evidencia M37.1 vinculada no verifica la fecha ni el contenido.
- [x] `DUE` significa recordatorio operativo debido, no vencimiento normativo.
- [x] Sin cálculo de días hábiles.
- [x] Sin cálculo de prescripción, caducidad o término estatutario.
- [x] Sin cierre, escalamiento o cumplimiento automático.

## Integridad

- [x] Fechas append-only con hash.
- [x] Correcciones por supersesión, no overwrite.
- [x] Sin bifurcaciones de corrección.
- [x] Recordatorios inmutables con eventos hash-linked.
- [x] `DUE` se deriva en lectura sin escritura automática.
- [x] Retry exacto de fechas antes de cuota.
- [x] Retry exacto de correcciones antes de cuota.
- [x] Retry exacto de recordatorios antes de cuota.
- [x] Acknowledge idempotente.

## Seguridad y privacidad

- [x] Hereda control de acceso M37.0.
- [x] Cross-tenant oculto con 404.
- [x] Same-origin en escrituras.
- [x] Sesión requerida.
- [x] CSRF requerido.
- [x] Rate limiting.
- [x] Ledger M37 no duplica valores de fecha ni `scheduled_for`.
- [x] Observabilidad no registra valores de fechas ni payload jurídico.
- [x] Respuesta pública no expone hashes ni actor IDs internos.

## No regresión

Pendiente de CI sobre el SHA candidato:

- [ ] `compileall` PASS.
- [ ] suite completa PASS.
- [ ] datos demo 11 productos / >=473 preguntas PASS.
- [ ] smoke HTTP M34.2 → M37.2 PASS.
- [ ] smoke público M33.1 PASS.
- [ ] visual-docx PASS.

## Evidencia de certificación

Se completará en el PR únicamente después de un workflow verde sobre el SHA exacto. La certificación técnica no equivale a aprobación jurídica humana, QA humano ni autorización de producción.
