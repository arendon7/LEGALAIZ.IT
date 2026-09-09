# M37.0 — Checklist de certificación técnica

M37.0 sólo puede marcarse certificado cuando un único SHA exacto cumpla todo este gate.

## Integridad y regresión

- [ ] `python -m compileall -q .` PASS.
- [ ] Suite completa `tests/test_*.py` PASS.
- [ ] 11 productos preservados.
- [ ] piso de 473 preguntas preservado.
- [ ] interfaz/datos demo PASS.
- [ ] smoke público M33.1 8/8 PASS.
- [ ] visual-docx SUCCESS.

## M37.0 funcional

- [ ] una lectura antes de iniciar no muta M24.
- [ ] sólo un caso M36.3 `DELIVERED_IN_APP` es elegible.
- [ ] los 11 productos y 44 actividades M24 tienen contrato exacto.
- [ ] `INICIAR SEGUIMIENTO` es confirmación exacta.
- [ ] inicio produce `ENTREGADO → EN_SEGUIMIENTO` una sola vez.
- [ ] retry de inicio es idempotente.
- [ ] caída posterior a M24 es recuperable sin cambiar actor original.
- [ ] no se duplican tareas M24.
- [ ] cliente ajeno obtiene 404.
- [ ] cola global sólo para administración.
- [ ] actualización legacy M24 queda bloqueada después del enrolamiento.
- [ ] bypass interno M24 de tareas queda bloqueado.
- [ ] cierre/escalamiento legacy quedan reservados después del enrolamiento.
- [ ] task retry no duplica evento.
- [ ] manipulación de cadena M37 bloquea lectura/escritura positiva.

## Semántica jurídica

- [ ] toda fecha M37 declara `is_legal_deadline=false`.
- [ ] toda fecha M37 declara `legal_deadline_verified=false`.
- [ ] M37.0 no calcula términos legales.
- [ ] reporte de cliente = `SELF_REPORTED`.
- [ ] registro profesional = `PROFESSIONAL_RECORDED`.
- [ ] `evidence_verified=false` en M37.0.
- [ ] `legal_effect_verified=false` en M37.0.
- [ ] completar tareas no ejecuta `CERRADO`.
- [ ] no existe escalamiento automático.

## Seguridad y trazabilidad

- [ ] POST exige same-origin + sesión + CSRF.
- [ ] rate limit real permanece intacto; CI no incorpora bypass.
- [ ] ledger M37 es append-only y hash-linked.
- [ ] notas no se duplican en ledger M37.
- [ ] salida pública no expone actores internos, snapshot, transición M24 ni hashes de cadena.
- [ ] observabilidad no registra nota, relato, respuestas, datos de pago ni hashes documentales.

## HTTP smoke

- [ ] recorrido real M35 → M36.0 → M36.1 → M32 legal/QA → M36.2 → M36.3 → M37.0 PASS.
- [ ] CSRF negativo PASS.
- [ ] confirmación débil negativa PASS.
- [ ] bypass M24 negativo PASS.
- [ ] cross-tenant negativo PASS.
- [ ] idempotencia PASS.
- [ ] close readiness sin cierre automático PASS.

## Evidencia de cierre

Registrar en PR:

- SHA exacto certificado;
- workflow/run id;
- número total de pruebas;
- resultado de smoke M37.0;
- M33.1;
- visual-docx.

La certificación técnica no equivale a aprobación jurídica humana, QA de contenido ni autorización de producción.
