# Jordan transaction understanding — behavior and evaluation contract 1.0.0

The owner approved the refactoring plan on 2026-10-25. This is task 1: a target behavior specification that future data, models, and adapters must implement. The machine-readable contract is `config/contracts/transaction_behavior.json`. It does not change the legacy `MasroofEngine` API or claim that the current model satisfies these requirements.

The 31 authored scenarios and 18 exact saved category policies validate separately
from model measurements. Current runtime evidence and gaps are in
`docs/BEHAVIOR_EVALUATION.md`; delivery status is in [the teammate handover](TEAMMATE_HANDOFF.md). Neither the
specification checks nor exposed regression results establish independent accuracy.

## Inputs and scope

Required: message `text`. Optional: `sender` (text/null), `isContact` (boolean), and `receivedAt` (timestamp with UTC offset/null). Missing sender information must not prevent text analysis. Sender formatting or saved-contact membership is context, not proof that a transaction occurred or did not occur. This system classifies notification evidence; it cannot authenticate bank origin from text alone.

An optional ownership-context interface is proposed at the end of this document.
It is a separate opt-in request/response wrapper; the active1.0.0 input above
does not accept those proposed fields yet.

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

Status: owner approved2026-10-26; Slice1 is implemented, with subsequent parsing
and source-supported purchase/direction repairs measured in `data/reports/behavior/arabic_direction_v1.json`.
Slice2 caller migration awaits
review of the differences. The existing JSON contract1.0.0 supplies the result fields and
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

No new numeric confidence threshold is introduced. The existing classifier's0.70
cutoff is reused only to send otherwise unrecognized candidate text to review;
it never establishes completion, direction or ownership. No independent dataset,
meaningful accuracy target or safe deployment claim is implied. Slice1 approval
was given2026-10-26 and implementation is complete; Slice2 waits for review of its
measured compatibility differences. See `docs/BEHAVIOR_EVALUATION.md` for results.
Training, final-test evaluation, promotion/publication and legacy deletion remain
separate decisions.

## Opt-in ownership context,2026-10-26

Status: owner approved implementation; available as a separate optional API.
The current implementation report is `data/reports/behavior/arabic_message_semantics_v1.json`.
The unchanged no-context baseline leaves37 transfer
relationships unresolved among the legacy-included development cases. The owner
answered **Mixed or unknown** for the original named Capital transfers; no
individual ownership label follows from that answer. A context interface cannot
resolve these records until actual ownership information is supplied.

### Implemented first slice

Accept an explicit human confirmation of the relationship for one particular
message. A confirmation says either “between my own accounts”, “with another
person”, or “I do not know”. It supplies ownership only. It does not establish
completion, amount, direction, sender authenticity or purchase category.

`analyzeDetailed` / `predict_detailed` and their existing input/result contract
remain unchanged. TypeScript `analyzeWithOwnership(request)` and
Python `predict_with_ownership(request)` are separate opt-in methods. Their wrapper version is1.0.0;
the nested assessment retains the existing transaction contract1.0.0. The active
canonical contract, validator, weights and default callers remain unchanged.
The wrapper contract is `config/contracts/ownership_context.json`; its response
validator is `tools/contracts/validate_ownership_context.py`. Optional metadata
fields follow the existing input interface's types; they supply no ownership fact.
The optional tester panel constructs a confirmation only after an explicit button
click; it stores nothing across reloads and revokes confirmation after body/sender/
contact edits, sample loading or New message. Mobile callers remain separate.

Python usage (the caller must first obtain the actual human confirmation):

```python
from src.python.engine import MasroofEngine

text = "JOD 20.00 debited. Transfer to LOCAL PERSON completed."
result = MasroofEngine().predict_with_ownership({
    "ownerScopeId": "profile-1",
    "messageId": "received-sms-1",
    "message": {"text": text},
    "ownershipContext": {
        "schemaVersion": "1.0.0", "ownerScopeId": "profile-1",
        "messageId": "received-sms-1", "text": text,
        "evidence": "user_confirmed", "relationship": "other_person",
    },
})
```

The TypeScript method accepts the same object. A valid request without
`ownershipContext`, or with null context, returns the existing detailed assessment
inside the wrapper with `absent/not_provided`. It does not resolve the37 records
without new facts. Reproduce the authored acceptance and baseline comparison with
`py -X utf8 -m training.evaluation.arabic_semantics --run-id arabic_message_semantics_v1 --check`.

```typescript
interface OwnershipRequest {
  ownerScopeId: string; // Opaque caller profile ID; not a bank or legal name.
  messageId: string;    // Stable caller ID for this specific message.
  message: DetailedInput;
  ownershipContext?: {
    schemaVersion: '1.0.0';
    ownerScopeId: string;
    messageId: string;
    text: string;       // Exact original message.text, including whitespace.
    evidence: 'user_confirmed';
    relationship: 'own_accounts' | 'other_person' | 'unknown';
  } | null;
}

interface OwnershipResponse {
  ownershipContractVersion: '1.0.0';
  assessment: DetailedResult; // Existing exact field set and reason codes.
  contextStatus: 'absent' | 'applied' | 'unresolved' |
    'not_applicable' | 'invalid' | 'conflict';
  contextReason: string;      // Closed vocabulary specified below.
}
```

IDs must be nonempty strings, compared exactly without trimming or case folding;
whitespace-only IDs are invalid. Require the exact wrapper/context keys/types/enums and
reject unknown fields or unsupported versions. Binding requires equality of
ownerScopeId, messageId and the exact raw text. Normalize neither names nor the
text for this comparison. Thus a confirmation cannot silently follow an edited
amount, another digit script, another message with similar wording, or another
owner profile. Same IDs with changed text must also fail binding.

Exact text is deliberately included instead of adding a new hashing dependency
to the offline runtime. The caller must assign distinct IDs to distinct received
messages, even when their bodies match. These IDs/text comparisons are consistency
checks, not authentication. The engine cannot verify that the caller's
`user_confirmed` claim was actually made by a human; trusted caller code must
construct it from an explicit review, never from SMS content, a model score,
assistant guessing, sender name, or presence/absence in an account list.

The engine performs no context storage, automatic reuse, network request, logging
of source text, or account enrollment. A future caller can persist confirmations
privately; persistence and mobile UI are outside this slice. A mistaken human
confirmation remains possible: return its provenance diagnostic without calling
it a correctness probability or treating it as training truth.

### Resolution order and conflict behavior

1. Validate the wrapper's required IDs and message envelope, then produce the
   same message evidence as the current detailed path. For a valid wrapper,
   missing/null context returns the exact current assessment with absent/not_provided.
   This must hold field-for-field, including names, reason ordering and defaults.
2. Validate supplied context and binding. Missing/non-string message text retains
   the existing empty_or_malformed assessment. Other malformed wrapper/context
   fields use the invalid diagnostic behavior below. Invalid context must never
   promote a transaction or trigger an own-account exclusion. For a recognized
   financial transfer, use ownership unknown + review, preserving independently
   known completion/amount/currency and physical direction. If the body had only
   own-account direction not_applicable, change that to uncertain. For ordinary
   messages and non-transfer events, preserve the body assessment. Use a stable
   diagnostic reason; do not throw on user-supplied malformed context or echo it.
3. For a valid context on non_transaction content or an event with not_transfer,
   keep the assessment unchanged and return not_applicable. Context cannot turn
   chat, OTP, requests, failed attempts or a purchase into a completed transfer.
   An unrecognized paired debit/credit message also needs a separate transfer
   event-detection improvement; a relationship label is not a shortcut for it.
4. Valid relationship unknown adds no fact: preserve the exact body assessment,
   with unresolved/confirmation_unknown. It does not contradict an explicit own
   or external relationship already established by the text.
5. Valid own_accounts/other_person can resolve a recognized unknown transfer or
   agree with the body's explicit relationship. Then derive decision/category
   using existing rules. Own-account movement has direction not_applicable and
   is excluded only when completion is established; uncertain completion still
   requires review. Other-person movement requires completed status, positive
   unique amount and a resolved body direction to include. Context never fills
   a missing amount or direction, and cannot assign a category by itself.
6. If a valid confirmation contradicts an explicit own/external relationship in
   the body, retain completion/amount/currency facts but require review with
   transferRelationship unknown and direction uncertain. Category becomes
   not_applicable. Return conflict/text_context_conflict. Do not silently favor
   either assertion or classify the conflict as an ordinary non-transaction.

The existing canonical reason codes are recomputed from the final evidence state.
For example, a completed ownership conflict requires completed_transaction,
transfer_ownership_unresolved and direction_unresolved, plus amount_unresolved
when appropriate. Context-specific diagnostics live in the wrapper, so the
canonical validator needs no new reason codes or version change.

Closed diagnostic pairs:

| contextStatus | Permitted contextReason |
| --- | --- |
| absent | not_provided |
| applied | confirmed_relationship |
| unresolved | confirmation_unknown |
| not_applicable | non_transaction, not_a_transfer |
| invalid | invalid_request, invalid_context, unsupported_version, owner_mismatch, message_mismatch, untrusted_evidence |
| conflict | text_context_conflict |

For invalid diagnostics, structural request errors take precedence over context
shape/version, then evidence, then owner binding, then message ID/text binding.
For valid context, non-transaction/non-transfer applicability is checked before
unknown/agreement/conflict resolution. No-context requests still validate the
wrapper's required fields; malformed wrappers use invalid_request rather than
the absent fast path. This gives both languages a deterministic error order.

### Acceptance cases

These are authored design cases, not source labels, training rows, or accuracy
measurements. Executable controls are in `tests/fixtures/ownership_context_cases.json`
and `tests/python/test_ownership_context.py`.

| Message evidence / context | Required assessment and diagnostic |
| --- | --- |
| Unknown transfer, context omitted or null | Exact current result; absent |
| Completed transfer, amount/direction known, user confirms other person | Include; other_person; applied |
| Completed transfer, user confirms own accounts | Exclude; own_accounts; direction/category not_applicable; applied |
| Completed own transfer, amount unreadable | Exclude; amount null; applied |
| Completion uncertain, user confirms own accounts | Still uncertain + review; applied |
| Completed external confirmation, amount or direction unresolved | Review; preserve the unresolved field; applied |
| User says unknown, even after seeing a party name | Exact body result; unresolved |
| Source text says own accounts, confirmation says other person (or reverse) | Completed status retained when known; review; relationship/direction uncertain; conflict |
| Context copied to different owner/message ID | No ownership promotion/exclusion; invalid |
| Amount, whitespace or digit script differs from bound original text | No ownership promotion/exclusion; invalid |
| Wrong types, extra keys, unsupported version or machine-derived evidence | No ownership promotion/exclusion; invalid |
| Two distinct records have identical bodies but different IDs | Confirmation applies only to its bound ID |
| OTP/chat/request/decline with a valid confirmation | Existing non-transaction exclusion; not_applicable |
| Completed purchase/non-transfer with valid confirmation | Exact body result; not_applicable |
| An array of two contrary confirmations instead of one context object | invalid_context; no implicit merge or last-record-wins rule |

The API accepts already-parsed objects; it cannot detect duplicate JSON keys that
a caller's parser discarded. Strict duplicate-key handling at serialization is
the caller's responsibility. The object schema itself has one value per field.

### Why account-list automation is deferred

The current canonical result has one party field and does not expose separately
bound source/destination account identifiers and spans. A reliable account-list
resolver first needs an endpoint-role contract. Only positive, uniquely matched
ownership facts could then be used: a known own source plus an unknown recipient
still leaves ownership unknown; an absent registry match does not mean external.
Names and shared last digits are insufficient. Matching masks needs explicit
scope, identifier type and collision handling; Unicode digit normalization alone
does not make `*6284`, `xxxx6284` and a full account number equivalent. No account
alias inference, bank registry, person-name ownership registry or completeness
assumption belongs in this first slice.

### Sample review and proposed paired-movement repair

After the ownership tester was added, a read-only review checked the CliQ In,
CliQ Out and `internal_transfer` presets, plus the English/Arabic explicit-own
contract examples. Five texts × four context choices × three numeral scripts
(Latin, Arabic-Indic, Eastern Arabic-Indic) produced60 complete Python/TypeScript/
browser matches. These are exposed development checks; the context choices are
hypothetical test inputs, not new human ownership facts or training labels.

CliQ In/Out preserve incoming/outgoing direction and amount, review unknown
ownership, include confirmed other-person movements, and exclude confirmed own
movements. Outgoing CliQ purpose remains unknown rather than inventing a category.
Explicit-own text is excluded without context; a contrary other-person confirmation
correctly requires review.

The preset button called Own-account transfer is only a historical label. Its body
describes one shared amount debited from a masked identifier and credited to
another; it does not establish ownership or explicitly use transfer wording.
Current detailed output is completed + review + uncertain direction + not_transfer;
valid context returns not_applicable/not_a_transfer. This is the event-detection
limitation already reserved in the ownership design, not a failing binding rule.
Do not use the preset name as a label or let context manufacture a transfer.

Proposed next bounded change (not implemented in this review):

- Recognize a narrowly linked debit-from / credit-to movement with one shared
  transaction amount and two explicit account-identifier roles, in parallel
  English/Arabic structural patterns. Apply existing negative/completion guards;
  reject unrelated events, OTP/requests/declines, multiple competing amounts and
  identifiers occurring only in balance/date/authorization text.
- Set transferRelationship to unknown. Two identifiers establish neither own
  ownership nor another person. Preserve unresolved physical direction when both
  legs are present and the owner's role is not stated.
- For the preset, no context or unknown confirmation must still review. Explicit
  own confirmation may exclude a completed movement; other-person confirmation
  must still review if direction is unresolved. Do not change amount/currency or
  infer a category from ownership.
- Add bilingual linked/unlinked and negative-event contrasts with the same numeral
  scripts. Measure every changed detailed output against archived source **and**
  evidence-contract bytes; preserve the legacy226-case gate, all frozen labels,
  model bytes and reservations. Existing ownership baseline checks deliberately
  assert an unchanged evidence contract: replace that assumption with an explicit
  reviewed change comparison for this future repair, rather than silently relaxing
  it or attempting historical replay with the new patterns.
- Rename the tester sample to Paired debit / credit during the repair. Keep the
  underlying preset/fixtures intact; no default caller migration, training,
  account-list automation or production publication follows from this proposal.

### Implementation and review boundary

The paired-movement proposal above was subsequently approved and implemented in
evidence grammar1.0.4. Two strict shared templates recognize one explicit amount
with linked debited-from/credited-to masked endpoints in English or Arabic. No
other financial event may remain outside the match; dates and balances retain
their existing handling. Missing/competing amounts, same masks, unlinked events,
card/reference slots and negative/conditional language cannot acquire ownership
confirmation through this detector. Account abbreviations such as Acc. are
supported without joining unrelated sentences. Scope is deliberately narrow;
there is no account registry, alias inference or new authenticity claim.

Without explicit text ownership the movement remains unknown + review + uncertain
direction. Own-account confirmation excludes a completed movement; another-person
confirmation still reviews unresolved direction. Explicit-own Arabic wording
continues to count as a body fact. The tester sample title is now Paired debit /
credit; its text and all older fixtures remain unchanged.

The39 new texts across three numeral scripts produce117 body/legacy comparisons
and468 wrapper comparisons in all three runtimes. Thirty body variants change
relative to the archived source and grammar; their full field differences are in
the report. One previously unrecognized ownership control has a versioned expected
outcome override in paired_movement_cases.json, preserving the old fixture bytes.
All389 prior detailed AND legacy assessments remain identical;778 omitted/null
context requests per runtime retain them. A Python-only legacy word-boundary
inconsistency also needed correction: three new numeral variants stop treating
«الحساب …» as a party name and now match TypeScript/browser.

At the paired-movement milestone, remaining findings were explicit in its report:
four unrecognized Arabic controls, in all three scripts, retain pre-existing
message-only inclusions (failure with definite العملية, conditional wording,
separate debit/credit sentences, and same-mask debit/credit). They gain no new
transfer recognition or ownership application. Their ordinary completion/direction
assessment was subsequently repaired below; these controls are not independent data.

### Arabic completion and credit repair, evidence1.0.5

The failed-operation grammar now covers definite العملية/الحركة. Pure Arabic
conditions (including clitic-prefixed إذا, لو, عندما, كلما and في حال/حالة) cannot
prove completion. Conditional clauses are scoped separately: a receipt followed
by help text stays factual, while an additional hypothetical money movement
requires review without erasing the earlier amount/direction. Long conditional
clauses and decimal amounts cannot bypass the guard.

Definite monetary credit wording «إضافة المبلغ» supplies incoming evidence.
Pronominal «إضافته إلى الحساب/محفظتك» requires an account/wallet target; a
perfective تم/تمت phrase can establish completion. Product/cart additions and
generic ledger posting do not become incoming payments through these rules.
When both debit and credit facts remain, direction stays uncertain; neither
same masks nor ownership confirmation resolves it automatically.

The four earlier inclusion findings now produce review for the contradictory
failure and ambiguous debit/credit texts, or exclusion for the purely conditional
text. Their exact field revisions live in the new
`tests/fixtures/arabic_message_semantics_cases.json`; the39-text prior fixture and
its historical report remain unchanged. Forty-five authored bilingual contrasts,
three digit scripts,135 body and540 wrapper comparisons agree across Python,
TypeScript and the browser. Eighteen previously included variants now exclude or
review; all changes against the saved1.0.4 source/engine/grammar are recorded.
All389 earlier detailed and legacy outputs remain identical.153 Python tests,
ten TypeScript suites and226 frozen cases pass. The tester's detailed comparison
and optional panel expose the repair; its default legacy view remains unchanged.
These are conformance checks, not independent accuracy or a model promotion.

The implemented ownership wrapper keeps the separate versioned contract/validator
and canonical result schema. It applies ownership before decision/category,
re-evaluates purpose after a reviewed transfer becomes included outgoing, and
preserves raw names, numeral handling and the approved tester layout.

Verify Python/TypeScript/browser equality including wrapper diagnostics, all
acceptance cases and numeral/name contrasts, current no-context measurements,
and the frozen legacy gate. Separate context-aided results from body-only
measurements, report their coverage/abstentions, and preserve new source hashes
under a new report ID. No promotion or accuracy claim follows from passing these
authored cases. A developer-only opt-in comparison control can be considered
after the engine contract works; default caller migration remains a separate gate.

### Explicit example introductions, evidence 1.0.6

The shared `reportedSpeech` pattern now recognizes explicit introductions such as
“This is an example…” and “هذا مثال توضيحي…”, including qualified teaching/test
examples and optional Note/ملاحظة prefixes. These new alternatives are anchored
to the start of a clause. The existing detailed assessment consequently treats
their transaction wording as reported speech rather than completion evidence.
Both originally reported examples now return `non_transaction` / `exclude`,
reason `personal_conversation`, with no monetary or party fields.

Quotation marks alone do not reject a notification. Quoted merchant names,
including “Example Shop” and “Teaching Example”, remain valid receipt content.
The current conservative conflict policy remains: mixed actual/example clauses
or examples containing additional completed-looking sentences return review.
This correction does not implement a general parser for nested quotations or
arbitrary reported speech.

The correction applies to `predict_detailed` / `analyzeDetailed` and the tester's
existing message-only recording assessment. Legacy caller outputs and all
learned heads remain unchanged; no model training or promotion occurred. Fourteen
authored controls, expanded over three numeric scripts and two sender/contact
settings, provide 84 complete Python/TypeScript/built-browser comparisons. A
436-input before/after check changes only the two reported examples. These are
structural conformance results, not learned-model or independent accuracy gains.
