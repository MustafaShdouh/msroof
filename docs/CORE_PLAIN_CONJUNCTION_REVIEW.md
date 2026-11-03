# Ordinary conjunction review and proposed safety fix — 2026-11-03

Status: the scored failures were subsequently repaired; see [CORE_PLAIN_CONJUNCTION_REPAIR.md](CORE_PLAIN_CONJUNCTION_REPAIR.md). This document and its metrics describe the preserved pre-repair review baseline.

The review found **54 failing variants from nine authored base cases**. All102existing controls pass. No parser, contract, model or tester code was changed in this review. A general split on and/و would be unsafe; the proposed fix must target incompatible posted amounts and prevent a local own-account phrase from excluding a mixed unresolved message.

## Frozen evidence and annotation limits

`tests/fixtures/core_plain_conjunction_review_v1.json` contains59bases:30required-review compositions,12unscored equal-value/same-direction descriptions and17inherited controls. Three digit scripts and two sender/contact settings produce354variants:180required-review,72observation-only and102controls. Sources are the immutable R5-after snapshot, prior coordinator fixture and existing paired-transfer fixture, all SHA-bound. Ordinary conjunction replacements preserve source wording/amounts. Completion status is deliberately unasserted for new conflicting compositions; existing controls retain their full original assertions.

The72observations may repeat one movement. Repeating the same amount without its currency does not establish a new unit or event: an isolated source's JOD default is not evidence that the composed text describes a separate JOD movement. Their expected labels are absent, their metrics explicitly say scored=false, and they are never counted correct or incorrect. Current observed outputs are12include/60review; these are observations, not truth or a recommendation. A static annotation review caught this omitted-currency issue before measurement; its unmeasured draft is preserved privately, not scored or used to tune runtime.

| Group/check | Result |
| --- | ---: |
| Required-review variants meeting both assertions |126/180 |
| Required-review variants with any mismatch |54/180 |
| Wrong includes in required-review group |12 |
| Wrong excludes in required-review group |30 |
| Incorrect selected amounts in required-review group |24 |
| Inherited controls matching all asserted fields |102/102 |
| Unscored observations |72 |

Failure counts overlap. The54failing variants represent nine bases, not54independent messages. All354full detailed results agree across Python, TypeScript and the generated tester. Digit/contact variants and source compositions are related exposed development checks, not real-world accuracy evidence.

## What the failures show

1. **A total can hide a distinct posting.** For example, an account debit of17.250 precedes another debit of17, fee0.500 and stated total17.500. The global primary selector chooses17.500 and includes the message, despite the extra posting. These12variants require review with no selected amount. In24variants overall, a total remains selected even when the opposite-flow message already receives review; a review decision does not make that amount safe to display as resolved.
2. **Own-account exclusion is global.** An own-account movement of17JOD joined to a debit of17.250 can be excluded because own_accounts takes priority over amount uncertainty. The local own-account fact does not establish that the entire mixed message is one excludable own-account movement. Thirty variants fail this way. Arabic attached and spaced و reveal a boundary sensitivity that the fix must test explicitly.
3. **Useful one-event conjunctions already work.** The102controls include linked paired transfers with one shared amount, explicit-own paired exclusion, existing opposite-flow review conventions, purchase/account-charge FX and fee-inclusive totals. A generic event split must not change them.

Equal-value same-direction restatements remain a separate unscored question. This review does not declare them all multiple events, merge them as duplicates, or turn observed predictions into gold. New genuine source facts or an explicit product policy would be needed to score their interpretation.

## Concrete next implementation slice

Keep this bounded to the scored failures; no model fitting, app work or general text parser rewrite.

1. **Represent selection ambiguity separately from a missing number.** A missing amount within one clear own-account transfer still permits its existing exclusion. Competing completed posting evidence must first prevent whole-message single-event certainty. Do not weaken own-account policy for an otherwise unambiguous event.
2. **Use conjunctions only as candidate boundaries for a safety check.** Both sides must have their own completed monetary evidence from existing completion/account templates and canonical candidate masks. Do not establish completion, direction or ownership by splitting text. Balance, reference/date, fee and standalone-total fragments cannot become new movements. Handle Arabic clitics through existing normalized structural evidence and preserve raw spans.
3. **Scope primary selection to coherent posting evidence.** A stated account charge/total can resolve its payment, not every posting in the message. With incompatible additional posting evidence and no explicit single-event linkage, clear the selected amount. Do not calculate sums/exchange rates or use source-default currencies as proof of a separate event.
4. **Block inappropriate own-account exclusion through the existing uncertainty path.** The validator requires completed+own_accounts to exclude. Therefore do not emit a contradictory completed/own_accounts/review result: mark single-event assessment uncertain when competing evidence prevents application of the own-account exclusion. Existing one-clause completed/review controls must retain their assertions unless a source-bound truth review is separately documented. No new output schema/reason code is required by this proposal.
5. **Preserve supporting relationships.** One shared amount across debit/credit endpoints is an existing paired transfer, not automatically two events. Explicit fee-inclusive totals and original-purchase/account-charge FX controls must keep working. Unscored equal-flow repeats cannot be silently relabelled or claimed as accuracy gains; report any changed observations separately.
6. **Verify before broadening.** Add paired Python/TypeScript safeguards for the nine failing bases, retain all102controls and prior source-bound status conventions, rebuild the tester, then replay the original2302entries, earlier ordering/movement/coordinator packs,70ownership requests,23models and full suite. Ownership confirmation must not invent event selection, amount or direction. If this structural guard cannot separate a case without a new policy, hold it unresolved rather than add a bank/merchant exception or edit old truth.

The expected end state for the scored new cases is180/180review/nullamount and102/102existing-control assertions retained. The72unscored observations remain outside that target. Use a NEW repair tag/snapshot/report; do not overwrite this review baseline or the original fixtures. The review fixture is not compatible with blindly treating every row as a scored core-boundary fixture: observation-only rows intentionally have no expected labels. Use the review producer's records/summary logic or an equally explicit split.

## Reproduction, safeguards and limits

- Producer `tools/evaluation/review_plain_conjunctions.py` validates source SHA, permitted edits, inherited truth and explicit observation status before current-engine comparison.
- Public `data/reports/behavior/core_plain_conjunction_review_v1.json` separates scored and unscored groups and lists only field-level failure references.
- Private `.local-backups/core_plain_conjunction_review_v1/results.json` preserves full inputs/results,70ownership outputs and23model hashes; unmeasured annotation draft is separate.
- Private `data/private/report_inputs/manifests/core_plain_conjunction_review_v1.json` archives source/model bytes. A final verification manifest also preserves the report, review tests and continuation notes.
- Two `test_plain_conjunction_review.py` audit safeguards pass: saved-summary reconstruction and rejection of invented observation labels or missing scored truth. Tests read the frozen review snapshot; they do not require the current parser to keep its measured failures after repair.

```powershell
python -X utf8 -m unittest tests.python.test_plain_conjunction_review -q
```

The last full runtime gate remains352Python+14TypeScript suites+226frozenPASS from the prior repair. It was not repeated for this read-only runtime review; current source/model hashes are verified unchanged. New review-specific failures above remain open and are not hidden by that legacy gate. No fitting, research-model or reserved/final inference, independent admission, outreach, app work, publication or push occurred. Source collection stays deferred. Independent release evidence, zero/signed eligibility and ingestion dedup remain open.
