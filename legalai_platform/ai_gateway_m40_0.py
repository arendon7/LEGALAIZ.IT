from __future__ import annotations

"""M40.0 · AI Governance & Provider Gateway.

This module is intentionally library-only.  It does not expose a new HTTP route,
call an external model, mutate a case, approve a document, release a revision or
execute a payment.  It creates the governed boundary that future M40 copilots can
use without bypassing the M34 Legal Fact Model or the M39.1 tenancy boundary.
"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping, Protocol

from legalai_platform.enterprise_tenancy_m39_1 import EnterpriseContext
from legalai_platform.fact_extraction_m34_2 import FactExtractionProvider, FactExtractionService
from legalai_platform.m34_intelligent_journey import (
    FactCriticality,
    RiskCode,
    fact_is_decision_usable,
    load_product_contracts,
    validate_legal_fact,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "m40" / "ai_gateway_policy.json"
AI_GATEWAY_SCHEMA_VERSION = "40.0.0"

_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{2,180}$")
_PROVIDER_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,120}$")
_PROVIDER_MODE_RE = re.compile(r"^[A-Z0-9_:-]{3,80}$")
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,160}$")
_PROMPT_VERSION_RE = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")
_FACT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,220}$")
_REASON_CODE_RE = re.compile(r"^[A-Z0-9_]{2,100}$|^[a-z0-9_]{1,100}$")
_QUESTION_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,140}$")


class AIGatewayError(RuntimeError):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class AIAccessScope(str, Enum):
    PUBLIC_PREAUTH = "PUBLIC_PREAUTH"
    TENANT = "TENANT"


class AICapability(str, Enum):
    FACT_EXTRACTION = "FACT_EXTRACTION"
    INTAKE_ASSIST = "INTAKE_ASSIST"
    CASE_ASSIST = "CASE_ASSIST"
    DOCUMENT_ASSIST = "DOCUMENT_ASSIST"
    REVIEW_ASSIST = "REVIEW_ASSIST"
    LEGAL_RESEARCH = "LEGAL_RESEARCH"


class AIActionType(str, Enum):
    PROPOSE_FACT = "PROPOSE_FACT"
    FLAG_RISK = "FLAG_RISK"
    SIGNAL_TOPIC = "SIGNAL_TOPIC"
    ASK_QUESTION = "ASK_QUESTION"
    PROPOSE_TEXT = "PROPOSE_TEXT"
    SUGGEST_SOURCE = "SUGGEST_SOURCE"
    NO_ACTION = "NO_ACTION"


@dataclass(frozen=True)
class AIAccessContext:
    scope: str
    actor_id: str = ""
    organization_id: str = ""
    membership_id: str = ""
    tenancy_source: str = ""
    public_session_hash: str = ""


@dataclass(frozen=True)
class AIRequest:
    request_id: str
    capability: str
    access: AIAccessContext
    prompt_version: str
    payload: Mapping[str, Any]
    case_id: str = ""
    document_id: str = ""
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AIProviderDescriptor:
    provider_id: str
    provider_mode: str
    model_id: str
    external: bool


class AIProvider(Protocol):
    provider_id: str
    provider_mode: str
    model_id: str
    external: bool

    def invoke(self, context: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise AIGatewayError("El contexto de IA contiene datos no serializables.", code="AI_NON_SERIALIZABLE") from exc


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _bounded_json(value: Any, *, maximum: int, label: str) -> Any:
    serialized = _canonical_json(value)
    if len(serialized) > maximum:
        raise AIGatewayError(f"{label} supera el límite permitido.", code="AI_SIZE_LIMIT")
    return value


def _bounded_text(value: Any, *, maximum: int, label: str, required: bool = True) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise AIGatewayError(f"{label} es obligatorio.", code="AI_VALIDATION_ERROR")
    if len(text) > maximum:
        raise AIGatewayError(f"{label} supera el límite permitido.", code="AI_SIZE_LIMIT")
    return text


def load_ai_gateway_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AIGatewayError("No fue posible cargar la política M40.0.", code="AI_POLICY_UNAVAILABLE") from exc
    if payload.get("schema_version") != AI_GATEWAY_SCHEMA_VERSION:
        raise AIGatewayError("La política M40.0 no coincide con el esquema del gateway.", code="AI_POLICY_VERSION_MISMATCH")
    if not str(payload.get("policy_version") or "").strip():
        raise AIGatewayError("La política M40.0 no declara versión.", code="AI_POLICY_INVALID")
    return payload


def public_preauth_access(session_reference: str) -> AIAccessContext:
    reference = _bounded_text(session_reference, maximum=240, label="session_reference")
    return AIAccessContext(
        scope=AIAccessScope.PUBLIC_PREAUTH.value,
        public_session_hash=sha256(reference.encode("utf-8")).hexdigest(),
    )


def tenant_access_from_m39(user_id: str, context: EnterpriseContext) -> AIAccessContext:
    actor_id = _bounded_text(user_id, maximum=180, label="user_id")
    if not isinstance(context, EnterpriseContext):
        raise AIGatewayError("El contexto empresarial debe provenir de M39.1.", code="AI_TENANCY_CONTEXT_REQUIRED")
    organization = dict(context.organization or {})
    membership = dict(context.membership or {})
    if membership.get("user_id") != actor_id:
        raise AIGatewayError("La membresía no corresponde al actor de IA.", code="AI_TENANCY_MISMATCH")
    if membership.get("organization_id") != organization.get("id"):
        raise AIGatewayError("La membresía no corresponde a la organización activa.", code="AI_TENANCY_MISMATCH")
    if membership.get("status") != "active" or organization.get("status") != "active":
        raise AIGatewayError("La organización o membresía no está activa.", code="AI_TENANCY_INACTIVE")
    if context.source not in {"explicit", "sole_membership"}:
        raise AIGatewayError("La fuente del contexto empresarial no es reconocida.", code="AI_TENANCY_CONTEXT_REQUIRED")
    return AIAccessContext(
        scope=AIAccessScope.TENANT.value,
        actor_id=actor_id,
        organization_id=str(organization["id"]),
        membership_id=str(membership["id"]),
        tenancy_source=f"M39_1:{context.source}",
    )


class AIPolicyEngine:
    def __init__(self, policy: Mapping[str, Any] | None = None):
        self.policy = dict(policy or load_ai_gateway_policy())

    def _reject_sensitive_keys(self, value: Any, path: str = "payload") -> None:
        sensitive = {str(item).casefold() for item in self.policy.get("sensitive_context_keys", [])}
        if isinstance(value, Mapping):
            for raw_key, nested in value.items():
                key = str(raw_key)
                folded = key.casefold()
                if any(marker in folded for marker in sensitive):
                    raise AIGatewayError(
                        f"El contexto de IA contiene una clave sensible no permitida en {path}.{key}.",
                        code="AI_SENSITIVE_CONTEXT_BLOCKED",
                    )
                self._reject_sensitive_keys(nested, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, nested in enumerate(value):
                self._reject_sensitive_keys(nested, f"{path}[{index}]")

    @staticmethod
    def _validate_identifier(value: str, label: str, *, required: bool = False) -> None:
        if not value:
            if required:
                raise AIGatewayError(f"{label} es obligatorio.", code="AI_ACCESS_CONTEXT_INVALID")
            return
        if not _ID_RE.fullmatch(value):
            raise AIGatewayError(f"{label} no tiene un formato válido.", code="AI_ACCESS_CONTEXT_INVALID")

    def validate_request(self, request: AIRequest) -> None:
        try:
            scope = AIAccessScope(str(request.access.scope))
            capability = AICapability(str(request.capability))
        except ValueError as exc:
            raise AIGatewayError("El alcance o capacidad de IA no está soportado.", code="AI_POLICY_DENIED") from exc

        scopes = self.policy.get("access_scopes") or {}
        scope_policy = scopes.get(scope.value)
        if not isinstance(scope_policy, Mapping):
            raise AIGatewayError("El alcance solicitado no está habilitado.", code="AI_POLICY_DENIED")
        if capability.value not in set(scope_policy.get("capabilities") or []):
            raise AIGatewayError("La capacidad de IA no está habilitada para este alcance.", code="AI_POLICY_DENIED")

        self._validate_identifier(str(request.request_id), "request_id", required=True)
        if not _PROMPT_VERSION_RE.fullmatch(str(request.prompt_version or "")):
            raise AIGatewayError("prompt_version no tiene un formato válido.", code="AI_PROMPT_VERSION_INVALID")

        access = request.access
        if scope == AIAccessScope.PUBLIC_PREAUTH:
            if any((access.actor_id, access.organization_id, access.membership_id, access.tenancy_source)):
                raise AIGatewayError("El contexto público preautenticado no puede simular un tenant.", code="AI_TENANCY_BYPASS_BLOCKED")
            if not re.fullmatch(r"[a-f0-9]{64}", str(access.public_session_hash or "")):
                raise AIGatewayError("El contexto público requiere una referencia de sesión hasheada.", code="AI_ACCESS_CONTEXT_INVALID")
            if request.case_id or request.document_id:
                raise AIGatewayError("El alcance público no puede acceder a expedientes ni documentos privados.", code="AI_TENANCY_BYPASS_BLOCKED")
        else:
            self._validate_identifier(str(access.actor_id), "actor_id", required=True)
            self._validate_identifier(str(access.organization_id), "organization_id", required=True)
            self._validate_identifier(str(access.membership_id), "membership_id", required=True)
            if not str(access.tenancy_source).startswith("M39_1:"):
                raise AIGatewayError("El alcance tenant requiere contexto resuelto por M39.1.", code="AI_TENANCY_CONTEXT_REQUIRED")
            if access.public_session_hash:
                raise AIGatewayError("Un contexto tenant no puede reutilizar una identidad pública preauth.", code="AI_ACCESS_CONTEXT_INVALID")
            self._validate_identifier(str(request.case_id), "case_id")
            self._validate_identifier(str(request.document_id), "document_id")

        allowed_payload = set((self.policy.get("capability_payload_keys") or {}).get(capability.value) or [])
        actual_payload = {str(key) for key in request.payload.keys()}
        unexpected = sorted(actual_payload - allowed_payload)
        if unexpected:
            raise AIGatewayError(
                f"La capacidad {capability.value} recibió claves de contexto no permitidas: {', '.join(unexpected)}",
                code="AI_CONTEXT_NOT_ALLOWLISTED",
            )
        self._reject_sensitive_keys(request.payload)
        limits = self.policy.get("limits") or {}
        _bounded_json(
            request.payload,
            maximum=int(limits.get("max_context_json_chars", 64000)),
            label="El contexto de IA",
        )

        source_ids = tuple(str(item) for item in request.source_ids)
        if len(source_ids) > int(limits.get("max_source_ids", 32)):
            raise AIGatewayError("La solicitud contiene demasiadas fuentes.", code="AI_SIZE_LIMIT")
        if len(source_ids) != len(set(source_ids)) or any(not _SOURCE_ID_RE.fullmatch(item) for item in source_ids):
            raise AIGatewayError("Los identificadores de fuente no son válidos.", code="AI_SOURCE_INVALID")


class AIContextBuilder:
    def __init__(self, policy_engine: AIPolicyEngine | None = None):
        self.policy_engine = policy_engine or AIPolicyEngine()

    def build(self, request: AIRequest) -> dict[str, Any]:
        self.policy_engine.validate_request(request)
        access = request.access
        return {
            "schema_version": AI_GATEWAY_SCHEMA_VERSION,
            "request_id": request.request_id,
            "capability": request.capability,
            "access": {
                "scope": access.scope,
                "actor_id": access.actor_id or None,
                "organization_id": access.organization_id or None,
                "membership_id": access.membership_id or None,
                "tenancy_source": access.tenancy_source or None,
                "public_session_hash": access.public_session_hash or None,
            },
            "case_id": request.case_id or None,
            "document_id": request.document_id or None,
            "prompt_version": request.prompt_version,
            "source_ids": list(request.source_ids),
            "payload": deepcopy(dict(request.payload)),
        }


class AIStructuredOutputValidator:
    def __init__(self, policy: Mapping[str, Any] | None = None):
        self.policy = dict(policy or load_ai_gateway_policy())
        self.products = load_product_contracts()

    def _reject_forbidden_output_keys(self, value: Any, path: str = "output") -> None:
        forbidden = {str(item).casefold() for item in self.policy.get("forbidden_provider_output_keys", [])}
        if isinstance(value, Mapping):
            for raw_key, nested in value.items():
                key = str(raw_key)
                if key.casefold() in forbidden:
                    raise AIGatewayError(
                        f"El proveedor intentó emitir un estado reservado: {path}.{key}",
                        code="AI_RESERVED_STATE_BLOCKED",
                    )
                self._reject_forbidden_output_keys(nested, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, nested in enumerate(value):
                self._reject_forbidden_output_keys(nested, f"{path}[{index}]")

    @staticmethod
    def _confidence(value: Any, *, label: str, required: bool = False) -> float | None:
        if value is None and not required:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AIGatewayError(f"{label} debe ser un número entre 0 y 1.", code="AI_OUTPUT_INVALID")
        number = float(value)
        if not 0 <= number <= 1:
            raise AIGatewayError(f"{label} está fuera de rango.", code="AI_OUTPUT_INVALID")
        return round(number, 4)

    def _fact(self, candidate: Mapping[str, Any], request: AIRequest) -> dict[str, Any]:
        fact_type = str(candidate.get("fact_type") or "").strip()
        if not _FACT_TYPE_RE.fullmatch(fact_type):
            raise AIGatewayError("El proveedor propuso un tipo de hecho inválido.", code="AI_OUTPUT_INVALID")
        if "value" not in candidate:
            raise AIGatewayError("El proveedor propuso un hecho sin valor.", code="AI_OUTPUT_INVALID")
        limits = self.policy.get("limits") or {}
        value = deepcopy(candidate.get("value"))
        _bounded_json(value, maximum=int(limits.get("max_fact_value_json_chars", 4000)), label="El valor del hecho")
        normalized = deepcopy(candidate.get("normalized_value", value))
        _bounded_json(normalized, maximum=int(limits.get("max_fact_value_json_chars", 4000)), label="El valor normalizado")
        confidence = self._confidence(candidate.get("extraction_confidence", candidate.get("confidence", 0.5)), label="La confianza del hecho", required=True)
        criticality = str(candidate.get("criticality") or FactCriticality.MEDIUM.value)
        if criticality not in {item.value for item in FactCriticality}:
            raise AIGatewayError("La criticidad del hecho no es válida.", code="AI_OUTPUT_INVALID")
        source_reference = str(candidate.get("source_reference") or f"ai-gateway:{request.request_id}").strip()
        if not source_reference or len(source_reference) > 256:
            raise AIGatewayError("La referencia del hecho propuesto no es válida.", code="AI_OUTPUT_INVALID")
        fingerprint = _hash({"request_id": request.request_id, "fact_type": fact_type, "value": value})[:16]
        fact = {
            "fact_id": f"fact_ai_m40_{fingerprint}",
            "fact_type": fact_type,
            "value": value,
            "normalized_value": normalized,
            "provenance": "AI_INFERRED",
            "confirmation_status": "UNCONFIRMED",
            "criticality": criticality,
            "source_reference": source_reference,
            "evidence_ids": [],
            "extraction_confidence": confidence,
            "legal_relevance": str(candidate.get("legal_relevance") or "MEDIUM")[:40],
            "created_at": None,
            "updated_at": None,
            "notes": "Candidato M40.0; requiere confirmación humana antes de uso decisorio.",
        }
        errors = validate_legal_fact(fact)
        if errors:
            raise AIGatewayError("El hecho propuesto no supera el Legal Fact Model: " + "; ".join(errors), code="AI_OUTPUT_INVALID")
        if fact_is_decision_usable(fact):
            raise AIGatewayError("Un hecho inferido por IA no puede salir como decisorio.", code="AI_FACT_PROMOTION_BLOCKED")
        return fact

    def _action(self, raw: Mapping[str, Any], request: AIRequest) -> dict[str, Any]:
        action_type = str(raw.get("type") or "").strip().upper()
        forbidden = set(self.policy.get("forbidden_action_types") or [])
        allowed = set(self.policy.get("allowed_action_types") or [])
        if action_type in forbidden:
            raise AIGatewayError(f"La acción {action_type} está reservada a flujos humanos/controlados.", code="AI_FORBIDDEN_ACTION")
        if action_type not in allowed:
            raise AIGatewayError(f"La acción de IA {action_type or '<vacía>'} no está soportada.", code="AI_ACTION_UNKNOWN")

        if action_type == AIActionType.PROPOSE_FACT.value:
            candidate = raw.get("fact")
            if not isinstance(candidate, Mapping):
                raise AIGatewayError("PROPOSE_FACT requiere un hecho estructurado.", code="AI_OUTPUT_INVALID")
            return {"type": action_type, "fact": self._fact(candidate, request), "status": "REQUIRES_HUMAN_CONFIRMATION"}

        if action_type == AIActionType.FLAG_RISK.value:
            risk = raw.get("risk")
            if not isinstance(risk, Mapping):
                raise AIGatewayError("FLAG_RISK requiere una señal estructurada.", code="AI_OUTPUT_INVALID")
            code = str(risk.get("code") or "")
            if code not in {item.value for item in RiskCode}:
                raise AIGatewayError(f"La señal de riesgo no está soportada: {code}", code="AI_OUTPUT_INVALID")
            return {
                "type": action_type,
                "risk": {
                    "code": code,
                    "confidence": self._confidence(risk.get("confidence", 0.5), label="La confianza de riesgo", required=True),
                    "status": "UNCONFIRMED_SIGNAL",
                },
            }

        if action_type == AIActionType.SIGNAL_TOPIC.value:
            product = raw.get("product")
            if not isinstance(product, Mapping):
                raise AIGatewayError("SIGNAL_TOPIC requiere un producto estructurado.", code="AI_OUTPUT_INVALID")
            code = str(product.get("product_code") or "")
            if code not in self.products:
                raise AIGatewayError(f"El producto señalado no pertenece al catálogo: {code}", code="AI_OUTPUT_INVALID")
            reasons = product.get("reason_codes") or []
            if not isinstance(reasons, list) or any(not _REASON_CODE_RE.fullmatch(str(item)) for item in reasons[:8]):
                raise AIGatewayError("Los códigos de razón del producto no son válidos.", code="AI_OUTPUT_INVALID")
            return {
                "type": action_type,
                "product": {
                    "product_code": code,
                    "reason_codes": [str(item) for item in reasons[:8]],
                    "status": "TOPIC_SIGNAL_ONLY",
                },
            }

        if action_type == AIActionType.ASK_QUESTION.value:
            question = raw.get("question")
            if not isinstance(question, Mapping):
                raise AIGatewayError("ASK_QUESTION requiere una pregunta estructurada.", code="AI_OUTPUT_INVALID")
            question_id = str(question.get("question_id") or "")
            if not _QUESTION_ID_RE.fullmatch(question_id):
                raise AIGatewayError("El identificador de la pregunta no es válido.", code="AI_OUTPUT_INVALID")
            prompt = _bounded_text(
                question.get("prompt"),
                maximum=int((self.policy.get("limits") or {}).get("max_question_chars", 1200)),
                label="La pregunta propuesta",
            )
            return {
                "type": action_type,
                "question": {"question_id": question_id, "prompt": prompt},
                "status": "AI_PROPOSAL_REQUIRES_USER_ACTION",
            }

        if action_type == AIActionType.PROPOSE_TEXT.value:
            text = _bounded_text(
                raw.get("text"),
                maximum=int((self.policy.get("limits") or {}).get("max_text_proposal_chars", 24000)),
                label="El texto propuesto",
            )
            purpose = str(raw.get("purpose") or "DRAFT").strip().upper()
            if not re.fullmatch(r"[A-Z0-9_]{2,80}", purpose):
                raise AIGatewayError("El propósito del texto no es válido.", code="AI_OUTPUT_INVALID")
            return {
                "type": action_type,
                "text": text,
                "purpose": purpose,
                "status": "DRAFT_AI_PROPOSAL_REQUIRES_HUMAN_REVIEW",
            }

        if action_type == AIActionType.SUGGEST_SOURCE.value:
            source = raw.get("source")
            if not isinstance(source, Mapping):
                raise AIGatewayError("SUGGEST_SOURCE requiere una fuente estructurada.", code="AI_OUTPUT_INVALID")
            source_id = str(source.get("source_id") or "")
            if not _SOURCE_ID_RE.fullmatch(source_id):
                raise AIGatewayError("El identificador de fuente sugerida no es válido.", code="AI_OUTPUT_INVALID")
            return {
                "type": action_type,
                "source": {"source_id": source_id},
                "status": "SOURCE_CANDIDATE_REQUIRES_VERIFICATION",
            }

        return {"type": AIActionType.NO_ACTION.value}

    def validate(self, raw: Mapping[str, Any], request: AIRequest) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise AIGatewayError("El proveedor devolvió una salida no estructurada.", code="AI_OUTPUT_INVALID")
        limits = self.policy.get("limits") or {}
        _bounded_json(raw, maximum=int(limits.get("max_output_json_chars", 96000)), label="La salida del proveedor")
        self._reject_forbidden_output_keys(raw)
        if raw.get("schema_version") != AI_GATEWAY_SCHEMA_VERSION:
            raise AIGatewayError("La salida del proveedor no coincide con el esquema M40.0.", code="AI_OUTPUT_VERSION_MISMATCH")
        actions = raw.get("actions") or []
        if not isinstance(actions, list) or len(actions) > int(limits.get("max_actions", 32)):
            raise AIGatewayError("La cantidad de acciones del proveedor no es válida.", code="AI_OUTPUT_INVALID")
        sanitized = [self._action(action, request) for action in actions if isinstance(action, Mapping)]
        if len(sanitized) != len(actions):
            raise AIGatewayError("El proveedor devolvió una acción con formato inválido.", code="AI_OUTPUT_INVALID")
        source_ids = raw.get("source_ids") or []
        if not isinstance(source_ids, list) or len(source_ids) > int(limits.get("max_source_ids", 32)):
            raise AIGatewayError("La salida contiene demasiadas fuentes.", code="AI_OUTPUT_INVALID")
        source_ids = [str(item) for item in source_ids]
        if len(source_ids) != len(set(source_ids)) or any(not _SOURCE_ID_RE.fullmatch(item) for item in source_ids):
            raise AIGatewayError("La salida contiene identificadores de fuente inválidos.", code="AI_SOURCE_INVALID")
        confidence = self._confidence(raw.get("confidence"), label="La confianza global")
        action_types = [item["type"] for item in sanitized]
        return {
            "schema_version": AI_GATEWAY_SCHEMA_VERSION,
            "actions": sanitized,
            "confidence": confidence,
            "source_ids": source_ids,
            "human_confirmation_required": AIActionType.PROPOSE_FACT.value in action_types,
            "notice": "La salida de IA es una propuesta controlada; no constituye aprobación Legal, QA, liberación documental ni autorización de pago.",
        }


class AIAuditBuilder:
    def __init__(self, policy: Mapping[str, Any] | None = None):
        self.policy = dict(policy or load_ai_gateway_policy())

    def build(
        self,
        *,
        request: AIRequest,
        context: Mapping[str, Any],
        result: Mapping[str, Any],
        provider: AIProviderDescriptor,
    ) -> dict[str, Any]:
        input_hash = _hash(context)
        output_hash = _hash(result)
        action_types = [str(item.get("type")) for item in result.get("actions", [])]
        all_sources = list(dict.fromkeys([*request.source_ids, *tuple(result.get("source_ids") or [])]))
        audit_id = "AI-AUD-" + sha256(f"{request.request_id}:{input_hash}:{output_hash}".encode("utf-8")).hexdigest()[:20].upper()
        return {
            "schema_version": AI_GATEWAY_SCHEMA_VERSION,
            "audit_id": audit_id,
            "created_at": _utc_iso(),
            "request_id": request.request_id,
            "policy_version": self.policy["policy_version"],
            "capability": request.capability,
            "access_scope": request.access.scope,
            "actor_id": request.access.actor_id or None,
            "organization_id": request.access.organization_id or None,
            "case_id": request.case_id or None,
            "document_id": request.document_id or None,
            "provider": {
                "id": provider.provider_id,
                "mode": provider.provider_mode,
                "model_id": provider.model_id,
                "external": provider.external,
            },
            "prompt_version": request.prompt_version,
            "source_ids": all_sources,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "output": {
                "schema_version": result.get("schema_version"),
                "action_count": len(action_types),
                "action_types": action_types,
                "human_confirmation_required": bool(result.get("human_confirmation_required")),
            },
            "confidence": result.get("confidence"),
            "human_confirmation_required": bool(result.get("human_confirmation_required")),
        }


class StaticDeterministicProvider:
    """Provider fixture for QA/dev. Never performs network or autonomous actions."""

    provider_id = "m40.test.static.v1"
    provider_mode = "TEST_DETERMINISTIC"
    model_id = "static-fixture-v1"
    external = False

    def __init__(self, output: Mapping[str, Any]):
        self.output = deepcopy(dict(output))

    def invoke(self, context: Mapping[str, Any]) -> Mapping[str, Any]:
        return deepcopy(self.output)


class M34FactExtractionAdapter:
    """Compatibility adapter: M40 governs the existing M34.2 extraction service."""

    provider_id = "m40.adapter.m34.fact-extraction.v1"
    provider_mode = "M34_COMPAT"
    model_id = "m34-fact-extraction-contract"
    external = False

    def __init__(self, provider: FactExtractionProvider | None = None):
        self.service = FactExtractionService(provider)
        descriptor = self.service.descriptor
        self.model_id = descriptor.provider_id
        self.external = bool(descriptor.ai_enabled)

    def invoke(self, context: Mapping[str, Any]) -> Mapping[str, Any]:
        if context.get("capability") != AICapability.FACT_EXTRACTION.value:
            raise AIGatewayError("El adaptador M34.2 sólo admite FACT_EXTRACTION.", code="AI_PROVIDER_CAPABILITY_MISMATCH")
        payload = context.get("payload") or {}
        extraction = self.service.extract(
            str(payload.get("problem_statement") or ""),
            str(payload.get("source_reference") or ""),
        )
        actions: list[dict[str, Any]] = []
        confidences: list[float] = []
        for fact in extraction.get("facts", []):
            actions.append({"type": AIActionType.PROPOSE_FACT.value, "fact": fact})
            if fact.get("extraction_confidence") is not None:
                confidences.append(float(fact["extraction_confidence"]))
        for risk in extraction.get("risk_signals", []):
            actions.append({"type": AIActionType.FLAG_RISK.value, "risk": risk})
            if risk.get("confidence") is not None:
                confidences.append(float(risk["confidence"]))
        for product in extraction.get("candidate_products", []):
            actions.append({
                "type": AIActionType.SIGNAL_TOPIC.value,
                "product": {
                    "product_code": product.get("product_code"),
                    "reason_codes": product.get("reason_codes") or [],
                },
            })
        confidence = round(sum(confidences) / len(confidences), 4) if confidences else None
        return {
            "schema_version": AI_GATEWAY_SCHEMA_VERSION,
            "actions": actions,
            "confidence": confidence,
            "source_ids": [],
        }


class AIGateway:
    def __init__(
        self,
        *,
        policy_engine: AIPolicyEngine | None = None,
        context_builder: AIContextBuilder | None = None,
        output_validator: AIStructuredOutputValidator | None = None,
        audit_builder: AIAuditBuilder | None = None,
    ):
        self.policy_engine = policy_engine or AIPolicyEngine()
        self.context_builder = context_builder or AIContextBuilder(self.policy_engine)
        self.output_validator = output_validator or AIStructuredOutputValidator(self.policy_engine.policy)
        self.audit_builder = audit_builder or AIAuditBuilder(self.policy_engine.policy)

    @staticmethod
    def _descriptor(provider: AIProvider) -> AIProviderDescriptor:
        descriptor = AIProviderDescriptor(
            provider_id=str(provider.provider_id),
            provider_mode=str(provider.provider_mode),
            model_id=str(provider.model_id),
            external=bool(provider.external),
        )
        if not _PROVIDER_ID_RE.fullmatch(descriptor.provider_id):
            raise AIGatewayError("El identificador del proveedor no es válido.", code="AI_PROVIDER_INVALID")
        if not _PROVIDER_MODE_RE.fullmatch(descriptor.provider_mode):
            raise AIGatewayError("El modo del proveedor no es válido.", code="AI_PROVIDER_INVALID")
        if not _MODEL_ID_RE.fullmatch(descriptor.model_id):
            raise AIGatewayError("El identificador del modelo no es válido.", code="AI_PROVIDER_INVALID")
        return descriptor

    def execute(self, request: AIRequest, provider: AIProvider) -> dict[str, Any]:
        context = self.context_builder.build(request)
        descriptor = self._descriptor(provider)
        raw = provider.invoke(context)
        result = self.output_validator.validate(raw, request)
        audit = self.audit_builder.build(
            request=request,
            context=context,
            result=result,
            provider=descriptor,
        )
        return {
            "result": result,
            "audit": audit,
        }


__all__ = [
    "AIAccessContext",
    "AIAccessScope",
    "AIAuditBuilder",
    "AICapability",
    "AIActionType",
    "AIContextBuilder",
    "AIGateway",
    "AIGatewayError",
    "AIProvider",
    "AIProviderDescriptor",
    "AIPolicyEngine",
    "AIRequest",
    "AIStructuredOutputValidator",
    "AI_GATEWAY_SCHEMA_VERSION",
    "M34FactExtractionAdapter",
    "StaticDeterministicProvider",
    "load_ai_gateway_policy",
    "public_preauth_access",
    "tenant_access_from_m39",
]
