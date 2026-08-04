from __future__ import annotations

from pathlib import Path
import json


class ReleaseCandidateCenter:
    """Consolida la preparación de contenido, experiencia e infraestructura.

    La aprobación jurídica controlada no se confunde con la habilitación de un
    entorno público de producción. El registro M6 conserva la evidencia de contenido y M7 añade evidencias inmutables
    de build; el diagnóstico de infraestructura se calcula en tiempo real.
    """

    def __init__(self, root: Path, approval_registry, settings, infrastructure):
        self.root = Path(root)
        self.approvals = approval_registry
        self.settings = settings
        self.infrastructure = infrastructure
        self.registry_path = self.root / "governance" / "m6" / "RELEASE_CANDIDATE_REGISTRY.json"

    def registry(self) -> dict:
        if not self.registry_path.is_file():
            return {
                "phase": "M6",
                "status": "blocked",
                "release_candidate_ready": False,
                "content": {"passed": 0, "total": 1, "score": 0, "checks": []},
                "products": [],
                "notice": "No existe el registro de Release Candidate M6.",
            }
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    @staticmethod
    def _runtime_checks(con, doctor: dict, settings) -> list[dict]:
        checks = list(doctor.get("checks") or [])
        active_demo = con.execute("SELECT COUNT(*) FROM users WHERE active=1 AND lower(email) LIKE '%@demo.legalaiz.it'").fetchone()[0]
        checks.append({
            "key": "demo_accounts",
            "label": "Cuentas de demostración restringidas al perfil local",
            "passed": settings.profile == "local" or active_demo == 0,
            "detail": f"{active_demo} cuentas demo activas; solo se permiten en perfil local.",
        })
        real_admin = con.execute("SELECT COUNT(*) FROM users WHERE active=1 AND role='admin' AND lower(email) NOT LIKE '%@demo.legalaiz.it'").fetchone()[0]
        checks.append({
            "key": "real_admin",
            "label": "Administrador institucional disponible",
            "passed": settings.profile == "local" or real_admin > 0,
            "detail": f"{real_admin} administradores no demo activos.",
        })
        return checks

    def summary(self, con) -> dict:
        registry = self.registry()
        doctor = self.infrastructure.doctor(con)
        runtime_checks = self._runtime_checks(con, doctor, self.settings)
        runtime_passed = sum(bool(x.get("passed")) for x in runtime_checks)
        runtime_total = len(runtime_checks)
        content = registry.get("content") or {}
        content_ready = bool(registry.get("release_candidate_ready"))
        production_ready = bool(
            content_ready
            and self.settings.profile == "production"
            and doctor.get("ready")
            and self.settings.database_backend == "postgresql"
            and self.settings.secure_cookies
            and self.settings.public_base_url.startswith("https://")
        )
        pilot_ready = bool(content_ready and self.settings.profile in {"local", "pilot"})
        score = round(
            ((int(content.get("passed") or 0) + runtime_passed)
             * 100)
            / max(1, int(content.get("total") or 0) + runtime_total)
        )
        return {
            **registry,
            "score": score,
            "release_candidate_ready": content_ready,
            "controlled_pilot_ready": pilot_ready,
            "production_ready": production_ready,
            "profile": self.settings.profile,
            "runtime": {
                "passed": runtime_passed,
                "total": runtime_total,
                "ready": bool(doctor.get("ready")),
                "checks": runtime_checks,
                "blocking": doctor.get("blocking") or [],
            },
            "approval": self.approvals.public_summary(),
            "notice": (
                "La biblioteca, los documentos y la experiencia M7 están preparados para un piloto profesional controlado. "
                "El perfil local no constituye un despliegue público de producción; producción permanece condicionada a "
                "PostgreSQL, HTTPS, cookies Secure, secretos administrados, MFA, backup verificado y escaneo antimalware."
            ),
        }

    def governance(self, con, products: list[dict]) -> dict:
        summary = self.summary(con)
        approval = self.approvals.public_summary()
        approved_by_code = {x.get("product_code"): x for x in approval.get("products", [])}
        rc_by_code = {x.get("product_code"): x for x in summary.get("products", [])}
        rows = []
        for product in products:
            code = product.get("code") or product.get("product_code")
            approved = approved_by_code.get(code, {})
            rc = rc_by_code.get(code, {})
            rows.append({
                "product_code": code,
                "title": product.get("title"),
                "vertical": product.get("vertical"),
                "status": "approved_controlled" if approved.get("publication_authorized") else "internal_review",
                "publication_authorized": bool(approved.get("publication_authorized")),
                "professional_use": bool(approved.get("professional_use")),
                "deep_library": rc.get("library"),
                "deep_documents": rc.get("documents", 0),
                "registered_sources": rc.get("sources", 0),
                "case_specific_review_required": bool(approved.get("case_specific_review_required")),
                "independent_reviewers": bool(approved.get("independent_reviewers")),
            })
        return {
            "summary": {
                "products": len(rows),
                "controlled_approved": sum(x["publication_authorized"] for x in rows),
                "deep_library_products": sum(bool(x.get("deep_library")) for x in rows),
                "professional_publication_authorized": bool(approval.get("professional_publication_authorized")),
                "controlled_pilot_ready": bool(summary.get("controlled_pilot_ready")),
                "production_ready": bool(summary.get("production_ready")),
                "profile": self.settings.profile,
            },
            "products": rows,
            "principles": [
                "Aprobación jurídica controlada y preparación de infraestructura son compuertas diferentes.",
                "La aprobación multietapa fue ejecutada por un responsable único y no equivale a revisión externa independiente.",
                "Los casos de alto impacto y riesgo rojo requieren revisión específica antes de liberar documentos.",
                "La vigencia normativa y la evidencia del caso deben verificarse en cada expediente.",
            ],
        }
