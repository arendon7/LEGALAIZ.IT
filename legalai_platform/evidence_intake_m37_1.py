from __future__ import annotations

"""M37.1 — controlled evidence intake and review boundary.

The layer accepts support files only for an ACTIVE M37.0 follow-up task. Files
are immutable, malware-scanned and hash-checked. A professional review records
an intake disposition but deliberately does not verify authenticity, legal
sufficiency, legal effect, authority receipt, deadline compliance or task
completion.
"""

from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping
import uuid
from zipfile import BadZipFile, ZipFile

import core_v11 as core
from legalai_platform.approval_desk_workspace import PermissionDenied
from legalai_platform.post_delivery_followup_m37_0 import PostDeliveryFollowUpCenter


SCHEMA_VERSION = "37.1.0"
STATE_RECEIVED = "RECEIVED"
REVIEW_DISPOSITIONS = frozenset({
    "ACKNOWLEDGED_FOR_FOLLOWUP",
    "NEEDS_CLARIFICATION",
    "NOT_RELEVANT_TO_TASK",
})


class EvidenceIntakeError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_id(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 120 or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise EvidenceIntakeError("IDENTIFIER_INVALID", f"{field} inválido.", 400)
    return text


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class EvidenceIntakeCenter:
    """Immutable evidence files plus append-only professional intake reviews."""

    def __init__(
        self,
        followup: PostDeliveryFollowUpCenter,
        malware_scanner,
        *,
        db_factory=None,
        evidence_root: str | Path | None = None,
        contract_path: str | Path | None = None,
    ):
        self.followup = followup
        self.malware_scanner = malware_scanner
        self.db_factory = db_factory or core.db
        self.evidence_root = Path(evidence_root or (core.RUNTIME / "m37-evidence")).resolve()
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self.contract_path = Path(contract_path or (core.ROOT / "config" / "m37" / "evidence_contracts.json"))
        self.contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        self.validate_contract()

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m37_evidence_item(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              follow_up_id TEXT NOT NULL,
              uploader_id TEXT NOT NULL,
              uploader_role TEXT NOT NULL,
              original_name TEXT NOT NULL,
              stored_name TEXT NOT NULL,
              file_path TEXT NOT NULL,
              file_kind TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              sha256 TEXT NOT NULL,
              scan_status TEXT NOT NULL,
              scan_engine TEXT NOT NULL,
              state TEXT NOT NULL CHECK(state='RECEIVED'),
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m37_evidence_case
              ON m37_evidence_item(case_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_m37_evidence_task
              ON m37_evidence_item(case_id,follow_up_id,created_at);
            CREATE TABLE IF NOT EXISTS m37_evidence_review(
              id TEXT PRIMARY KEY,
              evidence_id TEXT NOT NULL,
              case_id TEXT NOT NULL,
              reviewer_id TEXT NOT NULL,
              reviewer_role TEXT NOT NULL,
              disposition TEXT NOT NULL CHECK(disposition IN (
                'ACKNOWLEDGED_FOR_FOLLOWUP','NEEDS_CLARIFICATION','NOT_RELEVANT_TO_TASK'
              )),
              message_to_client TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m37_evidence_review_item
              ON m37_evidence_review(evidence_id,created_at,id);
            """
        )

    def validate_contract(self) -> dict[str, Any]:
        payload = self.contract
        if payload.get("schema") != "legalai_m37_1_evidence_contracts_v1":
            raise EvidenceIntakeError("EVIDENCE_CONTRACT_INVALID", "M37.1 usa un contrato de evidencia desconocido.", 500)
        if int(payload.get("max_file_bytes") or 0) != int(core.MAX_UPLOAD):
            raise EvidenceIntakeError("EVIDENCE_SIZE_POLICY_DRIFT", "M37.1 debe respetar el límite canónico de carga.", 500)
        if set(payload.get("review_dispositions") or []) != set(REVIEW_DISPOSITIONS):
            raise EvidenceIntakeError("EVIDENCE_REVIEW_POLICY_DRIFT", "Las disposiciones M37.1 no coinciden con el contrato.", 500)
        allowed = payload.get("allowed_types") or {}
        if set(allowed) != {"PDF", "PNG", "JPEG", "DOCX", "TEXT"}:
            raise EvidenceIntakeError("EVIDENCE_TYPE_POLICY_INVALID", "El conjunto de tipos M37.1 no es el esperado.", 500)
        governance = payload.get("governance") or {}
        false_keys = {
            "upload_completes_task",
            "review_completes_task",
            "authenticity_verified_by_upload",
            "authenticity_verified_by_review",
            "legal_sufficiency_verified_by_review",
            "legal_effect_verified_by_review",
            "automatic_close",
            "automatic_escalation",
        }
        if any(governance.get(key) is not False for key in false_keys):
            raise EvidenceIntakeError("EVIDENCE_GOVERNANCE_INVALID", "M37.1 no puede convertir recepción o revisión en una conclusión jurídica.", 500)
        if governance.get("immutable_files") is not True or governance.get("append_only_reviews") is not True:
            raise EvidenceIntakeError("EVIDENCE_IMMUTABILITY_REQUIRED", "M37.1 exige archivos inmutables y revisiones append-only.", 500)
        return {"valid": True, "types": len(allowed), "max_file_bytes": int(payload["max_file_bytes"])}

    def _allowed_by_extension(self, filename: str) -> tuple[str, dict[str, Any]]:
        suffix = Path(str(filename or "")).suffix.casefold()
        for kind, spec in (self.contract.get("allowed_types") or {}).items():
            if suffix in {str(item).casefold() for item in (spec.get("extensions") or [])}:
                return str(kind), dict(spec)
        raise EvidenceIntakeError(
            "EVIDENCE_TYPE_NOT_ALLOWED",
            "El soporte debe ser PDF, PNG, JPG/JPEG, DOCX o TXT.",
            415,
        )

    @staticmethod
    def _validate_docx(data: bytes) -> None:
        try:
            with ZipFile(BytesIO(data)) as archive:
                infos = archive.infolist()
                if not infos or len(infos) > 1000:
                    raise EvidenceIntakeError("EVIDENCE_DOCX_INVALID", "El DOCX tiene una estructura no permitida.", 422)
                names = {item.filename.replace("\\", "/") for item in infos}
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise EvidenceIntakeError("EVIDENCE_DOCX_INVALID", "El archivo no corresponde a un DOCX válido.", 422)
                total = 0
                for item in infos:
                    name = item.filename.replace("\\", "/")
                    parts = [part for part in name.split("/") if part]
                    if name.startswith("/") or ".." in parts:
                        raise EvidenceIntakeError("EVIDENCE_DOCX_PATH_INVALID", "El DOCX contiene rutas internas no permitidas.", 422)
                    total += int(item.file_size or 0)
                    lowered = name.casefold()
                    if lowered.endswith("vbaproject.bin") or "/embeddings/" in f"/{lowered}":
                        raise EvidenceIntakeError("EVIDENCE_DOCX_ACTIVE_CONTENT", "El DOCX contiene contenido activo o embebido no permitido.", 422)
                if total > 50 * 1024 * 1024:
                    raise EvidenceIntakeError("EVIDENCE_DOCX_EXPANSION_LIMIT", "El DOCX supera el límite seguro de contenido expandido.", 422)
        except BadZipFile as exc:
            raise EvidenceIntakeError("EVIDENCE_DOCX_INVALID", "El archivo no corresponde a un DOCX válido.", 422) from exc

    def _validate_file(self, filename: str, data: bytes) -> tuple[str, str, str]:
        if not isinstance(data, (bytes, bytearray)):
            raise EvidenceIntakeError("EVIDENCE_FILE_INVALID", "No se recibió un archivo binario válido.", 400)
        body = bytes(data)
        if not body:
            raise EvidenceIntakeError("EVIDENCE_FILE_EMPTY", "El soporte está vacío.", 400)
        if len(body) > int(self.contract["max_file_bytes"]):
            raise EvidenceIntakeError("EVIDENCE_FILE_TOO_LARGE", "El soporte supera el límite de 10 MB.", 413)
        original = Path(str(filename or "soporte")).name
        safe = core.safe_filename(original, fallback="soporte")
        kind, spec = self._allowed_by_extension(original)
        if kind == "PDF":
            if not body.startswith(b"%PDF-"):
                raise EvidenceIntakeError("EVIDENCE_SIGNATURE_MISMATCH", "El archivo .pdf no tiene una firma PDF válida.", 422)
        elif kind == "PNG":
            if not body.startswith(b"\x89PNG\r\n\x1a\n"):
                raise EvidenceIntakeError("EVIDENCE_SIGNATURE_MISMATCH", "El archivo .png no tiene una firma PNG válida.", 422)
        elif kind == "JPEG":
            if not body.startswith(b"\xff\xd8\xff"):
                raise EvidenceIntakeError("EVIDENCE_SIGNATURE_MISMATCH", "El archivo JPG/JPEG no tiene una firma válida.", 422)
        elif kind == "DOCX":
            self._validate_docx(body)
        elif kind == "TEXT":
            if b"\x00" in body:
                raise EvidenceIntakeError("EVIDENCE_TEXT_INVALID", "El TXT contiene bytes nulos no permitidos.", 422)
            try:
                body.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise EvidenceIntakeError("EVIDENCE_TEXT_ENCODING", "El TXT debe estar codificado en UTF-8.", 422) from exc
        return kind, str(spec["mime_type"]), safe

    def _followup_context(self, con, actor: Mapping[str, Any], case_id: str, *, writable: bool) -> tuple[dict[str, Any], dict[str, Any]]:
        self.followup.ensure_schema(con)
        self.ensure_schema(con)
        case = self.followup._require_access(con, case_id, actor)
        self.followup._delivery(con, case_id)
        enrollment = self.followup._enrollment(con, case_id)
        if not enrollment or str(enrollment.get("state") or "") != "ACTIVE":
            raise EvidenceIntakeError("EVIDENCE_FOLLOWUP_NOT_ACTIVE", "M37.1 requiere un seguimiento M37.0 activo.", 409)
        integrity = self.followup.verify_chain(con, case_id)
        if not integrity.get("valid"):
            raise EvidenceIntakeError("EVIDENCE_FOLLOWUP_AUDIT_INVALID", "La cadena M37 está alterada.", 422)
        if writable:
            journey = self.followup.journey.detail(con, case_id, dict(actor))
            if str(journey.get("current_state") or "") != "EN_SEGUIMIENTO":
                raise EvidenceIntakeError("EVIDENCE_FOLLOWUP_READ_ONLY", "El expediente ya no admite nuevos soportes o revisiones en M37.1.", 409)
        return case, enrollment

    def _task(self, con, case_id: str, follow_up_id: str, enrollment: Mapping[str, Any]) -> dict[str, Any]:
        if follow_up_id not in self.followup._task_ids(enrollment):
            raise EvidenceIntakeError("EVIDENCE_TASK_NOT_AVAILABLE", "La actividad no pertenece al seguimiento M37.0.", 404)
        row = con.execute(
            "SELECT id,action_label,status FROM m24_case_follow_up WHERE id=? AND case_id=?",
            (follow_up_id, case_id),
        ).fetchone()
        if not row:
            raise EvidenceIntakeError("EVIDENCE_TASK_NOT_AVAILABLE", "La actividad no está disponible.", 404)
        value = dict(row)
        contracts = self.followup._task_contracts(str(enrollment.get("product_code") or ""))
        if str(value.get("action_label") or "") not in contracts:
            raise EvidenceIntakeError("EVIDENCE_TASK_DRIFT", "La actividad dejó de coincidir con el contrato M37.", 422)
        return value

    @staticmethod
    def _item(con, case_id: str, evidence_id: str) -> dict[str, Any]:
        row = con.execute(
            "SELECT * FROM m37_evidence_item WHERE id=? AND case_id=?",
            (evidence_id, case_id),
        ).fetchone()
        if not row:
            raise EvidenceIntakeError("EVIDENCE_NOT_AVAILABLE", "El soporte no está disponible.", 404)
        return dict(row)

    def _path(self, row: Mapping[str, Any]) -> Path:
        target = Path(str(row.get("file_path") or "")).resolve()
        if target == self.evidence_root or self.evidence_root not in target.parents:
            raise EvidenceIntakeError("EVIDENCE_PATH_INVALID", "La ruta interna del soporte no es válida.", 422)
        if not target.is_file():
            raise EvidenceIntakeError("EVIDENCE_FILE_MISSING", "El soporte almacenado ya no está disponible.", 422)
        if target.is_symlink():
            raise EvidenceIntakeError("EVIDENCE_PATH_INVALID", "El soporte no puede ser un enlace simbólico.", 422)
        return target

    def _verify_file(self, row: Mapping[str, Any]) -> Path:
        target = self._path(row)
        if target.stat().st_size != int(row.get("size_bytes") or -1):
            raise EvidenceIntakeError("EVIDENCE_FILE_TAMPERED", "El tamaño del soporte ya no coincide con el registro de recepción.", 422)
        if _sha256_file(target) != str(row.get("sha256") or ""):
            raise EvidenceIntakeError("EVIDENCE_FILE_TAMPERED", "El soporte ya no coincide con el hash registrado.", 422)
        return target

    def _write_immutable(self, case_id: str, evidence_id: str, safe_name: str, data: bytes) -> Path:
        folder = (self.evidence_root / _safe_id(case_id, "case_id") / _safe_id(evidence_id, "evidence_id")).resolve()
        if self.evidence_root not in folder.parents:
            raise EvidenceIntakeError("EVIDENCE_PATH_INVALID", "No fue posible construir una ruta segura para el soporte.", 422)
        folder.mkdir(parents=True, exist_ok=False)
        try:
            os.chmod(folder, 0o700)
        except OSError:
            pass
        target = (folder / safe_name).resolve()
        if target.parent != folder:
            raise EvidenceIntakeError("EVIDENCE_PATH_INVALID", "El nombre del soporte no es seguro.", 422)
        temp = folder / ".upload.tmp"
        try:
            with temp.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, target)
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
            return target
        except Exception:
            temp.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            try:
                folder.rmdir()
            except OSError:
                pass
            raise

    @staticmethod
    def _latest_review(con, evidence_id: str) -> dict[str, Any] | None:
        row = con.execute(
            """SELECT * FROM m37_evidence_review WHERE evidence_id=?
               ORDER BY created_at DESC,id DESC LIMIT 1""",
            (evidence_id,),
        ).fetchone()
        return dict(row) if row else None

    def _public_item(self, con, row: Mapping[str, Any]) -> dict[str, Any]:
        self._verify_file(row)
        review = self._latest_review(con, str(row.get("id") or ""))
        review_count = int(con.execute(
            "SELECT COUNT(*) FROM m37_evidence_review WHERE evidence_id=?",
            (str(row.get("id") or ""),),
        ).fetchone()[0])
        if review:
            review_public = {
                "status": "REVIEWED_FOR_INTAKE",
                "disposition": str(review.get("disposition") or ""),
                "message_to_client": str(review.get("message_to_client") or ""),
                "reviewer_role": str(review.get("reviewer_role") or ""),
                "reviewed_at": str(review.get("created_at") or ""),
                "authenticity_verified": False,
                "legal_sufficiency_verified": False,
                "legal_effect_verified": False,
            }
        else:
            review_public = {
                "status": "PENDING_REVIEW",
                "disposition": None,
                "message_to_client": "",
                "reviewer_role": None,
                "reviewed_at": None,
                "authenticity_verified": False,
                "legal_sufficiency_verified": False,
                "legal_effect_verified": False,
            }
        scan_status = str(row.get("scan_status") or "")
        return {
            "evidence_id": str(row.get("id") or ""),
            "follow_up_id": str(row.get("follow_up_id") or ""),
            "filename": str(row.get("original_name") or ""),
            "file_kind": str(row.get("file_kind") or ""),
            "mime_type": str(row.get("mime_type") or ""),
            "size_bytes": int(row.get("size_bytes") or 0),
            "state": STATE_RECEIVED,
            "uploaded_by_role": str(row.get("uploader_role") or ""),
            "uploaded_at": str(row.get("created_at") or ""),
            "security_scan": {
                "status": scan_status,
                "external_scan_completed": scan_status == "clean",
                "local_demo_unscanned": scan_status == "not_scanned_local",
            },
            "integrity": {"stored_file_intact": True},
            "review": review_public,
            "review_count": review_count,
            "download_url": f"/api/m37/evidence/cases/{row.get('case_id')}/items/{row.get('id')}/download",
            "governance": {
                "upload_completed_task": False,
                "review_completed_task": False,
                "authenticity_verified": False,
                "legal_sufficiency_verified": False,
                "legal_effect_verified": False,
            },
        }

    def upload(
        self,
        actor: dict[str, Any],
        case_id: str,
        follow_up_id: str,
        filename: str,
        data: bytes,
        claimed_content_type: str = "",
    ) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        follow_up_id = _safe_id(follow_up_id, "follow_up_id")
        file_kind, mime_type, safe_name = self._validate_file(filename, data)
        try:
            scan = self.malware_scanner.scan(safe_name, bytes(data))
        except ValueError as exc:
            raise EvidenceIntakeError("EVIDENCE_MALWARE_BLOCKED", str(exc), 422) from exc
        except RuntimeError as exc:
            raise EvidenceIntakeError("EVIDENCE_SCAN_UNAVAILABLE", str(exc), 503) from exc
        evidence_id = f"EVD-{uuid.uuid4().hex[:16].upper()}"
        digest = _sha256_bytes(bytes(data))
        con = self.db_factory()
        target: Path | None = None
        try:
            case, enrollment = self._followup_context(con, actor, case_id, writable=True)
            task = self._task(con, case_id, follow_up_id, enrollment)
            before_status = str(task.get("status") or "")
            target = self._write_immutable(case_id, evidence_id, safe_name, bytes(data))
            if _sha256_file(target) != digest:
                raise EvidenceIntakeError("EVIDENCE_WRITE_INTEGRITY_FAILED", "El soporte no conservó el mismo hash al almacenarse.", 500)
            now = core.now()
            con.execute(
                """INSERT INTO m37_evidence_item
                   (id,case_id,follow_up_id,uploader_id,uploader_role,original_name,stored_name,file_path,file_kind,mime_type,
                    size_bytes,sha256,scan_status,scan_engine,state,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    evidence_id, case_id, follow_up_id, str(actor.get("id") or ""), str(actor.get("role") or ""),
                    Path(str(filename or safe_name)).name[:255], safe_name, str(target), file_kind, mime_type,
                    len(data), digest, str(scan.status), str(scan.engine), STATE_RECEIVED, now,
                ),
            )
            self.followup._append_event(
                con,
                case_id,
                "EVIDENCE_RECEIVED",
                actor,
                {
                    "evidence_id": evidence_id,
                    "follow_up_id": follow_up_id,
                    "file_kind": file_kind,
                    "size_bytes": len(data),
                    "evidence_sha256": digest,
                    "scan_status": str(scan.status),
                    "task_status_before": before_status,
                    "task_status_changed": False,
                    "authenticity_verified": False,
                    "legal_sufficiency_verified": False,
                    "legal_effect_verified": False,
                },
            )
            after = con.execute(
                "SELECT status FROM m24_case_follow_up WHERE id=? AND case_id=?",
                (follow_up_id, case_id),
            ).fetchone()
            if not after or str(after[0] or "") != before_status:
                raise EvidenceIntakeError("EVIDENCE_TASK_MUTATION_DETECTED", "La recepción del soporte alteró indebidamente la actividad de seguimiento.", 500)
            con.commit()
            row = self._item(con, case_id, evidence_id)
            result = self._public_item(con, row)
            result["claimed_content_type_trusted"] = False
            return result
        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            if target is not None:
                parent = target.parent
                target.unlink(missing_ok=True)
                try:
                    parent.rmdir()
                except OSError:
                    pass
            raise
        finally:
            con.close()

    @staticmethod
    def _require_reviewer(case: Mapping[str, Any], actor: Mapping[str, Any]) -> None:
        role = str(actor.get("role") or "")
        actor_id = str(actor.get("id") or "")
        if role == "admin" and actor_id:
            return
        if role == "specialist" and actor_id and actor_id == str(case.get("specialist_id") or ""):
            return
        raise PermissionDenied("La revisión de soportes requiere administración o el especialista asignado al expediente.")

    def review(
        self,
        actor: dict[str, Any],
        case_id: str,
        evidence_id: str,
        disposition: str,
        message_to_client: str = "",
    ) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        evidence_id = _safe_id(evidence_id, "evidence_id")
        disposition = str(disposition or "").strip().upper()
        if disposition not in REVIEW_DISPOSITIONS:
            raise EvidenceIntakeError("EVIDENCE_REVIEW_DISPOSITION_INVALID", "Disposición de revisión inválida.", 422)
        message = re.sub(r"[\r\n]+", " ", str(message_to_client or "")).strip()
        if len(message) > 1200:
            raise EvidenceIntakeError("EVIDENCE_REVIEW_MESSAGE_TOO_LONG", "El mensaje de revisión no puede superar 1.200 caracteres.", 422)
        if disposition in {"NEEDS_CLARIFICATION", "NOT_RELEVANT_TO_TASK"} and len(message) < 10:
            raise EvidenceIntakeError("EVIDENCE_REVIEW_MESSAGE_REQUIRED", "Esta disposición exige una explicación de al menos 10 caracteres.", 422)
        con = self.db_factory()
        try:
            case, enrollment = self._followup_context(con, actor, case_id, writable=True)
            self._require_reviewer(case, actor)
            row = self._item(con, case_id, evidence_id)
            self._task(con, case_id, str(row.get("follow_up_id") or ""), enrollment)
            self._verify_file(row)
            task_before = con.execute(
                "SELECT status FROM m24_case_follow_up WHERE id=? AND case_id=?",
                (str(row["follow_up_id"]), case_id),
            ).fetchone()[0]
            latest = self._latest_review(con, evidence_id)
            if latest and str(latest.get("disposition") or "") == disposition and str(latest.get("message_to_client") or "") == message:
                result = self._public_item(con, row)
                result["idempotent"] = True
                return result
            review_id = f"EVR-{uuid.uuid4().hex[:16].upper()}"
            now = core.now()
            con.execute(
                """INSERT INTO m37_evidence_review
                   (id,evidence_id,case_id,reviewer_id,reviewer_role,disposition,message_to_client,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (
                    review_id, evidence_id, case_id, str(actor.get("id") or ""), str(actor.get("role") or ""),
                    disposition, message, now,
                ),
            )
            self.followup._append_event(
                con,
                case_id,
                "EVIDENCE_REVIEW_RECORDED",
                actor,
                {
                    "evidence_id": evidence_id,
                    "follow_up_id": str(row.get("follow_up_id") or ""),
                    "review_id": review_id,
                    "disposition": disposition,
                    "message_present": bool(message),
                    "task_status_changed": False,
                    "authenticity_verified": False,
                    "legal_sufficiency_verified": False,
                    "legal_effect_verified": False,
                },
            )
            task_after = con.execute(
                "SELECT status FROM m24_case_follow_up WHERE id=? AND case_id=?",
                (str(row["follow_up_id"]), case_id),
            ).fetchone()[0]
            if str(task_after or "") != str(task_before or ""):
                raise EvidenceIntakeError("EVIDENCE_REVIEW_TASK_MUTATION_DETECTED", "La revisión del soporte alteró indebidamente la actividad.", 500)
            con.commit()
            result = self._public_item(con, row)
            result["idempotent"] = False
            return result
        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            raise
        finally:
            con.close()

    def detail(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        case_id = _safe_id(case_id, "case_id")
        con = self.db_factory()
        try:
            case, enrollment = self._followup_context(con, actor, case_id, writable=False)
            rows = [dict(row) for row in con.execute(
                "SELECT * FROM m37_evidence_item WHERE case_id=? ORDER BY created_at,id",
                (case_id,),
            ).fetchall()]
            items = [self._public_item(con, row) for row in rows]
            pending = sum(1 for item in items if item["review"]["status"] == "PENDING_REVIEW")
            clarification = sum(1 for item in items if item["review"].get("disposition") == "NEEDS_CLARIFICATION")
            return {
                "schema": "legalai_m37_1_evidence_intake_v1",
                "schema_version": SCHEMA_VERSION,
                "case_id": case_id,
                "product_code": str(case.get("product_code") or ""),
                "followup_enrollment_id": str(enrollment.get("id") or ""),
                "items": items,
                "metrics": {
                    "evidence_items": len(items),
                    "pending_review": pending,
                    "needs_clarification": clarification,
                },
                "notice": str(self.contract.get("notice") or ""),
                "governance": {
                    "files_immutable": True,
                    "reviews_append_only": True,
                    "upload_completes_task": False,
                    "review_completes_task": False,
                    "authenticity_verified": False,
                    "legal_sufficiency_verified": False,
                    "legal_effect_verified": False,
                    "automatic_close": False,
                    "automatic_escalation": False,
                },
            }
        finally:
            con.close()

    def download(self, actor: dict[str, Any], case_id: str, evidence_id: str) -> tuple[Path, str, dict[str, Any]]:
        case_id = _safe_id(case_id, "case_id")
        evidence_id = _safe_id(evidence_id, "evidence_id")
        con = self.db_factory()
        try:
            self._followup_context(con, actor, case_id, writable=False)
            row = self._item(con, case_id, evidence_id)
            target = self._verify_file(row)
            public = self._public_item(con, row)
            return target, core.safe_filename(str(row.get("original_name") or "soporte"), fallback="soporte"), public
        finally:
            con.close()


__all__ = [
    "EvidenceIntakeCenter",
    "EvidenceIntakeError",
    "REVIEW_DISPOSITIONS",
    "SCHEMA_VERSION",
]
