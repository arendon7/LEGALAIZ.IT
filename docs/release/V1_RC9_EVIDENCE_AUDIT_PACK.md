# LegalAIZ.it V1-RC9 — Evidence Audit Pack

## Objetivo

RC9 convierte el estado disperso de assurance en una vista operativa única, reproducible y redactada. No crea una nueva fuente de verdad: compone las fuentes ya certificadas y conserva sus límites.

Fuentes consumidas:

1. RC6 — execution plan de 22 controles.
2. RC2 — dossier de 10 controles externos heredados.
3. RC7 — ledger de 12 atestaciones externas RC4.
4. RC8.1 — campaña de coordinación y semántica de estado.
5. RC4/release readiness — procedencia de decisiones humanas de autorización.

## Salidas

`tools/v1_evidence_audit_pack.py` genera por stdout:

- `--format json`: snapshot estructurado determinista.
- `--format markdown`: reporte humano para Legal, QA y operaciones.
- `--campaign CMP-...`: opcionalmente vincula el snapshot a una campaña RC8/RC8.1 existente.

No existe opción de escritura, ejecución de controles, registro de evidencia, aprobación, ratificación, autorización o go-live.

## Redacción

El pack no expone:

- actores o identificadores de actores;
- `evidence_event_id`;
- rutas de evidencia, bundles o manifests;
- fingerprint del entorno;
- hashes de artefactos probatorios;
- referencia de evidencia de la decisión de autorización;
- secretos, tokens, credenciales, llaves o connection strings;
- contenido de evidencia.

Sí expone material necesario para auditoría de estado:

- 22 control refs y su framework RC2/RC4;
- dominio y alcance de release;
- estado canónico derivado;
- prerequisitos y dependencias pendientes;
- si la evidencia activa quedó vinculada a la campaña, como booleano;
- próxima acción operacional por código;
- conteos agregados de evidencia;
- estado de código, producción real y V1 comercial;
- estado y fuente de la decisión humana de autorización, sin su `evidence_ref`;
- blockers de release en forma de códigos no sensibles.

## Snapshot determinista

El `snapshot_sha256` se calcula sobre el contenido canónico redactado, excluyendo timestamps y otros valores volátiles. Con las mismas fuentes de verdad, dos ejecuciones producen el mismo digest. Una modificación real de campaña, evidencia o decisión cambia el snapshot.

El digest identifica el reporte, no acredita autenticidad de evidencia ni autoriza release.

## Separación de gates

### Estructura RC9

La política, cobertura 10 RC2 + 12 RC4, formatos y reglas de redacción forman parte del release candidate de código. Si esta estructura se rompe, `RC_CODE_READY` debe fallar.

### Salud runtime

Si el ledger runtime está alterado o el snapshot no puede construirse de forma íntegra, producción real y V1 comercial quedan bloqueadas. Ese defecto operativo no convierte automáticamente el artefacto de código en defectuoso.

### Autorización

Un snapshot con 22/22 controles verificados sigue sin ser autorización. Producción y pagos requieren la procedencia humana versionada ya definida por RC4 y sus metadata gates.

## Defensa de no regresión

`tools/v1_release_readiness_audit.py` conserva RC8 como baseline y evalúa RC9 como gate actual. RC9 no puede declarar el candidato listo si el baseline RC8 no lo está.

Cadena efectiva:

`CLI → RC9 → RC8 → RC7 → RC6 → RC5 → RC4`

El baseline RC8 se evalúa además como guard explícito de no regresión.

## Criterios de aceptación

1. 22 controles exactos: 10 RC2 + 12 RC4.
2. JSON y Markdown deterministas/redactados.
3. Ninguna clave interna prohibida en el pack.
4. Campaña RC8.1 `CREATED` no aparece bloqueada sólo por dependencias normales.
5. Cambios reales de coordinación cambian el snapshot.
6. 22/22 evidencia no produce autorización humana.
7. Corrupción runtime bloquea go-live pero no degrada por sí sola `RC_CODE_READY`.
8. Política RC9 inválida sí bloquea el candidato de código.
9. Sin rutas HTTP nuevas ni endpoints de release.
10. Suite completa, smoke HTTP y QA visual deben permanecer verdes antes de certificar el SHA.
