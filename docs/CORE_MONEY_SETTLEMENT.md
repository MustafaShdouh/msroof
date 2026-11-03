# R5a settlement, collection and remaining fields — 2026-10-31

The last 24 known completion misses and three annotated direction/relationship
errors are repaired. All **238 original exposed development entries** now match
their asserted core fields. Authored eligible complete-event matches rise
**33/48 → 48/48**, retaining reviews and misses in the denominator.

This is finite conformance on assistant-weak, exposed examples. It is not measured
accuracy on unseen genuine Jordan SMS. Status-only diagnostics do not suddenly
gain amount/ownership truth, and optional party/category fields are not adjudicated
by these core comparisons. R5 remains active for the already-known unmarked-amount
contract gap; R6/release readiness is not established.

## Shared changes

Grammar 1.0.16 extends the existing completion and account-effect contracts for:

- Finished/settled payments and debits, collected installments with a stated owner
  debit, recorded Arabic debit/credit roles and completed internal account movement.
- Money returned to the owner's card/account, distinguishing the actual incoming
  effect from a nominal earlier purchase word.
- Explicit bank fee/commission purposes and incoming salary-credit purposes.
  These purpose phrases alone do not create a person-to-person transfer.
- “No longer pending” wording, which cannot invalidate a separately stated finished
  debit. A genuinely conflicting pending notice still requires review.

Attached Arabic conjunctions are supported without changing returned source text.
Posting/account-effect predicates now also establish financial context for explicit
unresolved-final-outcome wording. A recorded debit with an unresolved result stays
`uncertain` / `review`, rather than being included.

## Transfer purpose is not ownership proof

`transfer_content` / `transferContent` remove only the bounded commission/fee or
salary-purpose phrase before detecting an additional transfer. Actual remaining
transfer wording, explicit person/own evidence, CliQ and linked debit/credit
endpoints preserve transfer semantics. No name, mask count, “internal” or “external”
adjective is upgraded to ownership proof.

Salary-purpose suppression requires incoming account-credit evidence without an
account debit. An outgoing movement merely labeled “حوالة الراتب” retains unknown
transfer ownership and review. Explicit own-account or another-person evidence still
takes precedence. A nontransfer fee cannot be turned into an own-account transfer
by the existing confirmation wrapper; its binding/schema behavior is unchanged.

No original expectations or source labels were edited. The existing shared
Python/TypeScript templates supply both completion and direction; no new bank,
merchant, sender or fixture-ID lists were introduced. Public API fields, flat
weights and legacy outputs are unchanged on the measured inputs. The optional
tester was rebuilt after the final guard change and checked against both engines.

## Monetary roles and balances

The grammar now recognizes “Balance after the movement/transaction” and
“الرصيد بعد الحركة/العملية” as balance metadata. Their values are masked before
amount selection, with raw Unicode source spans retained. Thus the original cash
receipt's movement amount no longer competes with its remaining balance; explicit
foreign currency on the movement is preserved.

Financial-candidate fallback also ignores these masked balance labels, so the word
“movement” in a balance-only notice cannot manufacture financial-event evidence.
An actual movement still needs independent completion evidence. No new arithmetic,
FX conversion, fee-total policy or primary-ranking heuristic was added.

## Development evidence

The new fixture has 60 bilingual base cases and 360 digit/sender/contact variants:
**138/360 before → 360/360 after**, with full Python/TypeScript/browser equality.
It covers settlement versus approval/request/denial/unknown outcomes, loan documents
and spending limits, points, purpose versus actual transfers, confirmation, real
owner endpoints, balance metadata and merchant-word traps. Variants are not
independent messages.

All six earlier packs remain correct: 168, 216, 300, 216, 252 and 276 variants.
Strict core remains 52/52 asserted cases, including 51 status assertions. Across
2,026 entries: full detailed parity, zero expected-field regressions, unchanged
measured legacy outputs, all 70 ownership requests and all 23 model artifacts.
All 37 reviewed nontransaction/uncertainty expectations still pass.

| Original exposed cohort | Status before | After |
| --- | ---: | ---: |
| Manual | 21/24 | 24/24 |
| Context probes | 19/24 | 24/24 |
| Scope development | 30/32 | 32/32 |
| Authored | 60/74 | 74/74 |

Old validation remains 18/18 and quote controls 14/14. All original asserted core
fields match; core's one partial expectation has no status truth. Exactly 24
statuses improve. Three already-completed authored field errors now resolve, and
the status-only English withdrawal diagnostic's previously unresolved amount is
recovered. Arabic and English authored status each match 37/37. None of these
counts is an independent final accuracy estimate or calibrated confidence claim.

## Artifacts and continuation

- Fixture: `tests/fixtures/completion_settlement_v1.json`.
- Four safeguards: `tests/python/test_completion_settlement.py`.
- Comparison: `data/reports/behavior/core_money_r5a_settlement_comparison.json`.
- Strict core: `core_money_v1_after_r5a_settlement.json` in behavior reports.
- Private full snapshots: `.local-backups/core_money_r5a_settlement/{before,after}.json`.
- Producer: existing `tools/evaluation/core_boundary_check.py`, all seven
  versioned completion fixtures.

Final verification passes **315 Python tests, 11 TypeScript suites and all 226
frozen compatibility cases**. Strict core passes 52/52 in every runtime with zero
parity mismatches. No historical expectation revisions were needed in this step.

No fitting, new research inference, reserved scoring, application migration or push
occurred. Hermes timing remains unmeasured. Existing historical review layers and
frozen reports/fixtures remain intact.

Next: test clear account quantities without a currency against the already-agreed
visible JOD-default policy, distinguishing amounts from IDs, dates and points.
Resolve only supported cases and leave ambiguity under review. Independent source
evidence and release thresholds remain separate work; passing these known examples
does not authorize reserved scoring or release.
