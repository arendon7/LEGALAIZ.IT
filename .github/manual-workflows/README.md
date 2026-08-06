# Workflows especializados archivados

Los workflows de las iteraciones M32.2 a M32.9 se conservan en esta carpeta como evidencia reproducible de sus compuertas especializadas.

La validación automática del repositorio se ejecuta únicamente mediante `.github/workflows/ci.yml`, que comprende:

- compilación y sintaxis;
- todas las pruebas `tests/test_*.py`;
- validación de los 11 productos y al menos 473 preguntas;
- arranque HTTP;
- generación y revisión visual automatizada de DOCX.

Los archivos de esta carpeta no son ejecutados automáticamente por GitHub Actions. Para reproducir una compuerta especializada, puede copiarse temporalmente el workflow correspondiente a `.github/workflows/` o ejecutar directamente sus comandos documentados.

La consolidación se aplicó para evitar ejecuciones duplicadas, colas obsoletas y conflictos entre validaciones históricas. `ci.yml` usa concurrencia con cancelación de ejecuciones anteriores del mismo PR o rama.
