# Documentación de LegalAIZ.it

## Documento vigente

La línea base canónica es **M32.9**. Para conocer el estado actual deben consultarse, en este orden:

1. `../VERSION`.
2. `../README.md`.
3. `../FINAL_RELEASE_NOTES.md`.
4. `ITERACION_M32_9_GOBIERNO_CONTACTO.md`.
5. Código, pruebas y configuración de `main`.

## Documentos históricos

Los archivos `ITERACION_M32_0_*` a `ITERACION_M32_8_*`, sus matrices y revisiones asociadas documentan decisiones ya incorporadas. Se conservan por trazabilidad técnica, pero no constituyen versiones instalables ni fuentes de verdad independientes.

Ante cualquier contradicción, prevalece la implementación vigente en `main`, seguida por la documentación canónica indicada arriba.

## Reglas de mantenimiento

- No crear carpetas completas por cada versión dentro del repositorio.
- No copiar aplicaciones, fábricas o plantillas con sufijos `old`, `backup`, `copy`, `final2` o equivalentes.
- Evolucionar los módulos compatibles sobre la línea base vigente.
- Conservar el historial mediante Git, PR y pruebas, no mediante duplicados en el árbol.
- Actualizar `VERSION`, `README.md` y `FINAL_RELEASE_NOTES.md` cuando cambie la línea base.
- No declarar aprobaciones, entregas o pruebas que no tengan evidencia verificable.
