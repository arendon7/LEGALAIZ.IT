from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO, StringIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import csv
import json
import mimetypes
import re
import uuid


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


MIME_BY_SUFFIX = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


class CanonicalActivationV210:
    """Activa el ingreso físico avanzado sin relajar ninguna puerta jurídica.

    La carpeta de intercambio permite que un usuario local coloque originales junto al
    prototipo. El escaneo únicamente los ingresa a cuarentena. No verifica identidad,
    no aprueba contenido, no publica plantillas y no habilita generación primaria.
    """

    CODES = ("CO-EM-003", "CO-LA-001", "CO-TR-002", "CO-TR-001")

    def __init__(self, root: Path, intake_plan: list[dict], intake, canonical_generation,
                 traceability, review, products: list[dict]):
        self.root = Path(root)
        self.dropbox = self.root / "administracion_avanzada" / "originales_juridicos"
        self.dropbox.mkdir(parents=True, exist_ok=True)
        self.intake_plan = {x["product_code"]: x for x in intake_plan if x["product_code"] in self.CODES}
        self.intake = intake
        self.canonical_generation = canonical_generation
        self.traceability = traceability
        self.review = review
        self.products = {x["code"]: x for x in products}
        self._ensure_dropbox_layout()

    def _ensure_dropbox_layout(self) -> None:
        overview = [
            "LegalAIZ.it · Administración avanzada · Originales jurídicos",
            "",
            "Esta carpeta NO es necesaria para abrir ni probar la webapp.",
            "",
            "1. Úsela únicamente cuando el equipo jurídico decida incorporar un original aprobado.",
            "2. Inicie la aplicación desde 00_ABRIR_LEGALAIZIT_MAC.command y abra Administración avanzada.",
            "3. Administración ejecuta Escanear e ingresar originales.",
            "4. Los archivos entran únicamente a cuarentena.",
            "5. Especialista y QA deben aprobar el mismo registro antes del cotejo.",
            "",
            "Esta carpeta no autoriza publicación ni uso profesional.",
        ]
        (self.dropbox / "LEEME_PRIMERO.txt").write_text("\n".join(overview) + "\n", encoding="utf-8")
        for code in self.CODES:
            plan = self.intake_plan.get(code, {"title": code, "artifacts": []})
            folder = self.dropbox / code
            folder.mkdir(parents=True, exist_ok=True)
            lines = [f"{code} · {plan.get('title', code)}", "", "Entregables esperados:"]
            for artifact in plan.get("artifacts", []):
                req = "OBLIGATORIO" if artifact.get("required") else "OPCIONAL"
                ext = ", ".join(artifact.get("extensions", []))
                hints = ", ".join(artifact.get("filename_hints", []))
                lines.append(f"- [{req}] {artifact['label']} · {ext} · pistas: {hints}")
            lines += ["", "No cambie el contenido para ajustarlo al sistema. Debe conservarse el binario recibido."]
            (folder / "LEEME.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def create_schema(self, con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS canonical_dropbox_scans_v210(
              id TEXT PRIMARY KEY,
              actor_id TEXT NOT NULL,
              status TEXT NOT NULL,
              files_found INTEGER NOT NULL,
              files_ingested INTEGER NOT NULL,
              files_skipped INTEGER NOT NULL,
              errors INTEGER NOT NULL,
              manifest_json TEXT NOT NULL,
              manifest_sha256 TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(actor_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS canonical_activation_rehearsals_v210(
              id TEXT PRIMARY KEY,
              product_code TEXT NOT NULL,
              status TEXT NOT NULL,
              score INTEGER NOT NULL,
              snapshot_json TEXT NOT NULL,
              snapshot_sha256 TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(created_by) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_car210_product ON canonical_activation_rehearsals_v210(product_code,created_at DESC);
            CREATE TABLE IF NOT EXISTS canonical_activation_events_v210(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              product_code TEXT,
              event_type TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              previous_event_hash TEXT,
              event_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_cae210_product ON canonical_activation_events_v210(product_code,id);
            """
        )

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")

    def _artifact_match(self, code: str, path: Path) -> tuple[dict | None, int]:
        plan = self.intake_plan.get(code)
        if not plan:
            return None, -1
        suffix = path.suffix.lower()
        stem = self._norm(path.stem)
        best = None
        best_score = -1
        compatible = []
        for artifact in plan.get("artifacts", []):
            if suffix not in artifact.get("extensions", []):
                continue
            compatible.append(artifact)
            score = 1 + (1 if artifact.get("required") else 0)
            for hint in artifact.get("filename_hints", []):
                if self._norm(hint) in stem:
                    score += 4
            if score > best_score:
                best, best_score = artifact, score
        if best_score <= 2 and len(compatible) > 1:
            return None, best_score
        return best, best_score

    def _dropbox_files(self, code: str) -> list[dict]:
        folder = self.dropbox / code
        rows = []
        for path in sorted(folder.iterdir()) if folder.exists() else []:
            if not path.is_file() or path.name.startswith(".") or path.name.upper().startswith("LEEME"):
                continue
            artifact, score = self._artifact_match(code, path)
            raw = path.read_bytes()
            rows.append({
                "name": path.name,
                "size_bytes": len(raw),
                "sha256": sha256(raw).hexdigest(),
                "suffix": path.suffix.lower(),
                "artifact_key": artifact.get("key") if artifact else None,
                "artifact_label": artifact.get("label") if artifact else None,
                "match_score": score,
                "recognized": bool(artifact),
            })
        return rows

    @staticmethod
    def _event(con, product_code: str | None, event_type: str, actor_id: str, detail: dict) -> str:
        prev = con.execute(
            "SELECT event_hash FROM canonical_activation_events_v210 WHERE product_code IS ? ORDER BY id DESC LIMIT 1",
            (product_code,),
        ).fetchone()
        previous = prev["event_hash"] if prev else ""
        created = utc_iso()
        detail_json = json.dumps(detail, ensure_ascii=False, sort_keys=True, default=str)
        digest = sha256("|".join([product_code or "GLOBAL", event_type, actor_id, created, previous, detail_json]).encode()).hexdigest()
        con.execute(
            """INSERT INTO canonical_activation_events_v210(product_code,event_type,actor_id,detail_json,previous_event_hash,event_hash,created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (product_code, event_type, actor_id, detail_json, previous or None, digest, created),
        )
        return digest

    @staticmethod
    def verify_chain(events: list[dict]) -> bool:
        previous_by_product: dict[str, str] = {}
        for event in sorted(events, key=lambda x: x["id"]):
            key = event.get("product_code") or "GLOBAL"
            previous = previous_by_product.get(key, "")
            digest = sha256("|".join([
                key, event["event_type"], event["actor_id"], event["created_at"], previous, event["detail_json"]
            ]).encode()).hexdigest()
            if (event.get("previous_event_hash") or "") != previous or event.get("event_hash") != digest:
                return False
            previous_by_product[key] = digest
        return True

    def _records(self, con, code: str) -> list[dict]:
        rows = con.execute(
            """SELECT id,artifact_key,original_name,sha256,size_bytes,detected_type,status,legal_decision,qa_decision,
                      source_file_id,uploaded_by,uploaded_at
               FROM canonical_intake_records WHERE product_code=? ORDER BY uploaded_at DESC,id DESC""",
            (code,),
        ).fetchall()
        return [dict(x) for x in rows]

    def product_summary(self, con, code: str) -> dict:
        code = code.upper()
        if code not in self.CODES:
            raise ValueError("Producto fuera de la ola de activación v2.10.")
        plan = self.intake_plan[code]
        records = self._records(con, code)
        files = self._dropbox_files(code)
        gate = self.canonical_generation.readiness(con, code)
        required = [x for x in plan.get("artifacts", []) if x.get("required")]
        satisfied = set()
        verified = set()
        for row in records:
            if row.get("status") == "Importado y verificado" or row.get("source_file_id"):
                verified.add(row["artifact_key"])
            if row.get("status") not in {"Duplicado detectado"}:
                satisfied.add(row["artifact_key"])
        latest = con.execute(
            "SELECT * FROM canonical_activation_rehearsals_v210 WHERE product_code=? ORDER BY created_at DESC LIMIT 1",
            (code,),
        ).fetchone()
        jobs = con.execute(
            """SELECT status AS current_status,COUNT(*) total FROM canonical_review_jobs
               WHERE product_code=? GROUP BY status""",
            (code,),
        ).fetchall()
        return {
            "product_code": code,
            "title": plan.get("title") or self.products.get(code, {}).get("title", code),
            "dropbox_relative_path": f"administracion_avanzada/originales_juridicos/{code}",
            "artifacts": [
                {
                    **artifact,
                    "received": artifact["key"] in satisfied,
                    "verified": artifact["key"] in verified,
                    "matching_files": [x for x in files if x.get("artifact_key") == artifact["key"]],
                }
                for artifact in plan.get("artifacts", [])
            ],
            "dropbox_files": files,
            "intake_records": records,
            "metrics": {
                "required_artifacts": len(required),
                "required_received": sum(x["key"] in satisfied for x in required),
                "required_verified": sum(x["key"] in verified for x in required),
                "dropbox_files": len(files),
                "recognized_files": sum(x["recognized"] for x in files),
                "intake_records": len(records),
                "verified_sources": gate.get("traceability_gate", {}).get("verified_source_files", 0),
                "review_jobs": sum(x["total"] for x in jobs),
                "approved_blocks": gate.get("traceability_gate", {}).get("approved_blocks", 0),
                "required_blocks": gate.get("traceability_gate", {}).get("required_blocks", 0),
                "release_score": gate["score"],
            },
            "readiness": gate,
            "review_statuses": [dict(x) for x in jobs],
            "latest_rehearsal": dict(latest) if latest else None,
            "professional_use_authorized": False,
        }

    def summary(self, con) -> dict:
        products = [self.product_summary(con, code) for code in self.CODES]
        scans = [dict(x) for x in con.execute(
            "SELECT * FROM canonical_dropbox_scans_v210 ORDER BY created_at DESC LIMIT 10"
        ).fetchall()]
        events = [dict(x) for x in con.execute(
            "SELECT * FROM canonical_activation_events_v210 ORDER BY id"
        ).fetchall()]
        return {
            "version": "2.10",
            "title": "Activación canónica guiada",
            "dropbox_relative_path": "administracion_avanzada/originales_juridicos",
            "products": products,
            "metrics": {
                "priority_products": len(products),
                "dropbox_files": sum(x["metrics"]["dropbox_files"] for x in products),
                "recognized_files": sum(x["metrics"]["recognized_files"] for x in products),
                "intake_records": sum(x["metrics"]["intake_records"] for x in products),
                "verified_sources": sum(x["metrics"]["verified_sources"] for x in products),
                "ready_products": sum(bool(x["readiness"]["ready"]) for x in products),
                "average_release_score": round(sum(x["readiness"]["score"] for x in products) / max(1, len(products))),
            },
            "scans": scans,
            "chain_valid": self.verify_chain(events),
            "notice": "El escaneo solo ingresa binarios a cuarentena. La identidad, el contenido, el cotejo, la aprobación dual y la publicación continúan separados.",
        }

    def scan(self, con, actor_id: str, actor_role: str) -> dict:
        found = ingested = skipped = errors = 0
        items = []
        for code in self.CODES:
            for item in self._dropbox_files(code):
                found += 1
                path = self.dropbox / code / item["name"]
                if not item["recognized"]:
                    errors += 1
                    items.append({**item, "product_code": code, "outcome": "No reconocido", "error": "Nombre o formato no permiten asociar el entregable."})
                    continue
                existing = con.execute(
                    """SELECT id,status FROM canonical_intake_records
                       WHERE product_code=? AND artifact_key=? AND sha256=? ORDER BY uploaded_at DESC LIMIT 1""",
                    (code, item["artifact_key"], item["sha256"]),
                ).fetchone()
                if existing:
                    skipped += 1
                    items.append({**item, "product_code": code, "outcome": "Ya ingresado", "intake_id": existing["id"], "status": existing["status"]})
                    continue
                try:
                    raw = path.read_bytes()
                    mime = MIME_BY_SUFFIX.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                    result = self.intake.upload(
                        con, code, item["artifact_key"], path.name, raw, mime,
                        item["sha256"], actor_id, actor_role,
                    )
                    ingested += 1
                    items.append({**item, "product_code": code, "outcome": "Ingresado a cuarentena", **result})
                    self._event(con, code, "dropbox_file_ingested", actor_id, {
                        "name": path.name, "artifact_key": item["artifact_key"], "sha256": item["sha256"],
                        "intake_id": result.get("intake_id"), "status": result.get("status"),
                    })
                except Exception as exc:
                    errors += 1
                    items.append({**item, "product_code": code, "outcome": "Error", "error": str(exc)})
        manifest = {
            "version": "2.10", "created_at": utc_iso(), "actor_id": actor_id,
            "files_found": found, "files_ingested": ingested, "files_skipped": skipped,
            "errors": errors, "items": items,
        }
        raw = json.dumps(manifest, ensure_ascii=False, sort_keys=True, default=str)
        digest = sha256(raw.encode()).hexdigest()
        scan_id = "SCAN-" + uuid.uuid4().hex[:12].upper()
        status = "Completado" if not errors else ("Completado con observaciones" if ingested or skipped else "Requiere atención")
        con.execute(
            """INSERT INTO canonical_dropbox_scans_v210(id,actor_id,status,files_found,files_ingested,files_skipped,errors,
               manifest_json,manifest_sha256,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (scan_id, actor_id, status, found, ingested, skipped, errors, raw, digest, manifest["created_at"]),
        )
        self._event(con, None, "dropbox_scan_completed", actor_id, {
            "scan_id": scan_id, "status": status, "files_found": found,
            "files_ingested": ingested, "files_skipped": skipped, "errors": errors,
            "manifest_sha256": digest,
        })
        return {"ok": True, "scan_id": scan_id, "status": status, "manifest_sha256": digest, **manifest}

    def rehearse(self, con, code: str, actor_id: str) -> dict:
        code = code.upper()
        product = self.product_summary(con, code)
        snapshot = {
            "version": "2.10",
            "product_code": code,
            "created_at": utc_iso(),
            "readiness": product["readiness"],
            "artifacts": [
                {k: x.get(k) for k in ("key", "label", "required", "received", "verified")}
                for x in product["artifacts"]
            ],
            "metrics": product["metrics"],
            "professional_use_authorized": False,
            "publication_performed": False,
            "notice": "El ensayo es una fotografía de controles. No aprueba ni publica el producto.",
        }
        raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
        digest = sha256(raw.encode()).hexdigest()
        status = "Listo para solicitar activación controlada" if product["readiness"]["ready"] else "Bloqueado por puertas pendientes"
        ident = "REH-" + uuid.uuid4().hex[:12].upper()
        con.execute(
            """INSERT INTO canonical_activation_rehearsals_v210(id,product_code,status,score,snapshot_json,snapshot_sha256,
               created_by,created_at) VALUES(?,?,?,?,?,?,?,?)""",
            (ident, code, status, product["readiness"]["score"], raw, digest, actor_id, snapshot["created_at"]),
        )
        self._event(con, code, "activation_rehearsal", actor_id, {
            "rehearsal_id": ident, "status": status, "score": product["readiness"]["score"],
            "snapshot_sha256": digest, "ready": product["readiness"]["ready"],
        })
        return {"ok": True, "id": ident, "status": status, "score": product["readiness"]["score"], "snapshot_sha256": digest, "snapshot": snapshot}

    def evidence_bytes(self, con, code: str) -> bytes:
        product = self.product_summary(con, code)
        rehearsals = [dict(x) for x in con.execute(
            "SELECT * FROM canonical_activation_rehearsals_v210 WHERE product_code=? ORDER BY created_at DESC",
            (code.upper(),),
        ).fetchall()]
        events = [dict(x) for x in con.execute(
            "SELECT * FROM canonical_activation_events_v210 WHERE product_code=? ORDER BY id",
            (code.upper(),),
        ).fetchall()]
        artifacts_csv = StringIO()
        writer = csv.writer(artifacts_csv)
        writer.writerow(["artifact_key", "label", "required", "received", "verified", "extensions"])
        for x in product["artifacts"]:
            writer.writerow([x["key"], x["label"], x.get("required", False), x["received"], x["verified"], ",".join(x.get("extensions", []))])
        intakes_csv = StringIO()
        writer = csv.writer(intakes_csv)
        writer.writerow(["id", "artifact_key", "original_name", "sha256", "status", "legal_decision", "qa_decision", "uploaded_at"])
        for x in product["intake_records"]:
            writer.writerow([x.get("id"), x.get("artifact_key"), x.get("original_name"), x.get("sha256"), x.get("status"), x.get("legal_decision"), x.get("qa_decision"), x.get("uploaded_at")])
        out = BytesIO()
        with ZipFile(out, "w", ZIP_DEFLATED) as z:
            z.writestr("ACTIVACION_RESUMEN.json", json.dumps(product, ensure_ascii=False, indent=2, default=str))
            z.writestr("ARTEFACTOS_ESPERADOS.csv", artifacts_csv.getvalue())
            z.writestr("REGISTROS_INGESTA.csv", intakes_csv.getvalue())
            z.writestr("ENSAYOS_ACTIVACION.json", json.dumps(rehearsals, ensure_ascii=False, indent=2, default=str))
            z.writestr("EVENTOS_CADENA.json", json.dumps({"chain_valid": self.verify_chain(events), "events": events}, ensure_ascii=False, indent=2, default=str))
            z.writestr("LEEME.txt", (
                f"LegalAIZ.it · Evidencia de activación {code.upper()} · v2.10\n\n"
                "Este paquete contiene metadatos, hashes, controles y resultados de ensayo.\n"
                "No contiene los binarios originales y no acredita aprobación jurídica o publicación.\n"
            ))
        return out.getvalue()
