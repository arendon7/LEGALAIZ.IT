# V1-RC4 — Procedencia de autorización y promoción fail-closed

## Problema corregido

V1-RC3 convergió correctamente RC1, RC2, Pilot y Release Readiness, pero dejó una ambigüedad futura en el cálculo de gobierno: una producción legítimamente habilitada podía marcarse como `unauthorized_promotion_detected` únicamente porque la política establece —correctamente— que CI no puede autorizar producción ni pagos.

RC4 separa dos conceptos que no deben confundirse:

1. **readiness**: que todos los controles técnicos, evidencias y gates estén satisfechos;
2. **procedencia de autorización**: que exista una decisión humana versionada y trazable que habilite el cambio de estado.

## Cambio

Se incorpora `config/v1/authorization_decisions.json` como registro versionado de decisiones de autorización. El estado inicial permanece deliberadamente:

- producción jurídica real: `NOT_AUTHORIZED`;
- V1 comercial/pagos reales: `NOT_AUTHORIZED`.

Una autorización futura sólo es válida cuando coinciden, de forma fail-closed:

- el gate explícito de `release_metadata`;
- el estado `AUTHORIZED_VERSIONED_HUMAN_DECISION`;
- la fuente de decisión exigida por contrato;
- una referencia de evidencia no vacía;
- las attestations externas exigidas por el release contract.

CI continúa sin capacidad de autorizar producción real o pagos reales.

## Semántica de gobierno

RC4 diferencia:

- `unauthorized_promotion_detected`: un gate de autorización fue activado sin una decisión humana versionada válida;
- `authorization_state_inconsistent`: metadata y registro de decisión no representan el mismo estado;
- `provenance_valid`: autorización activa, fuente correcta y referencia de evidencia presente.

Una autorización humana hipotética, completa y versionada ya no se confunde con una autorización automática de CI.

## Estado actual

RC4 **no autoriza nada** y no modifica `main`, `VERSION`, M33.1 ni los flags productivos.

Estado esperado:

- `RC_CODE_READY`;
- `REAL_PRODUCTION_BLOCKED`;
- `COMMERCIAL_V1_BLOCKED`;
- `REAL_PRODUCTION_AUTHORIZATION_DECISION` presente como blocker;
- `REAL_PAYMENTS_AUTHORIZATION_DECISION` presente como blocker;
- `unauthorized_promotion_detected=false`;
- `authorization_state_inconsistent=false`.

## Regresión

`tests/test_v1_rc4_authorization_provenance.py` prueba:

1. estado actual consistente y bloqueado;
2. CI sin facultad de autorización;
3. flag activado sin decisión versionada → promoción no autorizada;
4. decisión humana versionada + evidencia → procedencia válida;
5. autorización sin referencia de evidencia → fail-closed;
6. decisión adelantada al gate de metadata → inconsistencia.

## Gate de salida

RC4 sólo podrá certificarse sobre un SHA exacto si la suite completa, inventario, smokes HTTP, public demo y auditoría visual DOCX permanecen verdes, sin promoción de `main` ni habilitación real.
