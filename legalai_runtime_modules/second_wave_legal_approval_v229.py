from __future__ import annotations

import hashlib
import json
from pathlib import Path


class SecondWaveLegalApprovalV229:
    """Registro histórico de expedientes candidatos de la segunda ola.

    Desde v2.34 el paquete es autocontenido y no distribuye documentos de
    releases históricos. Se preservan metadatos, hashes y trazabilidad, pero
    la revisión activa debe realizarse sobre la consolidación vigente v2.35.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "data" / "second_wave_legal_approval_v229.json"
        self.spec = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def _sha(path: Path) -> str | None:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

    def _expected_registry(self) -> dict[str, dict]:
        return {x.get("path"): x for x in self.spec.get("artifact_registry", []) if x.get("path")}

    def _artifact_state(self):
        expected = self._expected_registry()
        paths: list[tuple[str, str, str]] = []
        for product in self.spec.get("products", []):
            for key in ("document", "pdf"):
                rel = product.get(key)
                if rel:
                    paths.append((product["code"], key, rel))
        for rel in self.spec.get("consolidated_documents", []):
            paths.append(("CONSOLIDATED", Path(rel).suffix.lstrip("."), rel))

        rows = []
        for product, kind, rel in paths:
            path = self.root / rel
            actual = self._sha(path)
            archived = expected.get(rel, {})
            rows.append(
                {
                    "product": product,
                    "kind": kind,
                    "path": rel,
                    "exists": path.is_file(),
                    "sha256": actual,
                    "bytes": path.stat().st_size if path.is_file() else 0,
                    "expected_sha256": archived.get("sha256"),
                    "expected_bytes": archived.get("bytes", 0),
                    "archived_hash_preserved": bool(archived.get("sha256")),
                    "included_in_current_package": path.is_file(),
                    "superseded_by": "2.35",
                }
            )
        return rows

    def _current_consolidation(self) -> dict:
        path = self.root / "data" / "third_wave_internal_approval_v235.json"
        if not path.is_file():
            return {"version": None, "exists": False, "artifacts_ready": 0, "artifacts": 0}
        data = json.loads(path.read_text(encoding="utf-8"))
        artifacts = data.get("approval_documents", [])
        ready = sum((self.root / rel).is_file() for rel in artifacts)
        return {
            "version": data.get("version"),
            "exists": True,
            "products": len(data.get("consolidated_products", [])),
            "artifacts": len(artifacts),
            "artifacts_ready": ready,
            "publication_authorized": bool(data.get("publication_authorized")),
            "endpoint": "/api/v235/third-wave-internal-approval",
        }

    def summary(self):
        data = json.loads(json.dumps(self.spec))
        artifacts = self._artifact_state()
        gates = data.get("quality_gates", [])
        current = self._current_consolidation()
        data["artifact_registry"] = artifacts
        data["packaging"] = {
            "policy": "current-only-autocontenido",
            "historical_binaries_included": False,
            "historical_hashes_preserved": True,
            "superseded_by": "2.35",
        }
        data["current_consolidation"] = current
        data["counts"] = {
            "products": len(data.get("products", [])),
            "decisions": sum(len(x.get("decisions", [])) for x in data.get("products", [])),
            "blocks": sum(len(x.get("blocks", [])) for x in data.get("products", [])),
            "traceability_rows": sum(len(x.get("traceability", [])) for x in data.get("products", [])),
            "verified_sources": len(data.get("sources_verified", [])),
            "artifacts": len(artifacts),
            "artifacts_ready": sum(x["exists"] and bool(x["sha256"]) for x in artifacts),
            "archived_hashes_preserved": sum(bool(x["archived_hash_preserved"]) for x in artifacts),
            "pending_gates": sum(x.get("status") in {"pending", "blocked"} for x in gates),
        }
        data["ready_for_internal_review"] = False
        data["historical_stage_record_preserved"] = data["counts"]["archived_hashes_preserved"] == data["counts"]["artifacts"] == 8
        data["current_review_target"] = "2.35"
        data["current_consolidation_ready"] = bool(
            current.get("version") == "2.35"
            and current.get("products") == 11
            and current.get("artifacts") == current.get("artifacts_ready")
            and not current.get("publication_authorized")
        )
        return data
