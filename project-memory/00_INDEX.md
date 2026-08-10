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
- [[03_SESSIONS/2026-08-10-m33-3-workflow|Handoff M33.3 / workflow 31425275721]]
- [[04_RUNBOOKS/CHATGPT_GITHUB|Runbook ChatGPT + GitHub]]

## Convención
Cada nota debe incluir metadatos `project`, `type`, `status`, `date` y, cuando aplique, `related`, `sha`, `pr`, `workflow_run`.

Estados recomendados: `active`, `approved`, `pending`, `superseded`, `blocked`, `closed`.

## Separación de responsabilidades
- `project-memory/`: decisiones, estado, sesiones, riesgos y continuidad humana.
- `graphify-out/`: mapa generado del código; nunca sustituye el estado jurídico ni las decisiones aprobadas.
- GitHub Actions: evidencia ejecutable asociada a un SHA.
- Artifacts: evidencia pesada o temporal; no constituyen por sí solos fuente canónica permanente.
