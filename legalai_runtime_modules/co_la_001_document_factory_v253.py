from __future__ import annotations

from pathlib import Path

from co_la_001_document_factory_v252 import CoLa001DocumentFactoryV252
from economic_calculation_engine import reconcile_line_items
from legalai_platform.document_quality import assert_docx_quality
from legalai_platform.document_visual_quality import assert_visual_structure


class CoLa001DocumentFactoryV253(CoLa001DocumentFactoryV252):
    VERSION = "2.53"

    def __init__(self, root, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = self.root / "data" / "generated" / "co-la-001-v253"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def calculate(self, answers):
        result = super().calculate(answers)
        if self._v(answers, "compensation.salary_type") == "integral":
            # En salario integral, cesantías, intereses y prima están compensados
            # anticipadamente; vacaciones e indemnización conservan tratamiento separado.
            excluded = {"cesantias", "cesantias_interest", "prima"}
            prior_excluded = 0.0
            for item in result["line_items"]:
                if item["key"] in excluded:
                    prior_excluded += item.get("prior_paid", 0.0)
                    item["gross"] = 0.0
                    item["prior_paid"] = 0.0
                    item["net"] = 0.0
                    item["formula"] = "Compensado por salario integral durante el pacto válido."
            result["interest_segments"] = []
            result["benefit_base"] = 0.0
            result["transport_aid_applied"] = False
            result["transport_aid_value"] = 0.0
            result["gross_total"] = round(sum(item["gross"] for item in result["line_items"]), 2)
            result["prior_payments_total"] = round(sum(item["prior_paid"] for item in result["line_items"]), 2)
            result["net_total"] = round(sum(item["net"] for item in result["line_items"]), 2)
            result["notes"] = [note for note in result.get("notes", []) if "auxilio de transporte" not in note.lower()]
            result["notes"].append("El cálculo trató cesantías, intereses y prima como compensados dentro del salario integral durante la vigencia válida del pacto escrito.")
            result["notes"].append("Las vacaciones y la indemnización se calcularon sobre la suma integral informada; debe verificarse el pacto escrito y su fecha de vigencia.")
            if prior_excluded:
                result["notes"].append("Se informaron pagos previos en conceptos normalmente integrados; deben conciliarse por separado y no fueron imputados automáticamente.")
            result["assumptions"].append("El tratamiento integral solo cubre los períodos en los que existió un pacto escrito válido y se cumplió el umbral legal aplicable.")
            result["integral_salary_treatment"] = True

        reconciliation = reconcile_line_items(
            result.get("line_items", []),
            gross_total=result.get("gross_total", 0),
            prior_total=result.get("prior_payments_total", 0),
            net_total=result.get("net_total", 0),
        )
        result["economic_reconciliation"] = reconciliation
        result["calculation_engine_version"] = "3.9.0-m28.2"
        if not reconciliation["valid"]:
            result.setdefault("notes", []).append("El control económico detectó una diferencia entre renglones y totales; el documento debe bloquearse hasta conciliarla.")
        return result

    def _period_for_key(self, calc, key):
        p = calc["periods"]
        if key in {"cesantias", "cesantias_interest"}:
            return f"{self._date_es(p['cesantias']['start'])} a {self._date_es(p['cesantias']['end'])} · {p['cesantias']['days_30_360']} días"
        if key == "prima":
            return f"{self._date_es(p['prima']['start'])} a {self._date_es(p['prima']['end'])} · {p['prima']['days_30_360']} días"
        if key == "vacation":
            return f"{p['vacation']['pending_days']} días pendientes"
        return f"{self._date_es(p['employment']['start'])} a {self._date_es(p['employment']['end'])}"

    def render_documents(self, answers, target_folder):
        evaluation, generated, hashes, calculation = super().render_documents(answers, target_folder)
        target_folder = Path(target_folder)
        for item in generated:
            path = target_folder / item["filename"]
            quality = assert_docx_quality(path, expected_product="CO-LA-001")
            visual = assert_visual_structure(path, expected_product="CO-LA-001")
            item["quality"] = {
                "valid": quality["valid"],
                "warnings": quality["warnings"],
                "metrics": quality["metrics"],
            }
            item["visual_preflight"] = {
                "valid": visual["valid"],
                "warnings": visual["warnings"],
                "metrics": visual["metrics"],
                "requires_human_visual_review": True,
            }
            hashes[item["filename"]] = quality["sha256"]
        return evaluation, generated, hashes, calculation
