# Multiple completed movements — 2026-11-03

The detailed parser now requires review when more than one completed clause has its own monetary movement, including amounts without a currency marker. A standalone inclusive total remains part of its payment. Python, TypeScript and the rebuilt tester agree on all 426 frozen variants.

## Measured defect and repair

The previous safeguard counted currency-marked amounts in completed clauses. It missed bare account effects, allowing one event's total or FX account charge to be selected while another movement remained present. An own-account phrase could exclude the combined message. Conversely, a principal and inclusive total, both currency-marked, were counted as two events.

`tests/fixtures/core_multiple_movements_v1.json` was frozen before repair and binds the original R5-after source snapshot by SHA. It contains 64 two-source compositions (16 pairs, two orders, plain/explicit separation) plus seven single-event controls. Three digit scripts and two sender/contact settings produce 384 multiple-movement variants and 42 controls. Arabic/English cases cover opposite flows, same-valued debits, foreign/bare amounts, fees/totals, account charges and own-account movements mixed with a separate debit. Source wording and existing completion/amount evidence are retained. Review/null amount for compositions follows the existing one-event contract, never a model prediction. These are related, exposed, assistant-authored development checks, not genuine new SMS or independent evidence.

| Check | Before | After |
| --- | ---: | ---: |
| All asserted core fields correct | 36/426 | 426/426 |
| Multiple movements wrongly included | 120/384 | 0/384 |
| Multiple movements wrongly excluded | 48/384 | 0/384 |
| Multiple movements reviewed without a selected amount | 168/384 | 384/384 |
| Single-event controls correct | 36/42 | 42/42 |

Paired `has_movement_amount` / `hasMovementAmount` helpers in `money_candidates.py` / `MoneyCandidates.ts` operate on normalized clauses. Currency-marked detection retains balance masking; bare candidates reuse canonical source/identifier/date masks and account/primary roles. Only an entire standalone total expression is supporting information. A total prefix cannot hide extra following movement text. Account-charge clauses remain movement evidence.

The detailed assessors use this check only when multiple clauses already have completion evidence. More than one amount-bearing movement clause sets status uncertain and amount null before ownership/recording. A total-only clause cannot create an extra event. No sums, currency conversions, names or account registries determine selection.

Shared structural grammar **1.0.18** adds `amountSummaryPrefix`. Learned features and weights are unchanged. The live-version assertion in `test_quoted_examples.py` advances to 1.0.18; its historical 1.0.5 replay and original frozen assertions remain intact. Before-source bytes were archived before editing.

## Evidence and preservation

- `data/reports/behavior/core_multiple_movements_v1_comparison.json`: frozen before/after for 238 original diagnostic entries plus 426 variants. Changes occur only in 390 new variants. No asserted-field regressions; full three-runtime parity; unchanged legacy outputs.
- `data/reports/behavior/core_multiple_movements_integrity_v1.json`: all original 2,302 full detailed/legacy results, 70 ownership requests and 23 model artifacts unchanged.
- Private `.local-backups/core_multiple_movements_v1/{before,after,regression}.json`: exact inputs/results.
- Private `data/private/report_inputs/manifests/core_multiple_movements_{before,integrity}_v1.json`: content-addressed before/final source and report inputs.
- `tests/python/test_core_multiple_movements.py`: source/policy provenance, full matrix/parity and summary-versus-movement/identifier/balance safeguards.

Full verification before the external branch switch: **349 Python tests, 14 TypeScript suites and 226 frozen cases pass**. This reruns the prior 6,984 formatting and 798 amount/ownership checks. Tester build byte-reproduces. Legacy APIs and weights are unchanged. No fitting, research-model/reserved/final inference, admission, app work or publication was performed by this task.

```powershell
python -X utf8 -m unittest tests.python.test_core_multiple_movements -q
```

Historical artifacts are immutable; future changes need new fixture/report versions. Include these newly exposed compositions in future exposure audits. No real-world accuracy, calibrated confidence, authentication or mobile-performance claim follows.

## Checkout recovery

An external branch switch temporarily moved the shared checkout to old `main` (`0fa785f`) while final notes were being written. The checkout then returned externally to `codex/merged-project` (`f97fb7c`), containing the tested runtime/tests/reports. All 17 files in the final source manifest matched their saved hashes after return; canonical tester build also byte-reproduced. The user authorized recovery. No agent reset, checkout, merge, commit or push was needed. Ignored STATE/HANDOFF were lost across the switch: they were reconstructed from verified evidence/current context and the preserved pre-cleanup reference; the original invariants skill was recovered byte-for-byte from Git. These are reconstructed notes, not a claim of exact recovery of the lost notes. Final post-recovery full gate also passes349Python+14TS+226frozen. The first recovered gate failed because two raw seed copies were missing; restored byte-identically from originals after ledger SHA verification. Seven additional raw archives recovered from matching historical Git blobs; all nine match the private audit, and ten provenance safeguards pass after recovery. No original/label/admission changed. Full gate ran after the two required seed copies; additional seven archive restorations were covered by the targeted provenance suite, with no runtime edits. Logs and private recovery ledger remain in .local-backups/core_multiple_movements_v1. STATE/HANDOFF/source bytes are now archived by content hash under a private recovery manifest.

## Next boundary

This is a completed-clause safeguard, not general event segmentation. Next freeze same-clause conjunction cases where a total/account charge and another movement share a sentence, alongside existing one-clause completion controls. Preserve original fixtures and explicit ownership/amount uncertainty. Do not invent event counts from names/repeated descriptions or silently change existing labels. Conflicting truth conventions require documented evidence and a versioned review. Collection remains deferred; zero/signed movements and ingestion deduplication remain uncontracted.
