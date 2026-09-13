# V1-RC3 — Convergencia de assurance y release readiness

## Objetivo

Eliminar la divergencia entre las líneas V1 ya certificadas sin retirar capacidades ni promover prematuramente `main`.

V1-RC3 combina en un único árbol:

- V1-RC0: integración del estándar jurídico/documental M33 con el journey M34–M37;
- V1-RC1: compuerta de configuración productiva fail-closed;
- V1-RC2: dossier reforzado de evidencia externa;
- V1 Pilot Readiness: gobierno de piloto controlado, aprobaciones separadas y ventana de ejecución;
- V1 Release Readiness: veredictos independientes para candidato de código, producción jurídica real y V1 comercial.

## Linaje preservado

El commit de convergencia conserva dos padres explícitos:

- `63257ffa1140465b5f571a110009669cae701a6f` — línea V1-RC0 → RC1 → RC2 → Pilot certificada;
- `ef1f118a26b77b7a4f12cf356d7b352411f283ac` — V1 Release Readiness Gate certificado.

La convergencia no reescribe ninguno de los dos historiales.

## Invariantes

La fase debe conservar simultáneamente:

1. 11 productos jurídicos y los pisos canónicos de preguntas y reglas.
2. Estándar documental M33 y journey M34.1 → M37.3.
3. Revisión jurídica y QA separadas sobre la misma revisión documental.
4. Producción real bloqueada mientras `REAL_PRODUCTION_AUTHORIZED=false` o falte evidencia externa.
5. Pagos reales bloqueados mientras `REAL_PAYMENTS_AUTHORIZED=false` o falte certificación del proveedor.
6. Datos sintéticos como frontera vigente mientras la release metadata permanezca en M33.1.
7. Pilot Readiness sin capacidad de saltarse RC2 ni la metadata versionada.
8. V1 Release Readiness como evaluación pasiva: no añade endpoint de activación ni muta configuración.
9. Ninguna CI, por sí sola, autoriza producción jurídica real, pagos reales o lanzamiento comercial.

## Regresión de convergencia

`tests/test_v1_rc3_convergence.py` verifica que:

- RC1, RC2 y Pilot continúan compuestos en el mismo árbol;
- el gate más reciente puede declarar `RC_CODE_READY` sin declarar producción o comercio listos;
- la metadata canónica no se promueve;
- todas las políticas de assurance coexisten;
- la convergencia no expone una nueva ruta de activación en `run.py`.

## Estado esperado antes de evidencia externa

- código: `RC_CODE_READY`;
- producción jurídica real: `REAL_PRODUCTION_BLOCKED`;
- V1 comercial: `COMMERCIAL_V1_BLOCKED`;
- piloto con clientes reales: bloqueado hasta RC2, aprobaciones humanas, ventana válida y metadata autorizada;
- `main`: sin cambios.

Estos bloqueos son deliberados y constituyen el comportamiento seguro esperado.

## Gate de certificación RC3

El SHA exacto de RC3 sólo podrá considerarse técnicamente certificado cuando GitHub Actions acredite, sobre ese mismo SHA:

- sintaxis/importación PASS;
- suite completa PASS, incluida la regresión RC3;
- inventario de 11 productos y pisos de preguntas/reglas PASS;
- smokes acumulados M34–M37 PASS;
- public demo M33.1 PASS;
- visual-docx del portafolio PASS;
- release readiness audit PASS en modo candidato de código;
- ausencia de promoción de `main`, producción real y pagos reales.

## Después de RC3

Una vez certificado el SHA exacto, la siguiente fase deja de ser principalmente desarrollo funcional. Debe concentrarse en evidencia real y controlada: PostgreSQL, migración, backup/restore, object storage, secretos, MFA, antimalware, monitoreo/incident response, privacidad, modelo operativo jurídico+QA, disaster recovery, validación Mac/Windows y proveedor de pagos si se pretende lanzamiento comercial.

Ninguna de esas evidencias debe fabricarse desde CI ni declararse cumplida sin verificación externa trazable.
