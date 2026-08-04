from __future__ import annotations

import json
from pathlib import Path


class GoldStandardCenter:
    """Registro acumulativo Gold Standard y prediagnóstico anónimo no persistente."""

    LEVEL_WEIGHT = {"green": 0, "yellow": 1, "red": 2}

    def __init__(self, root: Path, products, interviews, rules, sources, templates):
        self.root = Path(root)
        self.config, self.product_versions, self.config_files = self._load_config_chain()
        self.products = {item.get("code"): item for item in products}
        self.interviews = interviews
        self.rules = rules
        self.sources = sources
        self.templates = templates
        depth_path = self.root / "data" / "legal_depth_registry_m27.json"
        self.depth_registry = json.loads(depth_path.read_text(encoding="utf-8")) if depth_path.is_file() else {"products": {}}
        self.template_map = {}
        for template in templates:
            self.template_map.setdefault(template.get("product_code"), []).append(template)
        self._validate_config()
        self._validate_depth_registry()

    def _load_config_chain(self):
        data_dir = self.root / "data"
        base = data_dir / "gold_standard_products.json"
        files = [base] + sorted(
            path for path in data_dir.glob("gold_standard_products_*.json")
            if path.name != base.name
        )
        if not base.is_file():
            raise FileNotFoundError("No existe la configuración base Gold Standard.")

        merged = {"version": None, "status_label": "Gold Standard", "products": {}}
        product_versions = {}
        loaded_files = []
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            version = payload.get("version") or merged.get("version") or "Gold Standard"
            products = payload.get("products") or {}
            duplicates = sorted(set(products).intersection(merged["products"]))
            if duplicates:
                raise ValueError(f"Productos Gold Standard duplicados en {path.name}: {', '.join(duplicates)}")
            merged["products"].update(products)
            for code in products:
                product_versions[code] = version
            merged["version"] = version
            merged["status_label"] = payload.get("status_label") or merged["status_label"]
            loaded_files.append(path.name)
        return merged, product_versions, tuple(loaded_files)

    def _validate_config(self):
        for code, item in self.config.get("products", {}).items():
            if len(item.get("pillars") or []) != 5:
                raise ValueError(f"{code} debe declarar exactamente cinco pilares Gold Standard.")
            precheck = item.get("precheck") or {}
            questions = precheck.get("questions") or []
            if len(questions) != 4:
                raise ValueError(f"{code} debe declarar exactamente cuatro preguntas de prediagnóstico.")
            ids = [question.get("id") for question in questions]
            if None in ids or len(ids) != len(set(ids)):
                raise ValueError(f"{code} contiene identificadores de pregunta inválidos o duplicados.")
            allowed = {question["id"]: set(question.get("options") or []) for question in questions}
            for rule in precheck.get("rules") or []:
                field = rule.get("field")
                if field not in allowed:
                    raise ValueError(f"{code} contiene una regla para un campo inexistente: {field}")
                values = [rule.get("equals")] if "equals" in rule else list(rule.get("in") or [])
                if any(value not in allowed[field] for value in values):
                    raise ValueError(f"{code} contiene una regla con opción no permitida para {field}.")
                if rule.get("level") not in self.LEVEL_WEIGHT:
                    raise ValueError(f"{code} contiene un nivel de riesgo no permitido.")

    def _validate_depth_registry(self):
        products = self.depth_registry.get("products") or {}
        unknown = sorted(set(products) - set(self.products))
        if unknown:
            raise ValueError("El registro de profundidad contiene productos inexistentes: " + ", ".join(unknown))
        for code in self.config.get("products", {}):
            if code not in products:
                raise ValueError(f"{code} no tiene estado de profundidad jurídica M27.")
            item = products[code]
            if not item.get("status") or not item.get("public_label"):
                raise ValueError(f"{code} tiene un registro de profundidad incompleto.")
            if item.get("external_release_authorized") is not False:
                raise ValueError(f"{code} no puede declararse liberado externamente desde el registro M27.")

    @property
    def codes(self):
        return tuple(self.config.get("products", {}).keys())

    def _metrics(self, code):
        product = self.products.get(code) or {}
        interview = self.interviews.get(code) or {}
        templates = self.template_map.get(code) or []
        required = {
            "product": bool(product),
            "questions": len(interview.get("questions") or []) > 0,
            "rules": len(self.rules.get(code) or []) > 0,
            "sources": len(self.sources.get(code) or []) > 0,
            "templates": len(templates) > 0,
            "experience": code in self.config.get("products", {}),
        }
        depth = (self.depth_registry.get("products") or {}).get(code) or {}
        expected = int(depth.get("expected_document_count") or 0)
        integrated = len(templates)
        return {
            "question_count": len(interview.get("questions") or []),
            "rule_count": len(self.rules.get(code) or []),
            "source_count": len(self.sources.get(code) or []),
            "template_count": integrated,
            "expected_document_count": expected,
            "document_coverage_complete": bool(expected and integrated >= expected),
            "checks": required,
            "complete": all(required.values()),
        }

    def detail(self, code):
        config = self.config.get("products", {}).get(code)
        if not config:
            return None
        return {
            "product_code": code,
            "status": "Catálogo Gold",
            "version": self.product_versions.get(code) or self.config.get("version") or "Gold Standard",
            "catalog_version": self.config.get("version"),
            "config": config,
            "metrics": self._metrics(code),
            "legal_depth": dict((self.depth_registry.get("products") or {}).get(code) or {}),
            "anonymous_precheck": True,
            "precheck_persists_data": False,
        }

    def summary(self):
        items = [self.detail(code) for code in self.codes]
        depth_counts = {}
        for item in items:
            status = ((item or {}).get("legal_depth") or {}).get("status", "unregistered")
            depth_counts[status] = depth_counts.get(status, 0) + 1
        return {
            "version": self.config.get("version"),
            "status": "Catálogo Gold",
            "product_count": len(items),
            "complete_count": sum(bool(item and item["metrics"]["complete"]) for item in items),
            "integrated_specialized_count": depth_counts.get("integrated_specialized_package", 0),
            "depth_status_counts": depth_counts,
            "depth_registry_version": self.depth_registry.get("version"),
            "config_files": list(self.config_files),
            "products": items,
        }

    @staticmethod
    def _matches(rule, answers):
        value = answers.get(rule.get("field"))
        if "equals" in rule:
            return value == rule.get("equals")
        if "in" in rule:
            return value in (rule.get("in") or [])
        return False

    def precheck(self, code, answers):
        detail = self.detail(code)
        if not detail:
            raise ValueError("El producto no pertenece al catálogo Gold Standard.")
        if not isinstance(answers, dict):
            raise ValueError("Las respuestas deben enviarse como un objeto.")
        spec = detail["config"].get("precheck") or {}
        questions = spec.get("questions") or []
        allowed = {q["id"]: set(q.get("options") or []) for q in questions}
        missing = [q["id"] for q in questions if not answers.get(q["id"])]
        unknown = [key for key in answers if key not in allowed]
        invalid = [key for key, value in answers.items() if key in allowed and value not in allowed[key]]
        if missing:
            raise ValueError("Completa todas las preguntas del prediagnóstico.")
        if unknown:
            raise ValueError("La solicitud contiene campos que no pertenecen al prediagnóstico.")
        if invalid:
            raise ValueError("Una o más respuestas no pertenecen a las opciones permitidas.")
        alerts = [dict(rule) for rule in (spec.get("rules") or []) if self._matches(rule, answers)]
        level = max(
            (rule.get("level", "green") for rule in alerts),
            key=lambda value: self.LEVEL_WEIGHT.get(value, 0),
            default="green",
        )
        labels = {
            "green": "Compatible con el recorrido estándar",
            "yellow": "Puedes avanzar con alertas",
            "red": "Necesita revisión profesional antes de continuar",
        }
        service = "solucion_revisada" if level == "red" else "documento_personalizado"
        return {
            "product_code": code,
            "risk": level,
            "label": labels[level],
            "alerts": [{"level": item.get("level"), "message": item.get("message")} for item in alerts],
            "recommended_service": service,
            "next_action": "Crea una cuenta segura para continuar con el formulario completo y conservar la trazabilidad.",
            "data_saved": False,
            "disclaimer": "Resultado preliminar informativo. No constituye concepto jurídico ni garantiza procedencia.",
        }
