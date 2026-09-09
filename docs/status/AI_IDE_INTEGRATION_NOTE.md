# Integración futura con IDE y agentes locales

La integración futura con Visual Studio Code u otros entornos/agentes deberá consumir contratos del AI Gateway y herramientas de prueba, no conectarse directamente a secretos, bases de datos o flujos internos.

Objetivos futuros:
- ejecutar suites y benchmarks M40 desde el IDE;
- probar proveedores/modelos con fixtures controlados;
- inspeccionar trazas y diffs sin exponer payload sensible;
- permitir robots de desarrollo/QA con permisos acotados;
- conservar GitHub/CI y los gates de LegalAIZ.it como fuente de verdad.

Esta integración se abordará después de estabilizar M40.0–M40.4.
