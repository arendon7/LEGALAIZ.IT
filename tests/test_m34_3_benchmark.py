import unittest

from legalai_platform.adaptive_question_m34_3 import (
    AdaptiveIntakeStore,
    AdaptiveQuestionEngine,
)


def asserted_fact(fact_type, value):
    return {
        "fact_id": "fact_bench_" + fact_type.replace(".", "_")[:28],
        "fact_type": fact_type,
        "value": value,
        "normalized_value": value,
        "provenance": "USER_ASSERTED",
        "confirmation_status": "UNCONFIRMED",
        "criticality": "HIGH",
        "source_reference": "benchmark:m34.3",
        "evidence_ids": [],
        "extraction_confidence": None,
        "legal_relevance": "HIGH",
        "created_at": None,
        "updated_at": None,
        "notes": "benchmark",
    }


def substantive_value(contract):
    answer_type = contract.get("answer_type")
    options = contract.get("options") or []
    if answer_type == "select":
        choices = [
            item["value"]
            for item in options
            if str(item.get("value", "")).lower() not in {"no_se", "uncertain"}
        ]
        if not choices:
            raise AssertionError(f"Sin opción sustantiva: {contract.get('question_contract_id')}")
        return choices[0]
    if answer_type == "multiselect":
        if not options:
            raise AssertionError(f"Sin opciones: {contract.get('question_contract_id')}")
        return [options[0]["value"]]
    if answer_type == "date":
        return "2026-08-01"
    if answer_type == "money_cop":
        return {"amount_cop": 1800000, "currency": "COP"}
    if answer_type == "number":
        return 1
    if answer_type in {"text", "textarea"}:
        return "dato suficiente para el triage"
    if answer_type == "boolean":
        return True
    raise AssertionError(f"Tipo no cubierto: {answer_type}")


class M343PortfolioBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.engine = AdaptiveQuestionEngine()

    def base_state(self, code):
        return {
            "stage": "FACTS_REVIEWED",
            "facts": [],
            "pending_fact_count": 0,
            "risk_signals": [],
            "contradictions": [],
            "candidate_products": [
                {"product_code": code, "signal_score": 0.9, "status": "TOPIC_SIGNAL_ONLY"}
            ],
            "routing": {},
            "question_history": [],
        }

    def test_every_canonical_product_reaches_sufficiency_with_only_triage_contracts(self):
        failures = []
        for code in sorted(self.engine.products):
            state = self.base_state(code)
            asked = []
            for _ in range(12):
                step = self.engine.next_step(state)
                if step["action"] == "READY_FOR_RECOMMENDATION":
                    if code not in step["sufficiency"]["ready_product_codes"]:
                        failures.append(f"{code}: READY sin producto en ready_product_codes")
                    break
                if step["action"] != "ASK_QUESTION":
                    failures.append(f"{code}: acción inesperada {step['action']} antes de READY")
                    break
                qid = step["question"]["question_id"]
                if qid in asked:
                    failures.append(f"{code}: pregunta repetida {qid}")
                    break
                asked.append(qid)
                contract = self.engine.registry.fact_by_id[qid]
                state["facts"].append(asserted_fact(contract["fact_type"], substantive_value(contract)))
                state["question_history"].append({"question_id": qid, "kind": "FACT"})
            else:
                failures.append(f"{code}: no alcanzó READY dentro de 12 preguntas")

            triage_count = len(self.engine.registry.requirements_for_product(code, "TRIAGE_REQUIRED"))
            if len(asked) != triage_count:
                failures.append(f"{code}: preguntas={len(asked)} requisitos_triage={triage_count}")
            if len(asked) > 6:
                failures.append(f"{code}: triage demasiado largo ({len(asked)} preguntas)")

        if failures:
            self.fail("\n".join(failures))

    def test_portfolio_benchmark_never_returns_a_recommendation_payload(self):
        for code in sorted(self.engine.products):
            step = self.engine.next_step(self.base_state(code))
            self.assertNotIn("recommendation", step)
            self.assertNotIn("recommended_product", step)
            self.assertNotEqual(step["action"], "RECOMMEND")

    def test_unknown_non_select_answer_is_accepted_but_never_satisfies_fact(self):
        date_contract = next(
            item for item in self.engine.registry.fact_questions
            if item.get("requirement_mode") == "TRIAGE_REQUIRED" and item.get("answer_type") == "date"
        )
        normalized = AdaptiveIntakeStore.normalize_answer(date_contract, "UNCERTAIN")
        self.assertEqual(normalized, "UNCERTAIN")
        facts = [asserted_fact(date_contract["fact_type"], normalized)]
        self.assertNotIn(date_contract["fact_type"], self.engine.sufficient_fact_types(facts))

    def test_unknown_required_fact_does_not_loop_and_ends_in_safe_escalation(self):
        code = "CO-CD-003"
        state = self.base_state(code)
        first = self.engine.next_step(state)
        self.assertEqual(first["action"], "ASK_QUESTION")
        first_contract = self.engine.registry.fact_by_id[first["question"]["question_id"]]
        state["facts"].append(asserted_fact(first_contract["fact_type"], "UNCERTAIN"))
        state["question_history"].append({"question_id": first_contract["question_contract_id"], "kind": "FACT"})

        seen = {first_contract["question_contract_id"]}
        for _ in range(12):
            step = self.engine.next_step(state)
            if step["action"] == "ESCALATE":
                self.assertIn("INSUFFICIENT_INFORMATION", step["reason_codes"])
                return
            self.assertEqual(step["action"], "ASK_QUESTION")
            qid = step["question"]["question_id"]
            self.assertNotIn(qid, seen)
            seen.add(qid)
            contract = self.engine.registry.fact_by_id[qid]
            state["facts"].append(asserted_fact(contract["fact_type"], substantive_value(contract)))
            state["question_history"].append({"question_id": qid, "kind": "FACT"})
        self.fail("La incertidumbre crítica no terminó en escalamiento dentro del límite")

    def test_confirmed_criminal_signal_is_hard_escalation_for_every_product(self):
        for code in sorted(self.engine.products):
            state = self.base_state(code)
            state["risk_signals"] = [{"code": "CRIMINAL_MATTER", "status": "CONFIRMED_BY_USER"}]
            step = self.engine.next_step(state)
            self.assertEqual(step["action"], "ESCALATE", code)
            self.assertIn("CRIMINAL_MATTER", step["reason_codes"], code)


if __name__ == "__main__":
    unittest.main()
