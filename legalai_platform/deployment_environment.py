from __future__ import annotations

import base64
import os
from hashlib import sha256


def prepare_deployment_environment() -> None:
    """Normaliza variables administradas por el proveedor antes de cargar el runtime.

    Render publica RENDER_EXTERNAL_URL automáticamente. La usamos como origen
    público si no existe una configuración explícita. Para cifrado, Render genera
    un secreto opaco; se deriva determinísticamente una llave AES de 32 bytes sin
    registrar ni persistir el secreto fuente.
    """
    external_url = str(os.environ.get("RENDER_EXTERNAL_URL", "")).strip()
    if external_url and not str(os.environ.get("LEGAL_PUBLIC_BASE_URL", "")).strip():
        os.environ["LEGAL_PUBLIC_BASE_URL"] = external_url.rstrip("/")

    seed = str(os.environ.get("LEGAL_MASTER_KEY_SEED", ""))
    if seed and not str(os.environ.get("LEGAL_MASTER_KEY", "")).strip():
        derived = sha256(seed.encode("utf-8")).digest()
        encoded = base64.urlsafe_b64encode(derived).decode("ascii").rstrip("=")
        os.environ["LEGAL_MASTER_KEY"] = encoded


__all__ = ["prepare_deployment_environment"]
