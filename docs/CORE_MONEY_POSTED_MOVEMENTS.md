# R5a completed-event review and posted entries — 2026-10-31

The first completed-event repair recognizes explicit posted debit/credit entries,
including Arabic recorded deductions. It fixes 16 of the 68 original completed
status misses while preserving the reviewed safety boundaries. R5 remains active;
this is exposed development evidence, not an independent accuracy result.

## Reviewed source evidence

All 68 missed completed expectations were reviewed against their original source
texts: 43 Arabic and 25 English entries. Expectations are retained as assistant-weak
reviews, with raw source hashes and original cohort IDs. The separate review file
does not change labels, folds, training admission or reserved evaluation.

The misses span posted/settled entries, Arabic past-tense account movements,
income arrivals, transfer execution, refunds, cash dispensing and collection.
Some receipts assert completion but supply no numeric amount; some transfers leave
ownership unresolved. Completion can be established while recording still requires
review. The separately identified existing refund field error also remains pending.

`core_money_r5a_completed_review.json` records all 68 source-bound decisions,
review families and mismatches in other *annotated* fields. It does not invent
amount/direction truth for status-only diagnostics or certify bank authenticity.

## Runtime change

Shared grammar 1.0.13 defines explicit `postedDebit` / `postedCredit` evidence.
Examples include “a debit is now posted,” “posted as a credit,” and Arabic
“قيد خصم” / “سجل خصم.” The detailed completion and conditional guards reuse the
same evidence. Negated, future, conditional, quoted, personal and unknown-outcome
wording cannot obtain completed status from the newly recognized verb alone.

Direction uses those same posting roles when the posting has a bounded explicit
target on/to the owner's account, wallet, card or balance. An actual credit posting
takes precedence over a nominal earlier “payment” word. Both debit and credit
evidence, or an explicit direction denial, remain unresolved. Generic posting
without an owner target does not supply this direction override.

The paired-movement recognizer also treats an additional posting as independent
financial evidence; it cannot silently absorb it into an otherwise single paired
movement. Ownership confirmation remains separate and cannot invent amounts or
completion. Amount selection and public API fields are unchanged.

Testing found a real regression during implementation: the Arabic notice reporting
both debit and cancellation with an unresolved final outcome initially became
completed. It is repaired by recognizing that explicit Arabic final-outcome
uncertainty in financial context. The original expectation stayed unchanged, and
three fresh Arabic/English contrasts now protect the boundary.

## Measurement

The new fixture contains 36 bilingual base cases with three digit scripts and two
sender/contact variants: **78/216 → 216/216** asserted-field matches, with full
Python/TypeScript/browser equality. It covers postings, owner direction, missing
amounts, foreign currency, both posting effects, questions, denials, requests,
quotations, personal claims and noncash points. Counts of variants are not counts
of independent messages.

All previous 168 frame, 216 uncertainty and 300 nontransaction checks remain
correct. Strict core remains 52/52 asserted cases (51 status assertions). Across
1,138 entries there are no expected-field regressions and full detailed parity;
70 ownership requests, all measured legacy outputs and 23 model files are unchanged.

On the original exposed cohorts:

| Cohort | Status before | After | Completed misses remaining |
| --- | ---: | ---: | ---: |
| Manual | 16/24 | 18/24 | 6 |
| Context probes | 13/24 | 15/24 | 9 |
| Scope development | 26/32 | 28/32 | 4 |
| Authored 74 | 31/74 | 41/74 | 33 |

Old validation, quote controls and core counts are unchanged. Exactly 16 original
statuses improve, and one already-excluded negative gains a denial reason. All
37 reviewed nontransaction/uncertainty statuses still match. Zero false includes
or false completions are observed on the original cohort; no unseen-message
guarantee or pooled accuracy follows.

Authored eligible end-to-end correctness increases **8/48 → 16/48**, retaining
reviews and misses in the denominator. Arabic authored status rises 10/37 → 14/37;
English rises 21/37 → 27/37. Arabic is still weak. Two newly completed authored
cases retain downstream direction/relationship errors, alongside the earlier
refund field error. Recognition gains are not all complete-event gains.

## Evidence and continuation

- Source review: `data/reports/behavior/core_money_r5a_completed_review.json`.
- New fixture: `tests/fixtures/completion_posted_cases_v1.json`.
- Comparison: `core_money_r5a_posted_comparison.json` in behavior reports.
- Strict core: `core_money_v1_after_r5a_posted.json` in behavior reports.
- Private before/after: `.local-backups/core_money_r5a_posted/`.
- Four safeguards: `tests/python/test_completion_posted.py`, including full-result
  parity, unresolved-outcome regressions, original review bindings and behavior
  without candidate scores.

Verification passes **304 Python tests, 11 TypeScript suites and all 226 frozen
compatibility cases**. Strict core passes 52/52 in all three runtimes, with zero
parity mismatches. Earlier historical source-bound revisions remain in force;
no new historical expectation changes were needed in this step.

No new fit, learned research inference, reserved scoring, publication or app work
occurred. The optional tester was rebuilt. Actual Hermes timing remains unmeasured.

Next: extend source-backed Arabic account-movement evidence, starting with the
remaining passive/past-tense debit and credit forms; preserve explicit negation,
questions and uncertainty. Recheck all current packs after each bounded repair.
There are 52 completed-status misses and three annotated remaining-field failures
among currently completed original entries. Missing amounts must stay unresolved;
new fitting is not justified by this result alone. R6 remains gated.
