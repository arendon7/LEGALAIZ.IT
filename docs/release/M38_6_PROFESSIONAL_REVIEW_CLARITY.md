# M38.6 — Claridad de revisión profesional

## Objetivo

Mejorar la jerarquía cognitiva de la Mesa Jurídica sin modificar la lógica de aprobación, liberación, trazabilidad ni operación existente.

La mejora separa dos planos que antes aparecían mezclados:

1. **Decisión profesional**: qué debe revisar, decidir o resolver el especialista o QA.
2. **Evidencia técnica**: revisión inmutable, hallazgos, aprobaciones, huella SHA-256 y cadena de auditoría.

La evidencia técnica no se oculta ni se sustituye; simplemente deja de ser el primer mensaje de la interfaz.

## Cambios

- La bandeja profesional abre con lenguaje de revisión por documento, no con numeración interna de módulo.
- Cada documento muestra una señal determinista según su estado: siguiente control, decisión pendiente, bloqueo, liberación o estado de entrega.
- La vista de detalle mantiene visible la revisión, SHA-256, auditoría, hallazgos y aprobación dual.
- Los textos de M32.6 que podían confundirse con términos jurídicos se presentan como **objetivos internos de gestión**.
- La interfaz declara expresamente que esos tiempos no calculan prescripción, caducidad, términos procesales ni términos administrativos aplicables.
- Los labels de formularios se modifican sobre su nodo de texto, preservando `input`, `select` y demás controles hijos.
- La capa es responsive e idempotente frente a rerenders de M32.5/M32.6.

## Límites deliberados

M38.6 no:

- llama APIs ni crea nuevos endpoints;
- modifica `state`;
- aprueba, rechaza o libera documentos;
- cambia RBAC o capacidades;
- cambia hashes, revisiones, hallazgos o eventos;
- calcula riesgo jurídico, urgencia jurídica o vencimientos legales;
- sustituye la verificación profesional de términos aplicables;
- modifica la fuente de verdad M32.5/M32.6.

## Estados y señal profesional

| Estado | Señal principal |
| --- | --- |
| `draft` | Preparar la revisión |
| `legal_pending` | Revisión jurídica pendiente |
| `qa_pending` | Control QA independiente |
| `changes_required` | Ajustes requeridos bloquean aprobación |
| `findings_pending` | Hallazgos abiertos bloquean aprobación |
| `audit_invalid` | Integridad de auditoría bloquea liberación |
| `ready_to_release` | Verificar huella y liberar revisión aprobada |
| `released` | Documento liberado y vinculado al hash aprobado |
| `rejected` | Revisar rechazo y generar/seleccionar nueva revisión |

## Criterios de aceptación

1. Especialista y admin reciben la capa sólo en `/mesa-juridica`.
2. Cliente no recibe esta capa.
3. No existe canal de red o storage en M38.6.
4. No existe mutación de `state`.
5. No existe acción automática de approve/reject/release.
6. SHA-256, revisiones, hallazgos y auditoría permanecen visibles.
7. Los SLA se presentan como tiempos/objetivos internos.
8. Se advierte que los tiempos internos no equivalen a términos legales.
9. Los controles de formularios sobreviven a los cambios de copy.
10. La capa es idempotente y responsive.
11. Suite completa, smoke HTTP y QA visual deben permanecer en verde antes de certificar el SHA.
