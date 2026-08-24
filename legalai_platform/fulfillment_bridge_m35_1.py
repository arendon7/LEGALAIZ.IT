from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from legalai_platform.handoff_m35_0 import AccountHandoffStore, HandoffStateError
from legalai_platform.m34_intelligent_journey import fact_is_decision_usable


ROOT = Path(__file__).resolve().parents[1]
MAPPINGS_PATH = ROOT / "config" / "m35" / "fulfillment_fact_mappings.json"
QUESTION_CONTRACTS_PATH = ROOT / "config" / "m34" / "question_contracts.json"
INTERVIEWS_PATH = ROOT / "data" / "interviews.json"
SCHEMA_VERSION = "35.1.0"
SAFE_STATUSES = {"EXACT", "TRANSFORM_REQUIRED", "NO_SAFE_MAP"}
DIRECT_IDENTIFIER_IDS = {
    "requester_name", "requester_id", "petitioner_name", "petitioner_id", "email", "phone",
    "address", "provider_name", "creditor_name", "debtor_name", "employer_name", "worker_name",
    "client_name", "contractor_name", "lessor_name", "tenant_name", "property",
}


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _money_amount(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Mapping):
        raw = value.get("amount_cop")
    else:
        raw = value
    try:
        amount = int(float(raw))
    except (TypeError, ValueError):
        return None
    return amount if 0 <= amount <= 10_000_000_000_000 else None


def _text(value: Any, minimum: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    return normalized if len(normalized) >= minimum else None


def _date_iso(value: Any) -> str | None:
    text = str(value or "").strip()
    if len(text) != 10:
        return None
    try:
        year, month, day = [int(part) for part in text.split("-")]
        datetime(year, month, day)
    except (TypeError, ValueError):
        return None
    return text


def _value_map(mapping: Mapping[str, Any], value: Any) -> Any:
    return mapping.get(str(value))


NDA_RELATIONSHIP = {
    "prestacion_servicios": "Comercial/proveedor",
    "empleo": "Laboral/colaborador",
    "proveedor_cliente": "Comercial/proveedor",
    "otro": "Otra",
}
NDA_CATEGORY_LABELS = {
    "comercial": "Información comercial o estratégica",
    "financiera": "Información financiera",
    "tecnica": "Información técnica o know-how",
    "software_codigo": "Software o código fuente",
    "bases_datos": "Bases de datos",
    "datos_personales": "Datos personales",
    "secretos_empresariales": "Secretos empresariales",
    "otra": "Otra información definida por las partes",
}
PERSONAL_DATA = {"no": "No", "si_generales": "Sí", "si_sensibles": "Sí", "no_se": "No sé"}
PRIOR_CLAIM = {"PRIOR_CLAIM_ASSERTED": "Sí", "NO_PRIOR_CLAIM": "No"}
CONSUMER_REQUEST_MODE = {
    "GARANTIA": "Garantía legal",
    "RETRACTO": "Derecho de retracto",
    "REVERSION_PAGO": "Reversión del pago",
}
HEALTH_ENTITY = {"eps": "EPS", "ips": "IPS", "gestor_farmaceutico": "Gestor farmacéutico", "otra": "Otra"}
HEALTH_NEED = {
    "autorizacion": "Autorización o servicio",
    "medicamento": "Medicamento o insumo",
    "cita": "Cita o procedimiento",
    "procedimiento": "Cita o procedimiento",
    "historia_documentos": "Historia clínica",
    "respuesta_informacion": "Información o documentos",
}


def transform_value(name: str, value: Any) -> Any:
    if name == "DATE_ISO":
        return _date_iso(value)
    if name == "MONEY_COP_TO_NUMBER":
        return _money_amount(value)
    if name == "TEXT_MIN_3":
        return _text(value, 3)
    if name == "TEXT_MIN_20":
        return _text(value, 20)
    if name == "NDA_RELATIONSHIP_TO_RUNTIME":
        return _value_map(NDA_RELATIONSHIP, value)
    if name == "NDA_CATEGORIES_TO_TEXT":
        if not isinstance(value, list) or not value:
            return None
        labels = [NDA_CATEGORY_LABELS.get(str(item)) for item in value]
        if not all(labels):
            return None
        rendered = "; ".join(labels)
        return rendered if len(rendered) >= 15 else None
    if name == "PERSONAL_DATA_TO_YES_NO_UNKNOWN":
        return _value_map(PERSONAL_DATA, value)
    if name == "PRIOR_CLAIM_TO_YES_NO":
        return _value_map(PRIOR_CLAIM, value)
    if name == "CONSUMER_ISSUE_TO_REQUEST_MODE":
        return _value_map(CONSUMER_REQUEST_MODE, value)
    if name == "HEALTH_ENTITY_TO_RUNTIME":
        return _value_map(HEALTH_ENTITY, value)
    if name == "HEALTH_NEED_TO_RUNTIME":
        return _value_map(HEALTH_NEED, value)
    raise ValueError(f"Transformación M35.1 no soportada: {name}")


@dataclass(frozen=True)
class MappingValidation:
    ok: bool
    errors: tuple[str, ...]
    combinations: int
    reusable: int
    no_safe_map: int


class FulfillmentFactBridge:
    def __init__(self, root: Path = ROOT):
        self.root = Path(root)
        self.registry = _load_json(self.root / "config" / "m35" / "fulfillment_fact_mappings.json")
        self.question_contracts = _load_json(self.root / "config" / "m34" / "question_contracts.json")
        self.interviews = _load_json(self.root / "data" / "interviews.json")
        self.mappings = {
            (row["product_code"], row["fact_type"]): row
            for row in self.registry.get("mappings", [])
            if isinstance(row, dict)
        }

    def expected_combinations(self) -> set[tuple[str, str]]:
        expected: set[tuple[str, str]] = set()
        for question in self.question_contracts.get("fact_questions", []):
            if question.get("requirement_mode") != "TRIAGE_REQUIRED":
                continue
            for product_code in question.get("products", []):
                expected.add((str(product_code), str(question.get("fact_type"))))
        return expected

    def deferred_combinations(self) -> set[tuple[str, str]]:
        deferred: set[tuple[str, str]] = set()
        for question in self.question_contracts.get("fact_questions", []):
            if question.get("requirement_mode") != "FULFILLMENT_ONLY":
                continue
            for product_code in question.get("products", []):
                deferred.add((str(product_code), str(question.get("fact_type"))))
        return deferred

    def _question(self, product_code: str, question_id: str) -> dict[str, Any] | None:
        interview = self.interviews.get(product_code) or {}
        return next(
            (row for row in interview.get("questions", []) if str(row.get("id")) == question_id),
            None,
        )

    def validate(self) -> MappingValidation:
        errors: list[str] = []
        rows = self.registry.get("mappings", [])
        if not isinstance(rows, list):
            return MappingValidation(False, ("mappings must be an array",), 0, 0, 0)
        keys = [(str(row.get("product_code")), str(row.get("fact_type"))) for row in rows if isinstance(row, dict)]
        if len(keys) != len(set(keys)):
            errors.append("duplicate product/fact mapping")
        expected = self.expected_combinations()
        actual = set(keys)
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            errors.append(f"missing triage mappings: {missing}")
        if extra:
            errors.append(f"unexpected mappings: {extra}")
        if actual & self.deferred_combinations():
            errors.append(f"FULFILLMENT_ONLY fact mapped: {sorted(actual & self.deferred_combinations())}")

        reusable = 0
        no_safe = 0
        for row in rows:
            if not isinstance(row, dict):
                errors.append("mapping row must be an object")
                continue
            code = str(row.get("product_code") or "")
            fact_type = str(row.get("fact_type") or "")
            status = str(row.get("status") or "")
            if code not in self.interviews:
                errors.append(f"{code}/{fact_type}: unknown product")
            if status not in SAFE_STATUSES:
                errors.append(f"{code}/{fact_type}: unsupported status {status}")
                continue
            if status == "NO_SAFE_MAP":
                no_safe += 1
                if row.get("target_question_id"):
                    errors.append(f"{code}/{fact_type}: NO_SAFE_MAP cannot define target")
                continue
            reusable += 1
            target = str(row.get("target_question_id") or "")
            transform = str(row.get("transform") or "")
            if not target or not transform:
                errors.append(f"{code}/{fact_type}: reusable mapping requires target and transform")
                continue
            if target in DIRECT_IDENTIFIER_IDS:
                errors.append(f"{code}/{fact_type}: direct identifier target is prohibited")
            question = self._question(code, target)
            if not question:
                errors.append(f"{code}/{fact_type}: target question {target} does not exist")
                continue
            try:
                transform_value(transform, None)
            except ValueError as exc:
                errors.append(f"{code}/{fact_type}: {exc}")

            # Validate every transformable enumerated source value against target options.
            source = next(
                (
                    q for q in self.question_contracts.get("fact_questions", [])
                    if q.get("fact_type") == fact_type and code in q.get("products", [])
                ),
                None,
            ) or {}
            target_options = {str(item) for item in question.get("options", [])}
            if source.get("options") and target_options:
                for option in source.get("options", []):
                    source_value = option.get("value") if isinstance(option, dict) else option
                    try:
                        rendered = transform_value(transform, source_value)
                    except ValueError:
                        rendered = None
                    if rendered is not None and str(rendered) not in target_options:
                        errors.append(
                            f"{code}/{fact_type}: transform {transform} returns {rendered!r} outside {target} options"
                        )
        return MappingValidation(
            ok=not errors,
            errors=tuple(errors),
            combinations=len(expected),
            reusable=reusable,
            no_safe_map=no_safe,
        )

    def mapping_for(self, product_code: str, fact_type: str) -> dict[str, Any]:
        try:
            return self.mappings[(product_code, fact_type)]
        except KeyError as exc:
            raise KeyError(f"No M35.1 mapping for {product_code}/{fact_type}") from exc

    def build_prefill(self, product_code: str, facts: list[Mapping[str, Any]]) -> dict[str, Any]:
        if product_code not in self.interviews:
            raise KeyError(product_code)
        validation = self.validate()
        if not validation.ok:
            raise ValueError("M35.1 mapping registry invalid: " + "; ".join(validation.errors))

        by_type: dict[str, Mapping[str, Any]] = {}
        for fact in facts:
            if not fact_is_decision_usable(fact):
                continue
            fact_type = str(fact.get("fact_type") or "")
            if (product_code, fact_type) in self.mappings:
                by_type[fact_type] = fact

        answers: dict[str, Any] = {}
        reused: list[dict[str, str]] = []
        skipped: list[dict[str, str]] = []
        for (code, fact_type), mapping in sorted(self.mappings.items()):
            if code != product_code:
                continue
            fact = by_type.get(fact_type)
            if not fact:
                continue
            if mapping["status"] == "NO_SAFE_MAP":
                skipped.append({"fact_type": fact_type, "reason": "NO_SAFE_MAP"})
                continue
            rendered = transform_value(str(mapping["transform"]), fact.get("value"))
            if rendered is None:
                skipped.append({"fact_type": fact_type, "reason": "TRANSFORM_NOT_SAFE"})
                continue
            question = self._question(product_code, str(mapping["target_question_id"])) or {}
            if question.get("type") == "select" and rendered not in (question.get("options") or []):
                skipped.append({"fact_type": fact_type, "reason": "TARGET_OPTION_MISMATCH"})
                continue
            answers[str(mapping["target_question_id"])] = rendered
            reused.append(
                {
                    "fact_type": fact_type,
                    "question_id": str(mapping["target_question_id"]),
                    "mapping_status": str(mapping["status"]),
                }
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "product_code": product_code,
            "answers": answers,
            "reused": reused,
            "skipped": skipped,
        }


class FulfillmentContextStore(AccountHandoffStore):
    def __init__(self, crypto, self_service, offer_provider: Callable[[str], dict[str, Any]], retention_hours: int = 72):
        super().__init__(crypto, self_service, retention_hours=retention_hours)
        self.bridge = FulfillmentFactBridge()
        self.offer_provider = offer_provider

    def _owned_handoff(self, con, user_id: str, product_code: str):
        self.create_schema(con)
        return con.execute(
            """SELECT * FROM m35_intake_handoffs
               WHERE user_id=? AND product_code=? AND status!='CANCELLED'
               ORDER BY created_at DESC LIMIT 1""",
            (str(user_id or ""), str(product_code or "").upper()),
        ).fetchone()

    @staticmethod
    def _public_offer(offer: Mapping[str, Any]) -> dict[str, Any]:
        levels = []
        for level in offer.get("service_levels", []):
            levels.append(
                {
                    "id": level.get("id"),
                    "label": level.get("label"),
                    "price": int(level.get("price") or 0),
                    "price_label": level.get("price_label"),
                    "includes": list(level.get("includes") or []),
                    "checkout_enabled": bool(level.get("checkout_enabled")),
                }
            )
        return {
            "product_code": offer.get("product_code"),
            "public_name": offer.get("public_name"),
            "service_levels": levels,
            "pricing_status": offer.get("pricing_status"),
            "pricing_notice": offer.get("pricing_notice"),
        }

    def prepare(self, con, user_id: str, product_code: str) -> dict[str, Any]:
        product_code = str(product_code or "").upper().strip()
        handoff = self._owned_handoff(con, user_id, product_code)
        if not handoff:
            raise LookupError("No existe un diagnóstico transferido para esta solución.")
        intake = con.execute(
            "SELECT * FROM intelligent_intake_sessions WHERE id=? AND transferred_user_id=?",
            (handoff["intake_id"], user_id),
        ).fetchone()
        if not intake or intake["status"] != "Transferido":
            raise HandoffStateError("El diagnóstico transferido ya no está disponible para fulfillment.")
        payload = self._decrypt(intake)
        m350 = payload.get("m35_0") or {}
        if str(m350.get("decision_id") or "") != handoff["decision_id"]:
            raise HandoffStateError("La trazabilidad del diagnóstico y la recomendación no coincide.")
        if str(m350.get("product_code") or "") != product_code:
            raise HandoffStateError("La recomendación transferida no corresponde al producto solicitado.")

        draft = self.self_service.get_draft(con, user_id, handoff["draft_id"])
        if not draft or draft.get("product_code") != product_code:
            raise HandoffStateError("El borrador de fulfillment asociado no está disponible.")

        prefill = self.bridge.build_prefill(product_code, list(payload.get("facts") or []))
        existing_answers = dict(draft.get("answers") or {})
        merged_answers = {**prefill["answers"], **existing_answers}
        applied = [row for row in prefill["reused"] if row["question_id"] not in existing_answers]
        offer = self._public_offer(self.offer_provider(product_code))
        existing_result = dict(draft.get("result") or {})
        bridge_result = {
            **existing_result,
            "m35_1_schema_version": SCHEMA_VERSION,
            "fulfillment_status": "STARTED",
            "triage_reuse_status": "SAFE_MAPPING_APPLIED",
            "triage_reused_count": len(prefill["reused"]),
            "triage_reused_question_ids": [row["question_id"] for row in prefill["reused"]],
            "triage_skipped_count": len(prefill["skipped"]),
            "commercial_offer": offer,
            "offer_snapshot_at": utc_iso(),
        }
        updated = self.self_service.save_draft(
            con,
            user_id,
            product_code,
            merged_answers,
            current_step=int(draft.get("current_step") or 0),
            title=str(draft.get("title") or product_code),
            result=bridge_result,
        )
        con.execute(
            "UPDATE m35_intake_handoffs SET status='FULFILLMENT_STARTED',updated_at=? WHERE id=?",
            (utc_iso(), handoff["id"]),
        )
        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "handoff_id": handoff["id"],
            "draft_id": updated["id"],
            "product_code": product_code,
            "answers": updated.get("answers") or {},
            "eligible_prefill_count": len(prefill["reused"]),
            "applied_prefill_count": len(applied),
            "prefilled_question_ids": [row["question_id"] for row in prefill["reused"]],
            "offer": offer,
            "notice": (
                "Reutilizamos únicamente respuestas con equivalencia semántica validada. "
                "Puedes editarlas y debes confirmar la información antes del análisis final."
            ),
        }


__all__ = [
    "FulfillmentContextStore",
    "FulfillmentFactBridge",
    "MappingValidation",
    "SCHEMA_VERSION",
    "transform_value",
]
