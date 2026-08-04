from __future__ import annotations
from datetime import date, datetime
import json
from pathlib import Path

class InternalLegalApprovalV228:
    """Decisiones internas v2.28 sin sustituir la confirmación final del abogado responsable."""
    def __init__(self, root: Path):
        self.root=Path(root)
        self.spec=json.loads((self.root/"data"/"internal_legal_approval_v228.json").read_text(encoding="utf-8"))
    @staticmethod
    def _as_date(value):
        if isinstance(value,date): return value
        return datetime.strptime(str(value)[:10],"%Y-%m-%d").date()
    def labor_parameters(self, on_date=None):
        d=self._as_date(on_date or date.today())
        base=dict(self.spec.get("labor_parameters",{}))
        base["weekly_hours"]=42 if d>=date(2026,7,15) else (44 if d>=date(2025,7,15) else 46)
        base["night_start"]="19:00" if d>=date(2025,12,25) else "21:00"
        base["rest_day_surcharge_percent"]=100 if d>=date(2027,7,1) else (90 if d>=date(2026,7,1) else (80 if d>=date(2025,7,1) else 75))
        base["calculated_for"]=d.isoformat()
        return base
    def summary(self, on_date=None):
        products=list(self.spec.get("products",[])); gates=list(self.spec.get("quality_gates",[]))
        return {**self.spec,"labor_parameters":self.labor_parameters(on_date),"counts":{"products":len(products),"decisions":sum(len(x.get("decisions",[])) for x in products),"blocks":sum(len(x.get("blocks",[])) for x in products),"sources":len(self.spec.get("sources",[])),"gates":len(gates),"pending_gates":sum(x.get("status") in {"pending","blocked"} for x in gates)}}
