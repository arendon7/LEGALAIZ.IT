# V1-RC6 — Evidence Execution Pack

## Objetivo

RC5 consolidó el estándar de assurance: producción jurídica real exige simultáneamente 10 controles RC2 y 12 atestaciones RC4. RC6 convierte ese inventario en un **plan operativo ejecutable y auditable**, sin convertir el plan en evidencia ni habilitar producción.

La frontera es deliberada:

- CI puede comprobar que el runbook es completo y consistente;
- CI no puede declarar que un control externo fue ejecutado;
- CI no puede producir, aprobar ni falsificar evidencia;
- CI no puede autorizar producción real ni pagos reales.

## Inventario

`config/v1/evidence_execution_plan.json` contiene exactamente 22 controles:

- 10 controles RC2;
- 12 atestaciones RC4, incluida la certificación del proveedor de pagos.

Cada control conserva su identidad de origen. No se declara que un control RC2 sea equivalente a uno RC4, aunque puedan compartir artefactos o dependencias.

## Campos operativos por control

Cada entrada define como mínimo:

- `ref` estable con framework e ID fuente;
- dominio;
- entorno objetivo (`staging_equivalent` o `production_prelaunch`);
- rol ejecutor;
- rol revisor independiente;
- tipo de artefacto;
- artefactos mínimos esperados;
- vigencia máxima interna;
- alcance de release;
- prerequisitos;
- política de redacción;
- `evidence_ref=null`;
- `status=PENDING_EXTERNAL_EXECUTION`.

Los plazos son controles internos de release. No representan términos legales, regulatorios ni certificaciones de terceros.

## Separación de funciones

El ejecutor y el revisor deben ser roles distintos. La separación definida en RC6 no sustituye las aprobaciones de dominio y ratificación de release que RC2 ya exige; se suma a ellas.

Para el modelo jurídico/QA se exige un artefacto específico que documente:

- matriz de roles;
- procedimiento de aprobación dual;
- escalamiento;
- auditoría;
- ensayo de caso sintético o anonimizado;
- registro de aprobación.

## Seguridad de evidencia

El plan nunca debe almacenar:

- contraseñas;
- tokens;
- API keys;
- private keys;
- valores de secretos;
- credenciales;
- backups o dumps reales;
- documentos reales de clientes;
- datos personales innecesarios.

La evidencia externa debe quedar en un repositorio controlado y su referencia/hash será incorporada por los mecanismos de assurance ya existentes, no por este plan.

## Pagos

`RC4:real_payment_provider_certification` es el único control con `release_scope=commercial_only`.

Los otros 21 controles son de producción jurídica real. Esto evita que la ausencia de proveedor de pagos impida certificar estructuralmente el código, pero mantiene los cobros reales bloqueados hasta su certificación y autorización comercial versionada.

## Validación

`legalai_platform/evidence_execution_plan_v1.py` valida en modo fail-closed:

1. inventario exacto 10 RC2 + 12 RC4;
2. ausencia de duplicados o controles eliminados;
3. identidad con los archivos fuente de RC2 y RC4;
4. vigencia RC2 idéntica a la política original;
5. propietario RC4 alineado con el ejecutor;
6. separación ejecutor/revisor;
7. entornos y alcances permitidos;
8. artefactos y manifest SHA-256;
9. prerequisitos válidos y sin ciclos;
10. ausencia de referencias de evidencia embebidas;
11. ausencia de claves capaces de contener secretos;
12. estado inicial pendiente en los 22 controles.

`legalai_platform/release_readiness_v1_rc6.py` incorpora esa validación al candidato de código, pero deja explícitamente:

- `execution_ready=false`;
- `executed=0`;
- `pending=22`.

Por tanto, **un RC6 verde significa que sabemos exactamente qué debe ejecutarse y cómo debe revisarse; no significa que ya se haya ejecutado**.

## Estado esperado

Después de certificar RC6:

- código: `RC_CODE_READY`;
- execution pack: estructuralmente listo;
- evidencia ejecutada: `0/22` desde el plan;
- producción jurídica real: `REAL_PRODUCTION_BLOCKED`;
- V1 comercial: `COMMERCIAL_V1_BLOCKED`;
- producción y pagos: no autorizados.

## Siguiente fase

La siguiente fase legítima es la ejecución controlada del runbook sobre infraestructura real o equivalente a producción. Debe comenzar por dependencias técnicas fundacionales —PostgreSQL administrado, almacenamiento persistente, secretos, MFA, antimalware y observabilidad— y generar evidencia externa verificable.

Ningún control debe marcarse satisfecho a partir de CI, texto narrativo o datos fabricados.
