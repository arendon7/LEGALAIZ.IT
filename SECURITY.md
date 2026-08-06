# Política de seguridad de LegalAIZ.it

## Versión soportada

La única línea base soportada es la versión declarada en `VERSION` sobre la rama `main`. Las ramas, commits y documentos históricos no reciben correcciones independientes.

## Reporte responsable

No publiques vulnerabilidades, credenciales, datos personales, expedientes, documentos jurídicos, tokens, llaves o rutas privadas en issues públicos.

Utiliza el canal privado de reporte de vulnerabilidades de GitHub cuando esté habilitado. Si no está disponible, contacta privadamente al propietario del repositorio antes de divulgar detalles técnicos.

Incluye, cuando sea posible:

- componente y versión afectada;
- condiciones necesarias para reproducir;
- impacto sobre confidencialidad, integridad, disponibilidad, RBAC o trazabilidad;
- pasos de reproducción seguros;
- evidencia anonimizada;
- mitigación propuesta.

## Alcance prioritario

Se consideran especialmente sensibles:

- acceso cruzado entre usuarios, clientes, expedientes o documentos;
- evasión de RBAC, CSRF, control de origen o autenticación;
- exposición de secretos, tokens, llaves o datos personales;
- alteración de revisiones, aprobaciones, hashes o registros de auditoría;
- generación documental con variables no resueltas o contenido de otro expediente;
- descarga, liberación o comunicación sin autorización;
- inyección, traversal, carga insegura de archivos y ejecución de código.

## Manejo de datos

Las pruebas deben usar datos sintéticos. No adjuntes información real de clientes o asuntos jurídicos. Los archivos `.env`, bases locales, logs, cargas, secretos y artefactos generados están excluidos del repositorio.

## Limitación

La recepción de un reporte no implica aceptación automática de severidad, plazo de corrección ni recompensa. Cada hallazgo debe validarse de forma escéptica y trazable antes de su publicación o cierre.
