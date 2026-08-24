from __future__ import annotations

"""M36.3 — compuerta controlada de entrega in-app.

La entrega se construye exclusivamente a partir de copias M32.5 liberadas sobre
el hash aprobado. No reutiliza ``documents.file_path`` como fuente final, no
envía correo y no interpreta una solicitud de descarga como recepción efectiva.

La operación es una saga recuperable:

1. M36.2 debe acreditar ``delivery_gate_ready``;
2. se verifican todas las liberaciones M32;
3. se crea un paquete determinístico y se registra ``PREPARED``;
4. M24 pasa a ``ENTREGADO`` con la confirmación canónica;
5. el ledger M36.3 se finaliza como ``DELIVERED_IN_APP``.

Si el proceso cae después del paso 4, un retry valida la transición M24 y termina
el mismo delivery sin crear otro paquete ni una segunda entrega.
"""

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping
import re
import uuid
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import core_v11 as core
from legalai_platform.approval_desk_workspace import ApprovalDeskWorkspace, PermissionDenied
from legalai_platform.review_reconciliation_m36_2 import ReviewLifecycleReconciler, ReviewReconciliationError


SCHEMA_VERSION = "36.3.0"
DELIVERY_CONFIRMATION = "ENTREGAR SOLUCIÓN"
STATE_PREPARED = "PREPARED"
STATE_DELIVERED = "DELIVERED_IN_APP"
DELIVERY_STATES = frozenset({STATE_PREPARED, STATE_DELIVERED})
DOWNLOAD_ACTION = "DOWNLOAD_REQUESTED"
_FIXED_ZIP_DATE = (1980, 1, 1, 0, 0, 0)


class ControlledDeliveryError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _safe_id(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 100 or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise ControlledDeliveryError("IDENTIFIER_INVALID", f"{field} inválido.", 400)
    return text


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_info(name: str) -> ZipInfo:
    info = ZipInfo(name, _FIXED_ZIP_DATE)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    return info


class ControlledDeliveryCenter:
    """Entrega case-level de las copias M32 liberadas exactas."""

    def __init__(
        self,
        reconciler: ReviewLifecycleReconciler,
        workspace: ApprovalDeskWorkspace,
        journey,
        *,
        db_factory=None,
        delivery_root: str | Path | None = None,
    ):
        self.reconciler = reconciler
        self.workspace = workspace
        self.journey = journey
        self.db_factory = db_factory or core.db
        self.delivery_root = Path(delivery_root or (core.RUNTIME / "controlled-delivery")).resolve()
        self.delivery_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m36_controlled_delivery(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL UNIQUE,
              owner_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              fulfillment_intake_id TEXT NOT NULL,
              assignment_id TEXT NOT NULL,
              state TEXT NOT NULL,
              package_name TEXT NOT NULL,
              package_path TEXT NOT NULL,
              package_sha256 TEXT NOT NULL,
              manifest_sha256 TEXT NOT NULL,
              release_snapshot_json TEXT NOT NULL,
              release_snapshot_sha256 TEXT NOT NULL,
              release_count INTEGER NOT NULL,
              prepared_by TEXT NOT NULL,
              prepared_at TEXT NOT NULL,
              delivered_by TEXT,
              delivered_at TEXT,
              m24_transition_id TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m36_delivery_state
              ON m36_controlled_delivery(state,updated_at);
            CREATE TABLE IF NOT EXISTS m36_delivery_access_event(
              id TEXT PRIMARY KEY,
              delivery_id TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              action TEXT NOT NULL,
              package_sha256 TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m36_delivery_access
              ON m36_delivery_access_event(delivery_id,created_at);
            """
        )

    @staticmethod
    def _require_admin(actor: Mapping[str, Any]) -> None:
        if str(actor.get("role") or "") != "admin" or not str(actor.get("id") or "").strip():
            raise PermissionDenied("Solo administración puede ejecutar la entrega controlada del expediente.")

    @staticmethod
    def _case(con, case_id: str) -> dict[str, Any]:
        row = con.execute(
            "SELECT id,product_code,owner_id,status FROM cases WHERE id=?",
            (case_id,),
        ).fetchone()
        if not row:
            raise ControlledDeliveryError("CASE_NOT_FOUND", "Expediente no encontrado.", 404)
        value = dict(row)
        if not str(value.get("owner_id") or ""):
            raise ControlledDeliveryError("CASE_OWNER_MISSING", "El expediente no tiene titular verificable.", 422)
        return value

    @staticmethod
    def _row(con, case_id: str) -> dict[str, Any] | None:
        row = con.execute("SELECT * FROM m36_controlled_delivery WHERE case_id=?", (case_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _m36_links(con, case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        fulfillment = con.execute(
            "SELECT id,case_id,product_code,desk_case_ids_json,state FROM m36_fulfillment_intake WHERE case_id=?",
            (case_id,),
        ).fetchone()
        assignment = con.execute(
            "SELECT id,fulfillment_intake_id,state,specialist_id,qa_id FROM m36_professional_assignment WHERE case_id=?",
            (case_id,),
        ).fetchone()
        if not fulfillment or not assignment:
            raise ControlledDeliveryError("M36_TRACE_INCOMPLETE", "El expediente no conserva trazabilidad M36.0/M36.1 completa.", 422)
        fulfillment_value = dict(fulfillment)
        assignment_value = dict(assignment)
        if assignment_value.get("fulfillment_intake_id") != fulfillment_value.get("id"):
            raise ControlledDeliveryError("M36_TRACE_MISMATCH", "La asignación profesional no corresponde al intake vigente.", 422)
        if assignment_value.get("state") != "COMPLETE":
            raise ControlledDeliveryError("ASSIGNMENT_NOT_COMPLETE", "La asignación profesional aún no está completa.", 422)
        return fulfillment_value, assignment_value

    def _preflight(self, actor: dict[str, Any], case_id: str, con) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        self._require_admin(actor)
        case_id = _safe_id(case_id, "case_id")
        self.ensure_schema(con)
        case = self._case(con, case_id)
        fulfillment, assignment = self._m36_links(con, case_id)
        try:
            assessment = self.reconciler.assess(actor, case_id)
            history = self.reconciler.history(actor, case_id)
        except ReviewReconciliationError as exc:
            raise ControlledDeliveryError("REVIEW_RECONCILIATION_INVALID", str(exc), exc.status) from exc
        if not bool((history.get("audit") or {}).get("valid")):
            raise ControlledDeliveryError("RECONCILIATION_CHAIN_INVALID", "La cadena M36.2 no es íntegra.", 422)
        if assessment.get("m24_current_state") != "APROBADO_QA":
            raise ControlledDeliveryError("M24_NOT_QA_APPROVED", "M24 debe estar en APROBADO_QA antes de la entrega.", 422)
        if not assessment.get("qa_approval_complete") or not assessment.get("release_complete"):
            raise ControlledDeliveryError("RELEASE_GATE_INCOMPLETE", "Todos los documentos deben conservar aprobación jurídica, QA y liberación vigentes.", 422)
        if not assessment.get("delivery_gate_ready"):
            raise ControlledDeliveryError("DELIVERY_GATE_NOT_READY", "M36.2 aún no habilita la compuerta de entrega.", 422)
        if assessment.get("proposed_path") or assessment.get("blockers"):
            raise ControlledDeliveryError("REVIEW_RECONCILIATION_PENDING", "Existen estados de revisión pendientes de reconciliar.", 422)
        if int(assessment.get("desk_count") or 0) < 1:
            raise ControlledDeliveryError("NO_RELEASED_DOCUMENTS", "No existen documentos liberados para entrega.", 422)
        if str(case.get("product_code") or "") != str(assessment.get("product_code") or ""):
            raise ControlledDeliveryError("PRODUCT_TRACE_MISMATCH", "La revisión y el expediente corresponden a productos distintos.", 422)
        return case, fulfillment, assignment, assessment

    def _collect_releases(self, actor: dict[str, Any], case_id: str, assessment: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[tuple[str, bytes]]]:
        snapshot: list[dict[str, Any]] = []
        files: list[tuple[str, bytes]] = []
        used_names: set[str] = set()
        for item in assessment.get("desks") or []:
            desk_id = _safe_id(item.get("desk_id"), "desk_id")
            if not item.get("released"):
                raise ControlledDeliveryError("DESK_NOT_RELEASED", "Una mesa todavía no tiene copia liberada.", 422)
            try:
                source, release = self.workspace.released_path(actor, desk_id)
            except Exception as exc:
                raise ControlledDeliveryError("RELEASE_SOURCE_INVALID", "Una copia liberada M32 dejó de ser verificable.", 422) from exc
            body = source.read_bytes()
            digest = _sha256_bytes(body)
            if digest != str(release.get("sha256") or ""):
                raise ControlledDeliveryError("RELEASE_HASH_MISMATCH", "Una copia liberada no coincide con su hash aprobado.", 422)
            name = core.safe_filename(str(release.get("filename") or source.name), fallback="documento_final.docx")
            if name in used_names:
                name = core.safe_filename(f"{desk_id}_{name}", fallback=f"{desk_id}.docx")
            used_names.add(name)
            snapshot.append({
                "desk_id": desk_id,
                "document_id": str(item.get("document_id") or ""),
                "release_id": str(release.get("release_id") or ""),
                "revision_id": str(release.get("revision_id") or ""),
                "sha256": digest,
                "release_record_hash": str(release.get("release_record_hash") or ""),
                "filename": name,
                "size_bytes": len(body),
            })
            files.append((name, body))
        if not snapshot or len(snapshot) != int(assessment.get("desk_count") or 0):
            raise ControlledDeliveryError("RELEASE_COVERAGE_INCOMPLETE", "La entrega no cubre todos los documentos del expediente.", 422)
        return snapshot, files

    @staticmethod
    def _release_snapshot_sha(snapshot: list[dict[str, Any]]) -> str:
        return _sha256_bytes(_canonical_json(snapshot).encode("utf-8"))

    @staticmethod
    def _public_manifest(delivery_id: str, case: Mapping[str, Any], snapshot: list[dict[str, Any]], prepared_at: str) -> dict[str, Any]:
        return {
            "schema": "legalai_m36_3_delivery_manifest_v1",
            "schema_version": SCHEMA_VERSION,
            "delivery_id": delivery_id,
            "case_id": case["id"],
            "product_code": case["product_code"],
            "prepared_at": prepared_at,
            "delivery_channel": "IN_APP",
            "files": [
                {
                    "name": item["filename"],
                    "sha256": item["sha256"],
                    "size_bytes": item["size_bytes"],
                }
                for item in snapshot
            ],
            "controls": {
                "source": "M32_RELEASED_EXACT_HASH_ONLY",
                "dual_human_approval_verified": True,
                "automatic_legal_approval": False,
                "automatic_qa_approval": False,
                "external_notification_sent": False,
                "download_or_receipt_confirmed": False,
            },
            "notice": "El paquete fue preparado con copias liberadas tras revisión jurídica y QA. Su puesta a disposición no acredita descarga, lectura, recepción externa ni garantiza un resultado jurídico.",
        }

    def _package_dir(self, case_id: str, delivery_id: str) -> Path:
        target = (self.delivery_root / _safe_id(case_id, "case_id") / _safe_id(delivery_id, "delivery_id")).resolve()
        if self.delivery_root not in target.parents:
            raise ControlledDeliveryError("DELIVERY_PATH_INVALID", "Ruta interna de entrega inválida.", 500)
        return target

    def _write_package(
        self,
        *,
        case_id: str,
        delivery_id: str,
        package_name: str,
        manifest: Mapping[str, Any],
        files: list[tuple[str, bytes]],
    ) -> tuple[Path, str, str]:
        folder = self._package_dir(case_id, delivery_id)
        folder.mkdir(parents=True, exist_ok=True)
        target = (folder / core.safe_filename(package_name, fallback=f"{delivery_id}.zip")).resolve()
        if target.parent != folder:
            raise ControlledDeliveryError("DELIVERY_PATH_INVALID", "Ruta interna de paquete inválida.", 500)
        manifest_raw = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        manifest_sha = _sha256_bytes(manifest_raw)
        receipt = {
            "schema": "legalai_m36_3_availability_receipt_v1",
            "delivery_id": delivery_id,
            "case_id": case_id,
            "channel": "IN_APP",
            "prepared_at": manifest.get("prepared_at"),
            "document_count": len(files),
            "status": "PREPARED_FOR_CONTROLLED_DELIVERY",
            "download_confirmed": False,
            "external_delivery_confirmed": False,
        }
        readme = (
            "LegalAIZ.it — Entrega controlada\n\n"
            "Este paquete contiene únicamente las copias documentales liberadas sobre el hash aprobado por revisión jurídica y QA.\n"
            "La puesta a disposición se realiza dentro del expediente autenticado.\n"
            "La existencia del paquete no acredita que el usuario lo haya descargado, leído ni recibido por un canal externo.\n"
            "No constituye garantía de resultado jurídico ni representación judicial.\n"
        ).encode("utf-8")
        temporary = target.with_suffix(target.suffix + ".tmp")
        with ZipFile(temporary, "w") as archive:
            for name, body in sorted(files, key=lambda value: value[0]):
                archive.writestr(_zip_info(f"documentos_finales/{name}"), body)
            archive.writestr(_zip_info("MANIFEST.json"), manifest_raw)
            archive.writestr(
                _zip_info("CONSTANCIA_PUESTA_A_DISPOSICION.json"),
                json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"),
            )
            archive.writestr(_zip_info("LEEME.txt"), readme)
        temporary.replace(target)
        return target, _sha256_file(target), manifest_sha

    def _verify_package_row(self, row: Mapping[str, Any]) -> Path:
        target = Path(str(row.get("package_path") or "")).resolve()
        folder = self._package_dir(str(row["case_id"]), str(row["id"]))
        if target.parent != folder or not target.is_file():
            raise ControlledDeliveryError("DELIVERY_PACKAGE_MISSING", "El paquete controlado no está disponible.", 422)
        if _sha256_file(target) != str(row.get("package_sha256") or ""):
            raise ControlledDeliveryError("DELIVERY_PACKAGE_TAMPERED", "El paquete controlado cambió después de su preparación.", 422)
        try:
            with ZipFile(target) as archive:
                manifest_raw = archive.read("MANIFEST.json")
                if _sha256_bytes(manifest_raw) != str(row.get("manifest_sha256") or ""):
                    raise ControlledDeliveryError("DELIVERY_MANIFEST_TAMPERED", "El manifiesto del paquete no conserva su hash.", 422)
                manifest = json.loads(manifest_raw)
                if manifest.get("delivery_id") != row["id"] or manifest.get("case_id") != row["case_id"]:
                    raise ControlledDeliveryError("DELIVERY_MANIFEST_MISMATCH", "El manifiesto no corresponde al delivery registrado.", 422)
                for item in manifest.get("files") or []:
                    name = core.safe_filename(item.get("name"), fallback="")
                    if not name:
                        raise ControlledDeliveryError("DELIVERY_MANIFEST_INVALID", "El manifiesto contiene un nombre inválido.", 422)
                    body = archive.read(f"documentos_finales/{name}")
                    if _sha256_bytes(body) != str(item.get("sha256") or "") or len(body) != int(item.get("size_bytes") or -1):
                        raise ControlledDeliveryError("DELIVERY_FILE_TAMPERED", "Un documento del paquete no conserva su integridad.", 422)
        except ControlledDeliveryError:
            raise
        except Exception as exc:
            raise ControlledDeliveryError("DELIVERY_PACKAGE_INVALID", "El paquete controlado no puede verificarse.", 422) from exc
        return target

    def _verify_release_snapshot(self, actor: dict[str, Any], row: Mapping[str, Any]) -> None:
        try:
            expected = json.loads(row.get("release_snapshot_json") or "[]")
        except (TypeError, json.JSONDecodeError) as exc:
            raise ControlledDeliveryError("RELEASE_SNAPSHOT_INVALID", "El snapshot de liberaciones no puede verificarse.", 422) from exc
        if not isinstance(expected, list) or self._release_snapshot_sha(expected) != str(row.get("release_snapshot_sha256") or ""):
            raise ControlledDeliveryError("RELEASE_SNAPSHOT_TAMPERED", "El snapshot de liberaciones cambió.", 422)
        for item in expected:
            desk_id = _safe_id(item.get("desk_id"), "desk_id")
            try:
                source, release = self.workspace.released_path(actor, desk_id)
            except Exception as exc:
                raise ControlledDeliveryError("RELEASE_SOURCE_INVALID", "Una liberación fuente dejó de ser íntegra.", 422) from exc
            if (
                str(release.get("release_id") or "") != str(item.get("release_id") or "")
                or str(release.get("revision_id") or "") != str(item.get("revision_id") or "")
                or str(release.get("sha256") or "") != str(item.get("sha256") or "")
                or _sha256_file(source) != str(item.get("sha256") or "")
            ):
                raise ControlledDeliveryError("RELEASE_SNAPSHOT_DRIFT", "Las liberaciones actuales no coinciden con las preparadas para entrega.", 422)

    @staticmethod
    def _latest_delivery_transition(con, case_id: str) -> dict[str, Any] | None:
        row = con.execute(
            """SELECT * FROM m24_case_transition
               WHERE case_id=? AND to_state='ENTREGADO'
               ORDER BY created_at DESC,id DESC LIMIT 1""",
            (case_id,),
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _transition_matches_delivery(transition: Mapping[str, Any] | None, row: Mapping[str, Any]) -> bool:
        if not transition:
            return False
        try:
            evidence = json.loads(transition.get("evidence_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            return False
        return (
            transition.get("to_state") == "ENTREGADO"
            and evidence.get("source") == "m36_3_controlled_delivery"
            and evidence.get("delivery_id") == row.get("id")
            and evidence.get("package_sha256") == row.get("package_sha256")
            and int(evidence.get("release_count") or 0) == int(row.get("release_count") or 0)
        )

    def _finalize_after_m24(self, con, row: Mapping[str, Any], actor: Mapping[str, Any]) -> dict[str, Any]:
        transition = self._latest_delivery_transition(con, str(row["case_id"]))
        if not self._transition_matches_delivery(transition, row):
            raise ControlledDeliveryError("M24_DELIVERY_EVIDENCE_MISMATCH", "M24 no conserva la transición de entrega correspondiente a este paquete.", 422)
        now = core.now()
        con.execute(
            """UPDATE m36_controlled_delivery
               SET state=?,delivered_by=?,delivered_at=?,m24_transition_id=?,updated_at=? WHERE id=?""",
            (STATE_DELIVERED, str(actor.get("id") or row.get("prepared_by") or ""), transition["id"], now, now, row["id"]),
        )
        core.audit(
            con,
            str(actor.get("id") or row.get("prepared_by") or ""),
            "m36_controlled_delivery",
            row["id"],
            "delivered_in_app",
            {
                "case_id": row["case_id"],
                "package_sha256": row["package_sha256"],
                "release_count": int(row["release_count"]),
                "m24_transition_id": transition["id"],
                "channel": "IN_APP",
                "external_notification_sent": False,
            },
        )
        con.commit()
        updated = con.execute("SELECT * FROM m36_controlled_delivery WHERE id=?", (row["id"],)).fetchone()
        return dict(updated)

    def _prepare_new(
        self,
        con,
        actor: dict[str, Any],
        case: Mapping[str, Any],
        fulfillment: Mapping[str, Any],
        assignment: Mapping[str, Any],
        assessment: Mapping[str, Any],
    ) -> dict[str, Any]:
        delivery_id = "DLV-" + uuid.uuid4().hex[:14].upper()
        prepared_at = core.now()
        snapshot, files = self._collect_releases(actor, str(case["id"]), assessment)
        snapshot_sha = self._release_snapshot_sha(snapshot)
        manifest = self._public_manifest(delivery_id, case, snapshot, prepared_at)
        package_name = core.safe_filename(
            f"LegalAIZit_{case['id']}_entrega_controlada_{delivery_id}.zip",
            fallback=f"{delivery_id}.zip",
        )
        target, package_sha, manifest_sha = self._write_package(
            case_id=str(case["id"]),
            delivery_id=delivery_id,
            package_name=package_name,
            manifest=manifest,
            files=files,
        )
        now = core.now()
        try:
            con.execute(
                """INSERT INTO m36_controlled_delivery(
                     id,case_id,owner_id,product_code,fulfillment_intake_id,assignment_id,state,
                     package_name,package_path,package_sha256,manifest_sha256,release_snapshot_json,
                     release_snapshot_sha256,release_count,prepared_by,prepared_at,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?, ?,?,?,?,?, ?,?,?,?,?,?)""",
                (
                    delivery_id,
                    case["id"],
                    case["owner_id"],
                    case["product_code"],
                    fulfillment["id"],
                    assignment["id"],
                    STATE_PREPARED,
                    package_name,
                    str(target),
                    package_sha,
                    manifest_sha,
                    _canonical_json(snapshot),
                    snapshot_sha,
                    len(snapshot),
                    actor["id"],
                    prepared_at,
                    now,
                    now,
                ),
            )
            core.audit(
                con,
                actor["id"],
                "m36_controlled_delivery",
                delivery_id,
                "delivery_prepared",
                {
                    "case_id": case["id"],
                    "release_count": len(snapshot),
                    "package_sha256": package_sha,
                    "channel": "IN_APP",
                },
            )
            con.commit()
        except Exception:
            # Una carrera puede haber insertado el UNIQUE(case_id). Si existe un
            # delivery concurrente, se conserva ese ledger y se elimina sólo el
            # paquete huérfano de este intento.
            existing = self._row(con, str(case["id"]))
            if existing:
                try:
                    target.unlink(missing_ok=True)
                except OSError:
                    pass
                return existing
            raise
        row = con.execute("SELECT * FROM m36_controlled_delivery WHERE id=?", (delivery_id,)).fetchone()
        return dict(row)

    def deliver(self, actor: dict[str, Any], case_id: str, confirmation: str) -> dict[str, Any]:
        self._require_admin(actor)
        case_id = _safe_id(case_id, "case_id")
        if str(confirmation or "").strip() != DELIVERY_CONFIRMATION:
            raise ControlledDeliveryError(
                "DELIVERY_CONFIRMATION_REQUIRED",
                f"Para entregar debe escribir exactamente: {DELIVERY_CONFIRMATION}",
                422,
            )
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            existing = self._row(con, case_id)
            if existing:
                self._verify_package_row(existing)
                self._verify_release_snapshot(actor, existing)
                if existing["state"] == STATE_DELIVERED:
                    transition = self._latest_delivery_transition(con, case_id)
                    if not self._transition_matches_delivery(transition, existing):
                        raise ControlledDeliveryError("M24_DELIVERY_EVIDENCE_MISMATCH", "La entrega registrada no coincide con M24.", 422)
                    return self._public(existing, con, idempotent=True)
                if existing["state"] != STATE_PREPARED:
                    raise ControlledDeliveryError("DELIVERY_STATE_INVALID", "Estado interno de entrega inválido.", 422)
                journey = self.journey.detail(con, case_id, actor)
                if journey.get("current_state") == "ENTREGADO":
                    finalized = self._finalize_after_m24(con, existing, actor)
                    return self._public(finalized, con, idempotent=True)
                if journey.get("current_state") != "APROBADO_QA":
                    raise ControlledDeliveryError("M24_DELIVERY_STATE_INVALID", "El journey cambió después de preparar la entrega.", 422)
                row = existing
            else:
                case, fulfillment, assignment, assessment = self._preflight(actor, case_id, con)
                row = self._prepare_new(con, actor, case, fulfillment, assignment, assessment)
                self._verify_package_row(row)
                self._verify_release_snapshot(actor, row)

            evidence = {
                "source": "m36_3_controlled_delivery",
                "delivery_id": row["id"],
                "package_sha256": row["package_sha256"],
                "manifest_sha256": row["manifest_sha256"],
                "release_snapshot_sha256": row["release_snapshot_sha256"],
                "release_count": int(row["release_count"]),
                "channel": "IN_APP",
                "download_confirmed": False,
                "external_notification_sent": False,
            }
            self.journey.transition(
                con,
                case_id,
                "ENTREGADO",
                "Todos los documentos fueron liberados sobre el hash aprobado y se ponen a disposición del titular en su expediente autenticado.",
                evidence,
                DELIVERY_CONFIRMATION,
                actor,
            )
            refreshed = self._row(con, case_id)
            if not refreshed:
                raise ControlledDeliveryError("DELIVERY_LEDGER_MISSING", "La entrega preparada dejó de estar registrada.", 500)
            finalized = self._finalize_after_m24(con, refreshed, actor)
            return self._public(finalized, con, idempotent=False)
        finally:
            con.close()

    def _authorize_read(self, con, actor: Mapping[str, Any], case_id: str) -> dict[str, Any]:
        case = self._case(con, case_id)
        role = str(actor.get("role") or "")
        actor_id = str(actor.get("id") or "")
        if role == "admin":
            return case
        if role == "client" and actor_id and actor_id == str(case.get("owner_id") or ""):
            return case
        raise PermissionDenied("La entrega no existe o no está dentro del alcance del usuario.")

    def detail(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            self._authorize_read(con, actor, case_id)
            row = self._row(con, case_id)
            if not row or row["state"] != STATE_DELIVERED:
                raise ControlledDeliveryError("DELIVERY_NOT_AVAILABLE", "La entrega controlada todavía no está disponible.", 404)
            self._verify_package_row(row)
            return self._public(row, con, idempotent=True)
        finally:
            con.close()

    def download(self, actor: dict[str, Any], case_id: str) -> tuple[Path, str, dict[str, Any]]:
        case_id = _safe_id(case_id, "case_id")
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            self._authorize_read(con, actor, case_id)
            row = self._row(con, case_id)
            if not row or row["state"] != STATE_DELIVERED:
                raise ControlledDeliveryError("DELIVERY_NOT_AVAILABLE", "La entrega controlada todavía no está disponible.", 404)
            target = self._verify_package_row(row)
            # Para un cliente no usamos workspace.released_path(), porque M32.5
            # restringe su workspace a profesionales. La integridad post-entrega
            # se acredita por el paquete inmutable + snapshot fuente registrado.
            event_id = "DLA-" + uuid.uuid4().hex[:14].upper()
            now = core.now()
            con.execute(
                """INSERT INTO m36_delivery_access_event(
                     id,delivery_id,actor_id,actor_role,action,package_sha256,created_at
                   ) VALUES(?,?,?,?,?,?,?)""",
                (event_id, row["id"], actor["id"], actor["role"], DOWNLOAD_ACTION, row["package_sha256"], now),
            )
            core.audit(
                con,
                actor["id"],
                "m36_controlled_delivery",
                row["id"],
                "download_requested",
                {"case_id": case_id, "package_sha256": row["package_sha256"], "channel": "IN_APP"},
            )
            con.commit()
            return target, str(row["package_name"]), self._public(row, con, idempotent=True)
        finally:
            con.close()

    def queue(self, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            rows = [dict(row) for row in con.execute(
                "SELECT * FROM m36_controlled_delivery ORDER BY created_at DESC,id DESC"
            ).fetchall()]
            return {
                "schema": "legalai_m36_3_delivery_queue_v1",
                "schema_version": SCHEMA_VERSION,
                "items": [self._public(row, con, idempotent=True, compact=True) for row in rows],
                "metrics": {
                    "cases": len(rows),
                    "prepared": sum(row["state"] == STATE_PREPARED for row in rows),
                    "delivered_in_app": sum(row["state"] == STATE_DELIVERED for row in rows),
                },
                "notice": "DELIVERED_IN_APP significa puesta a disposición en el expediente autenticado; no acredita descarga, lectura ni recepción externa.",
            }
        finally:
            con.close()

    @staticmethod
    def _access_metrics(con, delivery_id: str) -> tuple[int, str | None, str | None]:
        row = con.execute(
            """SELECT COUNT(*) AS total,MIN(created_at) AS first_at,MAX(created_at) AS last_at
               FROM m36_delivery_access_event WHERE delivery_id=? AND action=?""",
            (delivery_id, DOWNLOAD_ACTION),
        ).fetchone()
        if not row:
            return 0, None, None
        return int(row["total"] or 0), row["first_at"], row["last_at"]

    @classmethod
    def _public(cls, row: Mapping[str, Any], con, *, idempotent: bool, compact: bool = False) -> dict[str, Any]:
        requests, first_at, last_at = cls._access_metrics(con, str(row["id"]))
        payload = {
            "schema": "legalai_m36_3_controlled_delivery_v1",
            "schema_version": SCHEMA_VERSION,
            "delivery_id": row["id"],
            "case_id": row["case_id"],
            "product_code": row["product_code"],
            "state": row["state"],
            "delivery_channel": "IN_APP",
            "document_count": int(row["release_count"]),
            "package_name": row["package_name"],
            "package_sha256": row["package_sha256"],
            "manifest_sha256": row["manifest_sha256"],
            "prepared_at": row["prepared_at"],
            "delivered_at": row.get("delivered_at"),
            "download_requests": requests,
            "first_download_requested_at": first_at,
            "last_download_requested_at": last_at,
            "download_url": f"/api/m36/delivery/cases/{row['case_id']}/download" if row["state"] == STATE_DELIVERED else None,
            "idempotent": bool(idempotent),
            "governance": {
                "source_is_m32_released_exact_hash": True,
                "dual_human_approval_preserved": True,
                "automatic_legal_approval": False,
                "automatic_qa_approval": False,
                "external_notification_sent": False,
                "download_request_is_not_receipt_confirmation": True,
                "delivery_state_means_in_app_availability": True,
            },
        }
        if compact:
            payload.pop("download_url", None)
        return payload


__all__ = [
    "ControlledDeliveryCenter",
    "ControlledDeliveryError",
    "SCHEMA_VERSION",
    "DELIVERY_CONFIRMATION",
    "STATE_PREPARED",
    "STATE_DELIVERED",
]
