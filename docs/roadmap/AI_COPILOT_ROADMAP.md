# LegalAIZ.it — Roadmap M40 Legal AI Copilot

## Objetivo
Integrar inteligencia artificial conversacional, jurídica y documental sin debilitar la trazabilidad, la confirmación de hechos, el aislamiento por organización/expediente, la revisión humana ni la aprobación dual existentes.

M40 inicia únicamente desde una base M39.2 certificada y convergida. La IA se añade como capa gobernada; no reemplaza los controles deterministas ya certificados.

## Arquitectura de referencia M40.0

`AI Gateway → Policy Engine → Context Builder → Provider → Structured Output → Validator → Audit`

El registro de auditoría deberá poder asociar, según aplique:
- usuario y rol;
- organización/tenant;
- expediente;
- documento/revisión;
- proveedor y modelo;
- versión de prompt/política;
- fuentes utilizadas;
- hash o referencia segura de inputs;
- salida estructurada;
- confianza/estado de validación cuando exista una métrica definida;
- acción propuesta/ejecutada;
- confirmación humana requerida y obtenida.

La observabilidad no debe convertir payload sensible en telemetría expuesta.

## M40.0 — AI Governance & Provider Gateway
- gateway único de proveedores/modelos;
- abstracción desacoplada para no amarrar el producto a un proveedor;
- políticas por rol, organización, expediente y documento;
- construcción de contexto mínimo autorizado;
- structured outputs validados por esquema;
- control de prompt/versionado;
- presupuestos, límites de consumo, timeout, circuit breaker y fallback;
- auditoría trazable de fuentes, hashes y acciones;
- ninguna salida de IA equivale a aprobación jurídica o QA.

## M40.1 — Copiloto de orientación/intake
- conversación inicial guiada;
- extracción de hechos candidatos;
- separación entre hecho inferido, hecho confirmado y hecho disputado;
- confirmación/disputa explícita;
- preguntas adaptativas;
- explicación comprensible de la ruta sugerida;
- escalamiento cuando falten hechos materiales o la incertidumbre sea jurídicamente relevante.

## M40.2 — Copiloto del expediente
- resumen trazable;
- faltantes, contradicciones y cronología;
- riesgos y próximos pasos;
- preguntas sobre documentos, evidencias y tareas dentro del tenant autorizado;
- ninguna lectura cross-tenant;
- ninguna alteración silenciosa del expediente.

## M40.3 — Copiloto documental
- explicar cláusulas y consecuencias;
- detectar inconsistencias internas y contra hechos confirmados;
- identificar variables incompletas, cláusulas ausentes y obligaciones contradictorias;
- proponer redacción alternativa;
- comparar hechos del expediente contra el documento;
- citar fuentes cuando la propuesta dependa de derecho positivo o interpretación jurídica.

Invariante documental:

`Documento Vn aprobado → propuesta IA → diff visible → Vn+1 borrador → revisión humana → Legal → QA → aprobación`

La IA nunca sobrescribe silenciosamente una revisión aprobada ni convierte una propuesta en versión final sin los gates existentes.

## M40.4 — Copiloto profesional/revisor
- revisión 360 para especialista;
- inconsistencias, fuentes, hechos sin soporte y cláusulas ausentes;
- alertas de fechas, valores, partes, anexos y firmas;
- detección de posibles fuentes desactualizadas;
- propuestas de corrección con diff y justificación;
- ninguna autoaprobación Legal o QA.

## M40.5 — RAG jurídico
- prioridad a fuentes oficiales colombianas;
- autoridad, norma, artículo, fecha de consulta, vigencia y localizador;
- distinción visible entre **NORMA / INTERPRETACIÓN / HECHO / RIESGO / RECOMENDACIÓN**;
- tratamiento explícito de derogatorias, modificaciones y conflictos de vigencia;
- fail-closed o escalamiento cuando la fuente sea insuficiente, no verificable o potencialmente desactualizada.

## M40.6 — Orquestación especializada
Agentes previstos:
- Intake Agent;
- Fact Agent;
- Legal Research Agent;
- Document Agent;
- Risk Agent;
- QA Agent;
- Case Agent.

Ningún agente puede saltarse RBAC, tenant isolation, confirmación de hechos, reglas jurídicas deterministas, gates documentales, auditoría ni aprobación humana.

## M40.7 — UX conversacional
- copiloto contextual por pantalla;
- conversación coherente con el estado del expediente;
- acciones sugeridas con confirmación explícita;
- citas/procedencia visibles cuando aplique;
- explicación de qué hizo la IA y qué requiere revisión;
- accesibilidad, responsive y experiencia móvil;
- diseño que acompañe al usuario sin ocultar los controles jurídicos.

## M40.8 — Evaluación legal y adversarial
- benchmark por los 11 productos;
- golden cases y casos límite;
- alucinación y citas inexistentes;
- conflicto de fuentes y vigencia;
- prompt injection e instrucciones contenidas en documentos subidos;
- fuga cross-tenant;
- hechos inventados o promovidos sin confirmación;
- propuestas documentales contradictorias;
- comparación controlada entre proveedores/modelos;
- regresión contra resultados deterministas y documentos certificados.

## M40.9 — Hardening y piloto
- observabilidad sin payload sensible;
- control de costos, latencia y disponibilidad;
- circuit breakers y fallback;
- rate limits y presupuestos por contexto;
- runbooks e incident response;
- métricas de escalamiento y corrección humana;
- gates específicos para piloto controlado.

## Guardrails transversales
Ningún proveedor, modelo o agente puede:
- promover hechos no confirmados;
- saltarse RBAC o aislamiento;
- leer contexto no autorizado;
- sobrescribir revisiones aprobadas;
- aprobar Legal o QA;
- inventar normas, artículos, sentencias, autoridades, fechas o citas;
- activar pagos, comunicaciones o producción por sí mismo;
- exponer secretos o payload sensible en logs.

## Integración futura con IDE y robots

La integración con Visual Studio Code, Antigravity u otros IDE/agentes se aborda **después de estabilizar M40.0–M40.4**.

La arquitectura deberá permitir que esos entornos consuman contratos explícitos del AI Gateway y tooling de pruebas, no que accedan directamente a secretos, bases de datos o flujos privilegiados.

Usos futuros previstos:
- ejecutar suites y benchmarks M40 desde el IDE;
- probar proveedores/modelos con fixtures controlados;
- correr robots de desarrollo y QA con permisos acotados;
- inspeccionar trazas, decisiones y diffs sin exponer payload sensible;
- reproducir fallos con datasets sanitizados;
- mantener GitHub/CI y los gates de LegalAIZ.it como fuente de certificación.

El IDE o robot nunca será la fuente canónica del estado jurídico, documental o de producción.
