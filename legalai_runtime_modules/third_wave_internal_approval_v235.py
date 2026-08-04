from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ThirdWaveInternalApprovalV235:
    """Aprobación jurídica interna asistida de la tercera ola y consolidación global.

    No sustituye ratificación del abogado responsable ni aprobación dual.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "data" / "third_wave_internal_approval_v235.json"
        self.spec = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def _sha(path: Path) -> str | None:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

    def _product_integrity(self):
        rows = []
        for product in self.spec.get("products", []):
            folder = self.root / product["integrity"]["folder"]
            files = sorted(p for p in folder.iterdir() if p.is_file()) if folder.is_dir() else []
            aggregate = hashlib.sha256(
                "".join(f"{p.name}:{self._sha(p)}\n" for p in files).encode("utf-8")
            ).hexdigest() if files else None
            rows.append({
                "product": product["code"],
                "folder": product["integrity"]["folder"],
                "exists": folder.is_dir(),
                "files_expected": product["integrity"]["files"],
                "files_actual": len(files),
                "expected_sha256": product["integrity"]["aggregate_sha256"],
                "actual_sha256": aggregate,
                "matches": bool(aggregate and aggregate == product["integrity"]["aggregate_sha256"] and len(files) == product["integrity"]["files"]),
            })
        return rows

    def _artifacts(self):
        rows = []
        for rel in self.spec.get("approval_documents", []):
            path = self.root / rel
            rows.append({
                "path": rel,
                "format": path.suffix.lstrip(".").upper(),
                "exists": path.is_file(),
                "sha256": self._sha(path),
                "bytes": path.stat().st_size if path.is_file() else 0,
            })
        return rows

    def summary(self):
        data = json.loads(json.dumps(self.spec))
        integrity = self._product_integrity()
        artifacts = self._artifacts()
        gates = data.get("quality_gates", [])
        consolidated = data.get("consolidated_products", [])
        data["product_integrity"] = integrity
        data["artifact_registry"] = artifacts
        data["counts"] = {
            "third_wave_products": len(data.get("products", [])),
            "consolidated_products": len(consolidated),
            "approved_positions": sum(len(x.get("approved_positions", [])) for x in data.get("products", [])),
            "mandatory_conditions": sum(len(x.get("mandatory_conditions", [])) for x in data.get("products", [])),
            "residual_risks": sum(len(x.get("residual_risks", [])) for x in data.get("products", [])),
            "verified_source_links": sum(len(x.get("verified_sources", [])) for x in data.get("products", [])),
            "product_integrity_verified": sum(bool(x.get("matches")) for x in integrity),
            "approval_artifacts": len(artifacts),
            "approval_artifacts_ready": sum(bool(x.get("exists") and x.get("sha256")) for x in artifacts),
            "internal_approvals_completed": sum(x.get("internal_legal_status") == "Aprobación jurídica interna asistida completada" for x in consolidated),
            "human_ratifications_pending": sum(x.get("human_ratification") == "Pendiente" for x in consolidated),
            "professional_publications_authorized": sum(x.get("professional_publication") != "Bloqueada" for x in consolidated),
            "pending_or_blocked_gates": sum(x.get("status") in {"pending", "blocked"} for x in gates),
        }
        data["integrity_ready"] = bool(integrity) and all(x.get("matches") for x in integrity)
        data["third_wave_decision_ready"] = bool(
            data.get("internal_legal_approval_completed")
            and data["integrity_ready"]
            and not data.get("publication_authorized")
        )
        data["all_products_consolidated"] = len(consolidated) == 11 and data["counts"]["internal_approvals_completed"] == 11
        return data
