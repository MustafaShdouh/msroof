# R5a Arabic account movements — 2026-10-31

The next bounded repair recognizes Arabic past/passive cash effects tied to an
explicitly owned account. It fixes nine additional completed-transaction misses,
reducing the original 52 remaining misses to 43. All nine obtain correct direction
and recording decisions on their existing annotated expectations.

## Shared architecture

`src/python/account_movement.py` and `src/typescript/AccountMovement.ts` compile
the same `accountMovement` templates from grammar 1.0.14. Both reuse the existing
monetary number and currency grammar, including Arabic/Eastern Arabic digits,
three-decimal amounts and supported foreign currencies. The templates require an
explicit monetary object, or the reference “المبلغ,” tied to the owner's account,
wallet, card or balance. An address added to a website profile does not qualify.

The detailed assessor uses these effects as completion evidence; the direction
policy uses the same predicates for owner-relative debit/credit. No second amount
parser or separate direction vocabulary was introduced. Templates compile once,
and runtime predicates return booleans. Polarity and conversational scope remain
the assessor's responsibility, not the movement component's.

Examples include “خُصم … من حسابك,” “أُضيف … إلى حسابك,” “أُودع … في حسابك,”
and “أُعيد … إلى رصيد بطاقتك.” Money returned and explicitly added after an
earlier purchase resolves incoming despite the nominal purchase word. Existing
English owned-account debited/credited effects join the same direction evidence,
preserving review when both effects occur, including mixed Arabic/English text.

Matching guards cover explicit nonexecution, future actions, requests, questions,
personal claims and unknown confirmation. Point deductions remain noncash, and
independent cash evidence is retained. Missing numeric amounts still require
review. The current new templates do not by themselves resolve every bare quantity
without a currency; existing currency-default policy and amount selection are
unchanged. Recognition and extraction gaps must remain visible.

The optional tester was rebuilt. Public result fields, ownership confirmation,
flat model weights, legacy output behavior and category scope are unchanged.
No training, new research inference or reserved evaluation occurred.

## Measured development results

The new fixture contains 42 base cases: actual cash movements and missing-amount,
negative, future, request, question, conditional, example, personal, noncash,
profile, uncertainty and conflicting-effect controls. Three digit scripts and two
sender/contact variants yield **108/252 before → 252/252 after**, with full
Python/TypeScript/browser equality. These are exposed assistant-authored variants,
not independent messages or accuracy estimates.

Earlier frame 168/168, uncertainty 216/216, nontransaction 300/300 and posting
216/216 checks remain correct. Strict core stays 52/52 asserted cases, including
51 status assertions. Full detailed parity and no expected-field regressions hold
across 1,390 entries. All measured legacy outputs, 70 ownership requests and 23
model artifacts are unchanged. All 37 source-reviewed safety statuses still match.

Exactly nine original diagnostic outputs improve, with all other original full
outputs unchanged:

- Manual Arabic refund and foreign-currency purchase: 18/24 → 20/24 status matches.
- Seven authored Arabic movements: withdrawal, incoming transfer, two refunds,
  cashback, installment debit and salary credit. Status rises 41/74 → 48/74.
- Authored complete-event matches rise **16/48 → 23/48**, keeping misses/reviews
  in the denominator. Arabic status rises **14/37 → 21/37**; English stays 27/37.

Other cohorts are unchanged. Completion misses remaining: manual 4, probes 9,
scope 4 and authored 26 = 43 cohort entries. The three already-completed authored
field failures (cash-in direction, refund direction and fee/transfer relationship)
also remain. Do not treat completion agreement as complete-event accuracy.

## Compatibility and evidence

An existing pure balance question initially acquired a conversational reason from
the new Arabic question guard. The final rule preserves `balance_only` for an
actual balance inquiry while retaining `personal_conversation` for a personal
money claim that merely mentions a balance. A dedicated cross-runtime regression
check covers both, plus a question about a cash movement. Historical fixtures and
expectations remain unchanged; no new review overrides were needed in this step.

The earlier intermediate comparison is preserved. The authoritative final report
uses the exact same pre-repair snapshot bytes, not a freshly inferred baseline:

- `data/reports/behavior/core_money_r5a_account_movements_final_comparison.json`.
- `data/reports/behavior/core_money_v1_after_r5a_account_movements_final.json`.
- `.local-backups/core_money_r5a_account_movements_final/{before,after}.json`.
- `tests/fixtures/completion_account_movements_v1.json`.
- `tests/python/test_completion_account_movements.py` (three safeguards).

The generic checker now also binds account-movement, direction-policy and monetary
source hashes. Its previous exact source is archived by SHA under
`.local-backups/source_snapshots/`; older reports retain their original hashes.
The intermediate report is historical and superseded by the final report above.

Final verification passes **307 Python tests, 11 TypeScript suites and all 226
frozen compatibility cases**. Strict core passes 52/52 in every runtime with zero
parity mismatches. No new historical expectation overrides were needed.

Next: source-backed income arrival, transfer execution and collection/settlement
wording, with the current safety, owner-direction and amount controls retained.
Address missing-currency quantities and downstream field gaps explicitly, without
inventing values. R5 remains active, R6 gated and no new fitting experiment is
justified by these exposed conformance gains alone. Hermes timing is unmeasured.
