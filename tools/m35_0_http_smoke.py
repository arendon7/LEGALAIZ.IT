#!/usr/bin/env python3
from __future__ import annotations

from http.cookiejar import CookieJar
import json
import sys
import uuid
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener


BASE = "http://127.0.0.1:8765"
ORIGIN = BASE


class Client:
    def __init__(self):
        self.cookies = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))
        self.csrf = ""

    def post(self, path: str, payload: dict, *, expected: int = 200) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Origin": ORIGIN,
            "User-Agent": "LegalAIZ-M35.0-CI-Smoke",
        }
        if self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        request = Request(
            BASE + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with self.opener.open(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
                if response.status != expected:
                    raise AssertionError(f"{path}: HTTP {response.status}, esperado {expected}: {data}")
                return data
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body or "{}")
            except json.JSONDecodeError:
                data = {"raw": body}
            if exc.code != expected:
                raise AssertionError(f"{path}: HTTP {exc.code}, esperado {expected}: {data}") from exc
            return data

    def get(self, path: str, *, expected: int = 200) -> dict:
        request = Request(
            BASE + path,
            method="GET",
            headers={"User-Agent": "LegalAIZ-M35.0-CI-Smoke"},
        )
        try:
            with self.opener.open(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
                if response.status != expected:
                    raise AssertionError(f"{path}: HTTP {response.status}, esperado {expected}: {data}")
                return data
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body or "{}")
            except json.JSONDecodeError:
                data = {"raw": body}
            if exc.code != expected:
                raise AssertionError(f"{path}: HTTP {exc.code}, esperado {expected}: {data}") from exc
            return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def register_client(client: Client, label: str) -> dict:
    suffix = uuid.uuid4().hex[:10]
    registered = client.post(
        "/api/auth/register",
        {
            "name": f"Cliente Smoke {label}",
            "email": f"m35-{label.lower()}-{suffix}@example.test",
            "password": "M35!Demo-Segura_2026#Ax7",
            "consent": True,
        },
        expected=201,
    )
    client.csrf = str(registered.get("csrf_token") or "")
    require(bool(client.csrf), f"Registro {label} no devolvió CSRF")
    require(registered.get("user", {}).get("role") == "client", f"Registro {label} no creó rol client")
    return registered


def answer_for(question: dict):
    answer_type = question.get("answer_type")
    options = question.get("options") or []
    if answer_type == "select":
        choices = [
            item for item in options
            if str(item.get("value")).lower() not in {"no_se", "uncertain"}
        ]
        require(bool(choices), f"Sin opción sustantiva para {question.get('question_id')}")
        return choices[0]["value"]
    if answer_type == "multiselect":
        require(bool(options), f"Sin opciones para {question.get('question_id')}")
        return [options[0]["value"]]
    if answer_type == "date":
        return "2026-08-01"
    if answer_type == "money_cop":
        return "1800000"
    if answer_type == "number":
        return 1
    if answer_type in {"text", "textarea"}:
        return "Descripción suficiente para continuar el fulfillment"
    if answer_type == "boolean":
        return True
    raise AssertionError(f"Tipo no soportado: {answer_type}")


def recommended_consumer_intake(client: Client) -> tuple[str, str]:
    narrative = (
        "Compré un producto defectuoso y quiero reclamar la garantía. "
        "Pagué con tarjeta de crédito y necesito revisar qué puedo solicitar."
    )
    started = client.post("/api/m34/intake/start", {"problem_statement": narrative}, expected=201)
    code = started.get("recovery_code")
    require(bool(code), "No se recibió recovery code M34")

    analyzed = client.post("/api/m34/intake/analyze", {"recovery_code": code}, expected=200)
    facts = analyzed.get("facts") or []
    require(bool(facts), "El smoke M35 requiere hechos M34 candidatos")
    client.post(
        "/api/m34/intake/facts/decide",
        {
            "recovery_code": code,
            "decisions": [{"fact_id": fact["fact_id"], "action": "CONFIRM"} for fact in facts],
        },
        expected=200,
    )

    for _ in range(16):
        step = client.post("/api/m34/intake/next-step", {"recovery_code": code}, expected=200)
        action = step.get("action")
        if action == "READY_FOR_RECOMMENDATION":
            break
        require(action in {"ASK_QUESTION", "ROUTE_TOPIC", "CONFIRM_RISK"}, f"Acción inesperada: {action}")
        question = step.get("question") or {}
        value = "dismiss" if action == "CONFIRM_RISK" else answer_for(question)
        client.post(
            "/api/m34/intake/answer",
            {"recovery_code": code, "question_id": question.get("question_id"), "value": value},
            expected=200,
        )
    else:
        raise AssertionError("No se alcanzó READY_FOR_RECOMMENDATION")

    recommendation = client.post("/api/m34/intake/recommendation", {"recovery_code": code}, expected=200)
    require(recommendation.get("outcome") == "RECOMMEND", "M35 smoke necesita recomendación vigente")
    require(recommendation.get("primary", {}).get("product_code") == "CO-CD-003", "Producto M35 smoke inesperado")
    return code, recommendation["decision_id"]


def main() -> int:
    anonymous = Client()
    code, decision_id = recommended_consumer_intake(anonymous)

    denied = anonymous.post("/api/m35/intake/claim", {"recovery_code": code}, expected=401)
    require(denied.get("code") == "AUTH_REQUIRED", "El claim anónimo debe fallar por autenticación")

    account = Client()
    register_client(account, "Owner")
    csrf = account.csrf
    account.csrf = ""
    csrf_denied = account.post("/api/m35/intake/claim", {"recovery_code": code}, expected=403)
    require(csrf_denied.get("code") == "CSRF_FAILED", "El claim sin CSRF debe fallar")
    account.csrf = csrf

    claimed = account.post("/api/m35/intake/claim", {"recovery_code": code}, expected=201)
    require(claimed.get("decision_id") == decision_id, "El handoff perdió decision_id")
    require(claimed.get("product_code") == "CO-CD-003", "El handoff cambió producto")
    require(claimed.get("next_route") == "/nuevo/CO-CD-003", "Ruta de fulfillment inesperada")
    require(claimed.get("idempotent") is False, "Primer claim no debe ser idempotente")

    draft = account.get("/api/drafts/product/CO-CD-003", expected=200)
    require(draft.get("id") == claimed.get("draft_id"), "Draft distinto al handoff")
    require(draft.get("answers") == {}, "M35.0 no debe fabricar respuestas de fulfillment")
    result = draft.get("result") or {}
    require(result.get("source") == "m35_m34_handoff", "Draft sin origen M35")
    require(result.get("decision_id") == decision_id, "Draft perdió decision_id")
    require(result.get("triage_reuse_status") == "PENDING_SAFE_MAPPING", "M35.0 adelantó mapping no implementado")
    serialized = json.dumps(draft, ensure_ascii=False).lower()
    require("compré un producto" not in serialized, "El relato fue copiado al draft plaintext")
    require("matched_fact_ids" not in serialized, "Metadata interna M34 llegó al draft")
    require("input_fingerprint" not in serialized, "Fingerprint interno M34 llegó al draft")

    repeated = account.post("/api/m35/intake/claim", {"recovery_code": code}, expected=200)
    require(repeated.get("handoff_id") == claimed.get("handoff_id"), "Reclaim creó otro handoff")
    require(repeated.get("draft_id") == claimed.get("draft_id"), "Reclaim creó otro draft")
    require(repeated.get("idempotent") is True, "Reclaim debería ser idempotente")

    intruder = Client()
    register_client(intruder, "Intruder")
    stolen = intruder.post("/api/m35/intake/claim", {"recovery_code": code}, expected=409)
    require(stolen.get("code") == "HANDOFF_CONFLICT", "Otra cuenta no fue bloqueada")

    unavailable = anonymous.post("/api/m34/intake/recover", {"recovery_code": code}, expected=422)
    require(unavailable.get("code") == "INTAKE_VALIDATION", "El código transferido siguió recuperable como intake anónimo")

    print(
        "M35.0 HTTP smoke PASS · "
        f"product={claimed.get('product_code')} decision={decision_id} "
        f"handoff={claimed.get('handoff_id')} csrf=blocked theft=blocked "
        f"idempotent={repeated.get('idempotent')}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"M35.0 HTTP smoke FAIL: {exc}", file=sys.stderr)
        raise
