# M36.2 — Certification Checklist

El SHA candidato sólo se certifica si todos los puntos siguientes pasan sobre el mismo head.

## Código y regresión

- [ ] `python -m compileall -q .` PASS.
- [ ] Suite completa `tests/test_*.py` PASS sin excluir módulos.
- [ ] Se preservan 11 productos y piso de 473 preguntas.
- [ ] No hay regresión de smokes M34.2 → M36.1.
- [ ] M33.1 public demo smoke 8/8 PASS.
- [ ] visual-docx PASS y artifact disponible.

## M36.2 — contratos funcionales

- [ ] Consume exactamente `EN_REVISION_JURIDICA` del ledger M36.0.
- [ ] Exige M36.1 `COMPLETE` y cobertura total de desks.
- [ ] Usuario no-admin no puede assess/reconcile/history.
- [ ] Aprobación jurídica parcial no avanza M24.
- [ ] Aprobación jurídica de todos los desks permite `APROBADO_JURIDICAMENTE → EN_QA`.
- [ ] QA parcial no avanza `APROBADO_QA`.
- [ ] QA completo permite `APROBADO_QA` sólo con legal previo sobre el mismo hash.
- [ ] Especialista y QA permanecen distintos.
- [ ] El actor M36.2 es técnico y no suplanta a los aprobadores humanos.
- [ ] Retry sin nuevo camino es read-only/idempotente.
- [ ] Un desk observado bloquea el éxito parcial y puede llevar M24 a `OBSERVADO`.
- [ ] Prioridad/SLA/notas M32.6 por sí solos no acreditan `CORREGIDO`.
- [ ] Nueva revisión/evidencia sustantiva puede habilitar `CORREGIDO → EN_REVISION_JURIDICA`.
- [ ] Regresión después de una aprobación ya reflejada escala; no rebobina silenciosamente.
- [ ] Cadena M36.2 alterada bloquea history y nuevas reconciliaciones.
- [ ] Respuestas públicas no exponen hashes, `evidence_json`, relato, respuestas ni datos de pago.
- [ ] `ENTREGADO` no puede ser producido por M36.2.
- [ ] Liberación completa sólo produce `delivery_gate_ready=true` manteniendo M24 en `APROBADO_QA`.

## HTTP real

- [ ] Compra sandbox M35 materializada.
- [ ] M36.0 crea desks e ingresa a revisión.
- [ ] M36.1 asigna manualmente especialista y QA.
- [ ] Especialista autenticado aprueba cada revisión vigente en M32.5.
- [ ] M36.2 rechaza progreso con aprobación parcial.
- [ ] M36.2 reconcilia legal completo a `EN_QA`.
- [ ] QA/admin independiente aprueba cada revisión vigente.
- [ ] M36.2 reconcilia QA completo a `APROBADO_QA`.
- [ ] Liberación M32 de todos los hashes no registra entrega automática.
- [ ] CSRF faltante bloquea POST M36.2.

## Evidencia final

Registrar en PR:

- SHA exacto certificado;
- workflow/run exactos;
- total de pruebas;
- línea final del smoke M36.2;
- resultado M33.1;
- artifact visual y digest.

Esta certificación es técnica. No constituye aprobación jurídica, QA, entrega, representación ni autorización de producción real.
