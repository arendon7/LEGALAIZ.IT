from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from difflib import get_close_matches
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional, Union

try:
    from co_tr_001_v258 import CoTr001CanonicalV258 as _BaseV258
    BASE_V258_AVAILABLE = True
except ImportError:
    BASE_V258_AVAILABLE = False

    class _BaseV258:
        """Adaptador funcional de QA para ejecutar el overlay sin la base v2.58.

        La liberación real permanece bloqueada hasta instalar la entrega sobre v2.58.
        """

        VERSION = "2.58-adapter"
        PRODUCT_ID = "CO-TR-001"
        RED_STAGES = {
            "collection",
            "cobro_coactivo",
            "payment_order",
            "mandamiento_pago",
            "embargo",
            "judicial",
            "court",
        }

        def __init__(self, root: Optional[Union[Path, str]] = None):
            self.root = Path(root or ".")
            product_dir = self.root / "app" / "assets" / "advanced-legal-library" / self.PRODUCT_ID
            self.matrix = self._load(product_dir / "INVESTIGACIONES_SAST_V259.json")
            self.alias_data = self._load(product_dir / "AUTORIDADES_ALIAS_V259.json")
            self.records = list(self.matrix.get("records") or [])
            self.aliases = dict(self.alias_data.get("aliases") or {})
            self._alias_index = self._build_alias_index()

        @staticmethod
        def _load(path: Path) -> dict[str, Any]:
            return json.loads(path.read_text(encoding="utf-8"))

        @staticmethod
        def _get(data: dict[str, Any], path: str, default: Any = None) -> Any:
            value: Any = data
            for part in path.split("."):
                if not isinstance(value, dict) or part not in value:
                    return default
                value = value[part]
            return value

        @staticmethod
        def normalize(value: Any) -> str:
            text = unicodedata.normalize("NFKD", str(value or ""))
            text = "".join(ch for ch in text if not unicodedata.combining(ch))
            text = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower()).strip()
            return re.sub(r"\s+", " ", text)

        @staticmethod
        def parse_date(value: Any) -> Optional[date]:
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            text = str(value or "").strip()
            if not text:
                return None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(text[:10], fmt).date()
                except ValueError:
                    pass
            return None

        def _build_alias_index(self) -> dict[str, str]:
            index: dict[str, str] = {}
            for key, values in self.aliases.items():
                index[self.normalize(key.replace("_", " "))] = key
                for value in values:
                    index[self.normalize(value)] = key
            for record in self.records:
                index[self.normalize(record.get("authority_name"))] = str(record.get("authority_key"))
            return index

        def normalize_authority(self, authority: Any) -> dict[str, Any]:
            normalized = self.normalize(authority)
            if not normalized:
                return {"resolved": False, "input": authority, "normalized": normalized, "candidates": []}
            if normalized in self._alias_index:
                key = self._alias_index[normalized]
                return {
                    "resolved": True,
                    "input": authority,
                    "normalized": normalized,
                    "authority_key": key,
                    "candidates": [],
                }
            hits = {
                key
                for alias, key in self._alias_index.items()
                if len(alias) >= 5 and (alias in normalized or normalized in alias)
            }
            if len(hits) == 1:
                key = next(iter(hits))
                return {
                    "resolved": True,
                    "input": authority,
                    "normalized": normalized,
                    "authority_key": key,
                    "candidates": [],
                }
            candidate_aliases = get_close_matches(normalized, list(self._alias_index), n=5, cutoff=0.58)
            candidates: list[str] = []
            for alias in candidate_aliases:
                key = self._alias_index[alias]
                if key not in candidates:
                    candidates.append(key)
            return {
                "resolved": False,
                "input": authority,
                "normalized": normalized,
                "candidates": candidates[:3],
            }

        def match(self, authority: Any, infraction_date: Any) -> dict[str, Any]:
            authority_result = self.normalize_authority(authority)
            parsed_date = self.parse_date(infraction_date)
            if not authority_result.get("resolved") or parsed_date is None:
                return {
                    "authority": authority_result,
                    "date": parsed_date.isoformat() if parsed_date else None,
                    "matches": [],
                    "complete": False,
                }
            key = authority_result["authority_key"]
            matches: list[dict[str, Any]] = []
            for record in self.records:
                if record.get("authority_key") != key:
                    continue
                start = date.fromisoformat(record["start_date"])
                end = date.fromisoformat(record["end_date"])
                if start <= parsed_date <= end:
                    matches.append(deepcopy(record))
            matches.sort(key=lambda item: item["id"])
            return {
                "authority": authority_result,
                "date": parsed_date.isoformat(),
                "matches": matches,
                "complete": True,
            }

        def summary(self) -> dict[str, Any]:
            return {
                "manifest": {
                    "product_id": self.PRODUCT_ID,
                    "version": self.VERSION,
                    "status": "macro_b_documental_governance_adapter",
                    "matrix_records": len(self.records),
                    "group_a": sum(1 for item in self.records if item.get("group") == "A"),
                    "group_b": sum(1 for item in self.records if item.get("group") == "B"),
                    "automatic_legal_relief": False,
                }
            }

        def evaluate(self, answers: dict[str, Any], mode: str = "precheck") -> dict[str, Any]:
            mode = str(mode or "precheck").lower()
            authority = self._get(answers, "authority.name") or answers.get("authority")
            infraction_date = self._get(answers, "infraction.date") or answers.get("date")
            consent = bool(self._get(answers, "consents.preliminary"))
            match_result = self.match(authority, infraction_date)

            missing: list[dict[str, str]] = []
            findings: list[dict[str, str]] = []
            reviews: list[str] = []
            blocked = False

            if not authority:
                missing.append({"path": "authority.name", "label": "Organismo de tránsito"})
            elif not match_result["authority"].get("resolved"):
                missing.append({"path": "authority.name", "label": "Organismo de tránsito identificable"})
                findings.append({"id": "TR1-004", "risk": "yellow", "message": "No fue posible normalizar el organismo de tránsito con certeza."})
            if not self.parse_date(infraction_date):
                missing.append({"path": "infraction.date", "label": "Fecha válida de la presunta infracción"})
                findings.append({"id": "TR1-005", "risk": "yellow", "message": "La fecha está ausente o no tiene un formato válido."})
            if not consent:
                missing.append({"path": "consents.preliminary", "label": "Aceptación del carácter preliminar del chequeo"})
                findings.append({"id": "TR1-006", "risk": "yellow", "message": "El chequeo no se ejecuta sin aceptación expresa de su carácter preliminar."})

            if mode == "registration":
                for path, label in (
                    ("identity.full_name", "Nombre completo"),
                    ("identity.email", "Correo electrónico"),
                    ("consents.data_processing", "Autorización de tratamiento de datos"),
                ):
                    value = self._get(answers, path)
                    if value in (None, "", False):
                        missing.append({"path": path, "label": label})
                email = str(self._get(answers, "identity.email") or "")
                if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                    missing.append({"path": "identity.email", "label": "Correo electrónico válido"})

            matches = list(match_result.get("matches") or []) if consent else []
            if consent and match_result.get("complete"):
                if matches:
                    findings.append({"id": "TR1-001", "risk": "yellow", "message": "Se encontraron %d coincidencia(s) preliminar(es) en la matriz oficial." % len(matches)})
                    reviews.append("La coincidencia debe verificarse por dispositivo, expediente, decisión firme y aplicabilidad individual.")
                    if len(matches) > 1:
                        findings.append({"id": "TR1-002", "risk": "yellow", "message": "Existen varias actuaciones aplicables al mismo organismo y fecha; deben conservarse separadas."})
                    if not self._get(answers, "device.location") and not self._get(answers, "device.id"):
                        findings.append({"id": "TR1-013", "risk": "yellow", "message": "No se identificó ubicación o dispositivo SAST; la coincidencia autoridad-fecha no basta para una conclusión individual."})
                else:
                    findings.append({"id": "TR1-003", "risk": "green", "message": "No se encontró coincidencia en los rangos cargados. Esto no demuestra la legalidad del comparendo ni excluye otras defensas."})

            payment = self.normalize(self._get(answers, "payment.status"))
            if payment in {"paid", "pagada", "pago", "agreement", "acuerdo", "acuerdo de pago"}:
                message = "Existe pago o acuerdo de pago; no se promete devolución y se requiere análisis individual."
                findings.append({"id": "TR1-007", "risk": "yellow", "message": message})
                reviews.append(message)

            stage = self.normalize(self._get(answers, "procedure.stage")).replace(" ", "_")
            if stage in self.RED_STAGES:
                blocked = True
                message = "Existe cobro coactivo, mandamiento de pago, embargo o proceso judicial; la ruta automática queda bloqueada."
                findings.append({"id": "TR1-008", "risk": "red", "message": message})
                reviews.append(message)
            if bool(self._get(answers, "procedure.imminent_deadline")):
                blocked = True
                message = "Existe un término urgente; el chequeo no suspende términos y se requiere revisión inmediata."
                findings.append({"id": "TR1-009", "risk": "red", "message": message})
                reviews.append(message)
            if bool(self._get(answers, "security.possible_fraud")):
                blocked = True
                message = "Hay indicios de fraude; no deben usarse enlaces ni documentos no verificados."
                findings.append({"id": "TR1-010", "risk": "red", "message": message})
                reviews.append(message)

            documents = ["sast_preliminary_report", "sast_source_trace"]
            if mode == "registration" and not missing:
                documents.append("sast_verified_case_file")
            if matches or blocked or reviews:
                documents.append("sast_professional_review_request")

            if blocked:
                risk = "red"
                status = "blocked"
            elif missing:
                risk = "yellow"
                status = "incomplete"
            elif any(item.get("risk") == "yellow" for item in findings):
                risk = "yellow"
                status = "ready_with_review"
            else:
                risk = "green"
                status = "ready"

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
            if matches:
                blocks.extend(["B258-COINCIDENCIAS", "B258-VERIFICACION-INDIVIDUAL"])
            else:
                blocks.append("B258-NO-COINCIDENCIA")
            if mode == "registration":
                blocks.extend(["B258-EXPEDIENTE-VERIFICADO", "B258-CONSENTIMIENTOS-DATOS"])
            if reviews or blocked:
                blocks.append("B258-REVISION-PROFESIONAL")
            if any(item.get("id") == "TR1-010" for item in findings):
                blocks.append("B258-ALERTA-FRAUDE")

            release_blockers: list[str] = []
            if blocked:
                release_blockers.append("El caso presenta riesgo rojo o una etapa excluida de automatización.")
            if missing:
                release_blockers.append("Faltan datos esenciales para generar un expediente completo y trazable.")
            release_blockers.append("El overlay debe instalarse sobre la base canónica v2.58 para habilitar liberación.")

            return {
                "product_id": self.PRODUCT_ID,
                "version": self.VERSION,
                "mode": mode,
                "status": status,
                "readiness": status,
                "risk": risk,
                "blocked": blocked,
                "missing_fields": missing,
                "authority_resolution": match_result.get("authority"),
                "infraction_date": match_result.get("date"),
                "matches": matches,
                "match_count": len(matches),
                "findings": findings,
                "professional_reviews": list(dict.fromkeys(reviews)),
                "review_requirements": list(dict.fromkeys(reviews)),
                "professional_review_required": bool(reviews or matches or blocked),
                "documents": list(dict.fromkeys(documents)),
                "blocks": list(dict.fromkeys(blocks)),
                "release_blocked": True,
                "release_blockers": release_blockers,
                "source_snapshot": self.matrix.get("snapshot_date"),
                "source_revalidation_required": True,
                "legal_notice": "Resultado preliminar. No constituye decisión administrativa, anulación, revocación, devolución, archivo ni representación judicial.",
                "document_disclaimer": "Los documentos expresan un chequeo preliminar y trazable. No sustituyen una decisión administrativa, no suspenden términos y no garantizan revocación, devolución, archivo ni representación judicial.",
            }


class CoTr001CanonicalV259(_BaseV258):
    """CO-TR-001, Macrofase C: validación, endurecimiento y cierre controlado."""

    VERSION = "2.59"
    PRODUCT_ID = "CO-TR-001"
    BASE_AVAILABLE = BASE_V258_AVAILABLE

    def __init__(self, root: Optional[Union[Path, str]] = None):
        try:
            super().__init__(root or Path("."))
        except TypeError:
            super().__init__()
            self.root = Path(root or ".")
        self.root = Path(root or getattr(self, "root", Path(".")))

    @staticmethod
    def _get(data: dict[str, Any], path: str, default: Any = None) -> Any:
        value: Any = data
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    @staticmethod
    def _append_finding(result: dict[str, Any], finding_id: str, risk: str, message: str, review: bool = True) -> None:
        findings = list(result.get("findings") or [])
        if finding_id not in {item.get("id") for item in findings}:
            findings.append({"id": finding_id, "risk": risk, "message": message})
        result["findings"] = findings
        if review:
            reviews = list(result.get("professional_reviews") or result.get("review_requirements") or [])
            if message not in reviews:
                reviews.append(message)
            result["professional_reviews"] = reviews
            result["review_requirements"] = reviews

    def summary(self) -> dict[str, Any]:
        data = dict(super().summary())
        manifest = dict(data.get("manifest") or {})
        manifest.update(
            {
                "product_id": self.PRODUCT_ID,
                "version": self.VERSION,
                "status": "macro_c_validation_closure",
                "document_factory": True,
                "document_types": 4,
                "consolidated_package": True,
                "immutable_revisions": True,
                "version_comparison": True,
                "dual_approval": True,
                "independent_approval": True,
                "cryptographic_integrity": True,
                "validation_closed": True,
                "release_gate": True,
                "official_source_control": True,
                "api_error_hardening": True,
                "source_snapshot_preserved": True,
                "canonical_scope_frozen": True,
                "supersedes": "2.58",
                "base_v258_available": self.BASE_AVAILABLE,
                "next_macro_phase": None,
            }
        )
        data["manifest"] = manifest
        data["version"] = self.VERSION
        return data

    def evaluate(self, answers: dict[str, Any], mode: str = "precheck") -> dict[str, Any]:
        result = dict(super().evaluate(answers, mode=mode))
        result["version"] = self.VERSION
        result["mode"] = str(mode or result.get("mode") or "precheck").lower()
        result.setdefault("findings", [])
        result.setdefault("documents", [])
        result.setdefault("blocks", [])
        result.setdefault("missing_fields", [])

        matches = list(result.get("matches") or [])
        firm_decision = bool(self._get(answers, "official_decision.firm"))
        decision_reference = str(self._get(answers, "official_decision.reference") or "").strip()
        if matches and not firm_decision:
            self._append_finding(
                result,
                "TR1-014",
                "yellow",
                "La coincidencia se relaciona con actuaciones publicadas; antes de atribuir revocación oficiosa debe verificarse una decisión firme de la Superintendencia de Transporte y su aplicabilidad individual.",
            )
        elif matches and firm_decision and not decision_reference:
            result["missing_fields"] = list(result.get("missing_fields") or []) + [
                {"path": "official_decision.reference", "label": "Referencia verificable de la decisión firme"}
            ]
            self._append_finding(
                result,
                "TR1-014-REF",
                "yellow",
                "Se indicó que existe decisión firme, pero falta una referencia verificable del acto y su ejecutoria.",
            )

        blocks = [str(item).replace("B258-", "B259-") for item in result.get("blocks", [])]
        for block in ("B259-CIERRE-VALIDACION", "B259-CONTROL-FUENTES", "B259-COMPUERTA-LIBERACION"):
            if block not in blocks:
                blocks.append(block)
        result["blocks"] = list(dict.fromkeys(blocks))

        reviews = list(dict.fromkeys(result.get("professional_reviews") or result.get("review_requirements") or []))
        result["professional_reviews"] = reviews
        result["review_requirements"] = reviews
        result["professional_review_required"] = bool(reviews or matches or result.get("blocked"))

        if result.get("blocked"):
            result["risk"] = "red"
            result["status"] = "blocked"
        elif result.get("missing_fields"):
            result["risk"] = "yellow"
            result["status"] = "incomplete"
        elif reviews or any(item.get("risk") == "yellow" for item in result.get("findings", [])):
            result["risk"] = "yellow"
            result["status"] = "ready_with_review"
        else:
            result["risk"] = "green"
            result["status"] = "ready"
        result["readiness"] = result["status"]

        blockers: list[str] = []
        if result.get("blocked"):
            blockers.append("El caso presenta riesgo rojo o una etapa excluida de automatización.")
        if result.get("missing_fields"):
            blockers.append("Faltan datos esenciales para generar un expediente completo y trazable.")
        if not self.BASE_AVAILABLE:
            blockers.append("La versión debe instalarse sobre la base canónica v2.58 para habilitar liberación.")
        result["release_blockers"] = list(dict.fromkeys(blockers))
        result["release_blocked"] = bool(blockers)
        result["source_revalidation_required"] = True
        result["decision_firmness_required"] = bool(matches and not firm_decision)
        result["decision_trace"] = [item.get("id") for item in result.get("findings", []) if item.get("id")]
        result["documents"] = list(dict.fromkeys(result.get("documents") or []))
        result["document_disclaimer"] = (
            "Documento generado con apoyo tecnológico a partir de información suministrada y fuentes oficiales verificadas. "
            "El resultado es preliminar, no suspende términos y no constituye decisión administrativa, revocación, devolución, archivo ni representación judicial."
        )
        return result
