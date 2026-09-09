# M37.3 — Certification Checklist

Estado: **NO CERTIFICADO** hasta un workflow verde sobre el SHA exacto candidato.

PR de certificación: `#37`.

## Lifecycle y gobernanza

- [x] M37.0 conserva bloqueo legacy de `CERRADO`/`ESCALADO`.
- [x] Cierre sólo por especialista asignado.
- [x] Escalamiento por especialista asignado o administración.
- [x] Cliente no puede disponer lifecycle.
- [x] Cierre exige `close_readiness` M37.0.
- [x] Cierre exige resolver soportes pendientes/aclaraciones M37.1.
- [x] Cierre exige resolver recordatorios activos M37.2.
- [x] Escalamiento no exige readiness de cierre.
- [x] Ninguna decisión es automática.

## Semántica jurídica

- [x] Cierre = alcance de seguimiento concluido, no éxito jurídico.
- [x] Sin verificación de efecto externo.
- [x] Sin verificación de autenticidad.
- [x] Sin verificación de término legal.
- [x] Sin cálculo normativo de fechas.
- [x] Sin comunicaciones externas automáticas.

## Privacidad

- [x] `internal_reason` separado de `client_summary`.
- [x] M24 recibe sólo `client_summary`.
- [x] Ledger M37 no duplica ninguno de los dos textos.
- [x] Observabilidad no registra razón interna ni resumen visible.
- [x] Modelo público no expone actor id ni hashes internos.

## Integridad y recuperación

- [x] Intent inmutable con hash.
- [x] Eventos append-only hash-linked.
- [x] Saga `PREPARED → M24 → COMPLETED`.
- [x] Retry post-commit recupera sin segunda transición.
- [x] Retry exacto completado es read-only/idempotente.
- [x] Retry diferente se rechaza.

## CI pendiente

- [ ] `compileall` PASS.
- [ ] suite completa PASS.
- [ ] 11 productos / >=473 preguntas PASS.
- [ ] HTTP M34.2 → M37.3 PASS.
- [ ] M37.3 close + retry + escalation PASS.
- [ ] M33.1 public demo 8/8 PASS.
- [ ] visual-docx PASS.

La certificación técnica no sustituye aprobación jurídica humana, QA humano de contenido ni autorización de producción.
