# LegalAIZ.it — Estado canónico

> Documento vivo. No sustituye los gates de CI, las decisiones humanas de release ni los artefactos de auditoría.

## Estado de referencia

- Línea funcional más avanzada: M39.1.
- SHA base de esta iteración: `c1a34283f27a55f025da3c56db2666f92cfedce8`.
- M39.1 incorpora tenancy empresarial con organizaciones, membresías, roles por organización y resolución de contexto fail-closed.
- La cadena previa preserva el journey M34–M37, la experiencia M38, la fábrica documental y la aprobación dual.
- `main` no debe considerarse equivalente al último candidato funcional hasta culminar la convergencia de la pila de PR.

## Piso funcional que no puede reducirse

- 11 productos jurídicos activos.
- Formularios, reglas y contratos canónicos vigentes.
- Fábrica documental y composición jurídica madura.
- Generación DOCX, controles OOXML/interoperabilidad y QA visual.
- Revisiones inmutables, comparación, trazabilidad y aprobación dual Legal + QA.
- Intake inteligente, extracción de hechos, confirmación, preguntas adaptativas y recomendación controlada.
- Checkout/case handoff controlado, revisión profesional, entrega y seguimiento.
- RBAC, aislamiento entre clientes/expedientes y controles fail-closed.

## Estado de producción

El código puede estar certificado como candidato técnico sin que ello autorice automáticamente:

- uso jurídico real con clientes;
- pagos reales;
- comunicaciones externas reales;
- producción comercial.

La autorización de producción depende de los gates de release y evidencia externa vigentes.

## Próxima línea

1. M39.2 — Canonical Release Convergence & Repository Cleanup.
2. M40.0 — AI Governance & Provider Gateway.
3. M40.1–M40.9 — Legal AI Copilot.

## Regla de limpieza

No eliminar archivos por antigüedad nominal. Un archivo sólo puede retirarse cuando se demuestre que no participa en runtime, imports, pruebas, migraciones, manifiestos, generación documental, compatibilidad o auditoría histórica.
