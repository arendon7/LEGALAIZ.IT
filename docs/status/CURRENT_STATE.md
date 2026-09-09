# LegalAIZ.it — Current State

Last reviewed: 2026-09-09
Milestone: **M39.2 — Canonical Release Convergence & Repository Cleanup**

## Canonical interpretation

`main` remains the formal protected release branch. The most advanced development candidate is the stacked M38/M39 lineage and must be converged deliberately; no blind mass merge is allowed.

Verified ancestry against `main` on 2026-09-09:
- `main`: `ea0d8171db040e090e7fc9a1efdb04dc652670d8`;
- advanced M39.2 line: 879 commits ahead, 0 behind;
- merge base equals the current `main` head above.

Open stacked milestone chain:
`M38.0 #76 → M38.1 #78 → M38.2 #80 → M38.3 #82 → M38.4 #84 → M38.5 #86 → M38.6 #88 → M38.7 #90 → M38.8 #92 → M39.0 #94 → M39.1 #96 → M39.2 #98`.

No remote PR or branch was found for **M38.9, M38.10 or M38.11**. Work discussed or produced outside GitHub under those labels is therefore non-canonical until it is independently revalidated and reintroduced on the certified line.

## Verified advanced candidate

- M39.1 PR: #96.
- M39.1 certified head previously verified: `c1a34283f27a55f025da3c56db2666f92cfedce8`.
- M39.1 evidence: CI successful, including the core test gate and DOCX visual gate; the recorded smoke suite reached 1,336 passing tests.
- M39.2 PR: #98.
- M39.2 branch: `release/m39-2-canonical-convergence-cleanup`.
- M39.2 base: `release/m39-1-enterprise-multitenancy-hardening`.
- M39.2 exact-head certification: **pending after cleanup consolidation**.

## Why M39.2 does not auto-run CI

`.github/workflows/ci.yml` runs automatically only on `push` to `main` or `pull_request` targeting `main`; it also exposes `workflow_dispatch`. Because #98 targets the M39.1 branch, an automatic PR run is not expected. M39.2 must therefore be validated on its exact final SHA through a main-target validation path or equivalent explicit workflow execution before convergence.

## Product state to preserve

- 11 active legal products.
- Advanced intake and guided navigation.
- Structured fact extraction, confirmation and adaptive questions.
- Explainable recommendation, checkout/case creation and status surfaces.
- Document Factory with controlled immutable revisions, comparison, DOCX generation and dual Legal/QA approval.
- Studio Jurídico and professional reviewer workflows.
- RBAC, tenant isolation, audit controls and enterprise hardening.
- Regression, smoke and visual document gates.

No cleanup may reduce these capabilities or weaken source traceability, permissions, audit, document governance or legal/QA approval.

## M39.2 scope and exit gates

M39.2 includes canonical documentation, evidence-backed repository hygiene, convergence planning and exact-head certification. It does **not** include AI feature development, architecture rewrites, mass deletion by version number or promotion to commercial production.

M39.2 closes only when:
1. the repository cleanup inventory is evidence-backed;
2. no destructive deletion remains unverified;
3. the M39.2 diff is minimal and coherent;
4. an exact final SHA is identified;
5. core CI and applicable DOCX visual QA are green on that candidate;
6. the M38/M39 convergence route to `main` is explicit;
7. local-only M38.9–M38.11 work is not falsely represented as canonical.

## M40 entry guardrails

M40.0 starts only from a certified M39.2/converged baseline. AI must be incremental and governed. No provider/model may:
- promote unconfirmed facts to confirmed facts;
- bypass RBAC or tenant isolation;
- silently overwrite an approved document revision;
- approve Legal or QA;
- expose sensitive payloads through logs/observability;
- autonomously activate payments or production operations.

## Immediate roadmap

1. Close M39.2 cleanup consolidation and exact-head certification.
2. Converge the stacked M38/M39 line to the formal canonical branch without blind mass merge.
3. Close superseded stacked draft PRs only after successful convergence, preserving Git history.
4. Start M40.0 — central AI governance and provider gateway.
5. Continue M40.1–M40.9 according to `docs/roadmap/AI_COPILOT_ROADMAP.md`.

## Deferred IDE / local-agent integration

Visual Studio Code, Antigravity or other local/IDE agents are deliberately deferred until the M40 gateway, permission model and audit contracts are stable. Future robots must consume governed AI/tool contracts, execute controlled fixtures/benchmarks and preserve GitHub/CI as the certification source of truth; they must not connect directly to secrets, databases or privileged production paths.

## Commercial release rule

Do not describe LegalAIZ.it as commercially production-live until external payments, communications and operational production gates are explicitly certified with real evidence.
