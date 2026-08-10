---
project: LegalAIZ.it
type: index
status: active
date: 2026-08-10
---

# LegalAIZ.it · Project Memory

Vault Obsidian compatible y memoria operativa curada del proyecto.

## Abrir primero
- [[01_STATE/CURRENT|Estado actual]]
- [[02_DECISIONS/ADR-0001-graphify-obsidian|Decisión Graphify + Obsidian]]
- [[04_RUNBOOKS/CHATGPT_GITHUB|Runbook ChatGPT + GitHub]]

## Snapshot estructural generado
La arquitectura regenerable vive fuera de `main`, en la rama `context/graphify-snapshot`:
- `graphify-out/CHATGPT_GRAPH_INDEX.md` — índice compacto;
- `project-memory/01_STATE/GRAPHIFY.md` — SHA y metadatos del snapshot;
- artifact `graphify-context-<sha>` — grafo completo y vault Obsidian generado.

## Convención
Cada nota debe incluir metadatos `project`, `type`, `status`, `date` y, cuando aplique, `related`, `sha`, `pr`, `workflow_run`.

Estados recomendados: `active`, `approved`, `pending`, `superseded`, `blocked`, `closed`.

## Separación de responsabilidades
- `project-memory/`: decisiones, estado, sesiones, riesgos y continuidad humana.
- `context/graphify-snapshot`: orientación estructural regenerable.
- GitHub Actions: evidencia ejecutable asociada a un SHA.
- Artifacts: evidencia pesada o temporal; no constituyen por sí solos fuente canónica permanente.
