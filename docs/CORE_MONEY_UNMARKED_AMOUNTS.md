# Unmarked owned-account amounts — 2026-11-01

Grammar 1.0.17 closes the known currency-default gap: a clear positive account
quantity such as “17.250 was debited from your account” or “خُصم ١٧٫٢٥٠ من حسابك”
now yields 17.25, outgoing, JOD with `currencyResolution: default_missing`.
Recognized ambiguous units such as “dollars” retain `default_ambiguous`.
Explicit foreign currencies retain their stated unit. No conversion is performed.

## Architecture and boundaries

`money_syntax.py` / `MoneySyntax.ts` supply the existing lexical grammar to both
the candidate collector and account-effect compiler. Extracting this dependency
first preserved 13,812 full detailed/legacy outputs plus 210 ownership outputs
on 2,302 inputs / 70 ownership requests; all 23 model artifacts were unchanged.
The exact intermediate sources are archived privately. Evidence:
`data/reports/behavior/core_money_r5a_unmarked_syntax_refactor.json`.

The shared account templates now recognize either an explicit monetary mention
or a guarded unmarked positive quantity. The same compiled templates provide
completion, direction and normalized numeric spans. This avoids a separate
bare-number recognizer disagreeing with the account-role recognizer.
Explicit-primary labels can also introduce an unmarked posted total/account charge.

The collector masks balances and dates first, captures account-role spans, then
applies identifier exclusions. Only a receipt role starting before the account
identifier label can protect its amount (“استلم حسابك 17”). An account label
before a numeric subject (“account 1234 was debited from your account”) does not
gain that protection. If identifier masking changes even part of a captured
number, the entire unmarked candidate is discarded; “Reference 17.250” cannot
leave `.250` as an amount. Owner masks can be removed without losing the earlier
source-account role. Raw offsets remain Unicode code points in original text.

Selection distinguishes source spans, including two distinct mentions of the
same value. A bare principal and a fee compete; a lone explicit fee cannot win
just because it has a currency. One explicitly stated primary total/account
charge wins under the existing owner-approved policy; multiple primary mentions
remain unresolved. The selected mention supplies its own currency resolution:
“Purchase USD 10; your account was charged 7.090” selects 7.09 JOD/default_missing,
without borrowing USD from the original purchase. Numeric lists remain unresolved.

Bare candidates require resolved completed context before selection. Negation,
questions, personal messages, quoted exercises, uncertain outcomes, points and
physical/count units remain guarded. Zero and signed quantities do not gain this
new bare path; their product policies remain unresolved and unscored. Existing
explicit-number behavior, ownership confirmations and public API are preserved.

## Measured development results

The frozen `tests/fixtures/core_unmarked_amounts_v1.json` contains 46 authored
base cases, expanded to 276 through three digit scripts and two contact/sender
wrappers. It is exposed development data, excluded from training and independent
evaluation. Its original expectations were retained throughout the repair.

| Asserted measure | Before | After |
| --- | ---: | ---: |
| All checked fields, new pack | 150/276 | 276/276 |
| Status, new pack | 222/276 | 276/276 |
| Eligible complete events, new pack | 18/126 | 126/126 |
| Arabic checked fields | 36/84 | 84/84 |
| English checked fields | 114/192 | 192/192 |
| False includes of labeled nontransactions | 0/54 | 0/54 |
| Missed labeled completions | 48/204 | 0/204 |
| Wrong certainty on uncertain outcomes | 6/18 | 0/18 |

All 2,302 detailed results agree across Python, TypeScript and the rebuilt tester.
Exactly 126 results changed, all in the new pack. The earlier 2,026 full detailed
results are identical, all asserted fields still pass, and all 70 ownership
requests, legacy outputs and 23 model artifacts remain unchanged. Core remains
52/52 asserted cases (51 status assertions). The original 238-entry queue remains
resolved on its asserted fields; authored messages retain 74/74 status and 48/48
eligible complete-event matches, including Arabic 24/24 and English 24/24 events.

Full verification: 320 Python tests, 11 TypeScript suites and 226 frozen cases pass.
Five new tests cover frozen contrasts, three-runtime/candidate parity, exact
Unicode spans, partial identifiers, account IDs, counts, equal-value competing
mentions, currency locality and structural decisions without candidate scoring.
Extra test contrasts are development checks, not additions to the frozen pack.

Evidence:

- `data/reports/behavior/core_money_r5a_unmarked_comparison.json`
- `data/reports/behavior/core_money_v1_after_r5a_unmarked.json`
- Private `.local-backups/core_money_r5a_unmarked/{before,after}.json`
- `tests/python/test_unmarked_account_amounts.py`

The comparison binds the shared syntax, account/direction/candidate/assessment
sources, contract, checker, fixtures and browser bundle. The previous checker
is archived by SHA in `.local-backups/source_snapshots`; old reports are unchanged.

## R5 exit decision

R5's finite conformance exit is met: the original reviewed error queue and the
known unmarked-amount contract gap are resolved with no observed regressions in
the measured development set. The simpler parser meets these finite requirements;
no further model fit or experiment is justified by a remaining measured failure
in this queue. This does not establish generalization, origin authentication,
calibrated confidence or performance on future Jordan SMS.

R6 starts with a readiness evidence inventory and coverage gaps, using existing
exposed results and an explicit separation from independent evidence. Release
thresholds are unset; reserved scope32/merchant29 remain uninferred. Independent
final evaluation, model fitting/promotion, app migration, publication and legacy
deletion require their own scope and evidence. No such action occurred here.
