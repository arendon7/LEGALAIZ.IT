from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import uuid
from typing import Any, Mapping

from legalai_platform.intelligent_intake_m34_1 import IntelligentIntakeStore
from legalai_platform.m34_intelligent_journey import (
    RiskCode,
    fact_is_decision_usable,
    load_product_contracts,
    validate_legal_fact,
)


ROOT = Path(__file__).resolve().parents[1]
QUESTION_CONTRACTS_PATH = ROOT / "config" / "m34" / "question_contracts.json"
ROUTING_CONTRACTS_PATH = ROOT / "config" / "m34" / "routing_contracts.json"
SCHEMA_VERSION = "34.3.0"
VALID_REQUIREMENT_MODES = {"TRIAGE_REQUIRED", "FULFILLMENT_ONLY"}
VALID_ANSWER_TYPES = {
    "select",
    "multiselect",
    "date",
    "money_cop",
    "number",
    "text",
    "textarea",
    "boolean",
}
UNCERTAIN_VALUES = {"no_se", "no sé", "no se", "uncertain", "desconocido", "desconocida"}
CRITICALITY_SCORE = {"LOW": 0, "MEDIUM": 5, "HIGH": 15, "BLOCKING": 30}
HARD_ESCALATION_RISKS = {"CRIMINAL_MATTER"}
MAX_TEXT_ANSWER = 1200
MAX_HISTORY = 128


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} debe contener un objeto JSON")
    return payload


def _problem_digest(problem: str) -> str:
    return sha256(str(problem or "").encode("utf-8")).hexdigest()


def _is_uncertain_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in UNCERTAIN_VALUES
    if isinstance(value, list):
        return any(_is_uncertain_value(item) for item in value)
    return False


@dataclass(frozen=True)
class ContractValidation:
    ok: bool
    errors: tuple[str, ...]
    fact_contracts: int
    risk_contracts: int
    covered_product_fact_pairs: int


class QuestionContractRegistry:
    """Curated semantic bridge between Product Contracts and pre-sale questions."""

    def __init__(self):
        self.questions = _load_json(QUESTION_CONTRACTS_PATH)
        self.routing = _load_json(ROUTING_CONTRACTS_PATH)
        self.products = load_product_contracts()
        self.fact_questions = list(self.questions.get("fact_questions") or [])
        self.risk_questions = list(self.questions.get("risk_questions") or [])
        self.fact_by_id = {
            str(item.get("question_contract_id")): item for item in self.fact_questions
        }
        self.risk_by_id = {
            str(item.get("question_contract_id")): item for item in self.risk_questions
        }
        self.risk_by_code = {
            str(item.get("risk_code")): item for item in self.risk_questions
        }
        self.broad_routing = dict(self.routing.get("broad_question") or {})
        self.disambiguators = list(self.routing.get("disambiguators") or [])

    def validate(self) -> ContractValidation:
        errors: list[str] = []
        product_codes = set(self.products)
        required_pairs = {
            (code, str(fact_type))
            for code, contract in self.products.items()
            for fact_type in contract.get("minimum_recommendation_facts", [])
        }
        covered_pairs: set[tuple[str, str]] = set()
        seen_ids: set[str] = set()

        if self.questions.get("schema_version") != SCHEMA_VERSION:
            errors.append("question contracts schema_version no coincide con M34.3")
        if self.routing.get("schema_version") != SCHEMA_VERSION:
            errors.append("routing contracts schema_version no coincide con M34.3")

        for item in self.fact_questions:
            if not isinstance(item, dict):
                errors.append("fact question inválida")
                continue
            qid = str(item.get("question_contract_id") or "")
            fact_type = str(item.get("fact_type") or "")
            mode = str(item.get("requirement_mode") or "")
            products = item.get("products") or []
            if not qid or qid in seen_ids:
                errors.append(f"question_contract_id inválido o duplicado: {qid}")
            seen_ids.add(qid)
            if mode not in VALID_REQUIREMENT_MODES:
                errors.append(f"{qid}: requirement_mode inválido")
            if not re.match(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$", fact_type):
                errors.append(f"{qid}: fact_type inválido")
            if not isinstance(products, list) or not products:
                errors.append(f"{qid}: products debe ser una lista no vacía")
                products = []
            for code in products:
                if code not in product_codes:
                    errors.append(f"{qid}: producto inexistente {code}")
                elif (code, fact_type) not in required_pairs:
                    errors.append(f"{qid}: {fact_type} no es requisito mínimo de {code}")
                else:
                    pair = (code, fact_type)
                    if pair in covered_pairs:
                        errors.append(f"{qid}: cobertura duplicada para {code}/{fact_type}")
                    covered_pairs.add(pair)
            if mode == "TRIAGE_REQUIRED":
                if not str(item.get("prompt") or "").strip():
                    errors.append(f"{qid}: triage requiere prompt")
                answer_type = str(item.get("answer_type") or "")
                if answer_type not in VALID_ANSWER_TYPES:
                    errors.append(f"{qid}: answer_type no soportado {answer_type}")
                if answer_type in {"select", "multiselect"}:
                    options = item.get("options") or []
                    if not isinstance(options, list) or not options:
                        errors.append(f"{qid}: select/multiselect requiere opciones")
            elif item.get("source_mode") != "DEFERRED":
                errors.append(f"{qid}: fulfillment-only debe declararse DEFERRED")

        missing_pairs = required_pairs - covered_pairs
        extra_pairs = covered_pairs - required_pairs
        if missing_pairs:
            errors.append(
                "faltan contratos para: "
                + ", ".join(f"{code}/{fact}" for code, fact in sorted(missing_pairs))
            )
        if extra_pairs:
            errors.append(
                "sobran contratos para: "
                + ", ".join(f"{code}/{fact}" for code, fact in sorted(extra_pairs))
            )

        allowed_risks = {item.value for item in RiskCode}
        seen_risks: set[str] = set()
        for item in self.risk_questions:
            if not isinstance(item, dict):
                errors.append("risk question inválida")
                continue
            qid = str(item.get("question_contract_id") or "")
            code = str(item.get("risk_code") or "")
            if not qid or qid in seen_ids:
                errors.append(f"risk question id inválido o duplicado: {qid}")
            seen_ids.add(qid)
            if code not in allowed_risks:
                errors.append(f"{qid}: risk_code no soportado {code}")
            if code in seen_risks:
                errors.append(f"{qid}: risk_code duplicado {code}")
            seen_risks.add(code)
            if not str(item.get("prompt") or "").strip():
                errors.append(f"{qid}: riesgo requiere prompt")

        broad_options = self.broad_routing.get("options") or []
        broad_product_union: set[str] = set()
        for option in broad_options:
            codes = option.get("product_codes") or []
            if any(code not in product_codes for code in codes):
                errors.append("routing broad contiene producto inexistente")
            broad_product_union.update(codes)
        if broad_product_union != product_codes:
            errors.append(
                "routing broad debe cubrir exactamente los 11 productos canónicos; "
                f"faltan={sorted(product_codes - broad_product_union)}"
            )

        for item in self.disambiguators:
            applies = item.get("applies_when") or []
            if len(applies) < 2 or any(code not in product_codes for code in applies):
                errors.append(f"disambiguator inválido: {item.get('question_id')}")
            option_union = {
                code
                for option in item.get("options") or []
                for code in option.get("product_codes") or []
            }
            if not set(applies).issubset(option_union):
                errors.append(f"{item.get('question_id')}: opciones no cubren applies_when")

        return ContractValidation(
            ok=not errors,
            errors=tuple(errors),
            fact_contracts=len(self.fact_questions),
            risk_contracts=len(self.risk_questions),
            covered_product_fact_pairs=len(covered_pairs),
        )

    def requirements_for_product(self, code: str, mode: str) -> tuple[str, ...]:
        if code not in self.products:
            raise KeyError(code)
        return tuple(
            str(item["fact_type"])
            for item in self.fact_questions
            if code in (item.get("products") or []) and item.get("requirement_mode") == mode
        )

    def question_for_fact(self, fact_type: str, product_scope: set[str]) -> dict[str, Any] | None:
        candidates = [
            item
            for item in self.fact_questions
            if item.get("fact_type") == fact_type
            and item.get("requirement_mode") == "TRIAGE_REQUIRED"
            and product_scope.intersection(item.get("products") or [])
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: int(item.get("information_value") or 0))

    @staticmethod
    def public_question(item: Mapping[str, Any], kind: str = "FACT") -> dict[str, Any]:
        return {
            "question_id": str(item.get("question_contract_id") or item.get("question_id") or ""),
            "kind": kind,
            "prompt": str(item.get("prompt") or ""),
            "answer_type": str(item.get("answer_type") or "select"),
            "options": list(item.get("options") or []),
            "why_asked": str(item.get("why_asked") or ""),
            "help_text": str(item.get("help_text") or ""),
        }

    def routing_question(self, product_scope: set[str], routing_state: Mapping[str, Any]) -> dict[str, Any] | None:
        if not routing_state.get("broad"):
            if not product_scope or len(product_scope) > 1:
                return self.public_question(self.broad_routing, "ROUTING")
        if len(product_scope) > 1 and not routing_state.get("disambiguation"):
            for item in self.disambiguators:
                if set(item.get("applies_when") or []) == product_scope:
                    return self.public_question(item, "ROUTING")
        return None

    def routing_option(self, question_id: str, value: str) -> dict[str, Any]:
        sources = [self.broad_routing, *self.disambiguators]
        source = next((item for item in sources if item.get("question_id") == question_id), None)
        if not source:
            raise ValueError("La pregunta de enrutamiento ya no está disponible.")
        option = next(
            (item for item in source.get("options") or [] if str(item.get("value")) == str(value)),
            None,
        )
        if not option:
            raise ValueError("La opción de enrutamiento no es válida.")
        return {"question": source, "option": option}


class AdaptiveQuestionEngine:
    """Deterministic pre-recommendation question and sufficiency gate."""

    def __init__(self, registry: QuestionContractRegistry | None = None):
        self.registry = registry or QuestionContractRegistry()
        validation = self.registry.validate()
        if not validation.ok:
            raise ValueError("Question Contracts M34.3 inválidos: " + "; ".join(validation.errors))
        self.products = self.registry.products

    @staticmethod
    def sufficient_fact_types(facts: list[Mapping[str, Any]]) -> set[str]:
        result: set[str] = set()
        for fact in facts:
            if fact_is_decision_usable(fact) and not _is_uncertain_value(fact.get("value")):
                result.add(str(fact.get("fact_type") or ""))
        return result

    @staticmethod
    def _signal_scores(state: Mapping[str, Any]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for item in state.get("candidate_products") or []:
            if item.get("status") == "TOPIC_SIGNAL_ONLY":
                try:
                    scores[str(item.get("product_code"))] = float(item.get("signal_score") or 0)
                except (TypeError, ValueError):
                    pass
        return scores

    def initial_scope(self, state: Mapping[str, Any]) -> set[str]:
        routing = state.get("routing") or {}
        if routing.get("disambiguation"):
            return set(routing["disambiguation"].get("product_codes") or [])
        if routing.get("broad"):
            return set(routing["broad"].get("product_codes") or [])
        scores = self._signal_scores(state)
        if not scores:
            return set()
        ranked = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
        if len(ranked) == 1:
            return {ranked[0][0]}
        top_score = ranked[0][1]
        close = {code for code, score in ranked if top_score - score < 0.15}
        if len(close) == 1:
            return close
        return close

    def sufficiency(self, state: Mapping[str, Any], product_scope: set[str]) -> dict[str, Any]:
        known = self.sufficient_fact_types(list(state.get("facts") or []))
        per_product: dict[str, Any] = {}
        ready: list[str] = []
        for code in sorted(product_scope):
            required = self.registry.requirements_for_product(code, "TRIAGE_REQUIRED")
            deferred = self.registry.requirements_for_product(code, "FULFILLMENT_ONLY")
            missing = [fact_type for fact_type in required if fact_type not in known]
            if not missing:
                ready.append(code)
            per_product[code] = {
                "triage_required": list(required),
                "known": [fact_type for fact_type in required if fact_type in known],
                "missing": missing,
                "deferred_for_fulfillment": list(deferred),
            }
        return {
            "known_fact_types": sorted(known),
            "per_product": per_product,
            "ready_product_codes": ready,
            "ready": bool(ready),
        }

    def _blocking_risk(self, state: Mapping[str, Any], product_scope: set[str]) -> tuple[str, ...]:
        confirmed_or_uncertain = {
            str(item.get("code"))
            for item in state.get("risk_signals") or []
            if item.get("status") in {"CONFIRMED_BY_USER", "USER_UNCERTAIN"}
        }
        blocking = set(HARD_ESCALATION_RISKS).intersection(confirmed_or_uncertain)
        for code in product_scope:
            contract = self.products.get(code) or {}
            blocking.update(set(contract.get("blocking_risks") or []).intersection(confirmed_or_uncertain))
        return tuple(sorted(blocking))

    def _next_fact_question(
        self,
        state: Mapping[str, Any],
        scope: set[str],
        sufficiency: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        history = {
            str(item.get("question_id"))
            for item in state.get("question_history") or []
            if item.get("kind") == "FACT"
        }
        missing_types = {
            fact_type
            for product in sufficiency.get("per_product", {}).values()
            for fact_type in product.get("missing") or []
        }
        scores = self._signal_scores(state)
        candidates: list[tuple[float, dict[str, Any]]] = []
        for fact_type in missing_types:
            question = self.registry.question_for_fact(fact_type, scope)
            if not question:
                continue
            qid = str(question.get("question_contract_id") or "")
            if qid in history:
                continue
            products = set(question.get("products") or []).intersection(scope)
            criticality = str(question.get("criticality") or "MEDIUM")
            info = float(question.get("information_value") or 0)
            signal_bonus = max((scores.get(code, 0) for code in products), default=0) * 20
            coverage_bonus = 5 * len(products)
            score = info + CRITICALITY_SCORE.get(criticality, 0) + signal_bonus + coverage_bonus
            candidates.append((score, question))
        if not candidates:
            return None
        candidates.sort(key=lambda pair: (-pair[0], str(pair[1].get("question_contract_id"))))
        return candidates[0][1]

    def next_step(self, state: Mapping[str, Any]) -> dict[str, Any]:
        stage = str(state.get("stage") or "PROBLEM_SUBMITTED")
        base = {
            "schema_version": SCHEMA_VERSION,
            "stage": stage,
            "product_scope": [],
            "sufficiency": {"ready": False, "per_product": {}, "ready_product_codes": []},
            "question": None,
            "reason_codes": [],
        }
        if stage == "PROBLEM_SUBMITTED":
            return {**base, "action": "ANALYZE_FACTS", "reason_codes": ["FACT_EXTRACTION_NOT_RUN"]}
        if int(state.get("pending_fact_count") or 0) > 0:
            return {**base, "action": "CONFIRM_FACTS", "reason_codes": ["UNCONFIRMED_EXTRACTED_FACTS"]}

        unresolved_risks = [
            item for item in state.get("risk_signals") or [] if item.get("status") == "UNCONFIRMED_SIGNAL"
        ]
        if unresolved_risks:
            risk = unresolved_risks[0]
            contract = self.registry.risk_by_code.get(str(risk.get("code")))
            if contract:
                return {
                    **base,
                    "action": "CONFIRM_RISK",
                    "question": self.registry.public_question(contract, "RISK"),
                    "reason_codes": [str(risk.get("code"))],
                }
            return {**base, "action": "ESCALATE", "reason_codes": ["UNMAPPED_RISK_SIGNAL"]}

        unresolved_contradictions = [
            item
            for item in state.get("contradictions") or []
            if item.get("status") in {None, "UNCONFIRMED_SIGNAL"}
        ]
        if unresolved_contradictions:
            return {**base, "action": "ESCALATE", "reason_codes": ["FACT_CONTRADICTION"]}

        routing = state.get("routing") or {}
        scope = self.initial_scope(state)
        routing_question = self.registry.routing_question(scope, routing)
        if routing_question:
            return {
                **base,
                "action": "ROUTE_TOPIC",
                "product_scope": sorted(scope),
                "question": routing_question,
                "reason_codes": ["PRODUCT_SCOPE_NEEDS_ROUTING"],
            }
        if not scope:
            return {**base, "action": "OUT_OF_SCOPE", "reason_codes": ["OUT_OF_CATALOG"]}

        blocking = self._blocking_risk(state, scope)
        if blocking:
            return {
                **base,
                "action": "ESCALATE",
                "product_scope": sorted(scope),
                "reason_codes": list(blocking),
            }

        sufficiency = self.sufficiency(state, scope)
        if sufficiency["ready"]:
            return {
                **base,
                "action": "READY_FOR_RECOMMENDATION",
                "product_scope": sorted(scope),
                "sufficiency": sufficiency,
                "reason_codes": ["TRIAGE_SUFFICIENT"],
                "notice": "Tenemos información suficiente para pasar al recomendador. Aún no se ha emitido una recomendación jurídica.",
            }

        question = self._next_fact_question(state, scope, sufficiency)
        if question:
            return {
                **base,
                "action": "ASK_QUESTION",
                "product_scope": sorted(scope),
                "sufficiency": sufficiency,
                "question": self.registry.public_question(question, "FACT"),
                "reason_codes": ["MISSING_TRIAGE_FACT"],
            }

        return {
            **base,
            "action": "ESCALATE",
            "product_scope": sorted(scope),
            "sufficiency": sufficiency,
            "reason_codes": ["INSUFFICIENT_INFORMATION"],
            "notice": "No es responsable avanzar automáticamente con la información disponible.",
        }


class AdaptiveIntakeStore(IntelligentIntakeStore):
    """M34.3 encrypted state and answer lifecycle on top of the M34 intake table."""

    @staticmethod
    def _fresh_state(problem_statement: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "origin_problem_sha256": _problem_digest(problem_statement),
            "routing": {},
            "question_history": [],
            "last_sufficiency": None,
        }

    def _m343(self, payload: dict[str, Any]) -> dict[str, Any]:
        problem = str(payload.get("problem_statement") or "")
        state = payload.get("m34_3")
        if not isinstance(state, dict) or state.get("origin_problem_sha256") != _problem_digest(problem):
            state = self._fresh_state(problem)
            payload["m34_3"] = state
        state.setdefault("routing", {})
        state.setdefault("question_history", [])
        state.setdefault("last_sufficiency", None)
        return state

    def _engine_state(self, row, payload: dict[str, Any]) -> dict[str, Any]:
        public = self._public_state(row, payload)
        m343 = self._m343(payload)
        public.update(
            {
                "routing": m343.get("routing") or {},
                "question_history": m343.get("question_history") or [],
            }
        )
        return public

    def next_step(self, con, token: str, engine: AdaptiveQuestionEngine) -> dict[str, Any]:
        row = self._active_row(con, token)
        payload = self._decrypt(row)
        state = self._engine_state(row, payload)
        step = engine.next_step(state)
        m343 = self._m343(payload)
        m343["last_sufficiency"] = step.get("sufficiency")
        target_stage = {
            "ROUTE_TOPIC": "QUESTIONING",
            "CONFIRM_RISK": "RISK_CONFIRMATION",
            "ASK_QUESTION": "QUESTIONING",
            "READY_FOR_RECOMMENDATION": "RECOMMENDATION_READY",
            "ESCALATE": "ESCALATED",
            "OUT_OF_SCOPE": "OUT_OF_SCOPE",
        }.get(step["action"])
        if target_stage and target_stage != row["stage"]:
            self._write_payload(con, row, payload, target_stage)
            row = con.execute("SELECT * FROM intelligent_intake_sessions WHERE id=?", (row["id"],)).fetchone()
            step["stage"] = target_stage
        return step

    @staticmethod
    def _allowed_option_values(question: Mapping[str, Any]) -> set[str]:
        return {str(item.get("value")) for item in question.get("options") or []}

    @classmethod
    def normalize_answer(cls, question: Mapping[str, Any], value: Any) -> Any:
        answer_type = str(question.get("answer_type") or "")
        if answer_type == "select":
            normalized = str(value or "").strip()
            if normalized not in cls._allowed_option_values(question):
                raise ValueError("La respuesta seleccionada no es válida.")
            return normalized
        if answer_type == "multiselect":
            if not isinstance(value, list) or not value:
                raise ValueError("Selecciona al menos una opción.")
            allowed = cls._allowed_option_values(question)
            normalized = [str(item) for item in value]
            if len(normalized) != len(set(normalized)) or any(item not in allowed for item in normalized):
                raise ValueError("La selección contiene una opción inválida.")
            return normalized
        if answer_type == "boolean":
            if isinstance(value, bool):
                return value
            normalized = str(value).strip().lower()
            if normalized in {"true", "si", "sí", "1"}:
                return True
            if normalized in {"false", "no", "0"}:
                return False
            raise ValueError("La respuesta debe ser sí o no.")
        if answer_type == "date":
            normalized = str(value or "").strip()
            try:
                datetime.strptime(normalized, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError("La fecha debe tener formato AAAA-MM-DD.") from exc
            return normalized
        if answer_type == "money_cop":
            if isinstance(value, bool):
                raise ValueError("El valor monetario no es válido.")
            raw = str(value or "")
            digits = re.sub(r"[^0-9]", "", raw)
            if not digits:
                raise ValueError("Ingresa un valor aproximado en pesos colombianos.")
            amount = int(digits)
            if amount <= 0 or amount > 10**15:
                raise ValueError("El valor monetario está fuera del rango permitido.")
            return {"amount_cop": amount, "currency": "COP"}
        if answer_type == "number":
            if isinstance(value, bool):
                raise ValueError("El número no es válido.")
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("Ingresa un número válido.") from exc
            if abs(number) > 10**15:
                raise ValueError("El número está fuera del rango permitido.")
            return number
        if answer_type in {"text", "textarea"}:
            normalized = " ".join(str(value or "").strip().split())
            if len(normalized) < 2 or len(normalized) > MAX_TEXT_ANSWER:
                raise ValueError("La respuesta de texto tiene una longitud inválida.")
            return normalized
        raise ValueError("El tipo de respuesta no está soportado por M34.3.")

    @staticmethod
    def _asserted_fact(question_contract: Mapping[str, Any], value: Any) -> dict[str, Any]:
        now = utc_iso()
        fact = {
            "fact_id": "fact_user_" + uuid.uuid4().hex[:16],
            "fact_type": str(question_contract["fact_type"]),
            "value": value,
            "normalized_value": value,
            "provenance": "USER_ASSERTED",
            "confirmation_status": "UNCONFIRMED",
            "criticality": str(question_contract.get("criticality") or "MEDIUM"),
            "source_reference": "m34-question:" + str(question_contract["question_contract_id"]),
            "evidence_ids": [],
            "extraction_confidence": None,
            "legal_relevance": "HIGH" if question_contract.get("criticality") in {"HIGH", "BLOCKING"} else "MEDIUM",
            "created_at": now,
            "updated_at": now,
            "notes": "Dato respondido directamente por el usuario durante el triage M34.3.",
        }
        errors = validate_legal_fact(fact)
        if errors:
            raise ValueError("La respuesta no pudo convertirse en un hecho trazable: " + "; ".join(errors))
        return fact

    def answer(self, con, token: str, engine: AdaptiveQuestionEngine, question_id: str, value: Any) -> dict[str, Any]:
        row = self._active_row(con, token)
        payload = self._decrypt(row)
        current_state = self._engine_state(row, payload)
        expected = engine.next_step(current_state)
        question = expected.get("question") or {}
        if str(question.get("question_id") or "") != str(question_id or ""):
            raise ValueError("La pregunta ya cambió o no corresponde al estado actual del diagnóstico.")
        m343 = self._m343(payload)
        history = m343.get("question_history") or []
        if len(history) >= MAX_HISTORY:
            raise ValueError("El diagnóstico alcanzó el límite de preguntas permitido.")

        action = expected.get("action")
        now = utc_iso()
        if action == "ROUTE_TOPIC":
            routed = engine.registry.routing_option(question_id, str(value or ""))
            option = routed["option"]
            entry = {
                "question_id": question_id,
                "value": str(option.get("value")),
                "product_codes": list(option.get("product_codes") or []),
                "answered_at": now,
            }
            if question_id == engine.registry.broad_routing.get("question_id"):
                m343["routing"] = {"broad": entry}
            else:
                routing = m343.setdefault("routing", {})
                routing["disambiguation"] = entry
            history.append({"question_id": question_id, "kind": "ROUTING", "answered_at": now})

        elif action == "CONFIRM_RISK":
            response = str(value or "").strip().lower()
            if response not in {"confirm", "dismiss", "uncertain"}:
                raise ValueError("La revisión de riesgo debe ser confirmar, descartar o no estoy seguro.")
            risk_code = str((expected.get("reason_codes") or [""])[0])
            target = next(
                (
                    item
                    for item in payload.get("risk_signals") or []
                    if str(item.get("code")) == risk_code and item.get("status") == "UNCONFIRMED_SIGNAL"
                ),
                None,
            )
            if not target:
                raise ValueError("La señal de riesgo ya no está pendiente.")
            target["status"] = {
                "confirm": "CONFIRMED_BY_USER",
                "dismiss": "DISMISSED_BY_USER",
                "uncertain": "USER_UNCERTAIN",
            }[response]
            target["reviewed_at"] = now
            history.append({"question_id": question_id, "kind": "RISK", "answered_at": now})

        elif action == "ASK_QUESTION":
            contract = engine.registry.fact_by_id.get(str(question_id))
            if not contract or contract.get("requirement_mode") != "TRIAGE_REQUIRED":
                raise ValueError("La pregunta jurídica no tiene un contrato de triage vigente.")
            normalized = self.normalize_answer(contract, value)
            existing_types = {
                str(fact.get("fact_type"))
                for fact in payload.get("facts") or []
                if fact_is_decision_usable(fact)
            }
            if str(contract["fact_type"]) in existing_types:
                raise ValueError("Este dato ya consta como hecho utilizable y no debe volver a preguntarse.")
            payload.setdefault("facts", []).append(self._asserted_fact(contract, normalized))
            history.append({"question_id": question_id, "kind": "FACT", "answered_at": now})
        else:
            raise ValueError("El estado actual no admite una respuesta M34.3.")

        m343["question_history"] = history
        interim_row = row
        interim_state = self._engine_state(interim_row, payload)
        next_step = engine.next_step(interim_state)
        m343["last_sufficiency"] = next_step.get("sufficiency")
        target_stage = {
            "ROUTE_TOPIC": "QUESTIONING",
            "CONFIRM_RISK": "RISK_CONFIRMATION",
            "ASK_QUESTION": "QUESTIONING",
            "READY_FOR_RECOMMENDATION": "RECOMMENDATION_READY",
            "ESCALATE": "ESCALATED",
            "OUT_OF_SCOPE": "OUT_OF_SCOPE",
        }.get(next_step["action"], "QUESTIONING")
        self._write_payload(con, row, payload, target_stage)
        return next_step


__all__ = [
    "AdaptiveIntakeStore",
    "AdaptiveQuestionEngine",
    "ContractValidation",
    "QuestionContractRegistry",
    "SCHEMA_VERSION",
]
