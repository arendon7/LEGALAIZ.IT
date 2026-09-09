# LegalAIZ.it — Product Roadmap

## Fase actual — M39.2: Canonical Release Convergence & Repository Cleanup

### Objetivo
Establecer una base única, limpia, auditable y certificada antes de introducir la capa M40 de IA avanzada, sin reducir capacidades funcionales, jurídicas, documentales, de seguridad o de QA ya acumuladas.

### Secuencia de cierre M39.2
1. congelar M39.1 como base verificable;
2. documentar fuente canónica y pila M38/M39;
3. auditar residuos y dependencias con criterio conservador;
4. consolidar documentación de gobernanza redundante;
5. retirar únicamente candidatos demostrados;
6. fijar SHA exacto M39.2;
7. ejecutar CI, smoke e integridad sobre ese SHA;
8. ejecutar QA visual DOCX sobre ese SHA;
9. converger la pila certificada hacia `main`;
10. cerrar PR apilados supersedidos sólo después de preservar la historia y comprobar la convergencia.

### Criterios de salida
M39.2 sólo termina cuando:
- el estado canónico está documentado y coincide con GitHub;
- M38.9–M38.11 no se presentan como remotos/canónicos sin evidencia;
- el inventario distingue runtime, compatibilidad, tooling, documentación y candidatos;
- cualquier retiro cumple prueba negativa de dependencia;
- el diff final contra M39.1 es mínimo y explicable;
- CI + smoke + gates de integridad están verdes en el SHA exacto;
- el gate visual DOCX está verde en el mismo SHA;
- existe ruta explícita de convergencia a `main`.

### No-goals
M39.2 no es un rediseño de arquitectura, una reescritura de contratos certificados, una poda masiva por versión ni una activación de pagos, comunicaciones o producción comercial. Tampoco introduce llamadas reales a LLM: esa responsabilidad empieza en M40.0.

## M40 — Legal AI Copilot

### Objetivo
Convertir las capacidades inteligentes existentes en copilotos contextuales, trazables y supervisados que acompañen al usuario y al profesional jurídico sin sustituir controles deterministas, hechos confirmados, fuentes, revisión humana ni aprobación dual.

La secuencia técnica y los invariantes están definidos en `AI_COPILOT_ROADMAP.md`.

## Piloto controlado

Sólo después del hardening M40 y de los gates externos de producción vigentes:
- cohorte acotada;
- métricas de error, escalamiento, satisfacción, latencia y costo;
- revisión humana obligatoria donde corresponda;
- rollback y auditoría disponibles;
- ninguna afirmación de producción comercial sin evidencia de pagos, comunicaciones y operación real certificados.

## Política de producto

Cada incremento debe evaluarse simultáneamente en cinco dimensiones:
1. utilidad jurídica;
2. precisión y trazabilidad;
3. experiencia de usuario;
4. seguridad y aislamiento;
5. auditabilidad y capacidad de revisión.

Un cambio que mejora una dimensión degradando materialmente otra no se considera terminado hasta corregir la regresión o documentar y aprobar expresamente el trade-off.
