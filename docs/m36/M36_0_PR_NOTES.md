# M36.0 — PR Notes

Parent milestone: M35.3 certified at `2e5e2138e3f5670964b122dd6e0c02145dfc5efa`.

M36.0 is intentionally an incremental bridge. It does not replace M32.5/M32.6, and it does not close the whole M36 roadmap.

CI procedure for this stacked PR:

1. open draft PR against `m35/case-activation-purchase-confirmation`;
2. temporarily retarget to `main` because the consolidated CI workflow triggers only for PRs based on `main`;
3. add a substantive validation commit after retargeting so GitHub emits a `synchronize` event;
4. certify only the exact head SHA that passes the full workflow;
5. record workflow/artifact evidence in the PR;
6. retarget the PR back to the M35.3 parent branch without changing the certified head SHA.
