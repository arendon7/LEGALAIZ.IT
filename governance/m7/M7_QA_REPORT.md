# LegalAIZ.it M7 — Informe de QA

## Estado

- Build: `M7-PREPRODUCTION-HARDENING-2026-07-29`.
- Aprobado para preproducción y piloto profesional controlado.
- Producción pública: **no autorizada**.

## Regresión activa

- Módulos: 16.
- Pruebas: 115 aprobadas.
- Subpruebas: 630 aprobadas.
- Fallas: 0.
- Errores: 0.
- Ejecución aislada por módulo para controlar servidores locales y estados heredados.

## Seguridad y smoke

- Smoke HTTP: 13 de 13 controles aprobados.
- Escaneo estático focal: 0 hallazgos altos o críticos.
- Contraseñas nuevas: scrypt; migración desde PBKDF2 al autenticar.
- MFA obligatorio para perfiles privilegiados.
- Expiración de sesión por inactividad y absoluta.
- Rate limiting, same-origin, proxy allowlist, request IDs y eventos encadenados.
- Cargas: bloqueo de ejecutables, macros, contenido activo, expansión sospechosa y EICAR; ClamAV fail-closed fuera de local.

## Validación estática

- Python compatible sintácticamente con 3.9: 363 archivos, 0 errores.
- `compileall`: aprobado.
- JavaScript activo: 1 archivo, sintaxis aprobada.
- JSON: 916 archivos, 0 errores.
- Acta M7: 4 páginas renderizadas e inspeccionadas; 0 hallazgos de accesibilidad.

## Compuertas externas

Permanecen pendientes PostgreSQL productivo, TLS público, monitoreo, restauración, carga, pentest independiente, privacidad, simulacro de incidentes, validación real macOS/Windows y rollback. `production_ready=false`.
