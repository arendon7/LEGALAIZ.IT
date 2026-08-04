# Gobierno M6

M6 consolida la preparación de LegalAIZ.it como Release Candidate para piloto profesional controlado.

## Fuentes de verdad

- `RELEASE_CANDIDATE_REGISTRY.json`: compuertas reproducibles de contenido y experiencia.
- Registro M3: aprobación controlada de los once productos.
- Registros M4 y M5: aprobación, fuentes e integridad de las bibliotecas profundas.
- `/api/rc-readiness`: estado combinado del contenido y del entorno actual.
- `/api/governance`: estado unificado por producto.

## Separación de compuertas

La aprobación jurídica controlada no equivale a habilitación automática de producción. La primera responde a suficiencia y gobierno del contenido canónico; la segunda exige controles de infraestructura, operación, privacidad y seguridad.

## Archivo histórico

Los activos, reportes, bibliotecas y launchers de fases anteriores se preservan bajo `governance/archive/`. No se cargan en la interfaz principal ni constituyen puntos de entrada vigentes.

## Aislamiento técnico

La raíz activa contiene los servicios de plataforma vigentes. Las 88 implementaciones históricas versionadas necesarias para compatibilidad se aislaron en `legacy_runtime/`; la arquitectura objetivo sigue siendo su sustitución gradual por servicios de dominio únicos. Las herramientas históricas se conservan bajo `governance/archive/tools_legacy/`.
