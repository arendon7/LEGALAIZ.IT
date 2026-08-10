# LegalAIZ.it · contexto operativo para ChatGPT

Este archivo es el punto de entrada corto para retomar el proyecto sin reconstruir toda la historia.

## Regla de lectura
1. Leer `project-memory/00_INDEX.md`.
2. Leer `project-memory/01_STATE/CURRENT.md`.
3. Si existe `graphify-out/GRAPH_REPORT.md`, usarlo para orientación arquitectónica antes de abrir archivos fuente.
4. Consultar únicamente los archivos directamente relacionados con la tarea activa.
5. Antes de cerrar una iteración, actualizar el estado, decisiones y handoff correspondientes.

## Fuentes de verdad
- Código y configuración: GitHub, rama/commit expresamente identificados.
- Estado humano y decisiones: `project-memory/`.
- Mapa estructural del repositorio: `graphify-out/`.
- Evidencia de CI: GitHub Actions y artifacts del SHA exacto.

## Regla de no regresión
No reducir ni sustituir las capacidades canónicas de LegalAIZ.it. Las modificaciones deben preservar RBAC, trazabilidad, revisiones inmutables, aprobación dual, Fábrica Documental, Studio Jurídico y los productos jurídicos existentes salvo instrucción expresa.

## Estado jurídico-documental activo al crear esta capa
- `main`: `0d21173e760808168db3ab557fc3bc59e27f1d2a` (M33.1).
- PR activo: `#17` — `M33.0 — estándar documental jurídico transversal`.
- HEAD certificado del PR #17: `53ee3a93e704ebf46131354791efd6276b9f3130`.
- Workflow certificado: run `31425275721`, conclusión `success`.
- Evidencia: 415/415 pruebas, 53/53 DOCX M33 y auditoría visual sin hallazgos reportados por ese run.
- PR #17 continúa `draft`; no debe confundirse certificación técnica con liberación jurídica.
