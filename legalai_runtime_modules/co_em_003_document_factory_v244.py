from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from co_em_003_document_factory_v243 import CoEm003DocumentFactoryV243
from legalai_platform.document_quality import assert_docx_quality


class CoEm003DocumentFactoryV244(CoEm003DocumentFactoryV243):
    VERSION = "2.44"

    def __init__(self, root, evaluator):
        super().__init__(root, evaluator)
        self.output_dir = self.root / "data" / "generated" / "co-em-003-v244"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read(data: dict, path: str):
        current = data
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    @classmethod
    def _first(cls, data: dict, paths: tuple[str, ...]):
        for path in paths:
            value = cls._read(data, path)
            if value not in (None, "", [], {}):
                return value
        return None

    @staticmethod
    def _write_if_empty(data: dict, path: str, value):
        if value in (None, "", [], {}):
            return
        parts = path.split(".")
        current = data
        for part in parts[:-1]:
            node = current.get(part)
            if not isinstance(node, dict):
                node = {}
                current[part] = node
            current = node
        if current.get(parts[-1]) in (None, "", [], {}):
            current[parts[-1]] = value

    @classmethod
    def _normalize_party(cls, answers: dict, prefix: str, aliases: tuple[str, ...]):
        current = cls._read(answers, f"{prefix}.identification")
        if isinstance(current, dict):
            identification = deepcopy(current)
        elif current not in (None, ""):
            identification = {"identification": current}
        else:
            identification = {}

        name_paths = tuple(f"{prefix}.{field}" for field in ("legal_name", "legalName", "full_name", "fullName", "name"))
        id_paths = tuple(f"{prefix}.{field}" for field in ("nit", "id_number", "idNumber", "identification_number", "identificationNumber"))
        alias_names = tuple(f"{alias}.name" for alias in aliases) + tuple(f"{alias}.legal_name" for alias in aliases)
        alias_ids = tuple(f"{alias}.identification" for alias in aliases) + tuple(f"{alias}.id_number" for alias in aliases)

        name = cls._first(answers, name_paths + alias_names)
        number = cls._first(answers, id_paths + alias_ids)
        domicile = cls._first(answers, tuple(f"{prefix}.{field}" for field in ("domicile", "address", "city")))
        email = cls._first(answers, (f"{prefix}.email",))
        if name not in (None, ""):
            identification.setdefault("name", name)
        if number not in (None, ""):
            identification.setdefault("identification_number", number)
        if domicile not in (None, ""):
            identification.setdefault("domicile", domicile)
        if email not in (None, ""):
            identification.setdefault("email", email)
        cls._write_if_empty(answers, f"{prefix}.identification", identification)

        signatory = cls._read(answers, f"{prefix}.signatory")
        if signatory in (None, "", {}):
            representative = cls._first(
                answers,
                (
                    f"{prefix}.representative",
                    f"{prefix}.legal_representative",
                    f"{prefix}.legalRepresentative",
                ),
            )
            cls._write_if_empty(answers, f"{prefix}.signatory", representative)

    @classmethod
    def _normalize_answers(cls, source: dict) -> dict:
        """Map supported legacy aliases without inventing facts or overwriting canonical answers."""
        answers = deepcopy(source or {})
        cls._normalize_party(answers, "client", ("customer", "contracting_party"))
        cls._normalize_party(answers, "contractor", ("provider", "service_provider"))

        mappings = {
            "service.object": ("contract.object", "scope.object", "object", "service.description"),
            "service.expected_result": ("contract.expected_result", "scope.expected_result", "service.result", "expected_result"),
            "scope.included": ("scope.services", "scope.activities", "service.scope", "included_scope"),
            "scope.excluded": ("scope.exclusions", "excluded_scope"),
            "scope.deliverables": ("service.deliverables", "deliverables"),
            "scope.acceptance_criteria": ("service.acceptance_criteria", "acceptance_criteria"),
        }
        for target, aliases in mappings.items():
            cls._write_if_empty(answers, target, cls._first(answers, aliases))
        return answers

    def render_documents(self, answers, target_folder):
        normalized = self._normalize_answers(answers)
        evaluation, generated, hashes = super().render_documents(normalized, target_folder)
        target_folder = Path(target_folder)
        for item in generated:
            report = assert_docx_quality(target_folder / item["filename"], expected_product="CO-EM-003")
            item["quality"] = {
                "valid": report["valid"],
                "warnings": report["warnings"],
                "metrics": report["metrics"],
            }
            hashes[item["filename"]] = report["sha256"]
        return evaluation, generated, hashes

    def generate(self, answers, actor=None):
        return super().generate(self._normalize_answers(answers), actor=actor)
