# V1-RC7 — External Evidence Intake & Append-only Ledger

## Objetivo

RC6 dejó definidos los 22 controles externos que deben ejecutarse antes de habilitar producción jurídica real o V1 comercial. RC7 crea el mecanismo para **recibir y gobernar evidencia real** sin almacenarla dentro del repositorio, sin degradar la cadena RC2 y sin convertir el registro de evidencia en una autorización de release.

## Principio de separación

RC7 distingue cuatro actuaciones:

1. **ejecución técnica** del control;
2. **registro** del paquete de evidencia;
3. **revisión independiente**;
4. **ratificación de release**.

Para las atestaciones RC4 estas identidades deben ser distintas. La separación de actores de RC7 es un control de gobierno de evidencia; no concede por sí misma permisos de aplicación ni modifica RBAC.

## Bundle externo

Cada ejecución se documenta fuera del repositorio mediante un directorio controlado que contiene `manifest.json` y los artefactos exigidos por RC6.

El manifiesto usa `schema=legalaiz-v1-external-evidence-bundle-v1` e identifica:

- control RC2/RC4;
- framework e ID fuente;
- entorno;
- fecha de observación;
- vigencia;
- ejecutor técnico;
- declaración de redacción;
- artefactos con ruta relativa, tamaño y SHA-256.

El `manifest.json` actúa como manifest SHA-256 del bundle. Los demás artefactos requeridos por RC6 deben existir físicamente y coincidir en hash y tamaño.

## Validación fail-closed

`legalai_platform/external_evidence_bundle_v1.py` rechaza:

- rutas absolutas o traversal `..`;
- controles no presentes en RC6;
- framework, ID, entorno o rol ejecutor inconsistentes;
- evidencia futura, vencida o con vigencia superior al máximo RC6;
- falta de declaración de redacción;
- claves de manifiesto capaces de almacenar secretos;
- artefactos faltantes;
- hashes o tamaños inconsistentes;
- nombres o rutas duplicadas.

El validador no intenta publicar ni copiar los archivos. La evidencia permanece bajo un `evidence_root` externo controlado.

## RC2: preservación completa

RC7 **no reemplaza** `ExternalEvidenceDossier` RC2.

`register_rc2_bundle()` valida primero el bundle y registra únicamente su manifiesto en el dossier RC2 existente. Después siguen siendo obligatorias:

- `DOMAIN_APPROVED`;
- `RELEASE_RATIFIED`;
- actores separados según política RC2;
- integridad del ledger;
- vigencia de la evidencia.

Además, RC7 vuelve a validar el bundle físico antes de aceptar como suficiente un control RC2 ya ratificado. Un archivo legado aprobado que no sea un bundle RC7 íntegro no puede abrir producción bajo RC7.

## RC4: ledger append-only

`legalai_platform/external_attestation_dossier_v1_rc7.py` gobierna las 12 atestaciones RC4 mediante eventos:

- `EVIDENCE_REGISTERED`;
- `REVIEW_APPROVED`;
- `RELEASE_RATIFIED`;
- `REVOKED`.

Cada evento incorpora secuencia, hash del evento y hash previo. Cualquier alteración rompe la cadena y falla cerrada.

Registrar un bundle no verifica la atestación. Para obtener `VERIFIED_EXTERNAL_EVIDENCE` se requiere:

1. bundle externo válido;
2. registrador distinto del ejecutor técnico;
3. revisor independiente con el rol definido en RC6;
4. ratificador de release distinto de ejecutor, registrador y revisor;
5. bundle todavía íntegro y vigente al momento de lectura.

La modificación posterior de cualquier artefacto invalida inmediatamente el estado efectivo aunque el ledger conserve las aprobaciones históricas.

## Registro estático

`config/v1/production_attestations.json` permanece como **input versionado e inmutable en runtime**.

RC7 no lo sobrescribe. El readiness crea un overlay de lectura desde el ledger append-only. Esto conserva:

- trazabilidad histórica;
- separación entre política versionada y evidencia operativa;
- ausencia de commits automáticos con evidencia real;
- capacidad de revocación sin reescribir historia.

## Readiness RC7

`legalai_platform/release_readiness_v1_rc7.py` envuelve RC6.

Para RC2 añade un gate de integridad del bundle sobre la aprobación RC2 existente.

Para RC4 sólo retira un blocker de atestación cuando el ledger reporta `VERIFIED_EXTERNAL_EVIDENCE`. No retira ni altera:

- flags de `release_metadata`;
- autorización humana versionada;
- blockers RC2;
- controles no verificados;
- autorización comercial.

Por ello, **evidencia verificada no equivale a go-live autorizado**.

## Seguridad

No deben almacenarse en manifiestos, repositorio, PR, CI o salidas públicas:

- contraseñas;
- tokens;
- API keys;
- private keys;
- recovery codes;
- valores de secretos;
- credenciales;
- dumps o backups reales;
- documentos de clientes;
- datos personales innecesarios.

Los informes públicos de readiness muestran estado agregado y no rutas internas ni identidades de actores.

## Estado inicial esperado

En un checkout limpio:

- código: `RC_CODE_READY`;
- bundles RC2 validados: `0/10`;
- atestaciones RC4 verificadas en runtime: `0/12`;
- producción jurídica real: `REAL_PRODUCTION_BLOCKED`;
- V1 comercial: `COMMERCIAL_V1_BLOCKED`;
- `production_attestations.json`: sin mutación;
- autorización productiva/comercial: sin mutación.

## Gate de salida

RC7 sólo puede certificarse si el SHA exacto conserva verde toda la regresión acumulada, los smokes HTTP, el public demo y el QA visual DOCX. Esa certificación acredita el mecanismo de intake/ledger, **no la existencia de evidencia externa real**.

## Siguiente fase

Después de certificar RC7, la siguiente frontera es el **orquestador de ejecución controlada**: permitir preparar una sesión por entorno, detectar prerequisitos, importar bundles reales de forma explícita, mostrar avance 0–22/22 y producir un dossier de auditoría para revisión humana, sin exponer artefactos sensibles ni habilitar automáticamente producción.
