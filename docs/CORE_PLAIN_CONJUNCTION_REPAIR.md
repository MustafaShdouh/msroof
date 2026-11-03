# Conflicting posted amounts and own-account scope — 2026-11-03

The54measured failures in the ordinary-conjunction review are repaired. All180required-review variants now return review with no selected amount; all102inherited controls pass. The72equal-value/same-direction observations remain unscored and their full outputs are unchanged. Python, TypeScript and the rebuilt tester agree. These are related exposed development checks, not independent accuracy.

## Bounded repair

Structural grammar **1.0.20** adds `conjoinedMovementCandidateBoundary`. Ordinary and/و is only a candidate boundary for a safety check inside already-completed clauses. Original context, completion, direction and ownership analysis still use the original text. A conjunction by itself never establishes another transaction.

Both candidate fragments must independently pass the existing completion predicate and expose exactly one positive canonical posted value. Values come from the existing candidate collector, including its balance/date/identifier masks and guarded account/primary roles. Local account/primary evidence takes precedence over original purchase amounts inside that same fragment; this preserves FX purchase/account-charge descriptions. Standalone totals are supporting information. Equal posted values do not establish conflict, including an omitted second currency; source defaults cannot prove a separate unit/event. No sum, exchange-rate inference or merchant/bank exception is added.

When two fragments establish incompatible values, a selected global total/account charge cannot resolve the whole message. The amount is cleared and the single-event assessment becomes uncertain before a transfer relationship could trigger exclusion. Transfer eligibility also receives this guard when amount is already missing, so a later ownership confirmation cannot turn mixed evidence into an own-account exclusion. Existing non-transfer completion-only review with no selected amount remains unchanged, preserving historical completed/review conventions. The uncertainty decision is made from body evidence BEFORE ownership overrides; confirmations cannot supply completion or event selection.

`money_candidates.py` / `MoneyCandidates.ts` share the exact standalone-total predicate with the existing multi-clause guard and expose `movement_values` / `movementValues`. The detailed assessors contain paired `conjoined_movement_conflict` / `conjoinedMovementConflict` checks. Candidate collection is skipped for fragments unless at least two pass the existing completion predicate; already-unresolved non-transfer review also avoids redundant work. No latency or Hermes claim follows.

Output schema/reason codes, learned preprocessing/export contracts, source-span semantics, model weights, legacy API and ownership wrapper schema remain unchanged. The live grammar-version assertion advances to1.0.20; historical1.0.5 replay and original assertions remain intact.

## Results and preservation

| Check | Before | After |
| --- | ---: | ---: |
| Required-review variants matching decision/null-amount assertions |126/180|180/180|
| Wrong includes in that group |12|0|
| Wrong excludes in that group |30|0|
| Incorrect retained amounts in that group |24|0|
| Inherited controls matching all their assertions |102/102|102/102|
| Unscored observation outputs preserved |72|72|

Exactly54full detailed results change, all in the scored required-review group. Failure counts overlap; nine authored bases expand to54variants, not54independent messages. The required-review labels assert trackingDecision/amount only, not every optional field or a universal completion status.

OriginalR5 snapshot2302entries, ordering snapshot1036, multi-clause snapshot664 and explicit-coordinator snapshot778 all retain their FULL detailed and legacy results. These4780preservation replays include repeated diagnostics. Seventy original ownership requests and23model artifacts are unchanged. All legacy outputs for the354review variants remain unchanged too.

Four new test safeguards pass:354full-parity comparisons with explicit unscored-output preservation;150hypothetical ownership requests (30required-review bases×absent/own/other/unknown/invalidcontext) preserving body completion and review/nullamount;24Arabic/English nonreceipt-frame contrasts; and typed posted-value checks for balances, references, account masks and local FX charge evidence. Hypothetical confirmations are not human ownership facts. Old review audit tests continue reading their frozen pre-repair evidence; they do not require the parser to retain bugs.

Full gate: **358 Python tests,14 TypeScript suites,226 frozen cases PASS**. Tester build byte-reproduces. No fitting, research-model/reserved/final inference, independent admission, source collection, app work, publication or push occurred.

## Evidence and reproduction

- `data/reports/behavior/core_plain_conjunction_repair_integrity_v1.json`: separate scored/unscored before/after metrics,54changes, old snapshot preservation and source/model hashes.
- Private `.local-backups/core_plain_conjunction_repair_v1/{before,after,regression}.json`: exact frozen pre/post/current-replay states. Before is byte-identical to the original review snapshot.
- Private `.local-backups/core_plain_conjunction_repair_v1/full_gate.log`: complete passing gate.
- Private `data/private/report_inputs/manifests/core_plain_conjunction_repair_{before,integrity,verification}_v1.json`: archived before/final source, models, tests, notes and reports.
- `tests/python/test_plain_conjunction_repair.py`: four current runtime safeguards. `test_plain_conjunction_review.py` still verifies frozen analysis and rejects invented truth for observation-only cases.

```powershell
python -X utf8 -m unittest tests.python.test_plain_conjunction_repair -q
```

Do not rerun the old review producer under the same immutable tag to replace its failure baseline. Its `records()` and `summarize()` functions may be reused with a NEW repair tag. Existing fixtures, annotations and reports were not relabelled or overwritten. Include these exposed descendants in future exposure audits.

## Next work and limits

Refresh the development-readiness summary with these completed repairs and give the owner a compact tester checklist for completion, amount/currency, direction and ownership. Distinguish observed finite conformance from independent accuracy; do not restart source collection or fitting. Equal-value restatements remain unscored; zero/signed movement eligibility, ingestion deduplication, independent evidence/acceptance thresholds and actual mobile-runtime measurements remain open. This is a bounded selection guard, not general event co-reference or sender authentication.
