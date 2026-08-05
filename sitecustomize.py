"""Bootstrap de compatibilidad para la compuerta documental LegalAIZ.it.

Python importa ``sitecustomize`` cuando la raíz del proyecto está en ``sys.path``.
La aplicación también instala la compuerta explícitamente desde ``run.py``; esta
segunda vía protege scripts, pruebas e integraciones que importan módulos históricos
de forma directa. La operación es idempotente.
"""

from legalai_platform.document_release_gate import install_docx_release_gate

install_docx_release_gate()
