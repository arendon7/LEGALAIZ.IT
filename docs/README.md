# Documentación de LegalAIZ.it

## Documento vigente

La línea base canónica es **M33.1**. Para conocer el estado actual deben consultarse, en este orden:

1. `../VERSION`.
2. `../README.md`.
3. `../FINAL_RELEASE_NOTES.md`.
4. `DESPLIEGUE_M33.md` para operación de la demostración pública.
5. Código, pruebas y configuración de `main`.

M33.1 conserva las capacidades jurídicas, documentales, operativas y de seguridad acumuladas hasta M33.0/M32.9 y añade endurecimiento del despliegue público demostrativo.

## Documentos históricos

Los archivos de iteraciones M32 y anteriores, sus matrices y revisiones asociadas documentan decisiones ya incorporadas. Se conservan por trazabilidad técnica, pero no constituyen versiones instalables ni fuentes de verdad independientes.

Ante cualquier contradicción, prevalece la implementación vigente en `main`, seguida por la documentación canónica indicada arriba.

## Reglas de mantenimiento

- No crear carpetas completas por cada versión dentro del repositorio.
- No copiar aplicaciones, fábricas o plantillas con sufijos `old`, `backup`, `copy`, `final2` o equivalentes.
- Evolucionar los módulos compatibles sobre la línea base vigente.
- Conservar el historial mediante Git, PR y pruebas, no mediante duplicados en el árbol.
- Actualizar `VERSION`, `README.md`, `FINAL_RELEASE_NOTES.md` y el runbook de despliegue cuando cambie la línea base.
- No versionar contraseñas, llaves, tokens ni secretos de despliegue.
- No declarar aprobaciones, entregas o pruebas que no tengan evidencia verificable.
