from __future__ import annotations
import json
from pathlib import Path

class LegalApprovalV227:
    """Continuidad funcional reconstruida de la primera ola v2.27."""
    def __init__(self, root: Path):
        self.root=Path(root)
        self.spec=json.loads((self.root/"data"/"legal_approval_v227.json").read_text(encoding="utf-8"))
    def summary(self):
        products=list(self.spec.get("products",[]))
        return {**self.spec,"counts":{"products":len(products),"clauses":sum(int(x.get("clauses",0)) for x in products),"gates":len(self.spec.get("gates",[]))}}
