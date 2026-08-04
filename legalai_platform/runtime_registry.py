from __future__ import annotations

import os
import secrets

import core_v11 as core
from legalai_platform.release_metadata import (
    VERSION, BUILD_ID, RELEASE_ID, RELEASE_NAME, RELEASE_CHANNEL,
    PRODUCTION_AUTHORIZED, DOCUMENT_RELEASE_APPROVAL_MODEL,
)

from legalai_platform.approval_registry import ApprovalRegistry
from legalai_platform.release_candidate import ReleaseCandidateCenter
from legalai_platform.operational_security import RateLimiter, MalwareScanner, ExternalAttestationRegistry
from legalai_platform.observability import StructuredLogger
from legalai_platform.privacy_governance import PrivacyGovernance
from legalai_platform.product_quality import ProductQualityCenter
from legalai_platform.m24_candidate_registry import M24CandidateRegistry
from legalai_platform.m24_pilot_validation import M24PilotValidationCenter
from legalai_platform.m24_candidate_governance import M24CandidateGovernance
from legalai_platform.m24_full_validation import M24FullValidationCenter
from legalai_platform.m24_release_governance import M24ReleaseGovernance
from legalai_platform.m24_case_journey import M24CaseJourneyCenter
from legalai_platform.m24_client_intake import M24ClientIntakeCenter
from legalai_platform.m24_pilot_operations import M24PilotOperationsCenter
from legalai_platform.m24_professional_network import M24ProfessionalNetwork
from legalai_platform.m24_human_approval import M24HumanApprovalRegistry
from legalai_platform.m25_pilot_readiness import M25PilotReadinessCenter
from legalai_platform.m30_pilot_execution import M30PilotExecutionCenter
from legalai_platform.m30_participant_operations import M30ParticipantOperationsCenter
from legalai_platform.m30_pilot_governance import M30PilotGovernanceCenter
from legalai_platform.m30_pilot_simulation import M30PilotSimulationCenter
from legalai_platform.m30_live_evaluation import M30LivePilotEvaluationCenter
from legalai_platform.m31_preproduction import M31PreproductionCenter
from legalai_platform.m31_demo_reality import M31DemoRealityCenter
from legalai_platform.m31_case_demo import M31CaseDemoCenter
from legalai_platform.m26_gold_standard import GoldStandardCenter
from legalai_platform.commercial_experience import CommercialExperienceCenter

from factory_backend import DocumentFactory
from canonical_import_backend import CanonicalImportCenter
from traceability_backend import TraceabilityCenter
from source_intake_backend import SourceIntakeCenter
from assisted_review_backend import AssistedReviewWorkbench
from batch_review_backend import ReviewBatchCenter
from normative_update_backend import NormativeUpdateCenter
from infrastructure import InfrastructureCenter, load_settings, read_reference_bytes
from ux_backend import ExperienceCenter
from workflow_backend import WorkflowExperience
from document_workspace_backend import DocumentWorkspace
from public_portal_backend import PublicPortal
from self_service_backend import SelfServiceCenter
from anonymous_draft_backend import AnonymousDraftCenter
from payment_sandbox_backend import PaymentSandboxCenter
from document_delivery_backend import DocumentDeliveryCenter
from pdf_acceptance_backend import PdfAcceptanceCenter
from canonical_generation_backend import CanonicalGenerationCenter
from canonical_product_v28 import FirstCanonicalProductV28
from priority_wave_v29 import PriorityWaveV29
from canonical_activation_v210 import CanonicalActivationV210
from co_em_003_v213 import CoEm003MaturityV213
from co_em_003_v242 import CoEm003CanonicalV242
from co_em_003_v243 import CoEm003CanonicalV243
from co_em_003_document_factory_v243 import CoEm003DocumentFactoryV243
from co_em_003_governance_v243 import CoEm003GovernanceV243
from co_em_003_v244 import CoEm003CanonicalV244
from co_em_003_document_factory_v244 import CoEm003DocumentFactoryV244
from co_em_003_governance_v244 import CoEm003GovernanceV244
from co_em_003_validation_v244 import CoEm003ValidationV244
from co_em_004_v214 import CoEm004MaturityV214
from co_em_004_v245 import CoEm004CanonicalV245
from co_em_004_v246 import CoEm004CanonicalV246
from co_em_004_document_factory_v246 import CoEm004DocumentFactoryV246
from co_em_004_governance_v246 import CoEm004GovernanceV246
from co_em_004_v247 import CoEm004CanonicalV247
from co_em_004_document_factory_v247 import CoEm004DocumentFactoryV247
from co_em_004_governance_v247 import CoEm004GovernanceV247
from co_em_004_validation_v247 import CoEm004ValidationV247
from complete_models_backend_v215 import CompleteLegalModelsV215
from extensive_generation_v216 import ExtensiveGenerationV216
from extensive_review_v217 import ExtensiveReviewV217
from visual_qa_v218 import VisualQaV218
from adaptive_validation_v219 import AdaptiveValidationV219
from change_control_v220 import ChangeControlV220
from release_cycle_v221 import ReleaseCycleV221
from co_la_001_v222 import CoLa001MaturityV222
from co_la_001_v251 import CoLa001CanonicalV251
from co_la_001_v252 import CoLa001CanonicalV252
from co_la_001_document_factory_v252 import CoLa001DocumentFactoryV252
from co_la_001_governance_v252 import CoLa001GovernanceV252
from co_la_001_v253 import CoLa001CanonicalV253
from co_la_001_document_factory_v253 import CoLa001DocumentFactoryV253
from co_la_001_governance_v253 import CoLa001GovernanceV253
from co_la_001_validation_v253 import CoLa001ValidationV253
from co_tr_002_v254 import CoTr002CanonicalV254
from co_tr_002_api_v256 import CoTr002ApiV256
from co_tr_001_api_v259 import CoTr001ApiV259
from co_ar_001_v223 import CoAr001MaturityV223
from co_ar_001_v248 import CoAr001CanonicalV248
from co_ar_001_v249 import CoAr001CanonicalV249
from co_ar_001_document_factory_v249 import CoAr001DocumentFactoryV249
from co_ar_001_governance_v249 import CoAr001GovernanceV249
from co_ar_001_v250 import CoAr001CanonicalV250
from co_ar_001_document_factory_v250 import CoAr001DocumentFactoryV250
from co_ar_001_governance_v250 import CoAr001GovernanceV250
from co_ar_001_validation_v250 import CoAr001ValidationV250
from co_la_002_v224 import CoLa002MaturityV224
from co_la_002_v236 import CoLa002CanonicalV236
from co_la_002_document_factory_v239 import CoLa002DocumentFactoryV239
from co_la_002_governance_v240 import CoLa002GovernanceV240
from co_tr_002_v225 import CoTr002MaturityV225
from co_tr_001_v226 import CoTr001MaturityV226
from legal_approval_v227 import LegalApprovalV227
from internal_legal_approval_v228 import InternalLegalApprovalV228
from second_wave_legal_approval_v229 import SecondWaveLegalApprovalV229
from second_wave_internal_decision_v230 import SecondWaveInternalDecisionV230
from co_sa_001_v231 import CoSa001MaturityV231
from co_cd_001_v232 import CoCd001MaturityV232
from co_cd_003_v233 import CoCd003MaturityV233
from co_cd_004_v234 import CoCd004MaturityV234
from third_wave_internal_approval_v235 import ThirdWaveInternalApprovalV235

# Marcadores históricos conservados para trazabilidad de pruebas de regresión.
# BUILD_ID = "M31-5-CERTIFICACION-POSTGRES-RECUPERACION-2026-08-04"  # active release marker
# VERSION = "5.0.0"  # M31.1
# VERSION = "4.9.0"  # M30.5
M31_1_INTEGRATION_ID = "M31-1-BASE-PREPRODUCCION-5.0.0-2026-08-03"
M31_INTEGRATION_ID = RELEASE_ID
M31_2_INTEGRATION_ID = RELEASE_ID
M24_7_INTEGRATION_ID = "M24.7-GUIDED-RESPONSIVE-UX-AND-VISUAL-QA-ON-M21.1-2026-08-01"
M24_INTEGRATION_ID = "M24.10-HUMAN-RATIFICATION-AND-CONTROLLED-APPROVAL-ON-M21.1-2026-08-02"
M25_INTEGRATION_ID = "M26-1-PUBLIC-SITE-3.1.0-2026-08-02"
M26_INTEGRATION_ID = "M26-3-CATALOGO-GOLD-INTEGRAL-3.3.0-2026-08-02"
M27_INTEGRATION_ID = "M27-4-PROFUNDIZACION-INTEGRAL-11-DE-11-3.7.0-2026-08-02"
M28_INTEGRATION_ID = "M28-2-CALCULOS-JURIDICOS-Y-COHERENCIA-ECONOMICA-3.9.0-2026-08-03"
core.VERSION = VERSION
APPROVALS = ApprovalRegistry(core.ROOT)
PRODUCT_QUALITY = ProductQualityCenter(core.ROOT)
M24_CANDIDATES = M24CandidateRegistry(core.ROOT)
M24_PILOT = M24PilotValidationCenter(core.ROOT, M24_CANDIDATES)
M24_PILOT_GOVERNANCE = M24CandidateGovernance(core.ROOT, M24_CANDIDATES, M24_PILOT)
M24_FULL = M24FullValidationCenter(core.ROOT, M24_CANDIDATES)
M24_RELEASE_GOVERNANCE = M24ReleaseGovernance(core.ROOT, M24_CANDIDATES, M24_FULL)
M24_CASE_JOURNEY = M24CaseJourneyCenter(core.ROOT)
M24_CLIENT_INTAKE = M24ClientIntakeCenter(core.ROOT, core.PRODUCTS)
M24_PILOT_OPERATIONS = M24PilotOperationsCenter(core.ROOT, M24_RELEASE_GOVERNANCE, M24_CASE_JOURNEY)
M24_PROFESSIONAL_NETWORK = M24ProfessionalNetwork(core.ROOT)
M24_HUMAN_APPROVAL = M24HumanApprovalRegistry(core.ROOT, M24_CANDIDATES, M24_FULL)
M25_PILOT_READINESS = M25PilotReadinessCenter(core.ROOT, M24_CANDIDATES, M24_FULL, M24_RELEASE_GOVERNANCE, M24_PILOT_OPERATIONS, M24_HUMAN_APPROVAL)
M30_PILOT_CENTER = M30PilotExecutionCenter(core.ROOT, M25_PILOT_READINESS, M24_PILOT_OPERATIONS, core.audit)
M30_PARTICIPANTS = M30ParticipantOperationsCenter(core.ROOT, M24_PILOT_OPERATIONS, M30_PILOT_CENTER, core.audit)
M30_GOVERNANCE = M30PilotGovernanceCenter(core.ROOT, M24_PILOT_OPERATIONS, M30_PILOT_CENTER, M30_PARTICIPANTS, core.audit)
M30_SIMULATION = M30PilotSimulationCenter(core.ROOT, core.audit)
M30_LIVE_EVALUATION = M30LivePilotEvaluationCenter(core.ROOT, core.audit)
APPROVALS.apply_to_products(core.PRODUCTS)
# Studio incorpora los controles calculados de los productos maduros sin duplicar reglas declarativas.
core.STUDIO.scenario_risk_hook = lambda code, content, answers: (
    core.diagnose(code, answers, strict=False).get('risk') if code in {'CO-AR-001', 'CO-LA-001', 'CO-LA-002', 'CO-TR-002', 'CO-TR-001', 'CO-SA-001', 'CO-CD-001', 'CO-CD-003', 'CO-CD-004'} else None
)
HOST = "127.0.0.1"
PORT = 8765
DOCUMENT_TEMPLATES = core.load_json('document_templates.json', [])
CANONICAL_PACKAGES = core.load_json('canonical_packages.json', [])
FACTORY = DocumentFactory(DOCUMENT_TEMPLATES, core.PRODUCTS, core.INTERVIEWS, core.SOURCES, core.eval_conditions)
DEMO_REALITY_M31_7 = M31DemoRealityCenter(core.ROOT, core.RUNTIME, FACTORY, DOCUMENT_TEMPLATES, core.PRODUCTS, core.INTERVIEWS)
M31_CASE_DEMO = M31CaseDemoCenter(core.ROOT, core.RUNTIME, FACTORY, DOCUMENT_TEMPLATES, core.PRODUCTS, core.INTERVIEWS, DEMO_REALITY_M31_7, core.diagnose, core.audit, core.now)
CANONICAL = CanonicalImportCenter(CANONICAL_PACKAGES, core.PRODUCTS, DOCUMENT_TEMPLATES, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS)
TRACEABILITY = TraceabilityCenter(CANONICAL_PACKAGES, DOCUMENT_TEMPLATES, core.PRODUCTS)
SETTINGS = load_settings(core.ROOT)
# Las credenciales demo solo existen en local y se generan por proceso. En piloto/producción
# deben utilizarse cuentas reales de bootstrap y MFA obligatorio.
DEMO_PASSWORD = os.environ.get("LEGAL_DEMO_PASSWORD") or secrets.token_urlsafe(18)
INFRA = InfrastructureCenter(core.ROOT, SETTINGS)
RATE_LIMITER = RateLimiter()
MALWARE_SCANNER = MalwareScanner(SETTINGS.malware_scanner, SETTINGS.profile)
OBSERVABILITY = StructuredLogger(core.ROOT)
PRIVACY = PrivacyGovernance(core.ROOT, SETTINGS)
EXTERNAL_ATTESTATIONS = ExternalAttestationRegistry(core.ROOT)
M31_PREPRODUCTION = M31PreproductionCenter(core.ROOT, SETTINGS, INFRA, OBSERVABILITY, EXTERNAL_ATTESTATIONS, core.audit)
RELEASE_CANDIDATE = ReleaseCandidateCenter(core.ROOT, APPROVALS, SETTINGS, INFRA)
SOURCE_INTAKE_PLAN = core.load_json('source_intake_plan.json', [])
INTAKE = SourceIntakeCenter(SOURCE_INTAKE_PLAN, core.ROOT, CANONICAL, TRACEABILITY, object_store=INFRA.objects)
REVIEW = AssistedReviewWorkbench(TRACEABILITY, core.PRODUCTS, SOURCE_INTAKE_PLAN)
BATCHES = ReviewBatchCenter(REVIEW, TRACEABILITY, FACTORY, CANONICAL, INTAKE, core.PRODUCTS)
NORMATIVE_REGISTRY = core.load_json('normative_source_registry.json', {})
NORMATIVE = NormativeUpdateCenter(NORMATIVE_REGISTRY, core.PRODUCTS, core.INTERVIEWS, core.RULES, DOCUMENT_TEMPLATES, core.SOURCES)
UX = ExperienceCenter(core.ROOT, core.PRODUCTS)
WORKFLOW = WorkflowExperience(core.ROOT, core.PRODUCTS, UX.requirements)
WORKSPACE = DocumentWorkspace(core.ROOT, core.GENERATED)
PORTAL = PublicPortal(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, DOCUMENT_TEMPLATES)
GOLD_STANDARD = GoldStandardCenter(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, DOCUMENT_TEMPLATES)
COMMERCIAL_EXPERIENCE = CommercialExperienceCenter()
SELF_SERVICE = SelfServiceCenter(core.PRODUCTS, PORTAL)
ANON_DRAFTS = AnonymousDraftCenter(INFRA.crypto, core.PRODUCTS, SELF_SERVICE)
PAYMENTS = PaymentSandboxCenter(INFRA.secrets.key)
DELIVERY = DocumentDeliveryCenter(core.ROOT, DOCUMENT_TEMPLATES)
PDF_ACCEPTANCE = PdfAcceptanceCenter(core.ROOT, INFRA.secrets.key)
CANONICAL_GENERATION = CanonicalGenerationCenter(core.ROOT, FACTORY, TRACEABILITY, CANONICAL, NORMATIVE, core.PRODUCTS)
COEM003_V28 = FirstCanonicalProductV28(core.ROOT, FACTORY, DOCUMENT_TEMPLATES, core.INTERVIEWS, core.RULES)
PRIORITY_V29 = PriorityWaveV29(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SAST)
ACTIVATION_V210 = CanonicalActivationV210(core.ROOT, SOURCE_INTAKE_PLAN, INTAKE, CANONICAL_GENERATION, TRACEABILITY, REVIEW, core.PRODUCTS)
COEM003_V213 = CoEm003MaturityV213(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS)
COEM003_V242 = CoEm003CanonicalV242(core.ROOT)
COEM003_V243 = CoEm003CanonicalV243(core.ROOT)
COEM003_FACTORY_V243 = CoEm003DocumentFactoryV243(core.ROOT, COEM003_V243)
COEM003_GOVERNANCE_V243 = CoEm003GovernanceV243(core.ROOT, COEM003_FACTORY_V243)
COEM003_V244 = CoEm003CanonicalV244(core.ROOT)
COEM003_FACTORY_V244 = CoEm003DocumentFactoryV244(core.ROOT, COEM003_V244)
COEM003_GOVERNANCE_V244 = CoEm003GovernanceV244(core.ROOT, COEM003_FACTORY_V244)
COEM003_VALIDATION_V244 = CoEm003ValidationV244(core.ROOT, COEM003_V244)
COEM004_V214 = CoEm004MaturityV214(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS)
COEM004_V245 = CoEm004CanonicalV245(core.ROOT)
COEM004_V246 = CoEm004CanonicalV246(core.ROOT)
COEM004_FACTORY_V246 = CoEm004DocumentFactoryV246(core.ROOT, COEM004_V246)
COEM004_GOVERNANCE_V246 = CoEm004GovernanceV246(core.ROOT, COEM004_FACTORY_V246)
COEM004_V247 = CoEm004CanonicalV247(core.ROOT)
COEM004_FACTORY_V247 = CoEm004DocumentFactoryV247(core.ROOT, COEM004_V247)
COEM004_GOVERNANCE_V247 = CoEm004GovernanceV247(core.ROOT, COEM004_FACTORY_V247)
COEM004_VALIDATION_V247 = CoEm004ValidationV247(core.ROOT, COEM004_V247)
COMPLETE_MODELS_V215 = CompleteLegalModelsV215(core.ROOT)
EXTENSIVE_V216 = ExtensiveGenerationV216(core.ROOT)
RELEASE_V217 = ExtensiveReviewV217(core.ROOT, WORKSPACE)
VISUAL_QA_V218 = VisualQaV218(core.ROOT)
VALIDATION_V219 = AdaptiveValidationV219(core.ROOT)
CHANGE_CONTROL_V220 = ChangeControlV220(core.ROOT)
RELEASE_CYCLE_V221 = ReleaseCycleV221(core.ROOT, CHANGE_CONTROL_V220)
COLA001_V222 = CoLa001MaturityV222(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS, core.PARAMETERS)
COLA001_V251 = CoLa001CanonicalV251(core.ROOT)
COLA001_V252 = CoLa001CanonicalV252(core.ROOT)
COLA001_FACTORY_V252 = CoLa001DocumentFactoryV252(core.ROOT, COLA001_V252)
COLA001_GOVERNANCE_V252 = CoLa001GovernanceV252(core.ROOT, COLA001_FACTORY_V252)
COLA001_V253 = CoLa001CanonicalV253(core.ROOT)
COLA001_FACTORY_V253 = CoLa001DocumentFactoryV253(core.ROOT, COLA001_V253)
COLA001_GOVERNANCE_V253 = CoLa001GovernanceV253(core.ROOT, COLA001_FACTORY_V253)
COLA001_VALIDATION_V253 = CoLa001ValidationV253(core.ROOT, COLA001_V253)
COTR002_V254 = CoTr002CanonicalV254(core.ROOT)
COTR002_API_V256 = CoTr002ApiV256(core.ROOT)
COTR001_API_V259 = CoTr001ApiV259(core.ROOT)
COAR001_V223 = CoAr001MaturityV223(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS, core.PARAMETERS)
COAR001_V248 = CoAr001CanonicalV248(core.ROOT)
COAR001_V249 = CoAr001CanonicalV249(core.ROOT)
COAR001_FACTORY_V249 = CoAr001DocumentFactoryV249(core.ROOT, COAR001_V249)
COAR001_GOVERNANCE_V249 = CoAr001GovernanceV249(core.ROOT, COAR001_FACTORY_V249)
COAR001_V250 = CoAr001CanonicalV250(core.ROOT)
COAR001_FACTORY_V250 = CoAr001DocumentFactoryV250(core.ROOT, COAR001_V250)
COAR001_GOVERNANCE_V250 = CoAr001GovernanceV250(core.ROOT, COAR001_FACTORY_V250)
COAR001_VALIDATION_V250 = CoAr001ValidationV250(core.ROOT, COAR001_V250)
COLA002_V224 = CoLa002MaturityV224(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS, core.PARAMETERS)
COLA002_V236 = CoLa002CanonicalV236(core.ROOT)
COLA002_FACTORY_V239 = CoLa002DocumentFactoryV239(core.ROOT, COLA002_V236)
COLA002_GOVERNANCE_V240 = CoLa002GovernanceV240(core.ROOT, COLA002_FACTORY_V239)
COTR002_V225 = CoTr002MaturityV225(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS, core.PARAMETERS)
COTR001_V226 = CoTr001MaturityV226(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS, core.PARAMETERS, core.SAST)
LEGAL_APPROVAL_V227 = LegalApprovalV227(core.ROOT)
INTERNAL_APPROVAL_V228 = InternalLegalApprovalV228(core.ROOT)
SECOND_WAVE_APPROVAL_V229 = SecondWaveLegalApprovalV229(core.ROOT)
SECOND_WAVE_DECISION_V230 = SecondWaveInternalDecisionV230(core.ROOT)
COSA001_V231 = CoSa001MaturityV231(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS, core.PARAMETERS)
COCD001_V232 = CoCd001MaturityV232(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS, core.PARAMETERS)
COCD003_V233 = CoCd003MaturityV233(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS, core.PARAMETERS)
COCD004_V234 = CoCd004MaturityV234(core.ROOT, core.PRODUCTS, core.INTERVIEWS, core.RULES, core.SOURCES, core.SCENARIOS, core.PARAMETERS)
THIRD_WAVE_APPROVAL_V235 = ThirdWaveInternalApprovalV235(core.ROOT)

ALLOWED_UPLOADS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
}
