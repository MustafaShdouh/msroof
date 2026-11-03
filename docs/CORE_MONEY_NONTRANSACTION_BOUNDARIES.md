# R5a remaining nontransaction boundaries — 2026-10-31

All 25 remaining priority-one status errors in the original reviewed queue are
repaired. All 37 source-reviewed expectations now match: 29 nontransactions
exclude and eight explicitly uncertain cases remain under review. This completes
that finite safety queue, not R5 or general transaction recognition.

## Runtime change

Shared grammar 1.0.12 covers the reviewed general boundaries:

- Explicit denials such as “nothing was debited,” “no debit is posted,” payment
  not carried out/finished, and Arabic withdrawal/execution/deduction denials.
- Refused payments/transfers and unsuccessful cash dispensing, including Arabic
  wording that was not covered by the previous refusal patterns.
- Approval awaited/needed, direct completion questions, receipt/confirmation
  requests, and explicit family/conversation/request introductions.
- Personal payment claims, login-code notices, PIN changes and clearly framed
  examples or fabricated lesson notices.

Paired `personal_context` / `personalContext` predicates now supply the same
context decision to completion, uncertainty collection and exclusion reasons.
An identified personal claim can no longer also supply positive completion.
Administrative notices exclude only when they have no recognized cash completion;
PIN changes beside real cash movements do not erase those movements.

No institution/merchant lists or fixture-ID exceptions were added. Amount,
direction, ownership and public result contracts are intact. The optional tester
was rebuilt from canonical sources. No learning or new research inference ran;
legacy results and all 23 model artifacts remain unchanged on measured inputs.

## New and existing evidence

`completion_nontransaction_cases_v1.json` contains 50 new bilingual base cases.
Three digit scripts and two sender/contact variants yield 300 checks: **126/300
before → 300/300 after**, with full Python/TypeScript/browser equality. They include
real cash, merchant-name, PIN/login-plus-cash, conflicting debit/failure and unknown
outcome controls. These are exposed assistant-authored development examples,
not independent accuracy measurements or training admissions.

The previous 168 frame variants, 216 uncertainty variants and all 52 core asserted
cases remain correct. The core includes 51 status assertions; one partial case
has no status truth. The before/after checker measures all 922 entries and 70
ownership requests, with no expected-field regressions, full detailed parity,
unchanged legacy outputs and unchanged model bytes.

On the original 238 exposed diagnostic entries:

| Cohort | Status before this repair | After |
| --- | ---: | ---: |
| Old validation | 16/18 | 18/18 |
| Manual cases | 14/24 | 16/24 |
| Context probes | 8/24 | 13/24 |
| Scope development | 17/32 | 26/32 |
| Authored 74 | 24/74 | 31/74 |
| Quote controls and core | Unchanged | Unchanged |

Exactly 25 statuses improve. Two other already-excluded entries gain denial
reasons; all other original detailed results remain unchanged. Zero false includes
or false completions are observed there, while **68 completed-status misses** and
one remaining asserted-field mismatch remain in the original queue. Authored
completed misses stay 43/54 and eligible end-to-end correctness stays 8/48.
Do not pool cohorts into an accuracy number or infer deployment readiness.

## Historical comparison integrity

The broader runner exposed three additional intended changes outside the R5
cohort. The old tests required exact equality to pre-feature review decisions:
one paired personal-chat control and two sanitized completion-question/receipt
requests. The current policy correctly excludes all three.

Their original fixtures, frozen before assessments, historical reports and
`training/evaluation/paired.py` remain unchanged. Explicit new review fixtures bind
the original source hashes and complete previous/current results:

- `nontransaction_paired_review_v1.json`: paired chat, all three digit scripts.
- `nontransaction_context_reviews_v1.json`: the two sanitized question/request rows.

`tests/python/nontransaction_review.py` validates those bindings. It adds the
paired review through the evaluator's existing explicit-revision mechanism, keeping
all original field, runtime and ownership assertions. The no-context test applies
only the two exact source/baseline-bound revisions; all other comparisons remain
unchanged. A mutation safeguard rejects a different baseline. This is an explicit
current expectation change, not a claim of unchanged historical behavior.

## Reproduction and continuation

Comparison: `data/reports/behavior/core_money_r5a_nontransaction_comparison.json`.
Strict core: `core_money_v1_after_r5a_nontransaction.json` in the same directory.
Private full before/after: `.local-backups/core_money_r5a_nontransaction/`.
Producer: `tools/evaluation/core_boundary_check.py`, using all three versioned
completion fixtures. Tests: `tests/python/test_completion_nontransactions.py`.
Original review/queue/labels and prior reports remain intact.

Full verification passes **300 Python tests, 11 TypeScript suites and all 226
frozen compatibility cases**. Strict core is 52/52 in each runtime, zero parity
mismatches. The first broader run identified the three intended historical changes
above; after adding their explicit reviewed revisions, all original assertions
and the added safeguards pass.

Next: source-review the 68 completed-status misses by event and language, distinguish
missing completion evidence from amount/direction/ownership gaps, and define small
positive/negated/requested/quoted contrasts before each paired repair. Preserve
the now-passing nontransaction/uncertainty boundaries. No new fit is justified yet;
R5 remains active, R6 gated and reserved sets uninferred.
