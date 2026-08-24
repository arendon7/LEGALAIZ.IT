# M35.1 — Certification scope

Certification candidate starts at branch head after `M35_1_FULFILLMENT_CONTEXT_OFFER.md`.

The gate must prove, on the same SHA:

- 49/49 triage product/fact combinations covered exactly once;
- every reusable target exists in the canonical 473-question interviews;
- no `FULFILLMENT_ONLY` or direct-identifier prefill;
- unconfirmed AI facts cannot prefill;
- user edits win over any later prefill;
- offer prices come from existing canonical product prices;
- `prepare` creates no order, payment or case;
- authenticated HTTP recommend → claim → prepare journey passes;
- M34.2, M34.3, M34.4, M35.0 remain green;
- M33.1 smoke remains green;
- DOCX visual regression remains green.

A green CI certifies technical integration only. It does not authorize real payments, production pricing, autonomous legal conclusions or release of documents without the existing human review/QA controls.
