# Explicit coordinated movements — 2026-11-03

The detailed parser now notices explicit separate-operation coordinators inside a completed clause before choosing one event's amount. Arabic and English use one shared boundary contract. The fragments refine competing-amount safety only: they cannot establish completion or replace the original context checks. All 540 frozen variants and 24 additional example-frame controls pass with full Python, TypeScript and generated-tester parity.

## Frozen contrasts and measured result

`tests/fixtures/core_coordinated_movements_v1.json` was frozen before edits. Its source snapshot and prior multi-clause fixture are SHA-bound. It contains 90 bases:64 two-source compositions,7 prior single-event controls,3 semicolon-to-ordinary-and supporting-amount controls, and16 separate-balance controls. The64 compositions preserve the32 ordered source pairs from the prior pack and use two explicit coordinators per language. English examples are “and separately” and “and as a separate transaction”; Arabic examples are «وفي عملية أخرى» and «وبعملية أخرى». Each fragment already has completed monetary evidence. Expected review/null amount follows the existing one-event policy, never predicted labels.

Three digit scripts and two sender/contact states create384 multiple-movement variants and156 controls=540related checks. Some source messages contain fee/total semicolons; the new coordinator joins the final amount-bearing fragment to the following movement. Source-language labels are inherited, and English balance additions make some Arabic-source controls mixed-language. These are exposed assistant-authored compositions, not genuine new SMS or independent evidence.

| Check | Before | After |
| --- | ---: | ---: |
| All asserted core fields correct | 216/540 | 540/540 |
| Separate-movement cases correct | 72/384 | 384/384 |
| Separate movements wrongly included | 84/384 | 0/384 |
| Separate movements wrongly excluded | 48/384 | 0/384 |
| Single-event and balance controls correct | 144/156 | 156/156 |

The twelve failed controls combined a standalone total with separately mentioned balance information; the old clause counter treated that combined fragment as another movement. Boundary refinement now leaves the standalone total and balance as supporting information, while the actual debit still establishes the movement. Ordinary conjunctions in a purchase/account-charge or inclusive-total description keep their existing behavior.

## Implementation boundary

`config/contracts/transaction_evidence.json` structural grammar **1.0.19** adds `separateMovementBoundary`. The Python/TypeScript detailed assessors retain the original sentence/conditional scope analysis, completion evidence, direction and ownership stages. After normal amount selection, they look only inside already-completed clauses for the explicit coordinator. If present, fragments must independently pass the existing `completed_clause` / `completedClause` predicate, then the existing `has_movement_amount` / `hasMovementAmount` predicate. More than one amount-bearing completed movement causes uncertain/review/null amount before ownership exclusion.

A coordinator is not evidence that money moved. Quoted examples still exit through the original nontransaction checks; balance-only fragments do not count. The predicates reuse guarded numeric/account/primary roles and source masks, plus the existing exact standalone-total exception. No general split on ordinary and/و, no inferred event count from names/masks, no sum/conversion and no merchant/bank exceptions. No learned preprocessing or weight change.

The live grammar assertion in `test_quoted_examples.py` advances to1.0.19; its frozen1.0.5 replay and historical original assertions remain intact. No source truth was revised and no historical fixture/report overwritten. The tester was rebuilt canonically and byte-reproduces.

## Verification and preservation

- `data/reports/behavior/core_coordinated_movements_v1_comparison.json`: original238diagnostics+540newvariants=778before/after entries; changes confined to324newvariants, no asserted-field regression, full three-runtime parity, unchanged legacy outputs.
- `data/reports/behavior/core_coordinated_movements_integrity_v1.json`: full detailed/legacy equality for originalR5 snapshot2302entries, prior ordering snapshot1036entries and prior multi-clause snapshot664entries. These4002replays include repeated diagnostics; they are preservation checks, not4002independent messages. Seventy ownership requests and23model artifacts unchanged.
- Private `.local-backups/core_coordinated_movements_v1/{before,after,regression}.json` preserve exact inputs/results. `data/private/report_inputs/manifests/core_coordinated_movements_{before,integrity}_v1.json` archive exact source/test/report bytes.
- Three `test_core_coordinated_movements.py` safeguards cover provenance,540full parity variants and24 additional framed examples (Arabic/English,3digits,2metadata). Explicit separate-operation text cannot escape an illustrative/nonreceipt frame. These authored scope checks are declared in the test, not additional independently frozen SMS truth.

Nine focused tests pass. Full gate: **352 Python tests,14 TypeScript suites,226 frozen cases PASS**; log `.local-backups/core_coordinated_movements_v1/full_gate.log`. Historical notes/recovery manifests describe older source versions and remain immutable; do not “refresh” them to1.0.19. Add new exposed compositions/scope controls to future exposure audits. No fitting, research-model or reserved/final inference, independent admission, app work or publication occurred.

```powershell
python -X utf8 -m unittest tests.python.test_core_coordinated_movements -q
```

## Next boundary and limits

Review ordinary and/و conjunctions against existing paired-transfer, equal-amount, debit/credit, inclusive-total and FX/account-charge controls before proposing a wider split. Ordinary conjunction can describe one event twice or its supporting figures, so it cannot establish multiple operations by itself. Freeze contrasts and source/policy evidence first; do not silently rewrite prior completion conventions. This explicit-coordinator safeguard is not general co-reference/event segmentation or proof of real-world accuracy. Independent release evidence, zero/signed policy and ingestion deduplication remain open; source collection stays deferred.
