# Amount-role ordering and transfer ownership — 2026-11-03

All **798 source-derived variants** pass their inherited core assertions with full Python, TypeScript and generated-tester result parity. No parser, tester, contract or model change was needed. This closes this bounded check, not the broader release gate.

## Frozen inputs and scope

`tests/fixtures/core_amount_ownership_v1.json` contains 133 contrasts from 43 existing source entries, bound to the SHA of the frozen R5-after snapshot. Five English amount-role sources yield 18 clause permutations plus one equal-valued competing-primary contrast. Thirty-eight transfer sources yield identity, balance-before and balance-after contrasts (114). Every contrast expands across three digit scripts and two sender/contact settings: 798 related checks.

The five amount sources cover bare FX account charge, bare total including fees, explicit total, principal plus fee without an explicit total, and competing primary amounts. Moving clauses preserves every word and number. The equal-primary contrast changes the second primary value to the first; this retains the source's unresolved amount assertion because two distinct primary mentions still compete. No sums, conversions or ownership labels were inferred.

Transfer sources cover own-account exclusion, explicit other-person inclusion, and unresolved ownership review. The balance fragment comes verbatim from the existing `core52/balance-before` case. It cannot provide completion, primary amount or ownership. Expected fields are limited to the source's existing core assertions; missing labels stay missing. Optional party/category output is not asserted invariant.

Fixture language labels identify the **source** language (76 English-source and 57 Arabic-source contrasts). The English balance fragment makes some Arabic-source combinations mixed-language; these are not pure-Arabic accuracy counts. Permutations and numeric/contact variants are neither new genuine SMS nor independent evidence. All training/fitting/independent-evaluation eligibility flags remain false.

## Confirmation and preservation checks

Thirteen existing applied ownership controls generate 52 additional wrapper checks: balance before/after, each with stale and freshly rebound confirmations. Stale raw-text confirmations are invalid with `message_mismatch` and review. Fresh exact-text confirmations preserve all seven core fields. Python, TypeScript and the actual tester bundle agree on full wrapper results. These are hypothetical context tests, not confirmations about actual accounts.

The new test module also verifies source SHA, exact permitted text edits, metadata preservation and inheritance of only existing expected fields. The runtime implementation is not used to create expected labels.

Evidence:

- `data/reports/behavior/core_amount_ownership_v1_comparison.json`: frozen before/after, 1,036 entries = original 238 diagnostics plus 798 new variants, no detailed-result changes or asserted-field regressions.
- `data/reports/behavior/core_amount_ownership_integrity_v1.json`: separately remeasures all original 2,302 full detailed and legacy outputs; all unchanged. Seventy ownership requests and 23 model artifacts also unchanged.
- Private `.local-backups/core_amount_ownership_v1/{before,after}.json`: exact frozen inputs/results; immutable R5 snapshot remains the source.
- Private `data/private/report_inputs/manifests/core_amount_ownership_integrity_v1.json`: content-addressed report inputs and source/model bytes.
- `tests/python/test_core_amount_ownership.py`: three safeguards covering provenance, runtime parity and confirmation binding.

Reproduce without rewriting historical evidence:

```powershell
python -X utf8 -m unittest tests.python.test_core_amount_ownership -q
```

The immutable before/after CLI needs a new tag for any future run; do not overwrite the original snapshots or reports. Keep these newly exposed contrasts in future exposure audits. No fitting, research-model inference, reserved/final scoring, data admission, app work or publication occurred.

Full verification: **346 Python tests, 14 TypeScript suites and 226 frozen cases pass**. Runtime/model bytes remain unchanged.

## Next bounded check

Test the one-event boundary using source-derived combinations of completed movements, including bare amounts, opposite flows and explicit totals/account charges. The existing behavior contract requires inseparable multiple events or conflicting amounts/outcomes to remain unresolved. Freeze those cases and their textual evidence before repair; do not assume that a total from one event resolves a second event. Keep zero/signed movements and ingestion deduplication outside scored assertions until their product policy is decided. Collection stays deferred by the owner's existing-data choice.
