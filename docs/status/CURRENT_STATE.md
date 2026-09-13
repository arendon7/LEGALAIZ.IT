# LegalAIZ.it — Current State

Last reviewed: 2026-09-13  
Milestone: **M40.0 — AI Governance & Provider Gateway**

## 1. Canonical baseline

`main` is the formal canonical branch.

Current certified baseline:
- `main`: `60aa4a1a596e6b1550cd863482f25f19bd9381c8`;
- M38/M39 canonical convergence: PR #99;
- labor-source freshness hotfix: PR #100;
- post-merge canonical CI: workflow `Validación LegalAIZ.it`, run #793, **success**;
- smoke suite: **1,336 tests passed** on the converged baseline before M40 changes;
- inventory gate: **11 products / 473 questions / 273 rules**;
- `visual-docx`: **success**;
- `graphify-context`: **success** on the `main` push.

M38.0–M39.2 stacked PRs were closed as superseded after convergence. Their Git history remains in `main`.

No canonical remote PR or branch exists for **M38.9, M38.10 or M38.11**. Work previously discussed outside the canonical repository under those labels remains non-canonical unless independently revalidated and reintroduced.

## 2. M39.2 closure

M39.2 is closed. Its cleanup outcome was intentionally conservative:
- redundant governance notes were consolidated;
- common tracked debris was audited and not found;
- historical/versioned runtime, tests, templates and tools were preserved when they still serve compatibility, QA, traceability or release controls;
- no mass deletion by filename/version was performed;
- the advanced M38/M39 line was converged to `main` through an explicit certified merge.

The evidence-backed cleanup policy remains in `docs/status/REPOSITORY_CLEANUP_INVENTORY.md`.

## 3. Legal freshness gate — labor parameters 2026

The first post-convergence `main` run correctly exposed an expired M33.4 legal-freshness window for the status of Decreto 1469 de 2025. The gate failed closed instead of silently reusing stale status.

After fresh official revalidation on 2026-09-13, PR #100:
- preserved SMLMV 2026 at COP 1,750,905;
- preserved transport aid 2026 at COP 249,095, subject to its factual/legal requirements;
- recorded the current procedural status of Decreto 1469 de 2025 as operative pending a merits decision after revocation of the provisional suspension;
- recorded `wage_status_verified_on = 2026-09-13`;
- renewed the special 30-day review boundary to `wage_status_review_due_on = 2026-10-13`;
- preserved fail-closed behavior after that date.

**Mandatory next review:** the wage-decree procedural status must be revalidated again no later than **2026-10-13**. Do not extend or remove this time bomb without fresh official evidence.

## 4. Product state to preserve

- 11 active legal products.
- Advanced intake and guided navigation.
- Structured fact extraction, explicit confirmation/dispute and adaptive questions.
- Explainable recommendation, checkout/case creation and status surfaces.
- Document Factory with controlled immutable revisions, comparison, DOCX generation and dual Legal/QA approval.
- Studio Jurídico and professional reviewer workflows.
- RBAC, tenant isolation, audit controls and enterprise hardening.
- Regression, HTTP smoke and visual document gates.

No M40 work may reduce these capabilities or weaken source traceability, permissions, audit, document governance or human approval.

## 5. M40.0 active workstream

Active branch:
`feature/m40-0-ai-governance-provider-gateway`

M40.0 adds AI as a governed layer over the certified deterministic stack. The reference architecture is:

`AI Gateway → Policy Engine → Context Builder → Provider → Structured Output → Validator → Audit`

The first implementation slice is library-only and is designed to:
- version AI policy explicitly;
- separate public-preauth and tenant-scoped capabilities;
- derive tenant access from the existing M39.1 `EnterpriseContext` rather than trusting a claimed organization id;
- allowlist context by capability and reject secret-bearing keys;
- provide a provider-neutral contract;
- validate every structured provider action fail-closed;
- force AI-proposed facts to remain `AI_INFERRED / UNCONFIRMED`;
- preserve M34.2 fact extraction through a compatibility adapter;
- record hashes, provider/model metadata, action types and source ids without persisting raw input/output in the audit record;
- forbid AI confirmation, Legal approval, QA approval, document release, approved-revision overwrite, tenant mutation and payment execution.

This M40.0 slice is **not certified until its own PR and CI gates pass**.

## 6. M40.0 non-goals for the current slice

The current slice does not:
- expose a new public HTTP endpoint;
- call an external LLM/model provider;
- store API keys or model credentials;
- mutate cases or approved documents;
- create autonomous agents;
- perform legal research/RAG yet;
- approve Legal or QA;
- release documents;
- execute payments or external communications;
- authorize real legal/commercial production.

## 7. M40 no-bypass invariants

No provider, model, copilot, agent or IDE integration may:
- promote an AI-inferred or document-extracted fact to a confirmed fact without an explicit confirmation event;
- treat disputed/superseded facts as certain;
- invent legal-success probabilities as factual outcomes;
- bypass RBAC or tenant isolation;
- read private case/document context from a public-preauth scope;
- silently overwrite an approved revision;
- approve Legal or QA;
- execute real payments, communications or production operations autonomously;
- expose secrets, recovery codes, raw legal narratives or sensitive fact values through observability/audit.

The detailed sequence remains in `docs/roadmap/AI_COPILOT_ROADMAP.md`.

## 8. Immediate execution order

1. Complete M40.0 policy/gateway/context/provider/validator/audit foundation.
2. Run M40-specific adversarial tests plus the full regression suite.
3. Run HTTP/inventory gates and DOCX visual QA even though this slice is library-only.
4. Merge M40.0 only after exact-head CI is green.
5. Require a green post-merge `main` push including `graphify-context`.
6. Continue to M40.1 intake copilot by routing the existing M34.2 provider contract through the governed gateway, without changing fact-confirmation semantics.

## 9. Deferred IDE / local-agent integration

Visual Studio Code, Antigravity or other IDE/local agents remain deferred until the M40 gateway, provider, policy and audit contracts are stable. Future robots must consume governed contracts and controlled fixtures/benchmarks; they must not connect directly to secrets, databases or privileged production paths. GitHub/CI remains the certification source of truth.

## 10. Commercial release rule

Do not describe LegalAIZ.it as commercially production-live until external payments, communications and operational production gates are explicitly certified with real evidence. M40 AI functionality does not override those gates.
