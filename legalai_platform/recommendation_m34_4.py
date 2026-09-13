from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import uuid
from typing import Any, Mapping

from legalai_platform.adaptive_question_m34_3 import (
    AdaptiveIntakeStore,
    AdaptiveQuestionEngine,
    QuestionContractRegistry,
)
from legalai_platform.m34_intelligent_journey import (
    RiskCode,
    fact_is_decision_usable,
    load_product_contracts,
)


ROOT = Path(__file__).resolve().parents[1]
RECOMMENDATION_CONTRACTS_PATH = ROOT / "config" / "m34" / "recommendation_contracts.json"
SCHEMA_VERSION = "34.4.0"
MAX_DECISIONS_PER_ANONYMOUS_INTAKE = 32
ELIGIBILITY_ORDER = {"FAIL": 0, "CONDITIONAL": 1, "PASS": 2}
SUPPORTED_CHECK_OPERATORS = {"EQ", "IN"}
SUPPORTED_CHECK_EFFECTS = {"FAIL", "CONDITIONAL", "ESCALATE"}


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} debe contener un objeto JSON")
    return payload


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _is_uncertain(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"uncertain", "no_se", "no sé", "no se", "desconocido", "desconocida"}
    if isinstance(value, list):
        return any(_is_uncertain(item) for item in value)
    return False


@dataclass(frozen=True)
class RecommendationContractValidation:
    ok: bool
    errors: tuple[str, ...]
    contracts: int


class RecommendationContractRegistry:
    def __init__(self):
        self.payload = _load_json(RECOMMENDATION_CONTRACTS_PATH)
        self.product_contracts = load_product_contracts()
        self.question_contracts = QuestionContractRegistry()
        contracts = self.payload.get("contracts") or []
        self.contracts = {
            str(item.get("product_code") or ""): item
            for item in contracts
            if isinstance(item, dict)
        }

    def validate(self) -> RecommendationContractValidation:
        errors: list[str] = []
        product_codes = set(self.product_contracts)
        if self.payload.get("schema_version") != SCHEMA_VERSION:
            errors.append("recommendation contracts schema_version no coincide con M34.4")
        if set(self.payload.get("decision_outcomes") or []) != {"RECOMMEND", "ASK_MORE", "ESCALATE", "OUT_OF_SCOPE"}:
            errors.append("decision_outcomes M34.4 no coinciden con el contrato canónico")
        if set(self.payload.get("eligibility_states") or []) != {"PASS", "CONDITIONAL", "FAIL"}:
            errors.append("eligibility_states M34.4 inválidos")
        if self.payload.get("public_score_policy") != "NEVER_EXPOSE_NUMERIC_FIT_SCORE":
            errors.append("M34.4 debe prohibir score numérico público")
        if set(self.contracts) != product_codes:
            errors.append(
                "recommendation/product contract mismatch: "
                f"missing={sorted(product_codes - set(self.contracts))}; "
                f"extra={sorted(set(self.contracts) - product_codes)}"
            )
        if len(self.contracts) != 11:
            errors.append(f"M34.4 requiere 11 contratos y encontró {len(self.contracts)}")

        for code, contract in self.contracts.items():
            if not str(contract.get("public_title") or "").strip():
                errors.append(f"{code}: falta public_title")
            if not str(contract.get("fit_statement") or "").strip():
                errors.append(f"{code}: falta fit_statement")
            reasons = contract.get("reason_templates") or []
            if not isinstance(reasons, list) or not 1 <= len(reasons) <= 5:
                errors.append(f"{code}: reason_templates debe tener 1-5 textos")
            if any(not isinstance(reason, str) or len(reason.strip()) < 15 for reason in reasons):
                errors.append(f"{code}: reason template inválido")
            reason_facts = contract.get("reason_fact_types") or []
            product_minimum = set(self.product_contracts[code].get("minimum_recommendation_facts") or [])
            if not isinstance(reason_facts, list) or not reason_facts:
                errors.append(f"{code}: reason_fact_types debe ser no vacío")
            for fact_type in reason_facts:
                if fact_type not in product_minimum:
                    errors.append(f"{code}: reason fact fuera del Product Contract: {fact_type}")

            for collection in ("includes", "not_included"):
                values = contract.get(collection) or []
                if not isinstance(values, list) or not values:
                    errors.append(f"{code}: {collection} debe ser no vacío")
                elif any(not isinstance(value, str) or len(value.strip()) < 6 for value in values):
                    errors.append(f"{code}: {collection} contiene texto inválido")

            expected_review = str(self.product_contracts[code].get("review_policy") or "").upper()
            actual_review = str(contract.get("review_requirement") or "").upper()
            normalized_expected = {
                "RISK_BASED": "RISK_BASED",
                "CASE_SPECIFIC_REVIEW_EXPECTED": "CASE_SPECIFIC_REVIEW_EXPECTED",
            }.get(expected_review, expected_review)
            if actual_review != normalized_expected:
                errors.append(f"{code}: review_requirement no coincide con Product Contract")

            triage_facts = set(self.question_contracts.requirements_for_product(code, "TRIAGE_REQUIRED"))
            for check in contract.get("catalog_checks") or []:
                if not isinstance(check, dict):
                    errors.append(f"{code}: catalog_check inválido")
                    continue
                fact_type = str(check.get("fact_type") or "")
                operator = str(check.get("operator") or "")
                effect = str(check.get("effect") or "")
                reason_code = str(check.get("reason_code") or "")
                if fact_type not in triage_facts:
                    errors.append(f"{code}: catalog_check usa hecho no disponible en triage: {fact_type}")
                if operator not in SUPPORTED_CHECK_OPERATORS:
                    errors.append(f"{code}: operador no soportado {operator}")
                if effect not in SUPPORTED_CHECK_EFFECTS:
                    errors.append(f"{code}: efecto no soportado {effect}")
                if not re.match(r"^[A-Z0-9_]{3,100}$", reason_code):
                    errors.append(f"{code}: reason_code inválido {reason_code}")
                if not str(check.get("public_message") or "").strip():
                    errors.append(f"{code}: catalog_check requiere public_message")
                for alternative in check.get("alternative_codes") or []:
                    if alternative not in product_codes or alternative == code:
                        errors.append(f"{code}: alternativa inválida {alternative}")

        return RecommendationContractValidation(
            ok=not errors,
            errors=tuple(errors),
            contracts=len(self.contracts),
        )


class ExplainableRecommendationEngine:
    """Deterministic product-fit engine. It does not predict legal outcomes."""

    def __init__(self, registry: RecommendationContractRegistry | None = None):
        self.registry = registry or RecommendationContractRegistry()
        validation = self.registry.validate()
        if not validation.ok:
            raise ValueError("Recommendation Contracts M34.4 inválidos: " + "; ".join(validation.errors))
        self.products = self.registry.product_contracts

    @staticmethod
    def _usable_facts(state: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
        usable: dict[str, Mapping[str, Any]] = {}
        for fact in state.get("facts") or []:
            if not isinstance(fact, Mapping):
                continue
            if not fact_is_decision_usable(fact) or _is_uncertain(fact.get("value")):
                continue
            fact_type = str(fact.get("fact_type") or "")
            if fact_type:
                usable[fact_type] = fact
        return usable

    @staticmethod
    def _topic_scores(state: Mapping[str, Any]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for candidate in state.get("candidate_products") or []:
            if not isinstance(candidate, Mapping) or candidate.get("status") != "TOPIC_SIGNAL_ONLY":
                continue
            try:
                score = float(candidate.get("signal_score") or 0)
            except (TypeError, ValueError):
                continue
            if 0 <= score <= 1:
                scores[str(candidate.get("product_code") or "")] = score
        return scores

    @staticmethod
    def _current_routing_codes(state: Mapping[str, Any]) -> set[str]:
        routing = state.get("routing") or {}
        if routing.get("disambiguation"):
            return set(routing["disambiguation"].get("product_codes") or [])
        if routing.get("broad"):
            return set(routing["broad"].get("product_codes") or [])
        return set()

    @staticmethod
    def _check_matches(check: Mapping[str, Any], facts: Mapping[str, Mapping[str, Any]]) -> bool:
        fact = facts.get(str(check.get("fact_type") or ""))
        if not fact:
            return False
        value = fact.get("normalized_value", fact.get("value"))
        operator = str(check.get("operator") or "")
        if operator == "EQ":
            return value == check.get("value")
        if operator == "IN":
            return value in (check.get("values") or [])
        raise ValueError(f"Operador de recomendación no soportado: {operator}")

    def _evaluate_product(
        self,
        code: str,
        state: Mapping[str, Any],
        ready_codes: set[str],
    ) -> dict[str, Any]:
        contract = self.registry.contracts[code]
        facts = self._usable_facts(state)
        eligibility = "PASS" if code in ready_codes else "FAIL"
        warnings: list[dict[str, Any]] = []
        escalation_reasons: list[dict[str, Any]] = []
        failed_reasons: list[dict[str, Any]] = []

        if code in ready_codes:
            for check in contract.get("catalog_checks") or []:
                if not self._check_matches(check, facts):
                    continue
                item = {
                    "reason_code": str(check["reason_code"]),
                    "message": str(check["public_message"]),
                    "alternative_codes": list(check.get("alternative_codes") or []),
                }
                effect = str(check["effect"])
                if effect == "ESCALATE":
                    escalation_reasons.append(item)
                    eligibility = "FAIL"
                elif effect == "FAIL":
                    failed_reasons.append(item)
                    eligibility = "FAIL"
                elif effect == "CONDITIONAL" and eligibility != "FAIL":
                    warnings.append(item)
                    eligibility = "CONDITIONAL"

        matched_fact_ids = [
            str(facts[fact_type].get("fact_id"))
            for fact_type in contract.get("reason_fact_types") or []
            if fact_type in facts
        ]
        matched_fact_types = [
            fact_type
            for fact_type in contract.get("reason_fact_types") or []
            if fact_type in facts
        ]
        topic_score = self._topic_scores(state).get(code, 0.0)
        routing_codes = self._current_routing_codes(state)
        routing_match = 1 if routing_codes and code in routing_codes else 0
        internal_rank = (
            ELIGIBILITY_ORDER.get(eligibility, 0),
            routing_match,
            round(topic_score, 6),
            len(matched_fact_types),
            code,
        )
        return {
            "product_code": code,
            "eligibility": eligibility,
            "public_title": contract["public_title"],
            "fit_statement": contract["fit_statement"],
            "why_this_solution": list(contract.get("reason_templates") or [])[:3],
            "includes": list(contract.get("includes") or []),
            "not_included": list(contract.get("not_included") or []),
            "review_requirement": contract["review_requirement"],
            "warnings": warnings,
            "failed_reasons": failed_reasons,
            "escalation_reasons": escalation_reasons,
            "matched_fact_ids": matched_fact_ids,
            "matched_fact_types": matched_fact_types,
            "_internal_rank": internal_rank,
        }

    @staticmethod
    def _public_evaluation(evaluation: Mapping[str, Any], *, compact: bool = False) -> dict[str, Any]:
        private_keys = {
            "failed_reasons",
            "escalation_reasons",
            "matched_fact_ids",
            "matched_fact_types",
        }
        public = {
            key: value
            for key, value in evaluation.items()
            if not str(key).startswith("_internal") and key not in private_keys
        }
        if compact:
            return {
                "product_code": public["product_code"],
                "eligibility": public["eligibility"],
                "public_title": public["public_title"],
                "fit_statement": public["fit_statement"],
                "review_requirement": public["review_requirement"],
                "warnings": public["warnings"],
            }
        return public

    def decide(self, state: Mapping[str, Any], gate: Mapping[str, Any]) -> dict[str, Any]:
        gate_action = str(gate.get("action") or "")
        if gate_action != "READY_FOR_RECOMMENDATION":
            if gate_action == "ESCALATE":
                return {
                    "schema_version": SCHEMA_VERSION,
                    "outcome": "ESCALATE",
                    "reason_codes": list(gate.get("reason_codes") or ["M34_3_ESCALATION"]),
                    "notice": "El gate previo exige revisión adicional antes de recomendar una solución.",
                }
            if gate_action == "OUT_OF_SCOPE":
                return {
                    "schema_version": SCHEMA_VERSION,
                    "outcome": "OUT_OF_SCOPE",
                    "reason_codes": list(gate.get("reason_codes") or ["OUT_OF_CATALOG"]),
                    "notice": "La situación no encaja con suficiente claridad en el catálogo automatizado actual.",
                }
            return {
                "schema_version": SCHEMA_VERSION,
                "outcome": "ASK_MORE",
                "reason_codes": list(gate.get("reason_codes") or ["TRIAGE_NOT_READY"]),
                "resume_action": gate_action or "ASK_MORE",
                "notice": "Todavía falta completar o confirmar información antes de evaluar una recomendación.",
            }

        sufficiency = gate.get("sufficiency") or {}
        ready_codes = set(sufficiency.get("ready_product_codes") or [])
        scope = set(gate.get("product_scope") or [])
        ready_in_scope = ready_codes.intersection(scope)
        if not ready_in_scope:
            return {
                "schema_version": SCHEMA_VERSION,
                "outcome": "ASK_MORE",
                "reason_codes": ["READY_SCOPE_MISMATCH"],
                "notice": "La suficiencia y el alcance del producto no coinciden; el sistema no debe forzar una recomendación.",
            }

        allowed_risks = {item.value for item in RiskCode}
        unresolved = [
            str(item.get("code"))
            for item in state.get("risk_signals") or []
            if str(item.get("code")) in allowed_risks
            and item.get("status") in {None, "UNCONFIRMED_SIGNAL", "USER_UNCERTAIN"}
        ]
        if unresolved:
            return {
                "schema_version": SCHEMA_VERSION,
                "outcome": "ESCALATE",
                "reason_codes": sorted(set(unresolved)),
                "notice": "Existe una señal de riesgo que no está suficientemente resuelta para recomendar automáticamente.",
            }

        evaluations = [self._evaluate_product(code, state, ready_in_scope) for code in sorted(ready_in_scope)]
        escalations = [item for item in evaluations if item["escalation_reasons"]]
        eligible = [item for item in evaluations if item["eligibility"] in {"PASS", "CONDITIONAL"}]
        eligible.sort(key=lambda item: item["_internal_rank"], reverse=True)

        if not eligible:
            if escalations:
                reason_codes = sorted({
                    reason["reason_code"]
                    for item in escalations
                    for reason in item["escalation_reasons"]
                })
                messages = [
                    reason["message"]
                    for item in escalations
                    for reason in item["escalation_reasons"]
                ]
                alternative_codes = []
                for item in escalations:
                    for reason in item["escalation_reasons"]:
                        for code in reason.get("alternative_codes") or []:
                            if code not in alternative_codes:
                                alternative_codes.append(code)
                return {
                    "schema_version": SCHEMA_VERSION,
                    "outcome": "ESCALATE",
                    "reason_codes": reason_codes,
                    "messages": messages[:3],
                    "possible_alternative_codes": alternative_codes[:2],
                    "notice": "La información supera el límite responsable de la recomendación automática.",
                }
            failures = [
                reason
                for item in evaluations
                for reason in item["failed_reasons"]
            ]
            return {
                "schema_version": SCHEMA_VERSION,
                "outcome": "OUT_OF_SCOPE",
                "reason_codes": sorted({reason["reason_code"] for reason in failures}) or ["OUT_OF_CATALOG"],
                "messages": [reason["message"] for reason in failures][:3],
                "notice": "Ninguna de las soluciones evaluadas encaja de forma responsable con los hechos disponibles.",
            }

        primary = eligible[0]
        max_alternatives = int(self.registry.payload.get("max_alternatives") or 2)
        alternatives = [self._public_evaluation(item, compact=True) for item in eligible[1:1 + max_alternatives]]
        return {
            "schema_version": SCHEMA_VERSION,
            "outcome": "RECOMMEND",
            "primary": self._public_evaluation(primary),
            "alternatives": alternatives,
            "reason_codes": ["PRODUCT_FIT_CONFIRMED"],
            "notice": (
                "Esta recomendación indica adecuación al producto de LegalAIZ.it según los hechos disponibles. "
                "No predice el resultado jurídico del caso ni sustituye la revisión profesional cuando corresponda."
            ),
            "_internal": {
                "ranked_candidates": [
                    {
                        "product_code": item["product_code"],
                        "eligibility": item["eligibility"],
                        "rank": list(item["_internal_rank"][:-1]),
                        "failed_reason_codes": [reason["reason_code"] for reason in item["failed_reasons"]],
                        "escalation_reason_codes": [reason["reason_code"] for reason in item["escalation_reasons"]],
                        "matched_fact_ids": list(item["matched_fact_ids"]),
                        "matched_fact_types": list(item["matched_fact_types"]),
                    }
                    for item in sorted(evaluations, key=lambda value: value["_internal_rank"], reverse=True)
                ]
            },
        }


class RecommendationStore(AdaptiveIntakeStore):
    """Append-only recommendation decisions inside the encrypted anonymous intake payload."""

    @staticmethod
    def _decision_input(state: Mapping[str, Any], gate: Mapping[str, Any]) -> dict[str, Any]:
        facts = []
        for fact in state.get("facts") or []:
            if not isinstance(fact, Mapping) or not fact_is_decision_usable(fact):
                continue
            facts.append(
                {
                    "fact_id": fact.get("fact_id"),
                    "fact_type": fact.get("fact_type"),
                    "value": fact.get("normalized_value", fact.get("value")),
                    "provenance": fact.get("provenance"),
                    "confirmation_status": fact.get("confirmation_status"),
                }
            )
        return {
            "facts": sorted(facts, key=lambda item: (str(item["fact_type"]), str(item["fact_id"]))),
            "risk_signals": sorted(
                [
                    {"code": item.get("code"), "status": item.get("status")}
                    for item in state.get("risk_signals") or []
                    if isinstance(item, Mapping)
                ],
                key=lambda item: str(item["code"]),
            ),
            "routing": state.get("routing") or {},
            "candidate_products": state.get("candidate_products") or [],
            "gate_scope": gate.get("product_scope") or [],
            "gate_ready_codes": (gate.get("sufficiency") or {}).get("ready_product_codes") or [],
        }

    @staticmethod
    def _public_result(record: Mapping[str, Any]) -> dict[str, Any]:
        result = dict(record.get("result") or {})
        result.pop("_internal", None)
        result["decision_id"] = record["decision_id"]
        result["decided_at"] = record["decided_at"]
        result["idempotent"] = bool(record.get("idempotent"))
        return result

    def recommend(
        self,
        con,
        token: str,
        adaptive_engine: AdaptiveQuestionEngine,
        recommendation_engine: ExplainableRecommendationEngine,
    ) -> dict[str, Any]:
        row = self._active_row(con, token)
        payload = self._decrypt(row)
        state = self._engine_state(row, payload)
        gate = adaptive_engine.next_step(state)
        result = recommendation_engine.decide(state, gate)

        input_payload = self._decision_input(state, gate)
        input_fingerprint = _fingerprint(
            {
                "recommendation_schema": SCHEMA_VERSION,
                "recommendation_contracts": recommendation_engine.registry.payload.get("schema_version"),
                "question_contracts": recommendation_engine.registry.question_contracts.questions.get("schema_version"),
                "product_contracts": recommendation_engine.registry.question_contracts.questions.get("product_contract_schema_version"),
                "input": input_payload,
            }
        )
        m344 = payload.setdefault(
            "m34_4",
            {
                "schema_version": SCHEMA_VERSION,
                "decisions": [],
                "current_decision_id": None,
            },
        )
        decisions = m344.setdefault("decisions", [])
        for existing in decisions:
            if (
                existing.get("input_fingerprint") == input_fingerprint
                and existing.get("schema_version") == SCHEMA_VERSION
            ):
                reused = dict(existing)
                reused["idempotent"] = True
                return self._public_result(reused)

        if len(decisions) >= MAX_DECISIONS_PER_ANONYMOUS_INTAKE:
            raise ValueError("El diagnóstico alcanzó el límite de decisiones anónimas permitido.")

        record = {
            "decision_id": "REC-" + uuid.uuid4().hex[:16].upper(),
            "schema_version": SCHEMA_VERSION,
            "decided_at": utc_iso(),
            "input_fingerprint": input_fingerprint,
            "result": result,
            "input_summary": {
                "usable_fact_ids": [item["fact_id"] for item in input_payload["facts"]],
                "risk_statuses": input_payload["risk_signals"],
                "product_scope": input_payload["gate_scope"],
                "ready_product_codes": input_payload["gate_ready_codes"],
            },
        }
        decisions.append(record)
        m344["current_decision_id"] = record["decision_id"]
        m344["schema_version"] = SCHEMA_VERSION
        target_stage = {
            "RECOMMEND": "RECOMMENDED",
            "ASK_MORE": "QUESTIONING",
            "ESCALATE": "ESCALATED",
            "OUT_OF_SCOPE": "OUT_OF_SCOPE",
        }[result["outcome"]]
        self._write_payload(con, row, payload, target_stage)
        return self._public_result(record)


__all__ = [
    "ExplainableRecommendationEngine",
    "RecommendationContractRegistry",
    "RecommendationContractValidation",
    "RecommendationStore",
    "SCHEMA_VERSION",
]
