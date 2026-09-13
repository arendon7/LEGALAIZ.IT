#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE = "http://127.0.0.1:8765"
ORIGIN = BASE


def post(path: str, payload: dict) -> dict:
    request = Request(
        BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Origin": ORIGIN,
            "User-Agent": "LegalAIZ-M34.4-CI-Smoke",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8") or "{}")
            if response.status >= 400:
                raise RuntimeError(f"{path}: HTTP {response.status}: {data}")
            return data
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path}: HTTP {exc.code}: {body}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def answer_for(question: dict):
    answer_type = question.get("answer_type")
    options = question.get("options") or []
    if answer_type == "select":
        preferred = [
            item for item in options
            if str(item.get("value")).lower() not in {"no_se", "uncertain"}
        ]
        require(bool(preferred), f"No hay opción sustantiva para {question.get('question_id')}")
        return preferred[0]["value"]
    if answer_type == "multiselect":
        require(bool(options), f"No hay opciones para {question.get('question_id')}")
        return [options[0]["value"]]
    if answer_type == "date":
        return "2026-08-01"
    if answer_type == "money_cop":
        return "1800000"
    if answer_type == "number":
        return 1
    if answer_type in {"text", "textarea"}:
        return "Descripción suficiente para evaluar la solución"
    if answer_type == "boolean":
        return True
    raise AssertionError(f"Tipo de respuesta no soportado: {answer_type}")


def prepare_ready_consumer_case() -> tuple[str, int]:
    narrative = (
        "Compré un producto defectuoso y quiero reclamar la garantía. "
        "Pagué con tarjeta de crédito y necesito revisar qué puedo solicitar."
    )
    started = post("/api/m34/intake/start", {"problem_statement": narrative})
    code = started.get("recovery_code")
    require(bool(code), "M34.4 start no devolvió recovery code")

    analyzed = post("/api/m34/intake/analyze", {"recovery_code": code})
    facts = analyzed.get("facts") or []
    require(bool(facts), "El relato smoke debería producir hechos candidatos")
    post(
        "/api/m34/intake/facts/decide",
        {
            "recovery_code": code,
            "decisions": [
                {"fact_id": fact["fact_id"], "action": "CONFIRM"}
                for fact in facts
            ],
        },
    )

    asked = 0
    for _ in range(16):
        step = post("/api/m34/intake/next-step", {"recovery_code": code})
        action = step.get("action")
        if action == "READY_FOR_RECOMMENDATION":
            require(
                "CO-CD-003" in ((step.get("sufficiency") or {}).get("ready_product_codes") or []),
                "El caso smoke no quedó listo para protección al consumidor",
            )
            return code, asked
        require(
            action in {"ASK_QUESTION", "ROUTE_TOPIC", "CONFIRM_RISK"},
            f"Acción inesperada antes de recomendación: {action}",
        )
        question = step.get("question") or {}
        value = "dismiss" if action == "CONFIRM_RISK" else answer_for(question)
        post(
            "/api/m34/intake/answer",
            {
                "recovery_code": code,
                "question_id": question.get("question_id"),
                "value": value,
            },
        )
        if action == "ASK_QUESTION":
            asked += 1
    raise AssertionError("El caso smoke no alcanzó READY_FOR_RECOMMENDATION")


def assert_public_boundary(result: dict) -> None:
    serialized = json.dumps(result, ensure_ascii=False).lower()
    for forbidden in (
        "matched_fact_ids",
        "matched_fact_types",
        "input_fingerprint",
        "signal_score",
        "fit_score",
        '"_internal"',
    ):
        require(forbidden not in serialized, f"Metadato interno expuesto: {forbidden}")
    require("decision_id" in result, "La recomendación pública debe conservar decision_id")
    require("decided_at" in result, "La recomendación pública debe conservar decided_at")


def main() -> int:
    code, asked = prepare_ready_consumer_case()
    first = post("/api/m34/intake/recommendation", {"recovery_code": code})
    require(first.get("outcome") == "RECOMMEND", f"Outcome inesperado: {first.get('outcome')}")
    primary = first.get("primary") or {}
    require(primary.get("product_code") == "CO-CD-003", f"Producto inesperado: {primary.get('product_code')}")
    require(primary.get("eligibility") in {"PASS", "CONDITIONAL"}, "Elegibilidad pública inválida")
    require(bool(primary.get("why_this_solution")), "Falta explicación de encaje")
    require(bool(primary.get("includes")), "Falta alcance incluido")
    require(bool(primary.get("not_included")), "Falta alcance excluido")
    require(len(first.get("alternatives") or []) <= 2, "M34.4 devolvió más de dos alternativas")
    require(first.get("idempotent") is False, "La primera decisión no puede presentarse como reutilizada")
    assert_public_boundary(first)

    second = post("/api/m34/intake/recommendation", {"recovery_code": code})
    require(second.get("decision_id") == first.get("decision_id"), "La misma entrada creó otra decisión")
    require(second.get("idempotent") is True, "La segunda decisión debería ser idempotente")
    assert_public_boundary(second)

    recovered = post("/api/m34/intake/recover", {"recovery_code": code})
    require(recovered.get("stage") == "RECOMMENDED", "La etapa RECOMMENDED no persistió")

    print(
        "M34.4 HTTP smoke PASS · "
        f"adaptive_questions={asked} primary={primary.get('product_code')} "
        f"decision={first.get('decision_id')} idempotent={second.get('idempotent')}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M34.4 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
