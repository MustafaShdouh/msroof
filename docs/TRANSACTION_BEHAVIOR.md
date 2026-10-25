# Jordan transaction understanding — behavior and evaluation contract 1.0.0

The owner approved the refactoring plan on 2026-10-25. This is task 1: a target behavior specification that future data, models, and adapters must implement. The machine-readable contract is `config/contracts/transaction_behavior.json`. It does not change the legacy `MasroofEngine` API or claim that the current model satisfies these requirements.

Implementation check: 31 authored scenarios and 18 exact saved category policies validate; 13 contract safeguards pass. The consolidated runner passes its 34 unit checks, existing preprocessing/scoring/browser checks, and all 226 frozen cases in both Python and TypeScript. These are specification/regression results, not new accuracy claims or final-test results.

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
