from __future__ import annotations

"""M40.0 governed AI runtime controls.

This module wraps the library-only M40.0 gateway with bounded execution controls:
timeout contracts, cumulative provider budgets, circuit breaker/fallback, and an
append-only audit ledger with hash chaining.  It does not expose HTTP routes,
perform network calls by itself, mutate legal facts/cases/documents, or bypass
human Legal/QA approvals.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import sqlite3
import time
from typing import Any, Callable, Mapping, Sequence

from legalai_platform.ai_gateway_m40_0 import (
    AIGateway,
    AIGatewayError,
    AIProvider,
    AIProviderDescriptor,
    AIRequest,
    AI_GATEWAY_SCHEMA_VERSION,
    load_ai_gateway_policy,
)


_RUNTIME_USAGE_KEY = "_runtime_usage"
_TERMINAL_RUNTIME_CODES = {"AI_BUDGET_EXCEEDED", "AI_USAGE_REQUIRED", "AI_USAGE_INVALID"}


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise AIGatewayError("El registro de auditoría contiene datos no serializables.", code="AI_AUDIT_INVALID") from exc


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AIRuntimeLimits:
    default_timeout_ms: int
    max_timeout_ms: int
    max_provider_units_per_request: int
    circuit_failure_threshold: int
    circuit_recovery_seconds: int
    max_fallback_providers: int
    external_provider_usage_required: bool
    external_provider_timeout_contract_required: bool

    @classmethod
    def from_policy(cls, policy: Mapping[str, Any]) -> "AIRuntimeLimits":
        runtime = policy.get("runtime") or {}
        limits = cls(
            default_timeout_ms=int(runtime.get("default_timeout_ms", 15000)),
            max_timeout_ms=int(runtime.get("max_timeout_ms", 60000)),
            max_provider_units_per_request=int(runtime.get("max_provider_units_per_request", 12000)),
            circuit_failure_threshold=int(runtime.get("circuit_failure_threshold", 3)),
            circuit_recovery_seconds=int(runtime.get("circuit_recovery_seconds", 60)),
            max_fallback_providers=int(runtime.get("max_fallback_providers", 3)),
            external_provider_usage_required=bool(runtime.get("external_provider_usage_required", True)),
            external_provider_timeout_contract_required=bool(
                runtime.get("external_provider_timeout_contract_required", True)
            ),
        )
        numeric = (
            limits.default_timeout_ms,
            limits.max_timeout_ms,
            limits.max_provider_units_per_request,
            limits.circuit_failure_threshold,
            limits.circuit_recovery_seconds,
        )
        if any(value <= 0 for value in numeric) or limits.max_fallback_providers < 0:
            raise AIGatewayError("La política runtime M40.0 contiene límites inválidos.", code="AI_RUNTIME_POLICY_INVALID")
        if limits.default_timeout_ms > limits.max_timeout_ms:
            raise AIGatewayError("El timeout por defecto supera el máximo permitido.", code="AI_RUNTIME_POLICY_INVALID")
        return limits


@dataclass
class _CircuitState:
    consecutive_failures: int = 0
    opened_at: float | None = None


class AICircuitBreaker:
    def __init__(self, limits: AIRuntimeLimits, *, monotonic: Callable[[], float] = time.monotonic):
        self.limits = limits
        self.monotonic = monotonic
        self._states: dict[str, _CircuitState] = {}

    def _state(self, provider_id: str) -> _CircuitState:
        return self._states.setdefault(provider_id, _CircuitState())

    def allow(self, provider_id: str) -> bool:
        state = self._state(provider_id)
        if state.opened_at is None:
            return True
        if self.monotonic() - state.opened_at >= self.limits.circuit_recovery_seconds:
            state.consecutive_failures = 0
            state.opened_at = None
            return True
        return False

    def record_success(self, provider_id: str) -> None:
        state = self._state(provider_id)
        state.consecutive_failures = 0
        state.opened_at = None

    def record_failure(self, provider_id: str) -> None:
        state = self._state(provider_id)
        state.consecutive_failures += 1
        if state.consecutive_failures >= self.limits.circuit_failure_threshold:
            state.opened_at = self.monotonic()

    def snapshot(self, provider_id: str) -> dict[str, Any]:
        state = self._state(provider_id)
        return {
            "consecutive_failures": state.consecutive_failures,
            "open": state.opened_at is not None and not self.allow(provider_id),
        }


class AIAuditLedger:
    """Append-only SQLite ledger containing only minimized execution metadata."""

    def __init__(self, database_path: str = ":memory:"):
        self.database_path = database_path
        self._connection = sqlite3.connect(database_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_audit_ledger (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def append(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        payload_json = _canonical_json(normalized)
        previous = self._connection.execute(
            "SELECT entry_hash FROM ai_audit_ledger ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = str(previous["entry_hash"]) if previous else "GENESIS"
        entry_hash = sha256(f"{previous_hash}:{payload_json}".encode("utf-8")).hexdigest()
        cursor = self._connection.execute(
            "INSERT INTO ai_audit_ledger(previous_hash, entry_hash, payload_json) VALUES (?, ?, ?)",
            (previous_hash, entry_hash, payload_json),
        )
        self._connection.commit()
        return {
            "sequence": int(cursor.lastrowid),
            "previous_hash": previous_hash,
            "entry_hash": entry_hash,
        }

    def entries(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT sequence, created_at, previous_hash, entry_hash, payload_json FROM ai_audit_ledger ORDER BY sequence"
        ).fetchall()
        return [
            {
                "sequence": int(row["sequence"]),
                "created_at": row["created_at"],
                "previous_hash": row["previous_hash"],
                "entry_hash": row["entry_hash"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def verify_chain(self) -> bool:
        previous_hash = "GENESIS"
        for entry in self.entries():
            if entry["previous_hash"] != previous_hash:
                return False
            payload_json = _canonical_json(entry["payload"])
            expected = sha256(f"{previous_hash}:{payload_json}".encode("utf-8")).hexdigest()
            if entry["entry_hash"] != expected:
                return False
            previous_hash = entry["entry_hash"]
        return True

    def close(self) -> None:
        self._connection.close()


class GovernedAIExecutor:
    """Bounded execution layer for provider chains behind the M40.0 gateway."""

    def __init__(
        self,
        *,
        gateway: AIGateway | None = None,
        ledger: AIAuditLedger | None = None,
        policy: Mapping[str, Any] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.gateway = gateway or AIGateway()
        self.policy = dict(policy or self.gateway.policy_engine.policy or load_ai_gateway_policy())
        self.limits = AIRuntimeLimits.from_policy(self.policy)
        self.ledger = ledger or AIAuditLedger()
        self.monotonic = monotonic
        self.circuit = AICircuitBreaker(self.limits, monotonic=monotonic)

    def _timeout_ms(self, requested: int | None) -> int:
        timeout_ms = self.limits.default_timeout_ms if requested is None else int(requested)
        if timeout_ms <= 0 or timeout_ms > self.limits.max_timeout_ms:
            raise AIGatewayError("El timeout solicitado está fuera de la política M40.0.", code="AI_TIMEOUT_POLICY_DENIED")
        return timeout_ms

    def _provider_descriptors(self, providers: Sequence[AIProvider]) -> list[AIProviderDescriptor]:
        descriptors = [self.gateway._descriptor(provider) for provider in providers]
        ids = [descriptor.provider_id for descriptor in descriptors]
        if len(ids) != len(set(ids)):
            raise AIGatewayError("La cadena de proveedores contiene identificadores duplicados.", code="AI_PROVIDER_CHAIN_INVALID")
        return descriptors

    def _extract_usage(self, raw: Mapping[str, Any], descriptor: AIProviderDescriptor) -> tuple[dict[str, Any], int]:
        clean = dict(raw)
        usage = clean.pop(_RUNTIME_USAGE_KEY, None)
        if usage is None:
            if descriptor.external and self.limits.external_provider_usage_required:
                raise AIGatewayError(
                    "El proveedor externo no reportó consumo verificable.",
                    code="AI_USAGE_REQUIRED",
                )
            return clean, 0
        if not isinstance(usage, Mapping):
            raise AIGatewayError("El reporte de consumo del proveedor no es válido.", code="AI_USAGE_INVALID")
        units = usage.get("units")
        if isinstance(units, bool) or not isinstance(units, int) or units < 0:
            raise AIGatewayError("Las unidades de consumo del proveedor no son válidas.", code="AI_USAGE_INVALID")
        return clean, units

    def _invoke(
        self,
        provider: AIProvider,
        descriptor: AIProviderDescriptor,
        context: Mapping[str, Any],
        timeout_ms: int,
    ) -> tuple[dict[str, Any], int, int]:
        started = self.monotonic()
        if descriptor.external:
            invoke_with_timeout = getattr(provider, "invoke_with_timeout", None)
            if self.limits.external_provider_timeout_contract_required and not callable(invoke_with_timeout):
                raise AIGatewayError(
                    "El proveedor externo no implementa un contrato explícito de timeout.",
                    code="AI_PROVIDER_TIMEOUT_CONTRACT_REQUIRED",
                )
            raw = invoke_with_timeout(context, timeout_ms) if callable(invoke_with_timeout) else provider.invoke(context)
        else:
            raw = provider.invoke(context)
        elapsed_ms = max(0, int(round((self.monotonic() - started) * 1000)))
        if elapsed_ms > timeout_ms:
            raise AIGatewayError("El proveedor excedió el timeout permitido.", code="AI_PROVIDER_TIMEOUT")
        if not isinstance(raw, Mapping):
            raise AIGatewayError("El proveedor devolvió una salida no estructurada.", code="AI_OUTPUT_INVALID")
        clean, usage_units = self._extract_usage(raw, descriptor)
        return clean, usage_units, elapsed_ms

    @staticmethod
    def _attempt(provider_id: str, *, status: str, error_code: str | None = None, elapsed_ms: int = 0, units: int = 0) -> dict[str, Any]:
        return {
            "provider_id": provider_id,
            "status": status,
            "error_code": error_code,
            "elapsed_ms": elapsed_ms,
            "units": units,
        }

    def _ledger_payload(
        self,
        *,
        request: AIRequest,
        context: Mapping[str, Any],
        outcome: str,
        attempts: Sequence[Mapping[str, Any]],
        total_units: int,
        timeout_ms: int,
        selected_provider_id: str | None = None,
        audit: Mapping[str, Any] | None = None,
        terminal_error_code: str | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": AI_GATEWAY_SCHEMA_VERSION,
            "event_type": "AI_GATEWAY_EXECUTION",
            "outcome": outcome,
            "request_id": request.request_id,
            "policy_version": self.policy.get("policy_version"),
            "capability": request.capability,
            "access_scope": request.access.scope,
            "actor_id": request.access.actor_id or None,
            "organization_id": request.access.organization_id or None,
            "case_id": request.case_id or None,
            "document_id": request.document_id or None,
            "context_hash": _hash(context),
            "selected_provider_id": selected_provider_id,
            "attempts": [dict(item) for item in attempts],
            "total_units": total_units,
            "timeout_ms": timeout_ms,
            "audit_id": (audit or {}).get("audit_id"),
            "input_hash": (audit or {}).get("input_hash"),
            "output_hash": (audit or {}).get("output_hash"),
            "terminal_error_code": terminal_error_code,
        }

    def execute(
        self,
        request: AIRequest,
        primary: AIProvider,
        *,
        fallbacks: Sequence[AIProvider] = (),
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        # Policy, tenancy and payload allowlisting happen before provider selection,
        # so fallback can never be used to bypass an access denial.
        context = self.gateway.context_builder.build(request)
        timeout = self._timeout_ms(timeout_ms)
        if len(fallbacks) > self.limits.max_fallback_providers:
            raise AIGatewayError("La cadena excede el máximo de fallbacks permitido.", code="AI_PROVIDER_CHAIN_INVALID")
        providers = [primary, *fallbacks]
        descriptors = self._provider_descriptors(providers)

        attempts: list[dict[str, Any]] = []
        total_units = 0
        terminal_error: AIGatewayError | None = None

        for provider, descriptor in zip(providers, descriptors):
            if not self.circuit.allow(descriptor.provider_id):
                attempts.append(self._attempt(descriptor.provider_id, status="SKIPPED", error_code="AI_CIRCUIT_OPEN"))
                continue

            elapsed_ms = 0
            usage_units = 0
            try:
                raw, usage_units, elapsed_ms = self._invoke(provider, descriptor, context, timeout)
                total_units += usage_units
                if total_units > self.limits.max_provider_units_per_request:
                    raise AIGatewayError(
                        "La cadena de proveedores excedió el presupuesto máximo de la solicitud.",
                        code="AI_BUDGET_EXCEEDED",
                    )
                result = self.gateway.output_validator.validate(raw, request)
                audit = self.gateway.audit_builder.build(
                    request=request,
                    context=context,
                    result=result,
                    provider=descriptor,
                )
                self.circuit.record_success(descriptor.provider_id)
                attempts.append(
                    self._attempt(
                        descriptor.provider_id,
                        status="SUCCESS",
                        elapsed_ms=elapsed_ms,
                        units=usage_units,
                    )
                )
                ledger_meta = self.ledger.append(
                    self._ledger_payload(
                        request=request,
                        context=context,
                        outcome="SUCCESS",
                        attempts=attempts,
                        total_units=total_units,
                        timeout_ms=timeout,
                        selected_provider_id=descriptor.provider_id,
                        audit=audit,
                    )
                )
                return {
                    "result": result,
                    "audit": audit,
                    "runtime": {
                        "selected_provider_id": descriptor.provider_id,
                        "fallback_used": descriptor.provider_id != descriptors[0].provider_id,
                        "attempts": attempts,
                        "total_units": total_units,
                        "timeout_ms": timeout,
                        "ledger": ledger_meta,
                    },
                }
            except AIGatewayError as exc:
                self.circuit.record_failure(descriptor.provider_id)
                attempts.append(
                    self._attempt(
                        descriptor.provider_id,
                        status="FAILED",
                        error_code=exc.code,
                        elapsed_ms=elapsed_ms,
                        units=usage_units,
                    )
                )
                if exc.code in _TERMINAL_RUNTIME_CODES:
                    terminal_error = exc
                    break
            except Exception as exc:  # provider exceptions are normalized; raw messages are never audited.
                self.circuit.record_failure(descriptor.provider_id)
                attempts.append(
                    self._attempt(
                        descriptor.provider_id,
                        status="FAILED",
                        error_code="AI_PROVIDER_FAILURE",
                        elapsed_ms=elapsed_ms,
                        units=usage_units,
                    )
                )

        error = terminal_error or AIGatewayError(
            "No fue posible obtener una salida válida de la cadena de proveedores.",
            code="AI_PROVIDER_CHAIN_EXHAUSTED",
        )
        self.ledger.append(
            self._ledger_payload(
                request=request,
                context=context,
                outcome="FAILURE",
                attempts=attempts,
                total_units=total_units,
                timeout_ms=timeout,
                terminal_error_code=error.code,
            )
        )
        raise error


__all__ = [
    "AIAuditLedger",
    "AICircuitBreaker",
    "AIRuntimeLimits",
    "GovernedAIExecutor",
]
