# R5 residual assessment — 2026-10-31

Assessment complete; **R5 exit is not met**. The passing 52-case core pack does
not represent the breadth of language in earlier exposed diagnostics. Do not
advance to release readiness or describe the engine as broadly accurate.

`tools/evaluation/assess_core_money_residuals.py` freezes expected-field metadata
before current detailed-engine evaluation, then verifies full-result parity in
Python, TypeScript and the built browser. It evaluates 238 cohort entries / 235
distinct text inputs, including the 112 old diagnostic entries, 52 core cases
and 74 weak authored cases. No reserved rows are evaluated. No research model is
loaded for inference; learned comparisons reuse saved v2 status outputs only.

## Measured status agreement

| Exposed cohort | Current detailed engine | Frozen direct status | Frozen factorized |
| --- | ---: | ---: | ---: |
| Old validation | 16/18 | 17/18 | 17/18 |
| Manual cases | 13/24 | 23/24 | 20/24 |
| Context probes | 8/24 | 23/24 | 23/24 |
| Quote controls | 14/14 | 8/14 | 5/14 |
| Newer scope development | 9/32 | 27/32 | 23/32 |
| Authored 74 | 21/74 | Not newly scored | Not newly scored |

Core conformance remains 52/52 asserted-field matches, including 51/51 status
assertions: one core case asserts only review/amount, so it has no status truth.
The denominators above retain uncertain labels. Binary historical results with
uncertainty skipped must not be substituted into this table.

The current engine has zero false **includes** in this assessment. That does not
mean correct rejection: many nontransactions become review, and the engine
labels a rewards-points notice and a teaching example completed but does not
include them because other required fields are unresolved. Improving extraction
alone could remove those accidental barriers. Fix the frame/outcome mistakes
before treating better amount coverage as an end-to-end improvement.

There is no pooled accuracy: cohorts overlap in ancestry and three inputs repeat.
Labels are assistant-weak, synthetic or exposed, not independent real-world truth.
No observed false includes on these examples is a guarantee about unseen SMS.

## Where the failures occur

On the authored 74, 43 of 54 completed cases lose completion. Status agrees on
21/74; all asserted core fields agree on 20/74. Among 48 eligible completed
external cases with known amount/currency/direction, only eight match end to end.
Missing/uncertain output is counted as failure, not removed from this denominator.

Field agreement on the 70 rows with corresponding annotations: amount 58/70,
currency 53/70, currency-resolution 53/70, direction 38/70 and relationship 48/70.
These denominators include expected null/not-applicable values; they are not
positive-amount-only extraction rates or independent measurements of each stage.
Some field errors follow earlier false exclusion rather than an isolated parser
failure. Four rows have no amount/direction annotation and remain unscored there.

Arabic is particularly weak: authored status 5/37 versus English 16/37; manual
3/12 versus English 10/12; context probes 3/12 versus English 5/12. This broader
result supersedes any impression of general Arabic quality from the narrower
passing core/number-format fixtures.

Representative problems:

- Completion paraphrases such as Arabic “أُنجز سحب” / “أُضيف راتبك” and English
  “cash payout successful,” “collected by deducting,” or “booked as a final credit”
  fall outside or collide with the current surface grammar.
- Requests, teaching frames and descriptions of unknown outcomes lack adequate
  scope handling. On the eight existing unspecified-outcome diagnostics, current
  status agrees on 3/8; unresolved-context 1/2; conservative scope controls 4/4.
- Internal-account descriptions and fee-purpose wording can confuse relationship
  or direction. Adding a completion synonym does not resolve these fields.

These are observed failures, not proven causal attribution to a training
hyperparameter or a specific neural feature. Do not add a long synonym list
without reviewing its negated, requested, quoted and ambiguous counterparts.

## Structural versus learned behavior

Detailed completion currently comes from structural event rules. The retained
legacy financial-candidate fallback was called 30 times across the 238 entries;
it influences fallback nontransaction/review behavior, not the completed-event
predicate. Its direction score does not supply the detailed direction result.
The failed direct/factorized/auxiliary research heads are not active in this path.

Saved direct-status results suggest semantic modeling may help coverage, while
the current structural rules are stronger on quote controls. Neither observation
establishes that replacing the detailed engine or blending scores is safe.
The direct candidate already failed its research quality conditions. Raw scores
are uncalibrated; no threshold or routing search was performed here.

`core_money_r5_frozen_head_exposure.json` records exposure before any possible
future learned comparison: 72 authored cases and one quote control match frozen
training text under research normalization. All 52 core inputs and the remaining
diagnostic entries are text-disjoint but still exposed/related weak examples.
Authored-set gains from that model would largely measure in-sample behavior.
No new learned inference or training was run, and none is recommended yet.

## Decision and next bounded work

Keep R5 active and create a **completion/frame repair subtask**, using
`core_money_r5_repair_queue.json`. It is a source-hash-bound queue of mismatches,
not a new training set or a set of reviewed label corrections.

1. Review highest-priority nontransaction/uncertainty mismatches against source
   clauses. Preserve raw expected truth unless a traceable weak-label correction
   is needed. Give points/noncash notices, questions, quoted instructions and
   unknown outcomes explicit contrasts; do not let extracted numbers prove money.
2. Review completed-event misses by family, including Arabic morphology and
   English posted/settled paraphrases. Define asserted/negated/requested/quoted
   event evidence before expanding recognition rules.
3. Add the reviewed contrasts to a new versioned development pack. Retain current
   finite core/ownership/amount safeguards, and report misses/reviews as well as
   false includes. No silent reclassification or training admission.
4. Only then decide whether a bounded semantic model experiment has adequate
   task labels and an informative evaluation design. Existing evidence does not
   justify another architecture/epoch search, promotion or a fresh fitting budget.

This keeps the next task concrete without repeating failed model experiments.
R6 remains gated on residual coverage, independently supportable evidence and
explicit acceptance criteria. Zero/signed and duplicate-ingestion policies also
remain unresolved. Merchant/category/app work remains deferred.

## Evidence and checks

Reports under `data/reports/behavior/`:
`core_money_r5_cohort.json`, `core_money_r5_residuals.json`,
`core_money_r5_frozen_head_exposure.json`, `core_money_r5_repair_queue.json`.
The residual report includes per-language/family metrics, denominators,
reason slices, fallback calls, input hashes and per-record mismatches.

Three metric safeguards pass: abstentions count as misses, missing truth remains
unscored, and end-to-end metrics include all eligible cases. The assessment
reproduces byte for byte. No engine/model/label changes or reserved inference
occurred; the full runtime suite was last run at R4 (288 Python, 11 TypeScript
suites, 226 compatibility cases), not rerun for this offline measurement.
