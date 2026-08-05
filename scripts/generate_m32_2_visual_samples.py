#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil


PRODUCT_KINDS = {
    "CO-TR-001": "sast_report",
    "CO-TR-002": "traffic_record_request",
    "CO-SA-001": "health_petition",
    "CO-CD-001": "habeas_claim",
    "CO-CD-003": "consumer_mechanism_diagnosis",
    "CO-CD-004": "debt_diagnostic",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera evidencia visual M32.2 mediante las fábricas activas.")
    parser.add_argument("--output", required=True, help="Directorio de salida para las seis muestras.")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    runtime = output.parent / "runtime"
    samples = output
    shutil.rmtree(output.parent, ignore_errors=True)
    samples.mkdir(parents=True, exist_ok=True)
    os.environ["LEGAL_RUNTIME_DIR"] = str(runtime)
    os.environ.setdefault("LEGAL_PROFILE", "local")
    os.environ.setdefault("LEGAL_ALLOW_DEMO_ACCOUNTS", "true")

    # La instalación debe ocurrir antes de importar core_v11, que conserva la
    # importación histórica directa de build_docx.
    from legalai_platform.document_release_gate import (
        enforce_document_release_gate,
        install_docx_release_gate,
        manifest_path_for,
    )

    install_docx_release_gate()
    import core_v11

    core_v11.init_db(reset=True, seed_demo_data=True)
    con = core_v11.db()
    records: list[dict] = []
    try:
        for product_code, preferred_kind in PRODUCT_KINDS.items():
            row = con.execute(
                """
                SELECT product_code, kind, name, file_path, version, status
                  FROM documents
                 WHERE product_code=?
                   AND mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                 ORDER BY CASE WHEN kind=? THEN 0 WHEN kind='traceability' THEN 2 ELSE 1 END,
                          updated_at DESC
                 LIMIT 1
                """,
                (product_code, preferred_kind),
            ).fetchone()
            if not row:
                raise RuntimeError(f"No se generó una muestra DOCX para {product_code}.")
            source = Path(row["file_path"])
            if not source.is_file():
                raise RuntimeError(f"La ruta generada no existe para {product_code}: {source}")
            source_manifest = manifest_path_for(source)
            if not source_manifest.is_file():
                enforce_document_release_gate(source, expected_product=product_code)
            destination = samples / f"{product_code}_{row['kind']}_M32_2.docx"
            shutil.copy2(source, destination)
            destination_manifest = manifest_path_for(destination)
            shutil.copy2(source_manifest, destination_manifest)
            gate = json.loads(destination_manifest.read_text(encoding="utf-8"))
            if gate.get("approval_state") != {"legal": "pending", "qa": "pending"}:
                raise RuntimeError(f"La muestra {product_code} no conserva aprobación dual pendiente.")
            if gate.get("requires_human_visual_review") is not True:
                raise RuntimeError(f"La muestra {product_code} no exige revisión visual humana.")
            records.append({
                "product_code": product_code,
                "kind": row["kind"],
                "source_name": row["name"],
                "sample_name": destination.name,
                "version": row["version"],
                "status": row["status"],
                "sha256": _sha256(destination),
                "quality_manifest": destination_manifest.name,
                "release_status": gate.get("release_status"),
            })
    finally:
        con.close()

    if {record["product_code"] for record in records} != set(PRODUCT_KINDS):
        raise RuntimeError("La evidencia no cubre exactamente los seis productos de M32.2.")
    manifest = {
        "iteration": "M32.2",
        "generator": "fábricas activas de core_v11/document_specs",
        "products": records,
        "approval_state": "pending_dual_approval",
        "requires_human_visual_review": True,
    }
    (samples / "m32-2-samples.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
