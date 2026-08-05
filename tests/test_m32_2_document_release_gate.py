from __future__ import annotations

import json
from pathlib import Path

import pytest

from legalai_platform.document_release_gate import (
    CANONICAL_PRODUCTS,
    M32_2_PRODUCTS,
    enforce_document_release_gate,
    install_docx_release_gate,
    manifest_path_for,
)


def _sections(product_code: str) -> list[dict]:
    return [
        {
            "heading": "1. Identificación y alcance",
            "text": (
                f"Documento demostrativo controlado del producto {product_code}. "
                "La información debe cotejarse con el expediente y los soportes aportados."
            ),
        },
        {
            "heading": "2. Solicitudes y evidencia",
            "bullets": [
                "Verificar identidad, competencia, fechas y destinatario.",
                "Conservar los soportes y la constancia de radicación.",
                "No afirmar consecuencias automáticas sin revisión del caso.",
            ],
        },
        {
            "heading": "CONTROL DE USO",
            "_type": "control",
            "text": "Borrador sujeto a revisión jurídica, QA y aprobación dual antes de liberación.",
        },
    ]


def test_catalogo_canonico_y_ola_m32_2_completos():
    assert len(CANONICAL_PRODUCTS) == 11
    assert M32_2_PRODUCTS == {
        "CO-TR-001",
        "CO-TR-002",
        "CO-SA-001",
        "CO-CD-001",
        "CO-CD-003",
        "CO-CD-004",
    }
    assert M32_2_PRODUCTS < CANONICAL_PRODUCTS


@pytest.mark.parametrize("product_code", sorted(M32_2_PRODUCTS))
def test_builder_instalado_genera_manifiesto_pendiente_de_aprobacion(tmp_path: Path, product_code: str):
    install_docx_release_gate()
    from docx_builder import build_docx

    target = tmp_path / f"{product_code}_M32_2_muestra.docx"
    build_docx(
        target,
        f"Muestra controlada {product_code}",
        "Preflight transversal M32.2",
        [("Producto", product_code), ("Estado", "Borrador controlado")],
        _sections(product_code),
    )

    sidecar = manifest_path_for(target)
    assert target.is_file()
    assert sidecar.is_file()
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["product_code"] == product_code
    assert payload["quality"]["valid"] is True
    assert payload["visual_preflight"]["valid"] is True
    assert payload["approval_state"] == {"legal": "pending", "qa": "pending"}
    assert payload["requires_human_visual_review"] is True
    assert payload["release_status"] == "preflight_passed_pending_dual_approval"
    assert len(payload["sha256"]) == 64


def test_compuerta_bloquea_un_archivo_que_no_es_docx(tmp_path: Path):
    invalid = tmp_path / "CO-TR-001_archivo_invalido.docx"
    invalid.write_text("esto no es un paquete OOXML", encoding="utf-8")
    with pytest.raises(ValueError, match="Control de calidad DOCX fallido"):
        enforce_document_release_gate(invalid, expected_product="CO-TR-001")
