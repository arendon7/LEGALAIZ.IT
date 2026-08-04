from __future__ import annotations

from pathlib import Path
from typing import Any

from co_tr_002_document_factory_v256 import DocumentGenerationError
from co_tr_002_service_v256 import CoTr002ServiceV256


class CoTr002ApiV256:
    """Adaptador HTTP agnóstico con errores seguros y autorización basada en el actor autenticado."""

    PREFIX = "/api/v256/co-tr-002"
    GENERATION_ROLES = {"user", "specialist", "specialist_legal", "qa", "admin"}

    def __init__(self, root: Path):
        self.service = CoTr002ServiceV256(root)

    @staticmethod
    def _error(status: int, code: str, message: str) -> tuple[int, dict[str, Any]]:
        return status, {"error": {"code": code, "message": message}}

    @staticmethod
    def _authenticated_actor(actor: dict[str, Any] | None) -> dict[str, Any]:
        actor = dict(actor or {})
        actor_id = str(actor.get("id") or "").strip()
        role = str(actor.get("role") or "").strip()
        if not actor_id or actor_id.lower() in {"anonymous", "anon", "none"}:
            raise PermissionError("Se requiere una sesión autenticada.")
        if not role:
            raise PermissionError("La sesión no tiene un rol válido.")
        return {"id": actor_id, "role": role}

    @staticmethod
    def _public_generation(result: dict[str, Any]) -> dict[str, Any]:
        manifest = dict(result.get("manifest") or {})
        return {
            "generation_id": result.get("generation_id"),
            "package_filename": manifest.get("package_filename"),
            "manifest": manifest,
            "evaluation": result.get("evaluation"),
            "governance": result.get("governance"),
        }

    def handle(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        actor: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        payload = payload if isinstance(payload, dict) else {}
        method = str(method or "").upper()
        try:
            if method == "GET" and path == f"{self.PREFIX}/capabilities":
                return 200, self.service.capabilities()
            if method == "GET" and path == f"{self.PREFIX}/closure":
                return 200, self.service.closure()
            if method == "GET" and path == f"{self.PREFIX}/source-control":
                return 200, self.service.source_control()
            if method == "POST" and path == f"{self.PREFIX}/evaluate":
                return 200, self.service.evaluate(payload.get("answers") or {})
            if method == "POST" and path == f"{self.PREFIX}/generate":
                auth = self._authenticated_actor(actor)
                if auth["role"] not in self.GENERATION_ROLES:
                    raise PermissionError("El rol no puede generar documentos.")
                result = self.service.generate(payload.get("answers") or {}, auth)
                return 201, self._public_generation(result)

            parts = [part for part in str(path or "").split("/") if part]
            prefix_parts = [part for part in self.PREFIX.split("/") if part]
            if parts[: len(prefix_parts)] != prefix_parts or len(parts) < len(prefix_parts) + 1:
                return self._error(404, "route_not_found", "Ruta v2.56 no encontrada.")
            generation_id = parts[len(prefix_parts)]
            action = parts[len(prefix_parts) + 1] if len(parts) > len(prefix_parts) + 1 else "summary"
            gov = self.service.governance

            if method == "GET" and action == "summary":
                return 200, gov.summary(generation_id)
            if method == "POST" and action == "revision":
                auth = self._authenticated_actor(actor)
                return 201, gov.create_revision(
                    generation_id,
                    payload.get("answers") or {},
                    auth,
                    payload.get("base_revision"),
                    payload.get("change_note"),
                )
            if method == "GET" and action == "compare":
                return 200, gov.compare(
                    generation_id,
                    int(payload.get("from_revision")),
                    int(payload.get("to_revision")),
                )
            if method == "POST" and action == "approve":
                auth = self._authenticated_actor(actor)
                return 200, gov.approve(
                    generation_id,
                    payload.get("approval_type"),
                    payload.get("decision"),
                    payload.get("comment"),
                    auth,
                )
            if method == "GET" and action == "integrity":
                return 200, gov.verify_integrity(generation_id)
            if method == "GET" and action == "release-gate":
                return 200, self.service.release_gate.report(generation_id)
            return self._error(404, "action_not_found", "Acción v2.56 no encontrada.")
        except PermissionError as exc:
            return self._error(403, "forbidden", str(exc))
        except FileNotFoundError:
            return self._error(404, "not_found", "El recurso solicitado no existe.")
        except (DocumentGenerationError, ValueError, TypeError) as exc:
            return self._error(422, "validation_error", str(exc))
        except Exception:
            return self._error(500, "internal_error", "No fue posible completar la operación de forma segura.")
