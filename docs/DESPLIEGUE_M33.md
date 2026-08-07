# Despliegue M33.0

`main` es la fuente de verdad. `ci.yml` valida la aplicación y `pages.yml` publica el frontend estático.

La aplicación completa se ejecuta desde el mismo commit mediante Docker, Codespaces o un servicio web compatible con `render.yaml`.

La demo pública utiliza `LEGAL_PUBLIC_DEMO_MODE=true`, cuentas sintéticas, SQLite efímero y pagos sandbox. La cohorte se reconstruye automáticamente al iniciar.

Producción jurídica real exige PostgreSQL certificado, secretos administrados, MFA, HTTPS/origin checks, persistencia, backup/restore, monitoreo, pentest y aprobación profesional independiente.
