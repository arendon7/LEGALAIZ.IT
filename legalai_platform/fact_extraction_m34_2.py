from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import unicodedata
import uuid
from typing import Any, Mapping, Protocol

from legalai_platform.m34_intelligent_journey import (
    RiskCode,
    load_product_contracts,
    validate_legal_fact,
)


EXTRACTION_SCHEMA_VERSION = "34.2.0"
MAX_EXTRACTED_FACTS = 32
MAX_CANDIDATE_PRODUCTS = 3
MAX_RISK_SIGNALS = 8
MAX_CONTRADICTIONS = 8
MAX_FACT_VALUE_JSON_CHARS = 4000
MAX_PROVIDER_ID_CHARS = 120
MAX_PROVIDER_MODE_CHARS = 80
MAX_SOURCE_REFERENCE_CHARS = 256


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _parse_date(value: str) -> str | None:
    raw = str(value or "").strip()
    for pattern, order in (
        (r"^(\d{4})-(\d{2})-(\d{2})$", (1, 2, 3)),
        (r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", (3, 2, 1)),
    ):
        match = re.match(pattern, raw)
        if not match:
            continue
        try:
            year = int(match.group(order[0]))
            month = int(match.group(order[1]))
            day = int(match.group(order[2]))
            return datetime(year, month, day, tzinfo=timezone.utc).date().isoformat()
        except ValueError:
            return None
    return None


def _parse_cop_amount(value: str) -> int | None:
    compact = re.sub(r"[^0-9]", "", str(value or ""))
    if not compact:
        return None
    try:
        amount = int(compact)
    except ValueError:
        return None
    if amount <= 0 or amount > 10**15:
        return None
    return amount


def _bounded_json_value(value: Any, label: str) -> Any:
    try:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"El proveedor devolvió un valor no serializable para {label}") from exc
    if len(serialized) > MAX_FACT_VALUE_JSON_CHARS:
        raise ValueError(f"El valor estructurado excede el límite permitido para {label}")
    return value


class FactExtractionProvider(Protocol):
    provider_id: str
    provider_mode: str
    ai_enabled: bool

    def extract(
        self,
        problem_statement: str,
        allowed_fact_types: set[str],
    ) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    provider_mode: str
    ai_enabled: bool


class ConservativeNarrativeProvider:
    """Conservative local parser used for demo, QA and fail-safe operation.

    This provider is deliberately *not* presented as an LLM. It only proposes
    structured candidates when the narrative contains explicit lexical or
    syntactic signals. Every proposed fact remains AI_INFERRED/UNCONFIRMED at
    the Legal Fact Model boundary because a machine performed the structuring.

    A future external model provider can implement the same provider contract
    without changing storage, confirmation, audit or recommendation gates.
    """

    provider_id = "m34.local.conservative.v1"
    provider_mode = "LOCAL_CONSERVATIVE"
    ai_enabled = False

    PRODUCT_SIGNALS: dict[str, tuple[str, ...]] = {
        "CO-LA-001": (
            "liquidacion",
            "me despidieron",
            "despido",
            "terminaron mi contrato",
            "cesantias",
            "prima",
            "vacaciones",
            "salario pendiente",
            "no me pagaron",
        ),
        "CO-LA-002": (
            "contrato de trabajo",
            "contratar empleado",
            "contratar trabajador",
            "nomina",
            "relacion laboral",
        ),
        "CO-EM-003": (
            "prestacion de servicios",
            "contratista",
            "honorarios",
            "servicios profesionales",
            "entregables",
        ),
        "CO-EM-004": (
            "confidencialidad",
            "nda",
            "secreto empresarial",
            "propiedad intelectual",
            "codigo fuente",
            "software",
        ),
        "CO-AR-001": (
            "arrendamiento",
            "arriendo",
            "arrendador",
            "arrendatario",
            "canon",
            "vivienda",
            "apartamento",
        ),
        "CO-SA-001": (
            "eps",
            "ips",
            "medicamento",
            "autorizacion",
            "tratamiento",
            "procedimiento de salud",
            "cita medica",
        ),
        "CO-CD-001": (
            "datacredito",
            "transunion",
            "central de riesgo",
            "reporte crediticio",
            "habeas data",
        ),
        "CO-CD-003": (
            "garantia",
            "retracto",
            "reversion",
            "producto defectuoso",
            "devolucion",
            "compra",
        ),
        "CO-CD-004": (
            "acuerdo de pago",
            "pagare",
            "cobro",
            "deuda",
            "cuotas",
            "acreedor",
            "deudor",
        ),
        "CO-TR-001": (
            "sast",
            "sistema automatico",
            "sistema semiautomatico",
            "camara de fotodeteccion",
        ),
        "CO-TR-002": (
            "fotomulta",
            "comparendo",
            "no me notificaron",
            "sin notificacion",
            "multa de transito",
        ),
    }

    RISK_SIGNALS: dict[str, tuple[str, ...]] = {
        "LITIGATION_ACTIVE": (
            "proceso judicial",
            "juzgado",
            "demanda en curso",
            "audiencia judicial",
        ),
        "CRIMINAL_MATTER": (
            "fiscalia",
            "proceso penal",
            "imputacion",
            "captura",
            "delito",
        ),
        "DEADLINE_RISK": (
            "vence hoy",
            "vence manana",
            "plazo vence",
            "termino vence",
            "audiencia manana",
        ),
        "MINOR_OR_VULNERABLE_PERSON": (
            "menor de edad",
            "nino",
            "nina",
            "adolescente",
        ),
        "PERSONAL_DATA_SENSITIVE": (
            "historia clinica",
            "dato biometrico",
            "datos biometricos",
            "datos de salud",
        ),
    }

    DATE_TOKEN = r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})"

    def _candidate_products(self, folded: str) -> list[dict[str, Any]]:
        ranked: list[tuple[int, str, list[str]]] = []
        for code, signals in self.PRODUCT_SIGNALS.items():
            matched = [signal for signal in signals if signal in folded]
            if matched:
                ranked.append((len(matched), code, matched[:4]))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        results: list[dict[str, Any]] = []
        for count, code, matched in ranked[:MAX_CANDIDATE_PRODUCTS]:
            results.append(
                {
                    "product_code": code,
                    "signal_score": round(min(0.95, 0.45 + 0.1 * count), 2),
                    "reason_codes": [
                        re.sub(r"[^a-z0-9]+", "_", item).strip("_")
                        for item in matched
                    ],
                    "status": "TOPIC_SIGNAL_ONLY",
                }
            )
        return results

    @staticmethod
    def _goal(folded: str) -> str | None:
        if any(term in folded for term in ("reclamar", "queja", "peticion", "solicitar", "corregir")):
            return "reclamar_o_solicitar"
        if any(term in folded for term in ("crear contrato", "hacer contrato", "formalizar", "redactar contrato")):
            return "crear_o_formalizar"
        if any(term in folded for term in ("revisar", "verificar", "saber si", "entender que")):
            return "revisar_o_verificar"
        return None

    @staticmethod
    def _explicit_date(text: str, folded: str, leading_terms: tuple[str, ...]) -> str | None:
        for term in leading_terms:
            index = folded.find(term)
            if index < 0:
                continue
            segment = text[index:index + 100]
            match = re.search(ConservativeNarrativeProvider.DATE_TOKEN, segment)
            if match:
                parsed = _parse_date(match.group(1))
                if parsed:
                    return parsed
        return None

    def extract(self, problem_statement: str, allowed_fact_types: set[str]) -> Mapping[str, Any]:
        text = str(problem_statement or "")
        folded = _fold(text)
        facts: list[dict[str, Any]] = []

        def add(
            fact_type: str,
            value: Any,
            *,
            normalized_value: Any = None,
            confidence: float = 0.64,
            criticality: str = "MEDIUM",
            legal_relevance: str = "MEDIUM",
        ) -> None:
            if fact_type not in allowed_fact_types or value is None:
                return
            facts.append(
                {
                    "fact_type": fact_type,
                    "value": value,
                    "normalized_value": normalized_value if normalized_value is not None else value,
                    "confidence": confidence,
                    "criticality": criticality,
                    "legal_relevance": legal_relevance,
                }
            )

        goal = self._goal(folded)
        if goal:
            add("goal.requested_outcome", goal, confidence=0.58, criticality="MEDIUM")

        if any(signal in folded for signal in self.PRODUCT_SIGNALS["CO-LA-001"] + self.PRODUCT_SIGNALS["CO-LA-002"]):
            start_date = self._explicit_date(
                text,
                folded,
                ("empece", "inicie", "comence", "inicio el", "inicio mi"),
            )
            if start_date:
                add(
                    "employment.start_date",
                    start_date,
                    confidence=0.78,
                    criticality="HIGH",
                    legal_relevance="HIGH",
                )
            end_date = self._explicit_date(
                text,
                folded,
                ("me despidieron", "terminaron", "termino el", "finalizo", "terminacion"),
            )
            if end_date:
                add(
                    "employment.end_date",
                    end_date,
                    confidence=0.78,
                    criticality="HIGH",
                    legal_relevance="HIGH",
                )

            pending_map = {
                "liquidacion": "liquidacion",
                "cesantias": "cesantias",
                "prima": "prima",
                "vacaciones": "vacaciones",
                "indemnizacion": "indemnizacion",
                "salario pendiente": "salario",
            }
            pending = sorted({label for signal, label in pending_map.items() if signal in folded})
            if pending:
                add(
                    "employment.pending_concepts",
                    pending,
                    confidence=0.72,
                    criticality="HIGH",
                    legal_relevance="HIGH",
                )

            compensation_match = re.search(
                r"(?:salario|sueldo|ganaba|me pagaban)\s*(?:mensualmente\s*)?(?:de|era|por|:)?\s*\$?\s*([0-9][0-9.,]{2,})",
                folded,
            )
            if compensation_match:
                amount = _parse_cop_amount(compensation_match.group(1))
                if amount:
                    add(
                        "employment.compensation_basis",
                        {"amount_cop": amount, "frequency": "UNCONFIRMED"},
                        normalized_value={"amount_cop": amount, "currency": "COP"},
                        confidence=0.7,
                        criticality="HIGH",
                        legal_relevance="HIGH",
                    )

        if "no me notificaron" in folded or "sin notificacion" in folded or "nunca me notificaron" in folded:
            add(
                "traffic.notification_status",
                "NOT_NOTIFIED",
                confidence=0.9,
                criticality="HIGH",
                legal_relevance="CRITICAL",
            )
        elif "me notificaron" in folded and any(term in folded for term in ("fotomulta", "comparendo", "transito")):
            add(
                "traffic.notification_status",
                "NOTIFIED",
                confidence=0.72,
                criticality="HIGH",
                legal_relevance="HIGH",
            )

        consumer_issue = None
        for signal, value in (
            ("garantia", "GARANTIA"),
            ("retracto", "RETRACTO"),
            ("reversion", "REVERSION_PAGO"),
            ("producto defectuoso", "PRODUCTO_DEFECTUOSO"),
        ):
            if signal in folded:
                consumer_issue = value
                break
        if consumer_issue:
            add(
                "consumer.issue_type",
                consumer_issue,
                confidence=0.8,
                criticality="HIGH",
                legal_relevance="HIGH",
            )

        payment_method = None
        for signal, value in (
            ("tarjeta de credito", "TARJETA_CREDITO"),
            ("tarjeta de debito", "TARJETA_DEBITO"),
            ("pse", "PSE"),
            ("transferencia", "TRANSFERENCIA"),
            ("efectivo", "EFECTIVO"),
        ):
            if signal in folded:
                payment_method = value
                break
        if payment_method:
            add("payment.method", payment_method, confidence=0.82, criticality="MEDIUM")

        if any(term in folded for term in ("arrendamiento", "arriendo", "arrendatario", "arrendador")):
            if any(term in folded for term in ("vivienda", "residencial", "apartamento", "casa")):
                add(
                    "lease.property_use",
                    "VIVIENDA_URBANA",
                    confidence=0.68,
                    criticality="HIGH",
                    legal_relevance="HIGH",
                )
            rent_match = re.search(
                r"(?:canon(?:\s+de\s+(?:arriendo|arrendamiento))?|arriendo|renta)\s*(?:mensual(?:mente)?\s*)?(?:de|es|:)?\s*\$?\s*([0-9][0-9.,]{2,})",
                folded,
            )
            if rent_match:
                amount = _parse_cop_amount(rent_match.group(1))
                if amount:
                    add(
                        "lease.rent",
                        {"amount_cop": amount, "frequency": "MONTHLY_UNCONFIRMED"},
                        normalized_value={"amount_cop": amount, "currency": "COP"},
                        confidence=0.68,
                        criticality="HIGH",
                        legal_relevance="HIGH",
                    )

        if any(term in folded for term in ("datacredito", "transunion", "central de riesgo", "reporte crediticio")):
            if any(term in folded for term in ("ya reclame", "reclame previamente", "presente reclamo", "hice reclamo")):
                add(
                    "credit_data.prior_claim_status",
                    "PRIOR_CLAIM_ASSERTED",
                    confidence=0.7,
                    criticality="HIGH",
                    legal_relevance="HIGH",
                )

        risk_signals: list[dict[str, Any]] = []
        for code, signals in self.RISK_SIGNALS.items():
            matched = [signal for signal in signals if signal in folded]
            if matched:
                risk_signals.append(
                    {
                        "code": code,
                        "basis": "EXPLICIT_TEXT_SIGNAL",
                        "signal_count": len(matched),
                        "confidence": round(min(0.9, 0.55 + 0.08 * len(matched)), 2),
                    }
                )

        return {
            "facts": facts[:MAX_EXTRACTED_FACTS],
            "candidate_products": self._candidate_products(folded),
            "risk_signals": risk_signals[:MAX_RISK_SIGNALS],
            "contradictions": [],
        }


class FactExtractionService:
    """Strict boundary between an extraction provider and the Legal Fact Model."""

    def __init__(self, provider: FactExtractionProvider | None = None):
        self.provider = provider or ConservativeNarrativeProvider()
        self.contracts = load_product_contracts()
        self.allowed_fact_types = {
            str(fact_type)
            for contract in self.contracts.values()
            for fact_type in contract.get("minimum_recommendation_facts", [])
        }

    @property
    def descriptor(self) -> ProviderDescriptor:
        descriptor = ProviderDescriptor(
            provider_id=str(self.provider.provider_id),
            provider_mode=str(self.provider.provider_mode),
            ai_enabled=bool(self.provider.ai_enabled),
        )
        if not re.fullmatch(r"[A-Za-z0-9._:-]{3,120}", descriptor.provider_id):
            raise ValueError("El identificador del proveedor de extracción no es válido.")
        if not re.fullmatch(r"[A-Z0-9_:-]{3,80}", descriptor.provider_mode):
            raise ValueError("El modo del proveedor de extracción no es válido.")
        return descriptor

    def _fact_from_candidate(self, candidate: Mapping[str, Any], source_reference: str) -> dict[str, Any]:
        if not isinstance(candidate, Mapping):
            raise ValueError("El extractor produjo un hecho candidato con formato inválido.")
        fact_type = str(candidate.get("fact_type") or "").strip()
        if fact_type not in self.allowed_fact_types:
            raise ValueError(f"El extractor produjo un tipo de hecho no permitido: {fact_type}")
        if "value" not in candidate:
            raise ValueError(f"El extractor omitió el valor para {fact_type}")
        if not source_reference or len(source_reference) > MAX_SOURCE_REFERENCE_CHARS:
            raise ValueError("La referencia de origen de la extracción no es válida.")

        value = _bounded_json_value(candidate.get("value"), fact_type)
        normalized_value = _bounded_json_value(
            candidate.get("normalized_value", value),
            f"{fact_type}.normalized_value",
        )
        confidence = candidate.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError(f"Confianza inválida para {fact_type}")
        confidence = float(confidence)
        if not 0 <= confidence <= 1:
            raise ValueError(f"Confianza fuera de rango para {fact_type}")

        descriptor = self.descriptor
        fact = {
            "fact_id": "fact_ai_" + uuid.uuid4().hex[:16],
            "fact_type": fact_type,
            "value": value,
            "normalized_value": normalized_value,
            "provenance": "AI_INFERRED",
            "confirmation_status": "UNCONFIRMED",
            "criticality": str(candidate.get("criticality") or "MEDIUM"),
            "source_reference": source_reference,
            "evidence_ids": [],
            "extraction_confidence": confidence,
            "legal_relevance": str(candidate.get("legal_relevance") or "MEDIUM"),
            "created_at": utc_iso(),
            "updated_at": utc_iso(),
            "notes": f"Candidato estructurado por {descriptor.provider_id}; requiere confirmación humana.",
        }
        errors = validate_legal_fact(fact)
        if errors:
            raise ValueError(f"Hecho extraído inválido ({fact_type}): {'; '.join(errors)}")
        return fact

    def extract(self, problem_statement: str, source_reference: str) -> dict[str, Any]:
        problem = str(problem_statement or "").strip()
        if not problem:
            raise ValueError("No hay un relato disponible para analizar.")
        if not source_reference or len(source_reference) > MAX_SOURCE_REFERENCE_CHARS:
            raise ValueError("La extracción requiere una referencia de origen válida.")
        descriptor = self.descriptor

        raw = self.provider.extract(problem, set(self.allowed_fact_types))
        if not isinstance(raw, Mapping):
            raise ValueError("El proveedor de extracción devolvió un formato inválido.")

        raw_facts = raw.get("facts") or []
        if not isinstance(raw_facts, list) or len(raw_facts) > MAX_EXTRACTED_FACTS:
            raise ValueError("La cantidad de hechos extraídos no es válida.")
        facts = [self._fact_from_candidate(candidate, source_reference) for candidate in raw_facts]
        if len({fact["fact_type"] for fact in facts}) != len(facts):
            raise ValueError("El extractor produjo hechos duplicados del mismo tipo.")

        raw_products = raw.get("candidate_products") or []
        if not isinstance(raw_products, list) or len(raw_products) > MAX_CANDIDATE_PRODUCTS:
            raise ValueError("La cantidad de productos candidatos no es válida.")
        candidate_products: list[dict[str, Any]] = []
        seen_products: set[str] = set()
        for candidate in raw_products:
            if not isinstance(candidate, Mapping):
                raise ValueError("Producto candidato inválido.")
            code = str(candidate.get("product_code") or "")
            if code not in self.contracts:
                raise ValueError(f"Producto candidato fuera del catálogo M34: {code}")
            if code in seen_products:
                raise ValueError(f"Producto candidato duplicado: {code}")
            seen_products.add(code)
            score = candidate.get("signal_score", 0)
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= float(score) <= 1:
                raise ValueError(f"Señal de producto inválida para {code}")
            reason_codes = candidate.get("reason_codes") or []
            if not isinstance(reason_codes, list) or any(not isinstance(item, str) for item in reason_codes):
                raise ValueError(f"Razones de producto inválidas para {code}")
            safe_reasons: list[str] = []
            for reason in reason_codes[:6]:
                reason = str(reason).strip()
                if not re.fullmatch(r"[a-z0-9_]{1,80}", reason):
                    raise ValueError(f"Código de razón inválido para {code}")
                safe_reasons.append(reason)
            candidate_products.append(
                {
                    "product_code": code,
                    "signal_score": round(float(score), 4),
                    "reason_codes": safe_reasons,
                    "status": "TOPIC_SIGNAL_ONLY",
                }
            )

        allowed_risks = {item.value for item in RiskCode}
        raw_risks = raw.get("risk_signals") or []
        if not isinstance(raw_risks, list) or len(raw_risks) > MAX_RISK_SIGNALS:
            raise ValueError("La cantidad de señales de riesgo no es válida.")
        risk_signals: list[dict[str, Any]] = []
        seen_risks: set[str] = set()
        for risk in raw_risks:
            if not isinstance(risk, Mapping):
                raise ValueError("Señal de riesgo inválida.")
            code = str(risk.get("code") or "")
            if code not in allowed_risks:
                raise ValueError(f"Señal de riesgo no soportada: {code}")
            if code in seen_risks:
                continue
            seen_risks.add(code)
            confidence = risk.get("confidence", 0)
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
                raise ValueError(f"Confianza de riesgo inválida para {code}")
            try:
                signal_count = max(1, int(risk.get("signal_count") or 1))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Conteo de señal de riesgo inválido para {code}") from exc
            risk_signals.append(
                {
                    "code": code,
                    "basis": str(risk.get("basis") or "STRUCTURED_EXTRACTION")[:80],
                    "signal_count": signal_count,
                    "confidence": round(float(confidence), 4),
                    "status": "UNCONFIRMED_SIGNAL",
                }
            )

        contradictions = raw.get("contradictions") or []
        if not isinstance(contradictions, list) or len(contradictions) > MAX_CONTRADICTIONS:
            raise ValueError("La cantidad de contradicciones no es válida.")
        safe_contradictions: list[dict[str, str]] = []
        seen_contradictions: set[str] = set()
        for item in contradictions:
            if not isinstance(item, Mapping):
                raise ValueError("Contradicción inválida.")
            code = str(item.get("code") or "").strip()
            if not code or not re.fullmatch(r"[A-Z0-9_]{3,80}", code):
                raise ValueError("Código de contradicción inválido.")
            if code in seen_contradictions:
                continue
            seen_contradictions.add(code)
            safe_contradictions.append(
                {
                    "code": code,
                    "status": "UNCONFIRMED_SIGNAL",
                }
            )

        return {
            "schema_version": EXTRACTION_SCHEMA_VERSION,
            "provider": {
                "id": descriptor.provider_id,
                "mode": descriptor.provider_mode,
                "ai_enabled": descriptor.ai_enabled,
            },
            "facts": facts,
            "candidate_products": candidate_products,
            "risk_signals": risk_signals,
            "contradictions": safe_contradictions,
            "requires_user_confirmation": bool(facts),
            "next_action": "CONFIRM_FACTS" if facts else "ASK_MORE",
            "notice": (
                "Los datos estructurados son candidatos. No constituyen una conclusión jurídica "
                "ni pueden decidir una recomendación hasta que corresponda confirmarlos."
            ),
        }


__all__ = [
    "ConservativeNarrativeProvider",
    "EXTRACTION_SCHEMA_VERSION",
    "FactExtractionProvider",
    "FactExtractionService",
    "MAX_CANDIDATE_PRODUCTS",
    "MAX_EXTRACTED_FACTS",
    "ProviderDescriptor",
]
