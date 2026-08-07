# LegalAIZ.it — M33.0 · v5.1.1

Rama vigente: `main`. M33.0 es la línea canónica después de integrar la producción demostrativa aprobada sobre M32.9.

M33.0 integra la **M31.9 v5.1.0 aprobada** sobre la línea canónica **M32.9**, sin retirar las mejoras posteriores de gobierno, operación, comunicaciones y seguridad.

## Capacidades

- 11 productos jurídicos y formularios demo completos.
- 11 expedientes sintéticos y 76 documentos demo.
- Revisiones inmutables, comparación, aprobación jurídica y QA independientes.
- Mesa Jurídica, asignaciones, alertas, SLA, notificaciones y calendario.
- Comunicaciones sandbox y gobierno de consentimientos/preferencias.
- Landing, catálogo público y checkout sandbox.
- Perfil de **producción demostrativa pública** con bootstrap automático.

## GitHub Pages

La landing y la interfaz estática se publican automáticamente en:

https://arendon7.github.io/LEGALAIZ.IT/

Pages no ejecuta Python; la aplicación completa usa el mismo repositorio mediante Docker/Codespaces/Render.

## Aplicación completa

### Local / Codespaces

- macOS: `01_INICIAR_DEMO_PUBLICA_MAC.command`
- Linux/Codespaces: `01_INICIAR_DEMO_PUBLICA_LINUX.sh`
- Windows: `01_INICIAR_DEMO_PUBLICA_WINDOWS.bat`

### Render

El repositorio incluye `render.yaml` para crear una instancia demostrativa desde `main`. La base es efímera a propósito: al iniciar se reconstruyen automáticamente los expedientes sintéticos.

## Credenciales demo

- Administradora: `ana@demo.legalaiz.it`
- Cliente: `juan@demo.legalaiz.it`
- Especialistas: `maria@demo.legalaiz.it`, `carlos@demo.legalaiz.it`, `laura@demo.legalaiz.it`
- Contraseña: `LegalAIZDemo2026!`

## Gobierno del repositorio

Solo existen dos workflows activos: `ci.yml` y `pages.yml`. `main` es la fuente de verdad y cualquier despliegue completo debe partir del mismo commit que supera CI.

## Alcance

No acredita aprobación profesional de casos reales ni habilita operación jurídica real. `LEGAL_PUBLIC_DEMO_MODE=true` habilita exclusivamente producción demostrativa. Los datos son sintéticos y los pagos permanecen sandbox. No habilita producción jurídica real, pagos reales, representación judicial ni radicación automática.

**LegalAIZ.it — Más que respuestas, soluciones.**
