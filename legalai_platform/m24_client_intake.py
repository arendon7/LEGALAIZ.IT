from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


class M24ClientIntakeCenter:
    """Explainable intake and offer layer for the controlled M24.6 pilot.

    This component classifies a short user narrative through deterministic,
    auditable rules. It does not generate a legal conclusion, publish M23.2,
    persist the narrative, or replace the product-specific questionnaire.
    """

    MAX_TEXT = 4000
    MIN_TEXT = 12

    PROFILES: dict[str, dict[str, Any]] = {
        "CO-LA-001": {
            "phrases": {
                "liquidacion laboral": 8, "liquidacion final": 8, "prestaciones sociales": 7,
                "cesantias": 6, "prima de servicios": 5, "vacaciones pendientes": 5,
                "indemnizacion por despido": 7, "me despidieron": 6, "no me pagaron la liquidacion": 10,
                "salarios pendientes": 5, "terminacion del contrato": 3,
            },
            "reason": "La situación parece referirse al cálculo o reclamación de acreencias derivadas de una relación laboral terminada.",
        },
        "CO-LA-002": {
            "phrases": {
                "contrato laboral": 9, "contrato de trabajo": 9, "contratar empleado": 8,
                "contratar trabajador": 8, "empleada domestica": 7, "mayordomo": 6,
                "mensajero": 5, "nomina": 4, "salario": 2, "periodo de prueba": 5,
                "trabajo remoto": 3, "teletrabajo": 4, "jornada laboral": 4,
            },
            "reason": "La necesidad apunta a formalizar una relación laboral y definir modalidad, funciones, jornada, remuneración y controles aplicables.",
        },
        "CO-EM-003": {
            "phrases": {
                "prestacion de servicios": 10, "contrato de servicios": 8, "contratista": 6,
                "honorarios": 5, "consultor": 4, "proveedor de servicios": 5,
                "entregables": 4, "independiente": 3, "subordinacion": 5,
            },
            "reason": "La necesidad parece corresponder a una contratación independiente con alcance, entregables, honorarios y asignación de riesgos.",
        },
        "CO-EM-004": {
            "phrases": {
                "confidencialidad": 8, "acuerdo de confidencialidad": 10, "nda": 9,
                "secreto empresarial": 8, "informacion reservada": 6, "propiedad intelectual": 7,
                "codigo fuente": 5, "software": 3, "licencia de software": 5,
                "datos personales": 3, "inteligencia artificial": 3,
            },
            "reason": "La situación exige delimitar información protegida, acceso, uso permitido, propiedad intelectual, datos o tecnología.",
        },
        "CO-AR-001": {
            "phrases": {
                "contrato de arrendamiento": 10, "arrendamiento de vivienda": 10, "arriendo": 7,
                "arrendar apartamento": 8, "arrendar casa": 8, "inquilino": 6,
                "arrendatario": 6, "arrendador": 6, "canon": 4, "inventario del inmueble": 5,
                "restitucion del inmueble": 5,
            },
            "reason": "La necesidad se relaciona con la formalización o gestión de un arrendamiento de vivienda urbana.",
        },
        "CO-SA-001": {
            "phrases": {
                "eps": 7, "ips": 6, "historia clinica": 8, "medicamento": 5,
                "cita medica": 5, "autorizacion": 4, "procedimiento medico": 5,
                "derecho de peticion salud": 10, "supersalud": 7, "continuidad del tratamiento": 6,
                "no me atienden": 5,
            },
            "reason": "La situación parece requerir una petición o reclamación documentada ante una EPS, IPS u otro actor de salud.",
        },
        "CO-CD-001": {
            "phrases": {
                "datacredito": 10, "transunion": 8, "central de riesgo": 9, "centrales de riesgo": 9,
                "reporte negativo": 8, "habeas data": 9, "deuda ya pagada": 8,
                "me reportaron": 8, "eliminar reporte": 6, "corregir reporte": 7,
                "historial crediticio": 5,
            },
            "reason": "La situación se refiere al acceso, corrección, actualización o permanencia de información financiera reportada.",
        },
        "CO-CD-003": {
            "phrases": {
                "garantia": 7, "producto defectuoso": 9, "servicio defectuoso": 8,
                "retracto": 9, "reversion del pago": 10, "devolucion del dinero": 7,
                "compra no entregada": 9, "no entregaron": 7, "debito automatico": 6,
                "consumidor": 4, "reclamo al vendedor": 6,
            },
            "reason": "La situación parece corresponder a garantía legal, retracto, reversión, falta de entrega u otra reclamación de consumo.",
        },
        "CO-CD-004": {
            "phrases": {
                "acuerdo de pago": 10, "pagare": 9, "cobrar una deuda": 8, "cobro de cartera": 8,
                "deudor": 5, "acreedor": 5, "saldo pendiente": 5, "cuotas": 3,
                "mora": 4, "carta de instrucciones": 7, "requerimiento de pago": 7,
            },
            "reason": "La necesidad apunta a documentar, negociar o recuperar una obligación civil o comercial.",
        },
        "CO-TR-001": {
            "phrases": {
                "sast": 10, "camara autorizada": 8, "fotodeteccion autorizada": 8,
                "dispositivo de fotodeteccion": 7, "punto de fotodeteccion": 7,
                "verificar la camara": 7, "autorizacion del dispositivo": 8,
            },
            "reason": "La consulta parece centrarse en verificar el estado técnico u oficial de un sistema de fotodetección.",
        },
        "CO-TR-002": {
            "phrases": {
                "fotomulta": 10, "comparendo electronico": 9, "no me notificaron": 9,
                "sin notificacion": 8, "simit": 7, "runt": 4, "multa de transito": 7,
                "camara de transito": 6, "audiencia de transito": 6, "fotodeteccion": 5,
            },
            "reason": "La situación parece requerir reconstruir la notificación, el expediente y el debido proceso de una fotodetección.",
        },
    }

    HIGH_RISK_SIGNALS = (
        ("urgencia_vital", ("urgencia vital", "riesgo de muerte", "vida esta en riesgo", "medicamento urgente", "no puedo respirar", "emergencia medica", "deterioro grave"),
         "La descripción sugiere una posible urgencia asistencial. La plataforma no sustituye atención médica inmediata."),
        ("proceso_activo", ("proceso judicial", "demanda activa", "audiencia mañana", "audiencia hoy", "tutela activa", "mandamiento de pago", "embargo"),
         "Existe una actuación o término que puede requerir revisión profesional inmediata y coordinación con el expediente existente."),
        ("fraude_suplantacion", ("suplantacion", "clonacion", "fraude", "robo de identidad"),
         "Los hechos pueden involucrar fraude o suplantación y exigen preservar evidencia y evaluar rutas adicionales."),
        ("termino_critico", ("vence hoy", "vence mañana", "ultimo dia", "plazo vence", "me notificaron hoy"),
         "La descripción menciona un término potencialmente crítico que debe verificarse antes de confiar en un flujo automatizado."),
        ("proteccion_reforzada", ("embarazada", "fuero sindical", "discapacidad", "estabilidad reforzada", "incapacidad medica"),
         "La situación puede involucrar protección constitucional o laboral reforzada y requiere revisión especializada."),
    )

    def __init__(self, root: Path, products: list[dict[str, Any]]):
        self.root = Path(root)
        payload = json.loads((self.root / "config" / "legal_products_registry.json").read_text(encoding="utf-8"))
        self.registry = {row["product_code"]: row for row in payload.get("products", [])}
        self.products = {row["code"]: row for row in products}

    @staticmethod
    def _normalize(value: str) -> str:
        value = unicodedata.normalize("NFKD", str(value or ""))
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.lower()
        value = re.sub(r"[^a-z0-9ñ\s]", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _contains(text: str, phrase: str) -> bool:
        return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None

    def _offer(self, code: str) -> dict[str, Any]:
        product = self.products.get(code, {})
        registry = self.registry.get(code, {})
        auto = int(product.get("price_auto") or 0)
        review = int(product.get("price_review") or 0)
        allowed = set(registry.get("service_levels") or [])
        levels = []
        if "orientacion" in allowed:
            levels.append({
                "id": "orientacion", "label": "Orientación jurídica", "price": 0,
                "price_label": "Incluida en el diagnóstico del piloto",
                "includes": ["clasificación inicial", "riesgos y vacíos", "ruta recomendada"],
                "checkout_enabled": False,
            })
        if "documento_personalizado" in allowed:
            levels.append({
                "id": "documento_personalizado", "label": "Documento personalizado", "price": auto,
                "price_label": None,
                "includes": ["formulario guiado", "documentos personalizados", "expediente y trazabilidad"],
                "checkout_enabled": True,
            })
        if "solucion_revisada" in allowed:
            levels.append({
                "id": "solucion_revisada", "label": "Solución revisada", "price": auto + review,
                "price_label": None,
                "includes": ["documento personalizado", "revisión jurídica", "QA independiente", "seguimiento"],
                "checkout_enabled": True,
            })
        return {
            "product_code": code,
            "public_name": registry.get("public_name") or product.get("title") or code,
            "title": product.get("title") or registry.get("internal_name") or code,
            "problem_solved": registry.get("problem_solved") or product.get("summary") or "",
            "scope": registry.get("scope") or product.get("outcomes") or [],
            "exclusions": registry.get("exclusions") or product.get("exclusions") or [],
            "required_evidence": registry.get("required_evidence") or [],
            "risk_level": registry.get("risk_level") or product.get("base_risk") or "medium",
            "service_levels": levels,
            "pricing_status": "sandbox_reference_not_commercially_approved",
            "pricing_notice": "Valores de referencia del entorno sandbox. No constituyen una oferta comercial pública definitiva.",
        }

    def offer(self, code: str) -> dict[str, Any]:
        code = str(code or "").upper().strip()
        if code not in self.registry or code not in self.products:
            raise LookupError("Solución no encontrada.")
        return self._offer(code)

    def analyze(self, narrative: str) -> dict[str, Any]:
        raw = str(narrative or "").strip()
        if len(raw) < self.MIN_TEXT:
            raise ValueError("Describe la situación con un poco más de detalle para orientar la ruta.")
        if len(raw) > self.MAX_TEXT:
            raise ValueError(f"La descripción no puede superar {self.MAX_TEXT} caracteres.")
        text = self._normalize(raw)
        scored: list[dict[str, Any]] = []
        for code, profile in self.PROFILES.items():
            matched = []
            score = 0
            for phrase, weight in profile["phrases"].items():
                normalized_phrase = self._normalize(phrase)
                if self._contains(text, normalized_phrase):
                    score += int(weight)
                    matched.append(phrase)
            if score:
                scored.append({"code": code, "score": score, "matched": matched, "reason": profile["reason"]})
        scored.sort(key=lambda row: (-row["score"], row["code"]))

        signals = []
        for signal_id, phrases, message in self.HIGH_RISK_SIGNALS:
            matches = [phrase for phrase in phrases if self._contains(text, self._normalize(phrase))]
            if matches:
                signals.append({"id": signal_id, "matches": matches, "message": message})

        top_score = scored[0]["score"] if scored else 0
        second_score = scored[1]["score"] if len(scored) > 1 else 0
        recommendations = []
        for index, row in enumerate(scored[:3]):
            if row["score"] < 4 and index > 0:
                continue
            gap = row["score"] - (second_score if index == 0 else 0)
            confidence = "high" if row["score"] >= 9 and (index > 0 or gap >= 3) else "medium" if row["score"] >= 5 else "low"
            offer = self._offer(row["code"])
            recommendations.append({
                **offer,
                "score": row["score"],
                "confidence": confidence,
                "matched_terms": row["matched"][:6],
                "recommendation_reason": row["reason"],
            })

        if signals:
            routing_status = "escalate"
        elif not recommendations or top_score < 4:
            routing_status = "needs_clarification"
        elif len(recommendations) > 1 and top_score - second_score < 3:
            routing_status = "needs_clarification"
        else:
            routing_status = "recommended"

        clarifications = []
        if not re.search(r"\b(19|20)\d{2}\b|\b(hoy|ayer|mañana|semana|mes|dia|fecha)\b", text):
            clarifications.append("¿Cuándo ocurrió el hecho principal o cuándo recibiste la comunicación?")
        if not re.search(r"\b(empresa|empleador|eps|ips|vendedor|banco|autoridad|transito|arrendador|arrendatario|deudor|acreedor)\b", text):
            clarifications.append("¿Quién es la persona, empresa o autoridad involucrada?")
        if not re.search(r"\b(quiero|necesito|solicito|busco|pretendo|devolver|corregir|cobrar|contratar|reclamar)\b", text):
            clarifications.append("¿Qué resultado concreto buscas obtener?")
        if routing_status == "needs_clarification" and recommendations:
            clarifications.append("Confirma cuál de las soluciones sugeridas se acerca más a tu objetivo.")

        privacy_flags = []
        if re.search(r"\b\d{8,16}\b", raw):
            privacy_flags.append("La descripción contiene una secuencia numérica extensa. Evita incluir cédulas, tarjetas, historias clínicas o números completos en este campo.")
        if "@" in raw:
            privacy_flags.append("Evita incluir correos personales de terceros durante la orientación inicial.")

        return {
            "schema": "legalai_m24_6_client_intake_v1",
            "routing_status": routing_status,
            "requires_professional_review": bool(signals),
            "recommendations": recommendations,
            "risk_signals": signals,
            "clarifying_questions": clarifications[:4],
            "privacy_warnings": privacy_flags,
            "analysis": {
                "method": "deterministic_explainable_keyword_rules",
                "narrative_persisted": False,
                "top_score": top_score,
                "candidate_count": len(recommendations),
            },
            "notice": "Esta orientación inicial no constituye concepto jurídico definitivo. Debe confirmarse mediante el formulario del producto, sus reglas, los soportes y, cuando aplique, revisión profesional.",
        }
