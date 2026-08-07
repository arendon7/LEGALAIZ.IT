from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

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

    @staticmethod
    def _join_values(*values) -> str:
        parts = []
        for value in values:
            if value in (None, "", [], {}):
                continue
            if isinstance(value, (list, tuple)):
                parts.extend(str(item).strip() for item in value if str(item).strip())
            else:
                text = str(value).strip()
                if text:
                    parts.append(text)
        return "; ".join(parts)

    @staticmethod
    def _strip_leading_infinitive(value, infinitive: str):
        if not isinstance(value, str):
            return value
        text = value.strip()
        prefix = infinitive.strip().casefold() + " "
        return text[len(prefix):].strip() if text.casefold().startswith(prefix) else text

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
    def _normalize_compound_fields(cls, answers: dict):
        """Adapta estructuras canónicas modernas al contrato profundo v2.43."""
        service = answers.get("service")
        if isinstance(service, dict):
            service["object"] = cls._strip_leading_infinitive(service.get("object"), "prestar")
            service["expected_result"] = cls._strip_leading_infinitive(service.get("expected_result"), "entregar")

        schedule = answers.get("schedule")
        if isinstance(schedule, dict):
            cls._write_if_empty(
                answers,
                "term",
                {
                    key: schedule.get(key)
                    for key in ("start_date", "end_date", "duration", "renewal")
                    if schedule.get(key) not in (None, "", [], {})
                },
            )
            schedule_text = cls._join_values(
                schedule.get("milestones"),
                schedule.get("dependencies"),
                schedule.get("client_delays"),
            )
            answers["schedule"] = schedule_text or "el cronograma y los hitos aprobados por las partes"

        fees = answers.get("fees")
        if isinstance(fees, dict) and not isinstance(fees.get("financial_terms"), dict):
            financial_terms = {
                "amount": fees.get("amount"),
                "currency": fees.get("currency"),
                "payment_terms": fees.get("payment_term") or fees.get("payment_terms"),
                "invoice_requirements": fees.get("invoice"),
                "taxes": fees.get("taxes") or fees.get("retentions"),
            }
            fees["financial_terms"] = {
                key: value for key, value in financial_terms.items() if value not in (None, "", [], {})
            }

        risk = answers.get("risk")
        if isinstance(risk, dict):
            cls._write_if_empty(answers, "risk_allocation", risk.get("allocation"))
            cls._write_if_empty(answers, "liability", risk.get("liability"))

        termination = answers.get("termination")
        if isinstance(termination, dict):
            answers["termination"] = cls._join_values(
                termination.get("rules"),
                (
                    f"Los incumplimientos subsanables tendrán un período de corrección de {termination.get('cure_period')}"
                    if termination.get("cure_period")
                    else None
                ),
            ) or "las causales y períodos de subsanación definidos en el contrato"

        closure = answers.get("closure")
        if isinstance(closure, dict):
            answers["closure"] = cls._join_values(
                closure.get("transition"),
                closure.get("return_destroy"),
            ) or "entrega ordenada, devolución de activos, cierre de accesos y acta final"

        data = answers.get("data")
        if isinstance(data, dict):
            cls._write_if_empty(answers, "data_processing.roles", data.get("roles"))
            cls._write_if_empty(answers, "data_processing.details", data.get("security"))

        ip = answers.get("ip")
        if isinstance(ip, dict):
            cls._write_if_empty(
                answers,
                "ip.details",
                cls._join_values(ip.get("preexisting"), ip.get("results"), ip.get("third_party")),
            )

    @classmethod
    def _normalize_answers(cls, source: dict) -> dict:
        """Map supported aliases without inventing facts or overwriting canonical answers."""
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
        cls._normalize_compound_fields(answers)
        return answers

    @staticmethod
    def _remove_forced_signature_break(path: Path) -> bool:
        """Retira solo el salto manual inmediatamente anterior a FIRMAS."""
        doc = Document(path)
        changed = False
        paragraphs = list(doc.paragraphs)
        for index, paragraph in enumerate(paragraphs):
            if paragraph.text.strip().casefold() != "firmas" or index == 0:
                continue
            previous = paragraphs[index - 1]
            for element in list(previous._p.iter(qn("w:br"))):
                if element.get(qn("w:type")) == "page":
                    parent = element.getparent()
                    parent.remove(element)
                    changed = True
            if changed and not previous.text.strip() and not list(previous._p.iter(qn("w:drawing"))):
                parent = previous._p.getparent()
                parent.remove(previous._p)
            break
        if changed:
            doc.save(path)
        return changed

    def render_documents(self, answers, target_folder):
        normalized = self._normalize_answers(answers)
        evaluation, generated, hashes = super().render_documents(normalized, target_folder)
        target_folder = Path(target_folder)
        for item in generated:
            target = target_folder / item["filename"]
            if item.get("id") == "DOC-EM-CONTRACT-001":
                self._remove_forced_signature_break(target)
            report = assert_docx_quality(target, expected_product="CO-EM-003")
            item["quality"] = {
                "valid": report["valid"],
                "warnings": report["warnings"],
                "metrics": report["metrics"],
            }
            hashes[item["filename"]] = report["sha256"]
        return evaluation, generated, hashes

    def generate(self, answers, actor=None):
        return super().generate(self._normalize_answers(answers), actor=actor)
