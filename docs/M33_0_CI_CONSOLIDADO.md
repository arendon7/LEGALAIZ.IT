# M33.0 — CI consolidado

Los controles transitorios de las oleadas M33.0 se consolidan en `.github/workflows/ci.yml` para conservar la política del repositorio de mantener únicamente `ci.yml` y `pages.yml` como workflows activos.

El job de regresión ejecuta la suite completa. El job visual genera y valida en una sola ejecución las cuatro muestras contractuales, seis muestras de la segunda oleada y siete muestras de salud y tránsito, además de la regresión visual histórica.
