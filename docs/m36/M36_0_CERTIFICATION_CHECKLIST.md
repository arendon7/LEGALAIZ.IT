# M36.0 — Certification Checklist

M36.0 may be considered technically certified only when the exact head SHA satisfies all items below.

## Repository and stack

- [ ] Branch is based on the certified M35.3 SHA.
- [ ] PR is draft and stacked on `m35/case-activation-purchase-confirmation` after CI certification.
- [ ] PR diff contains only M36.0 files and the minimum runtime/CI wiring.

## Functional invariants

- [ ] M35.3 must return `ACTIVE` before M36.0 can proceed.
- [ ] M35.2 commerce link and order must match the activated case.
- [ ] Every non-audit activated document is a materialized DOCX.
- [ ] There is exactly one deterministic M32.5 desk per activated document.
- [ ] No unrelated case/document is bootstrapped.
- [ ] M32.5 approval chain is valid.
- [ ] M32.6 operations chain is valid.
- [ ] M24 moves only from `GENERADO` to `EN_REVISION_JURIDICA` or reconciles an already-entered review phase.
- [ ] Retry is idempotent and does not create another ledger, revision, operation event, desk or M24 transition.
- [ ] Activation/document drift fails closed.

## Governance invariants

- [ ] No automatic specialist assignment.
- [ ] No automatic QA assignment.
- [ ] No automatic legal approval.
- [ ] No automatic QA approval.
- [ ] No automatic release/delivery.
- [ ] Dual approval is preserved.
- [ ] M32.6 SLA is described only as an operational target, never as a statutory/legal deadline.

## Security and privacy

- [ ] POST requires authenticated admin + same-origin + CSRF.
- [ ] Client cannot activate M36.0.
- [ ] Reads are admin-only in M36.0.
- [ ] Rate limits exist for read and write paths.
- [ ] Public M36.0 responses omit owner id, activation/document hashes, receipt, payment intent, story and answers.
- [ ] Observability omits receipt/payment payload/legal narrative.
- [ ] CI admin password is generated ephemerally in the job and is not committed or printed.

## CI evidence

- [ ] `python -m compileall -q .` PASS.
- [ ] Full unit/integration suite PASS.
- [ ] M34.2 → M36.0 HTTP smokes PASS.
- [ ] M36.0 smoke proves RBAC, CSRF, exact document coverage, M24 review state, manual assignment boundary, dual approval and idempotency.
- [ ] 11 products / at least 473 questions preserved.
- [ ] M33.1 public-demo smoke PASS.
- [ ] visual-docx PASS and artifact digest recorded.

A green CI run is a technical certification only. It does not constitute approval of real prices, real payments, legal advice in a concrete matter, professional legal review, QA approval, production authorization, representation or delivery of a legal result.
