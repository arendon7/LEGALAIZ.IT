# LegalAIZ.it V1-OPS2 — Mesa operativa de evidencia real

## 1. Propósito

OPS1 convirtió los 22 controles canónicos de RC6/RC8.1 en un runbook humano ordenado por dependencias.

OPS2 añade una **vista operativa read-only** sobre ese runbook. Su función es responder, sin reinterpretar la política:

- qué controles requieren primero una campaña;
- cuáles pueden ejecutarse materialmente;
- cuáles esperan prerequisitos;
- cuáles ya tienen coordinación iniciada;
- cuáles tienen evidencia vinculada;
- cuáles esperan revisión o ratificación;
- cuáles están verificados;
- cuáles requieren remediación por expiración, integridad o bloqueo.

No crea una nueva fuente de verdad.

## 2. Fuentes de verdad

La mesa lee:

1. OPS1 `EvidenceExecutionRunbook`;
2. RC8.1 `EvidenceCampaignLedger`;
3. RC8 `EvidenceAuditDossier`;
4. RC6 `evidence_execution_plan.json` de forma transitiva.

No introduce catálogo, equivalencias ni estados persistidos propios.

## 3. Modos

### TEMPLATE

Sin `--campaign`.

Los controles raíz se muestran como `CAMPAIGN_REQUIRED` y los dependientes como `WAITING_FOR_DEPENDENCY`, salvo que ya exista evidencia canónica verificada.

Este modo sirve para preparar la operación sin inventar una campaña.

### CAMPAIGN_BOUND

Con `--campaign <CAMPAIGN_ID>`.

La mesa verifica primero la cadena RC8.1. Si está alterada, falla cerrado.

Después deriva el estado operativo de cada control sin publicar:

- actor IDs;
- fingerprint del entorno;
- `evidence_event_id`;
- `evidence_ref`;
- rutas de evidencia;
- contenido probatorio;
- credenciales o secretos.

## 4. Estados operativos

- `CAMPAIGN_REQUIRED`
- `READY_TO_EXECUTE`
- `EXECUTION_COORDINATION_STARTED`
- `EVIDENCE_LINKED`
- `REVIEW_REQUIRED`
- `REVIEW_COORDINATION_READY`
- `RATIFICATION_REQUIRED`
- `WAITING_FOR_DEPENDENCY`
- `VERIFIED`
- `CONTROL_BLOCKED`
- `PLAN_DRIFT`
- `EVIDENCE_EXPIRED`
- `INTEGRITY_FAILURE`
- `CAMPAIGN_ABORTED`

Son estados de **trabajo**, no nuevas decisiones jurídicas ni de release.

`CONTROL_REVIEW_READY` continúa siendo sólo coordinación: nunca se presenta como aprobación.

## 5. CLI

Vista Markdown:

`python tools/v1_evidence_execution_board.py show`

Vista JSON:

`python tools/v1_evidence_execution_board.py show --format json`

Campaña concreta:

`python tools/v1_evidence_execution_board.py show --campaign <CAMPAIGN_ID>`

Exportación derivada:

`python tools/v1_evidence_execution_board.py write --campaign <CAMPAIGN_ID> --output-dir <directorio>`

La exportación sólo escribe JSON/Markdown en el directorio indicado. No escribe en el ledger.

## 6. Siguiente acción

Cada control expone un `next_action` derivado:

- crear campaña;
- ejecutar control externo;
- completar bundle;
- completar revisión;
- completar ratificación;
- esperar prerequisito;
- resolver bloqueo;
- remediar evidencia;
- no realizar más ejecución si la campaña está abortada.

Cuando la acción depende de ejecución o revisión, OPS2 muestra **el rol**, nunca una persona.

OPS2 no asigna ejecutores ni revisores.

## 7. Seguridad

La salida está diseñada para poder circular como herramienta interna de coordinación con un nivel de exposición menor que los dossiers.

No contiene:

- identificadores de actores;
- fingerprint del entorno;
- referencias internas de evidencia;
- payloads de evidencia;
- reason codes del ledger;
- hashes internos de eventos;
- secretos.

El `campaign_id` puede aparecer porque identifica la campaña operativa que se está consultando; no es una credencial ni una referencia de evidencia.

## 8. Integridad

Antes de leer una campaña, OPS2 ejecuta `verify_chain()` sobre RC8.1.

Una cadena alterada no genera un tablero parcial o aparentemente verde: genera error.

La mesa misma tiene `board_sha256` determinista sobre su contenido redactado.

Ese digest demuestra identidad del snapshot, **no firma, no no-repudio y no autorización**.

## 9. No mutación

OPS2 no:

- crea campañas;
- inicia controles;
- vincula evidencia;
- marca review-ready;
- bloquea controles;
- aborta campañas;
- registra evidencia;
- aprueba revisiones;
- ratifica dossiers;
- modifica release metadata;
- modifica RC9 o RC10;
- autoriza producción;
- autoriza pagos.

No se añade endpoint HTTP.

## 10. Relación con readiness

El release readiness continúa en RC9.

OPS2 es deliberadamente externo al gate de code readiness para evitar que una herramienta de coordinación se convierta en una nueva condición automática de go-live.

Incluso con 22/22 controles `VERIFIED`, siguen siendo necesarias, por separado, las decisiones humanas versionadas aplicables a:

- producción real;
- pagos/comercialización real.

## 11. Criterios de aceptación

1. 22 controles aparecen exactamente una vez.
2. La estructura de olas coincide con OPS1.
3. Plantilla limpia distingue campaña requerida de dependencias.
4. Una campaña creada habilita sólo controles con prerequisitos satisfechos.
5. `CONTROL_STARTED` nunca se presenta como ejecución terminada.
6. `EVIDENCE_LINKED` nunca se presenta como aprobación.
7. Review-ready nunca se presenta como aprobación.
8. Bloqueo explícito se ve sin exponer actor ni reason code.
9. Abortado es terminal.
10. Tampering del ledger falla cerrado.
11. No aparecen claves internas prohibidas.
12. El build es determinista.
13. Construir/mostrar/exportar no cambia el ledger.
14. La CLI contiene sólo `show` y `write`.
15. `run.py` no incorpora OPS2.
16. `v1_release_readiness_audit.py` continúa apuntando a RC9.
17. Suite completa, smokes y QA visual permanecen verdes antes de certificar.
