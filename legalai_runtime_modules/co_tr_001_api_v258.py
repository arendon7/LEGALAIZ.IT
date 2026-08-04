from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple

from co_tr_001_service_v258 import CoTr001ServiceV258


class CoTr001ApiV258:
    PREFIX = "/api/v258/co-tr-001"

    def __init__(self, root: Path):
        self.service = CoTr001ServiceV258(root)

    def handle(
        self,
        method: str,
        path: str,
        payload: Optional[dict[str, Any]] = None,
        actor: Optional[dict[str, Any]] = None,
    ) -> Tuple[int, dict[str, Any]]:
        payload = payload or {}
        actor = actor or {"id": "anonymous", "role": "user"}
        method = str(method or "GET").upper()
        try:
            if method == "GET" and path == self.PREFIX + "/capabilities":
                return 200, self.service.capabilities()
            if method == "POST" and path == self.PREFIX + "/evaluate":
                return 200, self.service.evaluate(payload.get("answers") or {}, payload.get("mode") or "precheck")
            if method == "POST" and path == self.PREFIX + "/generate":
                generated = self.service.generate(payload.get("answers") or {}, actor, payload.get("mode") or "precheck")
                public_result = {
                    key: value
                    for key, value in generated.items()
                    if key not in {"folder", "package"}
                }
                package_value = generated.get("package")
                if package_value:
                    public_result["package_filename"] = Path(str(package_value)).name
                return 201, public_result

            parts = [part for part in path.split("/") if part]
            prefix_parts = [part for part in self.PREFIX.split("/") if part]
            if parts[: len(prefix_parts)] != prefix_parts or len(parts) < len(prefix_parts) + 1:
                return 404, {"error": "route_not_found"}
            generation_id = parts[len(prefix_parts)]
            action = parts[len(prefix_parts) + 1] if len(parts) > len(prefix_parts) + 1 else "summary"
            gov = self.service.governance
            if method == "GET" and action == "summary":
                return 200, gov.summary(generation_id)
            if method == "POST" and action == "revision":
                return 201, gov.create_revision(
                    generation_id,
                    payload.get("answers") or {},
                    actor,
                    payload.get("base_revision"),
                    payload.get("change_note"),
                    payload.get("mode"),
                )
            if method == "GET" and action == "compare":
                return 200, gov.compare(generation_id, payload.get("from_revision"), payload.get("to_revision"))
            if method == "POST" and action == "approve":
                return 200, gov.approve(
                    generation_id,
                    payload.get("approval_type"),
                    payload.get("decision"),
                    payload.get("comment"),
                    actor,
                )
            if method == "GET" and action == "integrity":
                return 200, gov.verify_integrity(generation_id)
            return 404, {"error": "action_not_found"}
        except PermissionError:
            return 403, {"error": "forbidden"}
        except FileNotFoundError:
            return 404, {"error": "generation_not_found"}
        except (TypeError, ValueError) as exc:
            return 400, {"error": "invalid_request", "message": str(exc)}
        except Exception:
            return 500, {"error": "internal_error", "message": "No fue posible procesar la solicitud."}
