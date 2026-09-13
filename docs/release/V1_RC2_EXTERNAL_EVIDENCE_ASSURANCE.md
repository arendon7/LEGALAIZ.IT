# V1-RC2 — External Evidence Assurance

## Objetivo

V1-RC2 fortalece la evidencia externa exigida por V1-RC1 para una futura validación productiva controlada.

No añade nuevas funciones jurídicas al usuario y no modifica M34–M37. Tampoco habilita pagos reales, comunicaciones externas ni lanzamiento comercial.

La frontera que se endurece es esta:

`RC1 configuración segura + evidencia externa → validación productiva controlada`

RC2 sustituye, para el candidato RC2, la suficiencia del registro legacy `governance/m7/EXTERNAL_ATTESTATIONS.json` por un dossier de evidencia con:

1. archivo externo existente;
2. SHA-256 y tamaño registrados;
3. fecha observada y vigencia máxima por control;
4. aprobación del dominio correspondiente;
5. ratificación de release por un actor diferente;
6. historial append-only de registro, aprobación, ratificación y revocación;
7. verificación de integridad antes de cada actuación;
8. resumen público minimizado sin rutas, hashes, actores ni IDs de eventos.

## Controles obligatorios

RC2 gobierna exactamente los diez controles externos que RC1 ya exigía:

- `postgres_runtime`;
- `tls_certificate`;
- `monitoring_alerts`;
- `restore_drill_production`;
- `load_test`;
- `pentest`;
- `privacy_approval`;
- `incident_drill`;
- `mac_windows_validation`;
- `rollback_drill`.

La política canónica vive en `config/v1_rc2_external_evidence_policy.json`.

## Estados de un control

Un control no puede pasar directamente de “archivo presente” a “aprobado”. El read model puede producir, entre otros:

- `MISSING_EVIDENCE`;
- `EVIDENCE_FILE_MISSING`;
- `EVIDENCE_INTEGRITY_MISMATCH`;
- `EVIDENCE_EXPIRED`;
- `DOMAIN_APPROVAL_REQUIRED`;
- `RELEASE_RATIFICATION_REQUIRED`;
- `SEPARATION_OF_DUTIES_INVALID`;
- `VERIFIED_FOR_RELEASE_GATE`.

Sólo `VERIFIED_FOR_RELEASE_GATE` cuenta como PASS.

## Separación de funciones

La evidencia de un control debe ser aprobada por un rol permitido para su dominio. La ratificación posterior sólo puede hacerla un rol autorizado de release.

El mismo `actor_id` no puede cubrir aprobación de dominio y ratificación de release para la misma evidencia, incluso si dispone de más de un rol.

Esta separación no sustituye otras separaciones de funciones de LegalAIZ.it, como especialista jurídico + QA en aprobación documental.

## Vigencia

Los límites de días definidos en la política son controles operativos internos de release. No son plazos legales, certificaciones regulatorias ni periodos de validez establecidos por una autoridad.

Una evidencia vencida deja de satisfacer el gate sin borrar su historia.

## Revocación y reemplazo

La evidencia activa no se sobreescribe. Para reemplazarla:

1. se registra un evento `REVOKED` con `reason_code`;
2. el control vuelve a `MISSING_EVIDENCE`;
3. se registra una nueva evidencia;
4. se repiten aprobación de dominio y ratificación.

El historial anterior permanece en el dossier.

## Integridad y límite criptográfico

El dossier usa una cadena SHA-256 con `previous_hash` y `event_hash`, y los archivos externos se verifican contra el SHA-256 y tamaño registrados.

Esto permite detectar alteraciones bajo el modelo de control de la aplicación y fallar cerrado ante drift o corrupción.

**No debe describirse como almacenamiento inmutable externo, WORM, blockchain ni firma digital independiente.** Un actor con control total y no auditado del filesystem podría reescribir un archivo local y recalcular hashes. Para una producción de mayor assurance, el dossier debería anclarse adicionalmente en almacenamiento inmutable, firma externa, transparencia log o sistema de auditoría independiente.

## Composición con V1-RC1

`V1RC2ReleaseAssuranceGate` no reemplaza `V1RC1ProductionReadinessGate`.

RC2 entrega al gate RC1 un `external_summary` derivado exclusivamente del dossier RC2. Por tanto:

- el registro legacy M7 por sí solo no satisface RC2;
- 10/10 controles RC2 pueden habilitar `READY_FOR_CONTROLLED_PRODUCTION_VALIDATION` si el startup RC1 también es seguro;
- aun con 10/10, el lanzamiento comercial continúa bloqueado mientras la metadata de release mantenga:
  - `REAL_PRODUCTION_AUTHORIZED=False`;
  - `REAL_PAYMENTS_AUTHORIZED=False`;
  - `SYNTHETIC_DATA_ONLY=True`.

Los flags de entorno no pueden sustituir esa metadata.

## Evidencia pública vs. interna

El dossier interno conserva rutas relativas de evidencia, hashes, actores y IDs de eventos. `summary()` expone únicamente:

- clave del control;
- PASS/FAIL;
- estado;
- conteos;
- integridad general.

No debe exponerse públicamente el contenido del dossier interno.

## Gate técnico RC2

Antes de certificar un SHA RC2 deben pasar, como mínimo:

1. `python -m compileall`;
2. suite completa del repositorio;
3. pruebas RC2 de integridad, RBAC, vigencia, revocación y separación de funciones;
4. inventario 11 productos / >=473 preguntas / >=273 reglas;
5. runtime jurídico/documental M33;
6. HTTP journey M34.2 → M37.3;
7. M33.1 public demo 8/8;
8. visual-docx portfolio completo.

Un CI verde certifica únicamente la implementación del mecanismo y la ausencia de regresiones del SHA exacto. No crea las diez evidencias reales ni sustituye pentest, load test, restore/rollback drill, incident drill, aprobación de privacidad, validación Mac/Windows o revisión jurídica/QA humana.

## Siguiente frontera

Una vez certificado RC2, el trabajo restante para V1 comercial debe distinguir:

- controles que pueden cerrarse técnicamente en repositorio;
- controles que requieren ejecución en infraestructura real;
- aprobaciones humanas y jurídicas;
- decisión explícita de modificar la metadata de release;
- proveedores de pago/comunicación reales;
- plan de rollout, rollback y observabilidad productiva.

No debe cambiarse `release_metadata` ni habilitarse un proveedor real únicamente porque RC2 esté verde.
