# LegalAIZ.it — Política de limpieza del repositorio

## Principio
La antigüedad del nombre o de la versión no basta para eliminar un archivo. La limpieza es conservadora y basada en dependencias.

## Clasificación

### A. Runtime activo
No retirar. Incluye handlers, módulos, datos, plantillas y activos cargados por la versión vigente.

### B. Compatibilidad histórica
Conservar mientras exista import, alias, migración, fallback, prueba de regresión o contrato de compatibilidad.

### C. Tooling y QA
Conservar si participa en CI, generación de evidencia, smoke, benchmarks, release gates o auditoría.

### D. Documentación histórica
Puede archivarse cuando no sea canónica ni consumida por tooling. Debe mantenerse la trazabilidad de decisiones materiales.

### E. Candidato a retiro
Sólo retirar si se demuestra simultáneamente:
- cero imports/referencias runtime;
- cero referencias desde tests y CI activos;
- cero dependencia de migraciones o datos;
- cero uso en fábrica documental/plantillas;
- cero uso en release/auditoría;
- reemplazo canónico identificado cuando corresponda.

## Proceso de retiro
1. identificar candidato;
2. buscar referencias directas e indirectas;
3. documentar reemplazo o razón de obsolescencia;
4. retirar en cambio aislado;
5. ejecutar compile/test/smoke/QA visual aplicables;
6. revertir si aparece regresión.

## Prohibiciones
- borrar en masa por patrón de versión;
- eliminar clases históricas si el runtime o pruebas certificadas exigen compatibilidad;
- mezclar limpieza destructiva con cambios funcionales de M40;
- remover evidencia o controles de auditoría para reducir tamaño del repositorio.
