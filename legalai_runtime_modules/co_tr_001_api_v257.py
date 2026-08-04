from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from co_tr_001_service_v257 import CoTr001ServiceV257


class CoTr001ApiV257:
    """Contrato API independiente de framework; no expone rutas locales ni trazas."""

    def __init__(self, root: Optional[Union[Path, str]] = None):
        self.service = CoTr001ServiceV257(root)

    @staticmethod
    def _response(status: int, data: dict[str, Any]) -> dict[str, Any]:
        return {"status": status, "data": data}

    def handle(self, method: str, path: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        method = str(method or "GET").upper()
        path = "/" + str(path or "").strip("/")
        payload = payload or {}
        try:
            if method == "GET" and path == "/health":
                return self._response(200, self.service.health())
            if method == "POST" and path == "/v2.57/co-tr-001/check":
                return self._response(200, self.service.check(payload))
            if method == "POST" and path == "/v2.57/co-tr-001/register":
                return self._response(200, self.service.register(payload))
            if method == "POST" and path == "/v2.57/co-tr-001/authority":
                return self._response(200, self.service.authority_candidates(str(payload.get("text") or "")))
            return self._response(404, {"error": "route_not_found"})
        except (TypeError, ValueError):
            return self._response(400, {"error": "invalid_request"})
        except Exception:
            return self._response(500, {"error": "internal_error", "message": "No fue posible procesar la solicitud."})
