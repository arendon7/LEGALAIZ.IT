"""Bootstrap de compatibilidad para la compuerta documental LegalAIZ.it.

Python importa ``sitecustomize`` cuando la raíz del proyecto está en ``sys.path``.
La aplicación instala la compuerta explícitamente desde ``run.py``. Esta vía
adicional protege scripts e integraciones históricas, pero debe permanecer inerte
mientras las dependencias de DOCX todavía no estén instaladas.
"""

from importlib.util import find_spec


def _install_when_dependencies_are_ready() -> None:
    if find_spec("docx") is None:
        return
    try:
        from legalai_platform.document_release_gate import install_docx_release_gate
    except ModuleNotFoundError as exc:
        # Durante ``pip install -r requirements.txt`` puede existir el proyecto en
        # sys.path antes de que todas sus dependencias estén disponibles.
        if exc.name in {"docx", "lxml"}:
            return
        raise
    install_docx_release_gate()


_install_when_dependencies_are_ready()
