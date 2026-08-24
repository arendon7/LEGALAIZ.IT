from __future__ import annotations

"""M37.1 — controlled evidence intake and review boundary.

Support files are accepted only for an ACTIVE M37.0 task, scanned before
persistence and stored through the platform encrypted object store. A review is
an append-only intake classification, never a declaration of authenticity,
evidentiary sufficiency, authority receipt, deadline compliance, legal effect
or task completion.
"""

from hashlib import sha256
from io import BytesIO
import json
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


def _safe_id(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 120 or not re.fullmatch(r"[A-Za-z0-9._-]+", text):
        raise EvidenceIntakeError("IDENTIFIER_INVALID", f"{field} inválido.", 400)
    return text


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


class EvidenceIntakeCenter:
    """Encrypted immutable evidence objects plus append-only intake reviews."""

    def __init__(
        self,
        followup: PostDeliveryFollowUpCenter,
        malware_scanner,
        object_store,
        *,
        db_factory=None,
        contract_path: str | Path | None = None,
    ):
        self.followup = followup
        self.malware_scanner = malware_scanner
        self.object_store = object_store
        self.db_factory = db_factory or core.db
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
              file_kind TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              object_ref TEXT NOT NULL UNIQUE,
              plaintext_sha256 TEXT NOT NULL,
              scan_status TEXT NOT NULL,
              scan_engine TEXT NOT NULL,
              state TEXT NOT NULL CHECK(state='RECEIVED'),
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m37_evidence_case
              ON m37_evidence_item(case_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_m37_evidence_task
              ON m37_evidence_item(case_id,follow_up_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_m37_evidence_exact_retry
              ON m37_evidence_item(case_id,follow_up_id,original_name,plaintext_sha256,size_bytes);
            CREATE TABLE IF NOT EXISTS m37_evidence_review(
              id TEXT PRIMARY KEY,
              evidence_id TEXT NOT NULL,
              case_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              reviewer_id TEXT NOT NULL,
              reviewer_role TEXT NOT NULL,
              disposition TEXT NOT NULL CHECK(disposition IN (
                'ACKNOWLEDGED_FOR_FOLLOWUP','NEEDS_CLARIFICATION','NOT_RELEVANT_TO_TASK'
              )),
              message_to_client TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              UNIQUE(evidence_id,sequence)
            );
            CREATE INDEX IF NOT EXISTS idx_m37_evidence_review_item
              ON m37_evidence_review(evidence_id,sequence);
            """
        )

    def _ensure_schemas(self, con) -> None:
        self.followup.ensure_schema(con)
        self.ensure_schema(con)
        self.object_store.create_schema(con)

    def validate_contract(self) -> dict[str, Any]:
        payload = self.contract
        if payload.get("schema") != "legalai_m37_1_evidence_contracts_v1":
            raise EvidenceIntakeError("EVIDENCE_CONTRACT_INVALID", "M37.1 usa un contrato de evidencia desconocido.", 500)
        if int(payload.get("max_file_bytes") or 0) != int(core.MAX_UPLOAD):
            raise EvidenceIntakeError("EVIDENCE_SIZE_POLICY_DRIFT", "M37.1 debe respetar el límite canónico de carga.", 500)
        quotas = (
            int(payload.get("max_items_per_case") or 0),
            int(payload.get("max_items_per_task") or 0),
            int(payload.get("max_total_bytes_per_case") or 0),
        )
        if quotas[0] < 1 or quotas[1] < 1 or quotas[1] > quotas[0] or quotas[2] < int(payload["max_file_bytes"]):
            raise EvidenceIntakeError("EVIDENCE_QUOTA_POLICY_INVALID", "Las cuotas M37.1 no son coherentes.", 500)
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
        if governance.get("encrypted_object_store_required") is not True:
            raise EvidenceIntakeError("EVIDENCE_ENCRYPTION_REQUIRED", "M37.1 exige almacenamiento cifrado de objetos.", 500)
        if governance.get("immutable_files") is not True or governance.get("append_only_reviews") is not True:
            raise EvidenceIntakeError("EVIDENCE_IMMUTABILITY_REQUIRED", "M37.1 exige archivos inmutables y revisiones append-only.", 500)
        for method in ("create_schema", "put", "get", "is_reference"):
            if not callable(getattr(self.object_store, method, None)):
                raise EvidenceIntakeError("EVIDENCE_OBJECT_STORE_INVALID", "El object store M37.1 no implementa el contrato cifrado requerido.", 500)
        return {
            "valid": True,
            "types": len(allowed),
            "max_file_bytes": int(payload["max_file_bytes"]),
            "max_items_per_case": quotas[0],
            "max_items_per_task": quotas[1],
            "max_total_bytes_per_case": quotas[2],
        }

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

    def _validate_file(self, filename: str, data: bytes) -> tuple[str, str, str, bytes]:
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
        return kind, str(spec["mime_type"]), safe, body

    def _followup_context(self, con, actor: Mapping[str, Any], case_id: str, *, writable: bool) -> tuple[dict[str, Any], dict[str, Any]]:
        self._ensure_schemas(con)
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

    def _check_quota(self, con, case_id: str, follow_up_id: str, incoming_bytes: int) -> None:
        case_count = int(con.execute("SELECT COUNT(*) FROM m37_evidence_item WHERE case_id=?", (case_id,)).fetchone()[0])
        task_count = int(con.execute(
            "SELECT COUNT(*) FROM m37_evidence_item WHERE case_id=? AND follow_up_id=?",
            (case_id, follow_up_id),
        ).fetchone()[0])
        total_bytes = int(con.execute(
            "SELECT COALESCE(SUM(size_bytes),0) FROM m37_evidence_item WHERE case_id=?",
            (case_id,),
        ).fetchone()[0])
        if case_count >= int(self.contract["max_items_per_case"]):
            raise EvidenceIntakeError("EVIDENCE_CASE_ITEM_QUOTA", "El expediente alcanzó el máximo de soportes admitidos en M37.1.", 409)
        if task_count >= int(self.contract["max_items_per_task"]):
            raise EvidenceIntakeError("EVIDENCE_TASK_ITEM_QUOTA", "La actividad alcanzó el máximo de soportes admitidos en M37.1.", 409)
        if total_bytes + int(incoming_bytes) > int(self.contract["max_total_bytes_per_case"]):
            raise EvidenceIntakeError("EVIDENCE_CASE_BYTES_QUOTA", "El expediente alcanzó el límite total de almacenamiento de soportes.", 409)

    @staticmethod
    def _item(con, case_id: str, evidence_id: str) -> dict[str, Any]:
        row = con.execute("SELECT * FROM m37_evidence_item WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
        if not row:
            raise EvidenceIntakeError("EVIDENCE_NOT_AVAILABLE", "El soporte no está disponible.", 404)
        return dict(row)

    @staticmethod
    def _exact_retry(con, case_id: str, follow_up_id: str, original_name: str, digest: str, size_bytes: int) -> dict[str, Any] | None:
        row = con.execute(
            """SELECT * FROM m37_evidence_item
               WHERE case_id=? AND follow_up_id=? AND original_name=? AND plaintext_sha256=? AND size_bytes=?
               ORDER BY created_at,id LIMIT 1""",
            (case_id, follow_up_id, original_name, digest, int(size_bytes)),
        ).fetchone()
        return dict(row) if row else None

    def _verify_content(self, con, row: Mapping[str, Any]) -> bytes:
        reference = str(row.get("object_ref") or "")
        if not reference or not self.object_store.is_reference(reference):
            raise EvidenceIntakeError("EVIDENCE_OBJECT_REFERENCE_INVALID", "La referencia cifrada del soporte es inválida.", 422)
        try:
            data = self.object_store.get(con, reference)
        except FileNotFoundError as exc:
            raise EvidenceIntakeError("EVIDENCE_OBJECT_MISSING", "El objeto cifrado ya no está disponible.", 422) from exc
        except (ValueError, RuntimeError) as exc:
            raise EvidenceIntakeError("EVIDENCE_OBJECT_TAMPERED", "El objeto cifrado no superó la verificación de integridad.", 422) from exc
        if len(data) != int(row.get("size_bytes") or -1) or _sha256_bytes(data) != str(row.get("plaintext_sha256") or ""):
            raise EvidenceIntakeError("EVIDENCE_OBJECT_TAMPERED", "El contenido descifrado no coincide con el registro M37.1.", 422)
        return data

    @staticmethod
    def _latest_review(con, evidence_id: str) -> dict[str, Any] | None:
        row = con.execute(
            "SELECT * FROM m37_evidence_review WHERE evidence_id=? ORDER BY sequence DESC LIMIT 1",
            (evidence_id,),
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _next_review_sequence(con, evidence_id: str) -> int:
        return int(con.execute(
            "SELECT COALESCE(MAX(sequence),0)+1 FROM m37_evidence_review WHERE evidence_id=?",
            (evidence_id,),
        ).fetchone()[0])

    def _public_item(self, con, row: Mapping[str, Any]) -> dict[str, Any]:
        self._verify_content(con, row)
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
            "integrity": {"encrypted_at_rest": True, "stored_object_intact": True},
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
        con = self.db_factory()
        object_meta: dict[str, Any] | None = None
        try:
            case, enrollment = self._followup_context(con, actor, case_id, writable=True)
            task = self._task(con, case_id, follow_up_id, enrollment)
            file_kind, mime_type, safe_name, body = self._validate_file(filename, data)
            digest = _sha256_bytes(body)
            original_name = Path(str(filename or safe_name)).name[:255]
            existing = self._exact_retry(con, case_id, follow_up_id, original_name, digest, len(body))
            if existing:
                self._verify_content(con, existing)
                result = self._public_item(con, existing)
                result["claimed_content_type_trusted"] = False
                result["idempotent"] = True
                return result
            self._check_quota(con, case_id, follow_up_id, len(body))
            try:
                scan = self.malware_scanner.scan(safe_name, body)
            except ValueError as exc:
                raise EvidenceIntakeError("EVIDENCE_MALWARE_BLOCKED", str(exc), 422) from exc
            except RuntimeError as exc:
                raise EvidenceIntakeError("EVIDENCE_SCAN_UNAVAILABLE", str(exc), 503) from exc
            evidence_id = f"EVD-{uuid.uuid4().hex[:16].upper()}"
            object_meta = self.object_store.put(
                con,
                f"m37-evidence/{case_id}",
                original_name,
                body,
                mime_type,
                owner_id=str(case.get("owner_id") or ""),
            )
            if object_meta.get("plaintext_sha256") != digest or int(object_meta.get("size_bytes") or -1) != len(body):
                raise EvidenceIntakeError("EVIDENCE_OBJECT_WRITE_MISMATCH", "El object store no confirmó el mismo contenido recibido.", 500)
            before_status = str(task.get("status") or "")
            now = core.now()
            con.execute(
                """INSERT INTO m37_evidence_item
                   (id,case_id,follow_up_id,uploader_id,uploader_role,original_name,file_kind,mime_type,size_bytes,
                    object_ref,plaintext_sha256,scan_status,scan_engine,state,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    evidence_id, case_id, follow_up_id, str(actor.get("id") or ""), str(actor.get("role") or ""),
                    original_name, file_kind, mime_type, len(body), str(object_meta["reference"]), digest,
                    str(scan.status), str(scan.engine), STATE_RECEIVED, now,
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
                    "size_bytes": len(body),
                    "scan_status": str(scan.status),
                    "encrypted_at_rest": True,
                    "task_status_before": before_status,
                    "task_status_changed": False,
                    "authenticity_verified": False,
                    "legal_sufficiency_verified": False,
                    "legal_effect_verified": False,
                },
            )
            after = con.execute("SELECT status FROM m24_case_follow_up WHERE id=? AND case_id=?", (follow_up_id, case_id)).fetchone()
            if not after or str(after[0] or "") != before_status:
                raise EvidenceIntakeError("EVIDENCE_TASK_MUTATION_DETECTED", "La recepción del soporte alteró indebidamente la actividad de seguimiento.", 500)
            con.commit()
            row = self._item(con, case_id, evidence_id)
            result = self._public_item(con, row)
            result["claimed_content_type_trusted"] = False
            result["idempotent"] = False
            return result
        except Exception:
            try:
                con.rollback()
            except Exception:
                pass
            if object_meta and object_meta.get("stored_path"):
                try:
                    path = Path(str(object_meta["stored_path"])).resolve()
                    base = Path(getattr(self.object_store, "base", path.parent)).resolve()
                    if path.is_file() and (path.parent == base or base in path.parents):
                        path.unlink(missing_ok=True)
                except Exception:
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
            self._verify_content(con, row)
            task_before = con.execute("SELECT status FROM m24_case_follow_up WHERE id=? AND case_id=?", (str(row["follow_up_id"]), case_id)).fetchone()[0]
            latest = self._latest_review(con, evidence_id)
            if latest and str(latest.get("disposition") or "") == disposition and str(latest.get("message_to_client") or "") == message:
                result = self._public_item(con, row)
                result["idempotent"] = True
                return result
            sequence = self._next_review_sequence(con, evidence_id)
            review_id = f"EVR-{uuid.uuid4().hex[:16].upper()}"
            now = core.now()
            con.execute(
                """INSERT INTO m37_evidence_review
                   (id,evidence_id,case_id,sequence,reviewer_id,reviewer_role,disposition,message_to_client,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (review_id, evidence_id, case_id, sequence, str(actor.get("id") or ""), str(actor.get("role") or ""), disposition, message, now),
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
                    "review_sequence": sequence,
                    "disposition": disposition,
                    "message_present": bool(message),
                    "task_status_changed": False,
                    "authenticity_verified": False,
                    "legal_sufficiency_verified": False,
                    "legal_effect_verified": False,
                },
            )
            task_after = con.execute("SELECT status FROM m24_case_follow_up WHERE id=? AND case_id=?", (str(row["follow_up_id"]), case_id)).fetchone()[0]
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
            case, _enrollment = self._followup_context(con, actor, case_id, writable=False)
            rows = [dict(row) for row in con.execute("SELECT * FROM m37_evidence_item WHERE case_id=? ORDER BY created_at,id", (case_id,)).fetchall()]
            items = [self._public_item(con, row) for row in rows]
            pending = sum(1 for item in items if item["review"]["status"] == "PENDING_REVIEW")
            clarification = sum(1 for item in items if item["review"].get("disposition") == "NEEDS_CLARIFICATION")
            return {
                "schema": "legalai_m37_1_evidence_intake_v1",
                "schema_version": SCHEMA_VERSION,
                "case_id": case_id,
                "product_code": str(case.get("product_code") or ""),
                "items": items,
                "metrics": {
                    "evidence_items": len(items),
                    "total_bytes": sum(int(item.get("size_bytes") or 0) for item in items),
                    "pending_review": pending,
                    "needs_clarification": clarification,
                },
                "limits": {
                    "max_file_bytes": int(self.contract["max_file_bytes"]),
                    "max_items_per_case": int(self.contract["max_items_per_case"]),
                    "max_items_per_task": int(self.contract["max_items_per_task"]),
                    "max_total_bytes_per_case": int(self.contract["max_total_bytes_per_case"]),
                },
                "notice": str(self.contract.get("notice") or ""),
                "governance": {
                    "encrypted_object_store": True,
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

    def download(self, actor: dict[str, Any], case_id: str, evidence_id: str) -> tuple[bytes, str, str, dict[str, Any]]:
        case_id = _safe_id(case_id, "case_id")
        evidence_id = _safe_id(evidence_id, "evidence_id")
        con = self.db_factory()
        try:
            self._followup_context(con, actor, case_id, writable=False)
            row = self._item(con, case_id, evidence_id)
            data = self._verify_content(con, row)
            public = self._public_item(con, row)
            return data, core.safe_filename(str(row.get("original_name") or "soporte"), fallback="soporte"), str(row.get("mime_type") or "application/octet-stream"), public
        finally:
            con.close()


__all__ = ["EvidenceIntakeCenter", "EvidenceIntakeError", "REVIEW_DISPOSITIONS", "SCHEMA_VERSION"]
