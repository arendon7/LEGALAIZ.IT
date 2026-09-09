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
            "User-Agent": "LegalAIZ-M34.3-CI-Smoke",
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
        preferred = [item for item in options if str(item.get("value")).lower() not in {"no_se", "uncertain"}]
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
        return "Descripción suficiente para el triage"
    if answer_type == "boolean":
        return True
    raise AssertionError(f"Tipo de respuesta no soportado por smoke: {answer_type}")


def main() -> int:
    narrative = (
        "Compré un producto defectuoso y quiero reclamar la garantía. "
        "Pagué con tarjeta de crédito y necesito revisar qué puedo solicitar."
    )
    started = post("/api/m34/intake/start", {"problem_statement": narrative})
    code = started.get("recovery_code")
    require(bool(code), "M34.3 start no devolvió recovery code")

    analyzed = post("/api/m34/intake/analyze", {"recovery_code": code})
    facts = analyzed.get("facts") or []
    require(facts, "El relato de consumo debería producir hechos candidatos")
    require(all(fact.get("confirmation_status") == "UNCONFIRMED" for fact in facts), "M34.2 promovió hechos antes de M34.3")

    reviewed = post(
        "/api/m34/intake/facts/decide",
        {
            "recovery_code": code,
            "decisions": [{"fact_id": fact["fact_id"], "action": "CONFIRM"} for fact in facts],
        },
    )
    require(reviewed.get("stage") == "FACTS_REVIEWED", "El smoke no llegó a FACTS_REVIEWED")

    asked = 0
    for _ in range(16):
        step = post("/api/m34/intake/next-step", {"recovery_code": code})
        action = step.get("action")
        require("recommendation" not in step and "recommended_product" not in step, "M34.3 emitió recomendación antes de M34.4")
        if action == "READY_FOR_RECOMMENDATION":
            ready = step.get("sufficiency") or {}
            require(ready.get("ready") is True, "READY sin suficiencia positiva")
            require("CO-CD-003" in (ready.get("ready_product_codes") or []), "El caso de consumo no quedó listo para el producto esperado")
            require(asked >= 1, "El smoke debería haber necesitado al menos una pregunta adaptativa")
            recovered = post("/api/m34/intake/recover", {"recovery_code": code})
            user_facts = [fact for fact in recovered.get("facts") or [] if fact.get("provenance") == "USER_ASSERTED"]
            require(len(user_facts) == asked, "Las respuestas M34.3 no persistieron como USER_ASSERTED")
            require(all(str(fact.get("source_reference") or "").startswith("m34-question:") for fact in user_facts), "Hecho M34.3 sin procedencia de pregunta")
            print(f"M34.3 HTTP smoke PASS · adaptive_questions={asked} ready={','.join(ready.get('ready_product_codes') or [])}")
            return 0
        require(action in {"ASK_QUESTION", "ROUTE_TOPIC", "CONFIRM_RISK"}, f"Acción inesperada antes de suficiencia: {action}")
        question = step.get("question") or {}
        require(bool(question.get("question_id")), f"{action} no devolvió question_id")
        value = answer_for(question)
        if action == "CONFIRM_RISK":
            value = "dismiss"
        post(
            "/api/m34/intake/answer",
            {"recovery_code": code, "question_id": question["question_id"], "value": value},
        )
        if action == "ASK_QUESTION":
            asked += 1

    raise AssertionError("M34.3 no alcanzó READY_FOR_RECOMMENDATION dentro del límite de preguntas")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M34.3 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
