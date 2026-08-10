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
3. Verificar en GitHub únicamente los datos que pueden haber cambiado: `main`, PR activo y último workflow relevante.
4. Si existe `graphify-out/GRAPH_REPORT.md`, usarlo para orientar la búsqueda arquitectónica.
5. Abrir código fuente solo después de identificar los módulos concretos implicados.

## Durante una iteración
- Trabajar siempre contra un SHA o rama explícitos.
- Separar cambios de infraestructura, jurídicos, editoriales y UX cuando sea posible.
- Antes de modificar una pieza, identificar dependencias y posibles regresiones.
- No repetir lecturas de archivos ya resumidos si el SHA no cambió.
- Agrupar consultas GitHub por objetivo: estado, diff, pruebas o evidencia.

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
Cuando haya snapshot vigente, consultar primero relaciones y comunidades del grafo. Después abrir únicamente los archivos necesarios para verificar o modificar. Graphify es un índice de orientación, no una prueba de corrección.

## Política Obsidian
`project-memory/` debe seguir siendo pequeño y legible. No copiar código completo, logs extensos ni artifacts. Registrar decisiones y enlaces hacia la evidencia, no duplicarla.
