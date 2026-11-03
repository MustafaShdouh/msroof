# R3 amount layer — 2026-10-31

Later extension: [guarded unmarked account amounts](CORE_MONEY_UNMARKED_AMOUNTS.md)
documents grammar1.0.17, shared lexical syntax/account-role spans and source-local
JOD defaults. The R3 measurements below preserve the original milestone evidence.

The detailed assessor now delegates money candidate collection and selection to
`src/python/money_candidates.py` and `src/typescript/MoneyCandidates.ts`.
Both consume the same evidence/numeric contracts. Existing input/result shapes
and legacy extraction APIs remain intact.

## Candidate evidence and selection

`collect_candidates` / `collectCandidates` accepts an EntityText source view and
the existing number parser. It returns currency-bearing and anchored monetary
candidates, explicit-primary evidence, masked working text, and exclusion records
for balances, dates and identifiers. Candidates contain value, currency when
explicit, role, exact raw numeric text and half-open source offsets. Offsets are
Unicode code points in both runtimes; JavaScript converts its native UTF-16
indices before exposing evidence. Original digit script and source text survive
normalization. The JS collector uses RegExp match indices; deployed-engine
support and timing remain part of later runtime readiness checks, not measured
Hermes guarantees.

Candidate roles describe evidence, not a guarantee that a number is the posted
amount. The resolver retains the old balance-first exclusions, currency/default
markers, ambiguous-number review, anchored-number handling and bounded legacy FX
fallback. Nonfinite and nonpositive candidate values are rejected. It does not
invent amounts by summing fields or interpreting arbitrary signs.

The structural extraction was verified **before** the new policy work: 511 inputs
with six complete outputs each (Python/TypeScript/browser, detailed and legacy)
were identical before and after. The snapshot includes the retained Python
legacy exception on malformed null input; preservation is not a claim that the
old API handles that input successfully. The detailed malformed-input contract
continues to pass. All 23 model artifacts and source fixtures stayed unchanged.

Private snapshots are `.local-backups/core_money_r3/{before,after,policy}.json`.
`tools/evaluation/snapshot_core_money.py` captures and checks them. The public
summary is `data/reports/behavior/core_money_r3_integrity.json`. Snapshot inputs
come only from existing development/compatibility fixtures and core digit
variants; no reserved inference occurs.

## Owner-confirmed primary amount policies

The owner confirmed on 2026-10-31:

- With purchase JOD 10, fee JOD 0.500 and **explicit total debited JOD 10.500**,
  select JOD 10.500. Do not calculate an unstated total or create an extra fee event.
- With original purchase USD 10 and **explicit account charge JOD 7.090**,
  select JOD 7.090. The choice comes from the account-charge role, not a preference
  for JOD or an inferred exchange rate.

These rules are recorded in `transaction_evidence.json` version 1.0.8. A single
explicit-primary mention matching a positive monetary candidate can resolve
multiple amounts. Competing primary mentions remain unresolved. Bare multiple
amounts without that evidence continue to require review. Existing detailed
fields return the primary pair; original values remain in the input/candidate
evidence, rather than silently adding public result fields.

An account-charge amount overlapping the generic account-identifier pattern is
protected only when the explicit posted-charge grammar establishes its role.
This handles Arabic “تم خصم من حسابك ٧٫٠٩٠ دينار” without turning arbitrary
account numbers into amounts. Completion recognition also handles an account
that “was charged”; broader completion/ownership/review rules still apply.

The four original `pendingPolicyCases` in the frozen core fixture are retained
as historical questions. Fee-total and FX-primary decisions are now resolved
here and tested separately. Zero/signed adjustment and duplicate-ingestion
identity remain unresolved; this work does not impose new policy for them.

## Verification and continuation

`tests/python/test_money_candidates.py` checks Python/TS evidence parity, exact
raw spans with emoji/Arabic marks/three digit scripts, balance/identifier/date
roles, fractional/grouped amounts, ambiguity/nonfinite rejection, and four
owner-policy cases across all three detailed runtimes. No arithmetic fallback
or extra event is introduced. Category prediction is outside this work.

The final 52-case strict report is
`data/reports/behavior/core_money_v1_after_r3_final.json`. Before/after policy
comparison still finds zero changes on the existing 511-input snapshot; the
new behavior is exercised by the added policy cases. Final full-suite verification passed **285 Python tests, 11 TypeScript suites and 226 frozen compatibility cases**. These are exposed conformance checks,
not independent bank-SMS accuracy, authentication or device performance evidence.

Next: R4 direction/ownership isolation, beginning with another complete-output
snapshot and a behavior-preserving seam. Keep the current candidate contracts,
primary-amount decisions, ownership bindings and existing API behavior intact.
