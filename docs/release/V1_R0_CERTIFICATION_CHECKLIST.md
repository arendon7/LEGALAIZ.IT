# V1-R0 — Checklist de certificación técnica

V1-R0 sólo se considera técnicamente certificado para un SHA exacto si se conserva evidencia verificable de todos los puntos siguientes.

## Código y contrato

- [ ] `config/release/v1_readiness_contract.json` válido y fail-closed.
- [ ] 11 productos preservados.
- [ ] 473 preguntas o más preservadas.
- [ ] marcadores M34.1 → M37.3 presentes.
- [ ] runtime usa `http_handler_release_v1.Handler` sobre `http_handler_m37_3.Handler`.
- [ ] endpoint V1 es únicamente GET.
- [ ] endpoint V1 requiere rol admin.
- [ ] ningún código V1 modifica `REAL_PRODUCTION_AUTHORIZED`, `REAL_PAYMENTS_AUTHORIZED` o `SYNTHETIC_DATA_ONLY`.

## Semántica del gate

- [ ] entorno demo/local devuelve `platform_ready=false`.
- [ ] entorno demo/local devuelve `commercial_ready=false`.
- [ ] `activation_authorized=false` mientras `REAL_PRODUCTION_AUTHORIZED=false`.
- [ ] flags externas no pueden sustituir artefactos de repositorio ausentes.
- [ ] storage local cifrado no se presenta como storage durable productivo.
- [ ] pagos reales se evalúan en compuerta separada.
- [ ] readiness técnico no se presenta como aprobación jurídica, QA, seguridad o privacidad.

## Seguridad y privacidad

- [ ] respuesta HTTP no expone `DATABASE_URL` ni connection strings.
- [ ] respuesta HTTP no expone llaves, seeds, contraseñas o recovery codes.
- [ ] respuesta HTTP no expone inventario nominal de usuarios MFA.
- [ ] respuesta HTTP no expone narrativas, respuestas, documentos o payload jurídico.
- [ ] observabilidad registra sólo rol, estados y conteos; no secretos ni payload jurídico.
- [ ] cliente no puede leer readiness.
- [ ] especialista no puede leer readiness salvo futura decisión expresa de gobierno.

## Pruebas

- [ ] `python -m compileall -q .` PASS.
- [ ] suite completa `unittest` PASS.
- [ ] `tools/v1_r0_http_smoke.py` PASS contra servidor real de la rama.
- [ ] smoke M34.2 → M37.3 PASS sin regresión.
- [ ] M33.1 public demo smoke 8/8 PASS.
- [ ] visual-docx PASS.

## Evidencia de CI

Registrar sólo después de ejecución completa:

- SHA certificado: pendiente.
- Workflow `Validación LegalAIZ.it`: pendiente.
- Run id: pendiente.
- Conteo total de tests: pendiente.
- Artifact visual id: pendiente.
- Artifact digest: pendiente.

## Gobierno

- [ ] PR permanece draft durante desarrollo/certificación.
- [ ] CI se ejecuta temporalmente contra `main` si es necesario para activar workflow.
- [ ] después de certificar, PR se retargetea a `m37/professional-disposition-gate`.
- [ ] la certificación se registra sin crear un commit posterior al SHA certificado.
- [ ] no se cambia la línea base `main` ni `VERSION` como parte de V1-R0.
- [ ] no se declara producción jurídica real ni aprobación comercial.
