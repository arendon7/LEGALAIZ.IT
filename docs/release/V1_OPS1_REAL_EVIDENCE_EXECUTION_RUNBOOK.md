# LegalAIZ.it V1-OPS1 — Runbook de ejecución de evidencia real

## 1. Cambio de fase

RC6–RC10 dejaron resuelta la arquitectura de assurance: inventario de 22 controles, separación de evidencia y autorización, campañas append-only, dossiers canónicos, audit pack redactado y bundle de custodia verificable.

A partir de OPS1 el cuello de botella ya no es otro wrapper automático. Es **ejecución humana y externa**.

OPS1 convierte el plan RC6 y los `task_packet()` RC8.1 en una vista operativa única, ordenada por dependencias, sin copiar ni redefinir la política.

## 2. Qué genera

`python tools/v1_evidence_execution_runbook.py show --format markdown`

muestra el runbook completo.

`python tools/v1_evidence_execution_runbook.py write --output-dir <directorio>`

genera:

- `v1-real-evidence-runbook.json`
- `v1-real-evidence-runbook.md`

Ambos son **derivados**. No son evidencia y no cambian ningún estado.

## 3. Fuente de verdad

OPS1 no contiene un segundo catálogo de controles.

Lee directamente:

1. `config/v1/evidence_execution_plan.json` — RC6;
2. `EvidenceCampaignLedger.task_packet()` — RC8.1.

Por tanto conserva automáticamente para cada uno de los 22 controles:

- framework y referencia canónica;
- dominio;
- entorno;
- alcance de release;
- rol ejecutor;
- rol revisor independiente;
- dependencias;
- tipo de bundle;
- artefactos obligatorios;
- vigencia máxima;
- política de redacción;
- checklist del operador.

## 4. Olas de ejecución

OPS1 calcula un orden topológico a partir de las dependencias RC6.

Regla:

> Un control dependiente nunca aparece en la misma ola ni en una ola anterior a su prerequisito.

Esto evita que el equipo intente, por ejemplo, certificar un restore/rollback que depende de una certificación previa todavía no verificada.

Las olas son una herramienta de coordinación; **no implican que controles de una misma ola deban ejecutarse simultáneamente**.

## 5. Flujo operativo

1. Congelar la revisión Git que se pretende validar.
2. Definir el entorno real `production_prelaunch` o `staging_equivalent` aplicable.
3. Calcular externamente un fingerprint SHA-256 opaco del entorno sin publicar secretos.
4. Crear la campaña RC8.1 con un actor autorizado de gobierno.
5. Asignar personas reales a cada rol ejecutor/revisor. Los roles están definidos en RC6; las personas no se inventan en el runbook.
6. Empezar por la primera ola.
7. Antes de cada control, consultar su task packet canónico.
8. Registrar `start-control` únicamente como evento de coordinación.
9. Ejecutar materialmente la prueba o revisión fuera de la CLI.
10. Capturar exactamente los artefactos exigidos por RC6.
11. Redactar PII, secretos, credenciales, rutas privadas y detalles explotables conforme al packet.
12. Construir el manifest de integridad con hashes y tamaños reales.
13. Registrar la evidencia en el dossier canónico RC2 o RC7 según corresponda.
14. Vincular a campaña únicamente una evidencia que ya exista en el dossier canónico.
15. Completar la revisión independiente y, cuando corresponda, ratificación.
16. Sólo cuando las dependencias estén `VERIFIED`, avanzar a controles dependientes.
17. Repetir hasta cubrir 22/22 controles vigentes.
18. Generar RC9 Evidence Audit Pack.
19. Generar RC10 Custody Export y anclar externamente su `envelope_sha256` cuando se requiera trazabilidad posterior.
20. Tramitar por separado la decisión humana versionada de producción.
21. Tramitar por separado la decisión humana versionada de pagos/comercialización.

## 6. Lo que OPS1 no hace

OPS1 no:

- ejecuta pruebas de infraestructura;
- hace pentest;
- valida TLS real;
- prueba restauraciones reales;
- prueba Mac o Windows físicamente;
- registra evidencia;
- asigna personas;
- aprueba revisiones;
- ratifica dossiers;
- firma artefactos;
- altera una campaña;
- altera release metadata;
- autoriza producción;
- autoriza pagos.

## 7. Roles y separación de funciones

El runbook conserva los roles definidos en RC6, pero marca cada control como:

`ROLE_DEFINED_PERSON_NOT_ASSIGNED`

hasta que el equipo identifique a las personas reales.

La separación ejecutor/revisor permanece obligatoria. Si el plan pierde esa separación, RC6 ya falla estructuralmente y OPS1 no se construye.

## 8. Evidencia mínima

Cada control conserva su lista exacta de artefactos obligatorios. Todos exigen un `sha256_manifest`.

OPS1 no permite sustituir artefactos por equivalencias inferidas. Cualquier migración o equivalencia entre controles sigue requiriendo una política versionada explícita.

## 9. Seguridad de información

El runbook no expone:

- `evidence_ref`;
- `evidence_event_id`;
- actor IDs;
- fingerprint del entorno;
- secretos;
- API keys;
- credenciales;
- private keys;
- contenido de evidencia.

Los comandos incluidos son plantillas con placeholders (`<CAMPAIGN_ID>`, `<EXECUTOR_ID>`), nunca valores reales.

## 10. Criterios de aceptación OPS1

1. 22/22 controles canónicos aparecen exactamente una vez.
2. La matriz coincide con RC6 y los packets RC8.1.
3. Las dependencias siempre quedan en olas anteriores.
4. Ejecutores y revisores permanecen separados.
5. Todos los controles empiezan `PENDING_EXTERNAL_EXECUTION`.
6. Ninguna persona se asigna automáticamente.
7. No se incluyen referencias o contenido de evidencia.
8. El build es determinista.
9. Construir el runbook no crea ni modifica el ledger de campaña.
10. La salida Markdown contiene los 22 controles y su checklist.
11. El release gate sigue en RC9; OPS1 no se conecta a `release_readiness`.
12. No se añade endpoint HTTP.
13. Suite completa, smokes y QA visual deben permanecer verdes antes de certificar el incremento.

## 11. Estado esperado después de OPS1

Con OPS1 certificado, el repositorio queda listo para **operar** la campaña de evidence assurance sin seguir agregando abstracciones de software.

El próximo cambio legítimo de estado no es `RC_CODE_READY` —eso ya está cubierto— sino la aparición de evidencia externa auténtica, vigente, revisada y ratificada.

Hasta entonces deben permanecer deliberadamente:

- `REAL_PRODUCTION_BLOCKED`;
- `COMMERCIAL_V1_BLOCKED`.
