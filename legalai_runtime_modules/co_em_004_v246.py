from __future__ import annotations

from co_em_004_v245 import CoEm004CanonicalV245


class CoEm004CanonicalV246(CoEm004CanonicalV245):
    """Capa canónica documental y de gobierno de CO-EM-004 v2.46."""

    VERSION = "2.46"

    def summary(self):
        result = super().summary()
        result["manifest"] = dict(result["manifest"])
        result["manifest"].update({
            "version": self.VERSION,
            "status": "macro_b_documental_governance",
            "document_factory": True,
            "governance": True,
        })
        return result

    def evaluate(self, answers):
        result = super().evaluate(answers)
        result["version"] = self.VERSION
        result["review_requirements"] = [
            {
                "id": item["id"],
                "severity": item["severity"],
                "message": item["message"],
            }
            for item in result.get("findings", [])
            if item.get("severity") in {"blocker", "review"}
        ]
        if result.get("blocked"):
            result["readiness"] = "blocked"
        elif result.get("missing_fields"):
            result["readiness"] = "incomplete"
        elif result.get("professional_review_required"):
            result["readiness"] = "requires_review"
        else:
            result["readiness"] = "ready"
        return result
