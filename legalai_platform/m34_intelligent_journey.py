"""M34.0 foundation for the LegalAIZ.it intelligent journey.

This module is intentionally deterministic.  It does not call an LLM and it does
not replace the existing interview, rule, source, document-factory, review or QA
layers.  Its job is to give those layers a stable contract for the future M34
intake/orchestration work.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_CONTRACTS_PATH = ROOT / "config" / "m34" / "product_contracts.json"
LEGAL_FACT_SCHEMA_PATH = ROOT / "config" / "m34" / "legal_fact.schema.json"
INTERVIEWS_PATH = ROOT / "data" / "interviews.json"
RULES_PATH = ROOT / "data" / "rules.json"
ADVANCED_LIBRARY_ROOT = ROOT / "app" / "assets" / "advanced-legal-library"

FACT_ID_RE = re.compile(r"^fact_[A-Za-z0-9_-]+$")
FACT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


class FactProvenance(str, Enum):
    USER_ASSERTED = "USER_ASSERTED"
    DOCUMENT_EXTRACTED = "DOCUMENT_EXTRACTED"
    AI_INFERRED = "AI_INFERRED"
    RULE_DERIVED = "RULE_DERIVED"
    USER_CONFIRMED = "USER_CONFIRMED"
    LEGAL_REVIEWED = "LEGAL_REVIEWED"
    DISPUTED = "DISPUTED"


class ConfirmationStatus(str, Enum):
    UNCONFIRMED = "UNCONFIRMED"
    CONFIRMED_BY_USER = "CONFIRMED_BY_USER"
    CONFIRMED_BY_LEGAL_REVIEW = "CONFIRMED_BY_LEGAL_REVIEW"
    DISPUTED = "DISPUTED"
    SUPERSEDED = "SUPERSEDED"


class FactCriticality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKING = "BLOCKING"


class NextAction(str, Enum):
    RECOMMEND = "RECOMMEND"
    ASK_MORE = "ASK_MORE"
    ESCALATE = "ESCALATE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class RiskCode(str, Enum):
    DEADLINE_RISK = "DEADLINE_RISK"
    LITIGATION_ACTIVE = "LITIGATION_ACTIVE"
    CRIMINAL_MATTER = "CRIMINAL_MATTER"
    TAX_COMPLEXITY = "TAX_COMPLEXITY"
    REGULATORY_COMPLEXITY = "REGULATORY_COMPLEXITY"
    HIGH_VALUE = "HIGH_VALUE"
    MINOR_OR_VULNERABLE_PERSON = "MINOR_OR_VULNERABLE_PERSON"
    PERSONAL_DATA_SENSITIVE = "PERSONAL_DATA_SENSITIVE"
    MULTIPLE_PARTIES = "MULTIPLE_PARTIES"
    FACT_CONTRADICTION = "FACT_CONTRADICTION"
    DOCUMENT_CONTRADICTION = "DOCUMENT_CONTRADICTION"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    OUT_OF_JURISDICTION = "OUT_OF_JURISDICTION"
    OUT_OF_CATALOG = "OUT_OF_CATALOG"
    PROFESSIONAL_REVIEW_REQUIRED = "PROFESSIONAL_REVIEW_REQUIRED"


@dataclass(frozen=True)
class PortfolioInventory:
    products: int
    questions: int
    rules: int
    interview_product_codes: tuple[str, ...]
    rule_product_codes: tuple[str, ...]
    advanced_product_codes: tuple[str, ...]


@dataclass(frozen=True)
class FoundationValidation:
    ok: bool
    errors: tuple[str, ...]
    inventory: PortfolioInventory


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_product_contract_registry() -> dict[str, Any]:
    payload = _load_json(PRODUCT_CONTRACTS_PATH)
    if not isinstance(payload, dict):
        raise ValueError("M34 product contract registry must be a JSON object")
    return payload


def load_product_contracts() -> dict[str, dict[str, Any]]:
    payload = load_product_contract_registry()
    contracts = payload.get("contracts")
    if not isinstance(contracts, list):
        raise ValueError("M34 product contract registry requires a contracts array")

    indexed: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        if not isinstance(contract, dict):
            raise ValueError("Every M34 product contract must be an object")
        code = str(contract.get("product_code") or "").strip()
        if not code:
            raise ValueError("Every M34 product contract requires product_code")
        if code in indexed:
            raise ValueError(f"Duplicate M34 product contract: {code}")
        indexed[code] = contract
    return indexed


def portfolio_inventory() -> PortfolioInventory:
    interviews = _load_json(INTERVIEWS_PATH)
    rules = _load_json(RULES_PATH)

    if not isinstance(interviews, dict) or not isinstance(rules, dict):
        raise ValueError("Runtime interviews and rules must be keyed JSON objects")

    question_count = 0
    for code, interview in interviews.items():
        if not isinstance(interview, dict):
            raise ValueError(f"Interview {code} must be an object")
        questions = interview.get("questions", [])
        if not isinstance(questions, list):
            raise ValueError(f"Interview {code}.questions must be an array")
        question_count += len(questions)

    rule_count = 0
    for code, product_rules in rules.items():
        if not isinstance(product_rules, list):
            raise ValueError(f"Rules {code} must be an array")
        rule_count += len(product_rules)

    advanced_codes = sorted(
        path.name
        for path in ADVANCED_LIBRARY_ROOT.iterdir()
        if path.is_dir() and path.name.startswith("CO-")
    )

    return PortfolioInventory(
        products=len(interviews),
        questions=question_count,
        rules=rule_count,
        interview_product_codes=tuple(sorted(interviews)),
        rule_product_codes=tuple(sorted(rules)),
        advanced_product_codes=tuple(advanced_codes),
    )


def validate_legal_fact(fact: Mapping[str, Any]) -> tuple[str, ...]:
    """Validate the M34 invariants that do not require a JSON Schema package."""

    errors: list[str] = []
    required = (
        "fact_id",
        "fact_type",
        "value",
        "provenance",
        "confirmation_status",
        "criticality",
        "source_reference",
    )
    for field in required:
        if field not in fact:
            errors.append(f"missing field: {field}")

    fact_id = str(fact.get("fact_id") or "")
    if fact_id and not FACT_ID_RE.match(fact_id):
        errors.append("fact_id does not follow fact_<id>")

    fact_type = str(fact.get("fact_type") or "")
    if fact_type and not FACT_TYPE_RE.match(fact_type):
        errors.append("fact_type must be a dotted lowercase namespace")

    try:
        provenance = FactProvenance(str(fact.get("provenance")))
    except ValueError:
        provenance = None
        errors.append("invalid provenance")

    try:
        confirmation = ConfirmationStatus(str(fact.get("confirmation_status")))
    except ValueError:
        confirmation = None
        errors.append("invalid confirmation_status")

    try:
        FactCriticality(str(fact.get("criticality")))
    except ValueError:
        errors.append("invalid criticality")

    source_reference = str(fact.get("source_reference") or "").strip()
    if "source_reference" in fact and not source_reference:
        errors.append("source_reference cannot be empty")

    confidence = fact.get("extraction_confidence")
    if confidence is not None:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            errors.append("extraction_confidence must be a number between 0 and 1")
        elif not 0 <= float(confidence) <= 1:
            errors.append("extraction_confidence must be between 0 and 1")

    if provenance == FactProvenance.AI_INFERRED and confirmation in {
        ConfirmationStatus.CONFIRMED_BY_USER,
        ConfirmationStatus.CONFIRMED_BY_LEGAL_REVIEW,
    }:
        errors.append(
            "AI_INFERRED cannot be silently promoted to confirmed; create a user/legal-confirmed fact event"
        )

    if provenance == FactProvenance.DISPUTED and confirmation not in {
        ConfirmationStatus.DISPUTED,
        ConfirmationStatus.SUPERSEDED,
    }:
        errors.append("DISPUTED provenance requires DISPUTED or SUPERSEDED confirmation status")

    return tuple(errors)


def fact_is_decision_usable(fact: Mapping[str, Any]) -> bool:
    """Conservative gate for facts used in a recommendation decision.

    User assertions can be used as assertions. Document extractions and AI
    inferences require an explicit user or legal confirmation event before they
    may become decisive. Disputed/superseded facts are never decisive.
    """

    if validate_legal_fact(fact):
        return False

    provenance = FactProvenance(str(fact["provenance"]))
    confirmation = ConfirmationStatus(str(fact["confirmation_status"]))

    if confirmation in {ConfirmationStatus.DISPUTED, ConfirmationStatus.SUPERSEDED}:
        return False
    if provenance in {FactProvenance.AI_INFERRED, FactProvenance.DOCUMENT_EXTRACTED}:
        return confirmation in {
            ConfirmationStatus.CONFIRMED_BY_USER,
            ConfirmationStatus.CONFIRMED_BY_LEGAL_REVIEW,
        }
    return provenance in {
        FactProvenance.USER_ASSERTED,
        FactProvenance.USER_CONFIRMED,
        FactProvenance.LEGAL_REVIEWED,
        FactProvenance.RULE_DERIVED,
    }


def missing_recommendation_facts(
    product_code: str, facts: Iterable[Mapping[str, Any]]
) -> tuple[str, ...]:
    contracts = load_product_contracts()
    if product_code not in contracts:
        raise KeyError(product_code)

    usable_types = {
        str(fact.get("fact_type"))
        for fact in facts
        if fact_is_decision_usable(fact)
    }
    required = contracts[product_code]["minimum_recommendation_facts"]
    return tuple(fact_type for fact_type in required if fact_type not in usable_types)


def validate_foundation() -> FoundationValidation:
    registry = load_product_contract_registry()
    contracts = load_product_contracts()
    inventory = portfolio_inventory()
    floors = registry.get("compatibility_floors", {})
    errors: list[str] = []

    expected_products = int(floors.get("products", 11))
    minimum_questions = int(floors.get("questions", 473))
    minimum_rules = int(floors.get("rules", 273))

    if len(contracts) != expected_products:
        errors.append(
            f"product contracts: expected {expected_products}, found {len(contracts)}"
        )
    if inventory.products != expected_products:
        errors.append(
            f"runtime interviews: expected {expected_products}, found {inventory.products}"
        )
    if inventory.questions < minimum_questions:
        errors.append(
            f"runtime interview coverage regressed: {inventory.questions} < {minimum_questions}"
        )
    if inventory.rules < minimum_rules:
        errors.append(f"runtime rule coverage regressed: {inventory.rules} < {minimum_rules}")

    contract_codes = set(contracts)
    interview_codes = set(inventory.interview_product_codes)
    rule_codes = set(inventory.rule_product_codes)
    advanced_codes = set(inventory.advanced_product_codes)

    if contract_codes != interview_codes:
        errors.append(
            "contract/interview product mismatch: "
            f"contracts_only={sorted(contract_codes - interview_codes)}; "
            f"interviews_only={sorted(interview_codes - contract_codes)}"
        )
    if contract_codes != rule_codes:
        errors.append(
            "contract/rule product mismatch: "
            f"contracts_only={sorted(contract_codes - rule_codes)}; "
            f"rules_only={sorted(rule_codes - contract_codes)}"
        )
    if contract_codes != advanced_codes:
        errors.append(
            "contract/advanced-library product mismatch: "
            f"contracts_only={sorted(contract_codes - advanced_codes)}; "
            f"library_only={sorted(advanced_codes - contract_codes)}"
        )

    allowed_risks = {item.value for item in RiskCode}
    allowed_actions = {item.value for item in NextAction}
    registry_actions = set(registry.get("decision_outcomes", []))
    if registry_actions != allowed_actions:
        errors.append(
            f"decision outcomes drift: registry={sorted(registry_actions)} code={sorted(allowed_actions)}"
        )

    for code, contract in contracts.items():
        if contract.get("runtime", {}).get("interview_key") != code:
            errors.append(f"{code}: runtime interview key mismatch")
        if contract.get("runtime", {}).get("rules_key") != code:
            errors.append(f"{code}: runtime rules key mismatch")

        minimum_facts = contract.get("minimum_recommendation_facts")
        if not isinstance(minimum_facts, list) or not minimum_facts:
            errors.append(f"{code}: minimum_recommendation_facts must be non-empty")
        elif len(minimum_facts) != len(set(minimum_facts)):
            errors.append(f"{code}: duplicate minimum recommendation fact")
        else:
            for fact_type in minimum_facts:
                if not FACT_TYPE_RE.match(str(fact_type)):
                    errors.append(f"{code}: invalid fact type {fact_type}")

        for risk in contract.get("blocking_risks", []):
            if risk not in allowed_risks:
                errors.append(f"{code}: unsupported blocking risk {risk}")

        for section in ("runtime", "advanced_library"):
            bindings = contract.get(section)
            if not isinstance(bindings, dict):
                errors.append(f"{code}: missing {section} bindings")
                continue
            for binding_name, relative_path in bindings.items():
                if binding_name.endswith("_key"):
                    continue
                path = ROOT / str(relative_path)
                if not path.exists():
                    errors.append(f"{code}: missing source {relative_path}")

    if not LEGAL_FACT_SCHEMA_PATH.exists():
        errors.append("missing M34 Legal Fact JSON Schema")

    return FoundationValidation(ok=not errors, errors=tuple(errors), inventory=inventory)


__all__ = [
    "ConfirmationStatus",
    "FactCriticality",
    "FactProvenance",
    "FoundationValidation",
    "NextAction",
    "PortfolioInventory",
    "RiskCode",
    "fact_is_decision_usable",
    "load_product_contract_registry",
    "load_product_contracts",
    "missing_recommendation_facts",
    "portfolio_inventory",
    "validate_foundation",
    "validate_legal_fact",
]
