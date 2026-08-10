---
project: LegalAIZ.it
type: runbook
status: active
date: 2026-08-10
---

# Runbook · ChatGPT + GitHub

## Inicio de una conversación de continuidad
1. Leer `CHATGPT_CONTEXT.md`.
2. Leer `project-memory/01_STATE/CURRENT.md`.
3. Verificar únicamente los datos que pueden haber cambiado: `main`, PR activo y último workflow relevante.
4. Para arquitectura, leer `project-memory/01_STATE/GRAPHIFY.md` y `graphify-out/CHATGPT_GRAPH_INDEX.md` desde `context/graphify-snapshot` y comprobar que su SHA fuente corresponda al estado analizado.
5. Abrir código fuente solo después de identificar los módulos concretos implicados.

## Durante una iteración
- Trabajar siempre contra un SHA o rama explícitos.
- Separar cambios de infraestructura, jurídicos, editoriales y UX cuando sea posible.
- Antes de modificar una pieza, identificar dependencias y posibles regresiones.
- No repetir lecturas de archivos ya resumidos si el SHA no cambió.
- Agrupar consultas GitHub por objetivo: estado, diff, pruebas o evidencia.
- Si Graphify orienta hacia un módulo, confirmar la relación en código antes de modificarlo.

## Cierre mínimo verificable
Registrar:
- rama y HEAD;
- PR;
- workflows y conclusiones;
- pruebas relevantes;
- artifacts útiles;
- hallazgos abiertos;
- siguiente acción concreta.

Actualizar `CURRENT.md` solo cuando cambie el estado canónico.

## Política Graphify
El job `graphify-context` está consolidado dentro de `ci.yml`. En `push` a `main` genera grafo, índice y vault; publica el paquete pesado como artifact y empuja el snapshot compacto únicamente a `context/graphify-snapshot`. Nunca debe crear un commit automático en `main`.

## Política Obsidian
`project-memory/` debe seguir siendo pequeño y legible. No copiar código completo, logs extensos ni artifacts. Registrar decisiones y referencias hacia la evidencia, no duplicarla. El vault automático exportado por Graphify es regenerable y no sustituye la memoria curada.
