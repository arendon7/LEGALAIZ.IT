from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping
import uuid

import core_v11 as core
from legalai_platform.approval_desk_operations import ApprovalDeskOperations, OperationsIntegrityError
from legalai_platform.approval_desk_workspace import ApprovalDeskError, ApprovalDeskWorkspace, PermissionDenied
from legalai_platform.case_activation_m35_3 import CaseActivationCenter, CaseActivationError


SCHEMA_VERSION = "36.0.0"
STATE_REVIEW_INTAKE = "EN_REVISION_JURIDICA"
REVIEW_PHASE_STATES = {
    "EN_REVISION_JURIDICA",
    "OBSERVADO",
    "CORREGIDO",
    "APROBADO_JURIDICAMENTE",
    "EN_QA",
    "APROBADO_QA",
    "ENTREGADO",
    "EN_SEGUIMIENTO",
    "CERRADO",
    "ESCALADO",
}
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class FulfillmentIntakeError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_case_id(value: Any) -> str:
    case_id = str(value or "").strip()
    if not case_id or len(case_id) > 80 or not re.fullmatch(r"[A-Za-z0-9._-]+", case_id):
        raise FulfillmentIntakeError("CASE_ID_INVALID", "Expediente inválido.", 400)
    return case_id


class FulfillmentIntakeCenter:
    """Exact bridge from a verified M35 case into the existing M32 review machinery.

    The bridge never approves, releases or assigns legal/QA reviewers. It performs
    one explicit administrative intake for one exact source case and records an
    idempotent database ledger after the M32 document desks are ready.
    """

    def __init__(
        self,
        activation: CaseActivationCenter,
        workspace: ApprovalDeskWorkspace,
        operations: ApprovalDeskOperations,
        journey,
        db_factory=None,
    ):
        self.activation = activation
        self.workspace = workspace
        self.operations = operations
        self.journey = journey
        self.db_factory = db_factory or core.db

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m36_fulfillment_intake(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL UNIQUE,
              owner_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              commerce_link_id TEXT NOT NULL,
              order_id TEXT NOT NULL,
              activation_sha256 TEXT NOT NULL,
              document_snapshot_sha256 TEXT NOT NULL,
              desk_case_ids_json TEXT NOT NULL,
              state TEXT NOT NULL,
              initiated_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_m36_fulfillment_order
              ON m36_fulfillment_intake(order_id);
            CREATE INDEX IF NOT EXISTS idx_m36_fulfillment_state
              ON m36_fulfillment_intake(state,updated_at);
            """
        )

    @staticmethod
    def _require_admin(actor: Mapping[str, Any]) -> None:
        if str(actor.get("role") or "") != "admin" or not str(actor.get("id") or "").strip():
            raise PermissionDenied("Solo administración puede activar el ingreso a fulfillment jurídico.")

    @staticmethod
    def _source_case(con, case_id: str):
        return con.execute(
            "SELECT id,product_code,owner_id,status,risk FROM cases WHERE id=?",
            (case_id,),
        ).fetchone()

    @staticmethod
    def _commerce_link(con, owner_id: str, case_id: str):
        table = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='m35_commerce_case_links'"
        ).fetchone()
        if not table:
            return None
        return con.execute(
            """SELECT id,order_id,case_id,product_code,state FROM m35_commerce_case_links
               WHERE user_id=? AND case_id=? ORDER BY created_at DESC LIMIT 1""",
            (owner_id, case_id),
        ).fetchone()

    @staticmethod
    def _documents(con, case_id: str) -> list[dict[str, Any]]:
        rows = con.execute(
            """SELECT id,case_id,product_code,kind,name,mime_type,file_path,version,status
               FROM documents WHERE case_id=? AND kind!='audit' ORDER BY id""",
            (case_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _activation_fingerprint(activation: Mapping[str, Any], link_id: str) -> str:
        case = activation.get("case") or {}
        purchase = activation.get("purchase_confirmation") or {}
        documents = activation.get("documents") or {}
        return _canonical_sha256(
            {
                "case_id": case.get("id"),
                "product_code": case.get("product_code"),
                "commerce_link_id": link_id,
                "order_id": purchase.get("order_id"),
                "payment_intent_id": purchase.get("payment_intent_id"),
                "receipt_number": purchase.get("receipt_number"),
                "amount": int(purchase.get("amount") or 0),
                "currency": purchase.get("currency"),
                "service_level": purchase.get("service_level"),
                "review_included": bool(purchase.get("review_included")),
                "document_count": int(documents.get("count") or 0),
            }
        )

    @staticmethod
    def _document_snapshot(rows: list[dict[str, Any]]) -> tuple[str, list[dict[str, str]]]:
        normalized: list[dict[str, str]] = []
        for row in rows:
            path = Path(str(row.get("file_path") or "")).resolve()
            normalized.append(
                {
                    "document_id": str(row.get("id") or ""),
                    "product_code": str(row.get("product_code") or ""),
                    "kind": str(row.get("kind") or ""),
                    "version": str(row.get("version") or ""),
                    "sha256": _file_sha256(path),
                }
            )
        return _canonical_sha256({"documents": normalized}), normalized

    def _validated_documents(
        self,
        rows: list[dict[str, Any]],
        expected_count: int,
        product_code: str,
    ) -> list[dict[str, Any]]:
        if not rows:
            raise FulfillmentIntakeError("NO_REVIEWABLE_DOCUMENTS", "El expediente no tiene documentos para revisión.")
        if len(rows) != int(expected_count or 0):
            raise FulfillmentIntakeError(
                "DOCUMENT_COUNT_DRIFT",
                "El conjunto documental cambió después de la activación y debe reconciliarse antes de ingresar a revisión.",
            )
        for row in rows:
            if str(row.get("product_code") or "") != product_code:
                raise FulfillmentIntakeError("DOCUMENT_PRODUCT_MISMATCH", "Un documento no corresponde al producto del expediente.")
            source = Path(str(row.get("file_path") or "")).resolve()
            if (
                str(row.get("mime_type") or "") != DOCX_MIME
                or source.suffix.casefold() != ".docx"
                or not source.is_file()
            ):
                raise FulfillmentIntakeError(
                    "DOCUMENT_NOT_REVIEWABLE",
                    "Todos los documentos de la activación deben ser DOCX materializados antes del ingreso a revisión.",
                )
        return rows

    def _ensure_desk_case(self, actor: dict[str, Any], row: dict[str, Any]) -> tuple[str, bool]:
        source = Path(str(row["file_path"])).resolve()
        desk_case_id = self.workspace.desk_case_id(str(row["id"]))
        manifest = self.workspace.root / desk_case_id / "case.json"
        if not manifest.is_file():
            self.workspace.desk.create_case(
                case_id=desk_case_id,
                product_code=str(row["product_code"]),
                document_id=str(row["id"]),
                title=str(row.get("name") or row["id"]),
                source_generation_id=str(row["case_id"]),
                actor={
                    "id": str(actor.get("id") or ""),
                    "role": str(actor.get("role") or ""),
                    "name": str(actor.get("name") or ""),
                },
            )
            self.workspace.desk.add_revision(
                case_id=desk_case_id,
                source_file=source,
                actor={
                    "id": str(actor.get("id") or ""),
                    "role": str(actor.get("role") or ""),
                    "name": str(actor.get("name") or ""),
                },
                note="Revisión inicial registrada por el intake exacto M36.0 desde el documento activado.",
            )
            created = True
        else:
            detail = self.workspace.detail(actor, desk_case_id)
            if str(detail.get("source_case_id") or "") != str(row["case_id"]):
                raise FulfillmentIntakeError("DESK_CASE_SOURCE_MISMATCH", "La mesa existente apunta a otro expediente fuente.")
            if str((detail.get("case") or {}).get("document_id") or "") != str(row["id"]):
                raise FulfillmentIntakeError("DESK_DOCUMENT_MISMATCH", "La mesa existente apunta a otro documento.")
            current_id = str((detail.get("case") or {}).get("current_revision_id") or "")
            current = next((item for item in detail.get("revisions", []) if item.get("revision_id") == current_id), None)
            if not current:
                raise FulfillmentIntakeError("DESK_REVISION_MISSING", "La mesa existente no tiene revisión vigente.")
            if str(current.get("sha256") or "") != _file_sha256(source):
                raise FulfillmentIntakeError(
                    "DOCUMENT_CHANGED_BEFORE_INTAKE",
                    "El documento vigente cambió respecto de la revisión ya registrada; debe reconciliarse explícitamente.",
                )
            created = False
        detail = self.workspace.detail(actor, desk_case_id)
        if not bool((detail.get("audit") or {}).get("valid")):
            raise FulfillmentIntakeError("APPROVAL_CHAIN_INVALID", "La cadena de aprobación del documento no es íntegra.")
        operations_audit = self.operations.verify_chain(desk_case_id)
        if not operations_audit.get("valid"):
            raise OperationsIntegrityError("La cadena operativa M32.6 no es íntegra.")
        if int(operations_audit.get("events") or 0) == 0:
            self.operations.update_priority(actor, desk_case_id, "normal")
        return desk_case_id, created

    def _journey_state(self, con, case_id: str, actor: dict[str, Any]) -> dict[str, Any]:
        return self.journey.detail(con, case_id, actor)

    def _advance_journey(self, con, case_id: str, actor: dict[str, Any], intake_id: str, desk_ids: list[str]) -> dict[str, Any]:
        detail = self._journey_state(con, case_id, actor)
        current = str(detail.get("current_state") or "")
        if current == "GENERADO":
            return self.journey.transition(
                con,
                case_id,
                STATE_REVIEW_INTAKE,
                "Los documentos activados fueron registrados íntegramente en la Mesa Jurídica para revisión profesional.",
                {
                    "source": "m36_0_fulfillment_intake",
                    "fulfillment_intake_id": intake_id,
                    "desk_case_ids": desk_ids,
                    "document_count": len(desk_ids),
                },
                "",
                actor,
            )
        if current in REVIEW_PHASE_STATES:
            return detail
        raise FulfillmentIntakeError(
            "JOURNEY_NOT_READY_FOR_REVIEW",
            f"El recorrido operativo está en {current or 'estado desconocido'} y no puede ingresar a revisión desde M36.0.",
        )

    def activate(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        self._require_admin(actor)
        case_id = _safe_case_id(case_id)
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            source_case = self._source_case(con, case_id)
            if not source_case:
                raise FulfillmentIntakeError("CASE_NOT_FOUND", "Expediente no encontrado.", 404)
            source_case = dict(source_case)
            owner_id = str(source_case.get("owner_id") or "")
            if not owner_id:
                raise FulfillmentIntakeError("CASE_OWNER_MISSING", "El expediente no tiene titular verificable.")
            try:
                activation = self.activation.build(con, owner_id, case_id)
            except CaseActivationError as exc:
                raise FulfillmentIntakeError(
                    "ACTIVATION_NOT_VERIFIED",
                    "El expediente no supera la verificación post-compra requerida para fulfillment.",
                    exc.status if exc.status in {400, 404, 409, 422} else 409,
                ) from exc
            if activation.get("activation_status") != "ACTIVE":
                raise FulfillmentIntakeError(
                    "DOCUMENTS_NOT_READY",
                    "La activación todavía no acredita documentos materializados para revisión.",
                )
            activation_case = activation.get("case") or {}
            if str(activation_case.get("product_code") or "") != str(source_case.get("product_code") or ""):
                raise FulfillmentIntakeError("ACTIVATION_PRODUCT_MISMATCH", "La activación no corresponde al producto del expediente.")
            link = self._commerce_link(con, owner_id, case_id)
            if not link:
                raise FulfillmentIntakeError("COMMERCE_LINK_MISSING", "No existe vínculo comercial M35.2 verificable.")
            link = dict(link)
            if str(link.get("state") or "") != "CASE_CREATED":
                raise FulfillmentIntakeError("COMMERCE_NOT_FINAL", "El vínculo comercial todavía no está materializado.")
            purchase = activation.get("purchase_confirmation") or {}
            if str(link.get("order_id") or "") != str(purchase.get("order_id") or ""):
                raise FulfillmentIntakeError("ORDER_LINK_MISMATCH", "La activación y el vínculo comercial apuntan a órdenes distintas.")

            activation_sha = self._activation_fingerprint(activation, str(link["id"]))
            rows = self._validated_documents(
                self._documents(con, case_id),
                int((activation.get("documents") or {}).get("count") or 0),
                str(source_case["product_code"]),
            )
            document_sha, document_manifest = self._document_snapshot(rows)
            existing = con.execute("SELECT * FROM m36_fulfillment_intake WHERE case_id=?", (case_id,)).fetchone()
            if existing:
                existing = dict(existing)
                if existing["activation_sha256"] != activation_sha or existing["document_snapshot_sha256"] != document_sha:
                    raise FulfillmentIntakeError(
                        "FULFILLMENT_INTAKE_DRIFT",
                        "La activación o el conjunto documental cambió después del primer ingreso a fulfillment.",
                    )
                desk_ids = json.loads(existing["desk_case_ids_json"] or "[]")
                for desk_id in desk_ids:
                    detail = self.workspace.detail(actor, desk_id)
                    if str(detail.get("source_case_id") or "") != case_id or not bool((detail.get("audit") or {}).get("valid")):
                        raise FulfillmentIntakeError("FULFILLMENT_TRACE_BROKEN", "Una mesa documental del intake dejó de ser íntegra.")
                    if not self.operations.verify_chain(desk_id).get("valid"):
                        raise FulfillmentIntakeError("OPERATIONS_TRACE_BROKEN", "Una cadena operativa del intake dejó de ser íntegra.")
                journey = self._journey_state(con, case_id, actor)
                return self._public(existing, desk_ids, document_manifest, journey, idempotent=True)

            intake_id = "FUL-" + uuid.uuid4().hex[:14].upper()
            desk_ids: list[str] = []
            created_ids: list[str] = []
            for row in rows:
                desk_id, created = self._ensure_desk_case(actor, row)
                desk_ids.append(desk_id)
                if created:
                    created_ids.append(desk_id)
            if len(desk_ids) != len(rows) or len(set(desk_ids)) != len(desk_ids):
                raise FulfillmentIntakeError("DESK_COVERAGE_INCOMPLETE", "No se logró una mesa única para cada documento activado.")

            journey = self._advance_journey(con, case_id, actor, intake_id, desk_ids)
            now = core.now()
            con.execute(
                """INSERT INTO m36_fulfillment_intake(
                     id,case_id,owner_id,product_code,commerce_link_id,order_id,activation_sha256,
                     document_snapshot_sha256,desk_case_ids_json,state,initiated_by,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    intake_id,
                    case_id,
                    owner_id,
                    source_case["product_code"],
                    link["id"],
                    purchase["order_id"],
                    activation_sha,
                    document_sha,
                    json.dumps(desk_ids, ensure_ascii=False, separators=(",", ":")),
                    STATE_REVIEW_INTAKE,
                    actor["id"],
                    now,
                    now,
                ),
            )
            core.audit(
                con,
                actor["id"],
                "m36_fulfillment_intake",
                intake_id,
                "activate_review_intake",
                {
                    "case_id": case_id,
                    "product_code": source_case["product_code"],
                    "order_id": purchase["order_id"],
                    "desk_case_ids": desk_ids,
                    "created_desk_cases": created_ids,
                    "document_count": len(rows),
                    "journey_state": journey.get("current_state"),
                },
            )
            con.commit()
            row = dict(con.execute("SELECT * FROM m36_fulfillment_intake WHERE id=?", (intake_id,)).fetchone())
            return self._public(row, desk_ids, document_manifest, journey, idempotent=False)
        finally:
            con.close()

    def detail(self, actor: dict[str, Any], case_id: str) -> dict[str, Any]:
        self._require_admin(actor)
        case_id = _safe_case_id(case_id)
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            row = con.execute("SELECT * FROM m36_fulfillment_intake WHERE case_id=?", (case_id,)).fetchone()
            if not row:
                raise FulfillmentIntakeError("FULFILLMENT_NOT_ACTIVATED", "El expediente aún no ha ingresado a fulfillment jurídico.", 404)
            row = dict(row)
            desk_ids = json.loads(row["desk_case_ids_json"] or "[]")
            documents = self._documents(con, case_id)
            _, manifest = self._document_snapshot(self._validated_documents(documents, len(desk_ids), row["product_code"]))
            journey = self._journey_state(con, case_id, actor)
            return self._public(row, desk_ids, manifest, journey, idempotent=True)
        finally:
            con.close()

    def queue(self, actor: dict[str, Any]) -> dict[str, Any]:
        self._require_admin(actor)
        con = self.db_factory()
        try:
            self.ensure_schema(con)
            rows = [dict(row) for row in con.execute(
                "SELECT * FROM m36_fulfillment_intake ORDER BY created_at DESC,id DESC"
            ).fetchall()]
            items = []
            for row in rows:
                desk_ids = json.loads(row["desk_case_ids_json"] or "[]")
                states = []
                active_alerts = 0
                for desk_id in desk_ids:
                    state = self.operations.state(actor, desk_id)
                    states.append(state.get("workflow_status"))
                    active_alerts += sum(not alert.get("acknowledged") for alert in state.get("alerts", []))
                journey = self._journey_state(con, row["case_id"], actor)
                items.append(
                    {
                        "fulfillment_intake_id": row["id"],
                        "case_id": row["case_id"],
                        "product_code": row["product_code"],
                        "order_id": row["order_id"],
                        "state": row["state"],
                        "journey_state": journey.get("current_state"),
                        "document_count": len(desk_ids),
                        "desk_workflow_states": states,
                        "active_alerts": active_alerts,
                        "created_at": row["created_at"],
                    }
                )
            return {
                "schema": "legalai_m36_0_fulfillment_queue_v1",
                "schema_version": SCHEMA_VERSION,
                "items": items,
                "metrics": {
                    "cases": len(items),
                    "documents": sum(item["document_count"] for item in items),
                    "active_alerts": sum(item["active_alerts"] for item in items),
                },
                "notice": "Los SLA de la Mesa Jurídica son metas operativas y no sustituyen términos legales, judiciales, administrativos o contractuales.",
            }
        finally:
            con.close()

    @staticmethod
    def _public(
        row: Mapping[str, Any],
        desk_ids: list[str],
        document_manifest: list[dict[str, str]],
        journey: Mapping[str, Any],
        *,
        idempotent: bool,
    ) -> dict[str, Any]:
        return {
            "schema": "legalai_m36_0_fulfillment_intake_v1",
            "schema_version": SCHEMA_VERSION,
            "fulfillment_intake_id": row["id"],
            "case_id": row["case_id"],
            "product_code": row["product_code"],
            "order_id": row["order_id"],
            "state": row["state"],
            "journey_state": journey.get("current_state"),
            "document_count": len(desk_ids),
            "desk_case_ids": list(desk_ids),
            "documents": [
                {
                    "document_id": item["document_id"],
                    "kind": item["kind"],
                    "version": item["version"],
                }
                for item in document_manifest
            ],
            "idempotent": bool(idempotent),
            "governance": {
                "automatic_assignment": False,
                "automatic_legal_approval": False,
                "automatic_qa_approval": False,
                "automatic_release": False,
                "dual_approval_preserved": True,
                "m32_review_machinery_reused": True,
            },
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


__all__ = [
    "FulfillmentIntakeCenter",
    "FulfillmentIntakeError",
    "REVIEW_PHASE_STATES",
    "SCHEMA_VERSION",
    "STATE_REVIEW_INTAKE",
]
