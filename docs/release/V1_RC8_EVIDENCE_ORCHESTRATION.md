# V1-RC8 — Evidence Orchestration & Audit Dossier

## Objetivo

V1-RC8 convierte el execution pack RC6 y los mecanismos de intake RC7 en un proceso operativo coordinable y auditable, sin automatizar la ejecución de controles externos y sin crear una vía de autorización de producción.

RC8 no ejecuta pentests, restore drills, migraciones, rotaciones de secretos, validaciones MFA, pruebas de carga, pagos ni ningún otro control externo. Tampoco fabrica evidencia sintética para satisfacer gates reales.

## Arquitectura de separación

La cadena conserva cuatro planos independientes:

1. **Plan RC6**: define 22 controles independientes, responsables, artefactos, vigencias y dependencias.
2. **Evidencia RC2/RC7**: conserva los dossiers append-only, hashes, revisiones y ratificaciones canónicas.
3. **Campaña RC8**: registra exclusivamente coordinación operativa.
4. **Autorización RC4**: continúa requiriendo decisión humana versionada y evidencia de procedencia; RC8 no la modifica.

La regla central es:

> campaña preparada ≠ control ejecutado ≠ evidencia registrada ≠ evidencia revisada ≠ evidencia ratificada ≠ autorización de go-live.

## Campaign ledger

`legalai_platform/evidence_orchestration_v1_rc8.py` incorpora un ledger append-only con cadena SHA-256.

Eventos permitidos:

- `CAMPAIGN_CREATED`
- `CONTROL_STARTED`
- `EVIDENCE_LINKED`
- `CONTROL_REVIEW_READY`
- `CONTROL_BLOCKED`
- `CAMPAIGN_ABORTED`

No existen eventos `APPROVED`, `RATIFIED`, `AUTHORIZED`, `GO_LIVE` ni equivalentes.

Cada campaña fija:

- schema y versión del execution plan;
- SHA-256 exacto de `config/v1/evidence_execution_plan.json`;
- SHA Git completo del candidato fuente;
- fingerprint SHA-256 opaco del entorno;
- inventario 10 RC2 + 12 RC4.

Si el plan cambia después de crear la campaña, nuevas actuaciones fallan cerrado.

## Task packets

RC8 deriva los task packets directamente del execution plan RC6. No mantiene un segundo inventario manual.

Cada packet conserva:

- `control_ref` canónico;
- framework e identificador fuente;
- dominio;
- entorno;
- rol ejecutor y rol revisor;
- scope de release;
- tipo de artefacto;
- artefactos obligatorios;
- vigencia máxima;
- prerequisitos exactos RC6;
- política de redacción;
- schema del bundle RC7;
- checklist operativo seguro.

Los packets se generan con `evidence_ref = null` y no contienen credenciales, secretos ni evidencia.

## Dependencias

RC8 no inventa dependencias. Sólo consume `prerequisites` del execution plan RC6.

Un control con prerequisitos pendientes no puede registrarse como iniciado mediante el API de campaña. La verificación de prerequisitos se deriva del estado probatorio actual de los dossiers canónicos.

RC2 y RC4 continúan siendo controles independientes. No se presume equivalencia, sustitución o cobertura cruzada.

## Evidence linking

`EVIDENCE_LINKED` sólo puede referenciar el `evidence_event_id` activo del dossier canónico correspondiente.

El evento de campaña:

- no registra evidencia;
- no modifica el dossier RC2;
- no modifica el ledger RC7;
- no aprueba revisión;
- no ratifica release;
- no habilita producción.

## Audit dossier

`EvidenceAuditDossier` compone un read model de 22 controles con estados derivados:

- `MISSING`
- `PENDING`
- `REVIEW_REQUIRED`
- `RATIFICATION_REQUIRED`
- `VERIFIED`
- `EXPIRED`
- `TAMPERED`
- `BLOCKED_BY_DEPENDENCY`
- `BLOCKED_BY_PLAN_DRIFT`

Para RC2, una aprobación histórica sólo cuenta como `VERIFIED` si además la evidencia activa sigue siendo un bundle RC7 válido e íntegro. Esto preserva el gate aditivo introducido en RC7.

El dossier puede determinar `real_production_evidence_complete` y `commercial_evidence_complete`, pero ambos son conceptos probatorios. Incluso con 22/22 controles verificados, los campos de autorización del read model permanecen `false` hasta la decisión humana versionada del mecanismo de autorización.

## CLI segura

`tools/v1_evidence_campaign.py` permite:

- `create`
- `status`
- `packet`
- `audit`
- `start-control`
- `link-evidence`
- `review-ready`
- `block-control`
- `abort`

No ofrece comandos para aprobar, ratificar, autorizar o activar producción.

Las aprobaciones y ratificaciones continúan exclusivamente en los mecanismos profesionales RC2/RC7.

## Release readiness

`release_readiness_v1_rc8.py` envuelve RC7 y añade checks estructurales para:

- 22 controles;
- 10 RC2 + 12 RC4;
- 22 packets únicos;
- ausencia de evidencia embebida;
- integridad del ledger de campañas.

RC8 no elimina ningún blocker RC2/RC4/RC5/RC6/RC7 y no cambia los flags de autorización.

## Invariantes

- `main` no se modifica durante la certificación RC8.
- CI puede certificar código y estructura, no evidencia externa real.
- CI no puede autorizar producción jurídica real.
- CI no puede autorizar pagos reales.
- `EVIDENCE_COMPLETE` no equivale a autorización.
- ningún bundle de evidencia se versiona como parte de RC8.
- ningún secreto debe estar presente en campaign ledger, policy, packets o read models públicos.
- no se añade endpoint runtime de activación a `run.py`.

## Frontera posterior

Una vez certificado RC8, el siguiente avance legítimo ya no consiste en agregar flags de readiness. Corresponde ejecutar campañas reales en los entornos objetivo y alimentar los dossiers RC2/RC7 con evidencia auténtica, manteniendo separación de funciones y revisión humana. Sólo después de cerrar los gates de evidencia podría prepararse una decisión humana versionada de autorización.
