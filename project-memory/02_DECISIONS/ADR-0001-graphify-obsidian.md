---
project: LegalAIZ.it
type: decision
status: approved
date: 2026-08-10
related:
  - ChatGPT
  - GitHub
  - Graphify
  - Obsidian
---

# ADR-0001 · Graphify + Obsidian para continuidad del proyecto

## Decisión
Adoptar una capa de conocimiento en dos niveles, manteniendo GitHub `main` como fuente canónica del código:

1. **Obsidian / `project-memory/` en `main`**: memoria humana curada, pequeña y estable para decisiones, estado, handoffs, riesgos y runbooks.
2. **Graphify / rama `context/graphify-snapshot` + artifacts**: mapa generado de relaciones del código para orientar análisis antes de abrir archivos fuente.

ChatGPT seguirá siendo la interfaz principal de dirección. Esta arquitectura no exige usar Codex para operar el proyecto.

## Objetivos
- Reducir reconstrucción de contexto entre conversaciones.
- Evitar lecturas GitHub repetidas para redescubrir arquitectura ya conocida.
- Distinguir hechos certificados, decisiones humanas e inferencias técnicas.
- Conservar trazabilidad por SHA, PR y workflow.
- Disminuir riesgo de modificar componentes no relacionados.
- Evitar que la regeneración de contexto cambie el SHA canónico de `main`.

## Reglas
- Graphify orienta; GitHub y las pruebas verifican.
- La memoria nunca declara `success`, `merged`, `approved` o `released` sin evidencia del SHA exacto.
- Un cambio jurídico o normativo exige fuente oficial vigente y control humano cuando corresponda.
- No se guardan secretos, tokens, datos personales sensibles ni contenido de expedientes reales en el vault.
- Los outputs regenerables de Graphify no sustituyen documentación jurídica ni ADR.
- El grafo completo y el vault generado no se versionan en `main`; viven como artifacts.
- El índice compacto y su metadato se publican en `context/graphify-snapshot`, rama regenerable y no canónica.

## Política de actualización
- Al iniciar: leer índice + estado actual.
- Antes de explorar arquitectura: consultar `context/graphify-snapshot` si su SHA fuente coincide con el estado que se analiza.
- Al cambiar una decisión: crear/actualizar ADR y marcar la anterior como `superseded`, sin borrar historia.
- Al cerrar una sesión compleja: registrar un handoff breve con SHA, PR, checks, hallazgos y siguiente acción cuando aporte valor persistente.
- Al certificar un nuevo `main`: actualizar `CURRENT.md`.

## Razón
Graphify modela el repositorio como grafo consultable y permite acotar la exploración estructural. Obsidian funciona bien para notas Markdown enlazadas y decisiones persistentes. Separarlos evita mezclar conocimiento regenerable con decisiones jurídicas y operativas que requieren curaduría humana y evita commits automáticos posteriores a la certificación de `main`.
