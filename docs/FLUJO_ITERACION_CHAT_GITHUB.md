# Flujo de iteración LegalAIZ.it

## Objetivo

Convertir las decisiones tomadas en conversación en cambios trazables del repositorio, con validación automática y una vista pública actualizada.

## Canales de visualización

- **GitHub Pages:** landing, navegación pública, textos, imágenes, componentes visuales y responsive.
- **GitHub Codespaces:** aplicación completa con backend, perfiles demo, expedientes, documentos, revisiones y aprobaciones.

GitHub Pages no ejecuta Python. Por eso funciona como escaparate y entorno de revisión visual, mientras Codespaces conserva la demostración funcional completa.

## Flujo ordinario

1. Se define aquí el objetivo de la iteración y sus criterios de aceptación.
2. Se inspeccionan los archivos vigentes antes de modificar.
3. Se crea una rama breve para cambios estructurales, jurídicos, de seguridad o de múltiples archivos.
4. Se implementan textos, estilos, código e imágenes sin crear copias históricas dentro del repositorio.
5. GitHub Actions valida sintaxis, dependencias, arranque y endpoint de salud.
6. Cuando la validación es satisfactoria, el cambio se integra en `main`.
7. La vista pública de GitHub Pages se reconstruye automáticamente desde `app/`.
8. Se verifica la URL publicada y se informa el commit, alcance y resultado de las pruebas.

## Dos velocidades

### Cambio rápido

Para correcciones menores de texto, estilos aislados, enlaces o activos sin impacto funcional:

- modificación puntual;
- validación automática;
- integración en `main`;
- publicación en Pages.

### Cambio controlado

Para rutas, formularios, reglas, permisos, documentos, backend, seguridad o cambios amplios:

- rama dedicada;
- revisión del diff;
- pruebas pertinentes;
- pull request;
- integración únicamente con CI satisfactoria.

## Reglas del repositorio

- `main` representa la versión vigente.
- No se guardan carpetas duplicadas por versión dentro del código activo.
- Los cambios jurídicos deben indicar producto, riesgo, fuente y validación requerida.
- Las imágenes oficiales deben conservar logo, paleta y proporciones aprobadas.
- No se afirma que algo quedó corregido o probado sin evidencia del workflow o revisión directa.
- Todo cambio debe poder rastrearse a un commit y, cuando corresponda, a un pull request.

## Enlaces

- Repositorio: https://github.com/arendon7/LEGALAIZ.IT
- Vista pública: https://arendon7.github.io/LEGALAIZ.IT/
- Aplicación funcional: https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=1322097934
