from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from difflib import get_close_matches
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional, Union


class CoTr001CanonicalV257:
    """Motor funcional canónico de CO-TR-001 - Chequeo SAST.

    La coincidencia es preliminar. Este motor no declara nulidad, revocación,
    devolución ni archivo de un comparendo individual.
    """

    VERSION = "2.57"
    PRODUCT_ID = "CO-TR-001"

    RED_STAGES = {"collection", "cobro_coactivo", "payment_order", "mandamiento_pago", "embargo", "judicial", "court"}

    def __init__(self, root: Optional[Union[Path, str]] = None):
        self.root = Path(root or Path(__file__).resolve().parent)
        asset = self.root / "app/assets/advanced-legal-library/CO-TR-001"
        self.matrix = self._load(asset / "INVESTIGACIONES_SAST_V257.json")
        self.alias_data = self._load(asset / "AUTORIDADES_ALIAS_V257.json")
        self.sources = self._load(asset / "FUENTES_V257.json")
        self.interview = self._load(asset / "ENTREVISTA_V257.json")
        self.rules = self._load(asset / "REGLAS_V257.json")
        self.product = self._load(asset / "PRODUCTO_V257.json")
        self.records = list(self.matrix.get("records") or [])
        self.aliases = dict(self.alias_data.get("aliases") or {})
        self._alias_index = self._build_alias_index()

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

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
            return {"resolved": True, "input": authority, "normalized": normalized, "authority_key": key, "candidates": []}
        # Conservative containment: only accept when exactly one alias provides a unique authority.
        hits = {key for alias, key in self._alias_index.items() if len(alias) >= 5 and (alias in normalized or normalized in alias)}
        if len(hits) == 1:
            key = next(iter(hits))
            return {"resolved": True, "input": authority, "normalized": normalized, "authority_key": key, "candidates": []}
        candidate_aliases = get_close_matches(normalized, list(self._alias_index), n=5, cutoff=0.58)
        candidates = []
        for alias in candidate_aliases:
            key = self._alias_index[alias]
            if key not in candidates:
                candidates.append(key)
        return {"resolved": False, "input": authority, "normalized": normalized, "candidates": candidates[:3]}

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
        matches = []
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
                "status": "macro_a_functional",
                "matrix_records": len(self.records),
                "group_a": sum(1 for item in self.records if item.get("group") == "A"),
                "group_b": sum(1 for item in self.records if item.get("group") == "B"),
                "snapshot_date": self.matrix.get("snapshot_date"),
                "deterministic_matching": True,
                "automatic_legal_relief": False,
                "next_macro_phase": "2.58",
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

        matches = match_result.get("matches") or [] if consent else []
        if consent and match_result.get("complete"):
            if matches:
                findings.append({"id": "TR1-001", "risk": "yellow", "message": f"Se encontraron {len(matches)} coincidencia(s) preliminar(es) en la matriz oficial."})
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

        stage = self.normalize(self._get(answers, "procedure.stage"))
        stage_key = stage.replace(" ", "_")
        if stage_key in self.RED_STAGES:
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

        return {
            "product_id": self.PRODUCT_ID,
            "version": self.VERSION,
            "mode": mode,
            "status": status,
            "risk": risk,
            "blocked": blocked,
            "missing_fields": missing,
            "authority_resolution": match_result.get("authority"),
            "infraction_date": match_result.get("date"),
            "matches": matches,
            "match_count": len(matches),
            "findings": findings,
            "professional_reviews": list(dict.fromkeys(reviews)),
            "documents": list(dict.fromkeys(documents)),
            "cross_sell": ["CO-TR-002", "CO-TR-003"],
            "legal_notice": "Resultado preliminar. No constituye decisión administrativa, anulación, revocación, devolución, archivo ni representación judicial.",
            "source_snapshot": self.matrix.get("snapshot_date"),
        }
