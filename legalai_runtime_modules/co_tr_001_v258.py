from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

try:
    from co_tr_001_v257 import CoTr001CanonicalV257 as _BaseV257
    BASE_V257_AVAILABLE = True
except ImportError:
    BASE_V257_AVAILABLE = False

    class _BaseV257:
        """Adaptador mínimo para QA aislado del overlay.

        La liberación permanece bloqueada mientras no esté instalada la base v2.57.
        """

        VERSION = "2.57-adapter"
        PRODUCT_ID = "CO-TR-001"

        def __init__(self, root: Optional[Union[Path, str]] = None):
            self.root = Path(root or ".")

        @staticmethod
        def _get(data: dict[str, Any], path: str, default: Any = None) -> Any:
            value: Any = data
            for part in path.split("."):
                if not isinstance(value, dict) or part not in value:
                    return default
                value = value[part]
            return value

        def summary(self) -> dict[str, Any]:
            return {
                "manifest": {
                    "product_id": self.PRODUCT_ID,
                    "version": self.VERSION,
                    "status": "macro_a_functional_adapter",
                    "matrix_records": 49,
                    "group_a": 37,
                    "group_b": 12,
                    "automatic_legal_relief": False,
                }
            }

        def evaluate(self, answers: dict[str, Any], mode: str = "precheck") -> dict[str, Any]:
            mode = str(mode or "precheck").lower()
            authority = self._get(answers, "authority.name") or answers.get("authority")
            infraction_date = self._get(answers, "infraction.date") or answers.get("date")
            preliminary = bool(self._get(answers, "consents.preliminary"))
            missing: list[dict[str, str]] = []
            findings: list[dict[str, str]] = []
            reviews: list[str] = []
            blocked = False

            if not authority:
                missing.append({"path": "authority.name", "label": "Organismo de tránsito"})
            if not infraction_date:
                missing.append({"path": "infraction.date", "label": "Fecha de la presunta infracción"})
            if not preliminary:
                missing.append({"path": "consents.preliminary", "label": "Aceptación del carácter preliminar"})

            if mode == "registration":
                for path, label in (
                    ("identity.full_name", "Nombre completo"),
                    ("identity.email", "Correo electrónico"),
                    ("consents.data_processing", "Autorización de tratamiento de datos"),
                ):
                    if self._get(answers, path) in (None, "", False):
                        missing.append({"path": path, "label": label})

            stage = str(self._get(answers, "procedure.stage") or "").lower()
            if stage in {"collection", "payment_order", "embargo", "judicial"}:
                blocked = True
                findings.append({"id": "TR1-008", "risk": "red", "message": "Existe una etapa procesal de alto riesgo."})
                reviews.append("El caso requiere revisión profesional antes de cualquier actuación.")
            if bool(self._get(answers, "procedure.imminent_deadline")):
                blocked = True
                findings.append({"id": "TR1-009", "risk": "red", "message": "Existe un término urgente."})
                reviews.append("El chequeo no suspende términos.")
            if bool(self._get(answers, "security.possible_fraud")):
                blocked = True
                findings.append({"id": "TR1-010", "risk": "red", "message": "Existen indicios de fraude."})
                reviews.append("Deben verificarse los canales y documentos antes de continuar.")

            matches = list(answers.get("_adapter_matches") or []) if preliminary and not missing else []
            if matches:
                findings.append({"id": "TR1-001", "risk": "yellow", "message": "Existe coincidencia preliminar en la matriz."})
                reviews.append("Debe verificarse el dispositivo, la decisión firme y la aplicabilidad individual.")
            elif preliminary and authority and infraction_date:
                findings.append({"id": "TR1-003", "risk": "green", "message": "No se encontró coincidencia; esto no demuestra la legalidad del comparendo."})

            payment = str(self._get(answers, "payment.status") or "").lower()
            if payment in {"paid", "agreement", "pagada", "acuerdo", "acuerdo de pago"}:
                findings.append({"id": "TR1-007", "risk": "yellow", "message": "Existe pago o acuerdo; no se promete devolución."})
                reviews.append("Debe analizarse individualmente cualquier pretensión económica.")

            documents = ["sast_preliminary_report", "sast_source_trace"]
            if mode == "registration" and not missing:
                documents.append("sast_verified_case_file")
            if matches or blocked or reviews:
                documents.append("sast_professional_review_request")

            status = "blocked" if blocked else "incomplete" if missing else "ready_with_review" if reviews or matches else "ready"
            return {
                "product_id": self.PRODUCT_ID,
                "version": self.VERSION,
                "mode": mode,
                "status": status,
                "risk": "red" if blocked else "yellow" if reviews or matches else "green",
                "blocked": blocked,
                "missing_fields": missing,
                "authority_resolution": {"resolved": bool(authority), "input": authority, "authority_key": str(authority or "")},
                "infraction_date": str(infraction_date or ""),
                "matches": matches,
                "match_count": len(matches),
                "findings": findings,
                "professional_reviews": reviews,
                "documents": documents,
                "legal_notice": "Resultado preliminar. No constituye decisión administrativa ni alivio jurídico automático.",
                "source_snapshot": "2026-07-26",
            }


class CoTr001CanonicalV258(_BaseV257):
    """Macrofase B documental y de gobierno de CO-TR-001."""

    VERSION = "2.58"
    PRODUCT_ID = "CO-TR-001"
    BASE_AVAILABLE = BASE_V257_AVAILABLE

    def __init__(self, root: Optional[Union[Path, str]] = None):
        super().__init__(root or Path("."))
        self.root = Path(root or getattr(self, "root", Path(".")))

    def summary(self) -> dict[str, Any]:
        data = dict(super().summary())
        manifest = dict(data.get("manifest") or {})
        manifest.update(
            {
                "product_id": self.PRODUCT_ID,
                "version": self.VERSION,
                "status": "macro_b_documental_governance",
                "document_factory": True,
                "document_types": 4,
                "consolidated_package": True,
                "immutable_revisions": True,
                "version_comparison": True,
                "dual_approval": True,
                "cryptographic_integrity": True,
                "source_snapshot_preserved": True,
                "canonical_scope_frozen": True,
                "base_v257_available": self.BASE_AVAILABLE,
                "next_macro_phase": "2.59",
            }
        )
        data["manifest"] = manifest
        data["version"] = self.VERSION
        return data

    def evaluate(self, answers: dict[str, Any], mode: str = "precheck") -> dict[str, Any]:
        result = dict(super().evaluate(answers, mode=mode))
        result["version"] = self.VERSION
        result["mode"] = str(mode or result.get("mode") or "precheck").lower()
        reviews = list(result.get("professional_reviews") or [])
        documents = list(dict.fromkeys(result.get("documents") or []))

        blocks = [
            "B258-CONTROL-PREVIO",
            "B258-ENTRADAS-CHEQUEO",
            "B258-RESULTADO-PRELIMINAR",
            "B258-TRAZABILIDAD-FUENTES",
            "B258-LIMITES-JURIDICOS",
            "B258-HASH-INTEGRIDAD",
            "B258-AUDITORIA",
            "B258-REVISION-INMUTABLE",
            "B258-APROBACION-JURIDICA",
            "B258-APROBACION-QA",
        ]
        if result.get("matches"):
            blocks.extend(["B258-COINCIDENCIAS", "B258-VERIFICACION-INDIVIDUAL"])
        else:
            blocks.append("B258-NO-COINCIDENCIA")
        if result["mode"] == "registration":
            blocks.extend(["B258-EXPEDIENTE-VERIFICADO", "B258-CONSENTIMIENTOS-DATOS"])
        if reviews or result.get("blocked"):
            blocks.append("B258-REVISION-PROFESIONAL")
        if any(item.get("id") == "TR1-010" for item in result.get("findings", [])):
            blocks.append("B258-ALERTA-FRAUDE")

        release_blockers: list[str] = []
        if result.get("blocked"):
            release_blockers.append("El caso presenta riesgo rojo o una etapa excluida de automatización.")
        if result.get("missing_fields"):
            release_blockers.append("Faltan datos esenciales para generar un expediente completo y trazable.")
        if not self.BASE_AVAILABLE:
            release_blockers.append("El overlay debe instalarse sobre la base canónica v2.57 para habilitar liberación.")

        result.update(
            {
                "documents": documents,
                "blocks": list(dict.fromkeys(blocks)),
                "readiness": result.get("status"),
                "professional_review_required": bool(reviews or result.get("blocked") or result.get("matches")),
                "review_requirements": reviews,
                "release_blocked": bool(release_blockers),
                "release_blockers": release_blockers,
                "source_revalidation_required": True,
                "document_disclaimer": (
                    "Los documentos expresan un chequeo preliminar y trazable. No sustituyen una decisión administrativa, "
                    "no suspenden términos y no garantizan revocación, devolución, archivo ni representación judicial."
                ),
            }
        )
        return result
