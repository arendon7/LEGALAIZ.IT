# Historial de workflows especializados

La validación operativa vigente se define exclusivamente en:

- `.github/workflows/ci.yml`
- `.github/workflows/pages.yml`

Las definiciones especializadas de M32.2 a M32.9 fueron retiradas del árbol actual para evitar duplicación, colas masivas y ejecuciones en conflicto.

Su contenido continúa disponible de forma íntegra y trazable en:

- el historial de Git;
- los PR #5 a #13;
- los commits y artefactos citados en cada PR.

No deben restaurarse como workflows automáticos independientes. Cualquier compuerta especializada nueva debe incorporarse a la CI consolidada o ejecutarse localmente mediante sus scripts y pruebas.
