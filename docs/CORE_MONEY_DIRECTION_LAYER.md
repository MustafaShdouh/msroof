# R4 direction and ownership layer — 2026-10-31

The detailed assessment now delegates owner-relative direction, transfer
relationship refinement and recording eligibility to paired modules:
`src/python/direction_policy.py` and `src/typescript/DirectionPolicy.ts`.
Completion and amount extraction remain separate. The existing
`ownership_context.py` / `OwnershipContext.ts` wrapper still validates and binds
confirmations; this refactor does not introduce another ownership authority.

## Stage order

1. Derive initial direction and relationship from the relevant event clauses.
   Amount extraction still receives that initial direction, preserving its
   previous interpretation.
2. Resolve amount and multi-event ambiguity in the existing assessor.
3. Refine bounded paired-account evidence, then apply only a wrapper-validated
   relationship override. Confirmation cannot supply an amount or completion.
4. Compute recording eligibility: completed own-account events exclude; completed
   external/nontransfer events require amount and resolved direction; unresolved
   fields or ownership review. Nontransaction early rejection remains in the
   assessor before these stages.

No sender/merchant/person registry or inference from mask count is added. Amount,
completion, direction, relationship and recording remain distinct facts.

## Preservation proof

Before changing direction rules, the structural extraction preserved all six
complete outputs for 511 inputs (3,066 detailed/legacy results) and all three
ownership-wrapper outputs for 70 requests (210 results). The recorded detailed
results agree across Python, TypeScript and the built browser. All 23 model
artifacts and existing source fixtures are unchanged.

Private evidence: `.local-backups/core_money_r4/{before,after}.json` and
`ownership_{before,after}.json`. Producer:
`tools/evaluation/snapshot_direction_policy.py`. Public summary:
`data/reports/behavior/core_money_r4_integrity.json`.

## Explicit endpoint repairs, measured separately

The new perspective contrasts exposed pre-existing rule gaps, repaired in shared
grammar 1.0.9 after the structural proof:

- English “to your account/wallet” is an incoming transfer endpoint; “from your
  account/wallet” identifies an outgoing endpoint.
- “From account *1234” without an owner marker cannot alone establish outgoing
  direction. Two account masks leave the owner endpoint unresolved.
- Explicit “from your account … to your account” establishes own-account
  relationship; two arbitrary masks or a counterparty's name do not.

This does not claim a complete language/perspective parser. Conflicting direction
evidence remains unresolved, and a known owner-relative direction does not prove
that both accounts belong to the owner. P2P with another person can be included;
unknown ownership remains review.

Two old assistant-authored fixture expectations assumed outgoing direction from
unowned masks. `tests/fixtures/direction_policy_reviews_v1.json` records exact
source hashes, prior/new directions, reviewer and rationale. Original fixtures
are preserved. Tests apply this explicit weak review layer and still check all
other fields; both cases continue to require review. Historical source snapshots
and old grammar assertions remain intact; the live grammar assertion is 1.0.9.

The policy comparison is separate from the refactor proof:
`.local-backups/core_money_r4/policy_comparison/policy.json` and
`ownership_policy.json`; public `core_money_r4_direction_changes.json` under
`data/reports/behavior/`. Model/fixture/legacy equality is checked, and detailed
changes are enumerated rather than represented as refactor equality.

## Tests and limits

`tests/python/test_direction_policy.py` adds 15 incoming/outgoing, Arabic/English,
named-party, explicit-own, masked-account, cash/refund and pending/declined
contrasts with complete detailed-result parity. Five wrapper contrasts verify
profile/message/text binding, removal of confirmation and missing-amount review;
direct policy checks cover completion, missing amount/direction and own exclusion.
Existing ownership tests continue to check caller-data immutability, conflicts,
malformed context and browser confirmation revocation.

The strict 52-case core report is
`data/reports/behavior/core_money_v1_after_r4_final.json`. Final full-suite verification passed **288 Python tests, 11 TypeScript suites and 226 frozen compatibility cases**. These are exposed conformance
results, not independent receipt accuracy or authenticated bank origin. No model
training, reserved inference, category work, app migration or publication occurs.

Next: R5 remeasure residual core behavior before considering any learning work.
Reuse the stronger frozen direct model only as research evidence; failed attempts
remain consumed. Passing the authored pack is not a release threshold. Zero/signed
adjustments and duplicate-ingestion policy remain unresolved.
