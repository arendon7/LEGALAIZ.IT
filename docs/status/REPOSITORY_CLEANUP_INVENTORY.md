# LegalAIZ.it — Inventario de limpieza M39.2

Última auditoría: 2026-09-09
Estado: **CONSOLIDADO PARA CERTIFICACIÓN EXACT-HEAD**
SHA base de la auditoría de árbol: `32239dd1ad1aefd03a893768205cf46ffaea50e9`.

Este inventario gobierna la limpieza de M39.2. La evidencia ejecutable y los gates de CI tienen precedencia sobre descripciones manuales. Ninguna clasificación autoriza por sí sola una eliminación funcional.

## 1. Principio de conservación

La antigüedad del nombre, el sufijo de versión o la existencia de una implementación posterior no bastan para retirar un archivo. Un componente permanece mientras exista una dependencia material de runtime, compatibilidad, datos, documentos, pruebas, CI, migración, release o auditoría.

## 2. Clasificación verificada

| Categoría | Estado M39.2 | Decisión |
|---|---|---|
| A. Runtime activo | Preservado | No retirar handlers, módulos, datos, plantillas, assets ni contratos cargados por la línea certificada. |
| B. Compatibilidad histórica | Preservada | Los tests y módulos versionados no se consideran deuda únicamente por su nombre; pueden materializar regresión, alias, fallback o compatibilidad. |
| C. Tooling / QA / CI | Preservado | `ci.yml`, `pages.yml`, smoke tests, generadores, auditorías y gates documentales permanecen mientras participen en certificación o evidencia. |
| D. Documentación histórica | Preservada cuando aporta trazabilidad | Puede consolidarse documentación operativa redundante, pero no se elimina evidencia material de decisiones o releases. |
| E. Candidatos de retiro M39.2 | Sólo documentación redundante creada en esta iteración | Se aprueba consolidar su contenido en los cuatro documentos vivos y retirar los archivos auxiliares listados en §5. |

No hay en esta auditoría un candidato de runtime, template, migración, fuente jurídica, test o herramienta aprobado para eliminación.

## 3. Residuos técnicos buscados en el árbol auditado

En el árbol tracked del SHA indicado no se encontraron coincidencias para:

- `.DS_Store`;
- `__pycache__`;
- `.pyc`;
- `.orig`;
- `.rej`;
- `.zip`;
- `node_modules`.

Esto evita confundir limpieza real con una eliminación cosmética inexistente.

`.gitignore` ya previene, entre otros, caches Python, entornos locales, `.env`, secretos/certificados, runtime y datos locales, artefactos generados, logs, SQLite/DB, `node_modules`, builds, ZIP, backups, `.orig`, `.rej`, temporales, `.vscode`, `.idea` y `.DS_Store`.

## 4. Prueba negativa obligatoria para futuras eliminaciones funcionales

Un archivo sólo puede clasificarse como retirado si se demuestra simultáneamente, según aplique:

1. cero referencias desde `run.py`, handlers o runtime activo;
2. cero imports Python/JS y cero carga desde HTML/CSS/JS;
3. cero referencias desde tests, tools y CI activos;
4. cero dependencia de migraciones, datos o compatibilidad;
5. cero uso en Fábrica Documental, plantillas, bloques o generación de evidencia;
6. cero función de release, auditoría o trazabilidad;
7. reemplazo canónico identificado cuando corresponda.

Si una de estas comprobaciones es positiva o incierta, el archivo permanece.

## 5. Consolidación documental aprobada en M39.2

El contenido material de los siguientes documentos auxiliares fue revisado y debe quedar absorbido por `CURRENT_STATE.md`, este inventario, `PRODUCT_ROADMAP.md` y `AI_COPILOT_ROADMAP.md`:

- `docs/status/REPOSITORY_CLEANUP_POLICY.md`;
- `docs/status/M39_2_SCOPE.md`;
- `docs/status/M40_ENTRY_CRITERIA.md`;
- `docs/status/CONVERGENCE_CHECKLIST.md`;
- `docs/status/README.md`;
- `docs/status/AI_IDE_INTEGRATION_NOTE.md`;
- `docs/status/AUDIT_METHOD.md`;
- `docs/status/CLEANUP_DECISION_LOG.md`;
- `docs/status/CLEANUP_GATES.md`;
- `docs/status/CANONICAL_BRANCH_NOTE.md`;
- `docs/status/NON_GOALS_M39_2.md`;
- `docs/status/EXECUTION_ORDER.md`.

La eliminación de estos archivos reduce fragmentación documental; no altera runtime, seguridad, documentos jurídicos ni cobertura de pruebas.

## 6. Gate para cualquier retiro posterior

1. identificar candidato concreto;
2. ejecutar y documentar búsquedas de dependencias directas e indirectas;
3. identificar reemplazo o razón de obsolescencia;
4. hacer la retirada en un cambio aislable;
5. ejecutar compile/test/smoke y QA visual DOCX aplicables;
6. revertir ante cualquier regresión.

## 7. Prohibiciones vigentes

- borrar en masa por patrón de versión;
- eliminar compatibilidad que el runtime o las pruebas certificadas todavía exijan;
- mezclar poda funcional con M40;
- retirar evidencia, fuentes, controles de auditoría o aprobación para reducir tamaño;
- afirmar que un artefacto está obsoleto sin evidencia de dependencia negativa.

## 8. Pendiente para cerrar M39.2

Tras consolidar los documentos auxiliares debe fijarse el nuevo SHA exacto y ejecutar sobre ese candidato:

- CI completo;
- smoke HTTP aplicable;
- gate de integridad/generación documental;
- QA visual DOCX;
- revisión del diff final contra M39.1;
- definición de la convergencia certificada hacia `main`.
