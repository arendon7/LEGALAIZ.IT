# LegalAIZ.it V1-RC10 — Audit Custody Export

## Objetivo

RC10 resuelve una brecha operativa posterior a RC9: el Evidence Audit Pack ya era determinista, redactado y verificable dentro del runtime, pero no existía un artefacto canónico de custodia que pudiera entregarse a Legal, QA, operaciones o auditoría y verificarse después sin volver a consultar las fuentes internas.

RC10 **no crea una nueva fuente de verdad** y **no añade un nuevo gate de release**. Exporta una representación derivada del snapshot RC9 y permite verificar su integridad.

## Bundle canónico

`tools/v1_evidence_audit_export.py export --output-root <directorio> [--campaign CMP-...]`

genera un directorio cuyo nombre es el `envelope_sha256` y contiene exactamente:

1. `audit-pack.json`
2. `audit-pack.md`
3. `custody-manifest.json`

El bundle es inmutable por diseño. Si ya existe un directorio con el mismo digest:

- si verifica exactamente, la exportación es idempotente;
- si está alterado o incompleto, RC10 falla cerrado y **no lo sobrescribe**.

## Qué se hashea

El `custody-manifest.json` registra SHA-256 y tamaño únicamente de:

- `audit-pack.json`;
- `audit-pack.md`.

Esos dos archivos ya son salidas redactadas de RC9.

RC10 no incorpora ni publica:

- hashes de artefactos probatorios originales;
- rutas de evidencia;
- `evidence_event_id`;
- actores;
- fingerprint del entorno;
- `evidence_ref` de autorizaciones;
- secretos o credenciales;
- contenido de evidencia.

El `snapshot_sha256` conserva la identidad semántica del snapshot RC9. El `envelope_sha256` identifica el manifest de custodia y los dos payloads redactados.

## Integridad frente a no repudio

`envelope_sha256` **no es una firma digital** y por sí solo no prueba quién creó o aprobó el bundle.

Para comprobación posterior contra un valor previamente registrado:

`tools/v1_evidence_audit_export.py verify --bundle <directorio> --expected-envelope-sha256 <sha256>`

El digest esperado debe provenir de un anclaje externo confiable, por ejemplo un sistema de gestión de releases, expediente de auditoría, ticket de aprobación o mecanismo de firma externo. RC10 no implementa ni simula esa firma.

## Retención

RC10 no fija un plazo legal de conservación. La política declara expresamente que:

- la retención es definida por la organización;
- esa configuración no constituye una conclusión jurídica sobre términos legales de archivo o conservación.

Cualquier política corporativa de retención deberá validarse separadamente frente a la naturaleza del expediente, datos personales, obligaciones regulatorias y requisitos contractuales aplicables.

## Límites de gobierno

La exportación:

- no ejecuta controles;
- no registra evidencia;
- no modifica ledgers RC2/RC7/RC8;
- no modifica release metadata;
- no aprueba ni ratifica evidencia;
- no autoriza producción real;
- no autoriza pagos reales;
- no sustituye las decisiones humanas versionadas RC4;
- no modifica la cadena `release_readiness_v1_rc9`.

RC10 es una **capacidad operativa de custodia**, no un mecanismo de promoción.

## Verificación fail-closed

La verificación exige:

1. directorio real, no symlink;
2. exactamente los tres archivos canónicos;
3. JSON válido;
4. schema RC10 correcto;
5. digest canónico del manifest correcto;
6. nombre del directorio igual al `envelope_sha256`;
7. digest RC9 interno del `audit-pack.json` correcto;
8. vínculo exacto entre manifest y `snapshot_sha256`;
9. hash y tamaño exactos de los dos payloads;
10. referencia del snapshot dentro del Markdown;
11. preservación de que el digest no es firma y requiere anclaje externo para no repudio;
12. si se suministra un digest externo, coincidencia exacta.

## Criterios de aceptación

1. Exportación limpia crea exactamente tres archivos.
2. Dos exportaciones del mismo snapshot son idempotentes y generan un solo bundle.
3. Alterar JSON, Markdown o manifest invalida el bundle.
4. Un digest externo distinto falla cerrado.
5. Un bundle existente alterado jamás se sobrescribe automáticamente.
6. Campaña, ledger y autorización no son modificados por exportar.
7. Actores y fingerprint siguen redactados.
8. El manifest hashea únicamente las dos salidas redactadas.
9. `envelope_sha256` nunca se presenta como firma digital.
10. RC10 no cambia `release_readiness`; RC9 sigue siendo el gate actual.
11. No se añade endpoint HTTP ni ruta de activación.
12. Suite completa, smoke HTTP y QA visual deben seguir verdes antes de certificar el SHA.

## Próxima frontera real

Después de RC10, la mejora de assurance ya no debe consistir en añadir wrappers automáticos. La frontera restante es operacional y humana:

- ejecutar los 22 controles reales;
- registrar evidencia auténtica y vigente;
- completar revisiones y ratificaciones separadas;
- anclar externamente los digests de custodia que corresponda;
- documentar las decisiones humanas versionadas de producción y, por separado, de pagos.

Mientras esas condiciones no existan, `REAL_PRODUCTION_BLOCKED` y `COMMERCIAL_V1_BLOCKED` deben permanecer como estados legítimos y deliberados.
