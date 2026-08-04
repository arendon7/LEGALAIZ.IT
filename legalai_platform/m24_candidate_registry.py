from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class M24CandidateRegistry:
    """Read-only view of M23.2 immutable candidate revisions.

    The registry deliberately does not activate or publish revisions. It exposes
    candidate evidence to specialist and administrator workflows while the
    legacy M21.1 generation binding remains active.
    """

    PRODUCT_CODES = (
        "CO-LA-001", "CO-LA-002", "CO-EM-003", "CO-EM-004", "CO-AR-001",
        "CO-SA-001", "CO-CD-001", "CO-CD-003", "CO-CD-004", "CO-TR-001", "CO-TR-002",
    )

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.manifest_path = self.root / "config" / "runtime_manifest.json"
        self.product_root = self.root / "data" / "legal_products"
        self.scenarios_path = self.root / "qa" / "legal_scenarios_m24.json"
        self.human_approval_path = self.root / "config" / "m24_10_human_approval_policy.json"

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _product(self, code: str) -> dict[str, Any] | None:
        normalized = str(code or "").upper()
        if normalized not in self.PRODUCT_CODES:
            return None
        path = self.product_root / normalized / "product.json"
        return self._load(path) if path.is_file() else None

    def _candidate_metadata(self, product: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
        code = product["product_code"]
        revision_id = product.get("candidate_revision")
        revision_dir = self.product_root / code / "revisions" / str(revision_id)
        metadata_path = revision_dir / "metadata.json"
        if not revision_id or not metadata_path.is_file():
            raise FileNotFoundError(f"Candidate revision unavailable for {code}")
        return revision_dir, self._load(metadata_path)

    def summary(self) -> dict[str, Any]:
        manifest = self._load(self.manifest_path)
        scenario_count = 0
        if self.scenarios_path.is_file():
            scenarios = self._load(self.scenarios_path)
            scenario_count = len(scenarios.get("scenarios", []))
        human_policy = self._load(self.human_approval_path) if self.human_approval_path.is_file() else {}
        human_products = {row.get("product_code"): row for row in human_policy.get("products", [])}
        rows = []
        for code in self.PRODUCT_CODES:
            product = self._product(code)
            if not product:
                continue
            revision_dir, metadata = self._candidate_metadata(product)
            rows.append({
                "product_code": code,
                "public_name": product.get("public_name"),
                "category": product.get("category"),
                "active_revision": product.get("active_revision"),
                "published_revision": product.get("published_revision"),
                "candidate_revision": product.get("candidate_revision"),
                "candidate_status": metadata.get("status"),
                "asset_count": len(metadata.get("asset_hashes", {})),
                "candidate_dir_present": revision_dir.is_dir(),
                "legal_approved": bool(metadata.get("approvals", {}).get("legal", {}).get("approved")) or human_products.get(code, {}).get("legal_decision") == "approved",
                "qa_approved": bool(metadata.get("approvals", {}).get("qa", {}).get("approved")) or human_products.get(code, {}).get("qa_decision") == "approved",
                "human_approval_attested": code in human_products,
                "approval_model": human_policy.get("approval_model") if code in human_products else "distinct_specialist_then_admin_qa",
                "independent_reviewers": human_policy.get("independent_reviewers") if code in human_products else True,
            })
        return {
            "schema": "legalai_m24_candidate_library_summary_v1",
            "integration": manifest,
            "product_count": len(rows),
            "candidate_revision_count": len(rows),
            "asset_count": sum(row["asset_count"] for row in rows),
            "scenario_count": scenario_count,
            "active_revision_changes": 0,
            "published_revision_changes": 0,
            "publication_blocked": True,
            "human_approval_milestone": human_policy.get("milestone"),
            "human_approval_attestation_sha256": human_policy.get("attestation_sha256"),
            "products": rows,
        }

    def detail(self, code: str) -> dict[str, Any] | None:
        product = self._product(code)
        if not product:
            return None
        revision_dir, metadata = self._candidate_metadata(product)
        human_policy = self._load(self.human_approval_path) if self.human_approval_path.is_file() else {}
        human_product = next((row for row in human_policy.get("products", []) if row.get("product_code") == product["product_code"]), None)
        assets = []
        roles = {}
        plan_path = self.root / "migration" / "integration_plan.json"
        if plan_path.is_file():
            plan = self._load(plan_path)
            operation = next((item for item in plan.get("operations", []) if item.get("product_code") == product["product_code"]), None)
            if operation:
                roles = {item["file_name"]: item.get("role") for item in operation.get("files", [])}
        for filename, expected_hash in sorted(metadata.get("asset_hashes", {}).items()):
            path = revision_dir / filename
            assets.append({
                "file_name": filename,
                "role": roles.get(filename, "evidence"),
                "format": path.suffix.lower().lstrip("."),
                "size_bytes": path.stat().st_size if path.is_file() else 0,
                "sha256": expected_hash,
                "present": path.is_file(),
                "download_url": f"/api/m24/candidate-library/{product['product_code']}/assets/{filename}",
            })
        return {
            "schema": "legalai_m24_candidate_product_detail_v1",
            "product_code": product["product_code"],
            "public_name": product.get("public_name"),
            "internal_name": product.get("internal_name"),
            "category": product.get("category"),
            "active_revision": product.get("active_revision"),
            "published_revision": product.get("published_revision"),
            "candidate_revision": product.get("candidate_revision"),
            "candidate_policy": product.get("candidate_policy", {}),
            "legacy_runtime_binding": product.get("legacy_runtime_binding", {}),
            "candidate_metadata": metadata,
            "human_approval": {
                "attested": bool(human_product),
                "milestone": human_policy.get("milestone"),
                "approval_model": human_policy.get("approval_model"),
                "independent_reviewers": human_policy.get("independent_reviewers"),
                "legal_approved": bool(human_product and human_product.get("legal_decision") == "approved"),
                "qa_approved": bool(human_product and human_product.get("qa_decision") == "approved"),
                "disclosure": human_policy.get("same_person_disclosure"),
                "public_production_authorized": human_policy.get("scope", {}).get("public_production_authorized", False),
            },
            "assets": assets,
        }

    def asset_path(self, code: str, filename: str) -> Path | None:
        product = self._product(code)
        if not product:
            return None
        if not filename or Path(filename).name != filename:
            return None
        revision_dir, metadata = self._candidate_metadata(product)
        expected = metadata.get("asset_hashes", {}).get(filename)
        if not expected:
            return None
        path = (revision_dir / filename).resolve()
        try:
            path.relative_to(revision_dir.resolve())
        except ValueError:
            return None
        if not path.is_file() or self._sha256(path) != expected:
            return None
        return path

    def verify_integrity(self) -> dict[str, Any]:
        checked = 0
        failures = []
        for code in self.PRODUCT_CODES:
            product = self._product(code)
            if not product:
                failures.append({"product_code": code, "error": "missing_product_registry"})
                continue
            revision_dir, metadata = self._candidate_metadata(product)
            for filename, expected in metadata.get("asset_hashes", {}).items():
                checked += 1
                path = revision_dir / filename
                if not path.is_file():
                    failures.append({"product_code": code, "file_name": filename, "error": "missing"})
                elif self._sha256(path) != expected:
                    failures.append({"product_code": code, "file_name": filename, "error": "hash_mismatch"})
        return {"ok": not failures, "checked_files": checked, "failures": failures}
