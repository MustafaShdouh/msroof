# Jordan transaction understanding — behavior and evaluation contract 1.0.0

The owner approved the refactoring plan on 2026-10-25. This is task 1: a target behavior specification that future data, models, and adapters must implement. The machine-readable contract is `config/contracts/transaction_behavior.json`. It does not change the legacy `MasroofEngine` API or claim that the current model satisfies these requirements.

The 31 authored scenarios and 18 exact saved category policies validate separately
from model measurements. Current runtime evidence and gaps are in
`docs/BEHAVIOR_EVALUATION.md`; current work status is in `STATE.md`. Neither the
specification checks nor exposed regression results establish independent accuracy.

## Inputs and scope

Required: message `text`. Optional: `sender` (text/null), `isContact` (boolean), and `receivedAt` (timestamp with UTC offset/null). Missing sender information must not prevent text analysis. Sender formatting or saved-contact membership is context, not proof that a transaction occurred or did not occur. This system classifies notification evidence; it cannot authenticate bank origin from text alone.

Support Jordanian Arabic, English, and mixed-language messages, Western/Arabic-Indic/Persian digits, and Arabic decimal/group separators. Preserve explicit foreign currencies used by Jordanian customers. Numeric preprocessing contract 1.1.0 remains the shared normalization contract; do not apply account-number masking before extracting amounts.

## Result fields

| Field | Meaning |
| --- | --- |
| `contractVersion` | Exactly `1.0.0`. |
| `transactionStatus` | `completed`, `non_transaction`, or `uncertain`: what the notification establishes about money movement. |
| `trackingDecision` | `include`, `exclude`, or `review`: whether Masroof has enough evidence to record this event under the owner's tracking policy. |
| `reasonCodes` | Unique machine-readable explanations, defined in the JSON contract. Order carries no meaning. |
| `amount` | Finite positive transaction amount or null. Not balance, OTP, date, account mask, reference, or an invented total. |
| `currency` | Three-uppercase-letter currency code; null for non-transactions. |
| `currencyResolution` | `explicit`, `default_missing`, `default_ambiguous`, or `not_applicable`. |
| `direction` | `incoming`, `outgoing`, `uncertain`, or `not_applicable`, relative to the owner. |
| `transferRelationship` | `not_transfer`, `own_accounts`, `other_person`, `unknown`, or `not_applicable`. Unknown means a transfer whose ownership relationship is unresolved. |
| `merchantOrCounterparty` | Extracted text or null; never invent a missing party. |
| `expenseCategory` | One of the 15 canonical labels, or null. |
| `categoryStatus` | `assigned`, `uncertain`, or `not_applicable`. |

These fields describe the target core result. Account masks, balance, and FX details in the old API remain outside this first contract; their later migration needs explicit contracts. A future adapter must preserve or version existing caller behavior. No compatibility adapter should silently turn an uncertain outcome into a binary certainty.

The owner clarified on 2026-10-26 that merchant/counterparty names must preserve
their exact source text, including Arabic diacritics, spacing, digit script and
descriptors. The matching/source-projection convention is recorded separately in
`config/contracts/entity_text.json`; old mixed-convention fixtures remain frozen.

## Money movement and recording policy

| Evidence | Transaction status | Tracking decision | Direction / category |
| --- | --- | --- | --- |
| Completed purchase/withdrawal/external transfer; amount and direction known | completed | include | Direction resolved; outgoing category assigned or uncertain. |
| Completed transfer to/from another person | completed | include when amount/direction resolve | Outgoing/incoming; purpose may remain unknown. |
| Completed movement explicitly between the owner's accounts | completed | exclude | Direction/category not applicable to net spending/income. |
| Transfer completed but ownership relationship unresolved | completed | review | Do not assume own-account movement or auto-record an external transfer. |
| Completion established, amount or direction missing/ambiguous | completed | review | Preserve completion evidence and unresolved fields. |
| Completion cannot be determined, including unresolved contradictory outcomes | uncertain | review | Do not fabricate a completed event. |
| OTP, declined attempt, request/pending payment, balance-only alert, ordinary chat, promotion/admin alert | non_transaction | exclude | Financial result fields null/not applicable. |

Two masked account numbers do not prove common ownership. An external transfer is not excluded simply because it names two accounts. A person saying “I sent you money” does not become a completed financial notification. Rejected or pending events must not be treated as completed based on amount or merchant words alone.

`include` requires completed status, a positive unambiguous amount, a resolved direction, and no unresolved transfer relationship. Missing merchant or category does not block inclusion. This is the contract's minimum recording completeness; it must not hide the fact that a partial notification still establishes completion. Clear own-account movement takes exclusion priority over incomplete amount fields.

Version 1 describes one event. Messages with several inseparable events, conflicting amounts, or incompatible outcomes must remain unresolved; do not sum events or select a convenient amount. Future multiple-event output requires a separate contract change.

## Amount, currency, and category policy

Select the transaction amount in context, distinguishing it from balance and identifiers. Null is the answer when a unique amount cannot be recovered. Financial output uses JSON numbers consistent with existing runtimes; evaluation must use decimal-normalized values rather than loose string/substring equality or an arbitrary cent tolerance. The exact money representation for persistence is a later integration concern.

Explicit, unambiguous currency wins. Missing or ambiguous currency defaults to JOD, per the owner's decision, with `default_missing` or `default_ambiguous` retained. This is an assumption marker, not evidence that the source explicitly said JOD. Default application must be evaluated separately from extracting a known currency.

Assign an expense category only to included outgoing transactions. Income, own-account exclusions, uncertain completion, and events awaiting amount/direction/ownership review use null category with `not_applicable`. Included outgoing payments may have null category with `uncertain`; record the transaction while leaving category unresolved. Use `Other` only for an understood expense outside the remaining categories, not as a replacement for missing knowledge.

Canonical labels, in order: Telecom; Water and Electricity; Food; Groceries; Transportation; Subscriptions; Shopping; Health; Entertainment; Education; Travel; Cash Withdrawals; Installments; Fees; Other. The JSON contract must match `data/annotations/category_annotation_schema.json`.

Existing human decisions take precedence for their exact reviewed scenarios. The fixture snapshots all 18 existing illustrative reviews (16 assigned, 2 uncertain), including choices that differ from generic purpose-first advice:

- Orange tablet paid in full → Telecom; Orange device installment → Installments; its reviewed mixed service/device bill → Telecom.
- HyperMax television example → Groceries; pharmacy cosmetics example → Health.
- University tuition installment → Education; monthly mobile plan → Telecom; Netflix renewal and JETT commuting pass → Subscriptions.
- The specific bill-channel/missing-biller example → Fees. This is not permission to call every payment through that channel Fees.
- Talabat and Apple examples with missing purchase context stay uncertain; known Talabat grocery and meal examples keep their reviewed categories.

These are authored policy examples, not observed bank SMS. Do not expand an exact decision into a universal merchant rule or overwrite it with an assistant's preferred category. Generic future category evidence may use transaction context, accepted merchant defaults, and actual corrections; a merchant name or payment channel alone does not guarantee every payment's purpose. Model scores are uncalibrated unless independently demonstrated otherwise; never present a raw score or a reviewed single example as “100% general accuracy.”

## Evaluation definitions

Freeze candidate/configuration, reviewed truth, provenance, and source/template-family partitions before final evaluation. Report raw counts plus rates and uncertainty intervals. A metric with zero eligible cases is null/unmeasurable, never 0% or 100%. Keep human-gold results separate from assistant-label agreement. Contract examples, digit variants, the 226 development-exposed cases, and original seeds with generated descendants are not independent evidence.

| Measure | Numerator / denominator and treatment of uncertainty |
| --- | --- |
| Completion status | Full confusion counts for completed/non-transaction/uncertain. Own-account movement can be completed even though excluded. |
| Tracking decision | Include/exclude/review confusion against reviewed tracking truth, with unresolved gold cases identified separately. |
| Ordinary-message false inclusion | Non-transaction gold messages wrongly included / all gold non-transactions. This is not transaction precision. |
| Eligible transaction miss/review | Completed external eligible transactions excluded or sent to review / all gold eligible completed external transactions. Abstention contributes to this count. Own-account events are not in this denominator. |
| Own-account leakage | Gold completed own-account transfers included / all gold completed own-account transfers; separately report reviews and correct exclusions. |
| Person transfer coverage | Gold completed P2P transfers included / all gold eligible completed P2P transfers, separately incoming/outgoing. |
| Amount/currency exact | Joint exact match among gold external completed cases with independently known amount and currency. Report both all eligible cases and accepted-only cases, with denominators and failures/abstentions. Missing predictions count as incorrect in the all-eligible view. |
| Currency default policy | Correct missing/ambiguous-JOD resolution / default-policy cases. Keep separate from known explicit currency extraction; a fallback does not certify the unknown real currency. |
| Direction | Correct incoming/outgoing among all gold external completed cases with known direction; missing/uncertain predictions fail the all-eligible view. Also report accepted-only accuracy. |
| Category accuracy | Correct assigned category / assignments with adjudicated category truth. Assigning a label to an adjudicated context-needed case is an unsupported assignment, not an abstention; count these as errors in the aggregate answered measure. |
| Category coverage | Gold eligible outgoing transactions receiving an assigned category / all gold eligible outgoing transactions, including detection misses/reviews. Also show the conditional category answer rate among accepted outgoing transactions, so detection errors cannot disappear. |
| End-to-end correctness | Eligible gold completed external transactions correctly included with correct amount/currency/direction / all eligible cases with those gold fields known. Add a category-inclusive measure where gold purpose is known. |

For accuracy denominators, known truth must not be manufactured from model output, merchant default, or default currency. Clearly distinguish missing message information from missing annotation. Assistant labels and unadjudicated records cannot substantiate independent accuracy. Category assignment on incoming/excluded events is a contract violation rather than a category success.

Report Arabic, English, and mixed language separately, including number scripts, unfamiliar businesses, source/template families, and P2P/own-account/ambiguous-ownership cases. Avoid counting aliases or augmented variants as independent samples. Preserve all families across languages/scripts in their assigned split. The existing 226-case regression and its exact hashes remain a separate compatibility report.

## Targets and completion checklist

The earlier suggested targets remain proposals: ordinary-message false inclusion ≤1%; eligible transaction miss/review ≤5%; accepted amount/currency ≥99%; accepted direction ≥99%; assigned category accuracy ≥90%; category coverage ≥70%. The owner approved the implementation plan, not a measured claim that these targets are met. `releaseThresholds` remains null until independent data can support the measurements and the thresholds are explicitly approved. There is no currently authorized final-test run or promotion.

Task 1 is complete when:

- The versioned contract defines outcomes, outputs, transfer/uncertainty rules, category eligibility, and metric denominators.
- Authored examples cover Arabic/English/mixed text, numeral scripts, transfer relationships, sender metadata, incomplete fields, negative messages, defaults, and category uncertainty.
- Exact saved human category decisions are preserved and cannot silently become general merchant rules.
- Validation rejects contradictory outcomes, invalid amounts/currency/category states, invented provenance, or training/evaluation admission of the policy examples.
- The full regression runner retains the frozen baseline and checks the new target-contract artifacts independently of legacy inference.

Run `py tools/contracts/validate_transaction_behavior.py` to validate the examples and snapshots; run `py -m unittest tests.python.test_transaction_behavior_contract` for semantic checks. These validate the specification, not model understanding. Task 2 is a read/provenance audit of the located real seeds and their development exposure, with fresh evaluation acquisition still required.

## Proposed uncertainty implementation,2026-10-26

Status: concrete design for owner approval; no runtime/API change implemented by
this proposal. The existing JSON contract1.0.0 supplies the result fields and
approved product rules. This implements that contract without training another
model or admitting source examples to training. The current classifier remains
an imperfect source of evidence; its score cannot establish settlement,
direction or account ownership by itself.

### Recommended interface

Add `MasroofEngine.analyzeDetailed(input)` in TypeScript and
`MasroofEngine.predict_detailed(input)` in Python. Both accept the contract's
`text`, optional `sender`, `isContact` and `receivedAt`, and return exactly the
contract's canonical result fields. Use `transactionStatus` to describe completion
and `trackingDecision` to decide recording. An absent merchant/category does not
block an otherwise complete external transaction. Metadata does not authenticate
the sender; a saved contact or personal phone number alone does not settle the
result. Canonical missing/ambiguous currency defaults to JOD regardless of the
legacy API's optional caller currency default.

Factor reusable extraction/scoring evidence from the current engines rather
than deriving the new status from their boolean result or human-readable reason.
The current sender gates, lexical direction override, fallback direction head
and automatic own-transfer inference from two masks cannot serve as canonical
truth. Preserve exact source names and tested financial-number handling. Identify
candidate amounts, currencies and roles even when the old transaction threshold
would reject; a clear debit with an unreadable amount is completed + review.
The research BIO candidate remains isolated.

The detailed result has no correctness probability. Keep uncalibrated model
scores and legacy category suggestions in developer diagnostics outside the
canonical result. Do not silently map eight legacy category labels onto the15
purpose categories. Assign a canonical category only where an existing approved
exact policy or unambiguous purpose supports it; otherwise included outgoing
spending uses null + uncertain. Do not use Other for missing knowledge. Account,
balance and FX diagnostics stay outside this first canonical contract; preserve
the existing tested extraction behavior and report any ambiguity rather than
choosing a convenient amount from multiple events.

### Evidence and decision order

1. Collect clause-level evidence for requested/pending/failed events, completed
   money movement, direction, transfer relationship and field candidates. Use
   shared Arabic/English structural patterns and existing number normalization;
   no institution/name registry, source-row ID or fixture-specific override.
2. Empty/malformed input or clear chat/OTP/request/decline/notice/balance-only
   content with no conflicting completed event is non_transaction + exclude.
   Clear code requests retain the repaired OTP behavior. If clauses describe
   conflicting outcomes or inseparable events, use uncertain + review instead
   of allowing a global word match to invent a single settled event.
3. Financial-looking content without sufficient completion evidence is
   uncertain + review. Authorization alone is not proof of settlement. Generic
   ATM activity does not establish withdrawal direction. Recognizing a merchant
   or having a high transaction score does not resolve either uncertainty.
4. With explicit completed-movement evidence, keep completed status. A missing
   unique amount, unclear direction or unresolved transfer ownership requires
   review. Direction must come from the event and account-owner relationship;
   a model's default expense choice is insufficient.
5. Explicit own-account movement is completed + exclude, with direction/category
   not_applicable. Two account masks alone do not prove common ownership. Clear
   external/person transfer language permits inclusion when amount and direction
   resolve; an unresolved transfer relationship remains unknown + review.
6. Include only completed external movement with positive unique amount,
   resolved direction and resolved transfer relationship. Resolve currency using
   explicit evidence or the approved marked JOD default. Generate reason codes
   from these evidence states and validate their consistency with the contract.

Completion/direction evidence is interpreted in context: a word such as paid,
debited or تم inside a request, quotation or failed attempt is not sufficient.
When the first implementation cannot bind the evidence to a single event, it
must review rather than infer a direction or settlement from the score. Preserve
these unresolved cases for diagnostics without treating them as new gold data.

| Message evidence | Completion status | Tracking decision | Field treatment |
| --- | --- | --- | --- |
| Code needed to complete payment | non_transaction | exclude | Financial fields null/not_applicable |
| Generic ATM activity; direction not stated | uncertain | review | Visible amount/currency may remain; direction uncertain |
| Card authorization; settlement not established | uncertain | review | Do not infer completed spending or assign a category |
| Explicit debit, amount unreadable | completed | review | Amount null; preserve independently established direction |
| Completed P2P receipt with amount and direction | completed | include | Preserve exact named counterparty when present |
| Explicit completed transfer between own accounts | completed | exclude | No net direction or expense category |
| Completed transfer, ownership relationship unclear | completed | review | Transfer relationship unknown |

### Compatibility and small implementation slices

**Slice1 — detailed core and evidence report.** Add the detailed methods,
shared evidence grammar and parallel Python/TS decision code. Initially keep
`analyze`/`predict` as the named legacy path while comparing results. The browser
tester gets a developer comparison view with the canonical status, decision and
reasons. Review/exclude results are never offered as loggable transactions in
that view. Do not claim legacy callers are fixed by merely adding a new method.

**Slice2 — safe caller projection after the comparison is reviewed.** Route
normal `analyze`/`predict` through the approved detailed assessment. Return
`isValidTransaction:true` and populated legacy `data` only for include. Both
review and exclude return false + null legacy data, with the complete canonical
result in an additive `assessment` field so callers can distinguish them.
Existing legacy category fields remain explicitly deprecated suggestions;
canonical purpose/category status is authoritative. The browser default shows
canonical status and category, including Review required. No mobile app edits
are part of these slices. Keep the old inference path explicitly available for
development comparison while its replacement is measured; do not delete it as
part of this uncertainty task.

This is a compatibility migration: some previously accepted ambiguous messages
will cease to be automatically loggable; some clearly completed receipts will
pass despite contact/phone metadata. Record every changed decision and field.
Freeze the226-case corpus and labels. Continue measuring the old path against
its existing baseline; compare the new path separately with approved contract
semantics. An old label that conflicts with the contract is reported as a
compatibility disagreement, never relabeled or hidden to obtain a passing score.
Category suggestions and caller-supplied default currencies must not silently
override canonical category uncertainty or the JOD policy.

### Acceptance and scope limits

- Every canonical result validates against `validate_result`; Python/TS/browser
  canonical outputs agree on every exercised case, including reason-code sets.
- Target31/31 tracking decisions on the existing authored policy probes; also
  report completion, direction, ownership and all known-field disagreements.
  These are conformance checks, not independent accuracy or release thresholds.
- Additional authored contrasts cover code requests versus completed receipts,
  requested versus completed P2P, own versus external/unclear transfers, generic
  ATM versus explicit withdrawal/deposit, missing amounts, conflicting evidence,
  metadata changes, explicit versus default currency and Arabic/English/mixed
  forms with the three digit scripts. They remain outside training/final tests.
- Privately replay the four source examples: OTP excluded; three unresolved
  examples reviewed. Source origin/field-boundary gaps remain unresolved. Their
  now-exposed messages are diagnostic-only and cannot establish general accuracy.
- The compatibility projection never exposes legacy transaction data on review
  or exclude; the assessment retains partial known facts and explains uncertainty.
- Report all226 frozen compatibility outcomes, numeric/exact-name safeguards,
  category answer/abstention changes and stable source/model/data hashes. The old
  path must retain its measured gate; intentional new-path differences require
  visible review before Slice2. Preserve new report inputs under new run IDs.

No new numeric confidence threshold is proposed. No independent dataset,
meaningful accuracy target or safe deployment claim is implied. Implementation
of Slice1 requires owner approval of this concrete API design under Project
Control; Slice2 waits for review of its measured compatibility differences.
Training, final-test evaluation, promotion/publication and legacy deletion remain
separate decisions.
