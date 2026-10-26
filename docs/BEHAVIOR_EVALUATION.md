# Current behavior and model comparison

This is development evidence. The 31 authored contract probes, 226 exposed
regression cases, synthetic validation split and exact human category-policy
snapshots have different roles. None supplies independent real-world accuracy.
Legacy measurements: `data/reports/behavior/canonical_exact_names_v1.json`/`.md`.
Current detailed measurement: `data/reports/behavior/arabic_direction_v1.json`.

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
py -X utf8 -m unittest tests.python.test_detailed_assessment tests.python.test_runtime_parity
py -X utf8 training/evaluate_detailed.py --run-id arabic_direction_v1 --check
```

Current checks: 102 unit safeguards, the 226-case Python/TS gate, 299 legacy full-output parity
probes plus three prototype-word boundary inputs,22 authored authorization-request
controls across Python/TS/browser, and678 numeric variants per runtime.
Report inputs are preserved privately under
`data/private/report_inputs/`, deduplicated by byte hash with per-run manifests.
Changed source inputs require new report IDs; old reports remain measurements
of their recorded versions, not live checks of the latest code.

The minimal tester restyling changed its HTML/generator hashes. Its eight
targeted UI/runtime unit checks and merchant UI safeguards pass; real browser
checks cover desktop/mobile layout and controls. Re-evaluating the349 detailed
cohort comparisons produces exactly the parsing_v2 report fields/outcomes after
excluding input hashes. For `evaluate_detailed.py --run-id detailed_parsing_v2
--check`, use that report's archived UI sources. A second model report was not
created solely for the visual change. The subsequent purchase_evidence_v1 report
captures the approved current UI and the purchase-language repair below.

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

The rebuilt tester uses the canonical repaired runtime. At the OTP milestone, report
`data/reports/behavior/precompletion_code_v1.json` retains22/31 authored tracking
matches,1/9 ordinary false inclusions and3/15 eligible misses/reviews: the narrow
OTP repair does not resolve those other policy gaps. The legacy API still cannot
emit uncertain/review. The detailed API below adds those outputs while retaining
the legacy caller path for comparison. Independent reviewed
Jordan messages and transaction-purpose category truth remain needed.

## Detailed assessment Slice1,2026-10-26

Owner approved the design in `docs/TRANSACTION_BEHAVIOR.md`. Implemented
TypeScript `MasroofEngine.analyzeDetailed({text, sender?, isContact?, receivedAt?})`
and Python `engine.predict_detailed({...})`. They return the exact canonical
contract1.0.0 fields. Existing `analyze`/`predict` retain their legacy behavior;
the additive assessment/projection in Slice2 has not been implemented.

Shared structural evidence is in `config/contracts/transaction_evidence.json`,
with parallel `src/python/detailed_assessment.py` and
`src/typescript/DetailedAssessment.ts`. The new layer reuses extraction without
legacy category scoring. It distinguishes completed movement from requests,
failed/future/quoted events and unresolved authorizations; direction and transfer
ownership require contextual evidence. Identifiers, dates and balances are
masked before primary amount selection. Multiple/invalid monetary candidates
remain unresolved. Counterparty anchors project back to exact source text,
without treating account labels as names. Generic ATM activity remains review.

Canonical categories use narrow, explicit purpose evidence only; no new category
model was trained or promoted. Unknown or mixed purpose stays null/uncertain,
and Other requires an understood purpose outside the other categories. Legacy
category suggestions are not silently mapped onto the15 categories. The existing
classifier0.70 candidate cutoff is only a fallback to review, never a completion,
direction or ownership decision. Sender/contact metadata cannot determine status.

`tools/browser/tester.html` now has a detailed comparison section with a visible
Review required summary and canonical JSON; its legacy table is explicitly
labeled. This does not migrate existing callers. A UI-handler check exercises
the actual comparison output. Detailed execution latency on Hermes has not been
measured; the legacy regression timing is not a detailed-API benchmark.

Final report: `data/reports/behavior/detailed_assessment_v3.json`. Its inputs are
preserved in deduplicated private snapshots. Earlier v1/v2 reports preserve
intermediate versions; v1 revealed two unrecognized processed reversals, repaired
with general reversal evidence and authored contrasts. Do not overwrite the
earlier reports or interpret frozen compatibility labels as new canonical truth.

| Development check | Result |
| --- | --- |
| Authored policy tracking decisions |31/31; Arabic5/5, English25/25, mixed1/1 |
| All canonical policy fields |30/31 complete matches |
| Additional authored contextual controls |42/42 expected-field matches |
| Authorization/receipt controls |22, all applicable expectations pass |
| Full canonical Python/TS/browser comparison |321/321 identical results |
| Existing tests and frozen legacy gate |101 tests +226 cases pass |
| Private source replay |OTP excluded; three uncertain/review, three-runtime parity |

The single policy-field disagreement is `completed_missing_amount`: its frozen
expected `currencyResolution` is explicit, but the message has no currency token.
The API returns JOD + default_missing. The original label and fixture hashes are
unchanged; the discrepancy is recorded rather than converted into fabricated
explicit-currency evidence. These tiny authored/synthetic/exposed sets do not
establish independent accuracy or Arabic generalization.

On the226 frozen compatibility cases, legacy behavior remains106 included and120
excluded. Detailed behavior is25 include,113 review,88 exclude. The83 changes in
the boolean include projection comprise82 legacy inclusions now reviewed and
one previous phone-sender rejection now included. The latter follows the approved
rule that sender formatting alone cannot reject a completed notification; its
frozen label remains unchanged. Among the82 reviews, reasons overlap:
37 completion unresolved,37 transfer ownership unresolved,23 amount unresolved,
12 direction unresolved. Forty-five retain completed status while needing field
or relationship review. Of jointly included results,16 change the name boundary;
amount, currency and direction agree with legacy values. These are differences
to review, not adjudicated improvements.

Frozen script slices: Arabic-script-present12 include/52 review/47 exclude;
no-Arabic-script13 include/61 review/41 exclude. They describe output coverage,
not measured correctness. Private source replay is retained separately in
`data/private/entity_intake/web_review_v1/detailed_slice1_v3.json`; original
source annotations and admission flags remain unchanged.

### Compatibility triage,2026-10-26

Read-only review of all82 newly reviewed legacy inclusions and16 included
merchant-field changes is complete. This is diagnosis of exposed development
fixtures, not corrected truth or independent performance.

The82 review reasons overlap as reported above. The recurring cases point to
three different kinds of work:

- **Likely evidence-grammar defects:** all23 `amount_unresolved` cases have a
  visible transaction amount in the source text. Most also contain a second
  currency amount in a balance phrase. The shared balance masker does not cover
  common Arabic forms with `هو` before the value or a trailing `الرصيد` after
  the value, so the transaction amount and balance can both remain candidates.
  A narrow balance-span repair should be tested against the existing balance,
  date, reference, malformed-number and multi-event contrasts before changing
  any reviewed labels.
- **Completion evidence needing cautious adjudication:**37 cases lack a
  recognized completion cue. Several say “You have a purchase transaction” or
  “purchase transaction on account”; these imply a completed purchase in
  ordinary usage, but the current structural contract deliberately does not
  treat the noun alone as proof that an authorization settled. The fixtures
  are synthetic/exposed, so this review cannot establish issuer semantics. Keep
  them in review until a general phrase rule is supported by trustworthy
  message evidence and contrasts with authorization/pending messages.
- **Transfer relationship remains unresolved:**37 cases contain a transfer
  cue, often an outward/inward CliQ or a named/numbered recipient or sender.
  The implementation only resolves relation from explicit own-account or
  “another person” patterns. A separately reviewed rule could treat explicit
  transfer to/from a distinct named beneficiary as external, while retaining
  review for masked-account-only or otherwise unbound parties. Do not infer
  ownership from two masks or direction alone.

The16 name differences expose material entity-span issues, not merely the
approved exact-text change. Examples include `Acc` selected instead of a later
merchant after `at`, account/date/reference text returned as a party, `.COM`
truncated from `SHEIN.COM`/`AMAZON.COM`, and Arabic payment-mode wording such as
`بواسطة بطاقتك` included or `كهرباء إربد`/`أمنية إنترنت` omitted. Exact source
preservation is only valid after the right party span is identified. Repair
anchor selection and stop boundaries with generic role-based rules; do not add
business-name registries or fixture-specific exceptions.

The remaining review cases with explicit completed movement but unresolved
direction/amount/ownership should remain review until those fields resolve.
In particular, generic “purchase transaction” completion and inference of an
external counterparty are separate policy/evidence questions; a broad pattern
that makes the frozen226 gate pass would conceal those distinctions.

Next bounded implementation task: repair Arabic balance-span masking first,
then the generic party-anchor/span defects, with new authored positive/negative
contrasts and full Python/TypeScript/browser parity. Keep the current frozen226
labels unchanged and compare a fresh report run; do not migrate callers.
Completion and transfer-party rules remain separately gated on trustworthy
evidence. Trained weights, corpus labels, reserved final tests and the mobile
app remain unchanged.

### Parsing repair completed,2026-10-26

The owner approved the bounded repair. Shared evidence grammar1.0.1 now masks
Arabic balance values with `هو`, new/remaining balance descriptors and a trailing
balance label. Prefix balance spans take precedence over suffix labels; an
unreadable balance or unrelated second monetary amount cannot silently consume
the transaction amount. Both engines use the same masking for amount selection
and the existing multiple-event check.

Party extraction now prefers explicit party/biller labels, skips account/mask
roles, preserves internal dots, and stops at date, amount, payment-mode and
transfer-channel boundaries. Exact original case, diacritics, spacing and digit
script remain preserved. Generic service types and a payment channel alone do
not identify the biller. Correction to the initial triage: the empty biller in
`TC_POS_HOU_005` is appropriate because only eFAWATEERcom is named. No completion,
direction or transfer-ownership rule was broadened.

Final report `data/reports/behavior/detailed_parsing_v2.json` has31/31 authored
tracking matches, the same30/31 full-field matches/known currency annotation
issue,70/70 contextual expected-field matches and349/349 complete
Python/TypeScript/browser comparisons. The28 added parsing controls are also
checked under all three numeral scripts (84 variants per runtime). All102 unit
safeguards and the frozen226-case legacy gate pass. The browser tester bundles
the repaired canonical source. These are exposed development results, not
independent accuracy or a Hermes performance measurement.

| Frozen development comparison | Before repair (Slice1 v3) | After repair |
| --- | --- | --- |
| Detailed include/review/exclude |25 /113 /88 |33 /105 /88 |
| Amount unresolved among the original23 affected cases |23 |2 |
| Previously accepted legacy cases still sent to review |82 |75 |
| Completion/direction/ownership changed |— |0 of226 |
| Legacy complete outputs changed |— |0 of226 |

Twenty-one of the23 affected amounts now resolve; the two remaining messages
contain misspelled balance/transaction wording and retain review. Eight cases
move from review to include: seven were already accepted by legacy; one
(`TC_ADV_SND_012`) was rejected solely by legacy sender formatting. This joins
the previously documented sender-only disagreement and follows the approved
metadata policy. No includes moved to review/exclude. The original16 party
differences yield15 corrected source spans and the justified channel-only null.
Across all226 cases,84 party values change and25 amounts resolve; these counts
include partially known fields on reviewed messages and are not accuracy rates.

Six jointly included party values still differ from legacy: channel-only and
generic bill-type/agent roles remain null; three exact source phrases retain
`تاجر` before the business. Their boundaries have not been independently
adjudicated. Do not strip role/descriptor words merely to agree with the older
extractor. Among75 legacy-included reviews, overlapping remaining reasons are
37 completion,37 ownership,12 direction and2 amount;38 retain completed status.

Before/after outputs, every changed field and source-report hashes are preserved
privately in `data/private/detailed_parsing_repair_v1/before.json` and
`after_v2.json`, with deduplicated input manifests. The earlier parsing_v1 report
and private `after.json` retain an intermediate version. Private source replay
`data/private/entity_intake/web_review_v1/detailed_parsing_v2.json` keeps the OTP
excluded and the other three messages reviewed; all three runtimes agree,
C TOWN remains unresolved and JO-PETROL remains exact. Source admission and
annotation flags are unchanged. No model bytes or frozen corpus labels changed.

Next: inspect the remaining completion and P2P ownership cases against the
existing original-message evidence before proposing general rules. The current
33 inclusions/105 reviews do not justify a default caller migration. No new
originals request, training, final-test inference or promotion is needed for
that evidence review.

### Source-supported purchase wording,2026-10-26

The owner confirmed that the original Arab Bank “You have a purchase
transaction” alerts were actual purchases with money deducted. This applies to
four identified source blocks (`arab-seeds-001`,002,004,011); it does not prove
universal issuer settlement semantics or authenticate arbitrary copied text.
For the named Capital Bank transfers, the owner selected **Mixed or unknown**.
No individual own/external relationship was inferred from that answer.

Private evidence `data/private/sms_provenance/completion_transfer_evidence_v1.json`
records those answers, exact source/audit/code hashes and before outputs. All26
block offsets were checked against their original decoded bytes (including CRLF),
not a newline-normalized text view. The matching after replay is
`completion_transfer_after_v1.json`; all26 outputs agree across Python/TS/browser,
all four confirmed purchases now include, and all26 legacy results and transfer
relationships are unchanged. Only those four source outputs change. Originals,
audit labels and admission flags remain unchanged; this is exposed development
evidence, not an independent evaluation set.

Shared evidence grammar1.0.2 and parallel `completed_clause` / `completedClause`
now recognize a direct purchase-on-account/card receipt, direct past-tense
“made/completed a purchase”, and explicit Arabic “تمت حركة شراء”. No institution
or merchant registry is used. These forms are guarded against pending/declined
events, conditional or quoted examples, questions, authorization/hold wording,
and cross-sentence “authorization only / settlement unknown” qualifications.
Generic purchase/ATM nouns alone still do not establish completion. Transfer
ownership rules, model weights and the legacy caller path are unchanged.

Final report `data/reports/behavior/purchase_evidence_v1.json`:31/31 authored
tracking matches (same30/31 full-field result and documented currency annotation
issue),92/92 contextual expected-field matches,371 complete three-runtime
comparisons. Twenty-two new authored controls join the28 parsing controls in
150 numeral-script variants per runtime. Full102 safeguards and the226 legacy
gate pass. The approved minimal tester was rebuilt with the canonical repair.

On the226 development cases, detailed include/review/exclude changes from
33/105/88 to65/73/88. Twenty-eight of37 previously unrecognized completion cases
now establish completion;27 become included and one still needs an amount.
Five additional inclusions disagree with old exclusions: four sender-only
rejections and `TC_EDGE_TRUNCATED_SMS_001`, whose amount/direction are known but
merchant is truncated. Both behaviors follow the approved metadata and optional
merchant policies. The frozen labels are unchanged. All226 legacy outputs and
transfer relationships are unchanged; all32 decision changes are review→include.

Current compatibility disagreements comprise48 legacy-included reviews and
seven legacy-excluded inclusions (six sender-only and one missing merchant).
Among the48 reviews, overlapping reasons:37 ownership,9 completion,12 direction,
2 amount;39 keep completed status. Script slices: Arabic-present29 include/35
review/47 exclude; no-Arabic36/38/41. These are coverage diagnostics, not measured
real-world accuracy. Caller migration remains pending.

Next bounded issue: Arabic transfer direction. The outgoing pattern can match
`دفع` inside the noun `دفعة`, creating a false outgoing cue or cancelling an
explicit incoming cue. Correct the event/word boundaries with contrasts; do not
turn a named party into proof of external ownership. General transfer ownership
cannot be recovered from these texts alone; a future owner/account context
contract would require a separate design. No new personal-message data request
or final-test inference is needed for the direction repair.

### Arabic direction repair completed,2026-10-26

Shared grammar1.0.3 restricts Arabic `دفع` to a word boundary, preserving `دفع`
and `الدفع` while rejecting embedded forms such as `دفعة`/`دفعات` as an outgoing
cue. Direction also recognizes explicit owner-account/wallet source or recipient
phrases within a transfer clause. A named account, an unbound “transfer to …”,
or a generic ATM mention still cannot establish the owner's direction. Own-account
exclusions retain priority, and external ownership is never inferred from names.

Eighteen authored controls cover incoming payment nouns, diacritics, outgoing
verbs, source/recipient possession, unbound parties, own accounts, requests,
English and mixed text. They remain outside training and independent evaluation.
The shared numeral checks now exercise204 variants per runtime. Report
`data/reports/behavior/arabic_direction_v1.json` has110/110 expected-field control
matches,371+18=389 complete canonical and legacy runtime comparisons, the same
31/31 policy tracking matches and30/31 full-field result/known currency issue.
All102 safeguards and the226 frozen legacy gate pass.

A new control exposed a pre-existing legacy extractor mismatch: TypeScript
treated `من` inside a longer Arabic word as a name delimiter, while Python used
a word boundary. Both now require an actual preposition boundary. The detailed
name result was already identical; this small alignment makes the full legacy
diagnostics agree on the new control without changing any existing226 legacy
outputs. One new control originally used the literal placeholder “ANOTHER
PERSON”; it was corrected to a name placeholder because that phrase explicitly
asserts external ownership. No frozen case/label was edited to pass.

Across226 cases, eight detailed direction outputs change: six become incoming
from explicit receipt/owner-recipient evidence; two unsupported outgoing cues
become uncertain. Completion, amount, currency, party, ownership and tracking
are unchanged. Counts remain65 include/73 review/88 exclude. Among48 legacy
inclusions still reviewed, overlapping causes are37 ownership,9 completion,
9 direction and2 amount;39 retain completed status. These are finite exposed
development diagnostics, not independent Arabic accuracy.

Private comparison `data/private/sms_provenance/arabic_direction_v1.json` replays
the saved purchase_evidence_v1 Python implementation/patterns as the baseline,
with unchanged numeric/currency/purpose dependencies asserted. It compares226
frozen cases,26 original blocks and4 existing web diagnostics. All256 new
canonical outputs agree across runtimes and all256 legacy outputs are unchanged
from baseline. The two ambiguous Capital source directions change outgoing→
uncertain; source ownership remains unknown. All four web results are unchanged.
Only direction/reason fields change anywhere in this comparison. Source flags,
original text and admission remain unchanged; exact inputs are snapshotted.

Next: design optional account-ownership context for the engine. The37 unknown
relationships cannot reliably be resolved from a name or two masks alone, as
the owner's Mixed or unknown answer confirmed. A separate input/contract proposal
should describe what trusted owner facts are needed and how missing/ambiguous
context preserves review, before implementation or a default caller switch.
The mobile app and trained models remain outside that design task.
