# LegalAIZ.it — M32.9

**Versión canónica del repositorio:** M32.9  
**Estado:** línea base estable de demostración, revisión y desarrollo incremental.  
**Jurisdicción principal:** Colombia.

[![Validación LegalAIZ.it](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/ci.yml/badge.svg)](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/ci.yml)
[![GitHub Pages](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/pages.yml/badge.svg)](https://github.com/arendon7/LEGALAIZ.IT/actions/workflows/pages.yml)

> Esta versión demuestra flujos jurídicos, documentales y de gobierno con datos sintéticos. No acredita aprobación profesional de asuntos reales, representación judicial, radicación, firma, notificación externa ni entrega efectiva.

## Fuente de verdad

- Rama vigente: `main`.
- Marcador de versión: [`VERSION`](VERSION).
- Notas de versión: [`FINAL_RELEASE_NOTES.md`](FINAL_RELEASE_NOTES.md).
- Estado documental y técnico: [`docs/README.md`](docs/README.md).
- Historial de cambios: pull requests fusionados y commits de Git.

Las ramas de trabajo y los documentos de iteraciones anteriores son históricos. No deben utilizarse como versión vigente ni como base de nuevas modificaciones.

## Capacidades consolidadas

M32.9 conserva las capacidades acumuladas y añade gobierno de comunicaciones antes del procesamiento transaccional:

- 11 productos jurídicos y formularios demo completos;
- generación DOCX con compuertas de integridad, OOXML y preflight visual;
- expedientes, revisiones inmutables, comparación y liberación por SHA-256;
- aprobación jurídica y QA separadas;
- Mesa Jurídica, asignaciones, SLA operativos y alertas;
- centro de notificaciones, calendario operativo y cola externa sandbox;
- comunicaciones transaccionales auditables sin entrega real;
- relaciones, preferencias, negativas, supresiones y decisiones de contacto trazables;
- RBAC, CSRF, control de origen, minimización de datos y cadenas append-only.

## Vista pública

La landing y la interfaz estática se publican en:

https://arendon7.github.io/LEGALAIZ.IT/

GitHub Pages no ejecuta el backend Python.

## Aplicación funcional desde GitHub

1. Selecciona **Code**.
2. Abre **Codespaces**.
3. Crea un codespace sobre `main`.
4. Abre el puerto `8765` cuando la aplicación termine de iniciar.

Acceso directo:

https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=1322097934

## Ejecución local

- macOS: `00_ABRIR_LEGALAIZIT_MAC.command`
- Windows: `00_ABRIR_LEGALAIZIT_WINDOWS.bat`
- Linux: `00_ABRIR_LEGALAIZIT_LINUX.sh`

Ejecución manual:

```bash
pip install -r requirements.txt
python run.py --lan --no-browser
```

Abrir `http://127.0.0.1:8765`.

## Credenciales demo

- Administración / QA: `ana@demo.legalaiz.it`
- Especialista laboral: `maria@demo.legalaiz.it`
- Especialista contractual: `carlos@demo.legalaiz.it`
- Especialista tránsito: `laura@demo.legalaiz.it`
- Contraseña común: `LegalAIZDemo2026!`

Estas credenciales son exclusivamente demostrativas y deben permanecer deshabilitadas fuera del perfil demo autorizado.

## Validación automática

Solo existen dos workflows activos:

- `ci.yml`: sintaxis, pruebas, 11 productos, cobertura de formularios, arranque HTTP y renderizado DOCX;
- `pages.yml`: publicación posterior a una validación satisfactoria de `main`.

La CI usa concurrencia con cancelación de ejecuciones equivalentes. Las definiciones históricas de workflows no forman parte del árbol operativo.

**LegalAIZ.it — Más que respuestas, soluciones.**
