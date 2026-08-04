from __future__ import annotations

import hashlib
import json
from pathlib import Path


class SecondWaveInternalDecisionV230:
    """Registro histórico de la decisión interna asistida de la segunda ola.

    Los binarios v2.29/v2.30 se excluyen del paquete autocontenido vigente. Sus
    hashes permanecen como evidencia histórica; la ratificación activa debe
    recaer sobre los artefactos exactos de v2.35.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "data" / "second_wave_internal_decision_v230.json"
        self.spec = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def _sha(path: Path) -> str | None:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

    def _v229_registry(self) -> dict[str, dict]:
        path = self.root / "data" / "second_wave_legal_approval_v229.json"
        if not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {x.get("path"): x for x in data.get("artifact_registry", []) if x.get("path")}

    def _candidate_integrity(self):
        archived_registry = self._v229_registry()
        rows = []
        for product in self.spec.get("products", []):
            for kind, path_key, hash_key in (
                ("candidate_docx", "candidate_document", "candidate_sha256_docx"),
                ("candidate_pdf", "candidate_pdf", "candidate_sha256_pdf"),
            ):
                rel = product.get(path_key)
                if not rel:
                    continue
                path = self.root / rel
                actual = self._sha(path)
                expected = product.get(hash_key) or archived_registry.get(rel, {}).get("sha256")
                rows.append(
                    {
                        "product": product.get("code"),
                        "kind": kind,
                        "path": rel,
                        "exists": path.is_file(),
                        "expected_sha256": expected,
                        "actual_sha256": actual,
                        "matches": bool(actual and expected and actual == expected),
                        "archived_hash_preserved": bool(expected),
                        "bytes": path.stat().st_size if path.is_file() else 0,
                        "expected_bytes": archived_registry.get(rel, {}).get("bytes", 0),
                        "included_in_current_package": path.is_file(),
                        "superseded_by": "2.35",
                    }
                )
        return rows

    def _approval_artifacts(self):
        expected = {x.get("path"): x for x in self.spec.get("artifact_registry", []) if x.get("path")}
        rows = []
        for rel in self.spec.get("approval_documents", []):
            path = self.root / rel
            actual = self._sha(path)
            archived = expected.get(rel, {})
            rows.append(
                {
                    "path": rel,
                    "format": path.suffix.lstrip(".").upper(),
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
            return {"version": None, "exists": False}
        data = json.loads(path.read_text(encoding="utf-8"))
        artifacts = data.get("approval_documents", [])
        consolidated = {x.get("code"): x for x in data.get("consolidated_products", [])}
        scope = set(self.spec.get("scope", []))
        scope_pending = all(
            code in consolidated and consolidated[code].get("human_ratification") == "Pendiente"
            for code in scope
        )
        return {
            "version": data.get("version"),
            "exists": True,
            "products": len(data.get("consolidated_products", [])),
            "scope_ratification_pending": scope_pending,
            "artifacts": len(artifacts),
            "artifacts_ready": sum((self.root / rel).is_file() for rel in artifacts),
            "publication_authorized": bool(data.get("publication_authorized")),
            "endpoint": "/api/v235/third-wave-internal-approval",
        }

    def summary(self):
        data = json.loads(json.dumps(self.spec))
        candidates = self._candidate_integrity()
        artifacts = self._approval_artifacts()
        gates = data.get("quality_gates", [])
        current = self._current_consolidation()
        data["candidate_integrity"] = candidates
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
            "approved_positions": sum(len(x.get("approved_positions", [])) for x in data.get("products", [])),
            "mandatory_conditions": sum(len(x.get("mandatory_conditions", [])) for x in data.get("products", [])),
            "residual_risks": sum(len(x.get("residual_risks", [])) for x in data.get("products", [])),
            "verified_sources": len(data.get("normative_verification", [])),
            "source_conflicts": len(data.get("source_conflicts", [])),
            "candidate_files": len(candidates),
            "candidate_files_verified": sum(x.get("matches") for x in candidates),
            "candidate_hashes_preserved": sum(bool(x.get("archived_hash_preserved")) for x in candidates),
            "approval_artifacts": len(artifacts),
            "approval_artifacts_ready": sum(x.get("exists") and bool(x.get("sha256")) for x in artifacts),
            "approval_artifact_hashes_preserved": sum(bool(x.get("archived_hash_preserved")) for x in artifacts),
            "pending_gates": sum(x.get("status") in {"pending", "blocked"} for x in gates),
        }
        data["decision_integrity_ready"] = bool(candidates) and all(x.get("matches") for x in candidates)
        data["ready_for_human_ratification"] = False
        data["historical_decision_record_preserved"] = bool(
            len(candidates) == data["counts"]["candidate_hashes_preserved"] == 6
            and len(artifacts) == data["counts"]["approval_artifact_hashes_preserved"] == 8
        )
        data["current_ratification_target"] = "2.35"
        data["current_ratification_ready"] = bool(
            current.get("version") == "2.35"
            and current.get("products") == 11
            and current.get("scope_ratification_pending")
            and current.get("artifacts") == current.get("artifacts_ready")
            and not current.get("publication_authorized")
        )
        return data
