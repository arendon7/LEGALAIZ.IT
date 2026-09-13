# M37.0 — Hardening previo a certificación

## Invariantes añadidos

1. **Orden físico de SQLite no define el contrato jurídico.** Las actividades M24 se validan por `action_label` exacto y cobertura completa. Duplicados, faltantes, extras o identificadores vacíos fallan cerrado.
2. **Snapshot determinista.** Los IDs de actividades se almacenan en el orden explícito del contrato M37, aunque la base de datos entregue filas en otro orden.
3. **Frontera transaccional única.** `_finalize_start()` no confirma transacciones. `start()` confirma en una sola frontera la activación del enrolamiento y el evento `FOLLOW_UP_STARTED`, después de que la transición M24 `ENTREGADO → EN_SEGUIMIENTO` haya quedado registrada.
4. **Semántica jurídica conservadora.** Ninguna actividad completada acredita por sí sola evidencia, efecto jurídico, recepción, cumplimiento de término o procedencia de una acción.
5. **Sin cierre implícito.** `close_readiness=true` sólo expresa que todas las actividades contractualmente requeridas aparecen completadas; M37.0 no ejecuta `CERRADO` ni `ESCALADO`.

## Regresiones

`tests/test_m37_0_hardening.py` fija expresamente independencia del orden de filas, rechazo de duplicados y propiedad de la frontera de commit por `start()`.

La certificación sólo puede declararse sobre un SHA exacto con suite completa, smoke HTTP hasta M37.0, M33.1 y visual-docx en verde.
