# M36.1 — Certification Checklist

M36.1 may be technically certified only for the exact head SHA that satisfies every gate below.

## Stack and scope

- [ ] Branch descends from certified M36.0 SHA `e6f1976be9482a80d80efafcc4efaa170de292fb`.
- [ ] Final PR is draft and stacked on `m36/fulfillment-intake-bridge`.
- [ ] Final diff contains only the M36.1 delta plus minimum runtime/CI wiring.

## Assignment semantics

- [ ] Selection of specialist and QA is explicit and human/admin initiated.
- [ ] No matching or auto-assignment algorithm exists.
- [ ] Specialist is an active `specialist` and QA is an active `qa` or `admin` returned by M32.6.
- [ ] Specialist and QA must be distinct.
- [ ] Every desk of the M36.0 intake receives the same exact professional pair.
- [ ] Existing incompatible assignment blocks before overwrite.
- [ ] M24 remains in the professional review phase; assignment alone never records legal/QA approval.

## Recoverability and idempotency

- [ ] Failure while assigning a later desk leaves `PARTIAL` with completed desk checkpoints.
- [ ] Retry resumes only desks still missing assignment.
- [ ] Failure while evaluating M32.7 leaves `ASSIGNED` with notification checkpoints.
- [ ] Retry resumes only missing notification evaluations.
- [ ] `COMPLETE` retry is strictly read-only: no M32 event, M32.7 evaluation, timestamp or M36 audit mutation.
- [ ] A different later professional pair is a conflict, never a silent reassignment.
- [ ] A `COMPLETE` ledger with incomplete checkpoints fails closed.

## Governance

- [ ] `automatic_matching=false`.
- [ ] `automatic_legal_approval=false`.
- [ ] `automatic_qa_approval=false`.
- [ ] `automatic_release=false`.
- [ ] `dual_approval_preserved=true`.
- [ ] Assignment completion is explicitly distinct from review completion.
- [ ] Notification evaluation is explicitly distinct from message delivery.

## Security and privacy

- [ ] M36.1 reads/writes are admin-only.
- [ ] POST requires same-origin and CSRF.
- [ ] Rate limiting covers read and write paths.
- [ ] Observability excludes legal narrative, answers, receipt/payment payloads and M35 fingerprints.
- [ ] Client cannot enumerate the professional directory.

## Full CI gate

- [ ] compileall PASS.
- [ ] full unittest suite PASS.
- [ ] 11 products / at least 473 questions remain intact.
- [ ] HTTP smokes M34.2 → M36.1 PASS.
- [ ] Real M36.1 smoke proves same professional pair on every desk, `legal_pending`, M32.7 handoff, separation, CSRF and strict idempotency.
- [ ] M33.1 public demo smoke PASS.
- [ ] visual-docx PASS and artifact digest recorded.

A green run is technical evidence only. It is not a legal opinion, legal approval of a concrete document, QA approval, representation, real payment approval, production authorization or proof of delivery.
