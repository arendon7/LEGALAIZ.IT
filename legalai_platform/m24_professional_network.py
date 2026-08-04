from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class M24ProfessionalNetwork:
    """Closed professional network for the controlled M24 pilot.

    This additive module manages invitation, verification, capacity, case offers,
    conflict declarations and SLA evidence. It never publishes M23.2, approves
    legal content, processes real compensation or exposes a public directory.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.policy_path = self.root / "config" / "m24_9_professional_network_policy.json"
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.product_specialty_map = dict(self.policy.get("product_specialty_map") or {})
        self.product_codes = set(self.product_specialty_map)
        self.confirmations = dict(self.policy.get("confirmations") or {})
        conflict_key = os.environ.get("LEGAL_CONFLICT_HASH_KEY", "").strip()
        conflict_file = os.environ.get("LEGAL_CONFLICT_HASH_KEY_FILE", "").strip()
        if not conflict_key and conflict_file:
            key_path = Path(conflict_file)
            if not key_path.is_file():
                raise RuntimeError("LEGAL_CONFLICT_HASH_KEY_FILE no existe o no es legible.")
            conflict_key = key_path.read_text(encoding="utf-8").strip()
        self._conflict_key = (conflict_key or "M24.9-LOCAL-PILOT-NOT-FOR-PRODUCTION").encode("utf-8")

    @staticmethod
    def now_dt() -> datetime:
        return datetime.now(timezone.utc).replace(microsecond=0)

    @classmethod
    def now(cls) -> str:
        return cls.now_dt().isoformat()

    @staticmethod
    def _json(raw: Any, default: Any):
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(raw or "")
        except (TypeError, json.JSONDecodeError):
            return default

    @staticmethod
    def _actor_name(actor: dict[str, Any]) -> str:
        return str(actor.get("name") or actor.get("email") or actor.get("id") or "Usuario")

    @staticmethod
    def _normalize_party(value: str) -> str:
        value = re.sub(r"\s+", " ", str(value or "").strip().casefold())
        value = re.sub(r"[^a-z0-9áéíóúüñ& .-]", "", value)
        return value[:180]

    def _hash_parties(self, values: list[Any]) -> list[str]:
        hashes: list[str] = []
        for raw in values:
            normalized = self._normalize_party(str(raw))
            if len(normalized) < 2:
                continue
            digest = hmac.new(self._conflict_key, normalized.encode("utf-8"), hashlib.sha256).hexdigest()
            if digest not in hashes:
                hashes.append(digest)
        return hashes[:25]

    @staticmethod
    def _redact_note(value: str, party_names: list[Any] | None = None, limit: int = 800) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()[:limit]
        text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[correo omitido]", text)
        text = re.sub(r"(?<!\d)\d{6,}(?!\d)", "[identificador omitido]", text)
        for raw in sorted((party_names or []), key=lambda item: len(str(item)), reverse=True):
            party = str(raw or "").strip()
            if len(party) >= 2:
                text = re.sub(re.escape(party), "[parte omitida]", text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def ensure_schema(con) -> None:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS m24_professional_profile(
              user_id TEXT PRIMARY KEY,
              invitation_status TEXT NOT NULL CHECK(invitation_status IN ('invited','accepted','declined')),
              verification_status TEXT NOT NULL CHECK(verification_status IN ('pending','verified','suspended')),
              jurisdiction TEXT NOT NULL,
              bar_registration_last4 TEXT NOT NULL,
              specialties_json TEXT NOT NULL,
              product_codes_json TEXT NOT NULL,
              availability_status TEXT NOT NULL CHECK(availability_status IN ('available','limited','unavailable')),
              max_active_cases INTEGER NOT NULL,
              response_sla_hours INTEGER NOT NULL,
              review_sla_hours INTEGER NOT NULL,
              fee_reference_json TEXT NOT NULL,
              invited_by TEXT NOT NULL,
              invited_at TEXT NOT NULL,
              accepted_at TEXT,
              verified_by TEXT,
              verified_at TEXT,
              verification_note TEXT NOT NULL DEFAULT '',
              updated_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS m24_professional_assignment(
              id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              product_code TEXT NOT NULL,
              specialist_id TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('offered','held','accepted','rejected','expired','reassigned','completed','cancelled')),
              conflict_status TEXT NOT NULL CHECK(conflict_status IN ('pending','clear','conflict','needs_review')),
              offer_reason TEXT NOT NULL,
              decision_note TEXT NOT NULL DEFAULT '',
              match_score INTEGER NOT NULL,
              response_due_at TEXT NOT NULL,
              review_due_at TEXT,
              offered_by TEXT NOT NULL,
              offered_at TEXT NOT NULL,
              decided_at TEXT,
              completed_at TEXT,
              previous_assignment_id TEXT,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(specialist_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_m24_assignment_case ON m24_professional_assignment(case_id,status,updated_at);
            CREATE INDEX IF NOT EXISTS idx_m24_assignment_specialist ON m24_professional_assignment(specialist_id,status,response_due_at);
            CREATE TABLE IF NOT EXISTS m24_professional_conflict(
              id TEXT PRIMARY KEY,
              assignment_id TEXT NOT NULL UNIQUE,
              case_id TEXT NOT NULL,
              specialist_id TEXT NOT NULL,
              declaration TEXT NOT NULL CHECK(declaration IN ('clear','conflict','needs_review')),
              party_hashes_json TEXT NOT NULL,
              relationship_category TEXT NOT NULL,
              note_redacted TEXT NOT NULL,
              resolution_status TEXT NOT NULL CHECK(resolution_status IN ('not_required','pending','cleared','blocked')),
              declared_at TEXT NOT NULL,
              resolved_by TEXT,
              resolved_at TEXT,
              resolution_note TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(assignment_id) REFERENCES m24_professional_assignment(id),
              FOREIGN KEY(case_id) REFERENCES cases(id),
              FOREIGN KEY(specialist_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS m24_professional_event(
              id TEXT PRIMARY KEY,
              entity_type TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              actor_role TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_m24_prof_event_entity ON m24_professional_event(entity_type,entity_id,created_at);
            """
        )

    def _event(self, con, entity_type: str, entity_id: str, event_type: str, actor: dict[str, Any], detail: dict[str, Any]):
        con.execute(
            "INSERT INTO m24_professional_event VALUES(?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()), entity_type, entity_id, event_type,
                str(actor.get("id") or ""), str(actor.get("role") or ""),
                json.dumps(detail, ensure_ascii=False, sort_keys=True), self.now(),
            ),
        )

    @staticmethod
    def _require_role(actor: dict[str, Any], *roles: str) -> None:
        if actor.get("role") not in set(roles):
            raise PermissionError("El rol actual no tiene permiso para esta operación profesional.")

    @staticmethod
    def _user(con, user_id: str):
        row = con.execute("SELECT id,name,email,role,specialty,verified FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            raise LookupError("Usuario profesional no encontrado.")
        return row

    @staticmethod
    def _case(con, case_id: str):
        row = con.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not row:
            raise LookupError("Expediente no encontrado.")
        return row

    def _validate_product_codes(self, values: Any) -> list[str]:
        codes = list(dict.fromkeys(str(item).upper() for item in (values or [])))
        if not codes or any(code not in self.product_codes for code in codes):
            raise ValueError("Debe seleccionar productos jurídicos válidos para el perfil profesional.")
        return codes

    def _profile_from_row(self, row) -> dict[str, Any]:
        item = dict(row)
        item["specialties"] = self._json(item.pop("specialties_json"), [])
        item["product_codes"] = self._json(item.pop("product_codes_json"), [])
        item["fee_reference"] = self._json(item.pop("fee_reference_json"), {})
        item["bar_registration"] = f"••••{item.pop('bar_registration_last4')}"
        return item

    def _profile(self, con, user_id: str) -> dict[str, Any] | None:
        row = con.execute(
            """SELECT p.*,u.name,u.email,u.specialty AS account_specialty,u.verified AS account_verified
               FROM m24_professional_profile p JOIN users u ON u.id=p.user_id WHERE p.user_id=?""",
            (user_id,),
        ).fetchone()
        return self._profile_from_row(row) if row else None

    def _assignment_from_row(self, con, row) -> dict[str, Any]:
        item = dict(row)
        conflict = con.execute(
            "SELECT declaration,relationship_category,resolution_status,declared_at,resolved_at,party_hashes_json FROM m24_professional_conflict WHERE assignment_id=?",
            (item["id"],),
        ).fetchone()
        if conflict:
            c = dict(conflict)
            hashes = self._json(c.pop("party_hashes_json"), [])
            c["party_hash_count"] = len(hashes)
            item["conflict"] = c
        else:
            item["conflict"] = None
        now = self.now_dt()
        response_due = datetime.fromisoformat(item["response_due_at"])
        review_due = datetime.fromisoformat(item["review_due_at"]) if item.get("review_due_at") else None
        item["response_sla_status"] = "overdue" if item["status"] == "offered" and response_due < now else "on_time"
        item["review_sla_status"] = "overdue" if item["status"] == "accepted" and review_due and review_due < now else "on_time"
        return item

    def _assignments(self, con, where: str = "1=1", params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        rows = con.execute(
            f"""SELECT a.*,c.title AS case_title,c.risk,u.name AS specialist_name
                FROM m24_professional_assignment a
                JOIN cases c ON c.id=a.case_id JOIN users u ON u.id=a.specialist_id
                WHERE {where} ORDER BY a.updated_at DESC""",
            params,
        ).fetchall()
        return [self._assignment_from_row(con, row) for row in rows]

    def invite_profile(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        self._require_role(actor, "admin")
        if str(data.get("confirmation") or "").strip() != self.confirmations["invite"]:
            raise ValueError(f"Debe escribir exactamente: {self.confirmations['invite']}")
        specialist_id = str(data.get("specialist_id") or "").strip()
        user = self._user(con, specialist_id)
        if user["role"] != "specialist":
            raise ValueError("La invitación solo puede dirigirse a una cuenta con rol especialista.")
        jurisdiction = str(data.get("jurisdiction") or "Colombia").strip()
        if jurisdiction not in set(self.policy.get("jurisdictions") or []):
            raise ValueError("La jurisdicción no está habilitada para este piloto.")
        codes = self._validate_product_codes(data.get("product_codes"))
        specialties = [str(item).strip()[:120] for item in (data.get("specialties") or []) if str(item).strip()]
        if not specialties:
            specialties = list(dict.fromkeys(self.product_specialty_map[code] for code in codes))
        last4 = re.sub(r"\D", "", str(data.get("bar_registration_last4") or ""))[-4:]
        if len(last4) != 4:
            raise ValueError("Registre únicamente los últimos cuatro dígitos de la tarjeta profesional.")
        max_cases = int(data.get("max_active_cases") or self.policy["default_max_active_cases"])
        if max_cases < 1 or max_cases > int(self.policy["absolute_max_active_cases"]):
            raise ValueError("La capacidad profesional está fuera del rango permitido.")
        response_sla = int(data.get("response_sla_hours") or self.policy["response_sla_hours"])
        review_sla = int(data.get("review_sla_hours") or 48)
        if response_sla < 1 or review_sla < 1:
            raise ValueError("Los SLA deben expresarse en horas positivas.")
        fee_reference = data.get("fee_reference") or {"mode": "pilot_reference_only", "amount_cop": 0}
        now = self.now()
        con.execute(
            """INSERT INTO m24_professional_profile
               (user_id,invitation_status,verification_status,jurisdiction,bar_registration_last4,specialties_json,
                product_codes_json,availability_status,max_active_cases,response_sla_hours,review_sla_hours,
                fee_reference_json,invited_by,invited_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET invitation_status='invited',verification_status='pending',
                jurisdiction=excluded.jurisdiction,bar_registration_last4=excluded.bar_registration_last4,
                specialties_json=excluded.specialties_json,product_codes_json=excluded.product_codes_json,
                availability_status=excluded.availability_status,max_active_cases=excluded.max_active_cases,
                response_sla_hours=excluded.response_sla_hours,review_sla_hours=excluded.review_sla_hours,
                fee_reference_json=excluded.fee_reference_json,invited_by=excluded.invited_by,
                invited_at=excluded.invited_at,accepted_at=NULL,verified_by=NULL,verified_at=NULL,
                verification_note='',updated_at=excluded.updated_at""",
            (
                specialist_id, "invited", "pending", jurisdiction, last4,
                json.dumps(specialties, ensure_ascii=False), json.dumps(codes), "available", max_cases,
                response_sla, review_sla, json.dumps(fee_reference, ensure_ascii=False),
                str(actor.get("id")), now, now,
            ),
        )
        self._event(con, "professional_profile", specialist_id, "invited", actor, {"product_codes": codes, "max_active_cases": max_cases})
        con.commit()
        return self._profile(con, specialist_id) or {}

    def accept_invitation(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        self._require_role(actor, "specialist")
        if str(data.get("confirmation") or "").strip() != self.confirmations["accept_invitation"]:
            raise ValueError(f"Debe escribir exactamente: {self.confirmations['accept_invitation']}")
        profile = self._profile(con, str(actor.get("id")))
        if not profile or profile["invitation_status"] != "invited":
            raise LookupError("No existe una invitación profesional pendiente.")
        now = self.now()
        con.execute(
            "UPDATE m24_professional_profile SET invitation_status='accepted',accepted_at=?,updated_at=? WHERE user_id=?",
            (now, now, str(actor.get("id"))),
        )
        self._event(con, "professional_profile", str(actor.get("id")), "invitation_accepted", actor, {"policy_version": self.policy["version"]})
        con.commit()
        return self._profile(con, str(actor.get("id"))) or {}

    def verify_profile(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        self._require_role(actor, "admin")
        if str(data.get("confirmation") or "").strip() != self.confirmations["verify"]:
            raise ValueError(f"Debe escribir exactamente: {self.confirmations['verify']}")
        specialist_id = str(data.get("specialist_id") or "").strip()
        profile = self._profile(con, specialist_id)
        if not profile or profile["invitation_status"] != "accepted":
            raise ValueError("El especialista debe aceptar la invitación antes de la verificación.")
        decision = str(data.get("decision") or "verified").lower()
        if decision not in {"verified", "suspended"}:
            raise ValueError("La decisión de verificación no es válida.")
        note = self._redact_note(data.get("note") or "")
        if len(note) < 20:
            raise ValueError("Registre evidencia o fundamento de al menos 20 caracteres.")
        now = self.now()
        con.execute(
            """UPDATE m24_professional_profile SET verification_status=?,verified_by=?,verified_at=?,
               verification_note=?,updated_at=? WHERE user_id=?""",
            (decision, str(actor.get("id")), now, note, now, specialist_id),
        )
        self._event(con, "professional_profile", specialist_id, f"verification_{decision}", actor, {"note": note})
        con.commit()
        return self._profile(con, specialist_id) or {}

    def set_availability(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        target = str(data.get("specialist_id") or actor.get("id") or "")
        if actor.get("role") == "specialist" and target != str(actor.get("id")):
            raise PermissionError("El especialista solo puede modificar su propia disponibilidad.")
        self._require_role(actor, "specialist", "admin")
        profile = self._profile(con, target)
        if not profile:
            raise LookupError("Perfil profesional no encontrado.")
        status = str(data.get("availability_status") or "").lower()
        if status not in {"available", "limited", "unavailable"}:
            raise ValueError("Estado de disponibilidad no válido.")
        now = self.now()
        con.execute("UPDATE m24_professional_profile SET availability_status=?,updated_at=? WHERE user_id=?", (status, now, target))
        self._event(con, "professional_profile", target, "availability_changed", actor, {"availability_status": status})
        con.commit()
        return self._profile(con, target) or {}

    def _active_count(self, con, specialist_id: str) -> int:
        return int(con.execute(
            "SELECT COUNT(*) FROM m24_professional_assignment WHERE specialist_id=? AND status IN ('held','accepted')",
            (specialist_id,),
        ).fetchone()[0])

    def offer_assignment(self, con, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        self._require_role(actor, "admin")
        if str(data.get("confirmation") or "").strip() != self.confirmations["offer"]:
            raise ValueError(f"Debe escribir exactamente: {self.confirmations['offer']}")
        case_id = str(data.get("case_id") or "").strip()
        specialist_id = str(data.get("specialist_id") or "").strip()
        case = self._case(con, case_id)
        profile = self._profile(con, specialist_id)
        if not profile or profile["invitation_status"] != "accepted" or profile["verification_status"] != "verified":
            raise ValueError("El especialista debe estar invitado, aceptado y verificado.")
        if profile["availability_status"] == "unavailable":
            raise ValueError("El especialista está marcado como no disponible.")
        product_code = str(case["product_code"]).upper()
        if product_code not in set(profile["product_codes"]):
            raise ValueError("El producto no está habilitado en el perfil del especialista.")
        if self._active_count(con, specialist_id) >= int(profile["max_active_cases"]):
            raise ValueError("El especialista alcanzó su capacidad activa.")
        existing = con.execute(
            "SELECT id,status FROM m24_professional_assignment WHERE case_id=? AND status IN ('offered','held','accepted')",
            (case_id,),
        ).fetchone()
        if existing:
            raise ValueError("El expediente ya tiene una oferta o asignación profesional activa.")
        reason = self._redact_note(data.get("reason") or "")
        if len(reason) < 20:
            raise ValueError("La oferta requiere una justificación de al menos 20 caracteres.")
        now_dt = self.now_dt()
        response_due = now_dt + timedelta(hours=int(profile["response_sla_hours"]))
        risk = str(case["risk"] or "yellow").lower()
        risk_sla = int((self.policy.get("review_sla_hours_by_risk") or {}).get(risk, profile["review_sla_hours"]))
        slack = max(0, int(profile["max_active_cases"]) - self._active_count(con, specialist_id))
        score = min(100, 60 + (15 if profile["availability_status"] == "available" else 5) + min(20, slack * 4) + 5)
        assignment_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO m24_professional_assignment
               (id,case_id,product_code,specialist_id,status,conflict_status,offer_reason,match_score,
                response_due_at,offered_by,offered_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                assignment_id, case_id, product_code, specialist_id, "offered", "pending", reason,
                score, response_due.isoformat(), str(actor.get("id")), now_dt.isoformat(), now_dt.isoformat(),
            ),
        )
        self._event(con, "professional_assignment", assignment_id, "offered", actor, {"case_id": case_id, "specialist_id": specialist_id, "match_score": score, "planned_review_sla_hours": risk_sla})
        con.commit()
        return self._assignments(con, "a.id=?", (assignment_id,))[0]

    def decide_assignment(self, con, assignment_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        self._require_role(actor, "specialist")
        row = con.execute("SELECT * FROM m24_professional_assignment WHERE id=?", (assignment_id,)).fetchone()
        if not row:
            raise LookupError("Oferta profesional no encontrada.")
        if row["specialist_id"] != str(actor.get("id")):
            raise PermissionError("La oferta corresponde a otro especialista.")
        if row["status"] != "offered":
            raise ValueError("La oferta ya fue decidida o no está disponible.")
        action = str(data.get("action") or "").lower()
        note = self._redact_note(data.get("note") or "")
        now_dt = self.now_dt()
        if action == "reject":
            if len(note) < 12:
                raise ValueError("Indique brevemente el motivo del rechazo.")
            con.execute(
                "UPDATE m24_professional_assignment SET status='rejected',decision_note=?,decided_at=?,updated_at=? WHERE id=?",
                (note, now_dt.isoformat(), now_dt.isoformat(), assignment_id),
            )
            self._event(con, "professional_assignment", assignment_id, "rejected", actor, {"reason": note})
            con.commit()
            return self._assignments(con, "a.id=?", (assignment_id,))[0]
        if action != "accept":
            raise ValueError("La decisión debe ser aceptar o rechazar.")
        if str(data.get("confirmation") or "").strip() != self.confirmations["accept_assignment"]:
            raise ValueError(f"Debe escribir exactamente: {self.confirmations['accept_assignment']}")
        declaration = str(data.get("conflict_declaration") or "").lower()
        if declaration not in {"clear", "conflict", "needs_review"}:
            raise ValueError("Debe declarar el estado del conflicto de interés.")
        parties = list(data.get("parties") or [])
        party_hashes = self._hash_parties(parties)
        if not party_hashes:
            raise ValueError("Debe contrastar al menos una parte o entidad del expediente.")
        relationship = str(data.get("relationship_category") or "none").strip()[:80]
        conflict_note = self._redact_note(data.get("conflict_note") or "", parties)
        resolution_status = "not_required" if declaration == "clear" else "blocked" if declaration == "conflict" else "pending"
        conflict_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO m24_professional_conflict
               (id,assignment_id,case_id,specialist_id,declaration,party_hashes_json,relationship_category,
                note_redacted,resolution_status,declared_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                conflict_id, assignment_id, row["case_id"], row["specialist_id"], declaration,
                json.dumps(party_hashes), relationship, conflict_note, resolution_status, now_dt.isoformat(),
            ),
        )
        if declaration == "clear":
            case = self._case(con, row["case_id"])
            risk = str(case["risk"] or "yellow").lower()
            review_hours = int((self.policy.get("review_sla_hours_by_risk") or {}).get(risk, 48))
            review_due = now_dt + timedelta(hours=review_hours)
            con.execute(
                """UPDATE m24_professional_assignment SET status='accepted',conflict_status='clear',decision_note=?,
                   decided_at=?,review_due_at=?,updated_at=? WHERE id=?""",
                (note, now_dt.isoformat(), review_due.isoformat(), now_dt.isoformat(), assignment_id),
            )
            con.execute(
                "UPDATE cases SET specialist_id=?,review_status='Asignado',updated_at=? WHERE id=?",
                (str(actor.get("id")), now_dt.isoformat(), row["case_id"]),
            )
            event_type = "accepted_after_clear_conflict_check"
        elif declaration == "needs_review":
            con.execute(
                """UPDATE m24_professional_assignment SET status='held',conflict_status='needs_review',decision_note=?,
                   decided_at=?,updated_at=? WHERE id=?""",
                (note, now_dt.isoformat(), now_dt.isoformat(), assignment_id),
            )
            event_type = "held_for_conflict_review"
        else:
            con.execute(
                """UPDATE m24_professional_assignment SET status='rejected',conflict_status='conflict',decision_note=?,
                   decided_at=?,updated_at=? WHERE id=?""",
                (note, now_dt.isoformat(), now_dt.isoformat(), assignment_id),
            )
            event_type = "blocked_by_conflict"
        self._event(con, "professional_assignment", assignment_id, event_type, actor, {"declaration": declaration, "party_hash_count": len(party_hashes), "raw_parties_stored": False})
        con.commit()
        return self._assignments(con, "a.id=?", (assignment_id,))[0]

    def resolve_conflict(self, con, assignment_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        self._require_role(actor, "admin")
        if str(data.get("confirmation") or "").strip() != self.confirmations["resolve_conflict"]:
            raise ValueError(f"Debe escribir exactamente: {self.confirmations['resolve_conflict']}")
        row = con.execute("SELECT * FROM m24_professional_assignment WHERE id=?", (assignment_id,)).fetchone()
        conflict = con.execute("SELECT * FROM m24_professional_conflict WHERE assignment_id=?", (assignment_id,)).fetchone()
        if not row or not conflict:
            raise LookupError("Declaración de conflicto no encontrada.")
        if row["status"] != "held" or conflict["resolution_status"] != "pending":
            raise ValueError("La declaración no requiere una resolución pendiente.")
        decision = str(data.get("decision") or "").lower()
        if decision not in {"clear", "block"}:
            raise ValueError("La resolución debe ser clear o block.")
        note = self._redact_note(data.get("note") or "")
        if len(note) < 20:
            raise ValueError("La resolución requiere fundamento de al menos 20 caracteres.")
        now_dt = self.now_dt()
        if decision == "clear":
            case = self._case(con, row["case_id"])
            risk = str(case["risk"] or "yellow").lower()
            hours = int((self.policy.get("review_sla_hours_by_risk") or {}).get(risk, 48))
            con.execute(
                """UPDATE m24_professional_assignment SET status='accepted',conflict_status='clear',review_due_at=?,
                   updated_at=? WHERE id=?""",
                ((now_dt + timedelta(hours=hours)).isoformat(), now_dt.isoformat(), assignment_id),
            )
            con.execute(
                "UPDATE cases SET specialist_id=?,review_status='Asignado',updated_at=? WHERE id=?",
                (row["specialist_id"], now_dt.isoformat(), row["case_id"]),
            )
            resolution_status = "cleared"
        else:
            con.execute(
                "UPDATE m24_professional_assignment SET status='rejected',conflict_status='conflict',updated_at=? WHERE id=?",
                (now_dt.isoformat(), assignment_id),
            )
            resolution_status = "blocked"
        con.execute(
            """UPDATE m24_professional_conflict SET resolution_status=?,resolved_by=?,resolved_at=?,resolution_note=?
               WHERE assignment_id=?""",
            (resolution_status, str(actor.get("id")), now_dt.isoformat(), note, assignment_id),
        )
        self._event(con, "professional_assignment", assignment_id, f"conflict_{resolution_status}", actor, {"note": note})
        con.commit()
        return self._assignments(con, "a.id=?", (assignment_id,))[0]

    def complete_assignment(self, con, assignment_id: str, data: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        self._require_role(actor, "specialist", "admin")
        row = con.execute("SELECT * FROM m24_professional_assignment WHERE id=?", (assignment_id,)).fetchone()
        if not row:
            raise LookupError("Asignación profesional no encontrada.")
        if actor.get("role") == "specialist" and row["specialist_id"] != str(actor.get("id")):
            raise PermissionError("La asignación corresponde a otro especialista.")
        if row["status"] != "accepted":
            raise ValueError("Solo una asignación aceptada puede cerrarse.")
        if str(data.get("confirmation") or "").strip() != self.confirmations["complete"]:
            raise ValueError(f"Debe escribir exactamente: {self.confirmations['complete']}")
        note = self._redact_note(data.get("note") or "")
        if len(note) < 20:
            raise ValueError("Registre el alcance del cierre profesional.")
        now = self.now()
        con.execute(
            "UPDATE m24_professional_assignment SET status='completed',decision_note=?,completed_at=?,updated_at=? WHERE id=?",
            (note, now, now, assignment_id),
        )
        self._event(con, "professional_assignment", assignment_id, "completed_without_auto_approval", actor, {"note": note, "legal_approval_mutated": False})
        con.commit()
        return self._assignments(con, "a.id=?", (assignment_id,))[0]

    def summary(self, con, actor: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema(con)
        self._require_role(actor, "specialist", "admin")
        role = actor.get("role")
        if role == "specialist":
            profile = self._profile(con, str(actor.get("id")))
            assignments = self._assignments(con, "a.specialist_id=?", (str(actor.get("id")),))
            active = sum(1 for row in assignments if row["status"] in {"held", "accepted"})
            return {
                "mode": self.policy["mode"], "policy_version": self.policy["version"],
                "profile": profile, "assignments": assignments,
                "metrics": {
                    "offers_pending": sum(1 for row in assignments if row["status"] == "offered"),
                    "active_assignments": active,
                    "capacity": int(profile["max_active_cases"]) if profile else 0,
                    "response_sla_overdue": sum(1 for row in assignments if row["response_sla_status"] == "overdue"),
                    "review_sla_overdue": sum(1 for row in assignments if row["review_sla_status"] == "overdue"),
                },
                "commercial": self.policy["commercial"],
                "production_blockers": self.policy["production_blockers"],
            }
        profiles = [self._profile_from_row(row) for row in con.execute(
            """SELECT p.*,u.name,u.email,u.specialty AS account_specialty,u.verified AS account_verified
               FROM m24_professional_profile p JOIN users u ON u.id=p.user_id ORDER BY p.updated_at DESC"""
        ).fetchall()]
        eligible_specialists = [dict(row) for row in con.execute(
            """SELECT u.id,u.name,u.email,u.specialty,u.verified,
                      CASE WHEN p.user_id IS NULL THEN 0 ELSE 1 END AS profile_exists
               FROM users u LEFT JOIN m24_professional_profile p ON p.user_id=u.id
               WHERE u.role='specialist' ORDER BY u.name"""
        ).fetchall()]
        assignments = self._assignments(con)
        unassigned_cases = [dict(row) for row in con.execute(
            """SELECT c.id,c.product_code,c.title,c.risk,c.status,c.updated_at
               FROM cases c WHERE c.specialist_id IS NULL AND NOT EXISTS(
                 SELECT 1 FROM m24_professional_assignment a WHERE a.case_id=c.id AND a.status IN ('offered','held','accepted')
               ) ORDER BY c.updated_at DESC LIMIT 50"""
        ).fetchall()]
        return {
            "mode": self.policy["mode"], "policy_version": self.policy["version"],
            "profiles": profiles, "eligible_specialists": eligible_specialists, "assignments": assignments, "unassigned_cases": unassigned_cases,
            "metrics": {
                "invited_profiles": len(profiles),
                "verified_profiles": sum(1 for row in profiles if row["verification_status"] == "verified"),
                "available_profiles": sum(1 for row in profiles if row["availability_status"] != "unavailable" and row["verification_status"] == "verified"),
                "pending_offers": sum(1 for row in assignments if row["status"] == "offered"),
                "held_conflicts": sum(1 for row in assignments if row["status"] == "held"),
                "active_assignments": sum(1 for row in assignments if row["status"] == "accepted"),
                "overdue_slas": sum(1 for row in assignments if row["response_sla_status"] == "overdue" or row["review_sla_status"] == "overdue"),
            },
            "privacy": self.policy["privacy"], "commercial": self.policy["commercial"],
            "production_blockers": self.policy["production_blockers"],
        }
