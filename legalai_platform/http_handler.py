from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse
import json
import traceback
import uuid

from core_v11 import *  # noqa: F401,F403
import core_v11 as core
from security import (
    clear_session_cookie,
    compare_csrf,
    hash_password,
    make_session_cookie,
    parse_cookie,
    utc_iso,
    validate_password,
    verify_password,
)
from legalai_platform.operational_security import same_origin_allowed
from legalai_platform.runtime_registry import *  # noqa: F401,F403
from legalai_platform.system_api import config_payload, health_payload
from legalai_platform.http_base import RequestContextMixin
from legalai_platform.routes.public_routes import handle_public_get, handle_public_post
from legalai_platform.routes.auth_routes import handle_auth_get, handle_auth_post
from legalai_platform.routes.product_quality_routes import handle_product_quality_get
from legalai_platform.routes.m24_candidate_routes import handle_m24_candidate_get
from legalai_platform.routes.m24_pilot_routes import handle_m24_pilot_get, handle_m24_pilot_post
from legalai_platform.routes.m24_full_routes import handle_m24_full_get, handle_m24_full_post
from legalai_platform.routes.m24_case_routes import handle_m24_case_get, handle_m24_case_post
from legalai_platform.routes.m24_client_routes import handle_m24_client_get, handle_m24_client_post
from legalai_platform.routes.m24_pilot_operations_routes import handle_m24_pilot_operations_get, handle_m24_pilot_operations_post
from legalai_platform.routes.m24_professional_routes import handle_m24_professional_get, handle_m24_professional_post
from legalai_platform.routes.m25_readiness_routes import handle_m25_readiness_get, handle_m25_readiness_post
from legalai_platform.routes.m30_pilot_center_routes import handle_m30_pilot_center_get, handle_m30_pilot_center_post
from legalai_platform.routes.m30_participant_routes import handle_m30_participant_get, handle_m30_participant_post
from legalai_platform.routes.m30_governance_routes import handle_m30_governance_get, handle_m30_governance_post
from legalai_platform.routes.m30_simulation_routes import handle_m30_simulation_get, handle_m30_simulation_post
from legalai_platform.routes.m30_live_evaluation_routes import handle_m30_live_evaluation_get, handle_m30_live_evaluation_post
from legalai_platform.routes.m31_preproduction_routes import handle_m31_preproduction_get, handle_m31_preproduction_post
from legalai_platform.routes.m31_demo_reality_routes import handle_m31_demo_reality_get, handle_m31_demo_reality_post
from legalai_platform.routes.m31_case_demo_routes import handle_m31_case_demo_get, handle_m31_case_demo_post
from legalai_platform.routes.system_routes import handle_admin_system_get
from legalai_platform.application_services import (
    api_generation_action,
    api_prefix_match,
    attachment_row,
    authenticate,
    can_access_case,
    case_scope,
    current_api_actor,
    document_row,
    get_session,
    init_db,
    safe_case_detail,
    scoped_cases,
    scoped_dashboard,
    scoped_documents,
    secure_case_export_bytes,
    security_event,
    security_overview,
    validate_upload,
)

class Handler(RequestContextMixin, core.Handler):
    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        if handle_public_get(self, u, path): return
        if not path.startswith("/api/"):
            return super().do_GET()

        user = self.require_user()
        if not user: return
        if handle_auth_get(self, path, user): return
        if handle_product_quality_get(self, path, user): return
        if handle_m24_candidate_get(self, path, user): return
        if handle_m24_pilot_get(self, path, user): return
        if handle_m24_full_get(self, path, user): return
        if handle_m24_case_get(self, path, user): return
        if handle_m24_client_get(self, path, user): return
        if handle_m24_pilot_operations_get(self, path, user): return
        if handle_m24_professional_get(self, path, user): return
        if handle_m25_readiness_get(self, path, user): return
        if handle_m30_pilot_center_get(self, path, user): return
        if handle_m30_participant_get(self, path, user): return
        if handle_m30_governance_get(self, path, user): return
        if handle_m30_simulation_get(self, path, user): return
        if handle_m30_live_evaluation_get(self, path, user): return
        if handle_m31_preproduction_get(self, path, user): return
        if handle_m31_demo_reality_get(self, path, user): return
        if handle_m31_case_demo_get(self, path, user): return
        if handle_admin_system_get(self, path, user): return
        if api_prefix_match(path, COTR002_API_V256.PREFIX):
            generation_id, action = api_generation_action(path, COTR002_API_V256.PREFIX)
            if action in {"download", "approved-download"}:
                try:
                    governance = COTR002_API_V256.service.governance
                    if action == "approved-download":
                        package = governance.approved_package_path(generation_id)
                    else:
                        manifest = governance.summary(generation_id).get("manifest") or {}
                        package = governance.output_dir / str(manifest.get("package_filename") or "")
                        if not package.is_file():
                            package = None
                    if not package:
                        return self.send_json({"error": "El paquete solicitado no está disponible."}, 404)
                    return self.send_file(package, download_name=package.name)
                except (ValueError, FileNotFoundError):
                    return self.send_json({"error": "La generación solicitada no existe."}, 404)
            payload = {key: values[-1] for key, values in parse_qs(u.query).items() if values}
            status, obj = COTR002_API_V256.handle("GET", path, payload, current_api_actor(user))
            return self.send_json(obj, status)
        if api_prefix_match(path, COTR001_API_V259.PREFIX):
            generation_id, action = api_generation_action(path, COTR001_API_V259.PREFIX)
            if action in {"download", "approved-download"}:
                try:
                    governance = COTR001_API_V259.service.governance
                    if action == "approved-download":
                        package = governance.approved_package_path(generation_id)
                    else:
                        manifest = governance.summary(generation_id).get("manifest") or {}
                        package = governance.output_dir / str(manifest.get("package_filename") or "")
                        if not package.is_file():
                            package = None
                    if not package:
                        return self.send_json({"error": "El paquete solicitado no está disponible."}, 404)
                    return self.send_file(package, download_name=package.name)
                except (ValueError, FileNotFoundError):
                    return self.send_json({"error": "La generación solicitada no existe."}, 404)
            payload = {key: values[-1] for key, values in parse_qs(u.query).items() if values}
            status, obj = COTR001_API_V259.handle("GET", path, payload, current_api_actor(user))
            return self.send_json(obj, status)
        if path == "/api/self-service":
            con = core.db()
            try:
                obj = SELF_SERVICE.summary(con, user["id"])
            finally:
                con.close()
            return self.send_json(obj)
        if path == "/api/drafts":
            con = core.db()
            try:
                obj = SELF_SERVICE.list_drafts(con, user["id"])
            finally:
                con.close()
            return self.send_json(obj)
        if path.startswith("/api/drafts/product/"):
            code = path.split("/")[-1]
            con = core.db()
            try:
                obj = SELF_SERVICE.get_product_draft(con, user["id"], code)
            finally:
                con.close()
            return self.send_json(obj or {}, 200 if obj else 404)
        if path.startswith("/api/drafts/"):
            draft_id = path.split("/")[-1]
            con = core.db()
            try:
                obj = SELF_SERVICE.get_draft(con, user["id"], draft_id)
            finally:
                con.close()
            return self.send_json(obj or {}, 200 if obj else 404)
        if path.startswith("/api/checkout/orders/"):
            order_id = path.split("/")[-1]
            con = core.db()
            try:
                obj = SELF_SERVICE.get_order(con, user["id"], order_id, admin=user["role"] == "admin")
            finally:
                con.close()
            return self.send_json(obj or {}, 200 if obj else 404)
        if path.startswith("/api/payment-intents/"):
            intent_id = path.split("/")[-1]
            con = core.db()
            try:
                obj = PAYMENTS.intent(con, intent_id)
                if obj and user["role"] != "admin" and obj.get("user_id") != user["id"]:
                    obj = None
            finally:
                con.close()
            return self.send_json(obj or {}, 200 if obj else 404)
        if path == "/api/dashboard":
            return self.send_json(scoped_dashboard(user))
        if path == "/api/file-center":
            clause, params = case_scope(user)
            con = core.db()
            try:
                result = UX.file_center(con, clause, params)
            finally:
                con.close()
            return self.send_json(result)
        if path == "/api/file-requirements":
            code = parse_qs(u.query).get("product_code", [""])[0]
            return self.send_json(UX.product_requirements(code) if code else UX.requirements)
        if path == "/api/experience-metrics":
            if user["role"] != "admin":
                return self.send_json({"error": "Sin permisos para consultar analítica de experiencia."}, 403)
            days = parse_qs(u.query).get("days", ["30"])[0]
            con = core.db()
            try:
                return self.send_json(COMMERCIAL_EXPERIENCE.admin_summary(con, days=int(days)))
            except (TypeError, ValueError):
                return self.send_json({"error": "El rango solicitado no es válido."}, 400)
            finally:
                con.close()
        if path == "/api/search":
            query = parse_qs(u.query).get("q", [""])[0]
            clause, params = case_scope(user)
            con = core.db()
            try:
                result = UX.global_search(con, clause, params, query)
            finally:
                con.close()
            return self.send_json(result)
        if path == "/api/cases":
            return self.send_json(scoped_cases(user))
        if path == "/api/v29/priority-wave":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la ola prioritaria."}, 403)
            con = core.db()
            try:
                obj = PRIORITY_V29.summary(con)
            finally:
                con.close()
            return self.send_json(obj)
        if path == "/api/v210/canonical-activation":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la activación canónica."}, 403)
            con = core.db()
            try:
                obj = ACTIVATION_V210.summary(con)
            finally:
                con.close()
            return self.send_json(obj)
        if path.startswith("/api/v210/canonical-activation/") and path.endswith("/evidence"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar evidencia."}, 403)
            code = path.split("/")[-2].upper()
            con = core.db()
            try:
                body = ACTIVATION_V210.evidence_bytes(con, code)
            except ValueError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 404)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_bytes(body, "application/zip", f"LegalAIZit_Activacion_{code}_v2.10.zip")
        if path.startswith("/api/v29/priority-wave/") and path.endswith("/candidate-package"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar paquetes candidatos."}, 403)
            code = path.split("/")[-2]
            con = core.db()
            try:
                body = PRIORITY_V29.package_bytes(con, code)
            except ValueError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 404)
            finally:
                try: con.close()
                except Exception: pass
            filename = f"LegalAIZit_{code}_Candidato_v2.9.zip"
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        if path == "/api/v28/co-em-003":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el producto candidato."}, 403)
            con = core.db()
            try:
                obj = COEM003_V28.summary(con)
            finally:
                con.close()
            return self.send_json(obj)
        if path == "/api/v28/co-em-003/candidate-package":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar el paquete candidato."}, 403)
            con = core.db()
            try:
                body = COEM003_V28.package_bytes(con)
            finally:
                con.close()
            return self.send_bytes(body, "application/zip", "LegalAIZit_CO-EM-003_Candidato_Estructurado_v2.8.zip")
        if path == "/api/canonical-generation":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar publicación canónica."}, 403)
            con = core.db()
            try:
                obj = CANONICAL_GENERATION.summary(con)
            finally:
                con.close()
            return self.send_json(obj)
        if path.startswith("/api/canonical-generation/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar publicación canónica."}, 403)
            code = path.split("/")[-1]
            con = core.db()
            try:
                obj = CANONICAL_GENERATION.readiness(con, code)
            finally:
                con.close()
            return self.send_json(obj)
        if path == "/api/collaboration":
            clause, params = case_scope(user)
            con = core.db()
            try:
                obj = WORKFLOW.collaboration_overview(con, clause, params, user)
            finally:
                con.close()
            return self.send_json(obj)
        if path == "/api/v216/extensive-generation":
            return self.send_json(EXTENSIVE_V216.summary())
        if path == "/api/v217/release-control":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar liberaciones controladas."}, 403)
            con = core.db()
            try:
                obj = RELEASE_V217.summary(con)
                con.commit()
            finally: con.close()
            return self.send_json(obj)
        if path == "/api/v218/visual-qa":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la evidencia de QA visual."}, 403)
            con = core.db()
            try:
                obj = VISUAL_QA_V218.summary(con)
            finally:
                con.close()
            return self.send_json(obj)
        if path == "/api/v222/co-la-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la maduración laboral."}, 403)
            return self.send_json(COLA001_V222.summary())
        if path == "/api/v223/co-ar-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la maduración inmobiliaria."}, 403)
            return self.send_json(COAR001_V223.summary())
        if path == "/api/v242/co-em-003":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la capa canónica de servicios independientes."}, 403)
            return self.send_json(COEM003_V242.summary())
        if path == "/api/v244/co-em-003":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el producto validado de servicios independientes."}, 403)
            return self.send_json(COEM003_V244.summary())
        if path == "/api/v244/co-em-003/validation":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la validación de escenarios."}, 403)
            return self.send_json(COEM003_VALIDATION_V244.summary())
        if path.startswith("/api/v244/co-em-003/generations/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el gobierno documental de servicios independientes."}, 403)
            parts = [x for x in path.split("/") if x]
            generation_id = parts[4] if len(parts) > 4 else ""
            try:
                if path.endswith("/download"):
                    package = COEM003_FACTORY_V244.package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "Paquete no encontrado."}, 404)
                if path.endswith("/approved-download"):
                    package = COEM003_GOVERNANCE_V244.approved_package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "El paquete aún no cuenta con aprobación jurídica y QA vigentes."}, 409)
                if path.endswith("/compare"):
                    query = parse_qs(parsed.query)
                    return self.send_json(COEM003_GOVERNANCE_V244.compare(generation_id, int(query.get("from", [0])[0]), int(query.get("to", [0])[0])))
                return self.send_json(COEM003_GOVERNANCE_V244.summary(generation_id))
            except (ValueError, FileNotFoundError) as exc:
                return self.send_json({"error": str(exc)}, 404)
        if path == "/api/v243/co-em-003":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la fábrica documental de servicios independientes."}, 403)
            return self.send_json(COEM003_V243.summary())
        if path.startswith("/api/v243/co-em-003/generations/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el gobierno documental de servicios independientes."}, 403)
            parts = [x for x in path.split("/") if x]
            generation_id = parts[4] if len(parts) > 4 else ""
            try:
                if path.endswith("/download"):
                    package = COEM003_FACTORY_V243.package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "Paquete no encontrado."}, 404)
                if path.endswith("/approved-download"):
                    package = COEM003_GOVERNANCE_V243.approved_package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "El paquete aún no tiene aprobación dual vigente."}, 409)
                if path.endswith("/compare"):
                    qs = parse_qs(urlparse(self.path).query)
                    result = COEM003_GOVERNANCE_V243.compare(generation_id, int(qs.get("from", [0])[0]), int(qs.get("to", [0])[0]))
                    return self.send_json(result)
                return self.send_json(COEM003_GOVERNANCE_V243.summary(generation_id))
            except (ValueError, FileNotFoundError) as exc:
                return self.send_json({"error": str(exc)}, 404)
        if path == "/api/v224/co-la-002":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la maduración de contratación laboral."}, 403)
            return self.send_json(COLA002_V224.summary())
        if path.startswith("/api/v239/co-la-002/generations/") and path.endswith("/download"):
            user = self.require_user()
            if not user: return
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar documentos laborales canónicos."}, 403)
            generation_id = path.split("/")[-2]
            package = COLA002_FACTORY_V239.package_path(generation_id)
            return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "Paquete no encontrado"}, 404)

        if path.startswith("/api/v240/co-la-002/generations/"):
            user = self.require_user()
            if not user: return
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el gobierno documental laboral."}, 403)
            parts = [x for x in path.split("/") if x]
            generation_id = parts[4] if len(parts) > 4 else ""
            try:
                if path.endswith("/approved-download"):
                    package = COLA002_GOVERNANCE_V240.approved_package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "El paquete aún no tiene aprobación dual vigente."}, 409)
                if path.endswith("/compare"):
                    qs = parse_qs(urlparse(self.path).query)
                    result = COLA002_GOVERNANCE_V240.compare(generation_id, int(qs.get("from", [0])[0]), int(qs.get("to", [0])[0]))
                    return self.send_json(result)
                return self.send_json(COLA002_GOVERNANCE_V240.summary(generation_id))
            except (ValueError, FileNotFoundError) as exc:
                return self.send_json({"error": str(exc)}, 404)

        if path == "/api/v236/co-la-002":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la capa canónica laboral."}, 403)
            return self.send_json(COLA002_V236.summary())
        if path == "/api/v225/co-tr-002":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la maduración de fotodetecciones."}, 403)
            return self.send_json(COTR002_V225.summary())
        if path == "/api/v226/co-tr-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la maduración SAST."}, 403)
            return self.send_json(COTR001_V226.summary())
        if path == "/api/v231/co-sa-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la maduración del producto de salud."}, 403)
            return self.send_json(COSA001_V231.summary())
        if path == "/api/v232/co-cd-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la maduración de hábeas data financiero."}, 403)
            return self.send_json(COCD001_V232.summary())
        if path == "/api/v233/co-cd-003":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la maduración de protección al consumidor."}, 403)
            return self.send_json(COCD003_V233.summary())
        if path == "/api/v235/third-wave-internal-approval":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la aprobación jurídica interna consolidada."}, 403)
            return self.send_json(THIRD_WAVE_APPROVAL_V235.summary())
        if path.startswith("/api/v235/documents/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar documentos jurídicos internos v2.35."}, 403)
            filename = Path(path.rsplit("/", 1)[-1]).name
            allowed = {Path(x).name for x in THIRD_WAVE_APPROVAL_V235.spec.get("approval_documents", [])}
            if filename not in allowed:
                return self.send_json({"error": "Documento no autorizado o inexistente."}, 404)
            target = core.ROOT / "docs" / "v235" / filename
            return self.send_file(str(target), target.name) if target.is_file() else self.send_json({"error": "Documento no disponible."}, 404)
        if path == "/api/v234/co-cd-004":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la maduración de cobro, acuerdo y pagaré."}, 403)
            return self.send_json(COCD004_V234.summary())
        if path.startswith("/api/v234/documents/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar documentos internos de cartera."}, 403)
            filename = Path(path.rsplit("/", 1)[-1]).name
            allowed = {Path(x).name for x in COCD004_V234.spec.get("approval_documents", [])}
            if filename not in allowed:
                return self.send_json({"error": "Documento no autorizado o inexistente."}, 404)
            target = core.ROOT / "docs" / "v234" / filename
            return self.send_file(str(target), target.name) if target.is_file() else self.send_json({"error": "Documento no disponible."}, 404)
        if path.startswith("/api/v233/documents/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar documentos internos de protección al consumidor."}, 403)
            filename = Path(path.rsplit("/", 1)[-1]).name
            allowed = {Path(x).name for x in COCD003_V233.spec.get("approval_documents", [])}
            if filename not in allowed:
                return self.send_json({"error": "Documento no autorizado o inexistente."}, 404)
            target = core.ROOT / "docs" / "v233" / filename
            return self.send_file(str(target), target.name) if target.is_file() else self.send_json({"error": "Documento no disponible."}, 404)
        if path.startswith("/api/v232/documents/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar documentos internos de hábeas data."}, 403)
            filename = Path(path.rsplit("/", 1)[-1]).name
            allowed = {Path(x).name for x in COCD001_V232.spec.get("approval_documents", [])}
            if filename not in allowed:
                return self.send_json({"error": "Documento no autorizado o inexistente."}, 404)
            target = core.ROOT / "docs" / "v232" / filename
            return self.send_file(str(target), target.name) if target.is_file() else self.send_json({"error": "Documento no disponible."}, 404)
        if path.startswith("/api/v231/documents/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar documentos internos de salud."}, 403)
            filename = Path(path.rsplit("/", 1)[-1]).name
            allowed = {Path(x).name for x in COSA001_V231.spec.get("approval_documents", [])}
            if filename not in allowed:
                return self.send_json({"error": "Documento no autorizado o inexistente."}, 404)
            target = core.ROOT / "docs" / "v231" / filename
            return self.send_file(str(target), target.name) if target.is_file() else self.send_json({"error": "Documento no disponible."}, 404)
        if path == "/api/v227/legal-approval":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la primera ola de aprobación jurídica."}, 403)
            return self.send_json(LEGAL_APPROVAL_V227.summary())
        if path.startswith("/api/v228/documents/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar documentos jurídicos internos."}, 403)
            filename = Path(path.rsplit("/", 1)[-1]).name
            spec = INTERNAL_APPROVAL_V228.spec
            allowed = {
                Path(item[key]).name
                for item in spec.get("products", [])
                for key in ("document", "pdf")
                if item.get(key)
            }
            allowed.update({
                "LegalAIZit_Estandar_Contractual_Canonico_V228.docx",
                "LegalAIZit_Estandar_Contractual_Canonico_V228.pdf",
                "LegalAIZit_Informe_Continuidad_v227_a_v228.docx",
                "LegalAIZit_Informe_Continuidad_v227_a_v228.pdf",
            })
            if filename not in allowed:
                return self.send_json({"error": "Documento no autorizado o inexistente."}, 404)
            target = core.ROOT / "docs" / "v228" / filename
            if target.is_file():
                return self.send_file(str(target), target.name)
            return self.send_json({
                "error": "Artefacto histórico omitido del paquete autocontenido vigente.",
                "historical_version": "2.28",
                "superseded_by": "2.35",
                "current_endpoint": "/api/v235/third-wave-internal-approval",
            }, 410)
        if path == "/api/v228/internal-legal-approval":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar las decisiones jurídicas internas."}, 403)
            qs=parse_qs(urlparse(self.path).query)
            return self.send_json(INTERNAL_APPROVAL_V228.summary(qs.get("date", [None])[0]))
        if path.startswith("/api/v229/documents/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar expedientes de la segunda ola."}, 403)
            filename = Path(path.rsplit("/", 1)[-1]).name
            spec = SECOND_WAVE_APPROVAL_V229.spec
            allowed = {Path(item[key]).name for item in spec.get("products", []) for key in ("document", "pdf") if item.get(key)}
            allowed.update({Path(x).name for x in spec.get("consolidated_documents", [])})
            if filename not in allowed:
                return self.send_json({"error": "Documento no autorizado o inexistente."}, 404)
            target = core.ROOT / "docs" / "v229" / filename
            if target.is_file():
                return self.send_file(str(target), target.name)
            return self.send_json({
                "error": "Artefacto histórico omitido del paquete autocontenido vigente.",
                "historical_version": "2.29",
                "superseded_by": "2.35",
                "current_endpoint": "/api/v235/third-wave-internal-approval",
            }, 410)
        if path == "/api/v229/second-wave-legal-approval":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la segunda ola jurídica."}, 403)
            return self.send_json(SECOND_WAVE_APPROVAL_V229.summary())
        if path.startswith("/api/v230/documents/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar decisiones jurídicas internas."}, 403)
            filename = Path(path.rsplit("/", 1)[-1]).name
            spec = SECOND_WAVE_DECISION_V230.spec
            allowed = {Path(x).name for x in spec.get("approval_documents", [])}
            if filename not in allowed:
                return self.send_json({"error": "Documento no autorizado o inexistente."}, 404)
            target = core.ROOT / "docs" / "v230" / filename
            if target.is_file():
                return self.send_file(str(target), target.name)
            return self.send_json({
                "error": "Artefacto histórico omitido del paquete autocontenido vigente.",
                "historical_version": "2.30",
                "superseded_by": "2.35",
                "current_endpoint": "/api/v235/third-wave-internal-approval",
            }, 410)
        if path == "/api/v230/second-wave-internal-decision":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la decisión jurídica interna."}, 403)
            return self.send_json(SECOND_WAVE_DECISION_V230.summary())
        if path == "/api/v221/release-cycle":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar ciclos de entrega."}, 403)
            con = core.db()
            try:
                obj = RELEASE_CYCLE_V221.summary(con)
                con.commit()
            finally:
                con.close()
            return self.send_json(obj)
        if path.startswith("/api/v221/release-cycle/") and path.endswith("/bundle/download"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar el paquete de entrega."}, 403)
            release_id = path.split("/")[-3]
            con = core.db()
            try:
                body = RELEASE_CYCLE_V221.bundle(con, release_id)
                row = RELEASE_CYCLE_V221.detail(con, release_id)["release"]
            except KeyError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 404)
            except ValueError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 400)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_bytes(body, "application/zip", f"LegalAIZit_{row['version']}_{release_id}_evidencia.zip")
        if path.startswith("/api/v221/release-cycle/") and path.endswith("/evidence/download"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar evidencia de entrega."}, 403)
            release_id = path.split("/")[-3]
            con = core.db()
            try:
                body = RELEASE_CYCLE_V221.evidence(con, release_id)
            except KeyError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 404)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_bytes(body, "application/json; charset=utf-8", f"{release_id}_evidencia_v221.json")
        if path.startswith("/api/v221/release-cycle/") and len(path.strip("/").split("/")) == 4:
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar ciclos de entrega."}, 403)
            release_id = path.rsplit("/", 1)[-1]
            con = core.db()
            try:
                obj = RELEASE_CYCLE_V221.detail(con, release_id)
            except KeyError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 404)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_json(obj)
        if path == "/api/v220/change-control":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el control de cambios."}, 403)
            con = core.db()
            try:
                obj = CHANGE_CONTROL_V220.summary(con)
                con.commit()
            finally:
                con.close()
            return self.send_json(obj)
        if path.startswith("/api/v220/change-control/") and path.endswith("/evidence/download"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar evidencia de cambios."}, 403)
            change_id = path.split("/")[-3]
            con = core.db()
            try:
                body = CHANGE_CONTROL_V220.evidence(con, change_id)
            except KeyError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 404)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_bytes(body, "application/json; charset=utf-8", f"{change_id}_evidencia_v220.json")
        if path.startswith("/api/v220/change-control/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar cambios."}, 403)
            change_id = path.rsplit("/", 1)[-1]
            con = core.db()
            try:
                obj = CHANGE_CONTROL_V220.detail(con, change_id)
            except KeyError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 404)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_json(obj)
        if path == "/api/v219/validation-governance":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la gobernanza de validación."}, 403)
            con = core.db()
            try:
                obj = VALIDATION_V219.summary(con)
                con.commit()
            finally:
                con.close()
            return self.send_json(obj)
        if path == "/api/v218/visual-qa/evidence/download":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para descargar la evidencia de QA visual."}, 403)
            target = VISUAL_QA_V218.evidence_path()
            return self.send_file(str(target), target.name) if target else self.send_json({"error": "Evidencia visual no disponible."}, 404)
        if path.startswith("/api/v218/visual-qa/screenshots/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar capturas de QA."}, 403)
            filename = path.rsplit("/", 1)[-1]
            target = VISUAL_QA_V218.screenshot_path(filename)
            return self.send_file(str(target), target.name) if target else self.send_json({"error": "Captura no encontrada."}, 404)
        if path.startswith("/api/cases/") and path.endswith("/release-package/download"):
            cid = path.split("/")[-3]
            if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
            con = core.db()
            try:
                target = RELEASE_V217.release_path(con, cid)
                con.commit()
            finally: con.close()
            return self.send_file(str(target), target.name) if target else self.send_json({"error": "Liberación controlada no disponible."}, 404)
        if path.startswith("/api/cases/") and path.endswith("/release-certificate/download"):
            cid = path.split("/")[-3]
            if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
            con = core.db()
            try:
                target = RELEASE_V217.certificate_path(con, cid)
                con.commit()
            finally: con.close()
            return self.send_file(str(target), target.name) if target else self.send_json({"error": "Certificado de liberación no disponible."}, 404)
        if path.startswith("/api/cases/") and path.endswith("/release-control"):
            cid = path.split("/")[-2]
            if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
            con = core.db()
            try:
                obj = RELEASE_V217.detail(con, cid)
                con.commit()
            finally: con.close()
            return self.send_json(obj)
        if path.startswith("/api/cases/") and path.endswith("/generation-proof/download"):
            cid = path.split("/")[-3]
            if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
            con = core.db()
            try: target = EXTENSIVE_V216.proof_path(con, cid)
            finally: con.close()
            return self.send_file(str(target), target.name) if target else self.send_json({"error": "Evidencia de generación no encontrada."}, 404)
        if path.startswith("/api/cases/") and path.endswith("/generation-proof"):
            cid = path.split("/")[-2]
            if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
            con = core.db()
            try: obj = EXTENSIVE_V216.latest_proof(con, cid)
            finally: con.close()
            return self.send_json(obj or {}, 200 if obj else 404)
        if path.startswith("/api/cases/") and path.endswith("/collaboration"):
            cid = path.split("/")[-2]
            if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
            con = core.db()
            try:
                obj = WORKFLOW.case_collaboration(con, cid, user)
            finally:
                con.close()
            return self.send_json(obj)
        if path.startswith("/api/cases/") and path.endswith("/export"):
            cid = path.split("/")[-2]
            if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
            body = secure_case_export_bytes(user, cid)
            return self.send_bytes(body, "application/zip", f"LegalAIZit_Expediente_{cid}.zip") if body else self.send_json({"error": "Caso no encontrado"}, 404)
        if path.startswith("/api/cases/") and path.endswith("/delivery"):
            cid = path.split("/")[-2]
            if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
            con = core.db()
            try:
                obj = DELIVERY.summary(con, cid)
                con.commit()
            finally:
                con.close()
            return self.send_json(obj)
        if path.startswith("/api/document-packages/") and path.endswith("/download"):
            package_id = path.split("/")[-2]
            con = core.db()
            try:
                row = con.execute("SELECT case_id FROM document_packages WHERE id=?", (package_id,)).fetchone()
                if not row or not can_access_case(user, row["case_id"]):
                    con.close(); return self.send_json({"error": "Paquete no encontrado o sin acceso."}, 404)
                target = DELIVERY.package_path(con, package_id)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_file(str(target), target.name) if target else self.send_json({"error": "Archivo de paquete no disponible."}, 404)
        if path.startswith("/api/document-packages/"):
            package_id = path.split("/")[-1]
            con = core.db()
            try:
                row = con.execute("SELECT case_id FROM document_packages WHERE id=?", (package_id,)).fetchone()
                obj = DELIVERY.package(con, package_id) if row and can_access_case(user, row["case_id"]) else None
            finally:
                con.close()
            return self.send_json(obj or {}, 200 if obj else 404)
        if path.startswith("/api/cases/"):
            cid = path.split("/")[-1]
            if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
            obj = safe_case_detail(user, cid)
            return self.send_json(obj or {}, 200 if obj else 404)
        if path == "/api/documents":
            return self.send_json(scoped_documents(user))
        if path.startswith("/api/documents/") and path.endswith("/pdf-preview"):
            did = path.split("/")[-2]
            row = document_row(user, did)
            if not row:
                return self.send_json({"error": "Documento no encontrado o sin acceso."}, 404)
            con = core.db()
            try:
                preview = PDF_ACCEPTANCE.ensure_preview(con, did, user["id"])
                core.audit(con, user["id"], "document", did, "generate_pdf_preview", {"preview_id": preview.get("id"), "pdf_sha256": preview.get("pdf_sha256")})
                con.commit()
            except ValueError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 400)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_json(preview)
        if path.startswith("/api/pdf-previews/") and (path.endswith("/view") or path.endswith("/download")):
            preview_id = path.split("/")[-2]
            con = core.db()
            try:
                source = con.execute("SELECT document_id FROM document_pdf_previews WHERE id=?", (preview_id,)).fetchone()
                if not source or not document_row(user, source["document_id"]):
                    con.close(); return self.send_json({"error": "Vista PDF no encontrada o sin acceso."}, 404)
                target = PDF_ACCEPTANCE.preview_path(con, preview_id)
            finally:
                try: con.close()
                except Exception: pass
            if not target:
                return self.send_json({"error": "Archivo PDF no disponible."}, 404)
            body = target.read_bytes()
            return self.send_bytes(body, "application/pdf", target.name if path.endswith("/download") else None)
        if path.startswith("/api/documents/") and path.endswith("/acceptances"):
            did = path.split("/")[-2]
            row = document_row(user, did)
            if not row:
                return self.send_json({"error": "Documento no encontrado o sin acceso."}, 404)
            con = core.db()
            try:
                obj = PDF_ACCEPTANCE.list_for_document(con, did)
            finally:
                con.close()
            return self.send_json({"document_id": did, "acceptances": obj, "acceptance_text": PDF_ACCEPTANCE.ACCEPTANCE_TEXT})
        if path.startswith("/api/document-acceptances/") and path.endswith("/receipt"):
            acceptance_id = path.split("/")[-2]
            con = core.db()
            try:
                row = con.execute("SELECT document_id FROM document_acceptances WHERE id=?", (acceptance_id,)).fetchone()
                if not row or not document_row(user, row["document_id"]):
                    con.close(); return self.send_json({"error": "Constancia no encontrada o sin acceso."}, 404)
                target = PDF_ACCEPTANCE.receipt_path(con, acceptance_id)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_file(str(target), target.name) if target else self.send_json({"error": "Constancia no disponible."}, 404)
        if path.startswith("/api/document-acceptances/"):
            acceptance_id = path.split("/")[-1]
            con = core.db()
            try:
                obj = PDF_ACCEPTANCE.detail(con, acceptance_id)
                allowed = bool(obj and document_row(user, obj.get("document_id")))
            finally:
                con.close()
            return self.send_json(obj if allowed else {}, 200 if allowed else 404)
        if path.startswith("/api/documents/") and path.endswith("/preview"):
            did = path.split("/")[-2]
            obj = document_row(user, did)
            if not obj: return self.send_json({"error": "Documento no encontrado o sin acceso."}, 404)
            con = core.db()
            try:
                preview = WORKFLOW.document_preview(con, obj, user)
            finally:
                con.close()
            return self.send_json(preview)
        if path == "/api/activity":
            clause, params = case_scope(user)
            con = core.db()
            try:
                obj = WORKSPACE.activity_feed(con, clause, params, user)
            finally:
                con.close()
            return self.send_json(obj)
        if path.startswith("/api/documents/") and path.endswith("/versions"):
            did = path.split("/")[-2]
            row = document_row(user, did)
            if not row:
                return self.send_json({"error": "Documento no encontrado o sin acceso."}, 404)
            con = core.db()
            try:
                versions = WORKSPACE.version_catalog(con, did)
            finally:
                con.close()
            return self.send_json({"document_id": did, "versions": versions})
        if path.startswith("/api/documents/") and path.endswith("/compare"):
            did = path.split("/")[-2]
            row = document_row(user, did)
            if not row:
                return self.send_json({"error": "Documento no encontrado o sin acceso."}, 404)
            qs = parse_qs(urlparse(self.path).query)
            from_ref = qs.get("from", [""])[0]
            to_ref = qs.get("to", ["current"])[0]
            con = core.db()
            try:
                obj = WORKSPACE.compare(con, did, from_ref, to_ref, user["id"])
                core.audit(con, user["id"], "document", did, "compare_versions", {"from": from_ref, "to": to_ref, "compare_id": obj["compare_id"]})
                con.commit()
            except ValueError as exc:
                con.close(); return self.send_json({"error": str(exc)}, 400)
            finally:
                try: con.close()
                except Exception: pass
            return self.send_json(obj)
        if path.startswith("/api/document-factory/") and path.endswith("/working-draft"):
            if user["role"] != "admin":
                return self.send_json({"error": "Solo administración puede consultar borradores de trabajo."}, 403)
            tid = path.split("/")[-2]
            con = core.db()
            try:
                obj = WORKSPACE.working_draft(con, tid, user["id"])
            finally:
                con.close()
            return self.send_json(obj or {})
        if path.startswith("/api/documents/") and path.endswith("/download"):
            did = path.split("/")[-2]
            row = document_row(user, did)
            return self.send_file(row["file_path"], row["name"]) if row and row.get("file_path") else self.send_json({"error": "Documento no disponible"}, 404)
        if path.startswith("/api/documents/"):
            did = path.split("/")[-1]
            obj = document_row(user, did)
            if obj:
                for field in ("file_path", "content", "owner_id", "specialist_id"):
                    obj.pop(field, None)
            return self.send_json(obj or {}, 200 if obj else 404)
        if path.startswith("/api/attachments/") and path.endswith("/download"):
            aid = path.split("/")[-2]
            row = attachment_row(user, aid)
            if not row:
                return self.send_json({"error": "Soporte no encontrado"}, 404)
            con = core.db()
            try:
                body = read_reference_bytes(con, INFRA.objects, row["file_path"])
                con.commit()
            finally:
                con.close()
            return self.send_bytes(body, row.get("mime_type") or "application/octet-stream", row["name"])
        if path == "/api/users":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con = core.db()
            rows = [dict(x) for x in con.execute("SELECT id,name,email,role,specialty,verified,active,last_login_at FROM users ORDER BY role,name").fetchall()]
            con.close(); return self.send_json(rows)
        if path == "/api/reviews":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            clause, params = case_scope(user)
            con = core.db()
            rows = [dict(x) for x in con.execute(
                f"SELECT c.id,c.product_code,c.title,c.risk,c.status,c.review_status,c.updated_at,u.name specialist_name FROM cases c LEFT JOIN users u ON u.id=c.specialist_id WHERE {clause} AND c.review_status!='Aprobado' ORDER BY CASE c.risk WHEN 'red' THEN 1 WHEN 'yellow' THEN 2 ELSE 3 END,c.updated_at DESC", params
            ).fetchall()]
            con.close(); return self.send_json(rows)
        if path == "/api/legal-studio":
            if user["role"] != "admin": return self.send_json({"error": "Solo administración puede acceder al Studio Jurídico."}, 403)
            con = core.db(); obj = core.STUDIO.summary(con); con.close(); return self.send_json(obj)
        if path.startswith("/api/legal-studio/") and path.endswith("/export"):
            if user["role"] != "admin": return self.send_json({"error": "Sin permisos."}, 403)
            code = path.split("/")[-2]
            con = core.db(); body = core.STUDIO.export_bytes(con, code); con.close()
            return self.send_bytes(body, "application/json", f"LegalAIZit_{code}_paquete_juridico.json") if body else self.send_json({"error": "Producto no encontrado"}, 404)
        if path.startswith("/api/legal-studio/"):
            if user["role"] != "admin": return self.send_json({"error": "Sin permisos."}, 403)
            code = path.split("/")[-1]
            con = core.db(); obj = core.STUDIO.detail(con, code); con.close()
            return self.send_json(obj or {}, 200 if obj else 404)
        if path == "/api/document-factory":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Solo especialistas y administración pueden acceder a la Fábrica Documental."}, 403)
            con = core.db(); obj = FACTORY.summary(con); con.close(); return self.send_json(obj)
        if path.startswith("/api/document-factory/") and path.endswith("/download"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            tid = path.split("/")[-2]
            qs = parse_qs(urlparse(self.path).query); rid = int(qs.get("revision", [0])[0] or 0) or None
            con = core.db(); out = FACTORY.build_preview_docx(con, tid, {}, core.GENERATED, rid); con.close()
            return self.send_file(out, download_name=out.name) if out else self.send_json({"error": "Plantilla no encontrada"}, 404)
        if path.startswith("/api/document-factory/") and path.endswith("/compare"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            tid = path.split("/")[-2]; qs = parse_qs(urlparse(self.path).query)
            try: a=int(qs.get("from",[0])[0]); b=int(qs.get("to",[0])[0])
            except Exception: return self.send_json({"error":"Revisiones inválidas."},400)
            con=core.db(); obj=FACTORY.compare(con,tid,a,b); con.close(); return self.send_json(obj or {"error":"Revisiones no encontradas"},200 if obj else 404)
        if path.startswith("/api/document-factory/"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            tid = path.split("/")[-1]
            con=core.db(); obj=FACTORY.detail(con,tid); con.close(); return self.send_json(obj or {},200 if obj else 404)
        if path == "/api/canonical-cotejo/export":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); body=CANONICAL.export_bytes(con); con.close()
            return self.send_bytes(body, "application/zip", "LegalAIZit_Cotejo_Canonico_v2.0.zip")
        if path == "/api/canonical-cotejo":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); obj=CANONICAL.summary(con); con.close(); return self.send_json(obj)
        if path.startswith("/api/canonical-cotejo/") and path.endswith("/export"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            code=path.split("/")[-2]; con=core.db(); body=CANONICAL.export_bytes(con,code); con.close()
            return self.send_bytes(body, "application/json", f"LegalAIZit_{code}_cotejo_canonico.json") if body else self.send_json({"error":"Producto no encontrado"},404)
        if path.startswith("/api/canonical-cotejo/"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            code=path.split("/")[-1]; con=core.db(); obj=CANONICAL.detail(con,code); con.close(); return self.send_json(obj or {},200 if obj else 404)
        if path in {"/api/release-readiness", "/api/rc-readiness"}:
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error":"Sin permisos."},403)
            con=core.db()
            try: obj=RELEASE_CANDIDATE.summary(con)
            finally: con.close()
            return self.send_json(obj)
        if path == "/api/review-batches":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error":"Sin permisos."},403)
            con=core.db(); obj=BATCHES.summary(con,user["id"],user["role"]); con.close(); return self.send_json(obj)
        if path.startswith("/api/review-batches/") and path.endswith("/export"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error":"Sin permisos."},403)
            batch_id=path.split("/")[-2]; con=core.db(); detail=BATCHES.detail(con,batch_id)
            if not detail: con.close(); return self.send_json({"error":"Lote no encontrado."},404)
            if user["role"]=="specialist" and detail["batch"].get("assigned_to") not in (None,user["id"]): con.close(); return self.send_json({"error":"El lote está asignado a otro especialista."},403)
            body=BATCHES.export_bytes(con,batch_id,user["id"]); con.close(); return self.send_bytes(body,"application/zip",f"LegalAIZit_Lote_{batch_id}.zip")
        if path.startswith("/api/review-batches/"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error":"Sin permisos."},403)
            batch_id=path.split("/")[-1]; con=core.db(); obj=BATCHES.detail(con,batch_id); con.close()
            if obj and user["role"]=="specialist" and obj["batch"].get("assigned_to") not in (None,user["id"]): return self.send_json({"error":"El lote está asignado a otro especialista."},403)
            return self.send_json(obj or {},200 if obj else 404)
        if path == "/api/assisted-review/export":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); body=REVIEW.export_bytes(con); con.commit(); con.close()
            return self.send_bytes(body, "application/zip", "LegalAIZit_Mesa_Cotejo_Asistido_v2.0.zip")
        if path == "/api/assisted-review":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); obj=REVIEW.summary(con,user["id"],user["role"]); con.commit(); con.close(); return self.send_json(obj)
        if path.startswith("/api/assisted-review/jobs/") and path.endswith("/candidates"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            try: job_id=int(path.split("/")[-2])
            except Exception: return self.send_json({"error":"Trabajo inválido."},400)
            qs=parse_qs(urlparse(self.path).query); limit=int(qs.get("limit",[8])[0] or 8)
            con=core.db(); obj=REVIEW.candidates(con,job_id,user["id"],limit); con.commit(); con.close(); return self.send_json(obj)
        if path.startswith("/api/assisted-review/jobs/"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            try: job_id=int(path.split("/")[-1])
            except Exception: return self.send_json({"error":"Trabajo inválido."},400)
            con=core.db(); obj=REVIEW.job_detail(con,job_id); con.close(); return self.send_json(obj or {},200 if obj else 404)
        if path.startswith("/api/assisted-review/"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            code=path.split("/")[-1]; con=core.db(); obj=REVIEW.product_detail(con,code,user["id"],user["role"]); con.commit(); con.close(); return self.send_json(obj or {},200 if obj else 404)
        if path == "/api/traceability/export":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); body=TRACEABILITY.export_bytes(con); con.close()
            return self.send_bytes(body, "application/zip", "LegalAIZit_Trazabilidad_Semantica_v2.0.zip")
        if path == "/api/traceability":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); obj=TRACEABILITY.summary(con); con.close(); return self.send_json(obj)
        if path.startswith("/api/traceability/") and path.endswith("/export"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            code=path.split("/")[-2]; con=core.db(); body=TRACEABILITY.export_bytes(con,code); con.close()
            return self.send_bytes(body, "application/json", f"LegalAIZit_{code}_trazabilidad_v2.0.json") if body else self.send_json({"error":"Producto no encontrado"},404)
        if path.startswith("/api/traceability/") and path.endswith("/fragments"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            code=path.split("/")[-2]; qs=parse_qs(urlparse(self.path).query); query=qs.get("q",[""])[0]
            con=core.db(); obj=TRACEABILITY.search_fragments(con,code,query); con.close(); return self.send_json(obj)
        if path.startswith("/api/traceability/"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            code=path.split("/")[-1]; con=core.db(); obj=TRACEABILITY.detail(con,code); con.close(); return self.send_json(obj or {},200 if obj else 404)
        if path == "/api/source-intake/export":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); body=INTAKE.export_bytes(con); con.close()
            return self.send_bytes(body, "application/zip", "LegalAIZit_Ingesta_Canonica_v2.0.zip")
        if path == "/api/source-intake":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); obj=INTAKE.summary(con); con.close(); return self.send_json(obj)
        if path.startswith("/api/source-intake-records/") and path.endswith("/download"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            intake_id=path.split("/")[-2]; con=core.db(); row=INTAKE.record(con,intake_id)
            if not row or not row["stored_path"]:
                con.close(); return self.send_json({"error":"Fuente no disponible"},404)
            try:
                body = read_reference_bytes(con, INFRA.objects, row["stored_path"])
                con.commit()
            finally:
                con.close()
            return self.send_bytes(body, row["detected_type"] or "application/octet-stream", row["original_name"])
        if path.startswith("/api/source-intake/"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            code=path.split("/")[-1]; con=core.db(); obj=INTAKE.detail(con,code); con.close(); return self.send_json(obj or {},200 if obj else 404)
        if path == "/api/normative-updates/export":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); body=NORMATIVE.export_bytes(con); con.close()
            return self.send_bytes(body, "application/zip", "LegalAIZit_Control_Actualizacion_Normativa_v2.0.zip")
        if path == "/api/normative-updates":
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db(); obj=NORMATIVE.summary(con,user["id"],user["role"]); con.close(); return self.send_json(obj)
        if path.startswith("/api/normative-updates/") and path.endswith("/export"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            update_id=path.split("/")[-2]; con=core.db(); body=NORMATIVE.export_bytes(con,update_id); con.close()
            return self.send_bytes(body, "application/zip", f"LegalAIZit_Novedad_{update_id}.zip")
        if path.startswith("/api/normative-updates/"):
            if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos."}, 403)
            update_id=path.split("/")[-1]; con=core.db(); obj=NORMATIVE.detail(con,update_id); con.close(); return self.send_json(obj or {},200 if obj else 404)
        if path == "/api/infrastructure":
            if user["role"] != "admin": return self.send_json({"error": "Solo administración puede acceder al centro de infraestructura."}, 403)
            con = core.db(); obj = INFRA.summary(con); con.close(); return self.send_json(obj)
        if path == "/api/infrastructure/doctor":
            if user["role"] != "admin": return self.send_json({"error": "Sin permisos."}, 403)
            con = core.db(); obj = INFRA.doctor(con); con.close(); return self.send_json(obj)
        if path.startswith("/api/infrastructure/backups/") and path.endswith("/download"):
            if user["role"] != "admin": return self.send_json({"error": "Sin permisos."}, 403)
            backup_id = path.split("/")[-2]; con = core.db(); row = INFRA.backups.row(con, backup_id); con.close()
            return self.send_file(row["file_path"], row["filename"]) if row and Path(row["file_path"]).is_file() else self.send_json({"error": "Backup no encontrado."}, 404)
        if path == "/api/v213/co-em-003":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Solo especialistas y administración pueden consultar la matriz interna de maduración."}, 403)
            return self.send_json(COEM003_V213.summary())
        if path == "/api/v214/co-em-004":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Solo especialistas y administración pueden consultar la matriz interna de maduración."}, 403)
            return self.send_json(COEM004_V214.summary())
        if path == "/api/v250/co-ar-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el cierre de arrendamiento de vivienda urbana."}, 403)
            return self.send_json(COAR001_V250.summary())
        if path == "/api/v250/co-ar-001/validation":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la validación de escenarios de arrendamiento."}, 403)
            return self.send_json(COAR001_VALIDATION_V250.summary())
        if path.startswith("/api/v250/co-ar-001/generations/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el gobierno documental de arrendamiento."}, 403)
            parts = [x for x in path.split("/") if x]
            generation_id = parts[4] if len(parts) > 4 else ""
            try:
                if path.endswith("/download"):
                    package = COAR001_FACTORY_V250.package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "Paquete no encontrado."}, 404)
                if path.endswith("/approved-download"):
                    package = COAR001_GOVERNANCE_V250.approved_package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "El paquete aún no cuenta con aprobación jurídica y QA vigentes."}, 409)
                if path.endswith("/compare"):
                    query = parse_qs(u.query)
                    return self.send_json(COAR001_GOVERNANCE_V250.compare(generation_id, int(query.get("from", [0])[0]), int(query.get("to", [0])[0])))
                return self.send_json(COAR001_GOVERNANCE_V250.summary(generation_id))
            except (ValueError, FileNotFoundError) as exc:
                return self.send_json({"error": str(exc)}, 404)
        if path == "/api/v249/co-ar-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la fábrica de arrendamiento de vivienda urbana."}, 403)
            return self.send_json(COAR001_V249.summary())
        if path.startswith("/api/v249/co-ar-001/generations/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el gobierno documental de arrendamiento."}, 403)
            parts = [x for x in path.split("/") if x]
            generation_id = parts[4] if len(parts) > 4 else ""
            try:
                if path.endswith("/download"):
                    package = COAR001_FACTORY_V249.package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "Paquete no encontrado."}, 404)
                if path.endswith("/approved-download"):
                    package = COAR001_GOVERNANCE_V249.approved_package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "El paquete aún no cuenta con aprobación jurídica y QA vigentes."}, 409)
                if path.endswith("/compare"):
                    query = parse_qs(u.query)
                    return self.send_json(COAR001_GOVERNANCE_V249.compare(generation_id, int(query.get("from", [0])[0]), int(query.get("to", [0])[0])))
                return self.send_json(COAR001_GOVERNANCE_V249.summary(generation_id))
            except (ValueError, FileNotFoundError) as exc:
                return self.send_json({"error": str(exc)}, 404)
        if path == "/api/v254/co-tr-002":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la capa canónica de fotodetección."}, 403)
            return self.send_json(COTR002_V254.summary())
        if path == "/api/v253/co-la-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el cierre de liquidación laboral."}, 403)
            return self.send_json(COLA001_V253.summary())
        if path == "/api/v253/co-la-001/validation":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la validación de escenarios."}, 403)
            return self.send_json(COLA001_VALIDATION_V253.summary())
        if path.startswith("/api/v253/co-la-001/generations/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el gobierno documental de liquidación laboral."}, 403)
            parts = [x for x in path.split("/") if x]
            generation_id = parts[4] if len(parts) > 4 else ""
            try:
                if path.endswith("/download"):
                    package = COLA001_FACTORY_V253.package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "Paquete no encontrado."}, 404)
                if path.endswith("/approved-download"):
                    package = COLA001_GOVERNANCE_V253.approved_package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "El paquete aún no cuenta con aprobación jurídica y QA vigentes."}, 409)
                if path.endswith("/compare"):
                    query = parse_qs(u.query)
                    return self.send_json(COLA001_GOVERNANCE_V253.compare(generation_id, int(query.get("from", [0])[0]), int(query.get("to", [0])[0])))
                return self.send_json(COLA001_GOVERNANCE_V253.summary(generation_id))
            except (ValueError, FileNotFoundError) as exc:
                return self.send_json({"error": str(exc)}, 404)
        if path == "/api/v252/co-la-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la fábrica documental de liquidación laboral."}, 403)
            return self.send_json(COLA001_V252.summary())
        if path.startswith("/api/v252/co-la-001/generations/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el gobierno documental de liquidación laboral."}, 403)
            parts = [x for x in path.split("/") if x]
            generation_id = parts[4] if len(parts) > 4 else ""
            try:
                if path.endswith("/download"):
                    package = COLA001_FACTORY_V252.package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "Paquete no encontrado."}, 404)
                if path.endswith("/approved-download"):
                    package = COLA001_GOVERNANCE_V252.approved_package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "El paquete aún no cuenta con aprobación jurídica y QA vigentes."}, 409)
                if path.endswith("/compare"):
                    query = parse_qs(u.query)
                    return self.send_json(COLA001_GOVERNANCE_V252.compare(generation_id, int(query.get("from", [0])[0]), int(query.get("to", [0])[0])))
                return self.send_json(COLA001_GOVERNANCE_V252.summary(generation_id))
            except (ValueError, FileNotFoundError) as exc:
                return self.send_json({"error": str(exc)}, 404)
        if path == "/api/v251/co-la-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la capa canónica de liquidación laboral."}, 403)
            return self.send_json(COLA001_V251.summary())
        if path == "/api/v248/co-ar-001":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la capa canónica de arrendamiento de vivienda urbana."}, 403)
            return self.send_json(COAR001_V248.summary())
        if path == "/api/v245/co-em-004":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la capa canónica de confidencialidad y propiedad intelectual."}, 403)
            return self.send_json(COEM004_V245.summary())
        if path == "/api/v246/co-em-004":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la fábrica de confidencialidad y propiedad intelectual."}, 403)
            return self.send_json(COEM004_V246.summary())
        if path == "/api/v247/co-em-004":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el cierre de confidencialidad y propiedad intelectual."}, 403)
            return self.send_json(COEM004_V247.summary())
        if path == "/api/v247/co-em-004/validation":
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar la validación de escenarios."}, 403)
            return self.send_json(COEM004_VALIDATION_V247.summary())
        if path.startswith("/api/v247/co-em-004/generations/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el gobierno documental de confidencialidad y propiedad intelectual."}, 403)
            parts = [x for x in path.split("/") if x]
            generation_id = parts[4] if len(parts) > 4 else ""
            try:
                if path.endswith("/download"):
                    package = COEM004_FACTORY_V247.package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "Paquete no encontrado."}, 404)
                if path.endswith("/approved-download"):
                    package = COEM004_GOVERNANCE_V247.approved_package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "El paquete aún no cuenta con aprobación jurídica y QA vigentes."}, 409)
                if path.endswith("/compare"):
                    query = parse_qs(u.query)
                    return self.send_json(COEM004_GOVERNANCE_V247.compare(generation_id, int(query.get("from", [0])[0]), int(query.get("to", [0])[0])))
                return self.send_json(COEM004_GOVERNANCE_V247.summary(generation_id))
            except (ValueError, FileNotFoundError) as exc:
                return self.send_json({"error": str(exc)}, 404)
        if path.startswith("/api/v246/co-em-004/generations/"):
            if user["role"] not in ("specialist", "admin"):
                return self.send_json({"error": "Sin permisos para consultar el gobierno documental de confidencialidad y propiedad intelectual."}, 403)
            parts = [x for x in path.split("/") if x]
            generation_id = parts[4] if len(parts) > 4 else ""
            try:
                if path.endswith("/download"):
                    package = COEM004_FACTORY_V246.package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "Paquete no encontrado."}, 404)
                if path.endswith("/approved-download"):
                    package = COEM004_GOVERNANCE_V246.approved_package_path(generation_id)
                    return self.send_file(package, download_name=package.name) if package else self.send_json({"error": "El paquete aún no cuenta con aprobación jurídica y QA vigentes."}, 409)
                if path.endswith("/compare"):
                    query = parse_qs(u.query)
                    return self.send_json(COEM004_GOVERNANCE_V246.compare(generation_id, int(query.get("from", [0])[0]), int(query.get("to", [0])[0])))
                return self.send_json(COEM004_GOVERNANCE_V246.summary(generation_id))
            except (ValueError, FileNotFoundError) as exc:
                return self.send_json({"error": str(exc)}, 404)
        if path == "/api/v215/complete-models":
            return self.send_json(COMPLETE_MODELS_V215.summary())
        if path == "/api/governance":
            if user["role"] != "admin": return self.send_json({"error": "Sin permisos."}, 403)
            con=core.db()
            try: obj=RELEASE_CANDIDATE.governance(con, core.PRODUCTS)
            finally: con.close()
            return self.send_json(obj)
        return self.send_json({"error": "Ruta no encontrada"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if not self.require_origin(): return
            if handle_public_post(self, path): return

            user = self.require_user()
            if not user: return
            if not self.require_csrf(): return
            if handle_auth_post(self, path, user): return
            if handle_m24_pilot_post(self, path, user): return
            if handle_m24_full_post(self, path, user): return
            if handle_m24_case_post(self, path, user): return
            if handle_m24_client_post(self, path, user): return
            if handle_m24_pilot_operations_post(self, path, user): return
            if handle_m24_professional_post(self, path, user): return
            if handle_m25_readiness_post(self, path, user): return
            if handle_m30_pilot_center_post(self, path, user): return
            if handle_m30_participant_post(self, path, user): return
            if handle_m30_governance_post(self, path, user): return
            if handle_m30_simulation_post(self, path, user): return
            if handle_m30_live_evaluation_post(self, path, user): return
            if handle_m31_preproduction_post(self, path, user): return
            if handle_m31_demo_reality_post(self, path, user): return
            if handle_m31_case_demo_post(self, path, user): return

            if api_prefix_match(path, COTR002_API_V256.PREFIX):
                data = self.read_json()
                status, obj = COTR002_API_V256.handle("POST", path, data, current_api_actor(user))
                return self.send_json(obj, status)
            if api_prefix_match(path, COTR001_API_V259.PREFIX):
                data = self.read_json()
                status, obj = COTR001_API_V259.handle("POST", path, data, current_api_actor(user))
                return self.send_json(obj, status)

            if path == "/api/v247/co-em-004/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar acuerdos de confidencialidad y propiedad intelectual."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COEM004_V247.evaluate(answers))

            if path == "/api/v247/co-em-004/generate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para generar acuerdos de confidencialidad y propiedad intelectual."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                try:
                    generated = COEM004_FACTORY_V247.generate(answers, user)
                    result = COEM004_GOVERNANCE_V247.register_generation(generated, answers, user)
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 422)
                manifest = result["manifest"]
                manifest["download_url"] = f"/api/v247/co-em-004/generations/{manifest['generation_id']}/download"
                manifest["governance_url"] = f"/api/v247/co-em-004/generations/{manifest['generation_id']}"
                manifest["approved_download_url"] = f"/api/v247/co-em-004/generations/{manifest['generation_id']}/approved-download"
                return self.send_json(manifest, 201)

            if path.startswith("/api/v247/co-em-004/generations/"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para gestionar revisiones de confidencialidad y propiedad intelectual."}, 403)
                parts = [x for x in path.split("/") if x]
                generation_id = parts[4] if len(parts) > 4 else ""
                action = parts[5] if len(parts) > 5 else ""
                data = self.read_json()
                try:
                    if action == "revisions":
                        return self.send_json(COEM004_GOVERNANCE_V247.create_revision(generation_id, data.get("answers") or {}, user, data.get("base_revision"), data.get("change_note")), 201)
                    if action == "approvals":
                        return self.send_json(COEM004_GOVERNANCE_V247.approve(generation_id, data.get("approval_type"), data.get("decision"), data.get("comment"), user))
                    return self.send_json({"error": "Acción no soportada."}, 404)
                except PermissionError as exc:
                    return self.send_json({"error": str(exc)}, 403)
                except (ValueError, FileNotFoundError) as exc:
                    return self.send_json({"error": str(exc)}, 422)

            if path == "/api/v246/co-em-004/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar acuerdos de confidencialidad y propiedad intelectual."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COEM004_V246.evaluate(answers))

            if path == "/api/v246/co-em-004/generate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para generar acuerdos de confidencialidad y propiedad intelectual."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                try:
                    generated = COEM004_FACTORY_V246.generate(answers, user)
                    result = COEM004_GOVERNANCE_V246.register_generation(generated, answers, user)
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 422)
                manifest = result["manifest"]
                manifest["download_url"] = f"/api/v246/co-em-004/generations/{manifest['generation_id']}/download"
                manifest["governance_url"] = f"/api/v246/co-em-004/generations/{manifest['generation_id']}"
                manifest["approved_download_url"] = f"/api/v246/co-em-004/generations/{manifest['generation_id']}/approved-download"
                return self.send_json(manifest, 201)

            if path.startswith("/api/v246/co-em-004/generations/"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para gestionar revisiones de confidencialidad y propiedad intelectual."}, 403)
                parts = [x for x in path.split("/") if x]
                generation_id = parts[4] if len(parts) > 4 else ""
                action = parts[5] if len(parts) > 5 else ""
                data = self.read_json()
                try:
                    if action == "revisions":
                        return self.send_json(COEM004_GOVERNANCE_V246.create_revision(generation_id, data.get("answers") or {}, user, data.get("base_revision"), data.get("change_note")), 201)
                    if action == "approvals":
                        return self.send_json(COEM004_GOVERNANCE_V246.approve(generation_id, data.get("approval_type"), data.get("decision"), data.get("comment"), user))
                    return self.send_json({"error": "Acción no soportada."}, 404)
                except PermissionError as exc:
                    return self.send_json({"error": str(exc)}, 403)
                except (ValueError, FileNotFoundError) as exc:
                    return self.send_json({"error": str(exc)}, 422)

            if path.startswith("/api/v250/co-ar-001/generations/"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para gestionar revisiones de arrendamiento."}, 403)
                parts = [x for x in path.split("/") if x]
                generation_id = parts[4] if len(parts) > 4 else ""
                action = parts[5] if len(parts) > 5 else ""
                data = self.read_json()
                try:
                    if action == "revisions":
                        return self.send_json(COAR001_GOVERNANCE_V250.create_revision(generation_id, data.get("answers") or {}, user, data.get("base_revision"), data.get("change_note")), 201)
                    if action == "approvals":
                        return self.send_json(COAR001_GOVERNANCE_V250.approve(generation_id, data.get("approval_type"), data.get("decision"), data.get("comment"), user))
                    return self.send_json({"error": "Acción no soportada."}, 404)
                except PermissionError as exc:
                    return self.send_json({"error": str(exc)}, 403)
                except (ValueError, FileNotFoundError) as exc:
                    return self.send_json({"error": str(exc)}, 422)

            if path == "/api/v250/co-ar-001/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar arrendamientos de vivienda urbana."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COAR001_V250.evaluate(answers))

            if path == "/api/v250/co-ar-001/generate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para generar contratos de arrendamiento."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                try:
                    generated = COAR001_FACTORY_V250.generate(answers, user)
                    result = COAR001_GOVERNANCE_V250.register_generation(generated, answers, user)
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 422)
                manifest = result["manifest"]
                manifest["download_url"] = f"/api/v250/co-ar-001/generations/{manifest['generation_id']}/download"
                manifest["governance_url"] = f"/api/v250/co-ar-001/generations/{manifest['generation_id']}"
                manifest["approved_download_url"] = f"/api/v250/co-ar-001/generations/{manifest['generation_id']}/approved-download"
                return self.send_json(manifest, 201)

            if path.startswith("/api/v249/co-ar-001/generations/"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para gestionar revisiones de arrendamiento."}, 403)
                parts = [x for x in path.split("/") if x]
                generation_id = parts[4] if len(parts) > 4 else ""
                action = parts[5] if len(parts) > 5 else ""
                data = self.read_json()
                try:
                    if action == "revisions":
                        return self.send_json(COAR001_GOVERNANCE_V249.create_revision(generation_id, data.get("answers") or {}, user, data.get("base_revision"), data.get("change_note")), 201)
                    if action == "approvals":
                        return self.send_json(COAR001_GOVERNANCE_V249.approve(generation_id, data.get("approval_type"), data.get("decision"), data.get("comment"), user))
                    return self.send_json({"error": "Acción no soportada."}, 404)
                except PermissionError as exc:
                    return self.send_json({"error": str(exc)}, 403)
                except (ValueError, FileNotFoundError) as exc:
                    return self.send_json({"error": str(exc)}, 422)

            if path == "/api/v249/co-ar-001/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar arrendamientos de vivienda urbana."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COAR001_V249.evaluate(answers))

            if path == "/api/v249/co-ar-001/generate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para generar contratos de arrendamiento."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                try:
                    generated = COAR001_FACTORY_V249.generate(answers, user)
                    result = COAR001_GOVERNANCE_V249.register_generation(generated, answers, user)
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 422)
                manifest = result["manifest"]
                manifest["download_url"] = f"/api/v249/co-ar-001/generations/{manifest['generation_id']}/download"
                manifest["governance_url"] = f"/api/v249/co-ar-001/generations/{manifest['generation_id']}"
                manifest["approved_download_url"] = f"/api/v249/co-ar-001/generations/{manifest['generation_id']}/approved-download"
                return self.send_json(manifest, 201)

            if path.startswith("/api/v253/co-la-001/generations/"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para modificar el gobierno documental de liquidación laboral."}, 403)
                parts = [x for x in path.split("/") if x]
                generation_id = parts[4] if len(parts) > 4 else ""
                data = self.read_json()
                try:
                    if path.endswith("/revisions"):
                        return self.send_json(COLA001_GOVERNANCE_V253.create_revision(generation_id, data.get("answers") or {}, user, data.get("base_revision"), data.get("change_note")), 201)
                    if path.endswith("/approvals"):
                        return self.send_json(COLA001_GOVERNANCE_V253.approve(generation_id, data.get("approval_type"), data.get("decision"), data.get("comment"), user))
                except (ValueError, FileNotFoundError) as exc:
                    return self.send_json({"error": str(exc)}, 400)
            if path == "/api/v254/co-tr-002/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar expedientes de fotodetección."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COTR002_V254.evaluate(answers))

            if path == "/api/v253/co-la-001/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar liquidaciones laborales."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict):
                    return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COLA001_V253.evaluate(answers))
            if path == "/api/v253/co-la-001/generate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para generar liquidaciones laborales."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict):
                    return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                try:
                    generated = COLA001_FACTORY_V253.generate(answers, user)
                    result = COLA001_GOVERNANCE_V253.register_generation(generated, answers, user)
                    manifest = result["manifest"]
                    manifest["download_url"] = f"/api/v253/co-la-001/generations/{manifest['generation_id']}/download"
                    manifest["governance_url"] = f"/api/v253/co-la-001/generations/{manifest['generation_id']}"
                    manifest["approved_download_url"] = f"/api/v253/co-la-001/generations/{manifest['generation_id']}/approved-download"
                    return self.send_json(manifest, 201)
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 409)
            if path.startswith("/api/v252/co-la-001/generations/"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para gestionar revisiones de liquidación laboral."}, 403)
                parts = [x for x in path.split("/") if x]
                generation_id = parts[4] if len(parts) > 4 else ""
                action = parts[5] if len(parts) > 5 else ""
                data = self.read_json()
                try:
                    if action == "revisions":
                        return self.send_json(COLA001_GOVERNANCE_V252.create_revision(generation_id, data.get("answers") or {}, user, data.get("base_revision"), data.get("change_note")), 201)
                    if action == "approvals":
                        return self.send_json(COLA001_GOVERNANCE_V252.approve(generation_id, data.get("approval_type"), data.get("decision"), data.get("comment"), user))
                    return self.send_json({"error": "Acción no soportada."}, 404)
                except PermissionError as exc:
                    return self.send_json({"error": str(exc)}, 403)
                except (ValueError, FileNotFoundError) as exc:
                    return self.send_json({"error": str(exc)}, 422)

            if path == "/api/v252/co-la-001/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar liquidaciones laborales."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COLA001_V252.evaluate(answers))

            if path == "/api/v252/co-la-001/generate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para generar liquidaciones laborales."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                try:
                    generated = COLA001_FACTORY_V252.generate(answers, user)
                    result = COLA001_GOVERNANCE_V252.register_generation(generated, answers, user)
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 422)
                manifest = result["manifest"]
                manifest["download_url"] = f"/api/v252/co-la-001/generations/{manifest['generation_id']}/download"
                manifest["governance_url"] = f"/api/v252/co-la-001/generations/{manifest['generation_id']}"
                manifest["approved_download_url"] = f"/api/v252/co-la-001/generations/{manifest['generation_id']}/approved-download"
                return self.send_json(manifest, 201)

            if path == "/api/v251/co-la-001/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar liquidaciones laborales."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COLA001_V251.evaluate(answers))

            if path == "/api/v248/co-ar-001/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar arrendamientos de vivienda urbana."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COAR001_V248.evaluate(answers))

            if path == "/api/v245/co-em-004/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar acuerdos de confidencialidad y propiedad intelectual."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COEM004_V245.evaluate(answers))

            if path == "/api/v242/co-em-003/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar servicios independientes."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COEM003_V242.evaluate(answers))

            if path == "/api/v244/co-em-003/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar servicios independientes."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COEM003_V244.evaluate(answers))

            if path == "/api/v244/co-em-003/generate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para generar contratos de servicios independientes."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                try:
                    generated = COEM003_FACTORY_V244.generate(answers, user)
                    result = COEM003_GOVERNANCE_V244.register_generation(generated, answers, user)
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 422)
                manifest = result["manifest"]
                manifest["download_url"] = f"/api/v244/co-em-003/generations/{manifest['generation_id']}/download"
                manifest["governance_url"] = f"/api/v244/co-em-003/generations/{manifest['generation_id']}"
                manifest["approved_download_url"] = f"/api/v244/co-em-003/generations/{manifest['generation_id']}/approved-download"
                return self.send_json(manifest, 201)

            if path.startswith("/api/v244/co-em-003/generations/"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para gestionar revisiones de servicios independientes."}, 403)
                parts = [x for x in path.split("/") if x]
                generation_id = parts[4] if len(parts) > 4 else ""
                action = parts[5] if len(parts) > 5 else ""
                data = self.read_json()
                try:
                    if action == "revisions":
                        return self.send_json(COEM003_GOVERNANCE_V244.create_revision(generation_id, data.get("answers") or {}, user, data.get("base_revision"), data.get("change_note")), 201)
                    if action == "approvals":
                        return self.send_json(COEM003_GOVERNANCE_V244.approve(generation_id, data.get("approval_type"), data.get("decision"), data.get("comment"), user))
                    return self.send_json({"error": "Acción no soportada."}, 404)
                except (ValueError, FileNotFoundError) as exc:
                    return self.send_json({"error": str(exc)}, 422)

            if path == "/api/v243/co-em-003/evaluate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar servicios independientes."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                return self.send_json(COEM003_V243.evaluate(answers))

            if path == "/api/v243/co-em-003/generate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para generar contratos de servicios independientes."}, 403)
                data = self.read_json(); answers = data.get("answers") or {}
                if not isinstance(answers, dict): return self.send_json({"error": "Las respuestas deben enviarse como objeto JSON."}, 400)
                try:
                    generated = COEM003_FACTORY_V243.generate(answers, user)
                    result = COEM003_GOVERNANCE_V243.register_generation(generated, answers, user)
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 422)
                manifest = result["manifest"]
                manifest["download_url"] = f"/api/v243/co-em-003/generations/{manifest['generation_id']}/download"
                manifest["governance_url"] = f"/api/v243/co-em-003/generations/{manifest['generation_id']}"
                manifest["approved_download_url"] = f"/api/v243/co-em-003/generations/{manifest['generation_id']}/approved-download"
                return self.send_json(manifest, 201)

            if path.startswith("/api/v243/co-em-003/generations/"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para gestionar revisiones de servicios independientes."}, 403)
                parts = [x for x in path.split("/") if x]
                generation_id = parts[4] if len(parts) > 4 else ""
                action = parts[5] if len(parts) > 5 else ""
                data = self.read_json()
                try:
                    if action == "revisions":
                        result = COEM003_GOVERNANCE_V243.create_revision(generation_id, data.get("answers") or {}, user, data.get("base_revision"), data.get("change_note"))
                        return self.send_json(result, 201)
                    if action == "approvals":
                        result = COEM003_GOVERNANCE_V243.approve(generation_id, data.get("approval_type"), data.get("decision"), data.get("comment"), user)
                        return self.send_json(result)
                    return self.send_json({"error": "Acción de gobierno documental no encontrada."}, 404)
                except PermissionError as exc:
                    return self.send_json({"error": str(exc)}, 403)
                except (ValueError, FileNotFoundError) as exc:
                    return self.send_json({"error": str(exc)}, 422)

            if path == "/api/v239/co-la-002/generate":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para generar contratación laboral canónica."}, 403)
                data = self.read_json()
                answers = data.get("answers") or {}
                if not isinstance(answers, dict):
                    return self.send_json({"error": "Las respuestas deben enviarse como un objeto JSON."}, 400)
                try:
                    result = COLA002_FACTORY_V239.generate(answers, user)
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 422)
                result = COLA002_GOVERNANCE_V240.register_generation(result, answers, user)
                manifest = result["manifest"]
                manifest["governance_version"] = manifest.get("version", "2.40")
                manifest["version"] = "2.39"
                manifest["download_url"] = f"/api/v239/co-la-002/generations/{manifest['generation_id']}/download"
                manifest["governance_url"] = f"/api/v240/co-la-002/generations/{manifest['generation_id']}"
                return self.send_json(manifest, 201)

            if path.startswith("/api/v240/co-la-002/generations/"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para gestionar revisiones laborales."}, 403)
                parts = [x for x in path.split("/") if x]
                generation_id = parts[4] if len(parts) > 4 else ""
                action = parts[5] if len(parts) > 5 else ""
                data = self.read_json()
                try:
                    if action == "revisions":
                        result = COLA002_GOVERNANCE_V240.create_revision(generation_id, data.get("answers") or {}, user, data.get("base_revision"), data.get("change_note"))
                        return self.send_json(result, 201)
                    if action == "approvals":
                        result = COLA002_GOVERNANCE_V240.approve(generation_id, data.get("approval_type"), data.get("decision"), data.get("comment"), user)
                        return self.send_json(result)
                    return self.send_json({"error": "Acción de gobierno documental no encontrada."}, 404)
                except PermissionError as exc:
                    return self.send_json({"error": str(exc)}, 403)
                except (ValueError, FileNotFoundError) as exc:
                    return self.send_json({"error": str(exc)}, 422)

            if path in ("/api/v237/co-la-002/evaluate", "/api/v238/co-la-002/evaluate"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para evaluar la contratación laboral canónica."}, 403)
                data = self.read_json()
                answers = data.get("answers") or {}
                if not isinstance(answers, dict):
                    return self.send_json({"error": "Las respuestas deben enviarse como un objeto JSON."}, 400)
                result = COLA002_V236.evaluate(answers)
                result["version"] = "2.37" if path.startswith("/api/v237/") else "2.38"
                return self.send_json(result)

            if path == "/api/v221/release-cycle/releases":
                data = self.read_json()
                con = core.db()
                try:
                    result = RELEASE_CYCLE_V221.create_release(
                        con, user, data.get("version", ""), data.get("title", ""),
                        data.get("summary", ""), data.get("change_set_ids") or [],
                    )
                    core.audit(con, user["id"], "release_cycle", result["release"]["id"], "create", {"version": data.get("version"), "snapshot_sha256": result["release"]["snapshot_sha256"]})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)

            if path.startswith("/api/v221/release-cycle/") and path.endswith("/legal-confirm"):
                release_id = path.split("/")[-2]
                data = self.read_json()
                con = core.db()
                try:
                    result = RELEASE_CYCLE_V221.confirm_legal(con, user, release_id, data.get("statement", ""))
                    core.audit(con, user["id"], "release_cycle", release_id, "legal_confirm", {"version": VERSION})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except KeyError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 404)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path.startswith("/api/v221/release-cycle/") and path.endswith("/qa-confirm"):
                release_id = path.split("/")[-2]
                data = self.read_json()
                con = core.db()
                try:
                    result = RELEASE_CYCLE_V221.confirm_qa(con, user, release_id, data.get("statement", ""))
                    core.audit(con, user["id"], "release_cycle", release_id, "qa_confirm", {"version": VERSION})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except KeyError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 404)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path.startswith("/api/v221/release-cycle/") and path.endswith("/rebase"):
                release_id = path.split("/")[-2]
                con = core.db()
                try:
                    result = RELEASE_CYCLE_V221.rebase(con, user, release_id)
                    core.audit(con, user["id"], "release_cycle", release_id, "rebase", {"snapshot_sha256": result["release"]["snapshot_sha256"]})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except KeyError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 404)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path.startswith("/api/v221/release-cycle/") and path.endswith("/publish"):
                release_id = path.split("/")[-2]
                con = core.db()
                try:
                    result = RELEASE_CYCLE_V221.publish(con, user, release_id)
                    core.audit(con, user["id"], "release_cycle", release_id, "publish", {"version": result["release"]["version"], "manifest_sha256": result["release"]["manifest_sha256"]})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except KeyError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 404)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path == "/api/v220/change-control/preview":
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para planificar cambios."}, 403)
                data = self.read_json()
                try:
                    result = CHANGE_CONTROL_V220.plan(data.get("paths") or [])
                except ValueError as exc:
                    return self.send_json({"error": str(exc)}, 400)
                return self.send_json(result)

            if path == "/api/v220/change-control/change-sets":
                data = self.read_json()
                con = core.db()
                try:
                    result = CHANGE_CONTROL_V220.create_change_set(
                        con, user, data.get("title", ""), data.get("summary", ""), data.get("paths") or []
                    )
                    core.audit(con, user["id"], "change_set", result["change"]["id"], "create", {"version": VERSION, "plan_sha256": result["change"]["plan_sha256"]})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)

            if path.startswith("/api/v220/change-control/") and "/controls/" in path:
                parts = path.strip("/").split("/")
                change_id, control_code = parts[3], parts[5]
                data = self.read_json()
                con = core.db()
                try:
                    result = CHANGE_CONTROL_V220.complete_control(
                        con, user, change_id, control_code, data.get("result", ""), data.get("notes", ""),
                        data.get("evidence_ref", ""), data.get("evidence_sha256", ""),
                    )
                    core.audit(con, user["id"], "change_set", change_id, "control_complete", {"control_code": control_code, "result": data.get("result")})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except KeyError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 404)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path.startswith("/api/v220/change-control/") and path.endswith("/close"):
                change_id = path.split("/")[-2]
                con = core.db()
                try:
                    result = CHANGE_CONTROL_V220.close(con, user, change_id)
                    core.audit(con, user["id"], "change_set", change_id, "close", {"version": VERSION})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except KeyError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 404)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path == "/api/v219/validation-governance/legal-owner":
                data = self.read_json()
                con = core.db()
                try:
                    result = VALIDATION_V219.confirm_legal_owner(con, user, data.get("statement", ""))
                    core.audit(con, user["id"], "validation_governance", "GOV-219", "legal_owner_confirmed", {"version": VERSION})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path == "/api/v219/validation-governance/technical":
                data = self.read_json()
                con = core.db()
                try:
                    result = VALIDATION_V219.technical_decision(con, user, data.get("decision"), data.get("comment", ""))
                    core.audit(con, user["id"], "validation_governance", "GOV-219", "technical_decision", {"decision": data.get("decision"), "version": VERSION})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path == "/api/v210/canonical-activation/scan":
                if user["role"] != "admin":
                    return self.send_json({"error": "Solo administración puede ingresar archivos desde la carpeta local."}, 403)
                con = core.db()
                try:
                    result = ACTIVATION_V210.scan(con, user["id"], user["role"])
                    core.audit(con, user["id"], "canonical_activation", result["scan_id"], "dropbox_scan", result)
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)
            if path.startswith("/api/v210/canonical-activation/") and path.endswith("/rehearse"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "Sin permisos para ejecutar el ensayo."}, 403)
                code = path.split("/")[-2].upper()
                con = core.db()
                try:
                    result = ACTIVATION_V210.rehearse(con, code, user["id"])
                    core.audit(con, user["id"], "canonical_activation", result["id"], "rehearse", result)
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)

            if path == "/api/drafts/transfer-anonymous":
                data = self.read_json()
                con = core.db()
                try:
                    result = ANON_DRAFTS.transfer(con, data.get("recovery_code") or "", user["id"])
                    core.audit(con, user["id"], "anonymous_draft", result["anonymous_draft_id"], "transfer", {"draft_id": result["draft"]["id"]})
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)

            if path == "/api/drafts":
                data = self.read_json()
                con = core.db()
                try:
                    result = SELF_SERVICE.save_draft(
                        con, user["id"], data.get("product_code"), data.get("answers") or {},
                        data.get("current_step") or 0, data.get("title") or "", data.get("result")
                    )
                    core.audit(con, user["id"], "service_draft", result["id"], "save", {"product_code": result["product_code"], "current_step": result["current_step"]})
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)
            if path.startswith("/api/drafts/") and path.endswith("/delete"):
                draft_id = path.split("/")[-2]
                con = core.db()
                deleted = SELF_SERVICE.delete_draft(con, user["id"], draft_id)
                if deleted:
                    core.audit(con, user["id"], "service_draft", draft_id, "delete", {})
                con.commit(); con.close()
                return self.send_json({"ok": deleted}, 200 if deleted else 404)
            if path == "/api/checkout/orders":
                data = self.read_json()
                con = core.db()
                try:
                    result = SELF_SERVICE.create_order(
                        con, user["id"], data.get("product_code"), data.get("result") or {},
                        bool(data.get("review_selected")),
                        data.get("service_level")
                    )
                    core.audit(con, user["id"], "checkout_order", result["id"], "create", {"total": result["total"], "review_selected": result["review_selected"]})
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)
            if path.startswith("/api/checkout/orders/") and path.endswith("/intent"):
                order_id = path.split("/")[-2]
                data = self.read_json()
                con = core.db()
                try:
                    order = SELF_SERVICE.get_order(con, user["id"], order_id, admin=user["role"] == "admin")
                    if not order:
                        con.close(); return self.send_json({"error": "Orden no encontrada."}, 404)
                    result = PAYMENTS.create_intent(
                        con,
                        order,
                        order["user_id"],
                        data.get("provider") or "sandbox_card",
                        data.get("idempotency_key") or ("checkout-" + order_id),
                    )
                    core.audit(con, user["id"], "payment_intent", result["id"], "create", {"order_id": order_id, "provider": result["provider"]})
                    con.commit()
                except (ValueError, PermissionError) as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)

            if path.startswith("/api/payment-intents/") and path.endswith("/simulate"):
                intent_id = path.split("/")[-2]
                data = self.read_json()
                con = core.db()
                try:
                    current = PAYMENTS.intent(con, intent_id)
                    if not current or (user["role"] != "admin" and current.get("user_id") != user["id"]):
                        con.close(); return self.send_json({"error": "Intento no encontrado o sin acceso."}, 404)
                    result = PAYMENTS.simulate(con, intent_id, data.get("outcome") or "approved", user["id"])
                    core.audit(con, user["id"], "payment_intent", intent_id, "sandbox_result", {"status": result["status"], "event": result["event"]["event_id"]})
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path.startswith("/api/checkout/orders/") and path.endswith("/pay"):
                order_id = path.split("/")[-2]
                data = self.read_json()
                con = core.db()
                try:
                    result = SELF_SERVICE.pay_order(con, user["id"], order_id, data.get("payment_method") or "")
                    core.audit(con, user["id"], "checkout_order", order_id, "simulated_payment", {"receipt_number": result.get("receipt_number")})
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path == "/api/infrastructure/backups":
                if user["role"] != "admin": return self.send_json({"error": "Solo administración puede crear backups."}, 403)
                con = core.db(); result = INFRA.backups.create(con, core.DB, user["id"])
                INFRA.event(con, "backup_created", user["id"], {"backup_id": result["id"], "sha256": result["sha256"]})
                core.audit(con, user["id"], "infrastructure_backup", result["id"], "create", result)
                con.commit(); con.close(); return self.send_json(result, 201)
            if path.startswith("/api/infrastructure/backups/") and path.endswith("/verify"):
                if user["role"] != "admin": return self.send_json({"error": "Sin permisos."}, 403)
                backup_id = path.split("/")[-2]; con = core.db(); result = INFRA.backups.verify(con, backup_id)
                INFRA.event(con, "backup_verified", user["id"], result)
                core.audit(con, user["id"], "infrastructure_backup", backup_id, "verify", result)
                con.commit(); con.close(); return self.send_json(result)
            if path == "/api/infrastructure/objects/verify":
                if user["role"] != "admin": return self.send_json({"error": "Sin permisos."}, 403)
                con = core.db(); result = INFRA.objects.verify_all(con)
                INFRA.event(con, "object_store_verified", user["id"], result)
                con.commit(); con.close(); return self.send_json(result)

            if path.startswith("/api/source-intake/") and path.endswith("/upload"):
                if user["role"] != "admin": return self.send_json({"error": "Solo administración puede recibir binarios canónicos."}, 403)
                code=path.split("/")[-2]
                fields,files=self.read_multipart()
                if not files: return self.send_json({"error":"No se recibió ningún archivo."},400)
                f=files[0]
                if len(f["data"])>core.MAX_UPLOAD: return self.send_json({"error":"El archivo supera el límite de 10 MB."},400)
                detected,digest,security_status=validate_upload(f["filename"],f["data"])
                con=core.db()
                result=INTAKE.upload(con,code,fields.get("artifact_key", ""),f["filename"],f["data"],detected,digest,user["id"],user["role"])
                core.audit(con,user["id"],"canonical_intake",result["intake_id"],"upload",{**result,"security_status":security_status})
                security_event(con,user["id"],"canonical_source_upload","accepted",self.ip,self.agent,{"intake_id":result["intake_id"],"product_code":code,"sha256":digest})
                con.commit();con.close();return self.send_json(result,201)

            if path == "/api/file-center/upload":
                fields, files = self.read_multipart()
                cid = fields.get("case_id", "")
                if not cid or not can_access_case(user, cid):
                    return self.send_json({"error": "Seleccione un expediente válido y accesible."}, 404)
                if not files:
                    return self.send_json({"error": "No se recibió ningún archivo."}, 400)
                f = files[0]
                if len(f["data"]) > core.MAX_UPLOAD:
                    return self.send_json({"error": "El archivo supera el límite de 10 MB."}, 400)
                detected, digest, security_status = validate_upload(f["filename"], f["data"])
                aid = "ATT-" + uuid.uuid4().hex[:8].upper()
                t = core.now()
                category = fields.get("category", "Soporte general")
                requirement_key = fields.get("requirement_key") or None
                description = (fields.get("description") or "").strip()[:1000]
                con = core.db()
                stored = INFRA.objects.put(con, f"cases/{cid}/attachments", f["filename"], f["data"], detected, user["id"])
                security_status = security_status + "; cifrado AES-256-GCM en almacenamiento local"
                con.execute(
                    """INSERT INTO attachments(id,case_id,name,mime_type,size_bytes,category,file_path,created_at,sha256,detected_type,security_status,uploaded_by,requirement_key,description,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (aid, cid, f["filename"], detected, len(f["data"]), category, stored["reference"], t, digest, detected, security_status, user["id"], requirement_key, description, t),
                )
                con.execute("UPDATE case_tasks SET status='Completada',updated_at=? WHERE case_id=? AND label='Cargar y clasificar soportes'", (t, cid))
                con.execute("UPDATE cases SET updated_at=? WHERE id=?", (t, cid))
                con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (cid, "attachment", f"Soporte validado y cargado desde el Centro de Archivos: {f['filename']} ({category}).", t))
                core.audit(con, user["id"], "attachment", aid, "upload", {"case_id": cid, "name": f["filename"], "size": len(f["data"]), "sha256": digest, "requirement_key": requirement_key})
                security_event(con, user["id"], "upload", "accepted", self.ip, self.agent, {"attachment_id": aid, "sha256": digest, "detected_type": detected})
                con.commit(); con.close()
                return self.send_json({"ok": True, "attachment_id": aid, "name": f["filename"], "sha256": digest, "security_status": security_status}, 201)

            if path.startswith("/api/cases/") and path.endswith("/attachments"):
                cid = path.split("/")[-2]
                if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                fields, files = self.read_multipart()
                if not files: return self.send_json({"error": "No se recibió ningún archivo."}, 400)
                f = files[0]
                if len(f["data"]) > core.MAX_UPLOAD: return self.send_json({"error": "El archivo supera el límite de 10 MB."}, 400)
                detected, digest, security_status = validate_upload(f["filename"], f["data"])
                aid = "ATT-" + uuid.uuid4().hex[:8].upper()
                t = core.now(); category = fields.get("category", "Soporte general")
                requirement_key = fields.get("requirement_key") or None
                description = (fields.get("description") or "").strip()[:1000]
                con = core.db()
                stored = INFRA.objects.put(con, f"cases/{cid}/attachments", f["filename"], f["data"], detected, user["id"])
                security_status = security_status + "; cifrado AES-256-GCM en almacenamiento local"
                con.execute(
                    "INSERT INTO attachments(id,case_id,name,mime_type,size_bytes,category,file_path,created_at,sha256,detected_type,security_status,uploaded_by,requirement_key,description,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (aid, cid, f["filename"], detected, len(f["data"]), category, stored["reference"], t, digest, detected, security_status, user["id"], requirement_key, description, t),
                )
                con.execute("UPDATE case_tasks SET status='Completada',updated_at=? WHERE case_id=? AND label='Cargar y clasificar soportes'", (t, cid))
                con.execute("UPDATE cases SET updated_at=? WHERE id=?", (t, cid))
                con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (cid, "attachment", f"Soporte validado y cargado: {f['filename']} ({category}).", t))
                core.audit(con, user["id"], "attachment", aid, "upload", {"case_id": cid, "name": f["filename"], "size": len(f["data"]), "sha256": digest})
                security_event(con, user["id"], "upload", "accepted", self.ip, self.agent, {"attachment_id": aid, "sha256": digest, "detected_type": detected})
                con.commit(); con.close()
                return self.send_json({"ok": True, "attachment_id": aid, "name": f["filename"], "sha256": digest, "security_status": security_status}, 201)

            data = self.read_json()
            if path.startswith("/api/documents/") and path.endswith("/acceptances"):
                did = path.split("/")[-2]
                row = document_row(user, did)
                if not row:
                    return self.send_json({"error": "Documento no encontrado o sin acceso."}, 404)
                if user["role"] not in ("client", "admin"):
                    return self.send_json({"error": "La aceptación corresponde al titular del expediente o a administración autorizada."}, 403)
                con = core.db()
                try:
                    result = PDF_ACCEPTANCE.accept(
                        con, did, user, data.get("signer_name") or user.get("name"),
                        bool(data.get("accepted")), data.get("document_sha256") or "",
                        self.ip, self.agent, data.get("acceptance_type") or "Aceptación de borrador personalizado"
                    )
                    core.audit(con, user["id"], "document_acceptance", result["id"], "accept", {"document_id": did, "receipt_sha256": result.get("receipt_sha256")})
                    con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (row["case_id"], "document_acceptance", f"Se registró la aceptación electrónica simple del documento {row['name']}.", core.now()))
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)
            if path.startswith("/api/document-acceptances/") and path.endswith("/verify"):
                acceptance_id = path.split("/")[-2]
                con = core.db()
                try:
                    obj = PDF_ACCEPTANCE.detail(con, acceptance_id)
                    if not obj or not document_row(user, obj.get("document_id")):
                        con.close(); return self.send_json({"error": "Constancia no encontrada o sin acceso."}, 404)
                    result = PDF_ACCEPTANCE.verify(con, acceptance_id)
                    core.audit(con, user["id"], "document_acceptance", acceptance_id, "verify", result)
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)
            if path.startswith("/api/cases/") and path.endswith("/candidate-generate-v29"):
                cid = path.split("/")[-2]
                if not can_access_case(user, cid):
                    return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                con = core.db()
                try:
                    result = PRIORITY_V29.generate(con, cid, user["id"])
                    core.audit(con, user["id"], "case", cid, "priority_candidate_generation_v29", result)
                    delivery = DELIVERY.summary(con, cid)
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 409)
                finally:
                    try: con.close()
                    except Exception: pass
                result["document_delivery"] = delivery
                return self.send_json(result, 201)
            if path.startswith("/api/cases/") and path.endswith("/candidate-generate-v28"):
                cid = path.split("/")[-2]
                if not can_access_case(user, cid):
                    return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                con = core.db()
                try:
                    result = COEM003_V28.generate(con, cid, user["id"])
                    core.audit(con, user["id"], "case", cid, "candidate_generation_v28", result)
                    delivery = DELIVERY.summary(con, cid)
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 409)
                finally:
                    try: con.close()
                    except Exception: pass
                result["document_delivery"] = delivery
                return self.send_json(result, 201)
            if path.startswith("/api/cases/") and path.endswith("/canonical-generate"):
                if user["role"] not in ("specialist", "admin"):
                    return self.send_json({"error": "La generación primaria requiere especialista o administración."}, 403)
                cid = path.split("/")[-2]
                if not can_access_case(user, cid):
                    return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                con = core.db()
                try:
                    result = CANONICAL_GENERATION.generate(con, cid, user["id"])
                    core.audit(con, user["id"], "case", cid, "canonical_primary_generate", result)
                    delivery = DELIVERY.summary(con, cid)
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 409)
                finally:
                    try: con.close()
                    except Exception: pass
                result["document_delivery"] = delivery
                return self.send_json(result, 201)
            if path == "/api/activity/mark-read":
                con = core.db()
                try:
                    result = WORKSPACE.mark_activity_read(con, user["id"])
                    con.commit()
                finally:
                    con.close()
                return self.send_json(result)
            if path.startswith("/api/document-factory/") and path.endswith("/working-draft"):
                if user["role"] != "admin":
                    return self.send_json({"error": "Solo administración puede guardar borradores de trabajo."}, 403)
                tid = path.split("/")[-2]
                con = core.db()
                try:
                    result = WORKSPACE.save_working_draft(
                        con, tid, user["id"], int(data.get("base_revision_id") or 0),
                        data.get("content") or {}, data.get("note") or ""
                    )
                    core.audit(con, user["id"], "canonical_template", tid, "save_working_draft", result)
                    con.commit()
                finally:
                    con.close()
                return self.send_json(result, 201)
            if path == "/api/diagnose":
                return self.send_json(core.diagnose(data.get("product_code"), data.get("answers") or {}, strict=bool(data.get("strict"))))
            if path == "/api/cases":
                if user["role"] not in ("client", "admin"): return self.send_json({"error": "Solo clientes o administración pueden crear expedientes."}, 403)
                owner = user["id"] if user["role"] == "client" else data.get("owner_id", "USR-CLIENT")
                order_id = data.get("order_id") or None
                if order_id and user["role"] == "client":
                    con = core.db(); order = SELF_SERVICE.get_order(con, user["id"], order_id); con.close()
                    if not order: return self.send_json({"error": "Orden no encontrada."}, 404)
                    if order.get("status") not in {"Pagado (simulado)", "Pagado (sandbox)"}: return self.send_json({"error": "Confirma el checkout antes de generar el expediente."}, 409)
                    if order.get("product_code") != data.get("product_code"): return self.send_json({"error": "La orden no corresponde a esta solución."}, 409)
                created = core.create_case(data.get("product_code"), data.get("answers") or {}, data.get("title"), owner)
                con = core.db()
                try:
                    delivery = DELIVERY.summary(con, created["case_id"])
                    con.commit()
                finally:
                    con.close()
                created["document_delivery"] = delivery
                if order_id and user["role"] == "client":
                    con = core.db()
                    try:
                        order = SELF_SERVICE.attach_case(con, user["id"], order_id, created["case_id"])
                        journey = M24_CASE_JOURNEY.bootstrap_paid_generation(con, created["case_id"], order, user)
                        con.execute("DELETE FROM service_drafts WHERE user_id=? AND product_code=?", (user["id"], data.get("product_code")))
                        core.audit(con, user["id"], "checkout_order", order_id, "case_generated", {"case_id": created["case_id"], "journey_state": journey.get("current_state")})
                        con.commit()
                    finally:
                        con.close()
                    created["order"] = order
                    created["case_journey"] = journey
                return self.send_json(created, 201)
            if path.startswith("/api/cases/") and path.endswith("/document-package"):
                cid = path.split("/")[-2]
                if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                con = core.db()
                try:
                    result = DELIVERY.build(con, cid, user["id"])
                    core.audit(con, user["id"], "document_package", result["id"], "build", {"case_id": cid, "files": result["files"], "package_sha256": result["package_sha256"]})
                    con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (cid, "document_package", f"Se generó un paquete documental con {result['files']} archivos y manifiesto de integridad.", core.now()))
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result, 201)

            if path.startswith("/api/document-packages/") and path.endswith("/verify"):
                package_id = path.split("/")[-2]
                con = core.db()
                try:
                    row = con.execute("SELECT case_id FROM document_packages WHERE id=?", (package_id,)).fetchone()
                    if not row or not can_access_case(user, row["case_id"]):
                        con.close(); return self.send_json({"error": "Paquete no encontrado o sin acceso."}, 404)
                    result = DELIVERY.verify(con, package_id)
                    core.audit(con, user["id"], "document_package", package_id, "verify", result)
                    con.commit()
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 400)
                finally:
                    try: con.close()
                    except Exception: pass
                return self.send_json(result)

            if path.startswith("/api/cases/") and path.endswith("/regenerate"):
                if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos para regenerar documentos."}, 403)
                cid = path.split("/")[-2]
                if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                case = core.case_detail(cid)
                docs = core.generate_case_documents(cid, case["product_code"], case["answers"], case["result"], actor=user["id"], note=data.get("note", "Regeneración controlada v2.7"))
                con = core.db()
                try:
                    con.execute("UPDATE cases SET updated_at=? WHERE id=?", (core.now(), cid))
                    delivery = DELIVERY.summary(con, cid)
                    con.commit()
                finally:
                    con.close()
                return self.send_json({"ok": True, "documents": docs, "document_delivery": delivery})
            if path.startswith("/api/cases/") and path.endswith("/factory-generate"):
                if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos para generar desde la fábrica."}, 403)
                cid=path.split("/")[-2]
                if not can_access_case(user,cid): return self.send_json({"error":"Caso no encontrado o sin acceso."},404)
                con=core.db();case=con.execute("SELECT * FROM cases WHERE id=?",(cid,)).fetchone()
                if not case: con.close(); return self.send_json({"error":"Caso no encontrado."},404)
                if case["risk"]=="red": con.close(); return self.send_json({"error":"Los casos rojos no pueden producir documentos de fábrica; requieren escalamiento."},409)
                templates=FACTORY.published_for_product(con,case["product_code"])
                if not templates: con.close(); return self.send_json({"error":"No existen plantillas con aprobación jurídica y QA para este producto."},409)
                answers=json.loads(case["answers"]);created=[];t=core.now()
                for tpl in templates:
                    content=tpl["content"];preview=FACTORY.render(content,answers)
                    filename=core.safe_filename(f"{case['product_code']}_{cid}_{content.get('filename_suffix',content['kind'])}_factory_r{tpl['revision_id']}.docx")
                    target=core.GENERATED/filename
                    from docx_builder import build_docx
                    build_docx(target,preview["title"],preview["subtitle"],[("Caso",cid),("Plantilla",tpl["template_id"]),("Revisión aprobada",str(tpl["revision_id"])),("Hash",tpl["content_hash"][:24]+"…")],preview["sections"])
                    existing=con.execute("SELECT * FROM documents WHERE case_id=? AND kind=?",(cid,content["kind"])).fetchone()
                    did=existing["id"] if existing else "DOC-"+uuid.uuid4().hex[:8].upper();version=f"factory-{tpl['revision_id']}"
                    if existing:
                        con.execute("UPDATE documents SET name=?,mime_type=?,file_path=?,updated_at=?,version=?,status=? WHERE id=?",(filename,"application/vnd.openxmlformats-officedocument.wordprocessingml.document",str(target),t,version,"Aprobado por fábrica",did))
                    else:
                        con.execute("INSERT INTO documents(id,case_id,product_code,kind,name,mime_type,file_path,content,created_at,updated_at,version,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(did,cid,case["product_code"],content["kind"],filename,"application/vnd.openxmlformats-officedocument.wordprocessingml.document",str(target),None,t,t,version,"Aprobado por fábrica"))
                    con.execute("INSERT INTO document_versions(document_id,version,created_at,note,file_path) VALUES(?,?,?,?,?)",(did,version,t,f"Generado desde {tpl['template_id']} revisión {tpl['revision_id']} con aprobación dual.",str(target)))
                    created.append({"id":did,"kind":content["kind"],"name":filename,"version":version,"template_id":tpl["template_id"]})
                con.execute("UPDATE cases SET updated_at=? WHERE id=?",(t,cid));con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)",(cid,"factory",f"Se generaron {len(created)} documentos desde plantillas con aprobación dual.",t));core.audit(con,user["id"],"case",cid,"factory_generate",created)
                delivery=DELIVERY.summary(con,cid);con.commit();con.close()
                return self.send_json({"ok":True,"documents":created,"document_delivery":delivery},201)
            if path.startswith("/api/cases/") and "/release-control/" in path:
                cid = path.split("/")[3]
                if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                action = path.rsplit("/", 1)[-1]
                con = core.db()
                try:
                    if action == "start":
                        if user["role"] not in ("specialist", "admin"): raise PermissionError("Sin permisos para iniciar el ciclo.")
                        result = RELEASE_V217.ensure_cycle(con, cid, user["id"], user["role"])
                    elif action == "legal":
                        result = RELEASE_V217.legal_decision(con, cid, data.get("decision"), user["id"], user["role"], data.get("comment", ""))
                    elif action == "qa":
                        result = RELEASE_V217.qa_decision(con, cid, data.get("decision"), user["id"], user["role"], data.get("comment", ""))
                    elif action == "release":
                        result = RELEASE_V217.release(con, cid, user["id"], user["role"], data.get("comment", ""))
                    elif action == "compare":
                        if user["role"] not in ("specialist", "admin"): raise PermissionError("Sin permisos para comparar versiones.")
                        package = RELEASE_V217.detail(con, cid).get("package")
                        if not package: raise ValueError("No existe paquete consolidado para comparar.")
                        result = WORKSPACE.compare(con, package["id"], str(data.get("from_ref")), str(data.get("to_ref")), user["id"])
                    else:
                        con.close(); return self.send_json({"error": "Acción de liberación no encontrada."}, 404)
                    core.audit(con, user["id"], "extensive_review", cid, action, {"cycle": (result.get("cycle") or {}).get("id") if isinstance(result, dict) else None})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except ValueError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 409)
                except Exception:
                    con.close(); raise
                con.close(); return self.send_json(result, 201 if action in ("start", "release") else 200)
            if path.startswith("/api/cases/") and path.endswith("/assign"):
                if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos para asignar."}, 403)
                cid = path.split("/")[-2]
                if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                specialist = data.get("specialist_id")
                if user["role"] == "specialist": specialist = user["id"]
                con = core.db(); valid = con.execute("SELECT id FROM users WHERE id=? AND role='specialist' AND active=1", (specialist,)).fetchone()
                if not valid: con.close(); return self.send_json({"error": "Especialista no válido."}, 400)
                t = core.now()
                con.execute("UPDATE cases SET specialist_id=?,review_status=?,status=?,updated_at=? WHERE id=?", (specialist, "Asignado", "En revisión", t, cid))
                con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (cid, "assignment", f"Caso asignado a {specialist}.", t))
                core.audit(con, user["id"], "case", cid, "assign", {"specialist_id": specialist})
                con.commit(); con.close(); return self.send_json({"ok": True})
            if path.startswith("/api/cases/") and path.endswith("/review"):
                if user["role"] not in ("specialist", "admin"): return self.send_json({"error": "Sin permisos para revisar."}, 403)
                cid = path.split("/")[-2]
                if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                action = data.get("action"); comment = data.get("comment", "")
                specialist = user["id"] if user["role"] == "specialist" else data.get("specialist_id", "USR-COMM")
                status_map = {"approve": ("Aprobado", "Completado"), "request_info": ("Información requerida", "Pendiente de información"), "reject": ("Rechazado", "Requiere ajuste")}
                if action not in status_map: return self.send_json({"error": "Acción de revisión inválida."}, 400)
                con_guard = core.db()
                guard_case = con_guard.execute("SELECT product_code FROM cases WHERE id=?", (cid,)).fetchone()
                guard_package = con_guard.execute("SELECT 1 FROM documents WHERE case_id=? AND kind='consolidated_package'", (cid,)).fetchone()
                con_guard.close()
                if action == "approve" and guard_case and guard_case["product_code"] in ("CO-EM-003","CO-AR-001","CO-LA-002","CO-EM-004") and guard_package:
                    return self.send_json({"error": "Los paquetes extensos requieren aprobación jurídica, QA independiente y liberación controlada en el flujo v2.17."}, 409)
                review_status, status = status_map[action]
                rid = "REV-" + uuid.uuid4().hex[:8].upper(); t = core.now(); con = core.db()
                con.execute("INSERT INTO reviews VALUES(?,?,?,?,?,?)", (rid, cid, specialist, action, comment, t))
                con.execute("UPDATE cases SET review_status=?,status=?,specialist_id=?,updated_at=? WHERE id=?", (review_status, status, specialist, t, cid))
                if action == "approve":
                    con.execute("UPDATE documents SET status='Aprobado',updated_at=? WHERE case_id=? AND kind!='audit'", (t, cid))
                    con.execute("UPDATE case_tasks SET status='Completada',updated_at=? WHERE case_id=? AND label IN ('Asignar y obtener revisión profesional','Aprobar versión documental para uso')", (t, cid))
                elif action == "request_info":
                    con.execute("UPDATE case_tasks SET status='Pendiente',updated_at=? WHERE case_id=? AND label='Cargar y clasificar soportes'", (t, cid))
                con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (cid, "review", f"Revisión: {review_status}. {comment}", t))
                core.audit(con, user["id"], "case", cid, action, comment)
                con.commit(); con.close(); return self.send_json({"ok": True, "review_status": review_status, "status": status})
            if path.startswith("/api/tasks/") and path.endswith("/toggle"):
                tid = path.split("/")[-2]
                con = core.db(); row = con.execute("SELECT * FROM case_tasks WHERE id=?", (tid,)).fetchone()
                if not row or not can_access_case(user, row["case_id"]):
                    con.close(); return self.send_json({"error": "Tarea no encontrada o sin acceso."}, 404)
                if user["role"] != "admin" and row["owner_role"] not in (user["role"], "system"):
                    con.close(); return self.send_json({"error": "La tarea corresponde a otro rol."}, 403)
                new_status = "Completada" if row["status"] != "Completada" else "Pendiente"; t = core.now()
                con.execute("UPDATE case_tasks SET status=?,updated_at=? WHERE id=?", (new_status, t, tid))
                con.execute("INSERT INTO activity(case_id,kind,text,created_at) VALUES(?,?,?,?)", (row["case_id"], "task", f"Tarea “{row['label']}” marcada como {new_status}.", t))
                core.audit(con, user["id"], "task", tid, "toggle", {"status": new_status})
                con.commit(); con.close(); return self.send_json({"ok": True, "status": new_status})
            if path.startswith("/api/cases/") and path.endswith("/messages"):
                cid = path.split("/")[-2]
                if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                con = core.db()
                try:
                    result = WORKFLOW.post_message(con, cid, user, data.get("body", ""), data.get("visibility", "shared"), data.get("message_type", "message"))
                    core.audit(con, user["id"], "case_message", result["id"], "create", {"case_id": cid, "visibility": result["visibility"]})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except Exception:
                    con.close(); raise
                con.close(); return self.send_json(result, 201)
            if path.startswith("/api/cases/") and path.endswith("/tasks"):
                cid = path.split("/")[-2]
                if not can_access_case(user, cid): return self.send_json({"error": "Caso no encontrado o sin acceso."}, 404)
                con = core.db()
                try:
                    result = WORKFLOW.create_task(con, cid, user, data)
                    core.audit(con, user["id"], "task", result["id"], "create", {"case_id": cid, "owner_role": result["owner_role"]})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except Exception:
                    con.close(); raise
                con.close(); return self.send_json(result, 201)
            if path.startswith("/api/documents/") and path.endswith("/comments"):
                did = path.split("/")[-2]
                document = document_row(user, did)
                if not document: return self.send_json({"error": "Documento no encontrado o sin acceso."}, 404)
                con = core.db()
                try:
                    result = WORKFLOW.add_document_comment(con, did, document["case_id"], user, data)
                    core.audit(con, user["id"], "document_comment", result["id"], "create", {"document_id": did, "visibility": result["visibility"]})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except Exception:
                    con.close(); raise
                con.close(); return self.send_json(result, 201)
            if path.startswith("/api/document-comments/") and path.endswith("/resolve"):
                comment_id = path.split("/")[-2]
                con = core.db()
                row = con.execute("SELECT case_id FROM document_comments WHERE id=?", (comment_id,)).fetchone()
                if not row or not can_access_case(user, row["case_id"]):
                    con.close(); return self.send_json({"error": "Comentario no encontrado o sin acceso."}, 404)
                try:
                    result = WORKFLOW.resolve_comment(con, comment_id, user, data.get("status", "Resuelto"))
                    core.audit(con, user["id"], "document_comment", comment_id, "resolve", {"status": result["status"]})
                    con.commit()
                except PermissionError as exc:
                    con.close(); return self.send_json({"error": str(exc)}, 403)
                except Exception:
                    con.close(); raise
                con.close(); return self.send_json(result)
            if path.startswith("/api/legal-studio/"):
                if user["role"] != "admin": return self.send_json({"error": "Solo administración puede editar contenido jurídico."}, 403)
                parts = path.strip("/").split("/")
                if len(parts) >= 4:
                    code, action = parts[2], parts[3]
                    con = core.db()
                    try:
                        if action == "validate":
                            result = core.STUDIO.validate(code, data.get("content") or {})
                            con.close(); return self.send_json(result, 200 if result["valid"] else 422)
                        if action == "save":
                            result = core.STUDIO.save(con, code, data.get("content") or {}, user["id"], data.get("note", "Actualización desde Studio Jurídico v2.0."), data.get("workflow_status", "Borrador interno"))
                            core.audit(con, user["id"], "legal_product", code, "save_content", {"revision_id": result["revision_id"], "workflow_status": result["workflow_status"], "hash": result["content_hash"]})
                            con.commit(); con.close(); return self.send_json(result, 201)
                        if action == "restore":
                            result = core.STUDIO.restore(con, code, int(data.get("revision_id")), user["id"])
                            core.audit(con, user["id"], "legal_product", code, "restore_content", {"revision_id": data.get("revision_id")})
                            con.commit(); con.close(); return self.send_json(result, 201)
                    except Exception:
                        con.close(); raise
            if path.startswith("/api/document-factory/"):
                parts=path.strip("/").split("/")
                if len(parts)>=4:
                    tid,action=parts[2],parts[3]
                    con=core.db()
                    try:
                        if action=="validate":
                            if user["role"]!="admin": con.close(); return self.send_json({"error":"Solo administración puede editar plantillas."},403)
                            result=FACTORY.validate(tid,data.get("content") or {}); con.close(); return self.send_json(result,200 if result["valid"] else 422)
                        if action=="save":
                            if user["role"]!="admin": con.close(); return self.send_json({"error":"Solo administración puede guardar revisiones."},403)
                            result=FACTORY.save(con,tid,data.get("content") or {},user["id"],data.get("note","Actualización desde Fábrica Documental v2.0."),data.get("workflow_status","Borrador interno"))
                            core.audit(con,user["id"],"canonical_template",tid,"save_revision",result);con.commit();con.close();return self.send_json(result,201)
                        if action=="approve":
                            result=FACTORY.approve(con,tid,user["id"],user["role"],data.get("approval_type"),data.get("decision"),data.get("comment",""))
                            core.audit(con,user["id"],"canonical_template",tid,"approval",{"type":data.get("approval_type"),"decision":data.get("decision"),"result":result});con.commit();con.close();return self.send_json(result)
                        if action=="preview":
                            result=FACTORY.preview(con,tid,data.get("answers") or {},data.get("revision_id"));con.close();return self.send_json(result or {"error":"Plantilla no encontrada"},200 if result else 404)
                    except PermissionError as exc:
                        con.close();return self.send_json({"error":str(exc)},403)
                    except Exception:
                        con.close();raise
            if path.startswith("/api/canonical-cotejo/"):
                if user["role"] not in ("specialist", "admin"): return self.send_json({"error":"Sin permisos."},403)
                parts=path.strip("/").split("/")
                if len(parts)>=4:
                    code,action=parts[2],parts[3]
                    con=core.db()
                    try:
                        if action=="stage":
                            if user["role"]!="admin": con.close(); return self.send_json({"error":"Solo administración puede cambiar la etapa."},403)
                            result=CANONICAL.update_stage(con,code,data.get("stage"),user["id"],data.get("note",""))
                            core.audit(con,user["id"],"canonical_package",code,"update_stage",result);con.commit();con.close();return self.send_json(result)
                        if action=="approval":
                            result=CANONICAL.update_approval(con,code,data.get("approval_type"),data.get("decision"),user["id"],user["role"],data.get("comment",""))
                            core.audit(con,user["id"],"canonical_package",code,"approval",result);con.commit();con.close();return self.send_json(result)
                        if action=="mapping":
                            if user["role"]!="admin": con.close(); return self.send_json({"error":"Solo administración puede editar mapeos."},403)
                            result=CANONICAL.save_mapping(con,code,data.get("canonical_token"),data.get("canonical_label"),data.get("app_field"),data.get("template_variable"),data.get("status"),data.get("note"),user["id"])
                            core.audit(con,user["id"],"canonical_mapping",code,"save",data);con.commit();con.close();return self.send_json(result,201)
                        if action=="issue":
                            issue_id=int(data.get("issue_id")); result=CANONICAL.update_issue(con,issue_id,data.get("status"),user["id"],data.get("note",""))
                            core.audit(con,user["id"],"canonical_issue",str(issue_id),"update",result);con.commit();con.close();return self.send_json(result)
                    except PermissionError as exc:
                        con.close();return self.send_json({"error":str(exc)},403)
                    except Exception:
                        con.close();raise
            if path.startswith("/api/source-intake-records/") and path.endswith("/legal-decision"):
                if user["role"] != "specialist": return self.send_json({"error":"La decisión jurídica requiere especialista."},403)
                intake_id=path.split("/")[-2];con=core.db()
                result=INTAKE.legal_decision(con,intake_id,data.get("decision"),user["id"],user["role"],data.get("comment", ""))
                core.audit(con,user["id"],"canonical_intake",intake_id,"legal_decision",result);con.commit();con.close();return self.send_json(result)
            if path.startswith("/api/source-intake-records/") and path.endswith("/qa-decision"):
                if user["role"] != "admin": return self.send_json({"error":"La decisión de QA requiere administración."},403)
                intake_id=path.split("/")[-2];con=core.db()
                result=INTAKE.qa_decision(con,intake_id,data.get("decision"),user["id"],user["role"],data.get("comment", ""))
                if result.get("status") == "Importado y verificado":
                    record=INTAKE.record(con,intake_id)
                    if record: REVIEW.init_jobs(con,record["product_code"])
                core.audit(con,user["id"],"canonical_intake",intake_id,"qa_decision",result);con.commit();con.close();return self.send_json(result)

            if path == "/api/normative-updates":
                if user["role"] != "admin": return self.send_json({"error":"Solo administración puede registrar novedades normativas."},403)
                con=core.db()
                result=NORMATIVE.register_update(con,data.get("source_id"),data.get("title"),data.get("document_type"),data.get("source_url"),data.get("abstract"),data.get("severity"),data.get("product_codes") or [],user["id"],user["role"],data.get("identifier", ""),data.get("publication_date") or None,data.get("effective_date") or None,data.get("source_sha256") or None,data.get("relevance", "Potencial"))
                core.audit(con,user["id"],"normative_update",result["update"]["id"],"register",{"record_hash":result["update"]["record_hash"]}); con.commit(); con.close(); return self.send_json(result,201)
            if path == "/api/normative-monitor-checks":
                if user["role"] not in ("specialist","admin"): return self.send_json({"error":"Sin permisos."},403)
                con=core.db(); result=NORMATIVE.record_monitor_check(con,data.get("product_code"),data.get("source_id"),data.get("result"),data.get("notes", ""),user["id"],user["role"]); core.audit(con,user["id"],"normative_monitor",data.get("product_code"),"check",result); con.commit(); con.close(); return self.send_json(result,201)
            if path.startswith("/api/normative-impacts/"):
                if user["role"] != "admin": return self.send_json({"error":"La operación requiere administración."},403)
                parts=path.strip("/").split("/")
                if len(parts)>=4:
                    try: impact_id=int(parts[2])
                    except Exception: return self.send_json({"error":"Impacto inválido."},400)
                    action=parts[3]; con=core.db()
                    if action=="qa": result=NORMATIVE.qa_impact(con,impact_id,data.get("decision"),user["id"],user["role"],data.get("comment", ""))
                    elif action=="implement": result=NORMATIVE.mark_implemented(con,impact_id,data.get("evidence", ""),user["id"],user["role"])
                    else: con.close(); return self.send_json({"error":"Acción no encontrada."},404)
                    core.audit(con,user["id"],"normative_impact",str(impact_id),action,result.get("update",{})); con.commit(); con.close(); return self.send_json(result)
            if path.startswith("/api/normative-updates/"):
                if user["role"] not in ("specialist","admin"): return self.send_json({"error":"Sin permisos."},403)
                parts=path.strip("/").split("/")
                if len(parts)>=4:
                    update_id=parts[2]; action=parts[3]; con=core.db()
                    try:
                        if action=="verify": result=NORMATIVE.verify_reference(con,update_id,user["id"],user["role"],data.get("comment", ""),data.get("source_sha256") or None)
                        elif action=="claim": result=NORMATIVE.claim(con,update_id,user["id"],user["role"],data.get("expected_version"))
                        elif action=="impact": result=NORMATIVE.submit_impact(con,update_id,data.get("product_code"),data.get("component_type"),data.get("component_id"),data.get("action"),data.get("rationale", ""),data.get("proposed_change", ""),data.get("legal_effect", ""),user["id"],user["role"],data.get("expected_version"))
                        elif action=="finalize": result=NORMATIVE.finalize(con,update_id,user["id"],user["role"],data.get("comment", ""))
                        elif action=="discard": result=NORMATIVE.discard(con,update_id,user["id"],user["role"],data.get("reason", ""))
                        else: con.close(); return self.send_json({"error":"Acción no encontrada."},404)
                        core.audit(con,user["id"],"normative_update",update_id,action,result.get("update",{})); con.commit(); con.close(); return self.send_json(result)
                    except PermissionError as exc:
                        con.close(); return self.send_json({"error":str(exc)},403)
                    except Exception:
                        con.close(); raise
            if path == "/api/review-batches":
                if user["role"] != "admin": return self.send_json({"error":"Solo administración puede crear lotes."},403)
                con=core.db()
                result=BATCHES.create_batch(con,data.get("name"),data.get("product_code"),user["id"],user["role"],data.get("template_id") or None,data.get("assigned_to") or None,data.get("priority",2),data.get("due_at") or None,data.get("notes", ""),data.get("statuses") or None,data.get("max_jobs",20))
                core.audit(con,user["id"],"review_batch",result["batch"]["id"],"create",{"jobs":result["metrics"]["jobs"],"manifest_hash":result["batch"]["manifest_hash"]}); con.commit(); con.close(); return self.send_json(result,201)
            if path.startswith("/api/review-batches/"):
                if user["role"] not in ("specialist","admin"): return self.send_json({"error":"Sin permisos."},403)
                parts=path.strip("/").split("/")
                if len(parts)>=4:
                    batch_id=parts[2]; action=parts[3]; con=core.db()
                    try:
                        if action=="claim": result=BATCHES.claim(con,batch_id,user["id"],user["role"],data.get("expected_version"))
                        elif action=="refresh": result=BATCHES.refresh(con,batch_id,user["id"],user["role"])
                        elif action=="close": result=BATCHES.close(con,batch_id,user["id"],user["role"],data.get("comment", ""))
                        elif action=="cancel": result=BATCHES.cancel(con,batch_id,user["id"],user["role"],data.get("comment", ""))
                        else: con.close(); return self.send_json({"error":"Acción no encontrada."},404)
                        core.audit(con,user["id"],"review_batch",batch_id,action,{"status":result["batch"]["status"],"metrics":result["metrics"]}); con.commit(); con.close(); return self.send_json(result)
                    except PermissionError as exc:
                        con.close(); return self.send_json({"error":str(exc)},403)
                    except Exception:
                        con.close(); raise
            if path == "/api/assisted-review/refresh":
                if user["role"] != "admin": return self.send_json({"error":"Solo administración puede reconstruir la cola."},403)
                con=core.db(); result=REVIEW.init_jobs(con,data.get("product_code") or None); core.audit(con,user["id"],"assisted_review","queue","refresh",result); con.commit(); con.close(); return self.send_json(result)
            if path.startswith("/api/assisted-review/jobs/"):
                if user["role"] not in ("specialist","admin"): return self.send_json({"error":"Sin permisos."},403)
                parts=path.strip("/").split("/")
                if len(parts)>=5:
                    try: job_id=int(parts[3])
                    except Exception: return self.send_json({"error":"Trabajo inválido."},400)
                    action=parts[4]; con=core.db()
                    try:
                        if action=="claim":
                            result=REVIEW.claim(con,job_id,user["id"],user["role"],data.get("expected_version"))
                        elif action=="assign":
                            result=REVIEW.assign(con,job_id,data.get("assignee"),user["id"],user["role"],data.get("priority"),data.get("expected_version"))
                        elif action=="proposal":
                            result=REVIEW.submit_proposal(con,job_id,data.get("fragment_id"),data.get("link_type"),user["id"],user["role"],data.get("legal_rationale", ""),data.get("effect_assessment", ""),data.get("exception_reason", ""),data.get("expected_version"))
                        elif action=="qa":
                            result=REVIEW.qa_decision(con,job_id,data.get("decision"),user["id"],user["role"],data.get("comment", ""),data.get("expected_version"))
                        else:
                            con.close(); return self.send_json({"error":"Acción no encontrada."},404)
                        core.audit(con,user["id"],"assisted_review_job",str(job_id),action,result); con.commit(); con.close(); return self.send_json(result)
                    except PermissionError as exc:
                        con.close(); return self.send_json({"error":str(exc)},403)
                    except Exception:
                        con.close(); raise
            if path.startswith("/api/traceability/"):
                if user["role"] not in ("specialist", "admin"): return self.send_json({"error":"Sin permisos."},403)
                parts=path.strip("/").split("/")
                if len(parts)>=4:
                    code,action=parts[2],parts[3]
                    con=core.db()
                    try:
                        if action=="suggest":
                            result=TRACEABILITY.suggest(con,code,data.get("template_id"),data.get("block_id"),user["id"],int(data.get("limit",5)))
                            core.audit(con,user["id"],"traceability",code,"suggest",{"template_id":data.get("template_id"),"block_id":data.get("block_id")});con.commit();con.close();return self.send_json(result)
                        if action=="link":
                            if user["role"]!="admin": con.close(); return self.send_json({"error":"Solo administración puede crear vínculos de trazabilidad."},403)
                            result=TRACEABILITY.save_link(con,code,data.get("template_id"),data.get("block_id"),data.get("fragment_id"),data.get("link_type"),user["id"],data.get("legal_note",""),data.get("exception_reason",""))
                            core.audit(con,user["id"],"traceability_link",str(result["link_id"]),"create",result);con.commit();con.close();return self.send_json(result,201)
                        if action=="approve-link":
                            result=TRACEABILITY.approve_link(con,int(data.get("link_id")),data.get("approval_type"),data.get("decision"),user["id"],user["role"],data.get("comment",""))
                            core.audit(con,user["id"],"traceability_link",str(data.get("link_id")),"approval",result);con.commit();con.close();return self.send_json(result)
                        if action=="publication":
                            result=TRACEABILITY.publication_decision(con,code,data.get("decision"),user["id"],user["role"],data.get("comment",""))
                            core.audit(con,user["id"],"publication_gate",code,"decision",result);con.commit();con.close();return self.send_json(result)
                    except PermissionError as exc:
                        con.close();return self.send_json({"error":str(exc)},403)
                    except Exception:
                        con.close();raise
            if path.startswith("/api/security/sessions/") and path.endswith("/revoke"):
                if user["role"] != "admin": return self.send_json({"error": "Sin permisos."}, 403)
                sid = path.split("/")[-2]
                con = core.db(); con.execute("UPDATE sessions SET revoked=1 WHERE id=?", (sid,)); security_event(con, user["id"], "session_revoke", "success", self.ip, self.agent, {"session_id": sid}); con.commit(); con.close()
                return self.send_json({"ok": True})
            if path == "/api/reset-demo":
                if user["role"] != "admin": return self.send_json({"error": "Sin permisos."}, 403)
                init_db(reset=True)
                return self.send_json_cookie({"ok": True, "reauthenticate": True}, clear_session_cookie(secure=SETTINGS.secure_cookies), 200)
            return self.send_json({"error": "Ruta no encontrada"}, 404)
        except UnicodeDecodeError:
            return self.send_json({"error": "El archivo de texto no está codificado en UTF-8."}, 400)
        except ValueError as exc:
            return self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            traceback.print_exc()
            return self.send_json({"error": "Error interno de la aplicación", "code": "internal_error"}, 500)
