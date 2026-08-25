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
            "User-Agent": "LegalAIZ-M34.2-CI-Smoke",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw or "{}")
            if response.status >= 400:
                raise RuntimeError(f"{path}: HTTP {response.status}: {data}")
            return data
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path}: HTTP {exc.code}: {body}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    narrative = (
        "Compré un producto defectuoso y quiero reclamar la garantía. "
        "Pagué con tarjeta de crédito y necesito revisar qué puedo solicitar."
    )
    started = post("/api/m34/intake/start", {"problem_statement": narrative})
    code = started.get("recovery_code")
    require(bool(code), "El inicio M34.2 no devolvió código de continuidad")
    require(started.get("stage") == "PROBLEM_SUBMITTED", "Stage inicial inesperado")

    analyzed = post("/api/m34/intake/analyze", {"recovery_code": code})
    facts = analyzed.get("facts") or []
    require(analyzed.get("stage") == "FACTS_PENDING_CONFIRMATION", "La extracción no quedó pendiente de confirmación")
    require(len(facts) >= 2, "La narrativa smoke debería producir al menos dos hechos candidatos")
    require(all(fact.get("provenance") == "AI_INFERRED" for fact in facts), "La extracción promovió procedencia indebidamente")
    require(all(fact.get("confirmation_status") == "UNCONFIRMED" for fact in facts), "La extracción promovió confirmación indebidamente")
    require("recommended_product" not in analyzed and "recommendation" not in analyzed, "M34.2 no debe emitir recomendación")
    require(all(item.get("status") == "TOPIC_SIGNAL_ONLY" for item in analyzed.get("candidate_products") or []), "Producto candidato presentado como algo distinto de señal temática")

    decisions = [
        {"fact_id": fact["fact_id"], "action": "CONFIRM"}
        for fact in facts
    ]
    reviewed = post(
        "/api/m34/intake/facts/decide",
        {"recovery_code": code, "decisions": decisions},
    )
    require(reviewed.get("stage") == "FACTS_REVIEWED", "La revisión completa no cerró el stage")
    require(reviewed.get("pending_fact_count") == 0, "Quedaron hechos candidatos sin revisar")
    confirmed = reviewed.get("confirmed_facts") or []
    require(len(confirmed) == len(facts), "No se crearon todos los hechos humanos confirmados")
    require(all(fact.get("provenance") == "USER_CONFIRMED" for fact in confirmed), "Hecho confirmado sin procedencia humana separada")
    require(all(str(fact.get("source_reference") or "").startswith("fact_ai_") for fact in confirmed), "Hecho humano sin enlace al candidato de origen")

    recovered = post("/api/m34/intake/recover", {"recovery_code": code})
    require(recovered.get("stage") == "FACTS_REVIEWED", "La revisión no persistió tras recuperar")
    require(recovered.get("problem_statement") == narrative, "El relato cambió durante la extracción")

    print(
        "M34.2 HTTP smoke PASS · "
        f"facts={len(facts)} confirmed={len(confirmed)} "
        f"provider={analyzed.get('extraction_provider', {}).get('mode')}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M34.2 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
