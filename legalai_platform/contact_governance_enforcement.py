from __future__ import annotations

"""Refuerzos fail-closed para la compuerta M32.9.

Mantiene el motor base aislado y añade vinculación exacta entre decisión y
contacto, validación de sujetos, métricas acotadas por rol e integridad cruzada
M32.7/M32.8/M32.9 antes de procesar cualquier despacho.
"""

from hashlib import sha256
from typing import Any

from legalai_platform.approval_desk_workspace import ApprovalDeskError, PermissionDenied
from legalai_platform.approval_notification_center import NotificationIntegrityError
from legalai_platform.contact_governance import (
    CHANNELS,
    PURPOSES,
    ContactGovernance,
    ContactGovernanceIntegrityError,
    GovernedTransactionalCommunications,
)
from legalai_platform.transactional_communications import CommunicationsIntegrityError


class EnforcedContactGovernance(ContactGovernance):
    """Versión activa con controles de identidad interna y enlace de evidencia."""

    def _active_subject(self, subject_id: str) -> dict[str, Any]:
        profile = self._subject_profile(subject_id)
        if not profile or not bool(profile.get("active")):
            raise ApprovalDeskError("El titular no existe o está inactivo en el directorio autorizado.")
        return profile

    def record_relationship(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede registrar relaciones de contacto.")
        subject_id = str((payload or {}).get("subject_id") or "").strip()
        self._active_subject(subject_id)
        return super().record_relationship(user, payload)

    def record_preference(self, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if user.get("role") not in {"admin", "qa"}:
            raise PermissionDenied("El registro verificado de preferencias requiere administración o QA.")
        subject_id = str((payload or {}).get("subject_id") or "").strip()
        self._active_subject(subject_id)
        state_value = str((payload or {}).get("state") or "").strip().casefold()
        if state_value == "denied" and not (
            str((payload or {}).get("reason") or "").strip()
            or str((payload or {}).get("evidence_reference") or "").strip()
        ):
            raise ApprovalDeskError("Una negativa o revocatoria requiere motivo o referencia de evidencia.")
        return super().record_preference(user, payload)

    def evaluate(self, user: dict[str, Any], **kwargs) -> dict[str, Any]:
        subject_id = str(kwargs.get("subject_id") or "").strip()
        if user.get("role") == "specialist" and str(user.get("id")) != subject_id:
            raise PermissionDenied("El especialista solo puede evaluar sus propias preferencias de contacto.")
        if user.get("role") not in {"specialist", "admin", "qa"}:
            raise PermissionDenied("La evaluación requiere un actor profesional autenticado.")
        integrity = self.verify_chain()
        if not integrity["valid"]:
            raise ContactGovernanceIntegrityError("La evaluación está bloqueada por una cadena M32.9 inválida.")
        record = bool(kwargs.pop("record", True))
        result = super().evaluate(user, record=False, **kwargs)
        decision = result["decision"]
        profile = self._subject_profile(decision["subject_id"])
        if not profile or not bool(profile.get("active")):
            reasons = sorted(set([*decision.get("reasons", []), "inactive_or_unknown_subject"]))
            decision["reasons"] = reasons
            decision["allowed"] = False
            decision["outcome"] = "blocked"
            decision["declared_basis"] = None
        if record:
            event = self._append("decision.recorded", user, {"decision": decision})
            return {"event": event, "decision": decision}
        return {"decision": decision}

    def record_contact(
        self,
        user: dict[str, Any],
        *,
        decision_id: str,
        subject_id: str,
        purpose: str,
        channel: str,
        dispatch_id: str,
        occurred_at=None,
        synthetic: bool = True,
    ) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede registrar ejecuciones de contacto.")
        state = self._state()
        decision = next((item for item in state["decisions"] if item.get("decision_id") == decision_id), None)
        if not decision or not decision.get("allowed"):
            raise ApprovalDeskError("El contacto requiere una decisión permitida y trazable.")
        normalized_purpose = str(purpose or "").strip().casefold()
        normalized_channel = str(channel or "").strip().casefold()
        if normalized_purpose not in PURPOSES or normalized_channel not in CHANNELS:
            raise ApprovalDeskError("La finalidad o el canal del contacto no son válidos.")
        if (
            str(decision.get("subject_id")) != str(subject_id)
            or decision.get("purpose") != normalized_purpose
            or decision.get("channel") != normalized_channel
        ):
            raise ApprovalDeskError("El contacto no coincide con el titular, finalidad y canal autorizados.")
        dispatch_value = str(dispatch_id or "").strip()
        if sha256(dispatch_value.encode("utf-8")).hexdigest() != decision.get("context_sha256"):
            raise ApprovalDeskError("El despacho no coincide con el contexto exacto de la decisión.")
        if any(
            item.get("decision_id") == decision_id or item.get("dispatch_id") == dispatch_value
            for item in state["contacts"]
        ):
            raise ApprovalDeskError("La decisión o el despacho ya fueron registrados como contacto.")
        return super().record_contact(
            user,
            decision_id=decision_id,
            subject_id=subject_id,
            purpose=normalized_purpose,
            channel=normalized_channel,
            dispatch_id=dispatch_value,
            occurred_at=occurred_at,
            synthetic=synthetic,
        )

    def dashboard(self, user: dict[str, Any]) -> dict[str, Any]:
        payload = super().dashboard(user)
        if user.get("role") == "specialist":
            state = self._state()
            actor_id = str(user.get("id"))
            payload["metrics"]["relationships"] = int(actor_id in state["relationships"])
            payload["metrics"]["synthetic_contacts"] = sum(
                item.get("subject_id") == actor_id for item in state["contacts"]
            )
        return payload


class EnforcedGovernedTransactionalCommunications(GovernedTransactionalCommunications):
    """Procesamiento M32.8 sujeto a integridad cruzada y gobierno reforzado."""

    def __init__(self, *args, governance: ContactGovernance | None = None, **kwargs):
        super().__init__(*args, governance=governance, **kwargs)
        if governance is None:
            self.governance = EnforcedContactGovernance(
                self.root,
                db_factory=self.db_factory,
                now_factory=self.now_factory,
            )

    def process(self, user: dict[str, Any], *, limit: int | None = None) -> dict[str, Any]:
        if user.get("role") != "admin":
            raise PermissionDenied("Solo administración puede procesar despachos.")
        if not self.verify_chain()["valid"]:
            raise CommunicationsIntegrityError("El procesamiento está bloqueado por una cadena M32.8 inválida.")
        if not self.notification_center.verify_chain()["valid"]:
            raise NotificationIntegrityError("El procesamiento está bloqueado por una cadena M32.7 inválida.")
        if not self.governance.verify_chain()["valid"]:
            raise ContactGovernanceIntegrityError("El procesamiento está bloqueado por una cadena M32.9 inválida.")
        return super().process(user, limit=limit)


__all__ = [
    "EnforcedContactGovernance",
    "EnforcedGovernedTransactionalCommunications",
]
