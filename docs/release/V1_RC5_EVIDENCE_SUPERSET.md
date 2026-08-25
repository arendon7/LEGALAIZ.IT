# V1-RC5 — Superset de evidencia externa

## Hallazgo

Las líneas V1-RC2 y V1-RC4 llegaron a usar inventarios de assurance distintos:

- RC2 conserva 10 controles externos append-only: PostgreSQL runtime, TLS, monitoreo, restore drill, carga, pentest, privacidad, incidente, Mac/Windows y rollback.
- RC4 incorporó 12 atestaciones orientadas a go-live: PostgreSQL, backup/restore, migración, object storage, secretos, MFA, antimalware, monitoreo/IR, privacidad, modelo Legal+QA, DR y pagos.

RC4 amplía cobertura, pero no representa de forma explícita todos los controles RC2. Sustituir RC2 por RC4 habría permitido perder controles ya construidos —especialmente `load_test`, `pentest`, `mac_windows_validation`, `tls_certificate` y `rollback_drill`— sin una decisión de política expresa.

## Decisión RC5

No se infieren equivalencias automáticas entre ambos modelos.

Para producción jurídica real, RC5 exige **ambos gates de manera independiente**:

1. RC4: metadata, 11 atestaciones productivas, procedencia de autorización humana versionada y evidencia trazable.
2. RC2: las 10 atestaciones externas del dossier append-only con integridad, vigencia, aprobación de dominio y ratificación separada.

Para V1 comercial se suma, además, la atestación del proveedor de pagos y la autorización comercial versionada ya exigidas por RC4.

## Implementación

`legalai_platform/release_readiness_v1_rc5.py` envuelve el gate RC4 y agrega el dossier RC2 como condición necesaria.

El reporte incorpora:

- `schema=legalaiz-v1-release-readiness-report-v3`;
- `assurance_superset.strategy=RC4_PLUS_RC2_INDEPENDENT_GATES`;
- conteo esperado: 10 controles RC2 + 12 atestaciones RC4;
- `legacy_rc2_evidence_gate` dentro del readiness de producción real;
- blockers `RC2_EXTERNAL_EVIDENCE:<control>`;
- fallo cerrado ante política RC2 ausente/inválida o dossier con integridad inválida.

El CLI `tools/v1_release_readiness_audit.py` pasa a consumir RC5. No se añade endpoint HTTP ni mecanismo de activación.

## Invariantes

RC5 no modifica:

- `main`;
- `VERSION` ni M33.1;
- `REAL_PRODUCTION_AUTHORIZED=false`;
- `REAL_PAYMENTS_AUTHORIZED=false`;
- `SYNTHETIC_DATA_ONLY=true`;
- la exigencia de decisión humana versionada de RC4;
- el modelo append-only y separación de funciones de RC2.

CI continúa pudiendo certificar únicamente el candidato de código. No puede crear evidencia externa, autorizar producción, habilitar pagos ni afirmar go-live.

## Estado esperado sin evidencia externa

- `RC_CODE_READY`;
- `REAL_PRODUCTION_BLOCKED`;
- `COMMERCIAL_V1_BLOCKED`;
- RC2: `0/10` controles satisfechos en un checkout limpio;
- RC4: atestaciones externas pendientes;
- autorización productiva/comercial: `NOT_AUTHORIZED`.

Este estado bloqueado es el resultado seguro esperado.

## Regresión

`tests/test_v1_rc5_evidence_superset.py` verifica:

1. preservación simultánea de 10 controles RC2 y 12 atestaciones RC4;
2. imposibilidad de perder silenciosamente TLS, carga, pentest, Mac/Windows o rollback;
3. RC2 como gate obligatorio para producción;
4. herencia del bloqueo por la capa comercial;
5. política RC2 inválida en modo fail-closed;
6. CLI apuntando al gate RC5;
7. ausencia de nuevo endpoint de activación.

## Siguiente frontera

Después de certificar RC5, el trabajo correcto deja de ser añadir más flags. El siguiente paso es construir y ejecutar el paquete de evidencia externa real por entorno, con referencias auditables, responsables humanos y fechas de vigencia. Sólo entonces puede evaluarse una transición controlada de los estados `NOT_AUTHORIZED`.
