# Current behavior and model comparison

This is development evidence. The 31 authored contract probes, 226 exposed
regression cases, synthetic validation split and exact human category-policy
snapshots have different roles. None supplies independent real-world accuracy.
Current measurements: `data/reports/behavior/canonical_exact_names_v1.json`/`.md`.

## Measured gaps

All three engines agree on the 299 checked complete outputs. Python compatibility
aliases are validated and removed before comparison; confidence, reasons,
categories, balance and optional FX fields remain in the comparison. The frozen
226-case gate still passes in Python and TypeScript.

The authored policy probes match the required inclusion/review outcome in 22/31
cases. They expose one included payment request among nine ordinary/nontransaction
cases, three missed eligible receipts among 15, and inclusion of three of four
person transfers. Review outcomes, completion status, transfer ownership and
currency-resolution/category-status markers are unsupported by the legacy API;
the evaluator does not invent them from rejection reasons. Runtime category labels
still belong to the older taxonomy and are not silently mapped to the target 15.

Strict whole-value agreement is measured separately from the frozen runner's
permitted substring comparisons. Merchant values now agree with 96/99 old
annotations. The three remaining differences were inspected: full `COZMO
سوبرماركت` versus shortened `COZMO`, and two source names with Arabic diacritics
versus cleaned labels. The owner's new exact-name decision explains these
differences; frozen expectations remain unchanged. Account values agree with 71/81
literal annotations; ten old labels include wording such as `ending in`, while
the engine returns the identifier. Amount/currency/direction remain 106/106 and
annotated balances 104/104 on this development regression.

Exact character-span performance and independent family/language uncertainty
intervals remain unmeasurable with current reviewed truth. A zero denominator
is null, not a perfect score. The JSON includes counts, language and transfer
slices, missed versus accepted-only field results, and unsupported assignments.

## Refactoring and corrections

The optional tester now bundles the local canonical TypeScript module graph with
Node 24's type stripper. The copied JavaScript inference implementation is removed;
the 14 preset controls and separate merchant research panel remain. Embedded
source hashes and model equality are checked by the regression safeguards.

Legacy additive-IDF scoring is isolated in `LegacyTransactionModel.ts` and its
Python counterpart, preserving normal arithmetic and thresholds. Unknown words
that collide with JavaScript object properties no longer crash scoring or create
spurious correction/category results. The additive candidate scorer has the same
protection. Python legacy scoring also handles extreme negative logits consistently
with JavaScript. Explicit `between your own accounts` wording is recognized by
the existing own-account guard.

On 2026-10-26 the owner selected **preserve the exact name text**. The convention is
recorded in `config/contracts/entity_text.json`. `EntityText.ts`/`entity_text.py`
keep a normalized matching view and source offsets, then return the original name
with case, diacritics, internal spacing, descriptors and digit script intact.
Boundary fixes prevent a glued account mask, a following `Your ...` clause, or
an Arabic name beginning with `تم` from corrupting the extracted name. Eleven
authored controls verify this convention across runtimes.

Numeric equivalence checks now transform the expected exact name alongside the
input script. Every other structured field and decision still has to match.
This implements the raw-name policy rather than treating a source-text change
as a change in its monetary meaning.

## Research candidates

Two candidates were trained on the unchanged 1,702/418 global split using the
same counted word/bigram features and .7/.5 decision thresholds. One used the
existing sparse SGD routine; the controlled comparison used fixed-C liblinear.
Exported liblinear logits match the estimator, and both exported heads match the
TypeScript score contract. This is a two-trial development comparison, not a
hyperparameter search against the final test.

| Same runtime guards/extraction | Current baseline | Each candidate |
| --- | --- | --- |
| 418 synthetic validation rows | 0 false inclusions, 0 misses | 0 false inclusions, 45 misses |
| 226 regression cases | 0 false inclusions, 0 misses | 0 false inclusions, 20 misses |
| Direction among all 215 eligible validation transactions | 215 correct | 170 correct, including misses in denominator |

The raw candidate direction heads agree with 100/215 validation labels before
lexical runtime overrides. Both candidates are rejected. The current baseline
has historical exposure to the generator families, so its perfect development
score does not establish better real-world generalization. No existing model
file was modified or promoted. Current comparison artifacts:

- `data/reports/behavior/jordan_sanitized_v1_final_comparison.json`
- `data/reports/behavior/jordan_sanitized_liblinear_v1_final_comparison.json`

Their model-only training reports and earlier comparisons remain historical
evidence. No reserved merchant final-test inference occurred.

## Reproduction and next work

```powershell
py -X utf8 run_all_tests.py
py -X utf8 training/evaluate_behavior.py --run-id precompletion_code_v1 --check
py -X utf8 -m unittest tests.python.test_authorization_request
```

Current checks: 96 unit safeguards, the 226-case Python/TS gate, 299 full-output parity
probes plus three prototype-word boundary inputs,22 authored authorization-request
controls across Python/TS/browser, and678 numeric variants per runtime.
Report inputs are preserved privately under
`data/private/report_inputs/`, deduplicated by byte hash with per-run manifests.
Changed source inputs require new report IDs; old reports remain measurements
of their recorded versions, not live checks of the latest code.

The BIO label repair and approved context experiment are complete; see
`docs/BIO_EVALUATION.md`. Those results use prior recorded sources. Their historical
`--check` commands require those source versions from private input snapshots;
do not refit or overwrite reports to refresh changed hashes.

## Pre-completion code requests,2026-10-26

The new shared grammar `config/contracts/authorization_request.json` recognizes
explicit requests for a code to complete/authorize a financial operation in
English or Arabic, including reversed instruction order, Arabic diacritics,
Western/Arabic-Indic/Persian digits and common alef variants. Python
`authorization_request.py` and TypeScript `AuthorizationRequest.ts` apply this
structural guard before learned transaction scoring. Bare mentions of a code or
authorization do not trigger it. This is a targeted runtime repair, not a learned
model change or a claim of exhaustive OTP coverage.

All13 authored requests are excluded; nine nonmatching contrasts include six
completed receipts, all retained. All22 complete canonical outputs agree across
Python/TS/browser. A separate check verifies rejection before scoring/model
initialization. The original source OTP is privately replayed successfully in
`data/private/entity_intake/web_review_v1/diagnostic_after_otp_fix_v1.json`;
the other three source outputs are unchanged. Before/after private inputs are
preserved through deduplicated report snapshots. These are exposed development
checks, not independent accuracy. No training rows or model weights changed.

The rebuilt tester uses the canonical repaired runtime. Current behavior report
`data/reports/behavior/precompletion_code_v1.json` retains22/31 authored tracking
matches,1/9 ordinary false inclusions and3/15 eligible misses/reviews: the narrow
OTP repair does not resolve those other policy gaps. The legacy API still cannot
emit uncertain/review. Next work is a concrete design for that output and its
compatibility behavior before a meaningful API change. Independent reviewed
Jordan messages and transaction-purpose category truth remain needed.
