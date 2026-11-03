# R5a uncertainty versus exclusion — 2026-10-31

Explicitly unknown financial outcomes now survive the early rejection path and
return `uncertain` / `review`. All eight reviewed uncertain cases that were wrongly
excluded are repaired. This does not establish completion or improve the current
43/54 missed completed events in the authored diagnostic set. R5 remains active.

## Cause and repair

Two original messages already matched the unknown-outcome grammar, but a low
financial-candidate fallback discarded them before the uncertainty decision. Other
misses used unrecognized wording about unconfirmed settlement, unavailable posting
results, execution/pending alternatives, or missing governing context.

Shared grammar 1.0.11 and paired Python/TypeScript code now:

- Collect explicit unknown-outcome/context evidence before negative, balance-only
  and financial-candidate early returns. Such evidence must reach review.
- Filter explicit conversation, instructional examples, evidence inquiries,
  authorization-code requests and promotions before collecting that evidence.
  Unknown wording inside those frames does not establish a financial notification.
- Require financial context for a generic “its final outcome is unresolved” claim.
  Remove noncash point-posting phrases when assessing that context; points-only
  notices stay excluded, while separate cash/unknown evidence is retained.
- Recognize Arabic imperative numeric-code entry in the detailed request guard.
  This repairs an additional purchase-code case and protects the uncertainty path.

The evidence scan reduces flags in one pass. TypeScript reuses a compiled noncash
expression; it does not create a new expression for every clause. Actual Hermes
latency remains unmeasured. No learned weights, amount/direction resolution,
ownership policy or public result schema changed. The optional tester was rebuilt.

Only the detailed path changes. Legacy Python/TypeScript/browser outputs were
measured and remain unchanged, including their known limitations; this is not a
claim that the legacy classifier correctly rejects all new code-request examples.

## Measured exposed development results

New `completion_uncertainty_cases_v1.json`: 36 bilingual base cases, three digit
scripts and two sender/contact variants = 216 checks. They cover unknown versus
explicitly denied/pending/declined/completed outcomes, context ambiguity, questions,
OTPs, instructional quotes, nonfinancial results and points versus cash.

All asserted fields agree in Python, TypeScript and built browser:
**150/216 before → 216/216 after**. Earlier frame contrasts remain **168/168**;
the strict core remains **52/52 asserted cases** (51/51 status assertions).
These variants are not independent examples or evidence of general accuracy.

| Original exposed cohort | Status before this repair | After |
| --- | ---: | ---: |
| Authored 74 | 22/74 | 24/74 |
| Scope development | 11/32 | 17/32 |
| Manual cases | 13/24 | 14/24 |
| Old validation, probes, quotes, core | Unchanged | Unchanged |

Exactly nine original detailed results changed: the eight reviewed uncertain
cases now receive review, and the Arabic purchase-code request now excludes.
No previously correct asserted field regressed. All eight known wrong-certainty
errors in those two affected cohorts disappear. Zero false includes or false
completions are observed on the original 238 entries, while many missed events
and unnecessary reviews remain. Do not pool cohorts into an accuracy figure.

All 622 measured inputs retain full detailed three-runtime parity. All 70 ownership
requests, all legacy outputs and all 23 model artifacts are unchanged. No new
research-model inference, training, reserved scoring, app work or push occurred.

## Evidence and continuation

- `tools/evaluation/core_boundary_check.py`: reusable before/after checker; takes
  versioned fixture paths and report tag instead of copying a producer per repair.
- `tests/python/test_completion_uncertainty.py`: three tests cover the 216 variants,
  all eight source-reviewed failures without learned fallback, and explicit
  negative contexts without learned fallback.
- `data/reports/behavior/core_money_r5a_uncertainty_comparison.json`: immutable
  before/after cohort and language counts, complete changed results, source hashes
  and private snapshot hashes.
- `.local-backups/core_money_r5a_uncertainty/{before,after}.json`: full inputs/results.
- `data/reports/behavior/core_money_v1_after_r5a_uncertainty.json`: fresh strict core.

Verification completed: **297 Python tests, 11 TypeScript suites and all 226
frozen compatibility cases pass**. Strict core passes 52/52 in each runtime,
with zero parity mismatches. The targeted tests also confirm all eight repaired
unknowns reach review without the learned financial-candidate fallback.

The original review, queue, labels, frame fixture and historical reports are intact.
There are **25 remaining priority-one status errors**, all expected nontransactions:
explicit failures/denials, approval requests, conversation, administrative notices
and unrecognized instructional wording. Next, add versioned contrasts for those
boundaries before the 68 completed-status misses and one remaining-field mismatch.
No new fitting experiment is justified yet; R6 remains gated.
