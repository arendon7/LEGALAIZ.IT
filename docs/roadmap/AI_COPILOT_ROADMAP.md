# LegalAIZ.it — Roadmap M40 Legal AI Copilot

## Objetivo
Integrar inteligencia artificial conversacional y documental sin debilitar la trazabilidad, la confirmación de hechos, el aislamiento, la revisión humana ni la aprobación dual existentes.

## M40.0 — AI Governance & Provider Gateway
- gateway único de proveedores/modelos;
- políticas por rol, organización, expediente y documento;
- construcción de contexto mínimo autorizado;
- structured outputs validados;
- auditoría de modelo, versión de prompt, fuentes, hashes y acciones;
- presupuestos y límites de consumo;
- ninguna salida de IA equivale a aprobación jurídica.

## M40.1 — Copiloto de orientación
- conversación inicial;
- extracción de hechos candidata;
- confirmación/disputa;
- preguntas adaptativas;
- explicación de la ruta sugerida.

## M40.2 — Copiloto del expediente
- resumen trazable;
- faltantes y contradicciones;
- cronología;
- riesgos y próximos pasos;
- preguntas sobre documentos y tareas dentro del tenant autorizado.

## M40.3 — Copiloto documental
- explicar cláusulas;
- detectar inconsistencias;
- proponer redacción alternativa;
- comparar hechos del expediente contra el documento;
- generar revisión hija, nunca sobrescribir una revisión aprobada.

## M40.4 — Copiloto profesional
- revisión 360 para especialista;
- inconsistencias, fuentes, hechos sin soporte, cláusulas ausentes y alertas;
- propuestas de corrección sometidas a revisión humana.

## M40.5 — RAG jurídico
- fuentes oficiales priorizadas;
- autoridad, norma, artículo, fecha de consulta, vigencia y localizador;
- separación entre norma, interpretación, hecho, riesgo y recomendación;
- fail-closed ante fuente insuficiente o desactualizada.

## M40.6 — Orquestación especializada
- Intake Agent;
- Fact Agent;
- Legal Research Agent;
- Document Agent;
- Risk Agent;
- QA Agent;
- Case Agent.

Los agentes no pueden saltarse RBAC, confirmación de hechos, gates documentales ni aprobación humana.

## M40.7 — UX conversacional
- copiloto contextual por pantalla;
- acciones sugeridas con confirmación explícita;
- citas y procedencia visibles;
- accesibilidad y móvil.

## M40.8 — Evaluación
- benchmark por los 11 productos;
- casos adversariales;
- alucinación, conflicto de fuentes, prompt injection y fuga cross-tenant;
- comparación entre proveedores/modelos.

## M40.9 — Hardening y piloto
- observabilidad sin payload sensible;
- control de costos y latencia;
- circuit breakers y fallback;
- runbooks;
- gates específicos para piloto.

## Compatibilidad futura con IDE/agentes locales
La arquitectura M40.0 deberá exponer contratos desacoplados para permitir posteriormente ejecución y pruebas desde entornos como Visual Studio Code u otros IDE/agentes, sin convertir esas herramientas en fuente de verdad ni permitir que omitan las políticas de LegalAIZ.it.
