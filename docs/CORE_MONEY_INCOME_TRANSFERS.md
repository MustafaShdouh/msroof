# R5a income arrivals and transfer execution — 2026-10-31

This repair recognizes confirmed income arrivals, completed transfers and explicit
own-account endpoints. It fixes 19 more completed-status misses, leaving 24 in the
original exposed diagnostics. Authored complete-event matches rise **23/48 → 33/48**.
R5 remains active; these are weak, exposed development counts, not final accuracy.

## Runtime behavior and architecture

Grammar 1.0.15 extends the existing shared `accountMovement` templates used by
`account_movement.py` / `AccountMovement.ts`. The same predicates supply completion
and owner-relative direction for salary received/added, available wages, account
receipts, wallet increases and cash-in. Explicit currency amounts and financial
objects constrain the new effects; generic file deletion or address addition
cannot supply cash movement evidence.

Completed transfer wording now includes explicit English “is complete,” internal
account movement and Arabic executed/completed transfer forms. A confirmed cash
amount removed/deducted/taken from the owner's account is a debit. These shared
account-effect forms also repair an earlier cash-payout and fee receipt without
needing institution-specific rules.

Ownership stays separate from completion:

- Another person explicitly named by relationship wording can count as P2P.
- Explicitly owned source and destination accounts can exclude, including current/
  savings modifiers and Arabic “المملوك لك” / “الخاص بك.” The word “internal,”
  two masks or a person's name alone do not establish own accounts.
- “External transfer” is no longer accepted as proof of another person. Both
  Arabic and English receipts retain review when ownership is unspecified.
- Unknown direction or ownership, and missing amounts, still block inclusion.

Matching nonexecution, future, request, question, personal, quoted and unresolved
outcome guards were added with the new verbs. No caller, API, learned weights,
ownership-confirmation binding, category model or app integration changed. The
optional tester was rebuilt from canonical sources.

## Received-amount role repair

In “استلم حسابك 17 JOD,” the identifier masker previously treated the number
after “حسابك” as an account ID. A shared received-amount anchor now protects that
explicit currency amount from identifier masking. Real masked IDs, references,
dates and balances retain their exclusions and original source spans.

This is **not primary selection**: the received candidate remains an ordinary
currency amount. If another unresolved monetary mention competes with it, the
amount remains unresolved. Tests compare raw Arabic/Unicode spans in Python and
TypeScript, distinguish a genuine `*1234` identifier and preserve multiple-amount
review. No arithmetic or new currency-default policy was introduced.

## Exposed development results

The new fixture has 46 bilingual base cases and 276 digit/sender/contact variants:
**78/276 before → 276/276 after**, with complete Python/TypeScript/browser equality.
It includes known-person, unknown-owner and own-account transfers, missing amounts,
ordinary administrative actions and negative/context contrasts. Additional tests
cover external-bank ambiguity and received-amount source roles. Variants are not
independent examples.

All earlier 168/216/300/216/252 variant packs remain correct. Strict core remains
52/52 asserted cases (51 status assertions). All 37 reviewed safety expectations
remain correct. Across 1,666 entries: full detailed parity, zero expected-field
regressions, unchanged measured legacy outputs and model bytes. All 70 ownership
requests retain their full outputs; new explicit endpoint cases are covered
separately in the new pack. No frozen labels or historical review overrides changed.

| Original exposed cohort | Status before | After | Completion misses remaining |
| --- | ---: | ---: | ---: |
| Manual | 20/24 | 21/24 | 3 |
| Context probes | 15/24 | 19/24 | 5 |
| Scope development | 28/32 | 30/32 | 2 |
| Authored 74 | 48/74 | 60/74 | 14 |

Old validation, quote controls and core status counts are unchanged. Exactly 19
original statuses improve. Three other original outputs change: a previously
completed own-account movement now excludes correctly, a completed cash-in gets
incoming direction, and an already-excluded Arabic code request gains a denial
reason. No original assertion regresses.

Authored Arabic status rises **21/37 → 26/37**, English **27/37 → 34/37**. Complete
eligible cases rise **23/48 → 33/48**, with all misses/reviews in the denominator.
Newly completed salary-transfer record 047 still has unknown ownership from the
generic transfer word; the original refund direction (030) and transfer-fee
relationship (040) also remain wrong. Those field errors must be resolved explicitly,
not hidden by completion improvements. Never pool related cohorts into accuracy.

## Evidence and continuation

- Fixture: `tests/fixtures/completion_income_transfers_v1.json`.
- Four safeguards: `tests/python/test_completion_income_transfers.py`.
- Immutable comparison: `data/reports/behavior/core_money_r5a_income_transfers_comparison.json`.
- Strict core: `core_money_v1_after_r5a_income_transfers.json` in behavior reports.
- Private full before/after: `.local-backups/core_money_r5a_income_transfers/`.
- Producer: existing `tools/evaluation/core_boundary_check.py`, using all six
  versioned completion fixtures.

Final verification passes **311 Python tests, 11 TypeScript suites and all 226
frozen compatibility cases**. Strict core passes 52/52 in every runtime with zero
parity mismatches. No historical expectation revisions were needed.

No fitting, new research inference, reserved scoring, deployment or push occurred.
No measured Hermes-performance claim follows from these checks.

Next: collection, settlement and remaining ledger/cash wording, then the three
known direction/relationship gaps and missing-currency quantities. Keep the new
ownership-ambiguity and received-amount safeguards. R6 remains gated on residual
coverage, supported independent evidence and explicit acceptance criteria.
