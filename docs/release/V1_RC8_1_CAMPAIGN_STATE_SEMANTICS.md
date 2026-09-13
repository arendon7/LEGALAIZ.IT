# LegalAIZ.it V1-RC8.1 — Campaign state semantics

## Objetivo

RC8.1 corrige una ambigüedad del read model RC8 sin alterar el ledger de evidencia, los 22 controles, las dependencias RC6, los dossiers RC2/RC7 ni la procedencia de autorización RC4.

En RC8, `campaign_state()` clasificaba toda la campaña como `BLOCKED` cuando el dossier de auditoría reportaba uno o más controles `BLOCKED_BY_DEPENDENCY`. Esa condición es normal en un plan secuenciado: una tarea posterior puede esperar a que se verifique su prerrequisito mientras la campaña sigue correctamente creada o en progreso.

## Decisión

RC8.1 separa dos conceptos:

1. **Restricción local de control**: una dependencia RC6 no satisfecha impide iniciar únicamente el control afectado. Se expone como `dependency_blocked_controls` y `dependency_constraints_active`.
2. **Bloqueo global de campaña**: se reserva para drift del plan fijado o para un `CONTROL_BLOCKED` explícito. El aborto conserva su estado terminal `ABORTED`.

Por tanto:

- campaña recién creada + dependencias pendientes => `CREATED`;
- campaña con actividad + dependencias pendientes => `IN_PROGRESS`;
- control con prerrequisito pendiente => su inicio sigue fallando cerrado;
- drift de `evidence_execution_plan.json` => `BLOCKED`;
- bloqueo operativo explícito => `BLOCKED`;
- evidencia 22/22 => `EVIDENCE_COMPLETE`, pero nunca autorización.

## Compatibilidad

RC8.1 es un overlay compatible sobre `EvidenceCampaignLedger` RC8. Conserva:

- schema y cadena hash de eventos RC8;
- `CAMPAIGN_CREATED`, `CONTROL_STARTED`, `EVIDENCE_LINKED`, `CONTROL_REVIEW_READY`, `CONTROL_BLOCKED`, `CAMPAIGN_ABORTED`;
- permisos de manager, executor y reviewer;
- fijación de SHA del plan RC6;
- SHA Git de fuente y fingerprint SHA-256 opaco del entorno;
- verificación de evidencia mediante los dossiers canónicos RC2 y RC7;
- ausencia de comandos de aprobación, ratificación, autorización o go-live;
- `release_authorized=false` y `commercial_authorized=false` en el read model.

El CLI canónico `tools/v1_evidence_campaign.py` usa el overlay RC8.1. No se añade ninguna ruta HTTP ni endpoint de activación al runtime de la aplicación.

## Regla de seguridad

Una restricción por dependencia no se degrada ni se ignora. `start_control()` mantiene la validación RC8 y rechaza el inicio mientras los prerrequisitos declarados por RC6 no estén verificados. El cambio es exclusivamente de semántica agregada: no confundir una cola secuenciada saludable con una campaña fallida.

## Criterios de aceptación

- La campaña nueva no aparece globalmente bloqueada por dependencias normales.
- La campaña iniciada permanece `IN_PROGRESS` mientras existan dependencias pendientes.
- Los controles dependientes siguen fail-closed.
- Drift y bloqueos explícitos siguen produciendo `BLOCKED`.
- Abortado sigue siendo `ABORTED`.
- `EVIDENCE_COMPLETE` no implica autorización de producción ni pagos.
- No hay endpoints runtime nuevos.
- La suite completa, smoke HTTP y QA visual deben permanecer verdes antes de certificar el SHA.
