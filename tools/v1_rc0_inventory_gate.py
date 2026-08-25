#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    interviews = load_json(DATA / "interviews.json")
    rules = load_json(DATA / "rules.json")
    products = load_json(DATA / "products.json")
    contracts = load_json(ROOT / "config" / "m34" / "product_contracts.json")

    product_codes = set(interviews)
    question_count = sum(len((item or {}).get("questions") or []) for item in interviews.values())
    rule_count = sum(len(items or []) for items in rules.values())

    if len(product_codes) != 11:
        raise SystemExit(f"RC0: se esperaban 11 productos y se encontraron {len(product_codes)}")
    if question_count < 473:
        raise SystemExit(f"RC0: la cobertura fuente bajó de 473 a {question_count} preguntas")
    if rule_count < 273:
        raise SystemExit(f"RC0: la cobertura de reglas bajó de 273 a {rule_count}")

    if isinstance(products, dict):
        catalog_codes = set(products)
    elif isinstance(products, list):
        catalog_codes = {str(item.get("code") or item.get("product_code") or "") for item in products if isinstance(item, dict)}
    else:
        raise SystemExit("RC0: data/products.json tiene una forma inesperada")
    if not product_codes.issubset(catalog_codes):
        missing = sorted(product_codes - catalog_codes)
        raise SystemExit(f"RC0: productos de entrevista ausentes del catálogo: {missing}")

    contract_codes = set((contracts.get("products") or contracts).keys()) if isinstance(contracts, dict) else set()
    if contract_codes != product_codes:
        raise SystemExit(
            "RC0: los contratos M34 no cubren exactamente el portafolio fuente: "
            f"missing={sorted(product_codes - contract_codes)} extra={sorted(contract_codes - product_codes)}"
        )

    required_paths = [
        ROOT / "legalai_platform" / "legal_source_registry.py",
        ROOT / "legalai_platform" / "colombian_business_calendar.py",
        ROOT / "legalai_platform" / "runtime_m33_overrides.py",
        ROOT / "m33_4_consumer_source_finalize.py",
        ROOT / "m33_4_debt_source_finalize.py",
        ROOT / "m33_4_employment_source_finalize.py",
        ROOT / "m33_4_habeas_source_finalize.py",
        ROOT / "m33_4_health_source_finalize.py",
        ROOT / "m33_4_labor_source_finalize.py",
        ROOT / "m33_4_lease_source_finalize.py",
        ROOT / "m33_4_nda_source_finalize.py",
        ROOT / "m33_4_sast_source_finalize.py",
        ROOT / "m33_4_traffic_source_finalize.py",
        ROOT / "config" / "m34" / "recommendation_contracts.json",
        ROOT / "config" / "m35" / "fulfillment_fact_mappings.json",
        ROOT / "config" / "m37" / "disposition_contracts.json",
    ]
    missing_paths = [str(path.relative_to(ROOT)) for path in required_paths if not path.is_file()]
    if missing_paths:
        raise SystemExit(f"RC0: faltan capacidades requeridas de la línea combinada: {missing_paths}")

    print(
        "V1-RC0 inventory PASS · "
        f"products={len(product_codes)} questions={question_count} rules={rule_count} "
        "m33_4_sources=present m34_contracts=exact m37_disposition=present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
