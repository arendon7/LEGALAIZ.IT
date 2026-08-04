from __future__ import annotations

import copy
import json
from pathlib import Path


class ApprovalRegistry:
    """Canonical M3 controlled-approval registry.

    Approval is multi-stage but performed by one responsible lawyer. Public
    payloads deliberately exclude the approver's identification number.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "governance" / "m3" / "APPROVAL_REGISTRY.json"
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.by_code = {item["product_code"]: item for item in self.data.get("products", [])}

    @property
    def publication_authorized(self) -> bool:
        return bool(self.data.get("professional_publication_authorized"))

    def apply_to_products(self, products):
        for product in products:
            approval = self.by_code.get(product.get("code"))
            if not approval:
                continue
            product["professional_use"] = True
            product["publication_status"] = "Aprobado para uso profesional controlado"
            product["publication_authorized"] = True
            product["human_ratification"] = True
            product["specialist_approval"] = True
            product["qa_approval"] = True
            product["dual_approval"] = True
            product["approval_status"] = "approved_controlled"
            product["approval_model"] = "multi_stage_single_responsible"
            product["independent_reviewers"] = False
            product["approved_at"] = approval.get("approved_at")
            product["case_specific_review_required"] = approval.get("case_specific_review_required", False)
            product["approval_disclosure"] = self.data.get("disclosure")
            product["controlled_use_conditions"] = list(self.data.get("controlled_use_conditions", []))
            product["internal_legal_approval"] = {
                "status": "approved_controlled",
                "human_ratification": True,
                "specialist_approval": True,
                "qa_approval": True,
                "dual_approval": True,
                "publication_authorized": True,
                "approval_model": "multi_stage_single_responsible",
                "independent_reviewers": False,
                "approved_at": approval.get("approved_at"),
                "approver": copy.deepcopy(self.data.get("approver_public", {})),
                "case_specific_review_required": approval.get("case_specific_review_required", False),
                "disclosure": self.data.get("disclosure"),
            }
        return products

    def public_summary(self):
        return {
            "version": self.data.get("version"),
            "build_id": self.data.get("build_id"),
            "catalog_status": self.data.get("catalog_status"),
            "professional_publication_authorized": self.publication_authorized,
            "approval_model": self.data.get("approval_model"),
            "independent_reviewers": False,
            "approver": copy.deepcopy(self.data.get("approver_public", {})),
            "approved_at": self.data.get("approved_at"),
            "product_count": self.data.get("product_count"),
            "document_count": self.data.get("document_count"),
            "disclosure": self.data.get("disclosure"),
            "controlled_use_conditions": list(self.data.get("controlled_use_conditions", [])),
            "products": [
                {k: v for k, v in item.items() if k not in {"approval_event_hashes", "document_aggregate_sha256"}}
                for item in self.data.get("products", [])
            ],
        }

    def product_public(self, code: str):
        item = self.by_code.get(code)
        if not item:
            return None
        result = {k: v for k, v in item.items() if k not in {"approval_event_hashes", "document_aggregate_sha256"}}
        result["approval_model"] = self.data.get("approval_model")
        result["independent_reviewers"] = False
        result["approver"] = copy.deepcopy(self.data.get("approver_public", {}))
        result["disclosure"] = self.data.get("disclosure")
        return result

    def internal_summary(self):
        return copy.deepcopy(self.data)
