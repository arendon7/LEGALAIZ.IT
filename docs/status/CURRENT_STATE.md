# LegalAIZ.it — Current State

Last reviewed: 2026-09-09
Milestone: **M39.2 — Canonical Release Convergence & Repository Cleanup**

## 1. Canonical interpretation

`main` remains the formal published/canonical branch. The most advanced development candidate is the stacked M38/M39 lineage and must be converged deliberately; no blind mass merge is allowed.

Verified ancestry against `main` on 2026-09-09:
- `main`: `ea0d8171db040e090e7fc9a1efdb04dc652670d8`;
- advanced M39.2 line at the audited pre-consolidation point: 879 commits ahead, 0 behind;
- merge base equals the `main` head above.

Verified stacked milestone chain:
`M38.0 #76 → M38.1 #78 → M38.2 #80 → M38.3 #82 → M38.4 #84 → M38.5 #86 → M38.6 #88 → M38.7 #90 → M38.8 #92 → M39.0 #94 → M39.1 #96 → M39.2 #98`.

No remote PR or branch was found for **M38.9, M38.10 or M38.11**. Work discussed or produced outside GitHub under those labels is non-canonical until independently revalidated and reintroduced on the certified line.

## 2. Verified advanced candidate

- M39.1 PR: #96.
- M39.1 certified head previously verified: `c1a34283f27a55f025da3c56db2666f92cfedce8`.
- M39.1 evidence: successful CI, including the core test gate and DOCX visual gate; the recorded smoke suite reached 1,336 passing tests.
- M39.2 PR: #98, currently draft while certification is pending.
- M39.2 branch: `release/m39-2-canonical-convergence-cleanup`.
- M39.2 base branch: `release/m39-1-enterprise-tenancy`.
- M39.2 base SHA: `c1a34283f27a55f025da3c56db2666f92cfedce8`.
- Audited pre-consolidation M39.2 SHA: `32239dd1ad1aefd03a893768205cf46ffaea50e9`.
- Exact-head certification of the post-consolidation SHA: **pending CI + visual DOCX gate**.

## 3. Workflow state

`.github/workflows/ci.yml` has three entry modes:
- `push` to `main`;
- `pull_request` targeting `main`;
- `workflow_dispatch`.

Its principal jobs include syntax/compile validation, the Python test suite, inventory/integrity gates, frontend/demo validation, integrated HTTP smoke coverage and a separate `visual-docx` job that generates, converts, rasterizes and audits the document portfolio.

`.github/workflows/pages.yml` publishes the static public preview after successful `Validación LegalAIZ.it` on `main`, and also supports manual dispatch. M39.2 must not be treated as certified merely because M39.1 passed; the final M39.2 SHA requires its own run. If direct manual dispatch is unavailable from the active automation surface, a clearly labelled temporary PR to `main` may be used only as a CI anchor and must not be merged as a shortcut.

## 4. Repository hygiene result

The exact tracked tree of the audited M39.2 SHA was searched for common debris. No tracked `.DS_Store`, `__pycache__`, `.pyc`, `.orig`, `.rej`, `.zip` or `node_modules` entries were found.

`.gitignore` already blocks the principal local/generated categories, including Python caches, local environments, `.env`, secrets/certificates, runtime state, generated outputs, logs/databases, dependency/build directories, ZIP/backups/temp files, IDE metadata and operating-system artefacts.

Consequently, M39.2 does **not** authorize broad deletion of versioned runtime, tests, templates, data, sources, migrations or tools. Historical/versioned naming is not evidence of obsolescence. The evidence-backed policy and candidates are maintained in `docs/status/REPOSITORY_CLEANUP_INVENTORY.md`.

## 5. Product state to preserve

- 11 active legal products.
- Advanced intake and guided navigation.
- Structured fact extraction, confirmation and adaptive questions.
- Explainable recommendation, checkout/case creation and status surfaces.
- Document Factory with controlled immutable revisions, comparison, DOCX generation and dual Legal/QA approval.
- Studio Jurídico and professional reviewer workflows.
- RBAC, tenant isolation, audit controls and enterprise hardening.
- Regression, smoke and visual document gates.

No cleanup may reduce these capabilities or weaken source traceability, permissions, audit, document governance or Legal/QA approval.

## 6. Scope / non-goals of M39.2

M39.2 includes:
- canonical-state documentation;
- evidence-backed repository hygiene;
- consolidation of redundant governance notes;
- branch/PR convergence planning;
- certification on an exact final SHA.

M39.2 does not include:
- architecture rewrites;
- M40 AI functionality or live LLM calls;
- redesign of contracts already certified merely for cleanup;
- replacement of dual approval;
- mass deletion by version number;
- activation of real payments or communications;
- promotion to commercial production.

## 7. M39.2 exit gates

M39.2 closes only when:
1. the cleanup inventory is evidence-backed;
2. all retirements in the M39.2 diff are documented and non-functional or independently dependency-proven;
3. the diff against M39.1 is minimal and coherent;
4. an exact final SHA is fixed;
5. core CI, HTTP smoke and applicable integrity gates are green on that SHA;
6. DOCX visual QA is green on that SHA;
7. the M38/M39 convergence route to `main` is explicit;
8. local-only M38.9–M38.11 work is not represented as canonical.

## 8. M40 entry guardrails

M40.0 starts only from a certified M39.2/converged baseline. No AI provider/model/agent may:
- promote unconfirmed facts to confirmed facts;
- bypass RBAC or tenant isolation;
- silently overwrite an approved document revision;
- approve Legal or QA;
- expose sensitive payloads through logs/observability;
- autonomously activate payments, communications or production operations.

The detailed sequence is maintained in `docs/roadmap/AI_COPILOT_ROADMAP.md`.

## 9. Immediate execution order

1. Consolidate and remove redundant M39.2 governance files.
2. Fix the final M39.2 SHA.
3. Run exact-head CI and DOCX visual QA.
4. Review the final diff against M39.1.
5. Converge the certified M38/M39 line to `main` through an explicit integration strategy.
6. Close superseded stacked draft PRs only after successful convergence, preserving Git history.
7. Start M40.0 from the certified/converged base.

## 10. Deferred IDE / local-agent integration

Visual Studio Code, Antigravity or other local/IDE agents are deliberately deferred until the M40 gateway, permission model and audit contracts are stable. Future robots must consume governed AI/tool contracts, execute controlled fixtures/benchmarks and preserve GitHub/CI as the certification source of truth. They must not connect directly to secrets, databases or privileged production paths.

## 11. Commercial release rule

Do not describe LegalAIZ.it as commercially production-live until external payments, communications and operational production gates are explicitly certified with real evidence.
